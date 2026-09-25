"""Comprehensive coverage tests for runtime/csr.py.

Tests every public function and helper, including edge cases:
empty goals, missing/invalid timestamps, difficulty weighting bands,
staleness handling, trend computation, scoreboard formatting, and
root detection. External `goal_tracker` calls are mocked — no real
filesystem goals.jsonl is required.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime import csr as csr_mod
from mcp_server_nucleus.runtime.csr import (
    _claim_difficulty,
    _compute_trend,
    _detect_root,
    compute_csr,
    format_scoreboard,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _goal(
    goal_id: str = "g1",
    attempt: int = 1,
    passed: bool = True,
    claimed_delta: int = 10,
    ts: datetime | None = None,
    metric: str = "coverage",
    hit_ratio: float = 0.9,
    status: str = "met",
) -> dict:
    return {
        "goal_id": goal_id,
        "attempt": attempt,
        "passed": passed,
        "claimed_delta": claimed_delta,
        "ts": (ts or datetime.now()).isoformat(),
        "metric": metric,
        "hit_ratio": hit_ratio,
        "status": status,
    }


def _patch_goals(monkeypatch, all_goals, open_goals=None):
    """Patch goal_tracker functions used by compute_csr."""
    import mcp_server_nucleus.runtime.goal_tracker as gt

    monkeypatch.setattr(gt, "get_all_goals", lambda root: all_goals)
    monkeypatch.setattr(gt, "get_open_goals", lambda root: open_goals or [])
    # compute_csr imports the functions lazily from the module, so patch the
    # attributes on the goal_tracker module object that the import resolves to.
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.goal_tracker.get_all_goals",
        lambda root: all_goals,
        raising=False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.goal_tracker.get_open_goals",
        lambda root: open_goals or [],
        raising=False,
    )


# ---------------------------------------------------------------------------
# _claim_difficulty
# ---------------------------------------------------------------------------
class TestClaimDifficulty:
    def test_zero_delta_returns_moderate(self):
        assert _claim_difficulty({"claimed_delta": 0}) == 0.5

    def test_no_key_returns_moderate(self):
        assert _claim_difficulty({}) == 0.5

    def test_trivial_band(self):
        assert _claim_difficulty({"claimed_delta": 1}) == 0.1
        assert _claim_difficulty({"claimed_delta": 2}) == 0.1

    def test_easy_band(self):
        assert _claim_difficulty({"claimed_delta": 3}) == 0.3
        assert _claim_difficulty({"claimed_delta": 5}) == 0.3

    def test_moderate_band(self):
        assert _claim_difficulty({"claimed_delta": 6}) == 0.6
        assert _claim_difficulty({"claimed_delta": 20}) == 0.6

    def test_hard_band(self):
        assert _claim_difficulty({"claimed_delta": 21}) == 1.0
        assert _claim_difficulty({"claimed_delta": 1000}) == 1.0

    def test_negative_delta_uses_abs(self):
        assert _claim_difficulty({"claimed_delta": -21}) == 1.0
        assert _claim_difficulty({"claimed_delta": -2}) == 0.1


# ---------------------------------------------------------------------------
# compute_csr
# ---------------------------------------------------------------------------
class TestComputeCsr:
    def test_empty_goals_returns_zeros(self, monkeypatch):
        _patch_goals(monkeypatch, [])
        result = compute_csr(project_root=Path("/tmp/nonexistent"))
        assert result["csr"] == 0.0
        assert result["csr_raw"] == 0.0
        assert result["total_claims"] == 0
        assert result["claims_met"] == 0
        assert result["claims_open"] == 0
        assert result["claims_failed"] == 0
        assert result["avg_attempts_to_meet"] == 0.0
        assert result["trend"] == []
        assert result["open_goals"] == []

    def test_all_met(self, monkeypatch):
        now = datetime.now()
        goals = [
            _goal("g1", attempt=1, passed=True, claimed_delta=30, ts=now),
            _goal("g2", attempt=2, passed=True, claimed_delta=30, ts=now),
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        assert result["total_claims"] == 2
        assert result["claims_met"] == 2
        assert result["claims_open"] == 0
        assert result["claims_failed"] == 0
        assert result["csr"] == 1.0
        assert result["csr_raw"] == 1.0
        assert result["avg_attempts_to_meet"] == 1.5

    def test_mixed_met_open_failed(self, monkeypatch):
        now = datetime.now()
        recent = now
        stale = now - timedelta(days=10)
        goals = [
            _goal("g1", attempt=1, passed=True, claimed_delta=30, ts=recent),
            _goal("g2", attempt=1, passed=False, claimed_delta=30, ts=recent),
            _goal("g3", attempt=1, passed=False, claimed_delta=30, ts=stale),
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        assert result["total_claims"] == 3
        assert result["claims_met"] == 1
        assert result["claims_open"] == 1
        assert result["claims_failed"] == 1

    def test_latest_attempt_used(self, monkeypatch):
        now = datetime.now()
        # Two attempts for same goal; later attempt is a pass
        goals = [
            _goal("g1", attempt=1, passed=False, claimed_delta=30, ts=now),
            _goal("g1", attempt=2, passed=True, claimed_delta=30, ts=now),
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        assert result["total_claims"] == 1
        assert result["claims_met"] == 1
        assert result["avg_attempts_to_meet"] == 2.0

    def test_window_filters_old(self, monkeypatch):
        now = datetime.now()
        old = now - timedelta(days=60)
        goals = [
            _goal("g1", attempt=1, passed=True, claimed_delta=30, ts=old),
            _goal("g2", attempt=1, passed=True, claimed_delta=30, ts=now),
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(window_days=30, project_root=Path("/tmp/x"))
        # Only g2 in window
        assert result["total_claims"] == 1
        assert result["claims_met"] == 1

    def test_invalid_timestamp_included(self, monkeypatch):
        goals = [
            {"goal_id": "g1", "attempt": 1, "passed": True, "claimed_delta": 30, "ts": "not-a-date"},
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        assert result["total_claims"] == 1
        assert result["claims_met"] == 1
        # stale_days defaults to 0 -> open path not hit because passed=True

    def test_invalid_timestamp_not_passed_open(self, monkeypatch):
        goals = [
            {"goal_id": "g1", "attempt": 1, "passed": False, "claimed_delta": 30, "ts": "bad"},
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        assert result["total_claims"] == 1
        assert result["claims_open"] == 1
        assert result["claims_failed"] == 0

    def test_missing_goal_id_grouped_under_empty(self, monkeypatch):
        now = datetime.now()
        goals = [
            {"attempt": 1, "passed": True, "claimed_delta": 30, "ts": now.isoformat()},
            {"attempt": 1, "passed": True, "claimed_delta": 30, "ts": now.isoformat()},
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        # Both grouped under "" -> single latest
        assert result["total_claims"] == 1

    def test_weighted_csr_differs_from_raw(self, monkeypatch):
        now = datetime.now()
        goals = [
            _goal("g1", attempt=1, passed=True, claimed_delta=1, ts=now),   # weight 0.1
            _goal("g2", attempt=1, passed=False, claimed_delta=30, ts=now),  # weight 1.0, open
        ]
        _patch_goals(monkeypatch, goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        # weighted_met=0.1, weighted_total=1.1 -> 0.0909
        assert result["csr"] == round(0.1 / 1.1, 4)
        assert result["csr_raw"] == 0.5

    def test_open_goals_capped(self, monkeypatch):
        now = datetime.now()
        open_goals = [{"metric": f"m{i}", "status": "open"} for i in range(15)]
        goals = [_goal("g1", attempt=1, passed=True, claimed_delta=30, ts=now)]
        _patch_goals(monkeypatch, goals, open_goals=open_goals)
        result = compute_csr(project_root=Path("/tmp/x"))
        assert len(result["open_goals"]) == 10

    def test_detects_root_when_no_project_root(self, monkeypatch):
        now = datetime.now()
        goals = [_goal("g1", attempt=1, passed=True, claimed_delta=30, ts=now)]
        _patch_goals(monkeypatch, goals)
        # Should not raise; uses _detect_root
        result = compute_csr()
        assert "csr" in result


# ---------------------------------------------------------------------------
# _compute_trend
# ---------------------------------------------------------------------------
class TestComputeTrend:
    def test_empty_goals(self):
        assert _compute_trend([], weeks=4) == []

    def test_all_invalid_timestamps_skipped(self):
        goals = [{"goal_id": "g1", "passed": True, "ts": "bad", "attempt": 1}]
        assert _compute_trend(goals, weeks=4) == []

    def test_trend_values(self):
        now = datetime.now()
        goals = []
        # week 4 ago: 1 met, 1 failed
        w4 = now - timedelta(weeks=4, days=1)
        goals.append(_goal("a", attempt=1, passed=True, ts=w4))
        goals.append(_goal("b", attempt=1, passed=False, ts=w4))
        # week 1 ago: 1 met
        w1 = now - timedelta(weeks=1, days=1)
        goals.append(_goal("c", attempt=1, passed=True, ts=w1))
        trend = _compute_trend(goals, weeks=4)
        assert len(trend) >= 2
        # all values are floats between 0 and 1
        for v in trend:
            assert 0.0 <= v <= 1.0

    def test_latest_attempt_in_week(self):
        now = datetime.now()
        w2 = now - timedelta(weeks=2, days=1)
        goals = [
            _goal("a", attempt=1, passed=False, ts=w2),
            _goal("a", attempt=2, passed=True, ts=w2),
        ]
        trend = _compute_trend(goals, weeks=4)
        # The week bucket should reflect the latest attempt (passed)
        assert any(v == 1.0 for v in trend)


# ---------------------------------------------------------------------------
# format_scoreboard
# ---------------------------------------------------------------------------
class TestFormatScoreboard:
    def _base_data(self, **overrides):
        data = {
            "csr": 0.9,
            "csr_raw": 0.8,
            "total_claims": 10,
            "claims_met": 9,
            "claims_open": 1,
            "claims_failed": 0,
            "avg_attempts_to_meet": 1.5,
            "trend": [0.5, 0.6, 0.7, 0.9],
            "open_goals": [],
        }
        data.update(overrides)
        return data

    def test_basic_output(self):
        out = format_scoreboard(self._base_data())
        assert "NUCLEUS GOVERNANCE SCOREBOARD" in out
        assert "90%" in out
        assert "Total: 10 claims" in out
        assert "Avg attempts to meet: 1.5" in out

    def test_bar_length(self):
        out = format_scoreboard(self._base_data(csr=0.45))
        # 45% -> 9 filled, 11 empty -> 20 total
        assert "[#########...........]" in out

    def test_zero_csr_bar(self):
        out = format_scoreboard(self._base_data(csr=0.0))
        assert "[....................]" in out

    def test_full_csr_bar(self):
        out = format_scoreboard(self._base_data(csr=1.0))
        assert "[####################]" in out

    def test_open_goals_displayed(self):
        data = self._base_data(open_goals=[
            {"metric": "coverage", "status": "open", "hit_ratio": 0.5, "attempt": 2, "claimed_delta": 10},
            {"metric": "speed", "status": "abandoned", "hit_ratio": 0.1, "attempt": 3, "claimed_delta": 5},
        ])
        out = format_scoreboard(data)
        assert "Open Goals:" in out
        assert "coverage" in out
        assert "speed" in out
        assert "!" in out  # abandoned icon
        assert ">" in out  # open icon

    def test_open_goals_capped_at_five(self):
        goals = [{"metric": f"m{i}", "status": "open", "hit_ratio": 0.5, "attempt": 1, "claimed_delta": 1} for i in range(8)]
        out = format_scoreboard(self._base_data(open_goals=goals))
        # only first 5 shown
        assert "m0" in out
        assert "m4" in out
        assert "m5" not in out

    def test_trend_up(self):
        out = format_scoreboard(self._base_data(trend=[0.5, 0.6, 0.7, 0.9]))
        assert "^" in out

    def test_trend_down(self):
        out = format_scoreboard(self._base_data(trend=[0.9, 0.7, 0.5, 0.3]))
        assert "v" in out

    def test_trend_flat(self):
        out = format_scoreboard(self._base_data(trend=[0.5, 0.5, 0.5, 0.5]))
        assert "=" in out

    def test_trend_single_value(self):
        out = format_scoreboard(self._base_data(trend=[0.5]))
        assert "=" in out

    def test_no_trend(self):
        out = format_scoreboard(self._base_data(trend=[]))
        assert "Trend:" not in out

    def test_no_avg_attempts(self):
        out = format_scoreboard(self._base_data(avg_attempts_to_meet=0.0))
        assert "Avg attempts to meet" not in out

    def test_missing_open_goals_key(self):
        data = self._base_data()
        del data["open_goals"]
        out = format_scoreboard(data)
        assert "Open Goals:" not in out


# ---------------------------------------------------------------------------
# _detect_root
# ---------------------------------------------------------------------------
class TestDetectRoot:
    def test_finds_git_root(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        sub = tmp_path / "sub"
        sub.mkdir()
        monkeypatch.chdir(sub)
        assert _detect_root() == tmp_path.resolve()

    def test_fallback_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _detect_root() == tmp_path.resolve()
