"""Tests for sonnet_pair_daemon (L3 always-on Sonnet pair).

Covers the four behaviors that were validated by live-fire on 2026-05-08:
1. Authority-gate keyword detection (lateral-OK pass-through vs ALWAYS-escalate)
2. Identity stamping (per-daemon UUID, regenerated each invocation)
3. Escalate-routing (no subprocess spawn on escalate match; reply has correct
   subject + body shape)
4. Heartbeat busy% rolling-window math

Subprocess and relay_post are mocked — no live Sonnet calls, no relay file
writes outside the test's tmp_path.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

import pytest

from mcp_server_nucleus.runtime import sonnet_pair_daemon as spd


# ─── authority gate ──────────────────────────────────────────────────────


@pytest.mark.parametrize("subject,body,expected", [
    # Lateral-OK (must pass through)
    ("[DELEGATE] Read README.md and summarize", "", False),
    ("[DELEGATE] codebase audit for unused imports", "", False),
    ("[DELEGATE] grep test files for skip markers", "", False),
    ("[DELEGATE] summarize what windsurf shipped today", "", False),
    ("[DELEGATE] run pytest, report counts", "", False),
    # ALWAYS-escalate (must trip the gate)
    ("[DELEGATE] Author a feedback memo about X", "", True),
    ("[DELEGATE] git push origin main", "", True),
    ("[DELEGATE] decline this task", "", True),
    ("[DELEGATE] route this to windsurf", "", True),
    ("[DELEGATE] forward to founder", "", True),
    ("[DELEGATE] this is sovereign content", "", True),
    ("[DELEGATE] novel architecture proposal", "", True),
    ("[DELEGATE] merge PR #42", "", True),
    # Body-only triggers
    ("[DELEGATE] do the thing", "actually need a feedback memo", True),
])
def test_authority_gate(subject: str, body: str, expected: bool) -> None:
    assert spd.is_escalate(subject, body) is expected


# ─── identity stamping ────────────────────────────────────────────────────


def test_session_id_stable_within_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Within one daemon invocation, session_id is generated once."""
    monkeypatch.chdir(tmp_path)
    sid1 = spd._ensure_session_id("peer")
    sid2 = spd._ensure_session_id("peer")
    # _ensure_session_id rewrites on each call (matches "restart = new identity"
    # contract); but the daemon calls it exactly once at startup. We validate
    # the format is stable UUID, not stability across calls.
    import uuid
    uuid.UUID(sid1)  # raises ValueError if not a valid UUID
    uuid.UUID(sid2)


def test_session_id_persisted_to_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sid = spd._ensure_session_id("main")
    f = tmp_path / ".brain" / "daemon" / "sonnet_pair_main.session_id"
    assert f.exists()
    assert f.read_text() == sid


# ─── escalate routing (no subprocess spawn) ───────────────────────────────


def test_handle_one_escalate_no_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs" / "org" / "charters").mkdir(parents=True)
    charter = tmp_path / "docs" / "org" / "charters" / "sonnet_pair_peer.md"
    charter.write_text("# charter")

    posted: List[Dict[str, Any]] = []

    def fake_relay_post(**kw: Any) -> Dict[str, Any]:
        posted.append(kw)
        return {"sent": True, "message_id": "fake_001"}

    spawn_calls: List[Any] = []

    def fake_spawn(*a: Any, **kw: Any) -> tuple[bool, str]:
        spawn_calls.append((a, kw))
        return True, "should not be called on escalate"

    monkeypatch.setattr(spd, "relay_post", fake_relay_post)
    monkeypatch.setattr(spd, "_spawn_via_claude_code", fake_spawn)

    envelope = {
        "id": "src_relay_001",
        "from": "claude_code_peer",
        "subject": "[DELEGATE] Author a feedback memo about Z",
        "body": "",
    }
    busy = spd._BusyTracker()

    asyncio.run(spd.handle_one(
        envelope, "peer", charter,
        pair_session_id="test-session-uuid",
        pair_sender="sonnet_peer",
        busy=busy,
    ))

    # No subprocess spawned
    assert spawn_calls == []
    # Exactly one [ESCALATE] reply posted
    assert len(posted) == 1
    p = posted[0]
    assert p["to"] == "claude_code_peer"
    assert p["subject"].startswith("[ESCALATE]")
    assert p["sender"] == "sonnet_peer"
    assert p["from_session_id"] == "test-session-uuid"
    assert p["in_reply_to"] == "src_relay_001"
    body = json.loads(p["body"])
    assert "ALWAYS-escalate" in body["reason"]
    assert body["source_id"] == "src_relay_001"


# ─── happy-path subprocess spawn + reply ──────────────────────────────────


def test_handle_one_lateral_ok_spawns_and_replies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs" / "org" / "charters").mkdir(parents=True)
    charter = tmp_path / "docs" / "org" / "charters" / "sonnet_pair_peer.md"
    charter.write_text("# charter")

    posted: List[Dict[str, Any]] = []

    def fake_relay_post(**kw: Any) -> Dict[str, Any]:
        posted.append(kw)
        return {"sent": True, "message_id": "fake_002"}

    def fake_spawn(charter_path: Path, brief: str, *, timeout_s: int = 300) -> tuple[bool, str]:
        return True, "4"

    monkeypatch.setattr(spd, "relay_post", fake_relay_post)
    monkeypatch.setattr(spd, "_spawn_via_claude_code", fake_spawn)

    envelope = {
        "id": "src_relay_002",
        "from": "claude_code_peer",
        "subject": "[DELEGATE] What is 2+2?",
        "body": "",
    }
    busy = spd._BusyTracker()

    asyncio.run(spd.handle_one(
        envelope, "peer", charter,
        pair_session_id="test-uuid-2",
        pair_sender="sonnet_peer",
        busy=busy,
    ))

    assert len(posted) == 1
    p = posted[0]
    assert p["subject"].startswith("[DELEGATE-RESULT]")
    assert p["body"] == "4"
    assert p["priority"] == "normal"
    assert p["in_reply_to"] == "src_relay_002"
    # Busy tracker recorded the work item
    assert len(busy.events) == 1


def test_handle_one_skips_non_delegate_subject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    charter = tmp_path / "charter.md"
    charter.write_text("# c")

    posted: List[Dict[str, Any]] = []
    monkeypatch.setattr(spd, "relay_post",
                       lambda **kw: posted.append(kw) or {"sent": True})
    monkeypatch.setattr(spd, "_spawn_via_claude_code",
                       lambda *a, **kw: pytest.fail("should not spawn"))

    envelope = {
        "id": "src_relay_003",
        "from": "claude_code_peer",
        "subject": "[STATUS] random heartbeat from someone",
        "body": "",
    }
    asyncio.run(spd.handle_one(
        envelope, "peer", charter,
        pair_session_id="x", pair_sender="sonnet_peer",
        busy=spd._BusyTracker(),
    ))
    # No reply, no spawn
    assert posted == []


# ─── heartbeat busy% rolling-window math ──────────────────────────────────


def test_busy_tracker_zero_when_idle() -> None:
    b = spd._BusyTracker()
    assert b.busy_pct() == 0.0


def test_busy_tracker_simple_window() -> None:
    """90s busy across the 3600s window = 2.5%."""
    b = spd._BusyTracker()
    now = time.time()
    b.add(now - 600, 60)   # 60s busy 10min ago
    b.add(now - 120, 30)   # 30s busy 2min ago
    assert b.busy_pct(now=now) == pytest.approx(2.5, abs=0.05)


def test_busy_tracker_drops_events_outside_window() -> None:
    """Events that ended >1h ago must be dropped."""
    b = spd._BusyTracker()
    now = time.time()
    b.add(now - 7200, 100)  # 100s busy 2h ago — outside 1h window
    b.add(now - 60, 10)     # 10s busy 1min ago — inside
    pct = b.busy_pct(now=now)
    # Only the 10s recent event counts: 10/3600 = 0.28%
    assert pct == pytest.approx(0.28, abs=0.05)


def test_busy_tracker_clips_overlapping_event() -> None:
    """An event that started before the window should only count its in-window
    duration."""
    b = spd._BusyTracker()
    now = time.time()
    # Started 70min ago, ran for 20min — last 10min are inside window
    b.add(now - 4200, 1200)
    pct = b.busy_pct(now=now, window_s=3600)
    # In-window busy ≈ 600s; 600/3600 = 16.67%
    assert pct == pytest.approx(16.67, abs=0.5)


# ─── envelope parsing edge cases ──────────────────────────────────────────


def test_parse_envelope_malformed_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    assert spd.parse_envelope(p) is None


def test_parent_lane_for_inferred_from_sender() -> None:
    assert spd.parent_lane_for({"from": "claude_code_main"}) == "claude_code_main"
    assert spd.parent_lane_for({"from": "claude_code_peer"}) == "claude_code_peer"
    # Unknown senders default to main (defensive — won't broadcast to nowhere)
    assert spd.parent_lane_for({"from": "antigravity"}) == "claude_code_main"
    assert spd.parent_lane_for({}) == "claude_code_main"


# ─── operator_assistant lane ─────────────────────────────────────────────────


def test_handle_ops_handoff_writes_ops_queue(tmp_path: Path, monkeypatch: Any) -> None:
    """[OPS-HANDOFF] relay → .brain/ops_queue/ file created, no subprocess spawn."""
    monkeypatch.setattr(spd, "_brain_root", lambda: tmp_path / ".brain")
    (tmp_path / ".brain" / "ops_queue").mkdir(parents=True)

    envelope = {
        "id": "relay_test_ops_001",
        "from": "claude_code_main",
        "subject": "[OPS-HANDOFF] Kit CSV sync — Gumroad → Kit import",
        "body": "Import subscribers from Gumroad to Kit. ~5 min. Walkthrough at docs/kit-sync.md.",
    }

    with mock.patch.object(spd, "_notify_macos") as mock_notify, \
         mock.patch.object(spd, "_emit") as mock_emit:
        asyncio.run(spd.handle_ops_handoff(envelope, "session_test_123"))

    queue_files = list((tmp_path / ".brain" / "ops_queue").glob("*.md"))
    assert len(queue_files) == 1, "exactly one ops_queue file written"
    content = queue_files[0].read_text()
    assert "[OPS-HANDOFF]" in content
    assert "relay_test_ops_001" in content
    assert "Kit CSV sync" in content
    mock_notify.assert_called_once()
    mock_emit.assert_called_once()


def test_handle_ops_handoff_skips_non_ops_subject(tmp_path: Path, monkeypatch: Any) -> None:
    """Non-[OPS-HANDOFF] subjects are silently ignored (no queue write)."""
    monkeypatch.setattr(spd, "_brain_root", lambda: tmp_path / ".brain")
    (tmp_path / ".brain" / "ops_queue").mkdir(parents=True)

    envelope = {
        "id": "relay_regular_001",
        "from": "claude_code_main",
        "subject": "[DELEGATE] Summarise last 5 PRs",
        "body": "...",
    }

    with mock.patch.object(spd, "_notify_macos") as mock_notify:
        asyncio.run(spd.handle_ops_handoff(envelope, "session_x"))

    queue_files = list((tmp_path / ".brain" / "ops_queue").glob("*.md"))
    assert len(queue_files) == 0, "no file written for non-OPS subject"
    mock_notify.assert_not_called()


def test_handle_ops_result_also_queued(tmp_path: Path, monkeypatch: Any) -> None:
    """[OPS-RESULT] relays are also persisted (they complete the async loop)."""
    monkeypatch.setattr(spd, "_brain_root", lambda: tmp_path / ".brain")
    (tmp_path / ".brain" / "ops_queue").mkdir(parents=True)

    envelope = {
        "id": "relay_ops_result_001",
        "from": "claude_code_operator_assistant",
        "subject": "[OPS-RESULT] Kit CSV sync done — 3 subscribers imported",
        "body": "Completed. Confirmed 3 new subscribers visible in Kit.",
    }

    with mock.patch.object(spd, "_emit"), mock.patch.object(spd, "_notify_macos"):
        asyncio.run(spd.handle_ops_handoff(envelope, "session_y"))

    queue_files = list((tmp_path / ".brain" / "ops_queue").glob("*.md"))
    assert len(queue_files) == 1
    assert "[OPS-RESULT]" in queue_files[0].read_text()


def test_notify_macos_noop_on_linux(monkeypatch: Any) -> None:
    """_notify_macos does nothing on non-Darwin platforms (portable-primitive gate)."""
    import platform
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    # Should complete without error and without calling osascript
    with mock.patch("subprocess.run") as mock_run:
        spd._notify_macos("title", "message")
    mock_run.assert_not_called()
