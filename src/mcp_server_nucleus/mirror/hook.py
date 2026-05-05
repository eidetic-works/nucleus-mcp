"""Relay surfacing hook: emit unread messages + peer session-mirror.

Surfaces two independent channels so the founder never has to paste:
  1. Unread relay JSON under ``<brain>/relay/<recipient>/``
  2. Peer session-mirror at ``<brain>/session_mirror/cowork_last.md``
     (if mtime newer than the last time this hook surfaced it)

Usage: ``hook.py [EVENT_NAME] [RECIPIENT]``
  EVENT_NAME defaults to SessionStart. Pass UserPromptSubmit for turn-boundary
  surfacing. RECIPIENT defaults to ``$NUCLEUS_RELAY_RECIPIENT`` or
  ``claude_code``.

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
    sid = payload.get("session_id")
    return sid if isinstance(sid, str) and sid else None


def _collect_unread_relays(session_id: Optional[str], inbox: pathlib.Path) -> list[str]:
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
        body = (m.get("body") or "")[:240].strip()
        if body:
            lines.append(f"  {body}")
        mid = m.get("id")
        if mid:
            lines.append(f"  (id: {mid})")
    return lines


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

    recipient = (
        args[1] if len(args) > 1
        else os.environ.get("NUCLEUS_RELAY_RECIPIENT", "claude_code")
    )
    _brain, relay_root, mirror, seen = _brain_dirs()
    inbox = relay_root / recipient

    sections: list[str] = []
    relays = _collect_unread_relays(session_id, inbox)
    if relays:
        sections.append("\n".join(relays))
    mirror_lines = _collect_mirror(mirror, seen)
    if mirror_lines:
        sections.append("\n".join(mirror_lines))

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
