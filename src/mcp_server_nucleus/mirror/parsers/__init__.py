"""Per-surface parsers for the multi-surface engram capture daemon.

Each parser converts a raw transcript file (JSONL, JSON, etc.) into a stream of
``EngramEvent`` instances. Parsers are deliberately tiny and pure — they take a
``pathlib.Path`` and yield events. All filesystem watching, throttling,
backpressure, and sink-writing lives in the coordinator (``mirror/daemon.py``)
or in the per-surface watchers.

Adding a new surface = add a parser module + a watcher module + register in
``daemon.py`` config.
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Iterator, Optional


@dataclasses.dataclass(frozen=True)
class EngramEvent:
    """A single conversational turn captured from a surface transcript.

    Designed to be small + serializable: the coordinator persists these to the
    engram store, optionally batched.
    """

    surface: str  # "cursor" | "claude_code" | "cowork"
    role: str  # "user" | "assistant" | "tool_use" | "tool_result" | "system"
    content: str  # The text payload; may be empty for tool turns with no text
    timestamp: Optional[str] = None  # ISO-8601 if available, else None
    session_id: Optional[str] = None  # Surface-native session/conversation id
    workspace: Optional[str] = None  # Cursor-specific workspace identifier
    source_path: Optional[str] = None  # File the event was parsed from
    extra: Optional[dict] = None  # Free-form per-surface metadata


ParserFn = "callable[[pathlib.Path], Iterator[EngramEvent]]"


__all__ = ["EngramEvent", "ParserFn"]
