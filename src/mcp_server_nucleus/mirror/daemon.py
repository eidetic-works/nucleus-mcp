"""Cowork → CC session-mirror daemon.

Finds the peer agent's most-recent conversation JSONL on the host filesystem,
extracts the last assistant turn, and writes it to
``<brain>/session_mirror/cowork_last.md`` when content changes.
CC's ``relay_inbox_hook`` surfaces the mirror as additionalContext on
SessionStart + UserPromptSubmit.

Idempotent: guarded by source-mtime + content-hash; safe to run on any cadence.
Zero peer-side behavior required — reads on-disk transcripts directly.

Portable: transcript shape is pluggable via ``transcript_source`` (default
reads Cowork's JSONL shape). Root path comes from
``NUCLEUS_TRANSCRIPT_ROOT``; brain output is ``NUCLEUS_BRAIN`` /
session_mirror.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Callable, Iterator, Optional

from mcp_server_nucleus.paths import brain_path, transcript_root

JSONL_PATTERN = "*/*/local_*/.claude/projects/*/*.jsonl"
DEFAULT_COWORK_SUBPATH = "Library/Application Support/Claude/local-agent-mode-sessions"


TranscriptSource = Callable[[pathlib.Path], Iterator[dict]]


def cowork_jsonl_source(jsonl: pathlib.Path) -> Iterator[dict]:
    """Default adapter: read Cowork's JSONL conversation shape line-by-line."""
    with jsonl.open() as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _default_transcript_root() -> pathlib.Path:
    env = transcript_root(strict=False)
    if env is not None:
        return env
    return pathlib.Path.home() / DEFAULT_COWORK_SUBPATH


def _session_mirror_dir() -> pathlib.Path:
    return brain_path(strict=False) / "session_mirror"


def find_latest_jsonl(root: pathlib.Path) -> Optional[pathlib.Path]:
    if not root.exists():
        return None
    candidates = list(root.glob(JSONL_PATTERN))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def extract_last_assistant_text(
    jsonl: pathlib.Path,
    source: TranscriptSource = cowork_jsonl_source,
) -> Optional[str]:
    last: Optional[str] = None
    for d in source(jsonl):
        if not isinstance(d, dict) or d.get("type") != "assistant":
            continue
        m = d.get("message", {})
        content = m.get("content") if isinstance(m, dict) else None
        if isinstance(content, list):
            text_blocks = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            text = "\n".join(t for t in text_blocks if t).strip()
        elif isinstance(content, str):
            text = content.strip()
        else:
            text = ""
        if text:
            last = text
    return last


def load_state(state_path: pathlib.Path) -> dict:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state_path: pathlib.Path, s: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(s))


def main(
    transcript_root_path: Optional[pathlib.Path] = None,
    mirror_path: Optional[pathlib.Path] = None,
    state_path: Optional[pathlib.Path] = None,
    source: TranscriptSource = cowork_jsonl_source,
) -> int:
    root = transcript_root_path or _default_transcript_root()
    mirror_dir = _session_mirror_dir()
    mirror = mirror_path or mirror_dir / "cowork_last.md"
    state = state_path or mirror_dir / ".daemon_state.json"

    jsonl = find_latest_jsonl(root)
    if jsonl is None:
        return 0
    source_mtime = jsonl.stat().st_mtime
    current = load_state(state)
    if (
        current.get("source_path") == str(jsonl)
        and current.get("source_mtime") == source_mtime
    ):
        return 0
    text = extract_last_assistant_text(jsonl, source=source)
    new_state = {"source_path": str(jsonl), "source_mtime": source_mtime}
    if not text:
        new_state["content_hash"] = current.get("content_hash", "")
        save_state(state, new_state)
        return 0
    h = hashlib.sha256(text.encode()).hexdigest()
    new_state["content_hash"] = h
    if current.get("content_hash") == h:
        save_state(state, new_state)
        return 0
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(text)
    save_state(state, new_state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
