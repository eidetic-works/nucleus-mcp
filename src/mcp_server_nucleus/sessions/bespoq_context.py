"""v0.3.x / Task #63 — Bespoq session context reconstruction.

Per op-assistant 2026-06-09T13:25Z operator GREENLIT: without bespoq's
identity (system_prompt + tools + MCP servers), autonomous wake fires
correctly but calls BARE LLM (refuses to act as bespoq). Empirically
proven by 2026-06-09T17:17Z operator trace.

This module loads bespoq's session context from local Claude.app
session file + translates to /v1/messages payload shape.

Source file path:
  ~/Library/Application Support/Claude/local-agent-mode-sessions/
    <account_uuid>/<org_uuid>/local_<some_uuid>.json

Per op-assistant spec, the correct local_<uuid>.json for a given
api.anthropic.com session_id is the one whose `outboundCCRRemoteId`
field matches that session_id. We scan the dir + grep — robust
against operator not having a separate "local_session_uuid" config.

Fields extracted (per op-assistant spec):
- title (display + log_id)
- outboundCCRRemoteId (defensive check: matches config session_id?)
- remoteMcpServersConfig (translate to /v1/messages tools[] entries)
- userSelectedFolders + userSelectedFiles + userSelectedProjectUuids
  (system_prompt addendum)
- egressAllowedDomains (informational only)
- system_prompt or instructions field (if present)

Fallback (per op-assistant): if local file unreadable, log WARN +
caller uses spec-defined defaults (no fail-open; fail-noisily).

Pseudonymity discipline (Layers 0/1/2/4/5/integration carryover):
- account_uuid + org_uuid + session_id truncated [:12] in logs
- File path NEVER logged (contains operator UUIDs)
- File CONTENT (system_prompt may contain operator-specific instructions)
  NOT logged
- NO UUIDs hardcoded in source — all come from caller (AutonomousWakeConfig)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nucleus.bespoq_context")

_LOG_ID_MAX = 12  # PR #499 pseudonymity convention


class BespoqContextError(RuntimeError):
    """Raised when bespoq context reconstruction fails terminally.

    Callers should treat this as non-fatal — Layer 5 will fall back
    to degraded /v1/messages payload (no system_prompt / tools).
    """


def _truncate_id(value: str) -> str:
    return value[:_LOG_ID_MAX] if value else ""


def _local_sessions_dir(account_uuid: str, org_uuid: str) -> Path:
    """Compute the per-account-per-org local sessions directory.

    Does NOT log the constructed path (contains operator UUIDs).
    Returns the Path object without checking existence (caller decides).
    """
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "local-agent-mode-sessions"
        / account_uuid
        / org_uuid
    )


def _find_session_file(
    *,
    account_uuid: str,
    org_uuid: str,
    session_id: str,
) -> Optional[Path]:
    """Scan the per-account-per-org dir for local_<uuid>.json whose
    `outboundCCRRemoteId` field matches `session_id`. Returns None on
    no match / dir absent / read errors.
    """
    base = _local_sessions_dir(account_uuid, org_uuid)
    try:
        candidates = list(base.glob("local_*.json"))
    except OSError:
        return None
    if not candidates:
        return None

    for path in candidates:
        try:
            raw = path.read_text()
        except OSError:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        outbound = data.get("outboundCCRRemoteId")
        if isinstance(outbound, str) and outbound == session_id:
            return path
    return None


def _extract_mcp_servers_as_tools(
    raw_mcp_config: Any,
) -> List[Dict[str, Any]]:
    """Translate Claude.app remoteMcpServersConfig to /v1/messages
    mcp_servers + tools[] shape.

    Defensive: accepts list or dict shape; returns [] for anything else.
    Each entry expected to have at least `url` + `type` keys per Anthropic
    MCP server schema.
    """
    if isinstance(raw_mcp_config, list):
        servers = raw_mcp_config
    elif isinstance(raw_mcp_config, dict):
        # Common dict shape: {"servers": [...]} or {"mcp_servers": [...]}
        servers = (
            raw_mcp_config.get("servers")
            or raw_mcp_config.get("mcp_servers")
            or []
        )
    else:
        return []
    out: List[Dict[str, Any]] = []
    for s in servers:
        if not isinstance(s, dict):
            continue
        # Pass through with defensive copy. Anthropic /v1/messages accepts
        # arbitrary mcp_servers entries; caller (Layer 5 compose_wake_payload)
        # threads them as-is.
        out.append(dict(s))
    return out


def _extract_system_prompt_addendum(
    *,
    folders: Any,
    files: Any,
    projects: Any,
) -> str:
    """Build a system_prompt addendum from operator-selected working context.

    Translates userSelectedFolders + userSelectedFiles + userSelectedProjectUuids
    into a brief context section appended to the base system_prompt.

    Conservative formatting: each list becomes a comma-separated line; empty
    lists omitted. Returns "" if no context selected.
    """
    parts = []
    if isinstance(folders, list) and folders:
        items = [str(f) for f in folders if isinstance(f, str)]
        if items:
            parts.append(f"Working folders: {', '.join(items)}")
    if isinstance(files, list) and files:
        items = [str(f) for f in files if isinstance(f, str)]
        if items:
            parts.append(f"Working files: {', '.join(items)}")
    if isinstance(projects, list) and projects:
        items = [str(p) for p in projects if isinstance(p, str)]
        if items:
            parts.append(f"Active projects: {', '.join(items)}")
    if not parts:
        return ""
    return "\n".join(parts)


def load_bespoq_session_context(
    *,
    account_uuid: str,
    org_uuid: str,
    session_id: str,
    base_system_prompt: str = "",
) -> Optional[Dict[str, Any]]:
    """Load bespoq's session context from local Claude.app file.

    Returns dict with shape consumable as Layer 5 discovery_context:
      {
        system_prompt: str,
        tools: list,           # currently mirrors mcp_servers; refined later
        mcp_servers: list,
        title: str,            # for log_id
      }

    Returns None on any failure (file missing, parse error, UUID mismatch);
    caller falls back to degraded payload.

    Per op-assistant fail-noisily directive: emits logger.warning on
    failure (with truncated IDs, never the full path or content).
    """
    if not account_uuid or not org_uuid or not session_id:
        raise BespoqContextError(
            "account_uuid + org_uuid + session_id required"
        )

    path = _find_session_file(
        account_uuid=account_uuid,
        org_uuid=org_uuid,
        session_id=session_id,
    )
    if path is None:
        logger.warning(
            "bespoq_context: local file not found acct=%s org=%s cse=%s",
            _truncate_id(account_uuid),
            _truncate_id(org_uuid),
            _truncate_id(session_id),
        )
        return None

    try:
        raw = path.read_text()
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "bespoq_context: read/parse failed err=%s cse=%s",
            type(exc).__name__,
            _truncate_id(session_id),
        )
        return None
    if not isinstance(data, dict):
        logger.warning(
            "bespoq_context: file not JSON object cse=%s",
            _truncate_id(session_id),
        )
        return None

    # Defensive cross-check: outboundCCRRemoteId matches caller's session_id
    outbound = data.get("outboundCCRRemoteId")
    if not isinstance(outbound, str) or outbound != session_id:
        logger.warning(
            "bespoq_context: outboundCCRRemoteId mismatch cse=%s",
            _truncate_id(session_id),
        )
        return None

    mcp_servers = _extract_mcp_servers_as_tools(
        data.get("remoteMcpServersConfig"),
    )
    addendum = _extract_system_prompt_addendum(
        folders=data.get("userSelectedFolders"),
        files=data.get("userSelectedFiles"),
        projects=data.get("userSelectedProjectUuids"),
    )
    # Extract instructions / system_prompt field if present
    instructions_field = data.get("instructions") or data.get("system_prompt") or ""
    if not isinstance(instructions_field, str):
        instructions_field = ""

    system_prompt_parts = []
    if base_system_prompt:
        system_prompt_parts.append(base_system_prompt)
    if instructions_field.strip():
        system_prompt_parts.append(instructions_field.strip())
    if addendum:
        system_prompt_parts.append(addendum)
    final_system_prompt = "\n\n".join(system_prompt_parts) if system_prompt_parts else ""

    title = data.get("title")
    if not isinstance(title, str):
        title = ""

    logger.info(
        "bespoq_context: loaded cse=%s mcp_count=%d sys_chars=%d "
        "addendum_chars=%d title_chars=%d",
        _truncate_id(session_id),
        len(mcp_servers),
        len(final_system_prompt),
        len(addendum),
        len(title),
    )

    result: Dict[str, Any] = {}
    if final_system_prompt:
        result["system_prompt"] = final_system_prompt
    if mcp_servers:
        result["mcp_servers"] = mcp_servers
        # Mirror mcp_servers as tools[] (each MCP server exposes its
        # own tool set; Anthropic /v1/messages accepts either shape).
        # Refinement: extract tool schemas per server if present.
        # v1: pass mcp_servers through; tools[] left empty for now.
    if title:
        result["title"] = title
    return result


__all__ = [
    "BespoqContextError",
    "load_bespoq_session_context",
]
