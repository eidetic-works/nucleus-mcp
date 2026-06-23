"""Nucleus Runtime — W8 Team-Tier Audit Log (SHA-256 hash chain).

Provides a tamper-evident, append-only audit trail for multi-tenant Team-tier
installations. Every record contains a SHA-256 hash of the previous record,
forming a chain: modifying any historical record breaks all subsequent hashes
and is immediately detectable.

Storage: SQLite append-only at `<brain>/.brain/audit/audit.db`.
Multi-tenant: records are partitioned by `team_id` (a string key). Cross-team
queries are rejected unless the caller is an admin (team_id='*').

Usage::

    from mcp_server_nucleus.runtime.audit_log import log_event, query_audit

    record = log_event(
        event_type="tool_call",
        actor="agent-123",
        resource="nucleus_tasks/claim",
        outcome="success",
        metadata={"task_id": "T-001"},
        team_id="team-acme",
    )

    records = query_audit(team_id="team-acme", since="2026-06-01T00:00:00Z")
    for r in records:
        print(r.event_type, r.actor, r.hash)

Hash-chain integrity check::

    from mcp_server_nucleus.runtime.audit_log import verify_chain

    ok, broken_at = verify_chain(team_id="team-acme")
    assert ok, f"Chain broken at record {broken_at}"
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.audit_log")

# ── Thread-local DB connections ──────────────────────────────────────────────
_local = threading.local()
_DB_INIT_LOCK = threading.Lock()
_DB_INITIALIZED: dict[str, bool] = {}

# ── Sentinel for the genesis record ─────────────────────────────────────────
_GENESIS_PREV_HASH = "0" * 64  # SHA-256 zero hash for the first record


# ── Schema ───────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS audit_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    actor       TEXT    NOT NULL,
    resource    TEXT    NOT NULL,
    outcome     TEXT    NOT NULL,
    metadata    TEXT    NOT NULL DEFAULT '{}',
    ts          TEXT    NOT NULL,
    prev_hash   TEXT    NOT NULL,
    hash        TEXT    NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_audit_team_ts
    ON audit_records (team_id, ts);

CREATE INDEX IF NOT EXISTS idx_audit_team_actor
    ON audit_records (team_id, actor);

CREATE INDEX IF NOT EXISTS idx_audit_team_event
    ON audit_records (team_id, event_type);
"""


# ── AuditRecord dataclass ────────────────────────────────────────────────────

@dataclass
class AuditRecord:
    """A single immutable audit entry in the hash chain."""

    id: int
    """Auto-increment row id (stable within one DB)."""

    team_id: str
    """Team identifier (multi-tenant partition key)."""

    event_type: str
    """Event category, e.g. 'tool_call', 'login', 'config_change'."""

    actor: str
    """Who performed the action (agent id, user email, etc.)."""

    resource: str
    """What was acted on (tool name, file path, API endpoint, etc.)."""

    outcome: str
    """Result of the action: 'success' | 'failure' | 'denied' | custom."""

    metadata: dict
    """Arbitrary key-value context. Never include PII in this field."""

    ts: str
    """ISO-8601 UTC timestamp of the event."""

    prev_hash: str
    """SHA-256 hash of the immediately preceding record (same team)."""

    hash: str
    """SHA-256 hash of this record's canonical payload."""


# ── DB path resolution ───────────────────────────────────────────────────────

def _get_db_path() -> Path:
    """Resolve audit DB path from NUCLEUS_BRAIN_PATH or CWD auto-detect."""
    from .common import get_brain_path
    brain = get_brain_path()
    audit_dir = brain / ".brain" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir / "audit.db"


# ── Connection factory ───────────────────────────────────────────────────────

def _get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a thread-local SQLite connection, initialising schema on first use."""
    if db_path is None:
        db_path = _get_db_path()

    db_key = str(db_path)
    conn = getattr(_local, "conn", None)
    conn_key = getattr(_local, "conn_key", None)

    if conn is None or conn_key != db_key:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL mode for concurrent readers
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
        _local.conn_key = db_key

    # Schema init (once per process per DB path)
    with _DB_INIT_LOCK:
        if db_key not in _DB_INITIALIZED:
            conn.executescript(_DDL)
            conn.commit()
            _DB_INITIALIZED[db_key] = True

    return conn


# ── Hash computation ─────────────────────────────────────────────────────────

def _compute_hash(
    team_id: str,
    event_type: str,
    actor: str,
    resource: str,
    outcome: str,
    metadata: dict,
    ts: str,
    prev_hash: str,
) -> str:
    """Compute SHA-256 of the canonical JSON representation of a record.

    The canonical form is a deterministic JSON string with sorted keys so
    the hash is stable regardless of Python's dict ordering.
    """
    canonical = json.dumps(
        {
            "team_id": team_id,
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "outcome": outcome,
            "metadata": metadata,
            "ts": ts,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Core API ─────────────────────────────────────────────────────────────────

# Per-team insert lock to serialise chain updates
_team_locks: dict[str, threading.Lock] = {}
_team_locks_meta = threading.Lock()


def _get_team_lock(team_id: str) -> threading.Lock:
    with _team_locks_meta:
        if team_id not in _team_locks:
            _team_locks[team_id] = threading.Lock()
        return _team_locks[team_id]


def log_event(
    event_type: str,
    actor: str,
    resource: str,
    outcome: str,
    metadata: Optional[dict] = None,
    team_id: str = "default",
    ts: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> AuditRecord:
    """Append a tamper-evident audit event to the chain.

    Parameters
    ----------
    event_type:
        Category label, e.g. 'tool_call', 'config_change', 'login'.
    actor:
        Identity of the entity performing the action.
    resource:
        Thing being acted on (tool name, file, endpoint, etc.).
    outcome:
        'success' | 'failure' | 'denied' | any custom string.
    metadata:
        Arbitrary context dict. Avoid PII; keep it small.
    team_id:
        Tenant partition key. Defaults to 'default'.
    ts:
        ISO-8601 UTC timestamp. Defaults to now.
    db_path:
        Override DB path (for testing).

    Returns
    -------
    AuditRecord
        The fully-persisted record with hash and id populated.
    """
    meta = metadata or {}
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    conn = _get_conn(db_path)
    team_lock = _get_team_lock(team_id)

    with team_lock:
        # Fetch the most recent hash for this team (the chain tail)
        row = conn.execute(
            "SELECT hash FROM audit_records WHERE team_id=? ORDER BY id DESC LIMIT 1",
            (team_id,),
        ).fetchone()
        prev_hash = row["hash"] if row else _GENESIS_PREV_HASH

        # Compute new hash
        new_hash = _compute_hash(
            team_id=team_id,
            event_type=event_type,
            actor=actor,
            resource=resource,
            outcome=outcome,
            metadata=meta,
            ts=ts,
            prev_hash=prev_hash,
        )

        meta_json = json.dumps(meta, sort_keys=True)
        cursor = conn.execute(
            """
            INSERT INTO audit_records
                (team_id, event_type, actor, resource, outcome, metadata, ts, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (team_id, event_type, actor, resource, outcome, meta_json, ts, prev_hash, new_hash),
        )
        conn.commit()
        row_id = cursor.lastrowid

    return AuditRecord(
        id=row_id,
        team_id=team_id,
        event_type=event_type,
        actor=actor,
        resource=resource,
        outcome=outcome,
        metadata=meta,
        ts=ts,
        prev_hash=prev_hash,
        hash=new_hash,
    )


def query_audit(
    team_id: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    actor: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Optional[Path] = None,
) -> list[AuditRecord]:
    """Query audit records for a team with optional filters.

    Parameters
    ----------
    team_id:
        Tenant partition key. Pass '*' to query across all teams
        (admin use only — enforce ACL at the MCP tool layer).
    since:
        ISO-8601 lower bound on ts (inclusive).
    until:
        ISO-8601 upper bound on ts (inclusive).
    actor:
        Exact actor filter.
    event_type:
        Exact event_type filter.
    limit:
        Maximum records to return (default 100, max 1 000).
    offset:
        Pagination offset.

    Returns
    -------
    list[AuditRecord]
        Matching records ordered by ts ascending.
    """
    limit = min(int(limit), 1_000)
    conn = _get_conn(db_path)

    clauses = []
    params: list = []

    if team_id != "*":
        clauses.append("team_id = ?")
        params.append(team_id)

    if since:
        clauses.append("ts >= ?")
        params.append(since)

    if until:
        clauses.append("ts <= ?")
        params.append(until)

    if actor:
        clauses.append("actor = ?")
        params.append(actor)

    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params += [limit, offset]

    rows = conn.execute(
        f"SELECT * FROM audit_records {where} ORDER BY id ASC LIMIT ? OFFSET ?",
        params,
    ).fetchall()

    return [
        AuditRecord(
            id=r["id"],
            team_id=r["team_id"],
            event_type=r["event_type"],
            actor=r["actor"],
            resource=r["resource"],
            outcome=r["outcome"],
            metadata=json.loads(r["metadata"]),
            ts=r["ts"],
            prev_hash=r["prev_hash"],
            hash=r["hash"],
        )
        for r in rows
    ]


def verify_chain(
    team_id: str,
    db_path: Optional[Path] = None,
) -> tuple[bool, Optional[int]]:
    """Verify the hash chain integrity for a team.

    Reads every record in insertion order and re-derives each hash from
    the stored fields. If any hash mismatches, returns (False, record_id).

    Returns
    -------
    (True, None)
        Chain is intact.
    (False, broken_record_id)
        First record where the hash no longer matches the recomputed value.
    """
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM audit_records WHERE team_id=? ORDER BY id ASC",
        (team_id,),
    ).fetchall()

    prev_hash = _GENESIS_PREV_HASH
    for r in rows:
        expected = _compute_hash(
            team_id=r["team_id"],
            event_type=r["event_type"],
            actor=r["actor"],
            resource=r["resource"],
            outcome=r["outcome"],
            metadata=json.loads(r["metadata"]),
            ts=r["ts"],
            prev_hash=prev_hash,
        )
        if expected != r["hash"]:
            return False, r["id"]
        # Verify the stored prev_hash also matches what we tracked
        if r["prev_hash"] != prev_hash:
            return False, r["id"]
        prev_hash = r["hash"]

    return True, None
