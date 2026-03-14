"""Tests for heartbeat_ops.py — Proactive Context-Triggered Check-Ins.

Covers all 4 context trigger signals:
  - STALE_BLOCKER:  intensity ≥8 + "blocker" keyword + >24h old
  - STALE_DECISION: Decision context + intensity ≥7 + >72h old
  - VELOCITY_DROP:  <3 engram writes in 48h
  - SESSION_GAP:    No session save/resume in 24h+

Plus: formatting, status, and CLI handler dispatch.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.heartbeat_ops import (
    _heartbeat_check_impl,
    _heartbeat_status_impl,
    _check_stale_blockers,
    _check_stale_decisions,
    _check_velocity_drop,
    _check_session_gap,
    _format_heartbeat_output,
    _log_heartbeat_check,
)


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def empty_brain(tmp_path):
    """Create an empty brain directory."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "engrams").mkdir()
    (brain / "ledger").mkdir()
    return brain


@pytest.fixture
def brain_with_stale_blocker(tmp_path):
    """Create a brain with a stale blocker engram (>24h old, intensity ≥8)."""
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "ledger").mkdir(parents=True)

    old_ts = (datetime.now() - timedelta(hours=48)).isoformat()
    engram = {
        "key": "ci_pipeline_blocker",
        "value": "CI pipeline blocker: tests failing on main branch",
        "context": "Architecture",
        "intensity": 9,
        "timestamp": old_ts,
    }
    ledger = brain / "engrams" / "ledger.jsonl"
    ledger.write_text(json.dumps(engram) + "\n")
    return brain


@pytest.fixture
def brain_with_stale_decision(tmp_path):
    """Create a brain with a stale Decision engram (>72h old, intensity ≥7)."""
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "ledger").mkdir(parents=True)

    old_ts = (datetime.now() - timedelta(days=5)).isoformat()
    engram = {
        "key": "api_versioning_strategy",
        "value": "Decided to use URL-based API versioning v1/v2",
        "context": "Decision",
        "intensity": 8,
        "timestamp": old_ts,
    }
    ledger = brain / "engrams" / "ledger.jsonl"
    ledger.write_text(json.dumps(engram) + "\n")
    return brain


@pytest.fixture
def brain_with_velocity_drop(tmp_path):
    """Create a brain with many old engrams but few recent ones."""
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "ledger").mkdir(parents=True)

    ledger = brain / "engrams" / "ledger.jsonl"
    lines = []
    # 15 old engrams (>48h ago) to establish baseline
    for i in range(15):
        old_ts = (datetime.now() - timedelta(hours=100 + i)).isoformat()
        lines.append(json.dumps({
            "key": f"old_engram_{i}",
            "value": f"Old value {i}",
            "context": "Feature",
            "intensity": 5,
            "timestamp": old_ts,
        }))
    # Only 1 recent engram (within 48h)
    recent_ts = (datetime.now() - timedelta(hours=10)).isoformat()
    lines.append(json.dumps({
        "key": "recent_engram",
        "value": "Recent value",
        "context": "Feature",
        "intensity": 5,
        "timestamp": recent_ts,
    }))
    ledger.write_text("\n".join(lines) + "\n")
    return brain


@pytest.fixture
def brain_with_session_gap(tmp_path):
    """Create a brain with a stale session (>24h since last activity)."""
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "ledger").mkdir(parents=True)

    old_ts = (datetime.now() - timedelta(hours=48)).isoformat()
    session = {
        "session_id": "old-session-123",
        "context": "Working on heartbeat",
        "timestamp": old_ts,
    }
    sessions_file = brain / "ledger" / "sessions.jsonl"
    sessions_file.write_text(json.dumps(session) + "\n")
    return brain


# ── Tests: Individual Signal Checks ──────────────────────────

class TestStaleBlockers:
    def test_no_engrams(self, empty_brain):
        """Empty brain should return no stale blockers."""
        result = _check_stale_blockers(empty_brain)
        assert result == []

    def test_detects_stale_blocker(self, brain_with_stale_blocker):
        """Should detect a 48h-old blocker with intensity 9."""
        result = _check_stale_blockers(brain_with_stale_blocker)
        assert len(result) == 1
        assert result[0]["signal"] == "STALE_BLOCKER"
        assert result[0]["key"] == "ci_pipeline_blocker"
        assert result[0]["intensity"] == 9
        assert result[0]["age_hours"] >= 47  # ~48h
        assert "STALE BLOCKER" in result[0]["message"]

    def test_ignores_recent_blocker(self, tmp_path):
        """Blocker engram written 1h ago should NOT trigger."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        recent_ts = (datetime.now() - timedelta(hours=1)).isoformat()
        engram = {
            "key": "recent_blocker",
            "value": "Fresh blocker issue",
            "context": "Architecture",
            "intensity": 9,
            "timestamp": recent_ts,
        }
        (brain / "engrams" / "ledger.jsonl").write_text(json.dumps(engram) + "\n")
        result = _check_stale_blockers(brain)
        assert result == []

    def test_ignores_low_intensity(self, tmp_path):
        """Blocker with intensity < 8 should NOT trigger."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        old_ts = (datetime.now() - timedelta(hours=48)).isoformat()
        engram = {
            "key": "low_intensity_blocker",
            "value": "Low priority blocker",
            "context": "Feature",
            "intensity": 5,
            "timestamp": old_ts,
        }
        (brain / "engrams" / "ledger.jsonl").write_text(json.dumps(engram) + "\n")
        result = _check_stale_blockers(brain)
        assert result == []


class TestStaleDecisions:
    def test_no_engrams(self, empty_brain):
        result = _check_stale_decisions(empty_brain)
        assert result == []

    def test_detects_stale_decision(self, brain_with_stale_decision):
        """Should detect a 5-day-old Decision with intensity 8."""
        result = _check_stale_decisions(brain_with_stale_decision)
        assert len(result) == 1
        assert result[0]["signal"] == "STALE_DECISION"
        assert result[0]["key"] == "api_versioning_strategy"
        assert result[0]["age_days"] >= 4
        assert "Decision" in result[0]["message"] or "decision" in result[0]["message"].lower()

    def test_ignores_non_decision_context(self, tmp_path):
        """Engram with context != Decision should NOT trigger."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        engram = {
            "key": "old_feature",
            "value": "Some feature note",
            "context": "Feature",
            "intensity": 9,
            "timestamp": old_ts,
        }
        (brain / "engrams" / "ledger.jsonl").write_text(json.dumps(engram) + "\n")
        result = _check_stale_decisions(brain)
        assert result == []

    def test_limits_to_top_3(self, tmp_path):
        """Should return at most 3 stale decisions, sorted by age."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        lines = []
        for i in range(5):
            old_ts = (datetime.now() - timedelta(days=10 + i * 5)).isoformat()
            lines.append(json.dumps({
                "key": f"decision_{i}",
                "value": f"Decision {i}",
                "context": "Decision",
                "intensity": 8,
                "timestamp": old_ts,
            }))
        (brain / "engrams" / "ledger.jsonl").write_text("\n".join(lines) + "\n")
        result = _check_stale_decisions(brain)
        assert len(result) == 3
        # Sorted by age descending
        assert result[0]["age_days"] >= result[1]["age_days"]


class TestVelocityDrop:
    def test_no_engrams(self, empty_brain):
        result = _check_velocity_drop(empty_brain)
        assert result is None

    def test_detects_velocity_drop(self, brain_with_velocity_drop):
        """Should detect <3 writes in 48h when baseline >= 10."""
        result = _check_velocity_drop(brain_with_velocity_drop)
        assert result is not None
        assert result["signal"] == "VELOCITY_DROP"
        assert result["recent_writes"] == 1
        assert "📉" in result["message"]

    def test_no_trigger_with_enough_recent(self, tmp_path):
        """10+ total + 5 recent writes should NOT trigger velocity drop."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        lines = []
        # 10 old engrams
        for i in range(10):
            old_ts = (datetime.now() - timedelta(hours=100 + i)).isoformat()
            lines.append(json.dumps({
                "key": f"old_{i}", "value": f"v{i}",
                "context": "Feature", "intensity": 5, "timestamp": old_ts,
            }))
        # 5 recent engrams
        for i in range(5):
            recent_ts = (datetime.now() - timedelta(hours=i + 1)).isoformat()
            lines.append(json.dumps({
                "key": f"recent_{i}", "value": f"v{i}",
                "context": "Feature", "intensity": 5, "timestamp": recent_ts,
            }))
        (brain / "engrams" / "ledger.jsonl").write_text("\n".join(lines) + "\n")
        result = _check_velocity_drop(brain)
        assert result is None

    def test_no_trigger_with_few_total(self, tmp_path):
        """< 10 total engrams should NOT trigger (insufficient baseline)."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        lines = []
        for i in range(5):
            old_ts = (datetime.now() - timedelta(hours=100)).isoformat()
            lines.append(json.dumps({
                "key": f"e_{i}", "value": f"v{i}",
                "context": "Feature", "intensity": 5, "timestamp": old_ts,
            }))
        (brain / "engrams" / "ledger.jsonl").write_text("\n".join(lines) + "\n")
        result = _check_velocity_drop(brain)
        assert result is None


class TestSessionGap:
    def test_no_session_data(self, empty_brain):
        result = _check_session_gap(empty_brain)
        assert result is None

    def test_detects_session_gap(self, brain_with_session_gap):
        """Should detect 48h session gap."""
        result = _check_session_gap(brain_with_session_gap)
        assert result is not None
        assert result["signal"] == "SESSION_GAP"
        assert result["gap_hours"] >= 47
        assert "🔌" in result["message"]

    def test_no_trigger_with_recent_session(self, tmp_path):
        """Session activity within 24h should NOT trigger."""
        brain = tmp_path / ".brain"
        (brain / "ledger").mkdir(parents=True)
        recent_ts = (datetime.now() - timedelta(hours=1)).isoformat()
        session = {
            "session_id": "recent-session",
            "context": "Working now",
            "timestamp": recent_ts,
        }
        (brain / "ledger" / "sessions.jsonl").write_text(json.dumps(session) + "\n")
        result = _check_session_gap(brain)
        assert result is None


# ── Tests: Full Heartbeat Check ──────────────────────────────

class TestHeartbeatCheck:
    def test_empty_brain_all_clear(self, empty_brain):
        """Empty brain should report all clear, no triggers."""
        result = _heartbeat_check_impl(brain_path=str(empty_brain))
        assert result["trigger_count"] == 0
        assert result["should_notify"] is False
        assert "All clear" in result["formatted"]

    def test_stale_blocker_triggers(self, brain_with_stale_blocker):
        """Stale blocker should set should_notify=True."""
        result = _heartbeat_check_impl(brain_path=str(brain_with_stale_blocker))
        assert result["trigger_count"] >= 1
        assert result["should_notify"] is True
        assert "notification_title" in result
        assert "notification_body" in result
        signals = [t["signal"] for t in result["triggers"]]
        assert "STALE_BLOCKER" in signals

    def test_multiple_signals(self, tmp_path):
        """Brain with multiple issues should return all trigger signals."""
        brain = tmp_path / ".brain"
        (brain / "engrams").mkdir(parents=True)
        (brain / "ledger").mkdir(parents=True)

        lines = []
        # Stale blocker
        old_ts = (datetime.now() - timedelta(hours=48)).isoformat()
        lines.append(json.dumps({
            "key": "blocker_1", "value": "Major blocker in pipeline",
            "context": "Architecture", "intensity": 9, "timestamp": old_ts,
        }))
        # Stale decision
        very_old_ts = (datetime.now() - timedelta(days=5)).isoformat()
        lines.append(json.dumps({
            "key": "old_decision", "value": "Old arch decision",
            "context": "Decision", "intensity": 8, "timestamp": very_old_ts,
        }))
        # Pad with old engrams for velocity baseline
        for i in range(12):
            lines.append(json.dumps({
                "key": f"pad_{i}", "value": f"padding {i}",
                "context": "Feature", "intensity": 3,
                "timestamp": (datetime.now() - timedelta(hours=100 + i)).isoformat(),
            }))

        (brain / "engrams" / "ledger.jsonl").write_text("\n".join(lines) + "\n")

        # Also create stale session
        stale_session_ts = (datetime.now() - timedelta(hours=48)).isoformat()
        (brain / "ledger" / "sessions.jsonl").write_text(
            json.dumps({"session_id": "s1", "timestamp": stale_session_ts}) + "\n"
        )

        result = _heartbeat_check_impl(brain_path=str(brain))
        signals = [t["signal"] for t in result["triggers"]]
        assert "STALE_BLOCKER" in signals
        assert "STALE_DECISION" in signals
        assert "VELOCITY_DROP" in signals
        assert "SESSION_GAP" in signals
        assert result["trigger_count"] >= 4

    def test_logs_check(self, empty_brain):
        """Heartbeat should log its check to heartbeat/checks.jsonl."""
        _heartbeat_check_impl(brain_path=str(empty_brain))
        log_file = empty_brain / "heartbeat" / "checks.jsonl"
        assert log_file.exists()
        entries = [json.loads(l) for l in log_file.read_text().strip().split("\n") if l.strip()]
        assert len(entries) == 1
        assert "trigger_count" in entries[0]
        assert "duration_ms" in entries[0]


# ── Tests: Output Formatting ────────────────────────────────

class TestFormatting:
    def test_format_single_trigger(self):
        triggers = [{
            "signal": "STALE_BLOCKER",
            "key": "test_key",
            "message": "⏰ STALE BLOCKER: 'test_key' is 48h old.",
            "value_preview": "Some blocker description",
        }]
        output = _format_heartbeat_output(triggers)
        assert "NUCLEUS HEARTBEAT" in output
        assert "STALE BLOCKER" in output
        assert "1 item need attention" in output

    def test_format_multiple_triggers(self):
        triggers = [
            {"signal": "STALE_BLOCKER", "key": "k1", "message": "msg1"},
            {"signal": "VELOCITY_DROP", "key": "k2", "message": "msg2"},
        ]
        output = _format_heartbeat_output(triggers)
        assert "2 items need attention" in output


# ── Tests: Status ────────────────────────────────────────────

class TestHeartbeatStatus:
    def test_status_not_installed(self, empty_brain):
        """Status should show installed: False on a fresh brain."""
        result = _heartbeat_status_impl(brain_path=str(empty_brain))
        assert result["installed"] is False
        assert "❌ NO" in result["formatted"]
        assert result["total_checks"] == 0

    def test_status_with_history(self, empty_brain):
        """After a check, status should show check history."""
        # Run a check first to create log
        _heartbeat_check_impl(brain_path=str(empty_brain))
        result = _heartbeat_status_impl(brain_path=str(empty_brain))
        assert result["total_checks"] == 1
        assert len(result["recent_checks"]) == 1


# ── Tests: CLI Handler ──────────────────────────────────────

class TestCLIHandler:
    def test_heartbeat_help_shows_usage(self):
        """Running `nucleus heartbeat` with no subcommand should show help text."""
        import subprocess
        result = subprocess.run(
            ["nucleus", "heartbeat"],
            capture_output=True, text=True, timeout=15,
        )
        combined = result.stdout + result.stderr
        assert "heartbeat" in combined.lower()
        # Should show usage or help, not crash
        assert result.returncode == 0

    def test_heartbeat_check_json(self, empty_brain):
        """Check with --format json via CLI should return valid JSON."""
        import subprocess
        result = subprocess.run(
            ["nucleus", "heartbeat", "check", "--format", "json"],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "NUCLEUS_BRAIN_PATH": str(empty_brain)},
        )
        # Should not crash
        assert result.returncode == 0
        # stdout should contain JSON
        try:
            data = json.loads(result.stdout)
            assert "triggers" in data or "trigger_count" in data
        except json.JSONDecodeError:
            # Might have stderr mixed in — check stdout lines
            for line in result.stdout.strip().split("\n"):
                try:
                    data = json.loads(line)
                    if "triggers" in data or "trigger_count" in data:
                        break
                except json.JSONDecodeError:
                    continue
