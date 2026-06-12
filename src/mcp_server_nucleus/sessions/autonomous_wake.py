"""v0.3.0 Layer 5 — Autonomous wake via full inference replay.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 5
(spec lines 147-156) + op-assistant 2026-06-09T03:50Z Layer 3 NULL
VERDICT (no undocumented /run primitive exists for operator's account
— 30+ endpoint variants probed, all 404) + op-assistant 2026-06-09T09:15Z
architectural amendment (build INTO nucleus).

Per op-assistant 2026-06-09T03:50Z + 09:35Z directives: Layer 5 is the
**load-bearing** piece for autonomous fleet node behavior. Layer 1
PUT+presence alone do not wake; Layer 3 yielded NULL; Layer 5 (full
POST /v1/messages?beta=true inference replay) is the only path that
actually fires the agent autonomously.

What this module does:
  1. Triggered by relay_inbox_hook when a relay arrives at a registered
     autonomous-role inbox.
  2. Fetches OAuth bearer via Layer 0 (nucleus.oauth.exchange).
  3. Composes a /v1/messages payload by harvesting context via Layer 2
     discovery (nucleus.org.discovery): system_prompt + tools + MCP
     servers + memory + recent conversation history.
  4. Appends the new user-turn — the wake instruction crafted from the
     relay subject + body.
  5. POSTs to api.anthropic.com/v1/messages?beta=true with Bearer auth.
  6. Parses response, detects tool-use blocks (e.g., nucleus_relay
     calls) so callers can forward results back to fleet inboxes.

This is intentionally NOT a streaming implementation in v1 — non-stream
POST + parse keeps the module tractable. Streaming + tool-call routing
can land in v0.3.x extension if the empirical wake works.

Pseudonymity carryover (same discipline as Layers 0/1/2):
- OAuth bearer never logged at any level
- session_id + org_uuid truncated [:12] in logs (PR #499 _LOG_ID_MAX
  convention)
- Wake-instruction body MAY contain user content — never log message
  contents at any level (only counts + status)
- All HTTP via curl_cffi chrome120 impersonation

Host: api.anthropic.com (Bearer host per op-assistant Q4 host-split
empirical). claude.ai is NOT used here — inference is server-side.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from curl_cffi import requests as _curl_requests
except ImportError:  # pragma: no cover - tests stub via patch
    _curl_requests = None  # type: ignore[assignment]


logger = logging.getLogger("nucleus.autonomous_wake")

_API_ANTHROPIC = "https://api.anthropic.com"
_MESSAGES_URL = f"{_API_ANTHROPIC}/v1/messages?beta=true"
_ANTHROPIC_VERSION = "2023-06-01"  # per Layer 1 captured headers
_IMPERSONATE = "chrome120"  # consistent with Layers 0/1/2
_HTTP_TIMEOUT_S = 120.0  # inference can take longer than discovery
_LOG_ID_MAX = 12  # PR #499 pseudonymity convention

# Default model floor when caller doesn't specify — leave caller free to
# override per role. Anthropic accepts model strings directly in body.
_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 4096


class AutonomousWakeError(RuntimeError):
    """Raised when an autonomous wake call fails terminally."""


class WakeAuthError(AutonomousWakeError):
    """Inference POST rejected with HTTP 401 (stale/revoked bearer)."""


# Plan B per op-assistant 2026-06-09T17:50Z PRE-WIRE + cc-peer 18:00Z
# locked-contract verdict: substrate-owned `nucleus_relay` tool injected
# into every autonomous-wake payload regardless of the role's MCP server
# config. bespoq's Claude.app session may not have the nucleus MCP server
# registered → without this injection, the LLM has no way to forward an
# ACK / response back to the fleet.
#
# Name: `nucleus_relay` (cc-peer Q1 verdict — substrate-naming consistency
# with existing MCP tool surface used by cc-agents; dedup-by-name correctly
# skips duplicate if bespoq's session ever adds nucleus MCP).
#
# Recipient: ENUM-constrained to canonical-role aliases (cc-peer Q2 +
# Q4(a) reinforcement). Resolved via runtime.relay_inbox_canonical.
#
# 6 LLM-agency mitigations enforced by the receiver helper
# (sessions._relay_post_helper) per cc-peer Q4 locked contract:
#   (a) recipient enum (here)
#   (b) [AUTONOMOUS] subject prefix (forced at helper)
#   (c) sender-role LOCKED at helper call site (LLM cannot impersonate)
#   (d) body length cap 4096 chars (helper truncates)
#   (e) rate limit 20/hr per role disk-persistent (helper)
#   (f) audit log .brain/ledger/autonomous_relay_posts.jsonl (helper)

# Recipient enum derived from runtime.relay_inbox_canonical SSOT — the
# alias keys LLM would naturally emit. cc-peer locked contract: ENUM
# resists typos + makes validation deterministic.
_NUCLEUS_RELAY_RECIPIENT_ENUM: List[str] = [
    "main",
    "peer",
    "tb",
    "operator_assistant",
    "antigravity",
    "antigravity_gq",
    "antigravity_voice",
    "cc_gq",
    "gq",
    "ultraplan",
    "windsurf",
    "board",
]


NUCLEUS_RELAY_TOOL: Dict[str, Any] = {
    "name": "nucleus_relay",
    "description": (
        "Post a relay to another role inbox via the Nucleus substrate. "
        "Use this to send ACK / response / forwarded-data back to the "
        "fleet. Subject is automatically prefixed with [AUTONOMOUS] by "
        "the substrate. Body is capped at 4096 chars. Rate limit 20/hr."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "enum": list(_NUCLEUS_RELAY_RECIPIENT_ENUM),
                "description": (
                    "Canonical role alias the relay is sent TO. Must "
                    "match one of the enum values. Resolved to the "
                    "canonical inbox dir by the substrate."
                ),
            },
            "subject": {
                "type": "string",
                "description": (
                    "Subject line. Substrate prepends '[AUTONOMOUS]' "
                    "if not already present."
                ),
            },
            "body": {
                "type": "string",
                "description": (
                    "Free-form body content. Use a JSON-string if "
                    "structured data is needed. Capped at 4096 chars."
                ),
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "description": "Priority level. Defaults to 'normal'.",
            },
        },
        "required": ["recipient", "subject", "body"],
    },
}


def _truncate_id(value: str) -> str:
    return value[:_LOG_ID_MAX] if value else ""


def _get_session_events(
    session_id: str,
    *,
    bearer: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """GET /v1/sessions/<id>/events?limit=N — recent conversation history.

    Per spec line 152. Returns parsed list of event dicts (most recent
    last per Anthropic convention). Used to seed the messages history
    so the wake inference has continuity context.

    History fetch is optional — caller can pass limit=0 to skip. On
    transport/network failure, returns []  rather than raising; the
    wake itself should not abort due to history-fetch hiccup.
    """
    if limit <= 0:
        return []
    if not session_id or not bearer:
        return []
    if _curl_requests is None:
        return []
    url = f"{_API_ANTHROPIC}/v1/sessions/{session_id}/events?limit={int(limit)}"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Accept": "application/json",
    }
    try:
        resp = _curl_requests.get(
            url, headers=headers,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning(
            "autonomous_wake: history transport class=%s cse=%s",
            type(exc).__name__, _truncate_id(session_id),
        )
        return []
    if not (200 <= resp.status_code < 300):
        logger.warning(
            "autonomous_wake: history GET non-2xx status=%d cse=%s",
            resp.status_code, _truncate_id(session_id),
        )
        return []
    try:
        parsed = resp.json()
    except Exception:
        return []
    if isinstance(parsed, dict):
        return list(parsed.get("events") or parsed.get("data") or [])
    if isinstance(parsed, list):
        return parsed
    return []


def compose_wake_payload(
    *,
    wake_instruction: str,
    system_prompt: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
    mcp_servers: Optional[List[Dict[str, Any]]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    model: str = _DEFAULT_MODEL,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> Dict[str, Any]:
    """Build /v1/messages payload from discovered context + wake instruction.

    `wake_instruction` is the user-turn content (typically derived from
    the relay subject + body). Callers harvest `system_prompt`, `tools`,
    `mcp_servers` from Layer 2 discovery + bespoq_context (via
    discovery_context.build_discovery_context) and `history` from
    _get_session_events.

    LOOP-CLOSE FIX per op-assistant 2026-06-09T16:00Z empirical
    breakthrough: Anthropic /v1/messages?beta=true REJECTS `mcp_servers`
    as a top-level API field with HTTP 400 "Extra inputs are not
    permitted." This function FLATTENS each MCP server's tools list
    into the standard /v1/messages `tools[]` array (Anthropic's
    standard tool_use shape). bespoq's 55+ MCP tools become 55+
    tools[] entries; LLM treats them as native tools + emits
    tool_use blocks → response posts back to fleet.

    Translation per op-assistant inline-test verification:
      for server in mcp_servers:
        for t in server.get('tools', []):
          tools_out.append({
              'name': t['name'],
              'description': t.get('description', ''),
              'input_schema': t.get('input_schema')
                              or {'type': 'object', 'properties': {}},
          })

    Returns a dict ready to JSON-serialize as the POST body.
    """
    if not wake_instruction:
        raise AutonomousWakeError("wake_instruction required")

    messages: List[Dict[str, Any]] = []
    for ev in history or []:
        role = ev.get("role")
        content = ev.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": wake_instruction})

    payload: Dict[str, Any] = {
        "model": model,
        "max_tokens": int(max_tokens),
        "messages": messages,
    }
    if system_prompt:
        payload["system"] = system_prompt

    # Build combined tools[] from caller-supplied tools + flattened
    # MCP server tools. LOOP-CLOSE: NEVER pass mcp_servers as a
    # top-level API field (Anthropic 400).
    combined_tools: List[Dict[str, Any]] = []
    if tools:
        combined_tools.extend(list(tools))
    if mcp_servers:
        combined_tools.extend(_flatten_mcp_tools(mcp_servers))

    # Plan B per op-assistant 17:50Z + cc-peer 18:00Z locked contract:
    # dedup-append nucleus_relay tool. Skip if any existing tool is
    # already named nucleus_relay (bespoq's session may someday add
    # nucleus MCP server providing the same tool; in that case the
    # existing entry wins). cc-peer Q1 dedup-by-name keying.
    if not any(
        isinstance(t, dict) and t.get("name") == "nucleus_relay"
        for t in combined_tools
    ):
        combined_tools.append(dict(NUCLEUS_RELAY_TOOL))

    if combined_tools:
        payload["tools"] = combined_tools

    return payload


def _flatten_mcp_tools(
    mcp_servers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Translate MCP servers' nested tool definitions to Anthropic
    /v1/messages tools[] entries.

    Per op-assistant 2026-06-09T16:00Z empirical-verified translation:
    each MCP server has a `tools` list; flatten into standard
    {name, description, input_schema} entries.

    Defensive against malformed entries (non-dict servers, non-dict
    tools, missing name) — skipped with no log spam.
    """
    out: List[Dict[str, Any]] = []
    for server in mcp_servers or []:
        if not isinstance(server, dict):
            continue
        tools_list = server.get("tools")
        if not isinstance(tools_list, list):
            continue
        for t in tools_list:
            if not isinstance(t, dict):
                continue
            name = t.get("name")
            if not isinstance(name, str) or not name:
                continue
            entry: Dict[str, Any] = {
                "name": name,
                "description": t.get("description", "") or "",
            }
            schema = t.get("input_schema")
            if isinstance(schema, dict):
                entry["input_schema"] = schema
            else:
                entry["input_schema"] = {"type": "object", "properties": {}}
            out.append(entry)
    return out


def post_inference(
    payload: Dict[str, Any],
    *,
    bearer: str,
    session_id: str = "",
) -> Dict[str, Any]:
    """POST /v1/messages?beta=true with Bearer auth. Returns parsed body.

    `session_id` is purely for log correlation (truncated per
    _LOG_ID_MAX). Raises AutonomousWakeError on non-2xx or transport
    failure. Pseudonymity: bearer + payload body content NEVER logged.
    """
    if not bearer:
        raise AutonomousWakeError("bearer required")
    if not payload or not payload.get("messages"):
        raise AutonomousWakeError("payload.messages required")
    if _curl_requests is None:
        raise AutonomousWakeError("curl_cffi not installed")

    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = _curl_requests.post(
            _MESSAGES_URL, headers=headers, json=payload,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning(
            "autonomous_wake: inference transport class=%s cse=%s",
            type(exc).__name__, _truncate_id(session_id),
        )
        raise AutonomousWakeError(
            f"transport error: {type(exc).__name__}"
        ) from exc

    if not (200 <= resp.status_code < 300):
        logger.warning(
            "autonomous_wake: inference rejected status=%d cse=%s",
            resp.status_code, _truncate_id(session_id),
        )
        if resp.status_code == 401:
            raise WakeAuthError("inference rejected status=401")
        raise AutonomousWakeError(
            f"inference rejected status={resp.status_code}"
        )

    parsed = resp.json()
    msg_count = len(payload.get("messages", []))
    content_blocks = parsed.get("content") or []
    logger.info(
        "autonomous_wake: inference ok cse=%s msgs=%d blocks=%d stop=%s",
        _truncate_id(session_id),
        msg_count,
        len(content_blocks) if isinstance(content_blocks, list) else 0,
        parsed.get("stop_reason", "?"),
    )
    return parsed


def _refreshed_bearer(role: str) -> Optional[str]:
    """Force-refresh the OAuth access token for ``role``; None on any failure.

    Lazy import keeps the module importable without oauth deps. Broad
    except is deliberate — refresh is best-effort; on failure the caller
    propagates the original 401 instead of raising a new error.
    Pseudonymity: exception class only, never the message (may embed
    paths or token fragments).
    """
    try:
        from mcp_server_nucleus.oauth import exchange as _oauth_exchange

        return _oauth_exchange.get_access_token(role, force_refresh=True)
    except Exception as exc:
        logger.warning(
            "autonomous_wake: bearer refresh failed role=%s class=%s",
            role, type(exc).__name__,
        )
        return None


def extract_tool_use_blocks(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool_use content blocks from /v1/messages response.

    Anthropic returns content as a list of blocks; tool_use blocks have
    type=='tool_use' + name + input. Callers (e.g., relay forwarders)
    iterate these to fire follow-up relays.
    """
    blocks = response.get("content") or []
    if not isinstance(blocks, list):
        return []
    return [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]


def autonomous_wake_from_relay(
    *,
    role: str,
    session_id: str,
    relay_subject: str,
    relay_body: str,
    bearer: str,
    org_uuid: str = "",
    history_limit: int = 50,
    discovery_context: Optional[Dict[str, Any]] = None,
    model: str = _DEFAULT_MODEL,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> Dict[str, Any]:
    """Top-level orchestrator: relay arrival → autonomous inference fire.

    Called by relay_inbox_hook when a relay lands at a registered
    autonomous-role inbox (per integration pattern step 3).

    discovery_context (optional) is a dict pre-populated by caller from
    Layer 2 endpoints — typically {system_prompt, tools, mcp_servers}.
    If absent, payload composes with empty defaults (caller can patch
    later).

    Returns dict:
      {
        ok: bool,
        response: <parsed /v1/messages body>,
        tool_use_blocks: [<extracted tool_use blocks>],
        wake_instruction: <the user-turn text fired>,
      }

    Raises AutonomousWakeError on terminal failure.
    """
    if not role or not session_id or not bearer:
        raise AutonomousWakeError("role + session_id + bearer required")
    if not relay_subject and not relay_body:
        raise AutonomousWakeError("relay_subject or relay_body required")

    ctx = discovery_context or {}
    wake_instruction = _format_wake_instruction(
        role=role, subject=relay_subject, body=relay_body,
    )
    history = _get_session_events(
        session_id, bearer=bearer, limit=history_limit,
    )

    def _compose(hist: List[Dict[str, Any]]) -> Dict[str, Any]:
        return compose_wake_payload(
            wake_instruction=wake_instruction,
            system_prompt=ctx.get("system_prompt", ""),
            tools=ctx.get("tools"),
            mcp_servers=ctx.get("mcp_servers"),
            history=hist,
            model=model,
            max_tokens=max_tokens,
        )

    payload = _compose(history)

    logger.info(
        "autonomous_wake: firing role=%s cse=%s org=%s history=%d",
        role, _truncate_id(session_id), _truncate_id(org_uuid), len(history),
    )
    try:
        response = post_inference(
            payload, bearer=bearer, session_id=session_id,
        )
    except WakeAuthError:
        # Single retry after forced token refresh. A cached-but-revoked
        # bearer also silently empties the history fetch above (it
        # degrades to [] on non-2xx), so re-fetch before retrying.
        fresh = _refreshed_bearer(role)
        if not fresh or fresh == bearer:
            raise
        logger.info(
            "autonomous_wake: 401 — retrying once with refreshed bearer "
            "role=%s cse=%s", role, _truncate_id(session_id),
        )
        if not history and history_limit > 0:
            history = _get_session_events(
                session_id, bearer=fresh, limit=history_limit,
            )
            payload = _compose(history)
        response = post_inference(
            payload, bearer=fresh, session_id=session_id,
        )
    tool_use_blocks = extract_tool_use_blocks(response)
    return {
        "ok": True,
        "response": response,
        "tool_use_blocks": tool_use_blocks,
        "wake_instruction": wake_instruction,
    }


def _format_wake_instruction(*, role: str, subject: str, body: str) -> str:
    """Compose the user-turn text for the wake inference.

    Frames the relay as an inbound message the role-session should act
    on. Kept short — context comes from history + system_prompt, this
    is just the trigger.
    """
    subj = (subject or "").strip()
    body_text = (body or "").strip()
    return (
        f"[Autonomous wake from inbound relay]\n"
        f"Recipient role: {role}\n"
        f"Subject: {subj}\n\n"
        f"{body_text}"
    )


__all__ = [
    "AutonomousWakeError",
    "WakeAuthError",
    "compose_wake_payload",
    "post_inference",
    "extract_tool_use_blocks",
    "autonomous_wake_from_relay",
]
