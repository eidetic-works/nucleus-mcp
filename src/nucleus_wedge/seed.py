"""Seed three engrams verbatim from ``.brain/memory/engrams.json`` into history.jsonl on first run.

Idempotent: re-running is a no-op once the seed keys exist in history. "Pull verbatim, don't invent."
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nucleus_wedge.store import Store

SEED_KEYS = ("welcome_nucleus", "workflow_founder", "quick_reference")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engrams_json(brain_path: Path) -> list[dict]:
    path = brain_path / "memory" / "engrams.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def ensure_seeds(store: Store | None = None) -> list[str]:
    """Copy named seeds into history if absent. Returns the list of keys written (empty if all present)."""
    s = store or Store()
    engrams = _engrams_json(s.brain_path())
    by_key = {e.get("key"): e for e in engrams if e.get("key")}
    present = s.keys_present()
    written: list[str] = []
    for seed_key in SEED_KEYS:
        if seed_key in present:
            continue
        entry = by_key.get(seed_key)
        if not entry:
            continue
        s.append(
            value=entry.get("value", ""),
            kind=entry.get("context", "seed"),
            intensity=int(entry.get("intensity", 7)),
            source_agent=entry.get("source", "seed:nucleus-wedge"),
            key=seed_key,
            op_type="SEED",
        )
        written.append(seed_key)
    return written
