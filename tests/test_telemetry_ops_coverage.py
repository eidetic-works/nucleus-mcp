"""Comprehensive tests for mcp_server_nucleus.runtime.telemetry_ops.

Covers all _brain_*_impl functions with mocked commitment_ledger.
"""
import pytest

from mcp_server_nucleus.runtime import telemetry_ops


@pytest.fixture
def mock_ledger(monkeypatch):
    """Mock the commitment_ledger module used by telemetry_ops."""
    calls = {}

    def _mock(fn_name, return_value=None, side_effect=None):
        def _impl(*args, **kwargs):
            calls[fn_name] = {"args": args, "kwargs": kwargs}
            if side_effect:
                raise side_effect
            return return_value
        monkeypatch.setattr(telemetry_ops.commitment_ledger, fn_name, _impl)

    return calls, _mock


class TestRecordInteraction:
    def test_success(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_interaction")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_interaction_impl()
        assert "✅" in result
        assert "record_interaction" in calls

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_interaction", side_effect=RuntimeError("ledger error"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_interaction_impl()
        assert "Error" in result
        assert "ledger error" in result


class TestValueRatio:
    def test_success(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("calculate_value_ratio", return_value={
            "notifications_sent": 10,
            "high_impact_closed": 3,
            "ratio": 0.3,
            "verdict": "good",
        })
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_value_ratio_impl()
        assert "Value Ratio" in result
        assert "10" in result
        assert "3" in result
        assert "0.3" in result
        assert "good" in result

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("calculate_value_ratio", side_effect=ValueError("no data"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_value_ratio_impl()
        assert "Error" in result
        assert "no data" in result


class TestCheckKillSwitch:
    def test_success_with_days_inactive(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("check_kill_switch", return_value={
            "action": "pause",
            "message": "Too many notifications",
            "days_inactive": 5,
        })
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_check_kill_switch_impl()
        assert "Kill Switch" in result
        assert "pause" in result
        assert "Too many notifications" in result
        assert "Days Inactive" in result
        assert "5" in result

    def test_success_without_days_inactive(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("check_kill_switch", return_value={
            "action": "resume",
            "message": "All clear",
        })
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_check_kill_switch_impl()
        assert "resume" in result
        assert "All clear" in result
        assert "Days Inactive" not in result

    def test_success_no_message(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("check_kill_switch", return_value={"action": "ok"})
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_check_kill_switch_impl()
        assert "ok" in result
        assert "N/A" in result

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("check_kill_switch", side_effect=RuntimeError("switch error"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_check_kill_switch_impl()
        assert "Error" in result


class TestPauseNotifications:
    def test_success(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("pause_notifications")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_pause_notifications_impl()
        assert "paused" in result
        assert "resume_notifications" in result

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("pause_notifications", side_effect=RuntimeError("pause fail"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_pause_notifications_impl()
        assert "Error" in result
        assert "pause fail" in result


class TestResumeNotifications:
    def test_success(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("resume_notifications")
        _mock("record_interaction")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_resume_notifications_impl()
        assert "resumed" in result
        assert "Interaction recorded" in result
        assert "resume_notifications" in calls
        assert "record_interaction" in calls

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("resume_notifications", side_effect=RuntimeError("resume fail"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_resume_notifications_impl()
        assert "Error" in result
        assert "resume fail" in result


class TestRecordFeedback:
    def test_positive_feedback(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_feedback")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_feedback_impl("daily_briefing", 5)
        assert "Positive" in result
        assert "high-impact" in result
        assert calls["record_feedback"]["args"][1] == "daily_briefing"
        assert calls["record_feedback"]["args"][2] == 5

    def test_neutral_feedback(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_feedback")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_feedback_impl("alert", 3)
        assert "Neutral" in result

    def test_negative_feedback(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_feedback")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_feedback_impl("alert", 1)
        assert "Negative" in result
        assert "improve" in result

    def test_boundary_score_4(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_feedback")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_feedback_impl("x", 4)
        assert "Positive" in result

    def test_boundary_score_2(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_feedback")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_feedback_impl("x", 2)
        assert "Neutral" in result

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("record_feedback", side_effect=RuntimeError("feedback fail"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_record_feedback_impl("x", 5)
        assert "Error" in result


class TestMarkHighImpact:
    def test_success(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("mark_high_impact_closure")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_mark_high_impact_impl()
        assert "high-impact" in result
        assert "Value ratio updated" in result

    def test_exception(self, tmp_path, monkeypatch, mock_ledger):
        calls, _mock = mock_ledger
        _mock("mark_high_impact_closure", side_effect=RuntimeError("mark fail"))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain").mkdir()
        result = telemetry_ops._brain_mark_high_impact_impl()
        assert "Error" in result
        assert "mark fail" in result
