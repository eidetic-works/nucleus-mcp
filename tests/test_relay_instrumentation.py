"""Two-axis instrumentation for the relay cold-start gate.

Fire and skip events land in .brain/relay/event_log.jsonl. Human
classifications of skips land in .brain/relay/skip_classifications.jsonl.
Stats are derived on demand.
"""

import json
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import relay_ops
from mcp_server_nucleus.runtime.common import get_brain_path


@pytest.fixture(autouse=True)
def _isolated_brain(tmp_path, monkeypatch):
    """Force each test to use a fresh tmp brain dir even when the outer shell
    has NUCLEAR_BRAIN_PATH pointed at the real repo .brain."""
    test_brain = tmp_path / ".brain"
    (test_brain / "relay").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(test_brain))
    yield


def _event_log() -> Path:
    return get_brain_path() / "relay" / "event_log.jsonl"


def _classifications_log() -> Path:
    return get_brain_path() / "relay" / "skip_classifications.jsonl"


def test_log_event_fire_appends_entry():
    r = relay_ops.relay_log_event(
        event="fire",
        side="claude_code",
        subject="decision lock",
        tags=["decision"],
        match_reason="thread-reply: relay_abc",
        priority="high",
        message_id="relay_xyz",
        in_reply_to="relay_abc",
    )
    assert r["logged"] is True

    lines = _event_log().read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["event"] == "fire"
    assert entry["side"] == "claude_code"
    assert entry["subject"] == "decision lock"
    assert entry["tags"] == ["decision"]
    assert entry["match_reason"] == "thread-reply: relay_abc"
    assert entry["priority"] == "high"
    assert entry["message_id"] == "relay_xyz"
    assert entry["in_reply_to"] == "relay_abc"
    assert entry["ts"].endswith("Z")


def test_log_event_skip_no_message_id():
    r = relay_ops.relay_log_event(
        event="skip",
        side="cowork",
        subject="ambient comment",
        tags=["decision"],
        match_reason="none — cold-start default",
        priority="normal",
    )
    assert r["logged"] is True
    entry = json.loads(_event_log().read_text().strip().splitlines()[-1])
    assert entry["event"] == "skip"
    assert entry["message_id"] is None
    assert entry["in_reply_to"] is None


def test_log_event_rejects_invalid_event_type():
    r = relay_ops.relay_log_event(event="bogus", side="x", subject="y")
    assert r["logged"] is False
    assert "event must be one of" in r["error"]
    assert not _event_log().exists()


def test_skip_review_returns_only_unclassified():
    relay_ops.relay_log_event(
        event="skip", side="claude_code", subject="first skip",
        match_reason="none — cold-start default",
    )
    relay_ops.relay_log_event(
        event="skip", side="claude_code", subject="second skip",
        match_reason="none — cold-start default",
    )
    relay_ops.relay_log_event(
        event="fire", side="claude_code", subject="a fire",
        match_reason="keyword: foo", message_id="relay_fire_1",
    )

    # Classify one of the skips
    events = [json.loads(l) for l in _event_log().read_text().strip().splitlines()]
    first_skip = next(e for e in events if e["subject"] == "first skip")
    c = relay_ops.relay_classify_skip(
        ts=first_skip["ts"],
        subject=first_skip["subject"],
        classification="rightly_skipped",
    )
    assert c["classified"] is True

    review = relay_ops.relay_skip_review()
    assert review["total_skips"] == 2
    assert review["total_classified"] == 1
    assert review["unclassified_count"] == 1
    assert review["unclassified"][0]["subject"] == "second skip"


def test_skip_review_sorts_newest_first_and_respects_limit():
    # Create three skips; they'll have distinct ts because time advances.
    import time
    for i in range(3):
        relay_ops.relay_log_event(
            event="skip", side="claude_code", subject=f"skip_{i}",
            match_reason="none — cold-start default",
        )
        time.sleep(0.001)

    review = relay_ops.relay_skip_review(limit=2)
    subjects = [s["subject"] for s in review["unclassified"]]
    assert len(subjects) == 2
    assert subjects == ["skip_2", "skip_1"]


def test_classify_skip_rejects_invalid_classification():
    c = relay_ops.relay_classify_skip(
        ts="2026-04-14T20:00:00Z", subject="x", classification="maybe",
    )
    assert c["classified"] is False
    assert "classification must be one of" in c["error"]


def test_classify_skip_sidecar_leaves_event_log_untouched():
    relay_ops.relay_log_event(
        event="skip", side="claude_code", subject="preserve me",
        match_reason="none — cold-start default",
    )
    before = _event_log().read_text()
    entry = json.loads(before.strip().splitlines()[0])
    relay_ops.relay_classify_skip(
        ts=entry["ts"], subject=entry["subject"],
        classification="should_have_fired", note="missed signal",
    )
    after = _event_log().read_text()
    assert before == after

    classification = json.loads(_classifications_log().read_text().strip().splitlines()[0])
    assert classification["classification"] == "should_have_fired"
    assert classification["note"] == "missed signal"


def test_event_stats_empty_log():
    stats = relay_ops.relay_event_stats()
    assert stats["total_fires"] == 0
    assert stats["total_skips"] == 0
    assert stats["override_rate"] == 0.0
    assert stats["skip_rate"] == 0.0


def test_event_stats_computes_both_axes():
    # 3 fires (1 is an override — cold-start + priority=high + no question-to-peer)
    relay_ops.relay_log_event(
        event="fire", side="claude_code", subject="override fire",
        tags=["decision"], match_reason="none — cold-start default",
        priority="high", message_id="r1",
    )
    relay_ops.relay_log_event(
        event="fire", side="claude_code", subject="keyword fire",
        tags=["decision"], match_reason="decision", priority="normal",
        message_id="r2",
    )
    relay_ops.relay_log_event(
        event="fire", side="claude_code", subject="thread reply fire",
        tags=["decision"], match_reason="thread-reply: relay_abc",
        priority="high", message_id="r3",
    )
    # 1 skip
    relay_ops.relay_log_event(
        event="skip", side="claude_code", subject="silenced",
        tags=["artifact-ref"], match_reason="none — cold-start default",
    )

    stats = relay_ops.relay_event_stats()
    assert stats["total_fires"] == 3
    assert stats["total_skips"] == 1
    assert stats["total_attempts"] == 4
    assert stats["override_count"] == 1
    # 1 override / 3 fires
    assert stats["override_rate"] == round(1 / 3, 4)
    # 1 skip / 4 attempts
    assert stats["skip_rate"] == round(1 / 4, 4)


def test_event_stats_question_to_peer_high_priority_is_not_override():
    # question-to-peer at cold-start with priority=high — legitimate, not an override
    relay_ops.relay_log_event(
        event="fire", side="claude_code", subject="ask peer",
        tags=["question-to-peer"], match_reason="none — cold-start default",
        priority="high", message_id="r_qtp",
    )
    stats = relay_ops.relay_event_stats()
    assert stats["override_count"] == 0


def test_read_jsonl_tolerates_malformed_lines():
    path = _event_log()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"event": "fire", "subject": "ok"}\nnot-json\n{"event": "skip", "subject": "ok2"}\n')
    out = relay_ops._read_jsonl(path)
    assert len(out) == 2
    assert out[0]["subject"] == "ok"
    assert out[1]["subject"] == "ok2"
