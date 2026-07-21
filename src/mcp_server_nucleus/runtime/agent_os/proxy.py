#!/usr/bin/env python3
"""Nucleus Inference Proxy — one endpoint, the membrane picks the provider.

Exposes an OpenAI-compatible ``/v1/chat/completions`` endpoint that routes
through the Nucleus cognition scheduler (MEMBRANE §1). Your agents hit one
URL; the proxy picks the cheapest capable provider and falls through on failure.

Usage:
    python -m mcp_server_nucleus.runtime.agent_os.proxy [--port 8421]

Then point any OpenAI-compatible client at:
    OPENAI_BASE_URL=http://localhost:8421/v1
    OPENAI_API_KEY=anything  # proxy ignores the key; uses your configured providers

The proxy reads your provider credentials from the same env vars / token files
the scheduler uses — no separate config needed.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nucleus.agent_os.proxy")

# Provider priority — same as scheduler.py CAP_ANY
_PROVIDER_ORDER = ["antigravity", "groq", "gemini", "claude_oauth", "anthropic"]


def _try_providers(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int,
    capability: str,
) -> tuple[Optional[str], str, str]:
    """Try providers in priority order. Returns (text, engine, provider_id)."""
    import os
    from pathlib import Path

    from ..llm_client import get_llm_client

    skip = set()
    for provider in _PROVIDER_ORDER:
        if provider in skip:
            continue

        # Check credentials
        if provider == "antigravity":
            if not (Path.home() / ".tb" / "oauth_antigravity.json").exists():
                continue
        elif provider == "groq":
            if not os.environ.get("NUCLEUS_GROQ_API_KEY"):
                continue
        elif provider == "gemini":
            if not os.environ.get("GEMINI_API_KEY"):
                continue
        elif provider == "claude_oauth":
            if not (Path.home() / ".tb" / "oauth_bespoq_cowork.json").exists():
                continue
        elif provider == "anthropic":
            if not os.environ.get("NUCLEUS_ANTHROPIC_API_KEY"):
                continue

        try:
            # Build system instruction from messages
            sys_msgs = [m["content"] for m in messages if m["role"] == "system"]
            user_msgs = [m["content"] for m in messages if m["role"] == "user"]
            system_instruction = "\n".join(sys_msgs) if sys_msgs else None
            prompt = "\n".join(user_msgs) if user_msgs else ""

            client = get_llm_client(
                provider=provider,
                system_instruction=system_instruction,
            )
            resp = client.generate_content(prompt)
            text = getattr(resp, "text", "") or ""
            engine = getattr(resp, "engine", provider) or provider
            if text:
                return text, engine, provider
            skip.add(provider)
        except Exception as exc:
            logger.info("proxy: provider=%s failed: %s", provider, exc)
            skip.add(provider)
            continue

    return None, "NONE", "none"


class ProxyHandler(BaseHTTPRequestHandler):
    """OpenAI-compatible /v1/chat/completions handler."""

    def _send_json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if "x-nucleus-provider" in body:
            self.send_header("x-nucleus-provider", str(body["x-nucleus-provider"]))
        if "x-nucleus-engine" in body:
            self.send_header("x-nucleus-engine", str(body["x-nucleus-engine"]))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/v1/models":
            # List available providers as "models"
            models = [
                {"id": "nucleus-auto", "object": "model", "owned_by": "nucleus"},
                {"id": "nucleus-cheap", "object": "model", "owned_by": "nucleus"},
                {"id": "nucleus-reasoning", "object": "model", "owned_by": "nucleus"},
            ]
            self._send_json(200, {"object": "list", "data": models})
        elif self.path == "/health":
            self._send_json(200, {"status": "ok"})
        elif self.path == "/v1/providers":
            # Show provider credential status
            from .scheduler import _provider_available, _priority_order
            status = []
            for provider in _priority_order("any"):
                status.append({
                    "provider": provider,
                    "available": _provider_available(provider),
                })
            self._send_json(200, {"providers": status})
        else:
            self._send_json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "not found"}})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw)
        except Exception as exc:
            self._send_json(400, {"error": {"message": f"invalid JSON: {exc}"}})
            return

        messages = body.get("messages", [])
        model = body.get("model", "nucleus-auto")
        max_tokens = body.get("max_tokens", 4096)
        stream = body.get("stream", False)

        # Map model name to capability hint
        capability = "any"
        if model in ("nucleus-cheap", "cheap"):
            capability = "cheap"
        elif model in ("nucleus-reasoning", "reasoning"):
            capability = "reasoning"

        # Route through the scheduler
        text, engine, provider = _try_providers(messages, model, max_tokens, capability)

        if text is None:
            self._send_json(503, {
                "error": {
                    "message": "all providers unavailable",
                    "type": "provider_error",
                }
            })
            return

        # Return OpenAI-compatible response
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        timestamp = int(time.time())

        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": timestamp,
            "model": f"{provider}/{engine}",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
                "completion_tokens": len(text.split()),
                "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + len(text.split()),
            },
            "x-nucleus-provider": provider,
            "x-nucleus-engine": engine,
        }
        self._send_json(200, response)

    def log_message(self, fmt, *args):
        # Suppress default logging; use our own
        pass


def main():
    parser = argparse.ArgumentParser(description="Nucleus Inference Proxy")
    parser.add_argument("--port", type=int, default=8421, help="port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="host to bind")
    parser.add_argument(
        "--status",
        action="store_true",
        default=False,
        help="Print provider credential status and exit (no server started).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.status:
        from .scheduler import _provider_available, _priority_order
        print("# Nucleus Inference Proxy — provider status")
        print(f"{'provider':<20s} {'available':<12s}")
        print("-" * 32)
        for provider in _priority_order("any"):
            avail = _provider_available(provider)
            print(f"{provider:<20s} {'✓ yes' if avail else '✗ no':<12s}")
        return

    server = HTTPServer((args.host, args.port), ProxyHandler)
    logger.info("Nucleus Inference Proxy on http://%s:%d/v1", args.host, args.port)
    logger.info("Providers: %s", " → ".join(_PROVIDER_ORDER))
    logger.info("Set OPENAI_BASE_URL=http://%s:%d/v1 for your agents", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
