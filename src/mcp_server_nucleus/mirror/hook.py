"""Relay surfacing hook: emit unread messages + peer session-mirror.

Surfaces two independent channels so the founder never has to paste:
  1. Unread relay JSON under ``<brain>/relay/<recipient>/``
  2. Peer session-mirror at ``<brain>/session_mirror/cowork_last.md``
     (if mtime newer than the last time this hook surfaced it)

Usage: ``hook.py [EVENT_NAME] [RECIPIENT]``
  EVENT_NAME defaults to SessionStart. Pass UserPromptSubmit for turn-boundary
  surfacing. RECIPIENT, when omitted, resolves via env precedence:
  ``$CC_SESSION_ROLE`` → ``$NUCLEUS_SESSION_ROLE`` → ``$NUCLEUS_RELAY_RECIPIENT``
  → ``"main"``, then routed through ``resolve_canonical_inbox_name`` so each
  role lands at its canonical inbox (e.g. ``tb`` → ``cc_tb/``).

Per-session targeting: if stdin carries hook JSON with a ``session_id``,
messages whose ``to_session_id`` is set only surface to the matching session.
Broadcast messages (no ``to_session_id``) still surface to every session.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Optional

from mcp_server_nucleus.paths import brain_path

VALID_EVENTS = {"SessionStart", "UserPromptSubmit"}
MIRROR_MAX_CHARS = 4000


def _brain_dirs() -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
    brain = brain_path(strict=False)
    return (
        brain,
        brain / "relay",
        brain / "session_mirror" / "cowork_last.md",
        brain / "session_mirror" / ".seen_cowork_last",
    )


def _read_session_id() -> Optional[str]:
    """Return session_id from hook stdin JSON, or None if unavailable."""
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
        if not raw:
            return None
        payload = json.loads(raw)
    except Exception:
        return None
    # Class-wide guard: json.loads succeeds on any valid JSON value (list, str,
    # int, bool, None) — calling .get() on non-dict raises AttributeError that
    # the try/except above does NOT catch (it wraps only json.loads). Same root
    # pattern as PR #479's hook.py:82 dict-body crash. Per agy battle-test
    # CRACK 5 surface 2026-06-06 06:25Z + cc-main inline source verification.
    if not isinstance(payload, dict):
        return None
    sid = payload.get("session_id")
    return sid if isinstance(sid, str) and sid else None


def _collect_unread_relays(session_id: Optional[str], inbox: pathlib.Path) -> list[str]:
    # PR-A v0.1 swap-point: HTTP-mode routes through relay_transport.read_inbox
    # instead of FS glob. Canonical resolution at the boundary; defensive empty
    # list on transport failure per spec §"HTTP failure handling".
    from mcp_server_nucleus.runtime.relay_transport import is_http_mode, read_inbox
    if is_http_mode():
        unread = read_inbox(inbox.name, unread_only=True, limit=50)
        # Per-session targeting: filter to_session_id same as FS path
        if session_id:
            unread = [m for m in unread if not m.get("to_session_id") or m.get("to_session_id") == session_id]
        if not unread:
            return []
        # Fall through to the SAME presentation loop below.
    else:
        if not inbox.exists():
            return []
        unread = []
        for p in sorted(inbox.glob("*.json")):
            try:
                m = json.loads(p.read_text())
            except Exception:
                continue
            if m.get("read"):
                continue
            target = m.get("to_session_id")
            if target and target != session_id:
                continue
            unread.append(m)
    if not unread:
        return []
    lines = [f"{len(unread)} unread relay message(s) in .brain/relay/{inbox.name}/:"]
    for m in unread:
        priority = m.get("priority", "normal").upper()
        frm = m.get("from", "?")
        subj = m.get("subject", "(no subject)")
        lines.append(f"- [{priority}] from={frm}: {subj}")
        body_raw = m.get("body")
        if isinstance(body_raw, (dict, list)):
            body_raw = json.dumps(body_raw, separators=(",", ":"))
        body = (body_raw or "")[:240].strip() if isinstance(body_raw, str) else ""
        if body:
            lines.append(f"  {body}")
        mid = m.get("id")
        if mid:
            lines.append(f"  (id: {mid})")
    return lines


def _collect_ops_queue(brain: pathlib.Path) -> list[str]:
    """Surface pending OPS-HANDOFF briefs from .brain/ops_queue/."""
    ops_dir = brain / "ops_queue"
    if not ops_dir.exists():
        return []
    pending = sorted(ops_dir.glob("*.md"))
    if not pending:
        return []
    lines = [f"{len(pending)} pending OPS brief(s) in .brain/ops_queue/:"]
    for p in pending:
        try:
            first_line = p.read_text(encoding="utf-8").split("\n", 1)[0].strip()
        except OSError:
            first_line = p.name
        lines.append(f"- {first_line or p.name}")
    lines.append("(Open any .md in .brain/ops_queue/ to read the full brief.)")
    return lines


def _process_autonomous_wake(
    current_role: str,
    brain_root: pathlib.Path,
) -> None:
    """v0.3.0 — Best-effort autonomous-wake fire for offline roles.

    Per cc-peer 2026-06-09T12:15Z Piece B locked contract:
      1. Load NUCLEUS_AUTONOMOUS_WAKE_MAP from ~/.tb/autonomous_wake_config.json
      2. Enumerate OTHER autonomous-registered roles (not current hook role)
      3. Skip roles whose CC sessions are currently running (PID liveness)
      4. For offline roles: scrub bodies/subjects → add_arrival to coalesce
      5. drain_ready_roles after grace expiry → post_relay_to_role
      6. On FallbackChainError: write_failure_sentinel to op_assistant inbox

    Wrapped in outer try/except so any failure NEVER bubbles up + breaks
    the hook (HARD RULE feedback_substrate_behavior_verify_before_next_thing
    + PR #480 precedent). Disable entirely via
    NUCLEUS_AUTONOMOUS_WAKE_DISABLED=1 env var.
    """
    if os.environ.get("NUCLEUS_AUTONOMOUS_WAKE_DISABLED"):
        return
    try:
        from mcp_server_nucleus.runtime.pseudonymity_guard import scrub_pseudonymity
        from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name
        from mcp_server_nucleus.sessions.autonomous_wake_loader import load_autonomous_wake_map
        from mcp_server_nucleus.sessions.autonomous_wake_map import (
            get_autonomous_config,
            list_autonomous_roles,
        )
        from mcp_server_nucleus.sessions.autonomous_wake_sentinel import write_failure_sentinel
        from mcp_server_nucleus.sessions.coalesce_queue import add_arrival, drain_ready_roles
        from mcp_server_nucleus.sessions.discovery_context import build_discovery_context
        from mcp_server_nucleus.sessions.fallback import (
            FallbackChainError,
            post_relay_to_role,
        )
        from mcp_server_nucleus.sessions.session_presence import is_session_running

        load_autonomous_wake_map(clear_first=True)

        for autonomous_role in list_autonomous_roles():
            if autonomous_role == current_role:
                continue
            if is_session_running(autonomous_role):
                continue
            config = get_autonomous_config(autonomous_role)
            if config is None:
                continue
            inbox_name = resolve_canonical_inbox_name(autonomous_role) or autonomous_role
            inbox = brain_root / "relay" / inbox_name
            if not inbox.exists():
                continue
            for relay_path in sorted(inbox.glob("*.json")):
                try:
                    m = json.loads(relay_path.read_text())
                except Exception:
                    continue
                if m.get("read"):
                    continue
                subject_raw = m.get("subject", "") or ""
                body_raw = m.get("body", "")
                if isinstance(body_raw, (dict, list)):
                    body_raw = json.dumps(body_raw, separators=(",", ":"))
                add_arrival(autonomous_role, {
                    "filename": relay_path.name,
                    "subject": scrub_pseudonymity(subject_raw),
                    "body": scrub_pseudonymity(str(body_raw or "")),
                })

        for role, arrivals in drain_ready_roles().items():
            config = get_autonomous_config(role)
            if config is None or not arrivals:
                continue
            combined_subject = "\n".join(a["subject"] for a in arrivals)
            combined_body = "\n\n".join(
                f"({i + 1}) {a['body']}" for i, a in enumerate(arrivals)
            )
            filenames = [a["filename"] for a in arrivals]
            subjects = [a["subject"] for a in arrivals]

            bearer = _fetch_bearer_for_role(role)
            if not bearer:
                continue

            try:
                # Task #63 wiring: thread account_uuid + session_id so
                # build_discovery_context can call bespoq loader for
                # operator-configured identity (system_prompt + tools +
                # MCP servers from local Claude.app session file).
                # account_uuid is Optional on AutonomousWakeConfig —
                # roles without it get degraded (bare LLM) context.
                discovery_context = build_discovery_context(
                    role,
                    bearer=bearer,
                    org_uuid=config.org_uuid,
                    account_uuid=getattr(config, "account_uuid", None),
                    session_id=config.session_id,
                )
            except Exception:
                discovery_context = {}

            try:
                _fire_post_relay(
                    role=role,
                    config=config,
                    bearer=bearer,
                    relay_subject=combined_subject,
                    relay_body=combined_body,
                    discovery_context=discovery_context,
                )
            except FallbackChainError as exc:
                try:
                    write_failure_sentinel(
                        role=role,
                        error_class_name=type(exc).__name__,
                        original_relay_filenames=filenames,
                        relay_subjects=subjects,
                        brain_root=brain_root,
                    )
                except Exception:
                    pass
    except Exception:
        # NEVER let autonomous wake errors bubble up + break the hook.
        # PR #480 hook-break-broke-all-sessions precedent.
        pass


def _fetch_bearer_for_role(role: str) -> str:
    """Wrapper to fetch OAuth bearer; isolated for testability + safety."""
    try:
        from mcp_server_nucleus.oauth.exchange import get_access_token
        return get_access_token(role)
    except Exception:
        return ""


def _fire_post_relay(
    *,
    role,
    config,
    bearer: str,
    relay_subject: str,
    relay_body: str,
    discovery_context: dict,
) -> None:
    """Wrapper to fire Layer 4; isolated so tests can patch this seam
    without re-mocking the full fallback chain."""
    from mcp_server_nucleus.sessions.fallback import post_relay_to_role
    kwargs = {
        "role": role,
        "session_id": config.session_id,
        "org_uuid": config.org_uuid,
        "bearer": bearer,
        "relay_subject": relay_subject,
        "relay_body": relay_body,
        "discovery_context": discovery_context,
        "history_limit": config.history_limit,
        "prearm": config.prearm,
    }
    if config.model is not None:
        kwargs["model"] = config.model
    if config.max_tokens is not None:
        kwargs["max_tokens"] = config.max_tokens
    post_relay_to_role(**kwargs)


def _collect_mirror(mirror: pathlib.Path, seen: pathlib.Path) -> list[str]:
    if not mirror.exists():
        return []
    try:
        current_mtime = mirror.stat().st_mtime
    except OSError:
        return []
    last_mtime = 0.0
    if seen.exists():
        try:
            last_mtime = float(seen.read_text().strip() or "0")
        except (ValueError, OSError):
            last_mtime = 0.0
    if current_mtime <= last_mtime:
        return []
    try:
        content = mirror.read_text()
    except OSError:
        return []
    content = content.strip()
    if not content:
        return []
    if len(content) > MIRROR_MAX_CHARS:
        content = content[:MIRROR_MAX_CHARS] + (
            f"\n... (truncated, {len(content) - MIRROR_MAX_CHARS} more chars in {mirror})"
        )
    try:
        seen.parent.mkdir(parents=True, exist_ok=True)
        seen.write_text(str(current_mtime))
    except OSError:
        pass
    return [
        "Cowork's most recent turn (from .brain/session_mirror/cowork_last.md):",
        content,
    ]


def main(argv: Optional[list[str]] = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    event = args[0] if len(args) > 0 else "SessionStart"
    if event not in VALID_EVENTS:
        event = "SessionStart"

    session_id = _read_session_id()

    from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name
    role_input = (
        args[1] if len(args) > 1
        else os.environ.get("CC_SESSION_ROLE", "")
        or os.environ.get("NUCLEUS_SESSION_ROLE", "")
        or os.environ.get("NUCLEUS_RELAY_RECIPIENT", "")
        or "main"
    )
    recipient = resolve_canonical_inbox_name(role_input) or role_input
    _brain, relay_root, mirror, seen = _brain_dirs()
    inbox = relay_root / recipient

    sections: list[str] = []
    relays = _collect_unread_relays(session_id, inbox)
    if relays:
        sections.append("\n".join(relays))
    ops_lines = _collect_ops_queue(_brain)
    if ops_lines:
        sections.append("\n".join(ops_lines))
    mirror_lines = _collect_mirror(mirror, seen)
    if mirror_lines:
        sections.append("\n".join(mirror_lines))

    # v0.3.0 — opportunistic autonomous-wake for OFFLINE registered roles.
    # Wrapped internally in try/except; cannot break the hook.
    _process_autonomous_wake(role_input, _brain)

    if not sections:
        return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": "\n\n".join(sections),
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
