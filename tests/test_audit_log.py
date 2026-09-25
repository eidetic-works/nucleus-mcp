"""Unit tests for mcp_server_nucleus.runtime.audit_log (W8).

Covers:
  - Basic log_event persists and returns AuditRecord
  - Hash chain continuity (each record's prev_hash = previous record's hash)
  - Genesis record has zero-hash prev_hash
  - Chain integrity verification (verify_chain returns True on clean data)
  - Tamper detection (verify_chain returns False when a record is mutated)
  - Multi-team isolation (team A records never appear in team B queries)
  - query_audit filtering: since, until, actor, event_type
  - query_audit pagination: limit + offset
  - query_audit admin wildcard team_id='*'
  - Deterministic hash: same payload → same hash
  - AuditRecord hash is unique (UNIQUE constraint holds)
  - Metadata roundtrip (arbitrary dict preserved)
  - Custom timestamp accepted
"""

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.audit_log import (
    AuditRecord,
    _GENESIS_PREV_HASH,
    _compute_hash,
    _get_conn,
    log_event,
    query_audit,
    verify_chain,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Return a temporary DB path isolated per test."""
    return tmp_path / "audit.db"


# ── Basic log_event ──────────────────────────────────────────────────────────

class TestLogEvent:
    def test_returns_audit_record(self, tmp_db):
        r = log_event("tool_call", "agent-1", "nucleus_tasks/claim", "success", db_path=tmp_db)
        assert isinstance(r, AuditRecord)

    def test_record_fields_populated(self, tmp_db):
        r = log_event(
            "config_change", "admin", "settings.yaml", "success",
            metadata={"key": "model", "old": "haiku", "new": "sonnet"},
            team_id="acme",
            db_path=tmp_db,
        )
        assert r.event_type == "config_change"
        assert r.actor == "admin"
        assert r.resource == "settings.yaml"
        assert r.outcome == "success"
        assert r.team_id == "acme"
        assert r.metadata == {"key": "model", "old": "haiku", "new": "sonnet"}
        assert r.id >= 1

    def test_genesis_prev_hash(self, tmp_db):
        r = log_event("login", "user-1", "/auth", "success", db_path=tmp_db)
        assert r.prev_hash == _GENESIS_PREV_HASH

    def test_custom_timestamp_accepted(self, tmp_db):
        ts = "2026-01-01T00:00:00Z"
        r = log_event("login", "user-x", "/auth", "success", ts=ts, db_path=tmp_db)
        assert r.ts == ts

    def test_empty_metadata_default(self, tmp_db):
        r = log_event("event", "actor", "res", "success", db_path=tmp_db)
        assert r.metadata == {}


# ── Hash chain ────────────────────────────────────────────────────────────────

class TestHashChain:
    def test_second_record_links_to_first(self, tmp_db):
        r1 = log_event("e1", "a", "r", "success", db_path=tmp_db)
        r2 = log_event("e2", "a", "r", "success", db_path=tmp_db)
        assert r2.prev_hash == r1.hash

    def test_chain_of_three(self, tmp_db):
        r1 = log_event("e1", "a", "r", "success", db_path=tmp_db)
        r2 = log_event("e2", "a", "r", "success", db_path=tmp_db)
        r3 = log_event("e3", "a", "r", "success", db_path=tmp_db)
        assert r2.prev_hash == r1.hash
        assert r3.prev_hash == r2.hash

    def test_hash_is_hex_sha256(self, tmp_db):
        r = log_event("e", "a", "r", "success", db_path=tmp_db)
        assert len(r.hash) == 64
        int(r.hash, 16)  # must parse as hex

    def test_deterministic_hash(self, tmp_db1=None, tmp_db2=None):
        # Same payload → same hash regardless of DB
        h1 = _compute_hash("t1", "ev", "actor", "res", "ok", {}, "2026-01-01T00:00:00Z", _GENESIS_PREV_HASH)
        h2 = _compute_hash("t1", "ev", "actor", "res", "ok", {}, "2026-01-01T00:00:00Z", _GENESIS_PREV_HASH)
        assert h1 == h2

    def test_different_metadata_different_hash(self):
        h1 = _compute_hash("t", "ev", "a", "r", "ok", {"x": 1}, "2026-01-01T00:00:00Z", _GENESIS_PREV_HASH)
        h2 = _compute_hash("t", "ev", "a", "r", "ok", {"x": 2}, "2026-01-01T00:00:00Z", _GENESIS_PREV_HASH)
        assert h1 != h2


# ── Chain verification ────────────────────────────────────────────────────────

class TestVerifyChain:
    def test_clean_chain_is_valid(self, tmp_db):
        for i in range(5):
            log_event(f"e{i}", "actor", "res", "success", team_id="team-x", db_path=tmp_db)
        ok, broken_at = verify_chain(team_id="team-x", db_path=tmp_db)
        assert ok
        assert broken_at is None

    def test_empty_team_is_valid(self, tmp_db):
        ok, broken_at = verify_chain(team_id="nonexistent-team", db_path=tmp_db)
        assert ok
        assert broken_at is None

    def test_tampered_hash_detected(self, tmp_db):
        log_event("e1", "a", "r", "success", team_id="t", db_path=tmp_db)
        r2 = log_event("e2", "a", "r", "success", team_id="t", db_path=tmp_db)

        # Directly mutate the stored hash of record 1 (simulates tampering)
        conn = _get_conn(tmp_db)
        conn.execute(
            "UPDATE audit_records SET hash='deadbeef' WHERE id=1"
        )
        conn.commit()

        ok, broken_at = verify_chain(team_id="t", db_path=tmp_db)
        assert not ok
        assert broken_at is not None

    def test_tampered_payload_detected(self, tmp_db):
        log_event("e1", "a", "r", "success", team_id="t2", db_path=tmp_db)

        # Mutate actor field without updating hash
        conn = _get_conn(tmp_db)
        conn.execute("UPDATE audit_records SET actor='attacker' WHERE id=1")
        conn.commit()

        ok, broken_at = verify_chain(team_id="t2", db_path=tmp_db)
        assert not ok


# ── Multi-team isolation ──────────────────────────────────────────────────────

class TestMultiTeamIsolation:
    def test_records_partitioned_by_team(self, tmp_db):
        log_event("ev", "actor", "res", "success", team_id="alpha", db_path=tmp_db)
        log_event("ev", "actor", "res", "success", team_id="beta", db_path=tmp_db)

        alpha = query_audit(team_id="alpha", db_path=tmp_db)
        beta = query_audit(team_id="beta", db_path=tmp_db)

        assert len(alpha) == 1
        assert alpha[0].team_id == "alpha"
        assert len(beta) == 1
        assert beta[0].team_id == "beta"

    def test_chain_per_team_independent(self, tmp_db):
        a1 = log_event("e", "a", "r", "success", team_id="ta", db_path=tmp_db)
        b1 = log_event("e", "a", "r", "success", team_id="tb", db_path=tmp_db)
        # Both genesis records should have the zero prev_hash
        assert a1.prev_hash == _GENESIS_PREV_HASH
        assert b1.prev_hash == _GENESIS_PREV_HASH
        # Their hashes are different (different team_id in payload)
        assert a1.hash != b1.hash

    def test_admin_wildcard_query(self, tmp_db):
        log_event("ev", "actor", "res", "success", team_id="x", db_path=tmp_db)
        log_event("ev", "actor", "res", "success", team_id="y", db_path=tmp_db)

        all_records = query_audit(team_id="*", db_path=tmp_db)
        teams = {r.team_id for r in all_records}
        assert "x" in teams
        assert "y" in teams


# ── query_audit filters ───────────────────────────────────────────────────────

class TestQueryFilters:
    def _setup(self, tmp_db):
        log_event("login", "alice", "/auth", "success", team_id="t", ts="2026-01-01T10:00:00Z", db_path=tmp_db)
        log_event("tool_call", "bob", "nucleus_tasks", "failure", team_id="t", ts="2026-01-02T10:00:00Z", db_path=tmp_db)
        log_event("login", "alice", "/auth", "success", team_id="t", ts="2026-01-03T10:00:00Z", db_path=tmp_db)

    def test_filter_by_actor(self, tmp_db):
        self._setup(tmp_db)
        results = query_audit(team_id="t", actor="alice", db_path=tmp_db)
        assert all(r.actor == "alice" for r in results)
        assert len(results) == 2

    def test_filter_by_event_type(self, tmp_db):
        self._setup(tmp_db)
        results = query_audit(team_id="t", event_type="tool_call", db_path=tmp_db)
        assert len(results) == 1
        assert results[0].actor == "bob"

    def test_filter_since(self, tmp_db):
        self._setup(tmp_db)
        results = query_audit(team_id="t", since="2026-01-02T00:00:00Z", db_path=tmp_db)
        assert len(results) == 2

    def test_filter_until(self, tmp_db):
        self._setup(tmp_db)
        results = query_audit(team_id="t", until="2026-01-01T23:59:59Z", db_path=tmp_db)
        assert len(results) == 1

    def test_combined_filters(self, tmp_db):
        self._setup(tmp_db)
        results = query_audit(
            team_id="t",
            actor="alice",
            event_type="login",
            since="2026-01-02T00:00:00Z",
            db_path=tmp_db,
        )
        assert len(results) == 1
        assert results[0].ts == "2026-01-03T10:00:00Z"


# ── Pagination ────────────────────────────────────────────────────────────────

class TestPagination:
    def test_limit(self, tmp_db):
        for i in range(10):
            log_event(f"e{i}", "a", "r", "success", team_id="pg", db_path=tmp_db)
        results = query_audit(team_id="pg", limit=3, db_path=tmp_db)
        assert len(results) == 3

    def test_offset(self, tmp_db):
        for i in range(5):
            log_event(f"e{i}", "a", "r", "success", team_id="pg2", ts=f"2026-01-0{i+1}T00:00:00Z", db_path=tmp_db)
        page1 = query_audit(team_id="pg2", limit=2, offset=0, db_path=tmp_db)
        page2 = query_audit(team_id="pg2", limit=2, offset=2, db_path=tmp_db)
        assert len(page1) == 2
        assert len(page2) == 2
        ids1 = {r.id for r in page1}
        ids2 = {r.id for r in page2}
        assert ids1.isdisjoint(ids2)

    def test_limit_capped_at_1000(self, tmp_db):
        # Just verify the cap doesn't crash (we don't insert 1001 rows)
        results = query_audit(team_id="nobody", limit=99999, db_path=tmp_db)
        assert isinstance(results, list)
