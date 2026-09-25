"""Comprehensive tests for mcp_server_nucleus.watchdog.stall.

Covers _parse_body, _expects_reply, _in_reply_to, _iso_to_ts, age_min,
resolve_brain_path, scan_bucket, _iter_relays, find_ack_then_stalls,
find_refuse_without_reason, and main.
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.watchdog import stall
from mcp_server_nucleus.watchdog.stall import (
    _parse_body,
    _expects_reply,
    _in_reply_to,
    _iso_to_ts,
    age_min,
    resolve_brain_path,
    scan_bucket,
    find_ack_then_stalls,
    find_refuse_without_reason,
    main,
    LIVE_BUCKETS,
)


# ── _parse_body ──

class TestParseBody:
    def test_dict_input(self):
        d = {"key": "val"}
        assert _parse_body(d) == d

    def test_string_json(self):
        assert _parse_body('{"key": "val"}') == {"key": "val"}

    def test_string_invalid_json(self):
        assert _parse_body("not json") == {}

    def test_string_json_array(self):
        assert _parse_body("[1, 2]") == {}

    def test_none_input(self):
        assert _parse_body(None) == {}

    def test_int_input(self):
        assert _parse_body(42) == {}


# ── _expects_reply ──

class TestExpectsReply:
    def test_directive_tag(self):
        assert _expects_reply({"body": '{"tags": ["directive"]}'}) is True

    def test_question_tag(self):
        assert _expects_reply({"body": '{"tags": ["question-to-peer"]}'}) is True

    def test_convergence_tag(self):
        assert _expects_reply({"body": '{"tags": ["convergence-call"]}'}) is True

    def test_no_reply_tags(self):
        assert _expects_reply({"body": '{"tags": ["random"]}'}) is False

    def test_summary_ship_report(self):
        assert _expects_reply({"body": '{"summary": "please ship-report now"}'}) is True

    def test_summary_concur(self):
        assert _expects_reply({"body": '{"summary": "need to concur on this"}'}) is True

    def test_summary_reply_shape(self):
        assert _expects_reply({"body": '{"summary": "reply shape needed"}'}) is True

    def test_summary_no_match(self):
        assert _expects_reply({"body": '{"summary": "just chatting"}'}) is False

    def test_no_body(self):
        assert _expects_reply({}) is False

    def test_body_dict(self):
        assert _expects_reply({"body": {"tags": ["directive"]}}) is True


# ── _in_reply_to ──

class TestInReplyTo:
    def test_from_context(self):
        assert _in_reply_to({"context": {"in_reply_to": "msg-123"}}) == "msg-123"

    def test_from_body_string(self):
        assert _in_reply_to({"body": '{"in_reply_to": "msg-456"}'}) == "msg-456"

    def test_from_body_dict(self):
        assert _in_reply_to({"body": {"in_reply_to": "msg-789"}}) == "msg-789"

    def test_context_takes_priority(self):
        data = {
            "context": {"in_reply_to": "from-context"},
            "body": '{"in_reply_to": "from-body"}',
        }
        assert _in_reply_to(data) == "from-context"

    def test_none_when_missing(self):
        assert _in_reply_to({}) is None

    def test_empty_string_returns_none(self):
        assert _in_reply_to({"context": {"in_reply_to": ""}}) is None

    def test_non_string_value(self):
        assert _in_reply_to({"context": {"in_reply_to": 123}}) is None

    def test_body_fallback_when_context_missing(self):
        assert _in_reply_to({"body": '{"in_reply_to": "msg-body"}'}) == "msg-body"


# ── _iso_to_ts ──

class TestIsoToTs:
    def test_valid_iso(self):
        ts = _iso_to_ts("2026-01-01T00:00:00+00:00")
        assert ts is not None
        assert ts > 0

    def test_valid_iso_z(self):
        ts = _iso_to_ts("2026-01-01T00:00:00Z")
        assert ts is not None

    def test_none_input(self):
        assert _iso_to_ts(None) is None

    def test_empty_string(self):
        assert _iso_to_ts("") is None

    def test_invalid_string(self):
        assert _iso_to_ts("not a date") is None


# ── age_min ──

class TestAgeMin:
    def test_none_ts(self):
        assert age_min(1000.0, None) is None

    def test_positive_age(self):
        now = 1000.0
        ts = 900.0  # 100 seconds ago = 1.67 min
        result = age_min(now, ts)
        assert result == 1.7

    def test_zero_age(self):
        now = 1000.0
        result = age_min(now, 1000.0)
        assert result == 0.0

    def test_negative_clamped(self):
        now = 1000.0
        ts = 1100.0  # future timestamp
        result = age_min(now, ts)
        assert result == 0.0


# ── resolve_brain_path ──

class TestResolveBrainPath:
    def test_nucleus_brain_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN", str(tmp_path / "brain1"))
        assert resolve_brain_path(None) == tmp_path / "brain1"

    def test_cli_value(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_BRAIN", raising=False)
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        assert resolve_brain_path(str(tmp_path / "cli_brain")) == tmp_path / "cli_brain"

    def test_nucleus_brain_wins_over_cli(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN", str(tmp_path / "env_brain"))
        assert resolve_brain_path(str(tmp_path / "cli_brain")) == tmp_path / "env_brain"

    def test_legacy_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_BRAIN", raising=False)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "legacy_brain"))
        assert resolve_brain_path(None) == tmp_path / "legacy_brain"

    def test_default_fallback(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN", raising=False)
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        result = resolve_brain_path(None)
        assert isinstance(result, Path)


# ── scan_bucket ──

class TestScanBucket:
    def test_nonexistent_dir(self, tmp_path):
        result = scan_bucket(tmp_path / "nonexistent")
        assert result == (None, None, 0, 0, False)

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        result = scan_bucket(d)
        assert result == (None, None, 0, 0, True)

    def test_with_read_relay(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        relay = {"read": True, "created_at": "2026-01-01T00:00:00Z"}
        (d / "msg1.json").write_text(json.dumps(relay))
        youngest_any, youngest_unread, total, unread, _present = scan_bucket(d)
        assert total == 1
        assert unread == 0
        assert youngest_any is not None
        assert youngest_unread is None

    def test_with_unread_relay(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        relay = {"read": False, "created_at": "2026-01-01T00:00:00Z"}
        (d / "msg1.json").write_text(json.dumps(relay))
        youngest_any, youngest_unread, total, unread, _present = scan_bucket(d)
        assert total == 1
        assert unread == 1
        assert youngest_unread is not None

    def test_with_unread_no_created_at(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        relay = {"read": False}
        (d / "msg1.json").write_text(json.dumps(relay))
        youngest_any, youngest_unread, total, unread, _present = scan_bucket(d)
        assert total == 1
        assert unread == 1
        assert youngest_unread is not None

    def test_with_invalid_json(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        (d / "msg1.json").write_text("not json")
        youngest_any, youngest_unread, total, unread, _present = scan_bucket(d)
        assert total == 1
        assert unread == 1
        assert youngest_unread is not None

    def test_with_invalid_created_at(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        relay = {"read": False, "created_at": "not-a-date"}
        (d / "msg1.json").write_text(json.dumps(relay))
        youngest_any, youngest_unread, total, unread, _present = scan_bucket(d)
        assert total == 1
        assert unread == 1
        # Should fall back to mtime
        assert youngest_unread is not None

    def test_multiple_relays(self, tmp_path):
        d = tmp_path / "bucket"
        d.mkdir()
        old_ts = "2020-01-01T00:00:00Z"
        new_ts = "2026-01-01T00:00:00Z"
        (d / "msg1.json").write_text(json.dumps({"read": False, "created_at": old_ts}))
        (d / "msg2.json").write_text(json.dumps({"read": False, "created_at": new_ts}))
        youngest_any, youngest_unread, total, unread, _present = scan_bucket(d)
        assert total == 2
        assert unread == 2
        # Youngest unread should be the newer one
        expected_new = datetime.fromisoformat(new_ts.replace("Z", "+00:00")).timestamp()
        assert youngest_unread == expected_new


# ── _iter_relays ──

class TestIterRelays:
    def test_nonexistent_dir(self, tmp_path):
        relays = list(stall._iter_relays(tmp_path / "nonexistent"))
        assert relays == []

    def test_with_relays(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        (bucket / "msg1.json").write_text(json.dumps({"id": "1", "read": False}))
        relays = list(stall._iter_relays(root))
        assert len(relays) == 1
        assert relays[0][0] == "cowork"
        assert relays[0][2]["id"] == "1"

    def test_skips_invalid_json(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        (bucket / "msg1.json").write_text("not json")
        (bucket / "msg2.json").write_text(json.dumps({"id": "2"}))
        relays = list(stall._iter_relays(root))
        assert len(relays) == 1

    def test_skips_non_dict(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        (bucket / "msg1.json").write_text(json.dumps([1, 2, 3]))
        relays = list(stall._iter_relays(root))
        assert relays == []

    def test_skips_non_dir_buckets(self, tmp_path):
        root = tmp_path / "relay"
        root.mkdir(parents=True)
        (root / "file.json").write_text("x")
        relays = list(stall._iter_relays(root))
        assert relays == []


# ── find_ack_then_stalls ──

class TestFindAckThenStalls:
    def test_no_relays(self, tmp_path):
        result = find_ack_then_stalls(tmp_path / "relay", time.time(), 30)
        assert result == []

    def test_stalled_ack(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        # Old ack that expects reply, no follow-on
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        relay = {
            "id": "msg-1",
            "read_at": old_time,
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert len(result) == 1
        assert result[0]["id"] == "msg-1"
        assert result[0]["bucket"] == "cowork"

    def test_acked_and_replied(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        original = {
            "id": "msg-1",
            "read_at": old_time,
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        reply = {
            "id": "msg-2",
            "context": {"in_reply_to": "msg-1"},
            "subject": "Re: Need review",
        }
        (bucket / "msg1.json").write_text(json.dumps(original))
        (bucket / "msg2.json").write_text(json.dumps(reply))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert result == []

    def test_not_old_enough(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        recent_time = datetime.now(timezone.utc).isoformat()
        relay = {
            "id": "msg-1",
            "read_at": recent_time,
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert result == []

    def test_no_read_at(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert result == []

    def test_no_expects_reply(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        relay = {
            "id": "msg-1",
            "read_at": old_time,
            "subject": "FYI",
            "body": json.dumps({"tags": ["info"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert result == []

    def test_non_live_bucket(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "other_bucket"
        bucket.mkdir(parents=True)
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        relay = {
            "id": "msg-1",
            "read_at": old_time,
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert result == []

    def test_invalid_read_at(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "read_at": "not-a-date",
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        now = time.time()
        result = find_ack_then_stalls(root, now, 30)
        assert result == []


# ── find_refuse_without_reason ──

class TestFindRefuseWithoutReason:
    def test_no_relays(self, tmp_path):
        result = find_refuse_without_reason(tmp_path / "relay")
        assert result == []

    def test_refuse_no_reason(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "I refuse this",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"tags": [], "reason": "short"}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert len(result) == 1
        assert result[0]["id"] == "msg-1"
        assert result[0]["reason_len"] == len("short")

    def test_refuse_with_reason(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "I refuse this",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"reason": "This is a very long reason that explains why I refused the task"}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert result == []

    def test_refuse_tag(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "Normal subject",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"tags": ["kicked"], "reason": ""}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert len(result) == 1

    def test_not_refuse(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "Normal subject",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"tags": [], "reason": ""}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert result == []

    def test_no_in_reply_to(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "I refuse this",
            "body": json.dumps({"tags": [], "reason": ""}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert result == []

    def test_non_live_bucket(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "other"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "I refuse this",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"tags": [], "reason": ""}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert result == []

    def test_refuse_pattern_kickback(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "Kickback on this item",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"reason": ""}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert len(result) == 1

    def test_refuse_pattern_skipped(self, tmp_path):
        root = tmp_path / "relay"
        bucket = root / "cowork"
        bucket.mkdir(parents=True)
        relay = {
            "id": "msg-1",
            "subject": "I skipped this task",
            "context": {"in_reply_to": "orig-1"},
            "body": json.dumps({"reason": ""}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))
        result = find_refuse_without_reason(root)
        assert len(result) == 1


# ── main ──

class TestMain:
    def test_healthy_no_relays(self, tmp_path, monkeypatch, capsys):
        # Real "healthy" = relay root exists with empty buckets. A missing
        # relay root is indeterminate (test_indeterminate_no_relay_dir below).
        brain = tmp_path / "brain"
        relay_root = brain / "relay"
        for b in LIVE_BUCKETS:
            (relay_root / b).mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main([])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["stalled"] is False
        assert output["total_unread_across_buckets"] == 0
        assert output.get("indeterminate") is False

    def test_indeterminate_no_relay_dir(self, tmp_path, monkeypatch, capsys):
        # A missing .brain/relay/ (all buckets absent) is NOT "healthy" —
        # the watchdog could not check anything. Exit 2 = indeterminate.
        brain = tmp_path / "brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main([])
        assert exit_code == 2
        output = json.loads(capsys.readouterr().out)
        assert output["indeterminate"] is True
        assert output["stalled"] is False
        assert "indeterminate_reason" in output
        assert len(output["absent_buckets"]) == len(LIVE_BUCKETS)

    def test_stall_detected(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "brain"
        relay_root = brain / "relay"
        bucket = relay_root / "cowork"
        bucket.mkdir(parents=True)
        # Create an old unread relay
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        relay = {"read": False, "created_at": old_time}
        (bucket / "msg1.json").write_text(json.dumps(relay))
        # Set the file mtime to old time
        old_ts = datetime.fromisoformat(old_time.replace("Z", "+00:00")).timestamp()
        os.utime(bucket / "msg1.json", (old_ts, old_ts))

        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main(["--threshold-min", "30"])
        assert exit_code == 1
        output = json.loads(capsys.readouterr().out)
        assert output["stalled"] is True
        assert "cowork" in output["stalled_buckets"]

    def test_not_stalled_recent(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "brain"
        relay_root = brain / "relay"
        bucket = relay_root / "cowork"
        bucket.mkdir(parents=True)
        relay = {"read": False, "created_at": datetime.now(timezone.utc).isoformat()}
        (bucket / "msg1.json").write_text(json.dumps(relay))

        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main(["--threshold-min", "30"])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["stalled"] is False

    def test_clock_drift(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "brain"
        relay_root = brain / "relay"
        bucket = relay_root / "cowork"
        bucket.mkdir(parents=True)
        # Future timestamp = clock drift
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        relay = {"read": False, "created_at": future_time}
        (bucket / "msg1.json").write_text(json.dumps(relay))
        future_ts = datetime.fromisoformat(future_time.replace("Z", "+00:00")).timestamp()
        os.utime(bucket / "msg1.json", (future_ts, future_ts))

        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main(["--threshold-min", "30"])
        output = json.loads(capsys.readouterr().out)
        assert "cowork" in output["clock_drift_buckets"]

    def test_with_ack_then_stall(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "brain"
        relay_root = brain / "relay"
        bucket = relay_root / "cowork"
        bucket.mkdir(parents=True)
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        relay = {
            "id": "msg-1",
            "read_at": old_time,
            "subject": "Need review",
            "body": json.dumps({"tags": ["directive"]}),
        }
        (bucket / "msg1.json").write_text(json.dumps(relay))

        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main(["--ack-stall-threshold-min", "30"])
        output = json.loads(capsys.readouterr().out)
        assert output["silent_mode_detected"] is True
        assert len(output["ack_then_stalls"]) == 1

    def test_ball_stopped_in(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "brain"
        relay_root = brain / "relay"
        # Create stalls in two buckets
        for bname in ["cowork", "claude_code_main"]:
            bucket = relay_root / bname
            bucket.mkdir(parents=True)
            old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
            relay = {"read": False, "created_at": old_time}
            (bucket / "msg1.json").write_text(json.dumps(relay))
            old_ts = datetime.fromisoformat(old_time.replace("Z", "+00:00")).timestamp()
            os.utime(bucket / "msg1.json", (old_ts, old_ts))

        monkeypatch.setenv("NUCLEUS_BRAIN", str(brain))
        exit_code = main(["--threshold-min", "30"])
        output = json.loads(capsys.readouterr().out)
        assert "ball_stopped_in" in output
        assert output["ball_stopped_in"] in ["cowork", "claude_code_main"]

    def test_custom_brain_path_arg(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "custom_brain"
        relay_root = brain / "relay"
        bucket = relay_root / "cowork"
        bucket.mkdir(parents=True)
        monkeypatch.delenv("NUCLEUS_BRAIN", raising=False)
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        exit_code = main(["--brain-path", str(brain)])
        assert exit_code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["stalled"] is False
