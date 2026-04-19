"""Store — load/append .brain/engrams/history.jsonl using the existing record shape.

Record shape (matches ``auto_hook`` writers so both can coexist):

    {
      "key": <str>,
      "op_type": <str>,
      "timestamp": <ISO-8601>,
      "snapshot": {
        "key": <str>,            # duplicated for snapshot self-containment
        "value": <str>,          # primary content body
        "context": <str>,        # kind / taxonomy label
        "intensity": <int 1-10>,
        "version": <int>,
        "source_agent": <str>,
        "op_type": <str>,
        "timestamp": <ISO-8601>,
        "deleted": <bool>,
        "signature": <str|None>
      }
    }
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Append-only reader/writer over ``.brain/engrams/history.jsonl``."""

    def __init__(self, brain_path: Path | None = None):
        self._brain_path = Path(brain_path) if brain_path else self.brain_path()
        self._history = self._brain_path / "engrams" / "history.jsonl"
        self._history.parent.mkdir(parents=True, exist_ok=True)
        self._history.touch(exist_ok=True)

    @staticmethod
    def brain_path(flag: Path | str | None = None) -> Path:
        """Resolve ``.brain`` path per ``week2_init_flow_spec.md`` §3a.

        Order: explicit ``flag`` → ``NUCLEUS_BRAIN_PATH``/``NUCLEAR_BRAIN_PATH`` env →
        cwd contains ``.brain/`` → cwd contains ``.git/`` (greenfield, returned path
        not yet created) → abort. No silent walk-up across cwd ancestors (gap 1a:
        cwd-binding hazard from `feedback_relay_post_cross_worktree.md`).
        """
        if flag is not None:
            return Path(flag)
        env = os.environ.get("NUCLEUS_BRAIN_PATH") or os.environ.get("NUCLEAR_BRAIN_PATH")
        if env:
            return Path(env)
        cwd = Path.cwd()
        if (cwd / ".brain").exists():
            return cwd / ".brain"
        if (cwd / ".git").exists():
            return cwd / ".brain"
        raise ValueError(
            "nucleus init: cannot resolve brain path.\n"
            "  Either: pass --brain-path /absolute/path\n"
            "      or: export NUCLEUS_BRAIN_PATH=/absolute/path\n"
            "      or: run from a directory containing .git/ or .brain/"
        )

    @property
    def history_file(self) -> Path:
        return self._history

    def rows(self) -> Iterator[dict]:
        """Stream raw records from history.jsonl."""
        with self._history.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def keys_present(self) -> set[str]:
        """Top-level keys currently in history — used by ``seed.ensure_seeds`` for idempotence."""
        return {r.get("key") for r in self.rows() if r.get("key")}

    def append(
        self,
        value: str,
        kind: str = "note",
        tags: list[str] | None = None,
        intensity: int = 5,
        source_agent: str = "nucleus-wedge",
        key: str | None = None,
        op_type: str = "ADD",
    ) -> dict:
        """Append one record. Returns ``{key, timestamp}``."""
        ts = _iso_now()
        if not key:
            key = f"remember_{ts.replace(':', '').replace('-', '').replace('.', '')[:19]}_{uuid.uuid4().hex[:8]}"
        context = kind if not tags else f"{kind} [#{','.join(tags)}]"
        record = {
            "key": key,
            "op_type": op_type,
            "timestamp": ts,
            "snapshot": {
                "key": key,
                "value": value,
                "context": context,
                "intensity": intensity,
                "version": 1,
                "source_agent": source_agent,
                "op_type": op_type,
                "timestamp": ts,
                "deleted": False,
                "signature": None,
            },
        }
        with self._history.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"key": key, "timestamp": ts}

    @staticmethod
    def extract(row: dict) -> dict:
        """Flatten one row into ``{key, value, context, timestamp, kind}`` for ranking/return."""
        snap = row.get("snapshot") or {}
        return {
            "key": row.get("key"),
            "value": snap.get("value") or row.get("value") or "",
            "context": snap.get("context") or row.get("context") or "",
            "timestamp": snap.get("timestamp") or row.get("timestamp") or "",
            "kind": snap.get("context") or "",
            "source_agent": snap.get("source_agent") or "",
        }
