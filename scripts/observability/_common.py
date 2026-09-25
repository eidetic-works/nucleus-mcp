"""Shared helpers for cross-trio observability scripts.

Stdlib-only. Reads coord_events.jsonl, parses lines, exposes simple iterators.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def brain_path() -> Path:
    """Resolve .brain/ directory respecting NUCLEUS_BRAIN_PATH override."""
    env = os.environ.get("NUCLEUS_BRAIN_PATH")
    if env:
        return Path(env)
    # Walk up from cwd looking for .brain/
    p = Path.cwd().resolve()
    while p != p.parent:
        if (p / ".brain").is_dir():
            return p / ".brain"
        p = p.parent
    # Fallback: hardcoded developer path (only for personal-machine convenience)
    fallback = Path.home() / "ai-mvp-backend" / ".brain"
    if fallback.is_dir():
        return fallback
    raise SystemExit("Could not locate .brain/ — set NUCLEUS_BRAIN_PATH or run from inside repo")


def coord_events_path() -> Path:
    return brain_path() / "ledger" / "coordination_events.jsonl"


def iter_coord_events(since_iso: str | None = None) -> Iterator[dict[str, Any]]:
    """Yield coord events from ledger, optionally filtered to those at/after since_iso."""
    path = coord_events_path()
    if not path.exists():
        return
    since_dt = None
    if since_iso:
        since_dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since_dt:
                ts = ev.get("timestamp", "")
                try:
                    ev_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if ev_dt < since_dt:
                    continue
            yield ev


def parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def relay_buckets() -> list[Path]:
    """Return all relay bucket directories under .brain/relay/"""
    relay_dir = brain_path() / "relay"
    if not relay_dir.is_dir():
        return []
    return [d for d in relay_dir.iterdir() if d.is_dir() and d.name not in ("processed",)]


def iter_relays(bucket: Path, since_iso: str | None = None) -> Iterator[dict[str, Any]]:
    """Yield relay JSONs from a bucket dir."""
    if not bucket.is_dir():
        return
    since_dt = parse_iso(since_iso) if since_iso else None
    for f in sorted(bucket.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if since_dt:
            created = data.get("created_at", "")
            ev_dt = parse_iso(created)
            if not ev_dt or ev_dt < since_dt:
                continue
        yield data


def load_taxonomy() -> dict[str, dict[str, Any]]:
    """Load scope_taxonomy.yaml. Real yaml if available, minimal fallback otherwise."""
    path = brain_path() / "charters" / "scope_taxonomy.yaml"
    if not path.exists():
        raise SystemExit(f"taxonomy missing: {path}")
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:
        return _minimal_yaml_parse(path.read_text())


def _minimal_yaml_parse(text: str) -> dict[str, dict[str, Any]]:
    """Tiny YAML-subset parser supporting the exact shape of scope_taxonomy.yaml.

    Handles: top-level agent keys, nested permitted_tags/permitted_event_types/description,
    list values as `- tag` lines, simple scalar `key: value`, # comments.
    """
    out: dict[str, dict[str, Any]] = {}
    current_agent: str | None = None
    current_list_key: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw.startswith(" "):
            if line.endswith(":"):
                current_agent = line[:-1].strip()
                current_list_key = None
                out[current_agent] = {}
            continue
        if current_agent is None:
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 2 and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                out[current_agent][key] = val.strip("\"'")
                current_list_key = None
            else:
                current_list_key = key
                out[current_agent][key] = []
        elif indent >= 4 and stripped.startswith("- "):
            if current_list_key is not None:
                out[current_agent][current_list_key].append(stripped[2:].strip().strip("\"'"))
    return out


def taxonomy_lane_keywords(taxonomy: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """Derive agent-exclusive tag set per agent for cross-talk detection.

    A tag counts as a lane-keyword for agent X iff it appears under EXACTLY ONE
    agent's permitted_tags. Tags shared across multiple agents are dropped — they
    are shared vocabulary, not lane signals.

    Replaces the hard-coded LANE_KEYWORDS table in cross_trio_dashboard.cross_talk_rate
    so taxonomy edits flow through without code changes.
    """
    tag_owners: dict[str, set[str]] = {}
    for agent, charter in taxonomy.items():
        for tag in charter.get("permitted_tags", []) or []:
            tag_owners.setdefault(tag, set()).add(agent)
    exclusive: dict[str, set[str]] = {agent: set() for agent in taxonomy}
    for tag, owners in tag_owners.items():
        if len(owners) == 1:
            (only,) = owners
            exclusive[only].add(tag)
    return exclusive


def extract_tags_from_relay(relay: dict[str, Any]) -> list[str]:
    """Extract tags list from relay envelope, handling both legacy and current shapes."""
    body = relay.get("body", "")
    if isinstance(body, dict):
        tags = body.get("tags", [])
    else:
        # body is JSON string
        try:
            parsed = json.loads(body) if isinstance(body, str) else {}
            tags = parsed.get("tags", []) if isinstance(parsed, dict) else []
        except json.JSONDecodeError:
            tags = []
    return tags if isinstance(tags, list) else []
