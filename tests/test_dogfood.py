"""Tests for dogfood_tracker.py — 30-day dog food experiment."""

import json
import pytest
from pathlib import Path
from mcp_server_nucleus.runtime.dogfood_tracker import (
    log_daily,
    get_status,
    format_status,
)


@pytest.fixture
def tmp_brain(tmp_path):
    """Create a temporary brain directory."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    return brain


class TestDogfoodLog:
    def test_first_log(self, tmp_brain):
        result = log_daily(pain_score=8, brain_path=tmp_brain)
        assert result["entry"]["day_number"] == 1
        assert result["entry"]["pain_if_broken"] == 8
        assert result["summary"]["total_days"] == 1
        assert result["summary"]["avg_pain_score"] == 8.0
        assert result["kill_gate"]["status"] == "SAFE"

    def test_invalid_score(self, tmp_brain):
        result = log_daily(pain_score=0, brain_path=tmp_brain)
        assert "error" in result
        result = log_daily(pain_score=11, brain_path=tmp_brain)
        assert "error" in result

    def test_multiple_logs(self, tmp_brain):
        log_daily(pain_score=6, brain_path=tmp_brain)
        # Force a different date for second entry
        log_file = tmp_brain / "experiments" / "dogfood" / "daily_log.json"
        entries = json.loads(log_file.read_text())
        entries[0]["date"] = "2026-03-01"
        log_file.write_text(json.dumps(entries))

        result = log_daily(pain_score=9, brain_path=tmp_brain)
        assert result["summary"]["total_days"] == 2
        assert result["summary"]["avg_pain_score"] == 7.5

    def test_would_pay(self, tmp_brain):
        result = log_daily(pain_score=8, would_pay=True, brain_path=tmp_brain)
        assert result["entry"]["would_pay"] is True
        assert "1/1" in result["summary"]["would_pay_rate"]

    def test_decisions_faster(self, tmp_brain):
        result = log_daily(pain_score=7, decisions_faster=5, brain_path=tmp_brain)
        assert result["entry"]["decisions_faster"] == 5
        assert result["summary"]["total_decisions_faster"] == 5

    def test_notes(self, tmp_brain):
        result = log_daily(pain_score=8, notes="Great session", brain_path=tmp_brain)
        assert result["entry"]["notes"] == "Great session"

    def test_update_same_day(self, tmp_brain):
        log_daily(pain_score=5, brain_path=tmp_brain)
        result = log_daily(pain_score=9, brain_path=tmp_brain)
        # Should update, not add duplicate
        assert result["summary"]["total_days"] == 1
        assert result["entry"]["pain_if_broken"] == 9

    def test_kill_gate_at_risk(self, tmp_brain):
        result = log_daily(pain_score=3, brain_path=tmp_brain)
        assert result["kill_gate"]["status"] == "AT RISK"


class TestDogfoodStatus:
    def test_not_started(self, tmp_brain):
        status = get_status(tmp_brain)
        assert status["status"] == "NOT STARTED"
        assert status["total_days"] == 0

    def test_running(self, tmp_brain):
        log_daily(pain_score=8, brain_path=tmp_brain)
        status = get_status(tmp_brain)
        assert status["status"] == "RUNNING"
        assert status["total_days"] == 1
        assert status["days_remaining"] == 29

    def test_sparkline(self, tmp_brain):
        log_daily(pain_score=10, brain_path=tmp_brain)
        status = get_status(tmp_brain)
        assert len(status["sparkline"]) == 1


class TestDogfoodFormat:
    def test_format_not_started(self, tmp_brain):
        status = get_status(tmp_brain)
        output = format_status(status)
        assert "NOT STARTED" in output
        assert "DOG FOOD TEST" in output

    def test_format_running(self, tmp_brain):
        log_daily(pain_score=8, would_pay=True, brain_path=tmp_brain)
        status = get_status(tmp_brain)
        output = format_status(status)
        assert "Day: 1/30" in output
        assert "SAFE" in output
        assert "8.0/10" in output
