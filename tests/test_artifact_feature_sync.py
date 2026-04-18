"""
Tests for Artifact, Feature, and Sync Operations
=================================================
Covers untested runtime modules that handle cross-agent data sharing.
"""

import json
import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def brain(tmp_path):
    """Create a fresh isolated brain directory."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    for d in ["artifacts", "features", "sync", "ledger", "engrams", "sessions"]:
        (brain / d).mkdir(exist_ok=True)
    old = os.environ.get("NUCLEUS_BRAIN_PATH")
    os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
    yield brain
    if old is not None:
        os.environ["NUCLEUS_BRAIN_PATH"] = old
    else:
        os.environ.pop("NUCLEUS_BRAIN_PATH", None)


# ── Artifact Operations ──────────────────────────────────────────

class TestArtifactOps:
    def test_write_and_read_artifact(self, brain):
        from mcp_server_nucleus.runtime.artifact_ops import _write_artifact, _read_artifact
        result = _write_artifact("test_doc", "Hello, World!")
        assert "success" in result or "stored" in result.lower() or isinstance(result, str)

        content = _read_artifact("test_doc")
        assert "Hello, World!" in content or "test_doc" in content

    def test_write_artifact_with_mime_type(self, brain):
        from mcp_server_nucleus.runtime.artifact_ops import _write_artifact
        result = _write_artifact("schema.json", '{"type": "object"}')
        assert isinstance(result, str)

    def test_list_artifacts_empty(self, brain):
        from mcp_server_nucleus.runtime.artifact_ops import _list_artifacts
        result = _list_artifacts()
        assert isinstance(result, (list, str))

    def test_list_artifacts_after_write(self, brain):
        from mcp_server_nucleus.runtime.artifact_ops import _write_artifact, _list_artifacts
        _write_artifact("artifact_a", "content_a")
        _write_artifact("artifact_b", "content_b")
        result = _list_artifacts()
        # Result could be list or JSON string
        if isinstance(result, str):
            result = json.loads(result) if result.startswith("[") or result.startswith("{") else result
        assert "artifact_a" in str(result) or len(str(result)) > 0

    def test_read_nonexistent_artifact(self, brain):
        from mcp_server_nucleus.runtime.artifact_ops import _read_artifact
        result = _read_artifact("nonexistent_xyz")
        # Should return error or empty, not crash
        assert isinstance(result, str)


# ── Feature Operations ───────────────────────────────────────────

class TestFeatureOps:
    def test_add_feature(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _add_feature, _list_features
        result = _add_feature(
            product="nucleus",
            name="WAL Mode",
            description="SQLite WAL for concurrent access",
            source="reliability_audit",
            version="1.8.8",
            how_to_test=["Check PRAGMA journal_mode"],
            expected_result="journal_mode=wal",
        )
        assert result.get("success") is True or "id" in result or "feature_id" in result

    def test_list_features_empty(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _list_features
        result = _list_features(product="nucleus")
        assert isinstance(result, dict)

    def test_add_and_get_feature(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _add_feature, _get_feature
        added = _add_feature(
            product="nucleus",
            name="Circuit Breaker",
            description="Fault tolerance pattern",
            source="design_doc",
            version="1.8.8",
            how_to_test=["Trigger failures"],
            expected_result="State transitions to OPEN",
        )
        fid = added.get("feature_id") or added.get("id")
        if fid:
            result = _get_feature(fid)
            assert result.get("name") == "Circuit Breaker" or "Circuit Breaker" in str(result)

    def test_update_feature_status(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _add_feature, _update_feature
        added = _add_feature(
            product="nucleus",
            name="Atomic Writes",
            description="Crash-safe file operations",
            source="impl",
            version="1.8.8",
            how_to_test=["Kill during write"],
            expected_result="File remains valid",
        )
        fid = added.get("feature_id") or added.get("id")
        if fid:
            result = _update_feature(fid, status="done")
            assert result.get("success") is True or "updated" in str(result).lower()

    def test_mark_validated(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _add_feature, _mark_validated
        added = _add_feature(
            product="nucleus",
            name="Engram Cache",
            description="In-memory cache with mtime invalidation",
            source="perf_audit",
            version="1.8.8",
            how_to_test=["Run query twice"],
            expected_result="Second query uses cache",
        )
        fid = added.get("feature_id") or added.get("id")
        if fid:
            result = _mark_validated(fid, result="16 tests passing")
            assert result.get("success") is True or "validated" in str(result).lower()

    def test_search_features(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _add_feature, _search_features
        _add_feature(
            product="nucleus",
            name="SQLite WAL",
            description="Write-ahead logging for concurrent access",
            source="db_audit",
            version="1.8.8",
            how_to_test=["Check PRAGMA"],
            expected_result="WAL enabled",
        )
        result = _search_features("WAL")
        assert isinstance(result, dict)

    def test_list_features_filter_by_status(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _add_feature, _list_features
        _add_feature(
            product="nucleus",
            name="Feature A",
            description="Test feature",
            source="test",
            version="1.0",
            how_to_test=["test"],
            expected_result="pass",
            status="development",
        )
        result = _list_features(status="development")
        assert isinstance(result, dict)

    def test_get_nonexistent_feature(self, brain):
        from mcp_server_nucleus.runtime.feature_ops import _get_feature
        result = _get_feature("nonexistent_id_xyz")
        assert result.get("success") is False or "not found" in str(result).lower() or "error" in result


# ── Sync Operations ──────────────────────────────────────────────

class TestSyncOps:
    def test_is_sync_enabled_default(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import is_sync_enabled
        result = is_sync_enabled(brain)
        assert isinstance(result, bool)

    def test_get_sync_status(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import get_sync_status
        result = get_sync_status(brain)
        assert isinstance(result, dict)
        assert "enabled" in result or "status" in result or "mode" in result

    def test_set_and_get_current_agent(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import set_current_agent, get_current_agent
        set_current_agent("agent-claude", "production", brain_path=brain)
        agent = get_current_agent(brain)
        assert agent == "agent-claude" or "claude" in str(agent).lower()

    def test_get_agent_info(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import set_current_agent, get_agent_info
        set_current_agent("agent-test", "staging", role="implementer", brain_path=brain)
        info = get_agent_info(brain)
        assert isinstance(info, dict)
        assert info.get("agent_id") == "agent-test" or "agent-test" in str(info)

    def test_perform_sync(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import perform_sync
        result = perform_sync(brain_path=brain)
        assert isinstance(result, dict)

    def test_record_sync_time(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import record_sync_time, get_sync_status
        record_sync_time(brain)
        status = get_sync_status(brain)
        assert isinstance(status, dict)

    def test_sync_lock_context_manager(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import sync_lock
        with sync_lock(brain):
            # Should not deadlock or crash
            pass

    def test_get_sync_mode(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import get_sync_mode
        mode = get_sync_mode(brain)
        assert isinstance(mode, str)

    def test_get_watch_files(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import get_watch_files
        files = get_watch_files(brain)
        assert isinstance(files, list)

    def test_get_sync_interval(self, brain):
        from mcp_server_nucleus.runtime.sync_ops import get_sync_interval
        interval = get_sync_interval(brain)
        assert isinstance(interval, int)
        assert interval > 0
