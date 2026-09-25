"""Comprehensive tests for runtime/health_ops.py."""
import json
import platform
import sys
import time
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.health_ops import (
    _brain_health_impl,
    _brain_health_impl_legacy,
    _brain_version_impl,
    _brain_audit_log_impl,
    _get_version,
    _get_mcp,
    _get_start_time,
    _make_response,
)


# ── Helper functions ─────────────────────────────────────────────

class TestHelpers:
    def test_get_version(self):
        v = _get_version()
        assert isinstance(v, str)

    def test_get_mcp(self):
        mcp = _get_mcp()
        assert mcp is not None

    def test_get_start_time(self):
        st = _get_start_time()
        assert isinstance(st, float)
        assert st > 0

    def test_make_response_success(self):
        resp = _make_response(True, data={"key": "val"})
        parsed = json.loads(resp)
        assert parsed["success"] is True
        assert parsed["data"] == {"key": "val"}

    def test_make_response_error(self):
        resp = _make_response(False, error="something went wrong")
        parsed = json.loads(resp)
        assert parsed["success"] is False
        assert parsed["error"] == "something went wrong"

    def test_make_response_both(self):
        resp = _make_response(True, data="ok", error="warn")
        parsed = json.loads(resp)
        assert parsed["success"] is True
        assert parsed["data"] == "ok"
        assert parsed["error"] == "warn"

    def test_make_response_neither(self):
        resp = _make_response(True)
        parsed = json.loads(resp)
        assert parsed["success"] is True


# ── _brain_health_impl ───────────────────────────────────────────

class TestBrainHealthImpl:
    def test_returns_healthy_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _brain_health_impl()
        data = json.loads(result)
        assert data["status"] == "healthy"
        assert "version" in data
        assert "tools_registered" in data
        assert "brain_path" in data
        assert "uptime_seconds" in data
        assert "python_version" in data

    def test_brain_path_in_response(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _brain_health_impl()
        data = json.loads(result)
        assert str(tmp_path) in data["brain_path"] or data["brain_path"] == str(tmp_path.resolve())

    def test_python_version_matches(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _brain_health_impl()
        data = json.loads(result)
        assert data["python_version"] == sys.version.split()[0]

    def test_unhealthy_on_exception(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.health_ops._get_mcp", side_effect=Exception("boom")):
            result = _brain_health_impl()
            data = json.loads(result)
            assert data["status"] == "unhealthy"
            assert "boom" in data["error"]


# ── _brain_health_impl_legacy ────────────────────────────────────

class TestBrainHealthImplLegacy:
    def test_healthy_brain(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        (brain / "ledger" / "tasks.json").write_text(json.dumps({"tasks": [{"id": "t1"}, {"id": "t2"}]}))
        (brain / "ledger" / "events.jsonl").write_text('{"e": 1}\n{"e": 2}\n{"e": 3}\n')
        (brain / "state.json").write_text("{}")
        (brain / "slots").mkdir()
        (brain / "slots" / "registry.json").write_text(json.dumps({"slots": [{"id": "s1"}]}))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_health_impl_legacy()
        assert "NUCLEUS HEALTH CHECK" in result
        assert "healthy" in result.lower() or "HEALTHY" in result

    def test_missing_brain_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "nonexistent_brain"))
        result = _brain_health_impl_legacy()
        assert "NUCLEUS HEALTH CHECK" in result

    def test_degraded_brain(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        # No tasks file, no events file, no state, no slots
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_health_impl_legacy()
        assert "NUCLEUS HEALTH CHECK" in result
        # Should show warnings for missing files
        assert "MISSING" in result or "NO FILE" in result

    def test_corrupt_tasks_file(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        (brain / "ledger" / "tasks.json").write_text("not valid json{{{")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_health_impl_legacy()
        assert "CORRUPT" in result

    def test_corrupt_slots_file(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        (brain / "slots").mkdir()
        (brain / "slots" / "registry.json").write_text("not valid json{{{")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_health_impl_legacy()
        assert "CORRUPT" in result

    def test_events_read_error(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        events_path = brain / "ledger" / "events.jsonl"
        # Create events file but make it a directory to trigger read error
        events_path.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_health_impl_legacy()
        assert "NUCLEUS HEALTH CHECK" in result

    def test_exception_fallback(self, tmp_path, monkeypatch):
        with patch("mcp_server_nucleus.runtime.health_ops.get_brain_path", side_effect=Exception("crash")):
            result = _brain_health_impl_legacy()
            assert "CRITICAL ERROR" in result
            assert "crash" in result


# ── _brain_version_impl ──────────────────────────────────────────

class TestBrainVersionImpl:
    def test_returns_dict(self):
        result = _brain_version_impl()
        assert isinstance(result, dict)
        assert "nucleus_version" in result
        assert "python_version" in result
        assert "platform" in result
        assert "platform_release" in result
        assert "mcp_tools_count" in result
        assert "architecture" in result
        assert "status" in result

    def test_python_version_matches(self):
        result = _brain_version_impl()
        assert result["python_version"] == platform.python_version()

    def test_platform_matches(self):
        result = _brain_version_impl()
        assert result["platform"] == platform.system()

    def test_status_production_ready(self):
        result = _brain_version_impl()
        assert result["status"] == "production-ready"


# ── _brain_audit_log_impl ────────────────────────────────────────

class TestBrainAuditLogImpl:
    def test_no_log_file(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_audit_log_impl()
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["data"]["entries"] == []
        assert parsed["data"]["count"] == 0

    def test_with_entries(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        entries = []
        for i in range(5):
            entry = {"id": f"entry_{i}", "hash": f"hash_{i}"}
            entries.append(entry)
            log_path.write_text(log_path.read_text() if log_path.exists() else "")
        with open(log_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_audit_log_impl(limit=3)
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["data"]["count"] == 3
        assert parsed["data"]["total"] == 5

    def test_limit_larger_than_entries(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        with open(log_path, "w") as f:
            f.write(json.dumps({"id": "e1"}) + "\n")
            f.write(json.dumps({"id": "e2"}) + "\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_audit_log_impl(limit=20)
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 2
        assert parsed["data"]["total"] == 2

    def test_most_recent_first(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        with open(log_path, "w") as f:
            for i in range(3):
                f.write(json.dumps({"id": f"e{i}"}) + "\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_audit_log_impl(limit=3)
        parsed = json.loads(result)
        # Most recent first (reversed)
        assert parsed["data"]["entries"][0]["id"] == "e2"

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        with open(log_path, "w") as f:
            f.write(json.dumps({"id": "e1"}) + "\n")
            f.write("\n")
            f.write(json.dumps({"id": "e2"}) + "\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_audit_log_impl()
        parsed = json.loads(result)
        assert parsed["data"]["total"] == 2

    def test_exception_handling(self, tmp_path, monkeypatch):
        with patch("mcp_server_nucleus.runtime.health_ops.get_brain_path", side_effect=Exception("fail")):
            result = _brain_audit_log_impl()
            parsed = json.loads(result)
            assert parsed["success"] is False
            assert "Error reading audit log" in parsed["error"]

    def test_default_limit(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        with open(log_path, "w") as f:
            for i in range(25):
                f.write(json.dumps({"id": f"e{i}"}) + "\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _brain_audit_log_impl()
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 20
