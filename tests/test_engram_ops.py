"""
Tests for Engram Operations — Memory Ledger
============================================
Covers: write validation, query filtering, search, governance status, DSoR.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def brain_path(tmp_path):
    """Get the brain directory (created by conftest autouse fixture) and add subdirs."""
    brain = Path(os.environ["NUCLEAR_BRAIN_PATH"])
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "ledger" / "decisions").mkdir(parents=True, exist_ok=True)
    (brain / "ledger" / "snapshots").mkdir(parents=True, exist_ok=True)
    yield brain


def _write_engrams(brain_path, engrams):
    """Helper to write engrams directly to the ledger file."""
    ledger = brain_path / "engrams" / "ledger.jsonl"
    with open(ledger, "w", encoding="utf-8") as f:
        for e in engrams:
            f.write(json.dumps(e) + "\n")


def _parse_response(resp):
    """Parse a make_response JSON string."""
    return json.loads(resp)


# ── Write Engram Tests ────────────────────────────────────────

class TestWriteEngram:
    def test_rejects_empty_key(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        resp = _parse_response(_brain_write_engram_impl("", "val", "Feature", 5))
        assert resp["success"] is False
        assert "Security Violation" in resp["error"]

    def test_rejects_short_key(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        resp = _parse_response(_brain_write_engram_impl("x", "val", "Feature", 5))
        assert resp["success"] is False
        assert "at least 2 characters" in resp["error"]

    def test_rejects_invalid_key_chars(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        resp = _parse_response(_brain_write_engram_impl("bad key!", "val", "Feature", 5))
        assert resp["success"] is False
        assert "invalid characters" in resp["error"]

    def test_rejects_invalid_intensity_low(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        resp = _parse_response(_brain_write_engram_impl("valid_key", "val", "Feature", 0))
        assert resp["success"] is False
        assert "Intensity" in resp["error"]

    def test_rejects_invalid_intensity_high(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        resp = _parse_response(_brain_write_engram_impl("valid_key", "val", "Feature", 11))
        assert resp["success"] is False
        assert "Intensity" in resp["error"]

    def test_rejects_invalid_context(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        resp = _parse_response(_brain_write_engram_impl("valid_key", "val", "InvalidCtx", 5))
        assert resp["success"] is False
        assert "Context must be one of" in resp["error"]

    def test_accepts_all_valid_contexts(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.process.return_value = {"added": 1, "updated": 0, "skipped": 0, "mode": "ADD"}
        for ctx in ["Feature", "Architecture", "Brand", "Strategy", "Decision"]:
            with patch("mcp_server_nucleus.runtime.memory_pipeline.MemoryPipeline", mock_pipeline):
                resp = _parse_response(_brain_write_engram_impl(f"key_{ctx.lower()}", "val", ctx, 5))
                assert resp["success"] is True, f"Context '{ctx}' should be accepted"

    def test_successful_write_returns_data(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.process.return_value = {"added": 1, "updated": 0, "skipped": 0, "mode": "ADD"}
        with patch("mcp_server_nucleus.runtime.memory_pipeline.MemoryPipeline", mock_pipeline):
            resp = _parse_response(_brain_write_engram_impl("test_key", "test value", "Feature", 8))
            assert resp["success"] is True
            assert resp["data"]["key"] == "test_key"
            assert resp["data"]["intensity"] == 8
            assert resp["data"]["adun"]["mode"] == "ADD"

    def test_key_with_dots_and_hyphens(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.process.return_value = {"added": 1, "updated": 0, "skipped": 0, "mode": "ADD"}
        with patch("mcp_server_nucleus.runtime.memory_pipeline.MemoryPipeline", mock_pipeline):
            resp = _parse_response(_brain_write_engram_impl("my-key.v2", "val", "Feature", 5))
            assert resp["success"] is True


# ── Query Engram Tests ────────────────────────────────────────

class TestQueryEngrams:
    def test_empty_ledger_returns_empty(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1))
        assert resp["success"] is True
        assert resp["data"]["count"] == 0

    def test_filters_by_context(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [
            {"key": "k1", "value": "v1", "context": "Feature", "intensity": 5},
            {"key": "k2", "value": "v2", "context": "Strategy", "intensity": 5},
            {"key": "k3", "value": "v3", "context": "Feature", "intensity": 5},
        ])
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1))
        assert resp["data"]["count"] == 2

    def test_filters_by_min_intensity(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [
            {"key": "low", "value": "v", "context": "Feature", "intensity": 3},
            {"key": "high", "value": "v", "context": "Feature", "intensity": 8},
        ])
        resp = _parse_response(_brain_query_engrams_impl("Feature", 5))
        assert resp["data"]["count"] == 1
        assert resp["data"]["engrams"][0]["key"] == "high"

    def test_excludes_deleted(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [
            {"key": "alive", "value": "v", "context": "Feature", "intensity": 5},
            {"key": "dead", "value": "v", "context": "Feature", "intensity": 5, "deleted": True},
        ])
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1))
        assert resp["data"]["count"] == 1
        assert resp["data"]["engrams"][0]["key"] == "alive"

    def test_excludes_quarantined(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [
            {"key": "good", "value": "v", "context": "Feature", "intensity": 5},
            {"key": "bad", "value": "v", "context": "Feature", "intensity": 5, "quarantined": True},
        ])
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1))
        assert resp["data"]["count"] == 1

    def test_sorts_by_intensity_descending(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [
            {"key": "low", "value": "v", "context": "Feature", "intensity": 2},
            {"key": "high", "value": "v", "context": "Feature", "intensity": 9},
            {"key": "mid", "value": "v", "context": "Feature", "intensity": 5},
        ])
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1))
        intensities = [e["intensity"] for e in resp["data"]["engrams"]]
        assert intensities == [9, 5, 2]

    def test_limit_truncation(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        engrams = [{"key": f"k{i}", "value": "v", "context": "Feature", "intensity": 5} for i in range(10)]
        _write_engrams(brain_path, engrams)
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1, limit=3))
        assert resp["data"]["count"] == 3
        assert resp["data"]["total_matching"] == 10
        assert resp["data"]["truncated"] is True

    def test_limit_clamped_to_max_500(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [{"key": "k", "value": "v", "context": "Feature", "intensity": 5}])
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1, limit=9999))
        assert resp["data"]["limit"] == 500

    def test_case_insensitive_context(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        _write_engrams(brain_path, [
            {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
        ])
        resp = _parse_response(_brain_query_engrams_impl("feature", 1))
        assert resp["data"]["count"] == 1

    def test_skips_corrupted_json_lines(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write('{"key":"good","value":"v","context":"Feature","intensity":5}\n')
            f.write('CORRUPTED LINE\n')
            f.write('{"key":"also_good","value":"v","context":"Feature","intensity":5}\n')
        resp = _parse_response(_brain_query_engrams_impl("Feature", 1))
        assert resp["data"]["count"] == 2


# ── Search Engram Tests ───────────────────────────────────────

class TestSearchEngrams:
    def test_empty_ledger(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl
        resp = _parse_response(_brain_search_engrams_impl("anything"))
        assert resp["success"] is True
        assert resp["data"]["count"] == 0

    def test_matches_in_key(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl
        _write_engrams(brain_path, [
            {"key": "auth_module", "value": "handles login", "context": "Feature", "intensity": 5},
        ])
        resp = _parse_response(_brain_search_engrams_impl("auth"))
        assert resp["data"]["count"] == 1
        assert "key" in resp["data"]["engrams"][0]["_match_in"]

    def test_matches_in_value(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl
        _write_engrams(brain_path, [
            {"key": "module_x", "value": "handles authentication", "context": "Feature", "intensity": 5},
        ])
        resp = _parse_response(_brain_search_engrams_impl("authentication"))
        assert resp["data"]["count"] == 1
        assert "value" in resp["data"]["engrams"][0]["_match_in"]

    def test_case_insensitive_by_default(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl
        _write_engrams(brain_path, [
            {"key": "API_Gateway", "value": "Routes traffic", "context": "Architecture", "intensity": 5},
        ])
        resp = _parse_response(_brain_search_engrams_impl("api_gateway"))
        assert resp["data"]["count"] == 1

    def test_case_sensitive_when_enabled(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl
        _write_engrams(brain_path, [
            {"key": "API_Gateway", "value": "val", "context": "Architecture", "intensity": 5},
        ])
        resp = _parse_response(_brain_search_engrams_impl("api_gateway", case_sensitive=True))
        assert resp["data"]["count"] == 0
        resp = _parse_response(_brain_search_engrams_impl("API_Gateway", case_sensitive=True))
        assert resp["data"]["count"] == 1

    def test_excludes_deleted_and_quarantined(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl
        _write_engrams(brain_path, [
            {"key": "auth_a", "value": "v", "context": "Feature", "intensity": 5},
            {"key": "auth_b", "value": "v", "context": "Feature", "intensity": 5, "deleted": True},
            {"key": "auth_c", "value": "v", "context": "Feature", "intensity": 5, "quarantined": True},
        ])
        resp = _parse_response(_brain_search_engrams_impl("auth"))
        assert resp["data"]["count"] == 1


# ── Governance Status Tests ───────────────────────────────────

class TestGovernanceStatus:
    def test_returns_policies(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_governance_status_impl
        resp = _parse_response(_brain_governance_status_impl())
        assert resp["success"] is True
        assert resp["data"]["policies"]["default_deny"] is True

    def test_counts_audit_entries(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_governance_status_impl
        audit_path = brain_path / "ledger" / "interaction_log.jsonl"
        with open(audit_path, "w") as f:
            for i in range(5):
                f.write(json.dumps({"id": i}) + "\n")
        resp = _parse_response(_brain_governance_status_impl())
        assert resp["data"]["statistics"]["audit_log_entries"] == 5

    def test_counts_engrams(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_governance_status_impl
        _write_engrams(brain_path, [
            {"key": f"k{i}", "value": "v", "context": "Feature", "intensity": 5} for i in range(3)
        ])
        resp = _parse_response(_brain_governance_status_impl())
        assert resp["data"]["statistics"]["engram_count"] == 3

    def test_v9_security_flag(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_governance_status_impl
        os.environ["NUCLEUS_V9_SECURITY"] = "true"
        try:
            resp = _parse_response(_brain_governance_status_impl())
            assert resp["data"]["policies"]["immutable_audit"] is True
            assert resp["data"]["status"] == "ENFORCED"
        finally:
            os.environ.pop("NUCLEUS_V9_SECURITY", None)

    def test_partial_status_without_v9(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _brain_governance_status_impl
        os.environ.pop("NUCLEUS_V9_SECURITY", None)
        resp = _parse_response(_brain_governance_status_impl())
        assert resp["data"]["status"] == "PARTIAL"


# ── DSoR Tests ────────────────────────────────────────────────

class TestDSoR:
    def test_empty_decisions_ledger(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _dsor_query_decisions_impl
        resp = _parse_response(_dsor_query_decisions_impl())
        assert resp["success"] is True
        assert resp["data"]["count"] == 0

    def test_query_decisions_returns_reverse_chronological(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _dsor_query_decisions_impl
        decisions_path = brain_path / "ledger" / "decisions" / "decisions.jsonl"
        with open(decisions_path, "w") as f:
            f.write(json.dumps({"decision_id": "d1", "ts": "2024-01-01"}) + "\n")
            f.write(json.dumps({"decision_id": "d2", "ts": "2024-01-02"}) + "\n")
        resp = _parse_response(_dsor_query_decisions_impl())
        assert resp["data"]["count"] == 2
        assert resp["data"]["decisions"][0]["decision_id"] == "d2"

    def test_query_decisions_respects_limit(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _dsor_query_decisions_impl
        decisions_path = brain_path / "ledger" / "decisions" / "decisions.jsonl"
        with open(decisions_path, "w") as f:
            for i in range(10):
                f.write(json.dumps({"decision_id": f"d{i}"}) + "\n")
        resp = _parse_response(_dsor_query_decisions_impl(limit=3))
        assert resp["data"]["count"] == 3
        assert resp["data"]["truncated"] is True

    def test_get_trace_not_found(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _dsor_get_trace_impl
        resp = _parse_response(_dsor_get_trace_impl("nonexistent"))
        assert resp["success"] is False
        assert "not found" in resp["error"]

    def test_get_trace_found(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _dsor_get_trace_impl
        decisions_path = brain_path / "ledger" / "decisions" / "decisions.jsonl"
        with open(decisions_path, "w") as f:
            f.write(json.dumps({"decision_id": "d1", "context_hash": "abc123"}) + "\n")
        resp = _parse_response(_dsor_get_trace_impl("d1"))
        assert resp["success"] is True
        assert resp["data"]["trace"]["decision"]["decision_id"] == "d1"

    def test_get_trace_with_matching_snapshot(self, brain_path):
        from mcp_server_nucleus.runtime.engram_ops import _dsor_get_trace_impl
        decisions_path = brain_path / "ledger" / "decisions" / "decisions.jsonl"
        with open(decisions_path, "w") as f:
            f.write(json.dumps({"decision_id": "d1", "context_hash": "hash_abc"}) + "\n")
        snap_path = brain_path / "ledger" / "snapshots" / "snap1.json"
        with open(snap_path, "w") as f:
            json.dump({"state_hash": "hash_abc", "data": "snapshot_data"}, f)
        resp = _parse_response(_dsor_get_trace_impl("d1"))
        assert resp["data"]["trace"]["context_snapshot"]["state_hash"] == "hash_abc"
