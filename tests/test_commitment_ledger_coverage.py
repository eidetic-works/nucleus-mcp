"""Coverage tests for mcp_server_nucleus/commitment_ledger.py — the PEFS
Phase-2 commitment ledger (commitments, challenges, patterns, metrics,
feedback, librarian scanning, IP export)."""
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus import commitment_ledger as cl


# ── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path):
    bp = tmp_path / ".brain"
    for sub in ["commitments", "challenges", "patterns", "ledger", "exports"]:
        (bp / sub).mkdir(parents=True, exist_ok=True)
    return bp


# ── paths ───────────────────────────────────────────────────────────

class TestPaths:
    def test_ledger_path(self, brain):
        assert cl.get_ledger_path(brain) == brain / "commitments" / "ledger.json"

    def test_challenge_path(self, brain):
        assert cl.get_challenge_path(brain) == brain / "challenges" / "current_challenge.json"

    def test_patterns_path(self, brain):
        assert cl.get_patterns_path(brain) == brain / "patterns" / "learned_patterns.json"

    def test_feedback_path(self, brain):
        assert cl.get_feedback_path(brain) == brain / "commitments" / "feedback_log.json"


# ── load/save ledger ────────────────────────────────────────────────

class TestLoadSaveLedger:
    def test_load_default(self, brain):
        ledger = cl.load_ledger(brain)
        assert ledger["commitments"] == []
        assert ledger["stats"]["total_open"] == 0
        assert ledger["notifications_sent"] == 0

    def test_save_and_load(self, brain):
        ledger = {"commitments": [{"id": "c1"}], "stats": {"total_open": 1}, "last_scan": None,
                  "last_interaction": None, "notifications_sent": 0, "high_impact_closed": 0,
                  "notifications_paused": False, "manual_overrides_count": 0,
                  "estimated_time_saved_minutes": 0}
        cl.save_ledger(brain, ledger)
        loaded = cl.load_ledger(brain)
        assert loaded["commitments"] == [{"id": "c1"}]


# ── analyze_context ─────────────────────────────────────────────────

class TestAnalyzeContext:
    def test_high_novelty(self):
        c = cl.analyze_context("first time doing this", "f.py")
        assert c["novelty"] == "high"

    def test_low_novelty(self):
        c = cl.analyze_context("repeat this again", "f.py")
        assert c["novelty"] == "low"

    def test_medium_novelty(self):
        c = cl.analyze_context("just a task", "f.py")
        assert c["novelty"] == "medium"

    def test_low_dopamine(self):
        c = cl.analyze_context("fix the bug in config", "f.py")
        assert c["dopamine"] == "low"

    def test_high_dopamine(self):
        c = cl.analyze_context("build and create something", "f.py")
        assert c["dopamine"] == "high"

    def test_medium_dopamine(self):
        c = cl.analyze_context("just a task", "f.py")
        assert c["dopamine"] == "medium"

    def test_high_urgency(self):
        c = cl.analyze_context("deadline is urgent asap today", "f.py")
        assert c["urgency"] == "high"

    def test_medium_urgency(self):
        c = cl.analyze_context("do this soon this week", "f.py")
        assert c["urgency"] == "medium"

    def test_no_urgency(self):
        c = cl.analyze_context("just a task", "f.py")
        assert c["urgency"] is None

    def test_emotional_load(self):
        c = cl.analyze_context("should need to must haven't forgot", "f.py")
        assert c["emotional_load"] == 10  # 5 keywords * 2, capped at 10

    def test_zero_emotional_load(self):
        c = cl.analyze_context("just a task", "f.py")
        assert c["emotional_load"] == 0


# ── suggest_action ──────────────────────────────────────────────────

class TestSuggestAction:
    def _comm(self, age, **ctx_overrides):
        ctx = {"novelty": "medium", "dopamine": "medium", "urgency": None, "emotional_load": 0}
        ctx.update(ctx_overrides)
        return {"age_days": age, "context": ctx}

    def test_archive_stale(self):
        action, reason = cl.suggest_action(self._comm(35))
        assert action == "archive"
        assert "Stale" in reason

    def test_high_novelty_schedule(self):
        action, reason = cl.suggest_action(self._comm(5, novelty="high"))
        assert action == "schedule"
        assert "novelty" in reason.lower() or "review" in reason.lower()

    def test_low_dopamine_schedule(self):
        action, reason = cl.suggest_action(self._comm(3, dopamine="low"))
        assert action == "schedule"
        assert "morning" in reason.lower()

    def test_urgent_do_now(self):
        action, reason = cl.suggest_action(self._comm(5, urgency="high"))
        assert action == "do_now"
        assert "Urgent" in reason

    def test_recent_simple_do_now(self):
        action, reason = cl.suggest_action(self._comm(2, novelty="low"))
        assert action == "do_now"
        assert "quick win" in reason.lower()

    def test_default_schedule(self):
        action, reason = cl.suggest_action(self._comm(10))
        assert action == "schedule"
        assert "focused" in reason.lower()


# ── add_commitment ──────────────────────────────────────────────────

class TestAddCommitment:
    def test_add_basic(self, brain):
        comm = cl.add_commitment(brain, "f.py", 10, "fix the bug", "task")
        assert comm["id"].startswith("comm_")
        assert comm["age_days"] == 0
        assert comm["tier"] == "green"
        assert comm["status"] == "open"
        assert comm["suggested_action"] is not None
        # Verify persisted
        ledger = cl.load_ledger(brain)
        assert len(ledger["commitments"]) == 1

    def test_add_with_skills(self, brain):
        comm = cl.add_commitment(brain, "f.py", 10, "do thing", "task", required_skills=["python"])
        assert comm["required_skills"] == ["python"]

    def test_add_with_pattern_match(self, brain):
        # Set up a pattern that matches
        cl.save_patterns(brain, [{"name": "test", "keywords": ["fix"], "action": "do_now", "confidence": 0.8}])
        comm = cl.add_commitment(brain, "f.py", 10, "fix the bug", "task")
        assert comm["suggested_action"] == "do_now"
        assert "Pattern match" in comm["suggested_reason"]


# ── update_commitment_ages ──────────────────────────────────────────

class TestUpdateAges:
    def test_update_green(self, brain):
        cl.add_commitment(brain, "f.py", 10, "do thing", "task")
        ledger = cl.update_commitment_ages(brain)
        comm = ledger["commitments"][0]
        assert comm["age_days"] == 0
        assert comm["tier"] == "green"
        assert ledger["stats"]["total_open"] == 1
        assert ledger["stats"]["green_tier"] == 1

    def test_update_with_old_commitment(self, brain):
        cl.add_commitment(brain, "f.py", 10, "do thing", "task")
        # Manually age it
        ledger = cl.load_ledger(brain)
        ledger["commitments"][0]["created"] = (datetime.now() - timedelta(days=10)).isoformat()
        cl.save_ledger(brain, ledger)
        ledger = cl.update_commitment_ages(brain)
        comm = ledger["commitments"][0]
        assert comm["age_days"] >= 9
        assert comm["tier"] == "red"
        assert ledger["stats"]["red_tier"] == 1

    def test_update_by_type(self, brain):
        cl.add_commitment(brain, "f.py", 10, "do thing", "task")
        cl.add_commitment(brain, "f.py", 11, "other thing", "todo")
        ledger = cl.update_commitment_ages(brain)
        assert ledger["stats"]["by_type"]["task"] == 1
        assert ledger["stats"]["by_type"]["todo"] == 1


# ── close_commitment ────────────────────────────────────────────────

class TestCloseCommitment:
    def test_close_success(self, brain):
        comm = cl.add_commitment(brain, "f.py", 10, "do thing", "task")
        closed = cl.close_commitment(brain, comm["id"], "completed")
        assert closed["status"] == "closed"
        assert closed["closed_method"] == "completed"

    def test_close_not_found(self, brain):
        with pytest.raises(ValueError, match="not found"):
            cl.close_commitment(brain, "nonexistent", "completed")


# ── challenges ──────────────────────────────────────────────────────

class TestChallenges:
    def test_load_no_challenge(self, brain):
        assert cl.load_challenge(brain) is None

    def test_set_and_load(self, brain):
        challenge = {"id": "test", "title": "Test"}
        cl.set_challenge(brain, challenge)
        loaded = cl.load_challenge(brain)
        assert loaded["id"] == "test"

    def test_starter_challenges(self):
        starters = cl.get_starter_challenges()
        assert len(starters) == 5
        ids = [s["id"] for s in starters]
        assert "red_slayer" in ids
        assert "draft_finisher" in ids

    def test_check_progress_no_challenge(self, brain):
        assert cl.check_challenge_progress(brain) is None

    def test_check_progress_with_challenge(self, brain):
        cl.set_challenge(brain, {"id": "test"})
        result = cl.check_challenge_progress(brain)
        assert result["status"] == "in_progress"


# ── patterns ────────────────────────────────────────────────────────

class TestPatterns:
    def test_load_no_patterns(self, brain):
        assert cl.load_patterns(brain) == []

    def test_save_and_load(self, brain):
        cl.save_patterns(brain, [{"name": "p1"}])
        assert cl.load_patterns(brain) == [{"name": "p1"}]

    def test_suggest_pattern_match(self):
        result = cl.suggest_pattern_action(
            {"description": "fix the bug"}, [{"keywords": ["fix"], "action": "do_now", "name": "p"}])
        assert result is not None
        assert result[0] == "do_now"

    def test_suggest_pattern_no_match(self):
        result = cl.suggest_pattern_action(
            {"description": "write code"}, [{"keywords": ["fix"], "action": "do_now", "name": "p"}])
        assert result is None

    def test_learn_patterns(self, brain):
        # Add 3 closed commitments with same keyword and method
        for i in range(3):
            comm = cl.add_commitment(brain, "f.py", i, "fixing something", "task")
            cl.close_commitment(brain, comm["id"], "completed")
        patterns = cl.learn_patterns(brain)
        # Should detect "fixing" closed 3x via "completed"
        assert any("fixing" in p["keywords"] for p in patterns)

    def test_learn_patterns_no_new(self, brain):
        cl.add_commitment(brain, "f.py", 0, "do thing", "task")
        patterns = cl.learn_patterns(brain)
        # Only 1 closed item, no patterns learned
        assert patterns == []


# ── metrics ─────────────────────────────────────────────────────────

class TestMetrics:
    def test_empty_metrics(self, brain):
        m = cl.calculate_metrics(brain)
        assert m["velocity_7d"] == 0
        assert m["avg_days_to_close"] == 0
        assert m["current_load"]["total"] == 0

    def test_velocity_with_closed(self, brain):
        comm = cl.add_commitment(brain, "f.py", 0, "do thing", "task")
        cl.close_commitment(brain, comm["id"], "completed")
        m = cl.calculate_metrics(brain)
        assert m["velocity_7d"] == 1

    def test_closure_rates(self, brain):
        for i in range(3):
            comm = cl.add_commitment(brain, "f.py", i, "do thing", "task")
            cl.close_commitment(brain, comm["id"], "completed")
        m = cl.calculate_metrics(brain)
        assert "task" in m["closure_rates"]


# ── MDR_010 telemetry ───────────────────────────────────────────────

class TestTelemetry:
    def test_record_interaction(self, brain):
        cl.record_interaction(brain)
        ledger = cl.load_ledger(brain)
        assert ledger["last_interaction"] is not None

    def test_increment_notifications(self, brain):
        cl.increment_notifications(brain, 3)
        assert cl.load_ledger(brain)["notifications_sent"] == 3

    def test_mark_high_impact(self, brain):
        cl.mark_high_impact_closure(brain)
        assert cl.load_ledger(brain)["high_impact_closed"] == 1

    def test_value_ratio_no_notifications(self, brain):
        vr = cl.calculate_value_ratio(brain)
        assert vr["ratio"] is None
        assert "No notifications" in vr["verdict"]

    def test_value_ratio_excellent(self, brain):
        ledger = cl.load_ledger(brain)
        ledger["notifications_sent"] = 10
        ledger["high_impact_closed"] = 3
        cl.save_ledger(brain, ledger)
        vr = cl.calculate_value_ratio(brain)
        assert vr["ratio"] == 0.3
        assert "EXCELLENT" in vr["verdict"]

    def test_value_ratio_good(self, brain):
        ledger = cl.load_ledger(brain)
        ledger["notifications_sent"] = 10
        ledger["high_impact_closed"] = 1
        cl.save_ledger(brain, ledger)
        vr = cl.calculate_value_ratio(brain)
        assert "GOOD" in vr["verdict"]

    def test_value_ratio_poor(self, brain):
        ledger = cl.load_ledger(brain)
        ledger["notifications_sent"] = 100
        ledger["high_impact_closed"] = 1
        cl.save_ledger(brain, ledger)
        vr = cl.calculate_value_ratio(brain)
        assert "POOR" in vr["verdict"]

    def test_value_ratio_failure(self, brain):
        ledger = cl.load_ledger(brain)
        ledger["notifications_sent"] = 100
        ledger["high_impact_closed"] = 0
        cl.save_ledger(brain, ledger)
        vr = cl.calculate_value_ratio(brain)
        assert "FAILURE" in vr["verdict"]

    def test_record_manual_override(self, brain):
        cl.record_manual_override(brain, "test")
        assert cl.load_ledger(brain)["manual_overrides_count"] == 1

    def test_estimate_time_saved(self, brain):
        cl.estimate_time_saved(brain, 30)
        assert cl.load_ledger(brain)["estimated_time_saved_minutes"] == 30


# ── weekly summary ──────────────────────────────────────────────────

class TestWeeklySummary:
    def test_empty_summary(self, brain):
        s = cl.get_weekly_summary(brain)
        assert s["velocity_7d"] == 0
        assert s["friction_score"] == "LOW"

    def test_high_friction(self, brain):
        for i in range(6):
            cl.record_manual_override(brain)
        s = cl.get_weekly_summary(brain)
        assert s["friction_score"] == "HIGH"

    def test_medium_friction(self, brain):
        for i in range(3):
            cl.record_manual_override(brain)
        s = cl.get_weekly_summary(brain)
        assert s["friction_score"] == "MEDIUM"


# ── days since interaction / kill switch ────────────────────────────

class TestKillSwitch:
    def test_days_since_never(self, brain):
        assert cl.get_days_since_interaction(brain) == -1

    def test_days_since_recent(self, brain):
        cl.record_interaction(brain)
        assert cl.get_days_since_interaction(brain) == 0

    def test_kill_switch_continue(self, brain):
        cl.record_interaction(brain)
        result = cl.check_kill_switch(brain)
        assert result["action"] == "continue"

    def test_kill_switch_warn(self, brain):
        ledger = cl.load_ledger(brain)
        ledger["last_interaction"] = (datetime.now() - timedelta(days=8)).isoformat()
        cl.save_ledger(brain, ledger)
        result = cl.check_kill_switch(brain)
        assert result["action"] == "warn"

    def test_kill_switch_escalate(self, brain):
        ledger = cl.load_ledger(brain)
        ledger["last_interaction"] = (datetime.now() - timedelta(days=15)).isoformat()
        cl.save_ledger(brain, ledger)
        result = cl.check_kill_switch(brain)
        assert result["action"] == "escalate"

    def test_kill_switch_paused(self, brain):
        cl.pause_notifications(brain)
        result = cl.check_kill_switch(brain)
        assert result["action"] == "paused"

    def test_pause_resume(self, brain):
        cl.pause_notifications(brain)
        assert cl.load_ledger(brain)["notifications_paused"] is True
        cl.resume_notifications(brain)
        assert cl.load_ledger(brain)["notifications_paused"] is False


# ── feedback ────────────────────────────────────────────────────────

class TestFeedback:
    def test_load_no_feedback(self, brain):
        assert cl.load_feedback(brain) == []

    def test_save_and_load(self, brain):
        cl.save_feedback(brain, [{"score": 5}])
        assert cl.load_feedback(brain) == [{"score": 5}]

    def test_record_feedback_positive(self, brain):
        entry = cl.record_feedback(brain, "notification", 5)
        assert entry["score"] == 5
        # Positive feedback marks high impact
        assert cl.load_ledger(brain)["high_impact_closed"] == 1
        # Also records interaction
        assert cl.load_ledger(brain)["last_interaction"] is not None

    def test_record_feedback_worst_score_is_not_high_impact(self, brain):
        # score=1 is the WORST rating on the 1-5 scale, not a positive "yes" —
        # must never mark high impact. (This used to be misnamed
        # test_record_feedback_yn_positive and asserted the opposite,
        # encoding the exact bug this scale-collision fix corrects.)
        entry = cl.record_feedback(brain, "notification", 1)
        assert entry["score"] == 1
        assert cl.load_ledger(brain)["high_impact_closed"] == 0

    def test_record_feedback_negative(self, brain):
        cl.record_feedback(brain, "notification", 2)
        assert cl.load_ledger(brain)["high_impact_closed"] == 0

    def test_record_feedback_with_response_time(self, brain):
        entry = cl.record_feedback(brain, "notification", 4, response_time_seconds=30)
        assert entry["response_time_seconds"] == 30


# ── scan_for_commitments ────────────────────────────────────────────

class TestScan:
    def test_scan_no_matches(self, brain):
        result = cl.scan_for_commitments(brain)
        assert result["new_found"] == 0

    def test_scan_finds_checklist(self, brain):
        md_file = brain / "task.md"
        md_file.write_text("# Tasks\n- [ ] fix the bug\n- [ ] write tests\n")
        with patch("subprocess.run") as m_run:
            m_run.return_value = MagicMock(stdout=f"{md_file}:2:- [ ] fix the bug\n{md_file}:3:- [ ] write tests\n",
                                           returncode=0)
            result = cl.scan_for_commitments(brain)
        assert result["new_found"] == 2

    def test_scan_dedup(self, brain):
        md_file = brain / "task.md"
        md_file.write_text("# Tasks\n- [ ] fix the bug\n")
        # Pre-add the commitment
        cl.add_commitment(brain, str(md_file), 2, "fix the bug", "checklist_item")
        with patch("subprocess.run") as m_run:
            m_run.return_value = MagicMock(stdout=f"{md_file}:2:- [ ] fix the bug\n", returncode=0)
            result = cl.scan_for_commitments(brain)
        assert result["new_found"] == 0

    def test_scan_error(self, brain):
        with patch("subprocess.run", side_effect=FileNotFoundError("no rg")):
            result = cl.scan_for_commitments(brain)
        assert "error" in result


# ── auto_archive_stale ──────────────────────────────────────────────

class TestAutoArchive:
    def test_no_stale(self, brain):
        cl.add_commitment(brain, "f.py", 0, "do thing", "task")
        assert cl.auto_archive_stale(brain) == 0

    def test_archives_old(self, brain):
        comm = cl.add_commitment(brain, "f.py", 0, "do thing", "task")
        # Make it old
        ledger = cl.load_ledger(brain)
        ledger["commitments"][0]["created"] = (datetime.now() - timedelta(days=35)).isoformat()
        cl.save_ledger(brain, ledger)
        count = cl.auto_archive_stale(brain)
        assert count == 1
        ledger = cl.load_ledger(brain)
        assert ledger["commitments"][0]["status"] == "closed"
        assert ledger["commitments"][0]["closed_method"] == "auto_archived"


# ── brainignore / export ────────────────────────────────────────────

class TestBrainIgnore:
    def test_no_ignore_file(self, brain):
        patterns = cl.load_brainignore(brain)
        assert ".DS_Store" in patterns
        assert "__pycache__" in patterns

    def test_with_ignore_file(self, brain):
        (brain / ".brainignore").write_text("# comment\n*.secret\nnode_modules\n")
        patterns = cl.load_brainignore(brain)
        assert "*.secret" in patterns
        assert "node_modules" in patterns
        assert "# comment" not in patterns

    def test_export_brain(self, brain):
        (brain / "data.json").write_text('{"key": "value"}')
        (brain / ".DS_Store").write_text("ignored")
        result = cl.export_brain(brain)
        assert "Exported" in result
        # Check the zip was created
        exports = list((brain / "exports").glob("brain_export_*.zip"))
        assert len(exports) == 1
        with zipfile.ZipFile(exports[0]) as zf:
            names = zf.namelist()
            assert "data.json" in names
            assert ".DS_Store" not in names
            assert "exports/" not in names
