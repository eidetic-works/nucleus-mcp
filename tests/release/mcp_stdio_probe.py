#!/usr/bin/env python3
"""Boot an MCP stdio server and drive a real initialize + tools/list + tool call.

This is the runtime half of the release smoke gate (ADR-0043 W2). The 1.8.8
wheel *listed* 12 tools over a clean JSON-RPC handshake but every ``tools/call``
returned ``-32603 No module named ...`` — a "listed but dead" server. A handshake
that stops at ``tools/list`` would have shipped it. So this probe insists on one
successful ``tools/call`` result, not just a tool listing.

Transport: MCP stdio is newline-delimited JSON-RPC on stdin/stdout; server logs
and banners go to stderr and are ignored here. A background reader thread parses
each stdout line into a queue so interleaved/late lines never wedge the client.

Usage:
    python mcp_stdio_probe.py [--] <server-cmd> [args...]
    python mcp_stdio_probe.py                      # defaults to: nucleus-mcp

Exit code 0 iff initialize, tools/list, and one real tools/call all succeed.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time

PROTOCOL_VERSION = "2025-06-18"
# Read-only, side-effect-free tool call: returns version/platform info.
TOOL_NAME = "nucleus_engrams"
TOOL_ARGS = {"action": "version"}


def _log(msg: str) -> None:
    print(f"[mcp-probe] {msg}", flush=True)


def _reader(stream, q: "queue.Queue") -> None:
    for line in iter(stream.readline, ""):
        line = line.strip()
        if not line:
            continue
        try:
            q.put(json.loads(line))
        except json.JSONDecodeError:
            # Non-JSON noise on stdout (shouldn't happen, but ignore it).
            continue
    q.put(None)  # EOF sentinel


class ProbeError(RuntimeError):
    pass


def _await_response(q: "queue.Queue", want_id: int, what: str, timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            msg = q.get(timeout=deadline - time.time())
        except queue.Empty:
            break
        if msg is None:
            raise ProbeError(f"server closed stdout before responding to {what}")
        if isinstance(msg, dict) and msg.get("id") == want_id:
            return msg
        # Ignore notifications / unrelated ids.
    raise ProbeError(f"timed out after {timeout:.0f}s waiting for {what} response")


def run_probe(server_cmd: list[str], env: dict | None = None) -> int:
    _log(f"boot: {' '.join(server_cmd)}")
    proc = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
        bufsize=1,
    )
    q: "queue.Queue" = queue.Queue()
    t = threading.Thread(target=_reader, args=(proc.stdout, q), daemon=True)
    t.start()

    def send(obj: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    try:
        # 1) initialize
        send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "release-smoke", "version": "1"},
            },
        })
        init = _await_response(q, 1, "initialize")
        if "result" not in init:
            raise ProbeError(f"initialize returned an error: {init.get('error')}")
        server_info = init["result"].get("serverInfo", {})
        _log(f"initialize OK — serverInfo={server_info.get('name')} v{server_info.get('version')}")

        # 2) initialized notification
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 3) tools/list
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = _await_response(q, 2, "tools/list")
        if "result" not in listed:
            raise ProbeError(f"tools/list returned an error: {listed.get('error')}")
        tools = listed["result"].get("tools", [])
        names = [t.get("name") for t in tools]
        if not tools:
            raise ProbeError("tools/list returned an empty tool set")
        _log(f"tools/list OK — {len(tools)} tools")
        if TOOL_NAME not in names:
            raise ProbeError(f"expected tool {TOOL_NAME!r} not in listing: {names[:20]}")

        # 4) one REAL tool call — must return a non-error result (guards against
        #    the 1.8.8 'listed but every call is -32603' failure mode).
        send({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": TOOL_NAME, "arguments": TOOL_ARGS},
        })
        called = _await_response(q, 3, f"tools/call {TOOL_NAME}")
        if "error" in called:
            raise ProbeError(
                f"tools/call {TOOL_NAME}({TOOL_ARGS}) returned JSON-RPC error: "
                f"{called['error']}"
            )
        result = called.get("result", {})
        if result.get("isError"):
            raise ProbeError(
                f"tools/call {TOOL_NAME} returned isError=true: "
                f"{json.dumps(result)[:300]}"
            )
        content = result.get("content") or []
        text = ""
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                break
        if not text.strip():
            raise ProbeError(f"tools/call {TOOL_NAME} returned no text content: {result}")
        first = text.strip().splitlines()[0][:80]
        _log(f"tools/call OK — {TOOL_NAME}({TOOL_ARGS}) -> {first!r}")
        _log("PASS: initialize + tools/list + real tools/call all succeeded")
        return 0
    except ProbeError as exc:
        _log(f"FAIL: {exc}")
        return 1
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] == "--":
        args = args[1:]
    server_cmd = args if args else ["nucleus-mcp"]
    return run_probe(server_cmd, env=os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
