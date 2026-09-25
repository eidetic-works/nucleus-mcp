"""
Coverage tests for mcp_server_nucleus.runtime.goal_tracker.

Targets 90%+ line coverage. Uses tmp_path for filesystem. Mocks event_ops,
archive_pipeline, and failure_patterns imports. No real network/subprocess.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import goal_tracker as gt
from mcp_server_nucleus.runtime.goal_tracker import (
    _append_goal,
    _count_attempts,
    _goals_path,
    _load_goals,
    get_all_goals,
    get_goal_progress,
    get_open_goals,
    record_goal_attempt,
)


# ──────────────────────────────────────────────────────────────────────
# _goals_path
# ──────────────────────────────────────────────────────────────────────

def test_goals_path_creates_dir(tmp_path):
    p = _goals_path(tmp_path)
    assert p == tmp_path / ".brain" / "driver" / "goals.jsonl"
    assert p.parent.exists()


# ──────────────────────────────────────────────────────────────────────
# _load_goals
# ──────────────────────────────────────────────────────────────────────

def test_load_goals_no_file(tmp_path):
    pp = _goals_path(tmp_path)
    pp.unlink(missing_ok=True)
    assert _load_goals(tmp_path) == []


def test_load_goals_parses_lines(tmp_path):
    pp = _goals_path(tmp_path)
    with open(pp, "w") as f:
        f.write(json.dumps({"goal_id": "a", "attempt": 1}) + "\n")
        f.write(json.dumps({"goal_id": "a", "attempt": 2}) + "\n")
    assert len(_load_goals(tmp_path)) == 2


def test_load_goals_skips_blank_and_invalid(tmp_path):
    pp = _goals_path(tmp_path)
    with open(pp, "w") as f:
        f.write("\n")
        f.write("   \n")
        f.write("{bad}\n")
        f.write(json.dumps({"goal_id": "a"}) + "\n")
    assert len(_load_goals(tmp_path)) == 1


# ──────────────────────────────────────────────────────────────────────
# _append_goal
# ──────────────────────────────────────────────────────────────────────

def test_append_goal_writes(tmp_path):
    _append_goal(tmp_path, {"goal_id": "x", "attempt": 1})
    lines = _goals_path(tmp_path).read_text().splitlines()
    assert json.loads(lines[0])["goal_id"] == "x"


# ──────────────────────────────────────────────────────────────────────
# _count_attempts
# ──────────────────────────────────────────────────────────────────────

def test_count_attempts_zero(tmp_path):
    assert _count_attempts(tmp_path, "nope") == 0


def test_count_attempts_counts(tmp_path):
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 1})
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 2})
    _append_goal(tmp_path, {"goal_id": "other", "attempt": 1})
    assert _count_attempts(tmp_path, "g") == 2


# ──────────────────────────────────────────────────────────────────────
# record_goal_attempt
# ──────────────────────────────────────────────────────────────────────

def test_record_goal_attempt_skips_non_tier5(tmp_path):
    record_goal_attempt("plan.md", {}, [{"tier": 4, "metric": "m"}], tmp_path)
    assert _load_goals(tmp_path) == []


def test_record_goal_attempt_appends_failed(tmp_path):
    sig = {"tier": 5, "metric": "coverage", "claimed_delta": 10, "actual_delta": 0,
           "hit_ratio": 0.0, "passed": False}
    with patch("mcp_server_nucleus.runtime.event_ops._emit_event") as mock_emit, \
         patch("mcp_server_nucleus.runtime.failure_patterns.catalog_failure") as mock_cat:
        record_goal_attempt("plan.md", {}, [sig], tmp_path)
    goals = _load_goals(tmp_path)
    assert len(goals) == 1
    g = goals[0]
    assert g["goal_id"] == "plan:coverage"
    assert g["attempt"] == 1
    assert g["passed"] is False
    # goal_progress event emitted for failure
    mock_emit.assert_called_once()
    assert mock_emit.call_args[0][0] == "goal_progress"
    mock_cat.assert_called_once()


def test_record_goal_attempt_appends_passed_emits_achieved(tmp_path):
    sig = {"tier": 5, "metric": "coverage", "claimed_delta": 10, "actual_delta": 10,
           "hit_ratio": 1.0, "passed": True}
    with patch("mcp_server_nucleus.runtime.event_ops._emit_event") as mock_emit, \
         patch("mcp_server_nucleus.runtime.goal_tracker._record_goal_dpo") as mock_dpo:
        record_goal_attempt("plan.md", {}, [sig], tmp_path)
    goals = _load_goals(tmp_path)
    assert goals[0]["passed"] is True
    mock_emit.assert_called_once()
    assert mock_emit.call_args[0][0] == "goal_achieved"
    mock_dpo.assert_called_once()


def test_record_goal_attempt_increments_attempt(tmp_path):
    sig = {"tier": 5, "metric": "m", "passed": False}
    with patch("mcp_server_nucleus.runtime.event_ops._emit_event"), \
         patch("mcp_server_nucleus.runtime.failure_patterns.catalog_failure"):
        record_goal_attempt("plan.md", {}, [sig], tmp_path)
        record_goal_attempt("plan.md", {}, [sig], tmp_path)
    goals = _load_goals(tmp_path)
    assert {g["attempt"] for g in goals} == {1, 2}


def test_record_goal_attempt_uses_check_when_no_metric(tmp_path):
    sig = {"tier": 5, "check": "outcome_file", "passed": False}
    with patch("mcp_server_nucleus.runtime.event_ops._emit_event"), \
         patch("mcp_server_nucleus.runtime.failure_patterns.catalog_failure"):
        record_goal_attempt("plan.md", {}, [sig], tmp_path)
    g = _load_goals(tmp_path)[0]
    assert g["metric"] == "outcome_file"
    assert g["goal_id"] == "plan:outcome_file"


def test_record_goal_attempt_event_emission_failure_nonfatal(tmp_path):
    sig = {"tier": 5, "metric": "m", "passed": False}
    with patch("mcp_server_nucleus.runtime.event_ops._emit_event",
               side_effect=RuntimeError("boom")):
        # should not raise
        record_goal_attempt("plan.md", {}, [sig], tmp_path)
    assert len(_load_goals(tmp_path)) == 1


def test_record_goal_attempt_catalog_failure_importerror_nonfatal(tmp_path):
    sig = {"tier": 5, "metric": "m", "passed": False}
    # Force the catalog_failure import inside the function to fail by making
    # _emit_event succeed but the inner ImportError path trigger.
    # Simulate by patching event_ops._emit_event to run the else branch which
    # tries to import catalog_failure — we make that import raise.
    import sys
    real_emit = MagicMock()

    with patch("mcp_server_nucleus.runtime.event_ops._emit_event", real_emit):
        # Temporarily hide failure_patterns module to trigger ImportError
        original = sys.modules.get("mcp_server_nucleus.runtime.failure_patterns")
        sys.modules["mcp_server_nucleus.runtime.failure_patterns"] = None
        try:
            record_goal_attempt("plan.md", {}, [sig], tmp_path)
        finally:
            if original is not None:
                sys.modules["mcp_server_nucleus.runtime.failure_patterns"] = original
            else:
                sys.modules.pop("mcp_server_nucleus.runtime.failure_patterns", None)
    assert len(_load_goals(tmp_path)) == 1


# ──────────────────────────────────────────────────────────────────────
# _record_goal_dpo
# ──────────────────────────────────────────────────────────────────────

def test_record_goal_dpo_success(tmp_path):
    from mcp_server_nucleus.runtime.goal_tracker import _record_goal_dpo
    mock_archive = MagicMock()
    with patch("mcp_server_nucleus.runtime.archive_pipeline.ArchivePipeline",
               return_value=mock_archive):
        _record_goal_dpo("gid", "plan.md", 3, tmp_path)
    mock_archive.record_outcome_preference.assert_called_once()
    call = mock_archive.record_outcome_preference.call_args
    assert call.kwargs["success"] is True
    assert call.kwargs["context"] == "gid"


def test_record_goal_dpo_failure_nonfatal(tmp_path):
    from mcp_server_nucleus.runtime.goal_tracker import _record_goal_dpo
    with patch("mcp_server_nucleus.runtime.archive_pipeline.ArchivePipeline",
               side_effect=RuntimeError("nope")):
        # should not raise
        _record_goal_dpo("gid", "plan.md", 1, tmp_path)


# ──────────────────────────────────────────────────────────────────────
# get_open_goals
# ──────────────────────────────────────────────────────────────────────

def test_get_open_goals_empty(tmp_path):
    pp = _goals_path(tmp_path)
    pp.unlink(missing_ok=True)
    assert get_open_goals(tmp_path) == []


def test_get_open_goals_returns_latest_unachieved(tmp_path):
    now_iso = datetime.now().isoformat()
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 1, "passed": False, "ts": now_iso})
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 2, "passed": False, "ts": now_iso})
    open_goals = get_open_goals(tmp_path)
    assert len(open_goals) == 1
    assert open_goals[0]["attempt"] == 2
    assert open_goals[0]["status"] == "open"
    assert "stale_days" in open_goals[0]


def test_get_open_goals_skips_achieved(tmp_path):
    now_iso = datetime.now().isoformat()
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 1, "passed": False, "ts": now_iso})
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 2, "passed": True, "ts": now_iso})
    assert get_open_goals(tmp_path) == []


def test_get_open_goals_marks_abandoned_when_stale(tmp_path):
    old = (datetime.now() - timedelta(days=10)).isoformat()
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 1, "passed": False, "ts": old})
    open_goals = get_open_goals(tmp_path)
    assert open_goals[0]["status"] == "abandoned"


def test_get_open_goals_missing_ts_defaults_stale_zero(tmp_path):
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 1, "passed": False})  # no ts
    open_goals = get_open_goals(tmp_path)
    assert open_goals[0]["status"] == "open"
    assert open_goals[0]["stale_days"] == 0.0


def test_get_open_goals_invalid_ts_defaults_stale_zero(tmp_path):
    _append_goal(tmp_path, {"goal_id": "g", "attempt": 1, "passed": False, "ts": "not-a-date"})
    open_goals = get_open_goals(tmp_path)
    assert open_goals[0]["status"] == "open"


# ──────────────────────────────────────────────────────────────────────
# get_goal_progress / get_all_goals
# ──────────────────────────────────────────────────────────────────────

def test_get_goal_progress_filters(tmp_path):
    _append_goal(tmp_path, {"goal_id": "a", "attempt": 1})
    _append_goal(tmp_path, {"goal_id": "b", "attempt": 1})
    _append_goal(tmp_path, {"goal_id": "a", "attempt": 2})
    prog = get_goal_progress("a", tmp_path)
    assert len(prog) == 2
    assert all(g["goal_id"] == "a" for g in prog)


def test_get_all_goals_returns_all(tmp_path):
    _append_goal(tmp_path, {"goal_id": "a", "attempt": 1})
    _append_goal(tmp_path, {"goal_id": "b", "attempt": 1})
    assert len(get_all_goals(tmp_path)) == 2
