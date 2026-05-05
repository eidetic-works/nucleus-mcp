"""Central schema-version registry for durable Nucleus data kinds.

Each kind declared here has a `SCHEMA_VERSION` that MAY be embedded in
new writes and MUST be honored on reads (with auto-upgrade from older
versions). Bumping a version is a deliberate act — it signals readers
that migration is required.

The envelope has its own version in `tools/_envelope.ENVELOPE_SCHEMA_VERSION`
(different lifecycle, consumer-facing).

Usage:
    from mcp_server_nucleus.runtime.schema_versions import ENGRAM_SCHEMA_VERSION, upgrade
    record = upgrade("engram", raw_record)
"""

from __future__ import annotations

from typing import Any, Callable, Dict

# -----------------------------------------------------------------------------
# Version constants — bump these when a write-shape change is introduced.
# -----------------------------------------------------------------------------

STATE_SCHEMA_VERSION = 2
"""state.json — top-level sprint / priorities / deadlines shape."""

ENGRAM_SCHEMA_VERSION = 2
"""Individual engram records in .brain/engrams/."""

TASK_SCHEMA_VERSION = 2
"""Task records in .brain/tasks/."""

MANIFEST_SCHEMA_VERSION = 2
"""`.brain/manifest.yaml` shape."""


# -----------------------------------------------------------------------------
# Upgrade registry — pure functions that promote a record from version N-1 to N.
# -----------------------------------------------------------------------------

# Each upgrader receives a dict and MUST return a dict. It MAY be called
# multiple times (chained) to walk a record from a very old version up
# to current.
_UPGRADERS: Dict[str, Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]]] = {
    "state": {},
    "engram": {},
    "task": {},
    "manifest": {},
}


def _bump_state_v1_to_v2(record: Dict[str, Any]) -> Dict[str, Any]:
    """Add stale_after defaults to priorities/tasks for Phase 1.3 hygiene GC."""
    out = dict(record)
    priorities = out.get("priorities", [])
    if isinstance(priorities, list):
        out["priorities"] = [
            {**p, "stale_after": p.get("stale_after", "14d")}
            if isinstance(p, dict)
            else p
            for p in priorities
        ]
    tasks = out.get("tasks", [])
    if isinstance(tasks, list):
        out["tasks"] = [
            {**t, "stale_after": t.get("stale_after", "30d")}
            if isinstance(t, dict)
            else t
            for t in tasks
        ]
    out["schema_version"] = 2
    return out


def _bump_engram_v1_to_v2(record: Dict[str, Any]) -> Dict[str, Any]:
    """Add project/brain_id defaults for Phase 2.2 scoping (v1.3-facing but
    stub reserved in v1.2 so readers don't choke on mixed corpora)."""
    out = dict(record)
    out.setdefault("project", "_unscoped")
    out.setdefault("brain_id", "unknown")
    out["schema_version"] = 2
    return out


def _bump_task_v1_to_v2(record: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(record)
    out.setdefault("stale_after", "30d")
    out["schema_version"] = 2
    return out


def _bump_manifest_v1_to_v2(record: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(record)
    out.setdefault("tracks_projects", [])
    out.setdefault("primary_brain", False)
    out["schema_version"] = 2
    return out


_UPGRADERS["state"][2] = _bump_state_v1_to_v2
_UPGRADERS["engram"][2] = _bump_engram_v1_to_v2
_UPGRADERS["task"][2] = _bump_task_v1_to_v2
_UPGRADERS["manifest"][2] = _bump_manifest_v1_to_v2


_CURRENT = {
    "state": STATE_SCHEMA_VERSION,
    "engram": ENGRAM_SCHEMA_VERSION,
    "task": TASK_SCHEMA_VERSION,
    "manifest": MANIFEST_SCHEMA_VERSION,
}


def current_version(kind: str) -> int:
    """Return the current schema version for `kind`."""
    if kind not in _CURRENT:
        raise ValueError(f"unknown kind: {kind!r}. Known: {sorted(_CURRENT)}")
    return _CURRENT[kind]


def upgrade(kind: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Walk `record` up to the current schema version for `kind`.

    If `record` has no `schema_version`, treat it as version 1.
    Each step MUST be pure — no I/O, no global state.
    Idempotent: upgrading an already-current record returns it unchanged.
    """
    if not isinstance(record, dict):
        raise TypeError(f"record must be dict, got {type(record).__name__}")
    current = current_version(kind)
    version = int(record.get("schema_version", 1))
    while version < current:
        next_version = version + 1
        upgrader = _UPGRADERS[kind].get(next_version)
        if upgrader is None:
            raise RuntimeError(
                f"missing upgrader for {kind} v{version} -> v{next_version}"
            )
        record = upgrader(record)
        version = next_version
    return record


__all__ = [
    "STATE_SCHEMA_VERSION",
    "ENGRAM_SCHEMA_VERSION",
    "TASK_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "current_version",
    "upgrade",
]
