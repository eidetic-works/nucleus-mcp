"""Cursor chat-session parser.

Empirically determined from Cursor on macOS (2026-05-21, Cursor 1.x):

- Per-workspace session JSON lives at
  ``<workspaceStorage>/<workspace-hash>/chatSessions/<session-uuid>.json``
- Top-level schema (verified on real session files)::

    {
      "version": 3,
      "requesterUsername": "...",
      "responderUsername": "...",
      "sessionId": "<uuid>",
      "creationDate": <epoch-ms>,
      "lastMessageDate": <epoch-ms>,
      "requests": [
        {
          "requestId": "request_<uuid>",
          "message": {"text": "<user prompt>", "parts": [...]},
          "response": [
            {"value": "<assistant text fragment>"},
            ...
          ]
        },
        ...
      ]
    }

- Some workspaces ALSO store conversations inside SQLite at
  ``<workspaceStorage>/<workspace-hash>/state.vscdb`` under the
  ``ItemTable`` key ``composer.composerData``. The current parser handles the
  JSON shape only; SQLite extraction is a follow-up (tracked in ADR-0010).
- ``response`` is sometimes a list of fragment-dicts (each carrying ``value``),
  sometimes a list of plain strings, sometimes a single string. We coerce all
  shapes into a single concatenated string.

Version tolerance: ``version`` field is informational; we never read it as a
gate. Unknown fields are ignored. Malformed files yield no events rather than
crashing the watcher.
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
from typing import Any, Iterator, Optional

from . import EngramEvent


def _epoch_ms_to_iso(value: Any) -> Optional[str]:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    try:
        # creationDate / lastMessageDate are epoch milliseconds
        return _dt.datetime.fromtimestamp(value / 1000.0, tz=_dt.timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _coerce_response_text(resp: Any) -> str:
    """Cursor's response field is heterogenous — collapse to a single string."""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp.strip()
    if isinstance(resp, dict):
        # Single response object
        v = resp.get("value")
        return v.strip() if isinstance(v, str) else ""
    if isinstance(resp, list):
        parts = []
        for item in resp:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                v = item.get("value")
                if isinstance(v, str):
                    parts.append(v)
        return "".join(parts).strip()
    return ""


def _coerce_request_text(msg: Any) -> str:
    """User-side prompt text. Cursor may store it as a string or as a
    structured ``parts`` array."""
    if msg is None:
        return ""
    if isinstance(msg, str):
        return msg.strip()
    if isinstance(msg, dict):
        text = msg.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        # Fall back to concatenating "parts"
        parts = msg.get("parts")
        if isinstance(parts, list):
            chunks = []
            for p in parts:
                if isinstance(p, dict):
                    t = p.get("text")
                    if isinstance(t, str):
                        chunks.append(t)
                elif isinstance(p, str):
                    chunks.append(p)
            return "".join(chunks).strip()
    return ""


def parse_session_file(path: pathlib.Path) -> Iterator[EngramEvent]:
    """Yield ``EngramEvent`` for every user prompt + assistant reply in the
    Cursor session JSON at ``path``.

    Silently yields nothing on malformed JSON or missing schema. Never raises
    on file-content issues — only OSError from path operations propagates.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    if not raw.strip():
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return

    session_id = data.get("sessionId") if isinstance(data.get("sessionId"), str) else None
    creation_iso = _epoch_ms_to_iso(data.get("creationDate"))
    last_iso = _epoch_ms_to_iso(data.get("lastMessageDate"))

    # Workspace identifier comes from the path: chatSessions lives under
    # <workspace-hash>/chatSessions/, so the workspace hash is the parent of
    # the chatSessions directory.
    workspace: Optional[str] = None
    try:
        if path.parent.name == "chatSessions":
            workspace = path.parent.parent.name
    except (AttributeError, IndexError):
        pass

    requests = data.get("requests")
    if not isinstance(requests, list):
        return

    for idx, req in enumerate(requests):
        if not isinstance(req, dict):
            continue
        # Per-request timestamps are not always present; fall back to session.
        ts = (
            _epoch_ms_to_iso(req.get("timestamp"))
            or _epoch_ms_to_iso(req.get("creationDate"))
            or creation_iso
            or last_iso
        )
        request_id = req.get("requestId") if isinstance(req.get("requestId"), str) else None

        user_text = _coerce_request_text(req.get("message"))
        if user_text:
            yield EngramEvent(
                surface="cursor",
                role="user",
                content=user_text,
                timestamp=ts,
                session_id=session_id,
                workspace=workspace,
                source_path=str(path),
                extra={"request_id": request_id, "request_index": idx},
            )

        assistant_text = _coerce_response_text(req.get("response"))
        if assistant_text:
            yield EngramEvent(
                surface="cursor",
                role="assistant",
                content=assistant_text,
                timestamp=ts,
                session_id=session_id,
                workspace=workspace,
                source_path=str(path),
                extra={"request_id": request_id, "request_index": idx},
            )


__all__ = ["parse_session_file"]
