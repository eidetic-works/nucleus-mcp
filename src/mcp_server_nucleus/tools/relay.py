"""Relay-substrate MCP facade — wraps runtime/relay_transport.py.

Per ADR-0036 amendment c068abc1 (v0.2 wake-primitive item #7 promoted to
LEAD ENABLER): exposes relay-substrate ops as native MCP tools so woken
sessions don't need to fashion curl-with-bearer commands in their prompt.
The tool is the audited surface; bearer is read from per-role file or
NUCLEUS_RELAY_BEARER env at relay_transport call-time (PR #488 / PR #493
contract), never from the model prompt — eliminating the Opus 4.8 Max
curl-refusal pattern.

v0.2.1 Layer A (per-role bearer, .brain/specs/v021_per_role_bearer_and_
registry_binding.md): bearer follows role per-call via _resolve_bearer.
Reads ~/.tb/relay_token_<role> first; falls through to NUCLEUS_RELAY_BEARER
env for v0.2.0 single-role compat. Shared MCP subprocess across Chat /
Cowork / Dispatch tabs can now identity-switch per call.

Actions (action="<name>", params={...}):
  post    - relay_transport.post_relay(payload). params: {to, subject, body,
            sender?, priority?, in_reply_to?, context?, id?, from_session_id?}
            sender auto-fills from role (param > CC_SESSION_ROLE > 'main')
            when omitted — Task #62. Server still enforces sender ==
            token_owner (403 sender_mismatch), so the default is
            authenticated, not heuristic.
  inbox   - relay_transport.read_inbox(role, unread_only?, limit?).
            role auto-fills from CC_SESSION_ROLE env (mirrors board's
            from_role auto-fill). params can override.
  ack     - relay_transport.mark_seen(role, message_ids). role auto-fills.
  status  - DIAGNOSTIC. Returns {is_http_mode, relay_url_set, bearer_set,
            canonical_role}. Does NOT call server. Useful for tool-init
            verification + fleet-wide remote-debug.

Pattern mirrors tools/board.py (single facade + ROUTER + json.dumps).
"""

import json
import os
from pathlib import Path

from ._dispatch import async_dispatch


class RelayConfigError(RuntimeError):
    """Raised when no bearer can be resolved for a role.

    Per v0.2.1 Layer A spec § 'Failure modes': surfaces actionable message
    naming both the expected per-role file path AND the env-var fallback.
    Subclass of RuntimeError so existing handlers catching RuntimeError
    (from runtime/relay_transport._bearer_or_raise) keep working.
    """


def register(mcp, helpers):
    """Register the nucleus_relay facade tool with the MCP server."""
    from ..runtime import relay_transport
    from ..runtime.relay_inbox_canonical import resolve_canonical_inbox_name

    def _resolve_role(role=None):
        """Resolve role string. Explicit param > CC_SESSION_ROLE env > 'main'."""
        if role:
            return str(role).strip().lower()
        env_role = os.environ.get("CC_SESSION_ROLE", "").strip().lower()
        return env_role or "main"

    def _resolve_bearer(role):
        """Resolve bearer for ``role``. Per-role file > env > RelayConfigError.

        Per v0.2.1 Layer A spec § 'Internal flow':
          1. Read ~/.tb/relay_token_<role> (strip whitespace). Non-empty wins.
          2. Empty file or missing path → fall through to NUCLEUS_RELAY_BEARER
             env (v0.2.0 single-role compat path).
          3. Neither → raise RelayConfigError citing both expected paths.

        Returned bearer is passed via the kwarg into relay_transport functions.
        Never logged, never echoed in error messages.

        Note: status action does NOT call this helper — it's diagnostic-only
        and intentionally never raises on missing bearer (mirrors PR #494
        anti-leak Crack 1 discipline).
        """
        role_token_path = Path.home() / ".tb" / f"relay_token_{role}"
        try:
            # SEC-002 fix: open directly without exists() check to close TOCTOU
            # race (symlink swap between exists() and read_text()). Using open()
            # with a single syscall avoids the race window.
            with open(role_token_path, "r", encoding="utf-8") as f:
                contents = f.read().strip()
            if contents:
                return contents
        except (OSError, FileNotFoundError):
            # Permission rejected / not-readable / missing → fall through to env
            # per spec failure-modes table line 79.
            pass
        env_bearer = os.environ.get("NUCLEUS_RELAY_BEARER", "").strip()
        if env_bearer:
            return env_bearer
        raise RelayConfigError(
            f"No bearer for role={role!r}. Expected per-role file at "
            f"~/.tb/relay_token_{role} (mode 600) or NUCLEUS_RELAY_BEARER env."
        )

    def _post(
        to=None,
        subject="",
        body=None,
        sender=None,
        priority="normal",
        in_reply_to=None,
        context=None,
        id=None,
        from_session_id=None,
        role=None,
        recipient=None,
    ):
        # Alias: "recipient" — natural-language synonym for "to".
        # Added for ChatGPT App Catalog reviewer ergonomics (test cases use "recipient").
        if to is None and recipient is not None:
            to = recipient
        if not to:
            return json.dumps(
                {"sent": False, "error": "missing_to_field"}, indent=2
            )
        sender_role = _resolve_role(role)
        payload = {
            "to": to,
            "subject": subject,
            "body": body if body is not None else {},
            "priority": priority,
            # Task #62 sender auto-fill: default to the SAME role string that
            # selects the bearer below. Unlike the R6.1-banned
            # detect_session_type() heuristic, this is authenticated-default
            # attribution — the HTTP server enforces sender == token_owner
            # (403 sender_mismatch), so a wrong default fails loud instead of
            # silently mis-attributing across surfaces.
            "sender": sender or sender_role,
        }
        if in_reply_to:
            payload["in_reply_to"] = in_reply_to
        if context is not None:
            payload["context"] = context
        if id:
            payload["id"] = id
        if from_session_id:
            payload["from_session_id"] = from_session_id
        bearer = _resolve_bearer(sender_role)
        result = relay_transport.post_relay(payload, bearer=bearer)
        return json.dumps(result, indent=2, default=str)

    def _inbox(role=None, unread_only=True, limit=50):
        canonical_role = _resolve_role(role)
        bearer = _resolve_bearer(canonical_role)
        result = relay_transport.read_inbox(
            canonical_role,
            unread_only=bool(unread_only),
            limit=int(limit),
            bearer=bearer,
        )
        # InboxResult truth-in-signaling flags (PR #540) surfaced so MCP
        # clients can tell "inbox empty" from "transport failed / page
        # truncated / budget exhausted". getattr defaults keep this safe
        # if a plain list ever comes back.
        return json.dumps(
            {
                "messages": result,
                "role": canonical_role,
                "has_more": bool(getattr(result, "has_more", False)),
                "rate_limited": bool(getattr(result, "rate_limited", False)),
                "transport_error": bool(getattr(result, "transport_error", False)),
            },
            indent=2,
            default=str,
        )

    def _ack(message_ids=None, role=None):
        canonical_role = _resolve_role(role)
        bearer = _resolve_bearer(canonical_role)
        ids = list(message_ids) if message_ids else []
        result = relay_transport.mark_seen(canonical_role, ids, bearer=bearer)
        return json.dumps(result, indent=2, default=str)

    def _status(role=None):
        canonical_role = _resolve_role(role)
        url = os.environ.get("NUCLEUS_RELAY_URL", "").strip()
        bearer = os.environ.get("NUCLEUS_RELAY_BEARER", "").strip()
        out = {
            "is_http_mode": relay_transport.is_http_mode(),
            "relay_url_set": bool(url),
            "bearer_set": bool(bearer),
            "canonical_role": canonical_role,
            "resolved_inbox_dir": resolve_canonical_inbox_name(canonical_role) or canonical_role,
        }
        return json.dumps(out, indent=2, default=str)

    ROUTER = {
        "post": lambda to=None, subject="", body=None, sender=None, priority="normal", in_reply_to=None, context=None, id=None, from_session_id=None, role=None, recipient=None: _post(
            to, subject, body, sender, priority, in_reply_to, context, id, from_session_id, role, recipient
        ),
        "inbox": lambda role=None, unread_only=True, limit=50: _inbox(role, unread_only, limit),
        "ack": lambda message_ids=None, role=None: _ack(message_ids, role),
        "status": lambda role=None: _status(role),
    }

    @mcp.tool(title="Relay Messaging", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})
    async def nucleus_relay(action: str, params: dict = None) -> str:
        """Relay-substrate facade — post / read / ack / status.

Actions:
  post    - Send a relay envelope. params: {to, subject, body, sender?,
            priority?, in_reply_to?, context?, id?, from_session_id?}
            sender? auto-fills from your session role when omitted.
            to accepts short role aliases: main, peer, tb, ops, agy, board.
            "recipient" is accepted as an alias for "to".
            Returns {sent: bool, id: str (server message_id), error?: str}.
  inbox   - List inbox messages. params: {role?, unread_only?, limit?}
            role auto-fills from CC_SESSION_ROLE env.
            Returns {messages: [...], role: str}.
  ack     - Mark messages seen. params: {message_ids: [str], role?}
            Returns {acked: int, failed: int}.
  status  - Diagnostic (no server call). params: {role?}
            Returns {is_http_mode, relay_url_set, bearer_set, canonical_role,
            resolved_inbox_dir}.

Bearer resolves per-role at call-time (~/.tb/relay_token_<role>, falling back
to NUCLEUS_RELAY_BEARER env) — never passed via this tool's prompt surface.
Per ADR-0036 amendment c068abc1 + v0.2.1 Layer A.
"""
        params = params or {}
        return await async_dispatch(action, params, ROUTER, "nucleus_relay")

    return [("nucleus_relay", nucleus_relay)]
