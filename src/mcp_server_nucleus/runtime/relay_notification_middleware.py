"""Relay notification middleware — auto-surfaces unread relays on every tool call.

This is the client-agnostic replacement for Claude Code's SessionStart hook.
Every agent (Claude Code, agy, Devin) connects to the same MCP server. This
middleware fires on every tool call, checks the calling agent's relay inbox
for unread messages, and surfaces them via ctx.info() BEFORE the tool executes.

The agent doesn't need to call next_message or relay_subscribe. It doesn't
need SessionStart hooks. It doesn't need a .md file with instructions. The
server IS the mechanism.

How it works:
  1. Agent calls any MCP tool (e.g. nucleus_tasks, nucleus_sync)
  2. Middleware fires before the tool executes
  3. Middleware resolves the agent's inbox from posture or session role
  4. Middleware checks for unread relays
  5. If unread found: fires ctx.info() with relay summary
  6. Tool executes normally
  7. Agent sees the relay notification in its context and acts on it

Throttling: checks at most once per 10 seconds per session to avoid
spamming ctx.info() on rapid tool calls. First call always checks.
"""
import asyncio
import logging
import os
import time
from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger("nucleus.relay_middleware")

# Throttle: minimum seconds between relay checks for the same session
_CHECK_INTERVAL_SEC = 10
# Track last check time per session
_last_check: dict[str, float] = {}
# Track surfaced message IDs per session (avoid re-nagging within session)
_surfaced_ids: dict[str, set] = {}
# Track whether arm-directive has been fired for a session (first-call nudge)
_armed_sessions: set[str] = set()


class RelayNotificationMiddleware(Middleware):
    """Auto-surface unread relays on every tool call via ctx.info().

    Uses on_list_tools as the server-side SessionStart hook. Every MCP
    client calls tools/list automatically at connection time — no user
    prompt needed. This fires the arm-directive + surfaces pending relays
    before the agent even sees its first prompt. Works for CC, agy, Devin,
    and any future MCP client without client-side hooks.

    on_call_tool handles subsequent relay arrivals during the session.
    """

    async def on_list_tools(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Fire at tools/list — the server-side SessionStart hook.

        Every MCP client calls tools/list automatically at connection.
        By this point the handshake is complete and ctx.info() works.
        We fire the arm-directive + surface pending relays here, before
        the agent sees its first prompt.
        """
        try:
            ctx = context.fastmcp_context
            if ctx is not None:
                session_id = _get_session_id(context)

                # Surface pending relays at connection time
                inbox_name = _resolve_inbox(ctx)
                if inbox_name:
                    from .relay.core import relay_inbox
                    inbox = relay_inbox(unread_only=True, recipient=inbox_name, limit=5)
                    messages = inbox.get("messages", [])
                    surfaced = _surfaced_ids.setdefault(session_id, set())
                    for msg in messages:
                        msg_id = msg.get("id", "")
                        if msg_id not in surfaced:
                            subject = msg.get("subject", "")[:100]
                            sender = msg.get("from", "?")
                            body_preview = msg.get("body", "")[:300]
                            surfaced.add(msg_id)
                            await ctx.info(
                                f"[relay-pending] id={msg_id} from={sender} "
                                f"subject={subject}\n{body_preview}\n"
                                f"→ call nucleus_next_message to fetch+ack"
                            )

                    # Arm-directive: tell agent to arm the idle loop
                    await ctx.info(
                        "[arm-directive] You are connected to nucleus. "
                        "When you have no pending work, call "
                        "nucleus_next_message() to wait for new tasks. "
                        "When a task arrives, execute it, mark DONE via "
                        "nucleus_tasks, and re-arm by calling "
                        "nucleus_next_message() again. This is your idle "
                        "loop — do not sit at a prompt waiting."
                    )
                    _armed_sessions.add(session_id)
        except Exception as exc:
            logger.debug("on_list_tools middleware error (non-fatal): %s", exc)

        return await call_next(context)

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        try:
            ctx = context.fastmcp_context
            if ctx is None:
                return await call_next(context)

            session_id = _get_session_id(context)

            # Throttle: don't check more than once per _CHECK_INTERVAL_SEC
            now = time.monotonic()
            last = _last_check.get(session_id, 0)
            if now - last < _CHECK_INTERVAL_SEC:
                return await call_next(context)
            _last_check[session_id] = now

            # Resolve the agent's inbox
            inbox_name = _resolve_inbox(ctx)
            if not inbox_name:
                return await call_next(context)

            # Check for unread relays
            from .relay.core import relay_inbox
            inbox = relay_inbox(unread_only=True, recipient=inbox_name, limit=5)
            messages = inbox.get("messages", [])
            if not messages:
                return await call_next(context)

            # Surface each unread relay via ctx.info().
            # Include message_id so the agent can ack via relay_ack or
            # fetch full body via next_message. Track surfaced IDs per
            # session so we don't re-nag within the session.
            session_key = session_id
            surfaced = _surfaced_ids.setdefault(session_key, set())
            new_messages = [m for m in messages if m.get("id") not in surfaced]
            if not new_messages:
                return await call_next(context)

            for msg in new_messages:
                msg_id = msg.get("id", "")
                subject = msg.get("subject", "")[:100]
                sender = msg.get("from", "?")
                priority = msg.get("priority", "normal")
                body_preview = msg.get("body", "")[:300]
                surfaced.add(msg_id)
                await ctx.info(
                    f"[relay-arrival] id={msg_id} from={sender} priority={priority} "
                    f"subject={subject}\n{body_preview}\n"
                    f"→ call nucleus_next_message to fetch+ack, or "
                    f"nucleus_sync(action=\"relay_ack\", params={{\"message_id\": \"{msg_id}\"}})"
                )
        except Exception as exc:
            logger.debug("relay notification middleware error (non-fatal): %s", exc)

        return await call_next(context)


def _get_session_id(context: MiddlewareContext[Any]) -> str:
    """Extract a session identifier from the context."""
    try:
        ctx = context.fastmcp_context
        if ctx and hasattr(ctx, "session_id") and ctx.session_id:
            return str(ctx.session_id)
    except Exception:
        pass
    return "default"


def _resolve_inbox(ctx: Any) -> str | None:
    """Resolve the calling agent's inbox name from posture or session role."""
    # Try posture first
    try:
        from .posture import get_current_posture
        from .relay_inbox_canonical import resolve_canonical_inbox_name
        posture = get_current_posture()
        if posture.get("status") == "active":
            agent_id = posture.get("agent_id", "")
            if agent_id:
                return resolve_canonical_inbox_name(agent_id)
    except Exception:
        pass

    # Fall back to session role detection
    try:
        role = os.environ.get("CC_SESSION_ROLE", "").strip()
        if not role:
            role = os.environ.get("NUCLEUS_SESSION_ROLE", "").strip()
        if role:
            # Map role to canonical inbox
            role_map = {
                "main": "claude_code_main",
                "peer": "claude_code_peer",
                "agy": "antigravity",
                "antigravity": "antigravity",
                "op_assistant": "claude_code_operator_assistant",
                "op-assistant": "claude_code_operator_assistant",
            }
            return role_map.get(role, f"claude_code_{role}")
    except Exception:
        pass

    return None
