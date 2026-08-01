"""Anthropic Messages API served by the free vendor CLIs.

Point ``ANTHROPIC_BASE_URL`` at this and Claude Code's own harness — subagents,
Workflow phases, schemas, context management — runs on GLM or Gemini weights
with **no Claude wrapper agent in the path**.

WHY THIS EXISTS (measured 2026-08-01, not assumed)
--------------------------------------------------
The `vendor-lane` wrapper works, but every free model call needs a paid Claude
agent to babysit it. Under a 5-workflow fan-out the box saturated: load 10.41 on
10 cores, `claude` at 35.8% CPU, per-call hook shells at ~13.5% each — while the
vendor CLIs sat at **4.5% of 1000%**, asleep on network I/O. A separate test
showed the vendors parallelise fine (N=4 → 10.2s median, N=8 → 12.9s, 8/8 ok).

So the ceiling was never the free models or a vendor throttle. It was the
wrapper. This removes it: one HTTP request per call instead of a Claude agent,
its tool calls, and its hook chain.

WHAT IT DOES AND DOES NOT DO
----------------------------
The backend is the vendor **CLI**, not a vendor API — devin's OpenAI-compatible
endpoint authenticates but has zero models entitled to this subscription, and
agy's live credential is not on disk. The CLI is the only free path that works.

* **Text stages** — full fidelity. The vendor is itself an agent, so it reads
  files and runs commands through its OWN tools and returns a finished answer.
* **Schema stages** — supported by SYNTHESIS. Claude Code sends a `tools` array
  and expects a `tool_use` block; the vendor returns text. This module asks the
  vendor for JSON matching the schema and wraps it as a `tool_use` block. That
  is what makes `agent(..., {schema})` work at all here, and it is the reason a
  CLI-backed shim is worth building rather than dismissing as "text-only".
* **NOT supported** — a Claude-Code-orchestrated multi-turn tool loop. CC cannot
  drive Read/Grep/Bash on this backend under its own permission layer; the
  vendor uses its own tools instead. A stage needing CC's tools must stay on a
  Claude model.

Every non-Anthropic route fails CLOSED. There is no fallback to Anthropic: a
silent fallback would return a real answer from the wrong model and be
indistinguishable from success, which is the exact defect class this repo keeps
paying for.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

from .vendor_dispatch import VENDOR_SPECS, VendorCLIExecutor, resolve_model

logger = logging.getLogger("nucleus.vendor_shim")

# Model strings this shim answers for. Deliberately namespaced: routing on a
# bare tier name would also capture Claude Code's internal haiku traffic (titles,
# summarisation) and drag it through a multi-second CLI.
# Built from the REAL vendor list, longest name first. A generic
# `(?P<vendor>[a-z0-9-]+)-(?P<model>...)` cannot work: it is greedy, so
# `nucleus/devin-glm-5.2` parses as vendor `devin-glm-5` / model `2`. And the
# ambiguity is genuine rather than cosmetic — `devin-swe` is itself a hyphenated
# vendor name, so `nucleus/devin-swe-swe-1.7` has two valid readings. Alternating
# over known vendors longest-first resolves both.
def _model_re() -> "re.Pattern[str]":
    names = sorted(VENDOR_SPECS, key=len, reverse=True)
    alt = "|".join(re.escape(n) for n in names)
    return re.compile(rf"^nucleus/(?P<vendor>{alt})-(?P<model>[A-Za-z0-9.\-]+)$")


_MODEL_RE = _model_re()

_SECRET_ENV = "NUCLEUS_VENDOR_SHIM_SECRET"
_MODE_ENV = "NUCLEUS_VENDOR_SHIM_MODE"          # read | write (default read)
_TIMEOUT_ENV = "NUCLEUS_VENDOR_SHIM_TIMEOUT_S"  # per-call ceiling


def parse_model(model: str) -> Optional[Tuple[str, str]]:
    """``nucleus/devin-glm-5.2`` -> ``("devin", "glm-5.2")``; else None.

    Returns None for anything outside the namespace so the caller can 400 rather
    than guess. Validation against the real allowlist happens in :func:`resolve`.
    """
    if not isinstance(model, str):
        return None
    m = _MODEL_RE.match(model.strip())
    if not m:
        return None
    return m.group("vendor"), m.group("model")


def resolve(vendor: str, model_id: str) -> Tuple[str, str]:
    """Validate vendor+model against VENDOR_SPECS. Raises ValueError if unknown.

    Reuses the same allowlist that guards argv injection in vendor_dispatch —
    a second, drifting copy of that list is how a shim starts accepting model
    ids the CLI no longer has.
    """
    if vendor not in VENDOR_SPECS:
        raise ValueError(
            f"unknown vendor {vendor!r}; expected one of {sorted(VENDOR_SPECS)}"
        )
    return vendor, resolve_model(vendor, model_id)


def _blocks_to_text(content: Any) -> str:
    """Render an Anthropic content value to plain text.

    Handles the shapes Claude Code actually sends: a bare string, or a list of
    blocks. ``tool_use`` and ``tool_result`` are rendered rather than dropped —
    silently discarding them would corrupt a multi-turn conversation while the
    response still looked valid.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    out: List[str] = []
    for b in content:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            out.append(str(b.get("text") or ""))
        elif t == "tool_use":
            out.append(
                f"[assistant called tool {b.get('name')!r} with input "
                f"{json.dumps(b.get('input'), ensure_ascii=False)}]"
            )
        elif t == "tool_result":
            inner = b.get("content")
            rendered = _blocks_to_text(inner) if not isinstance(inner, str) else inner
            out.append(f"[tool result: {rendered}]")
        elif t == "image":
            out.append("[image omitted — this backend is text-only]")
        else:
            out.append(f"[unsupported block type {t!r} omitted]")
    return "\n".join(x for x in out if x)


def _forced_tool(
    tools: List[Dict[str, Any]], tool_choice: Any
) -> Optional[Dict[str, Any]]:
    """The tool the caller REQUIRES, or None if tools are merely available.

    This distinction is the whole correctness of the shim, and getting it wrong
    was a real defect (2026-08-01, caught by a live `claude -p` run): every
    Claude Code request carries its full tool array — Agent, Read, Bash and the
    rest — because those are *available*, not *required*. Demanding JSON on any
    tool-bearing request made GLM answer a plain question with
    "expected JSON for tool 'Agent', got unparseable output" in 2 of 4 calls.

    `tool_choice` is the signal:
      {"type": "auto"} / absent  -> model may answer in text     -> None
      {"type": "any"}            -> some tool must be called
      {"type": "tool", "name":X} -> that tool must be called
    A schema stage sets one of the latter two, which is exactly the case where
    synthesising a tool_use block is correct.
    """
    usable = [t for t in tools if isinstance(t, dict) and t.get("name")]
    if not usable:
        return None

    kind = tool_choice.get("type") if isinstance(tool_choice, dict) else None
    if kind == "tool":
        named = tool_choice.get("name")
        return next((t for t in usable if t.get("name") == named), None)
    if kind == "any":
        # Some tool is required but the caller did not say which. Prefer a
        # StructuredOutput-shaped one, since that is the schema path.
        return next(
            (t for t in usable if "structured" in str(t.get("name", "")).lower()),
            usable[0],
        )
    return None  # "auto" or absent — text is a valid answer, do not force JSON


def _schema_instruction(
    tools: List[Dict[str, Any]], tool_choice: Any
) -> Optional[Tuple[str, str]]:
    """``(tool_name, instruction)`` when a tool is REQUIRED, else None."""
    chosen = _forced_tool(tools, tool_choice)
    if chosen is None:
        return None
    name = str(chosen["name"])
    schema = chosen.get("input_schema") or chosen.get("parameters") or {}
    return name, (
        "\n\n=== REQUIRED OUTPUT FORMAT ===\n"
        "Reply with ONE JSON object and NOTHING ELSE — no prose before or after, "
        "no markdown fence. It must validate against this JSON Schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}\n"
        "Every field must be filled from your actual analysis. If you cannot "
        "determine a value, use null rather than inventing one."
    )


def flatten(payload: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Anthropic Messages payload -> (prompt, tool_name_or_None)."""
    parts: List[str] = []

    system = payload.get("system")
    sys_text = system if isinstance(system, str) else _blocks_to_text(system)
    if sys_text:
        parts.append(f"=== SYSTEM ===\n{sys_text}")

    for msg in payload.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        text = _blocks_to_text(msg.get("content"))
        if text:
            parts.append(f"=== {str(msg.get('role', 'user')).upper()} ===\n{text}")

    tool_name = None
    tools = payload.get("tools")
    if isinstance(tools, list) and tools:
        got = _schema_instruction(tools, payload.get("tool_choice"))
        if got:
            tool_name, instruction = got
            parts.append(instruction)
        else:
            # Tools available but not required — the model may answer in text.
            # Say so explicitly: CC's system prompt tells the model it HAS tools,
            # and on this backend it cannot call them, so without this it tries.
            logger.debug(
                "vendor_shim: %d tools available, none forced — text reply allowed",
                len(tools),
            )
            parts.append(
                "\n\n=== NOTE ===\nTool definitions appear above, but you CANNOT "
                "call them on this channel. Answer directly in plain text using "
                "your own capabilities."
            )

    return "\n\n".join(parts), tool_name


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Optional[Any]:
    """Pull one JSON object out of vendor text. None if there isn't one.

    Vendors wrap JSON in prose or markdown fences regardless of instruction, so
    try the fence, then the outermost brace span, then the raw string. Returning
    None (rather than a guess) lets the caller fail closed.
    """
    if not text:
        return None
    for candidate in (
        *(m.group(1) for m in _FENCE_RE.finditer(text)),
        text[text.find("{"): text.rfind("}") + 1] if "{" in text and "}" in text else "",
        text,
    ):
        c = (candidate or "").strip()
        if not c:
            continue
        try:
            return json.loads(c)
        except (ValueError, TypeError):
            continue
    return None


def _usage(prompt: str, output: str) -> Dict[str, int]:
    """Rough token accounting. CC needs plausible numbers for context math."""
    return {
        "input_tokens": max(1, len(prompt) // 4),
        "output_tokens": max(1, len(output) // 4),
    }


def build_response(
    model: str, text: str, tool_name: Optional[str], prompt: str
) -> Dict[str, Any]:
    """Anthropic Messages response. Synthesises a tool_use block when asked.

    THE SYNTHESIS IS THE POINT. A schema stage is a FORCED tool call: Claude Code
    will not accept prose where it expects a `tool_use` block. The vendor cannot
    emit one, so this wraps the JSON it returned as that block. Without this,
    every `agent(..., {schema})` stage fails and the shim is worth little.
    """
    content: List[Dict[str, Any]] = []
    stop_reason = "end_turn"

    if tool_name:
        parsed = extract_json(text)
        if parsed is not None:
            content.append({
                "type": "tool_use",
                "id": "toolu_" + uuid.uuid4().hex[:24],
                "name": tool_name,
                "input": parsed if isinstance(parsed, dict) else {"value": parsed},
            })
            stop_reason = "tool_use"
        else:
            # Fail LOUD in the text, not silently: a schema stage that quietly
            # degrades to prose looks like a model that chose not to use a tool.
            logger.warning(
                "vendor_shim: tool %r requested but vendor returned no parseable "
                "JSON (%d chars) — returning text, stage will likely fail",
                tool_name, len(text),
            )
            content.append({
                "type": "text",
                "text": f"[vendor-shim: expected JSON for tool {tool_name!r}, "
                        f"got unparseable output]\n{text}",
            })
    else:
        content.append({"type": "text", "text": text})

    return {
        "id": "msg_" + uuid.uuid4().hex[:24],
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": _usage(prompt, text),
    }


def sse_frames(body: Dict[str, Any]) -> str:
    """Render a completed response as an Anthropic SSE stream.

    Claude Code sends ``stream: true`` and needs the event sequence, but SSE does
    not require incremental chunks — one delta carrying the whole value is a
    valid stream. The vendor CLI is one-shot, so this emits the finished result
    in the shape CC's parser expects.
    """
    msg_start = {k: v for k, v in body.items() if k != "content"}
    msg_start["content"] = []
    out = [_ev("message_start", {"type": "message_start", "message": msg_start})]

    for i, block in enumerate(body["content"]):
        if block["type"] == "tool_use":
            out.append(_ev("content_block_start", {
                "type": "content_block_start", "index": i,
                "content_block": {"type": "tool_use", "id": block["id"],
                                  "name": block["name"], "input": {}},
            }))
            out.append(_ev("content_block_delta", {
                "type": "content_block_delta", "index": i,
                "delta": {"type": "input_json_delta",
                          "partial_json": json.dumps(block["input"], ensure_ascii=False)},
            }))
        else:
            out.append(_ev("content_block_start", {
                "type": "content_block_start", "index": i,
                "content_block": {"type": "text", "text": ""},
            }))
            out.append(_ev("content_block_delta", {
                "type": "content_block_delta", "index": i,
                "delta": {"type": "text_delta", "text": block["text"]},
            }))
        out.append(_ev("content_block_stop", {"type": "content_block_stop", "index": i}))

    out.append(_ev("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": body["stop_reason"], "stop_sequence": None},
        "usage": {"output_tokens": body["usage"]["output_tokens"]},
    }))
    out.append(_ev("message_stop", {"type": "message_stop"}))
    return "".join(out)


def _ev(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _err(status: int, etype: str, message: str) -> Tuple[int, Dict[str, Any]]:
    return status, {"type": "error", "error": {"type": etype, "message": message}}


def handle_messages(payload: Dict[str, Any]) -> Tuple[int, Any, bool]:
    """Core routing. Returns ``(status, body, is_stream)``. Never raises."""
    model = payload.get("model")
    parsed = parse_model(model or "")
    if not parsed:
        return (*_err(
            400, "invalid_request_error",
            f"model {model!r} is not in the nucleus/ namespace. This shim only "
            f"serves nucleus/<vendor>-<model_id>; it does NOT proxy to Anthropic.",
        ), False)

    try:
        vendor, model_id = resolve(*parsed)
    except ValueError as exc:
        return (*_err(400, "invalid_request_error", str(exc)), False)

    prompt, tool_name = flatten(payload)
    if not prompt.strip():
        return (*_err(400, "invalid_request_error", "no renderable content in request"), False)

    mode = os.environ.get(_MODE_ENV, "read")
    timeout_s = int(os.environ.get(_TIMEOUT_ENV, "1800"))

    result = VendorCLIExecutor(
        vendor, prompt, model=model_id, mode=mode, timeout_s=timeout_s
    ).run()

    # FAIL CLOSED. No fallback to Anthropic, ever. A fallback here would return
    # a genuine answer from a model the caller did not ask for, and nothing
    # downstream could tell the difference.
    if result.status != "ok" or not result.produced_output:
        logger.warning(
            "vendor_shim: %s/%s FAILED status=%s rc=%s dur=%.1fs",
            vendor, model_id, result.status, result.rc, result.duration,
        )
        return (*_err(
            502, "api_error",
            f"vendor {vendor}/{model_id} did not produce output "
            f"(status={result.status}, rc={result.rc}, {result.duration:.1f}s)",
        ), False)

    logger.info(
        "vendor_shim: %s/%s ok %.1fs %d chars%s",
        vendor, model_id, result.duration, len(result.result),
        f" tool={tool_name}" if tool_name else "",
    )
    body = build_response(model, result.result, tool_name, prompt)
    return 200, body, bool(payload.get("stream"))


class _Handler(BaseHTTPRequestHandler):
    server_version = "nucleus-vendor-shim/1.0"

    # Socket read timeout. Without it, `self.rfile.read(n)` blocks FOREVER when a
    # client sends a Content-Length larger than the bytes it actually transmits —
    # ThreadingHTTPServer sets no default, so the handler thread leaks and the
    # connection never closes. Found 2026-08-01 by gemini-3.1-pro-high reviewing
    # this file THROUGH THIS SHIM, ~30 minutes after it was written.
    timeout = 30

    # Refuse absurd bodies outright rather than trying to buffer them.
    MAX_BODY = 64 * 1024 * 1024

    def log_message(self, fmt: str, *args: Any) -> None:      # noqa: A003
        logger.debug("http: " + fmt, *args)

    def _send(self, status: int, body: Any, *, sse: bool = False) -> None:
        if sse:
            raw = sse_frames(body).encode("utf-8")
            ctype = "text/event-stream"
        else:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            ctype = "application/json"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("x-shim-backend", "vendor-cli")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:                                  # noqa: N802
        if self.path.rstrip("/") == "/health":
            self._send(200, {"ok": True, "vendors": sorted(VENDOR_SPECS)})
        else:
            self._send(404, _err(404, "not_found", "no such route")[1])

    def do_POST(self) -> None:                                 # noqa: N802
        if self.path.split("?")[0].rstrip("/") != "/v1/messages":
            self._send(404, _err(404, "not_found", "no such route")[1])
            return

        secret = os.environ.get(_SECRET_ENV, "")
        if secret:
            presented = self.headers.get("x-api-key") or ""
            auth = self.headers.get("authorization") or ""
            if presented != secret and auth != f"Bearer {secret}":
                self._send(401, _err(401, "authentication_error", "invalid x-api-key")[1])
                return

        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0 or n > self.MAX_BODY:
                self._send(413, _err(413, "invalid_request_error",
                                     f"Content-Length {n} outside 0..{self.MAX_BODY}")[1])
                return
            raw = self.rfile.read(n) if n else b"{}"
            # A short read means the client declared more than it sent. Say so
            # rather than parsing a truncated body into a plausible-looking
            # request — the socket timeout above stops the hang, this stops the
            # silent misparse.
            if n and len(raw) != n:
                self._send(400, _err(400, "invalid_request_error",
                                     f"body truncated: declared {n} bytes, got {len(raw)}")[1])
                return
            payload = json.loads(raw or b"{}")
        except TimeoutError:
            self._send(408, _err(408, "invalid_request_error",
                                 "timed out reading request body")[1])
            return
        except Exception:
            self._send(400, _err(400, "invalid_request_error", "body is not valid JSON")[1])
            return

        try:
            status, body, sse = handle_messages(payload)
        except Exception as exc:                               # noqa: BLE001
            logger.exception("vendor_shim: unhandled")
            self._send(500, _err(500, "api_error", f"{type(exc).__name__}: {exc}")[1])
            return

        self._send(status, body, sse=sse and status == 200)


def serve(port: int = 8787, host: str = "127.0.0.1") -> None:
    srv = ThreadingHTTPServer((host, port), _Handler)
    logger.info("vendor_shim listening on http://%s:%d", host, port)
    logger.info("  ANTHROPIC_BASE_URL=http://%s:%d", host, port)
    logger.info("  models: nucleus/<vendor>-<model_id>, vendors=%s", sorted(VENDOR_SPECS))
    srv.serve_forever()


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="nucleus vendor-shim")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if a.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    serve(port=a.port, host=a.host)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
