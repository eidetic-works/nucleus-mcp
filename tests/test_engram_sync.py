"""Tests for brain content sync — local ↔ hosted engram synchronization.

Covers:
  - Sync endpoint (POST /engrams/sync): basic round-trip, conflict resolution,
    tenant isolation, incremental sync (since_timestamp), validation
  - Sync client (sync.py): local engram reading, sync state persistence,
    remote engram application, dry-run mode, status display
  - Conflict resolution: version > timestamp > intensity (deterministic)
  - Edge cases: empty brains, missing token, unreachable endpoint
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from starlette.testclient import TestClient
from starlette.middleware import Middleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    """Create an isolated brain directory and set NUCLEAR_BRAIN_PATH."""
    brain = tmp_path / "brain"
    brain.mkdir()
    (brain / "engrams").mkdir()
    (brain / "ledger").mkdir()
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(brain))
    return brain


@pytest.fixture
def tenant_brain(tmp_path, monkeypatch):
    """Create a brain dir structured for NucleusTenantMiddleware.

    The middleware resolves brain path as <NUCLEUS_BRAIN_ROOT>/<tenant_id>/.brain/
    So we set NUCLEUS_BRAIN_ROOT=tmp_path and NUCLEUS_TENANT_ID=test_tenant,
    giving us tmp_path/test_tenant/.brain/ as the brain path.
    """
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(tmp_path))
    monkeypatch.setenv("NUCLEUS_TENANT_ID", "test_tenant")
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "false")
    brain = tmp_path / "test_tenant" / ".brain"
    brain.mkdir(parents=True, exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(brain))
    return brain


@pytest.fixture
def sample_engram():
    """Return a valid engram record."""
    return {
        "key": "test_engram_001",
        "value": "This is a test engram about PostgreSQL architecture",
        "context": "Architecture",
        "intensity": 7,
        "version": 1,
        "source_agent": "test_agent",
        "op_type": "ADD",
        "timestamp": "2026-06-21T10:00:00Z",
        "deleted": False,
        "signature": None,
    }


@pytest.fixture
def sample_engram_v2():
    """Return v2 of the same engram (updated)."""
    return {
        "key": "test_engram_001",
        "value": "Updated engram about PostgreSQL architecture with more detail",
        "context": "Architecture",
        "intensity": 8,
        "version": 2,
        "source_agent": "test_agent",
        "op_type": "UPDATE",
        "timestamp": "2026-06-21T11:00:00Z",
        "deleted": False,
        "signature": None,
    }


def _write_engrams_to_ledger(brain_path: Path, engrams: list):
    """Write engram records to the ledger.jsonl file."""
    ledger = brain_path / "engrams" / "ledger.jsonl"
    with open(ledger, "a", encoding="utf-8") as f:
        for e in engrams:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Sync endpoint tests (POST /engrams/sync)
# ---------------------------------------------------------------------------


class TestEngramSyncEndpoint:
    """Tests for the hosted sync endpoint."""

    @pytest.fixture
    def app_with_sync(self, tenant_brain, monkeypatch):
        """Create a test app with sync routes + tenant middleware."""
        from mcp_server_nucleus.http_transport.engram_sync_route import (
            engram_sync_route,
            engram_sync_status_route,
        )
        from starlette.applications import Starlette
        from starlette.routing import Route
        from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware

        app = Starlette(
            routes=[engram_sync_route, engram_sync_status_route],
            middleware=[Middleware(NucleusTenantMiddleware)],
        )
        return app

    def test_sync_empty_local_to_empty_hosted(self, app_with_sync, tenant_brain):
        """Sync with no local engrams and no hosted engrams → synced=true, 0 counts."""
        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [],
            "local_sync_state": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced"] is True
        assert data["synced_count"] == 0
        assert data["remote_count"] == 0

    def test_sync_pushes_local_to_hosted(self, app_with_sync, tenant_brain, sample_engram):
        """Local engrams are pushed to hosted ledger."""
        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [sample_engram],
            "local_sync_state": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["synced_count"] == 1
        assert data["conflict_count"] == 0

        # Verify engram was written to hosted ledger
        hosted_ledger = tenant_brain / "engrams" / "ledger.jsonl"
        assert hosted_ledger.exists()
        lines = hosted_ledger.read_text().strip().split("\n")
        assert len(lines) == 1
        written = json.loads(lines[0])
        assert written["key"] == sample_engram["key"]

    def test_sync_returns_hosted_engrams_to_local(self, app_with_sync, tenant_brain, sample_engram):
        """Hosted engrams that local doesn't have are returned."""
        # Pre-populate hosted ledger
        _write_engrams_to_ledger(tenant_brain, [sample_engram])

        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [],  # local has nothing
            "local_sync_state": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["remote_count"] == 1
        assert data["remote_engrams"][0]["key"] == sample_engram["key"]

    def test_conflict_resolution_version_wins(self, app_with_sync, tenant_brain, sample_engram, sample_engram_v2):
        """Higher version wins conflict resolution."""
        # Hosted has v1
        _write_engrams_to_ledger(tenant_brain, [sample_engram])

        client = TestClient(app_with_sync)
        # Local pushes v2
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [sample_engram_v2],
            "local_sync_state": {},
        })
        data = resp.json()
        assert data["synced_count"] == 1  # v2 applied to hosted
        assert data["conflict_count"] == 1
        assert data["conflicts"][0]["resolution"] == "local_wins"

    def test_conflict_resolution_remote_wins(self, app_with_sync, tenant_brain, sample_engram, sample_engram_v2):
        """Remote higher version is returned to local, not overwritten."""
        # Hosted has v2
        _write_engrams_to_ledger(tenant_brain, [sample_engram_v2])

        client = TestClient(app_with_sync)
        # Local pushes v1 (older)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [sample_engram],
            "local_sync_state": {},
        })
        data = resp.json()
        assert data["synced_count"] == 0  # v1 NOT applied (remote v2 wins)
        assert data["conflict_count"] == 1
        assert data["conflicts"][0]["resolution"] == "remote_wins"
        # Remote v2 should be in remote_engrams
        assert data["remote_count"] == 1
        assert data["remote_engrams"][0]["version"] == 2

    def test_noop_on_identical_engrams(self, app_with_sync, tenant_brain, sample_engram):
        """Identical engrams (same version + timestamp + intensity) → noop."""
        _write_engrams_to_ledger(tenant_brain, [sample_engram])

        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [sample_engram],
            "local_sync_state": {},
        })
        data = resp.json()
        assert data["synced_count"] == 0
        assert data["conflict_count"] == 1
        assert data["conflicts"][0]["resolution"] == "noop"

    def test_incremental_sync_since_timestamp(self, app_with_sync, tenant_brain):
        """since_timestamp filters remote_engrams to only newer ones."""
        old_engram = {
            "key": "old_001", "value": "old", "context": "Decision",
            "intensity": 5, "version": 1, "source_agent": "test",
            "op_type": "ADD", "timestamp": "2026-06-20T10:00:00Z",
            "deleted": False, "signature": None,
        }
        new_engram = {
            "key": "new_001", "value": "new", "context": "Decision",
            "intensity": 5, "version": 1, "source_agent": "test",
            "op_type": "ADD", "timestamp": "2026-06-21T10:00:00Z",
            "deleted": False, "signature": None,
        }
        _write_engrams_to_ledger(tenant_brain, [old_engram, new_engram])

        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": "2026-06-20T12:00:00Z",  # after old, before new
            "local_engrams": [],
            "local_sync_state": {},
        })
        data = resp.json()
        # Only new_engram should be returned (old is before since_timestamp)
        keys = [e["key"] for e in data["remote_engrams"]]
        assert "new_001" in keys
        assert "old_001" not in keys

    def test_validation_rejects_invalid_engram(self, app_with_sync, tenant_brain):
        """Invalid engram records are rejected with schema_violation."""
        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [{"key": "x"}],  # missing version, timestamp
            "local_sync_state": {},
        })
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "schema_violation"

    def test_validation_rejects_bad_context(self, app_with_sync, tenant_brain):
        """Invalid context value is rejected."""
        client = TestClient(app_with_sync)
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [{
                "key": "test_001", "value": "test", "context": "InvalidContext",
                "intensity": 5, "version": 1, "source_agent": "test",
                "op_type": "ADD", "timestamp": "2026-06-21T10:00:00Z",
                "deleted": False, "signature": None,
            }],
            "local_sync_state": {},
        })
        assert resp.status_code == 400

    def test_status_endpoint(self, app_with_sync, tenant_brain, sample_engram):
        """GET /engrams/sync/status returns hosted brain state."""
        _write_engrams_to_ledger(tenant_brain, [sample_engram])
        client = TestClient(app_with_sync)
        resp = client.get("/engrams/sync/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["engram_count"] == 1

    def test_body_too_large_rejected(self, app_with_sync, tenant_brain, monkeypatch):
        """Oversized request body is rejected."""
        # Patch MAX_BODY_BYTES at module level (avoid importlib.reload which
        # permanently changes the module for subsequent tests)
        import mcp_server_nucleus.http_transport.engram_sync_route as mod
        monkeypatch.setattr(mod, "MAX_BODY_BYTES", 100)

        client = TestClient(app_with_sync)
        big_payload = {"since_timestamp": None, "local_engrams": [], "local_sync_state": {}}
        big_payload["padding"] = "x" * 200
        resp = client.post("/engrams/sync", json=big_payload)
        assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Sync client tests (sync.py)
# ---------------------------------------------------------------------------


class TestSyncClient:
    """Tests for the sync client logic."""

    def test_read_local_engrams_empty(self, isolated_brain):
        """Reading engrams from empty brain returns []."""
        from mcp_server_nucleus.sync import _read_local_engrams
        result = _read_local_engrams(isolated_brain)
        assert result == []

    def test_read_local_engrams_returns_latest_version(self, isolated_brain, sample_engram, sample_engram_v2):
        """Reading returns only the latest version per key."""
        _write_engrams_to_ledger(isolated_brain, [sample_engram, sample_engram_v2])
        from mcp_server_nucleus.sync import _read_local_engrams
        result = _read_local_engrams(isolated_brain)
        assert len(result) == 1
        assert result[0]["version"] == 2

    def test_sync_state_load_empty(self, isolated_brain):
        """Loading sync state from non-existent file returns defaults."""
        from mcp_server_nucleus.sync import _load_sync_state
        state = _load_sync_state(isolated_brain)
        assert state["last_sync_timestamp"] is None
        assert state["sync_count"] == 0

    def test_sync_state_save_and_load(self, isolated_brain):
        """Sync state persists across save/load."""
        from mcp_server_nucleus.sync import _save_sync_state, _load_sync_state
        state = {
            "last_sync_timestamp": "2026-06-21T10:00:00Z",
            "sync_count": 5,
            "last_sync_at": "2026-06-21T10:05:00Z",
        }
        _save_sync_state(isolated_brain, state)
        loaded = _load_sync_state(isolated_brain)
        assert loaded["last_sync_timestamp"] == "2026-06-21T10:00:00Z"
        assert loaded["sync_count"] == 5

    def test_apply_remote_engrams_dry_run(self, isolated_brain, sample_engram):
        """Dry run doesn't write to ledger."""
        from mcp_server_nucleus.sync import _apply_remote_engrams
        applied, skipped = _apply_remote_engrams(
            [sample_engram], isolated_brain, dry_run=True
        )
        assert applied == 1
        assert skipped == 0
        # Ledger should NOT exist (dry run)
        assert not (isolated_brain / "engrams" / "ledger.jsonl").exists()

    def test_apply_remote_engrams_writes(self, isolated_brain, sample_engram):
        """Real apply writes to local ledger via ADUN pipeline."""
        from mcp_server_nucleus.sync import _apply_remote_engrams
        applied, skipped = _apply_remote_engrams(
            [sample_engram], isolated_brain, dry_run=False
        )
        assert applied == 1
        # Ledger should exist with the engram
        ledger = isolated_brain / "engrams" / "ledger.jsonl"
        assert ledger.exists()

    def test_get_sync_url_default(self):
        """Default sync URL is relay.nucleusos.dev."""
        from mcp_server_nucleus.sync import _get_sync_url, DEFAULT_SYNC_URL
        assert _get_sync_url(None) == DEFAULT_SYNC_URL

    def test_get_sync_url_explicit(self):
        """Explicit URL overrides env."""
        from mcp_server_nucleus.sync import _get_sync_url
        assert _get_sync_url("https://custom.example.com/sync") == "https://custom.example.com/sync"

    def test_get_sync_url_env(self, monkeypatch):
        """NUCLEUS_SYNC_URL env var is respected."""
        monkeypatch.setenv("NUCLEUS_SYNC_URL", "https://env.example.com/sync")
        from mcp_server_nucleus.sync import _get_sync_url
        assert _get_sync_url(None) == "https://env.example.com/sync"

    def test_perform_sync_no_token_fails(self, isolated_brain, monkeypatch):
        """Sync without token returns error code 1."""
        monkeypatch.delenv("NUCLEUS_SYNC_TOKEN", raising=False)
        monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
        from mcp_server_nucleus.sync import perform_sync
        result = perform_sync(dry_run=False)
        assert result == 1

    def test_perform_sync_dry_run_succeeds(self, isolated_brain, sample_engram, monkeypatch):
        """Dry run sync succeeds without network calls."""
        _write_engrams_to_ledger(isolated_brain, [sample_engram])
        from mcp_server_nucleus.sync import perform_sync
        result = perform_sync(dry_run=True, verbose=True)
        assert result == 0

    def test_show_sync_status(self, isolated_brain, monkeypatch):
        """Status display works on fresh brain."""
        monkeypatch.setenv("NUCLEUS_SYNC_TOKEN", "test_token")
        from mcp_server_nucleus.sync import show_sync_status
        result = show_sync_status()
        assert result == 0


# ---------------------------------------------------------------------------
# Conflict resolution unit tests
# ---------------------------------------------------------------------------


class TestConflictResolution:
    """Unit tests for the deterministic conflict resolution logic."""

    def test_higher_version_wins(self):
        from mcp_server_nucleus.http_transport.engram_sync_route import _engram_rank
        v1 = {"version": 1, "timestamp": "2026-06-21T10:00:00Z", "intensity": 5}
        v2 = {"version": 2, "timestamp": "2026-06-21T10:00:00Z", "intensity": 5}
        assert _engram_rank(v2) > _engram_rank(v1)

    def test_same_version_later_timestamp_wins(self):
        from mcp_server_nucleus.http_transport.engram_sync_route import _engram_rank
        earlier = {"version": 1, "timestamp": "2026-06-21T10:00:00Z", "intensity": 5}
        later = {"version": 1, "timestamp": "2026-06-21T11:00:00Z", "intensity": 5}
        assert _engram_rank(later) > _engram_rank(earlier)

    def test_same_version_timestamp_higher_intensity_wins(self):
        from mcp_server_nucleus.http_transport.engram_sync_route import _engram_rank
        low = {"version": 1, "timestamp": "2026-06-21T10:00:00Z", "intensity": 3}
        high = {"version": 1, "timestamp": "2026-06-21T10:00:00Z", "intensity": 9}
        assert _engram_rank(high) > _engram_rank(low)

    def test_identical_engrams_are_equal(self):
        from mcp_server_nucleus.http_transport.engram_sync_route import _engram_rank
        e1 = {"version": 1, "timestamp": "2026-06-21T10:00:00Z", "intensity": 5}
        e2 = {"version": 1, "timestamp": "2026-06-21T10:00:00Z", "intensity": 5}
        assert _engram_rank(e1) == _engram_rank(e2)

    def test_version_beats_timestamp(self):
        """Version takes precedence over timestamp."""
        from mcp_server_nucleus.http_transport.engram_sync_route import _engram_rank
        v1_late = {"version": 1, "timestamp": "2026-06-22T10:00:00Z", "intensity": 5}
        v2_early = {"version": 2, "timestamp": "2026-06-21T10:00:00Z", "intensity": 5}
        assert _engram_rank(v2_early) > _engram_rank(v1_late)


# ---------------------------------------------------------------------------
# Round-trip integration test
# ---------------------------------------------------------------------------


class TestSyncRoundTrip:
    """End-to-end: local → hosted → local round-trip preserves engrams."""

    def test_round_trip_preserves_engrams(self, tenant_brain, sample_engram, monkeypatch):
        """Engram pushed to hosted and pulled back is identical."""
        from mcp_server_nucleus.http_transport.engram_sync_route import (
            engram_sync_route,
            engram_sync_status_route,
        )
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.middleware import Middleware
        from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware

        app = Starlette(
            routes=[engram_sync_route, engram_sync_status_route],
            middleware=[Middleware(NucleusTenantMiddleware)],
        )
        client = TestClient(app)

        # Phase 1: Push local engram to hosted
        resp = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [sample_engram],
            "local_sync_state": {},
        })
        assert resp.json()["synced_count"] == 1

        # Phase 2: Simulate a second local brain (empty) syncing with hosted
        # The hosted brain is at tenant_brain; we just sync with empty local
        resp2 = client.post("/engrams/sync", json={
            "since_timestamp": None,
            "local_engrams": [],
            "local_sync_state": {},
        })
        data2 = resp2.json()
        assert data2["remote_count"] == 1
        received = data2["remote_engrams"][0]
        assert received["key"] == sample_engram["key"]
        assert received["value"] == sample_engram["value"]
        assert received["version"] == sample_engram["version"]
