"""Test manual replication detector + nudge ops (issue #37).

Verifies that:
1. detect_manual_compound_replication detects rapid audit queries
2. detect_manual_compound_replication detects manual task loop pattern
3. detect_manual_compound_replication detects manual training exports
4. emit_nudge respects throttle (1/hour)
5. emit_nudge writes to nudge log
6. detect_and_nudge integrates both
"""
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

import pytest

from mcp_server_nucleus.runtime.manual_replication_detector import (
    DetectionResult,
    detect_manual_compound_replication,
    _is_sequential_compound_pattern,
)
from mcp_server_nucleus.runtime.nudge_ops import (
    emit_nudge,
    should_nudge,
    detect_and_nudge,
    NUDGE_THROTTLE_SECONDS,
)


@dataclass
class FakeAuditRecord:
    """Fake audit record for testing."""
    event_type: str
    actor: str
    ts: str = ""
    hash: str = ""
    team_id: str = "test-team"
    resource: str = ""
    outcome: str = "success"
    metadata: dict = None

    def __post_init__(self):
        if not self.ts:
            from datetime import datetime, timezone
            self.ts = datetime.now(timezone.utc).isoformat()
        if self.metadata is None:
            self.metadata = {}


class TestManualReplicationDetector:
    """Test the detection logic."""

    def test_rapid_audit_queries_detected(self):
        """3+ audit queries in window should trigger detection."""
        records = [
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
        ]
        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=records):
            result = detect_manual_compound_replication("test-team")
        assert result is not None
        assert result.detected
        assert result.pattern == "rapid_audit_queries"
        assert result.confidence == 0.8

    def test_two_audit_queries_not_detected(self):
        """Fewer than 3 audit queries should not trigger."""
        records = [
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
        ]
        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=records):
            result = detect_manual_compound_replication("test-team")
        assert result is None

    def test_manual_task_loop_detected(self):
        """Sequential claim→execute→sync pattern should trigger."""
        records = []
        for _ in range(3):  # 3 full cycles
            records.append(FakeAuditRecord(event_type="task_claim", actor="agent-1"))
            records.append(FakeAuditRecord(event_type="task_execute", actor="agent-1"))
            records.append(FakeAuditRecord(event_type="sync", actor="agent-1"))

        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=records):
            result = detect_manual_compound_replication("test-team")
        assert result is not None
        assert result.detected
        assert result.pattern == "manual_task_loop"
        assert result.confidence == 0.9

    def test_manual_training_export_detected(self):
        """2+ manual training exports should trigger."""
        records = [
            FakeAuditRecord(event_type="training_export", actor="agent-1"),
            FakeAuditRecord(event_type="training_export", actor="agent-1"),
        ]
        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=records):
            result = detect_manual_compound_replication("test-team")
        assert result is not None
        assert result.detected
        assert result.pattern == "manual_training_export"

    def test_no_records_no_detection(self):
        """Empty audit log should not trigger."""
        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=[]):
            result = detect_manual_compound_replication("test-team")
        assert result is None

    def test_is_sequential_pattern(self):
        """Test the sequential pattern matcher directly."""
        ops = [
            FakeAuditRecord(event_type="task_claim", actor="a"),
            FakeAuditRecord(event_type="task_execute", actor="a"),
            FakeAuditRecord(event_type="sync", actor="a"),
            FakeAuditRecord(event_type="task_claim", actor="a"),
            FakeAuditRecord(event_type="task_execute", actor="a"),
            FakeAuditRecord(event_type="sync", actor="a"),
        ]
        assert _is_sequential_compound_pattern(ops) is True

    def test_not_sequential_pattern(self):
        """Random ops should not match sequential pattern."""
        ops = [
            FakeAuditRecord(event_type="task_claim", actor="a"),
            FakeAuditRecord(event_type="sync", actor="a"),
            FakeAuditRecord(event_type="task_execute", actor="a"),
        ]
        assert _is_sequential_compound_pattern(ops) is False


class TestNudgeOps:
    """Test the nudge delivery logic."""

    def test_should_nudge_when_no_prior_nudge(self, tmp_path):
        """Should nudge when no prior nudge exists."""
        assert should_nudge(tmp_path / "brain", "test-team") is True

    def test_should_not_nudge_within_throttle_window(self, tmp_path):
        """Should not nudge within the throttle window."""
        brain = tmp_path / "brain"
        # Emit a nudge
        with patch("mcp_server_nucleus.runtime.relay.core.relay_post"):
            emit_nudge("test-team", "test_pattern", "agent-1", "test details", brain_path=brain)
        # Should be throttled now
        assert should_nudge(brain, "test-team") is False

    def test_emit_nudge_writes_log(self, tmp_path):
        """emit_nudge should write to the nudge log."""
        brain = tmp_path / "brain"
        with patch("mcp_server_nucleus.runtime.relay.core.relay_post"):
            result = emit_nudge("test-team", "rapid_audit_queries", "agent-1", "3 queries in 5min", brain_path=brain)

        assert result["emitted"] is True
        nudge_log = brain / "nudges" / "nudge_log.jsonl"
        assert nudge_log.exists()
        with open(nudge_log) as f:
            entry = json.loads(f.readline())
        assert entry["pattern"] == "rapid_audit_queries"
        assert entry["actor"] == "agent-1"

    def test_emit_nudge_throttled(self, tmp_path):
        """Second nudge within throttle window should be throttled."""
        brain = tmp_path / "brain"
        with patch("mcp_server_nucleus.runtime.relay.core.relay_post"):
            result1 = emit_nudge("test-team", "pattern1", "agent-1", "details1", brain_path=brain)
            result2 = emit_nudge("test-team", "pattern2", "agent-1", "details2", brain_path=brain)

        assert result1["emitted"] is True
        assert result2["emitted"] is False
        assert result2["reason"] == "throttled"

    def test_emit_nudge_updates_state(self, tmp_path):
        """emit_nudge should update the nudge state file."""
        brain = tmp_path / "brain"
        with patch("mcp_server_nucleus.runtime.relay.core.relay_post"):
            emit_nudge("test-team", "test_pattern", "agent-1", "details", brain_path=brain)

        state_file = brain / "nudges" / "manual_replication_test-team.json"
        assert state_file.exists()
        with open(state_file) as f:
            state = json.load(f)
        assert state["nudge_count"] == 1
        assert state["last_pattern"] == "test_pattern"


class TestDetectAndNudge:
    """Test the integrated detect + nudge flow."""

    def test_detect_and_nudge_fires(self, tmp_path):
        """detect_and_nudge should detect and nudge in one call."""
        brain = tmp_path / "brain"
        records = [
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
            FakeAuditRecord(event_type="audit_query", actor="agent-1"),
        ]
        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=records):
            with patch("mcp_server_nucleus.runtime.relay.core.relay_post"):
                result = detect_and_nudge("test-team", brain_path=brain)

        assert result["detected"] is True
        assert result["nudged"] is True
        assert result["pattern"] == "rapid_audit_queries"

    def test_detect_and_nudge_no_detection(self, tmp_path):
        """detect_and_nudge should not nudge when no pattern detected."""
        brain = tmp_path / "brain"
        with patch("mcp_server_nucleus.runtime.audit_log.query_audit", return_value=[]):
            result = detect_and_nudge("test-team", brain_path=brain)

        assert result["detected"] is False
        assert result["nudged"] is False
