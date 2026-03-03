"""Tests for trace_viewer module."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def brain_dir():
    """Create a temporary brain directory with DSoR traces."""
    tmp = tempfile.mkdtemp(prefix="nucleus_test_trace_")
    brain = Path(tmp) / ".brain"
    brain.mkdir()
    dsor = brain / "dsor"
    dsor.mkdir()

    # Create sample traces
    trace1 = {
        "type": "KYC_REVIEW",
        "review_id": "KYC-ABCD1234",
        "application_id": "APP-001",
        "applicant": "John Smith",
        "recommendation": "APPROVE",
        "risk_score": 0,
        "risk_level": "LOW",
        "started_at": "2026-01-01T10:00:00Z",
        "completed_at": "2026-01-01T10:00:01Z",
        "hitl_required": False,
        "sovereign_guarantee": "All processing local.",
        "decision_trail": [
            {"step": 1, "action": "Sanctions Check", "result": "PASS",
             "reasoning": "Not on list", "risk_impact": 0,
             "timestamp": "2026-01-01T10:00:00Z"},
            {"step": 2, "action": "Final Decision", "result": "APPROVE",
             "reasoning": "All clear", "risk_impact": 0,
             "timestamp": "2026-01-01T10:00:01Z"},
        ],
    }
    (dsor / "KYC-ABCD1234.json").write_text(json.dumps(trace1))

    trace2 = {
        "type": "KYC_REVIEW",
        "review_id": "KYC-EFGH5678",
        "application_id": "APP-003",
        "applicant": "Dmitri Volkov",
        "recommendation": "REJECT",
        "risk_score": 175,
        "risk_level": "HIGH",
        "started_at": "2026-01-02T10:00:00Z",
        "completed_at": "2026-01-02T10:00:01Z",
        "hitl_required": True,
        "sovereign_guarantee": "All processing local.",
        "decision_trail": [
            {"step": 1, "action": "Sanctions Check", "result": "FAIL",
             "reasoning": "Sanctioned nationality", "risk_impact": 100,
             "timestamp": "2026-01-02T10:00:00Z"},
        ],
    }
    (dsor / "KYC-EFGH5678.json").write_text(json.dumps(trace2))

    trace3 = {
        "type": "AGENT_DECISION",
        "review_id": "AD-9999",
        "recommendation": "PROCEED",
        "decision_trail": [],
    }
    (dsor / "AD-9999.json").write_text(json.dumps(trace3))

    yield brain
    shutil.rmtree(tmp)


class TestTraceViewer:
    """Tests for DSoR trace viewer."""

    def test_list_all_traces(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import list_traces
        data = list_traces(brain_dir)

        assert data["count"] == 3
        assert len(data["traces"]) == 3
        assert "KYC_REVIEW" in data["types"]
        assert "AGENT_DECISION" in data["types"]

    def test_list_filtered_by_type(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import list_traces
        data = list_traces(brain_dir, trace_type="KYC_REVIEW")

        assert data["count"] == 2
        assert all(t["type"] == "KYC_REVIEW" for t in data["traces"])

    def test_list_empty_dsor(self):
        from mcp_server_nucleus.runtime.trace_viewer import list_traces
        tmp = tempfile.mkdtemp()
        brain = Path(tmp) / ".brain"
        brain.mkdir()
        (brain / "dsor").mkdir()

        data = list_traces(brain)
        assert data["count"] == 0

        shutil.rmtree(tmp)

    def test_list_no_dsor_dir(self):
        from mcp_server_nucleus.runtime.trace_viewer import list_traces
        tmp = tempfile.mkdtemp()
        brain = Path(tmp) / ".brain"
        brain.mkdir()

        data = list_traces(brain)
        assert data["count"] == 0
        assert data["status"] == "no_dsor_directory"

        shutil.rmtree(tmp)

    def test_get_trace_by_exact_id(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import get_trace
        trace = get_trace(brain_dir, "KYC-ABCD1234")

        assert trace is not None
        assert trace["review_id"] == "KYC-ABCD1234"
        assert trace["recommendation"] == "APPROVE"

    def test_get_trace_by_partial_id(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import get_trace
        trace = get_trace(brain_dir, "KYC-ABCD")

        assert trace is not None
        assert trace["review_id"] == "KYC-ABCD1234"

    def test_get_trace_not_found(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import get_trace
        trace = get_trace(brain_dir, "NONEXISTENT")
        assert trace is None

    def test_format_trace_list(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import list_traces, format_trace_list
        data = list_traces(brain_dir)
        formatted = format_trace_list(data)

        assert "DSoR TRACES" in formatted
        assert "KYC-ABCD1234" in formatted
        assert "KYC-EFGH5678" in formatted

    def test_format_trace_detail(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import get_trace, format_trace_detail
        trace = get_trace(brain_dir, "KYC-EFGH5678")
        formatted = format_trace_detail(trace)

        assert "DSoR TRACE" in formatted
        assert "REJECT" in formatted
        assert "Dmitri Volkov" in formatted
        assert "DECISION TRAIL" in formatted
        assert "Sanctions Check" in formatted

    def test_trace_summary_fields(self, brain_dir):
        from mcp_server_nucleus.runtime.trace_viewer import list_traces
        data = list_traces(brain_dir)

        for trace in data["traces"]:
            assert "file" in trace
            assert "type" in trace
            assert "review_id" in trace
            assert "recommendation" in trace
