"""v0.3.0 integration + Task #63 wiring — discovery_context composer.

Per op-assistant 2026-06-09T14:45Z empirical e2e finding: PR #519
shipped bespoq_context LOADER but no call site existed. Autonomous
wake fired with BARE LLM context; loop didn't close. This module
now calls load_bespoq_session_context when caller passes account_uuid
+ session_id — closing the wiring gap per op-assistant routing.

Best-effort posture:
- Each Layer 2 call wrapped in try/except DiscoveryError
- bespoq_context loader returns None on failure (file missing /
  corrupt / mismatch); absorbed without breaking the wake fire
- Backward-compat: when account_uuid/session_id absent OR loader
  returns None, Layer 2 mcp_servers path is unchanged. Degraded
  not crashed.

Merge precedence (system_prompt + mcp_servers):
- bespoq context wins for system_prompt (operator-configured
  identity for the autonomous role)
- mcp_servers MERGED from both sources (bespoq + Layer 2);
  de-duplicated by url (bespoq first wins)

Pseudonymity:
- OAuth bearer never logged (Layer 2 + bespoq_context enforce)
- org_uuid + account_uuid truncated [:12] in logs per PR #499
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from mcp_server_nucleus.org.discovery import (
    DiscoveryError,
    get_mcp_bootstrap,
)
from mcp_server_nucleus.sessions.bespoq_context import (
    BespoqContextError,
    load_bespoq_session_context,
)


logger = logging.getLogger("nucleus.discovery_context")

_LOG_ID_MAX = 12  # PR #499 pseudonymity convention


def _truncate_id(value: str) -> str:
    return value[:_LOG_ID_MAX] if value else ""


def build_discovery_context(
    role: str,
    *,
    bearer: str,
    org_uuid: str,
    system_prompt: str = "",
    account_uuid: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Compose Layer 5 discovery_context from Layer 2 + bespoq loader.

    Returns a dict suitable for passing as discovery_context to
    nucleus.sessions.autonomous_wake.autonomous_wake_from_relay
    OR nucleus.sessions.fallback.post_relay_to_role:

      {
        system_prompt: str,   # bespoq wins; else caller arg
        mcp_servers: list,    # merged: bespoq + Layer 2 (de-duped by url)
        title: str,           # bespoq title for log_id (when present)
      }

    Each call is best-effort. Result behavior:
    - account_uuid + session_id absent: bespoq lookup skipped
      (backward compat — same shape as pre-Task-63 callers)
    - bespoq loader returns None (file missing / corrupt / mismatch):
      logged WARN + Layer 2 path unchanged
    - Layer 2 DiscoveryError: logged WARN + bespoq context still threaded
    """
    if not role:
        raise ValueError("role required")
    if not bearer:
        raise ValueError("bearer required")
    if not org_uuid:
        raise ValueError("org_uuid required")

    context: Dict[str, Any] = {}
    base_system_prompt = system_prompt or ""

    # ── Task #63 wiring: bespoq context loader (best-effort) ───────
    bespoq_mcp_servers: List[Dict[str, Any]] = []
    if account_uuid and session_id:
        try:
            bespoq = load_bespoq_session_context(
                account_uuid=account_uuid,
                org_uuid=org_uuid,
                session_id=session_id,
                base_system_prompt=base_system_prompt,
            )
        except BespoqContextError as exc:
            logger.warning(
                "discovery_context: bespoq loader rejected role=%s err=%s",
                role, type(exc).__name__,
            )
            bespoq = None
        if bespoq is not None:
            if bespoq.get("system_prompt"):
                context["system_prompt"] = bespoq["system_prompt"]
            if bespoq.get("title"):
                context["title"] = bespoq["title"]
            bespoq_mcp_servers = list(bespoq.get("mcp_servers") or [])
        else:
            logger.warning(
                "discovery_context: bespoq context unavailable role=%s acct=%s",
                role, _truncate_id(account_uuid),
            )

    # bespoq did not supply system_prompt → fall back to caller arg
    if "system_prompt" not in context and base_system_prompt:
        context["system_prompt"] = base_system_prompt

    # ── Layer 2: MCP server inventory (best-effort) ────────────────
    layer2_mcp_servers: List[Dict[str, Any]] = []
    try:
        bootstrap = get_mcp_bootstrap(org_uuid, bearer=bearer)
        layer2_mcp_servers = _extract_mcp_servers(bootstrap)
    except DiscoveryError as exc:
        logger.warning(
            "discovery_context: get_mcp_bootstrap failed role=%s org=%s err=%s",
            role, _truncate_id(org_uuid), type(exc).__name__,
        )

    merged_servers = _merge_mcp_servers(bespoq_mcp_servers, layer2_mcp_servers)
    if merged_servers:
        context["mcp_servers"] = merged_servers

    logger.info(
        "discovery_context: built role=%s org=%s acct=%s "
        "bespoq=%d layer2=%d merged=%d sys_chars=%d",
        role,
        _truncate_id(org_uuid),
        _truncate_id(account_uuid or ""),
        len(bespoq_mcp_servers),
        len(layer2_mcp_servers),
        len(merged_servers),
        len(context.get("system_prompt", "")),
    )

    return context


def _merge_mcp_servers(
    primary: List[Dict[str, Any]],
    fallback: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """De-duplicate by `url`; primary wins. Entries without `url` kept
    (no dedup possible)."""
    seen_urls = set()
    out: List[Dict[str, Any]] = []
    for s in list(primary) + list(fallback):
        if not isinstance(s, dict):
            continue
        url = s.get("url")
        if isinstance(url, str):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            out.append(s)
        else:
            out.append(s)
    return out


def _extract_mcp_servers(bootstrap: Any) -> list:
    """Extract mcp_servers list from /mcp/v2/bootstrap response.

    Response shape per spec § Layer 2 is provisional; defensive
    parsing accepts:
      - {"mcp_servers": [...]}
      - {"servers": [...]}
      - {"data": {"mcp_servers": [...]}}
      - list at top level
    """
    if isinstance(bootstrap, list):
        return list(bootstrap)
    if not isinstance(bootstrap, dict):
        return []
    candidates = (
        bootstrap.get("mcp_servers"),
        bootstrap.get("servers"),
        (bootstrap.get("data") or {}).get("mcp_servers"),
    )
    for candidate in candidates:
        if isinstance(candidate, list):
            return list(candidate)
    return []


__all__ = [
    "build_discovery_context",
]
