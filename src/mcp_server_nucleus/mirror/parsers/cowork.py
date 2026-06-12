"""Cowork (Claude Desktop ``local-agent-mode-sessions``) parser.

Cowork stores conversations as JSONL very similar to Claude Code but with
a slightly different envelope shape (no ``parentUuid`` chain; ``message`` is
the canonical key with ``role`` + ``content``).

This parser wraps the existing logic in ``mirror/daemon.py`` (the
``cowork_jsonl_source`` adapter + ``extract_last_assistant_text``) into the
uniform ``EngramEvent`` interface used by the multi-surface coordinator. The
legacy ``main()`` entrypoint in ``daemon.py`` still works for the
single-shot Cowork mirror behavior (it just writes the LAST assistant turn
to ``cowork_last.md`` for the relay-inbox hook).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Iterator

from . import EngramEvent


def _coerce_text(content: Any) -> str:
    """Cowork content is either a string or a list of {type:text, text:...}
    blocks — same shape as Anthropic's content blocks."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                t = b.get("text")
                if isinstance(t, str):
                    chunks.append(t)
        return "\n".join(c for c in chunks if c).strip()
    return ""


def parse_session_file(path: pathlib.Path) -> Iterator[EngramEvent]:
    """Yield ``EngramEvent`` for every assistant + user turn in a Cowork JSONL.

    Matches the existing ``daemon.cowork_jsonl_source`` adapter behavior
    (skips malformed lines silently) but emits structured events instead of
    just returning the last assistant text.
    """
    try:
        f = path.open("r", encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    session_id = path.stem  # Cowork JSONLs are named <session-uuid>.jsonl

    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(d, dict):
                continue

            envelope_type = d.get("type")
            if envelope_type not in ("assistant", "user"):
                continue

            msg = d.get("message")
            if not isinstance(msg, dict):
                continue

            text = _coerce_text(msg.get("content"))
            if not text:
                continue

            yield EngramEvent(
                surface="cowork",
                role=envelope_type,
                content=text,
                timestamp=d.get("timestamp") if isinstance(d.get("timestamp"), str) else None,
                session_id=session_id,
                source_path=str(path),
                extra={"envelope_type": envelope_type},
            )


__all__ = ["parse_session_file"]
