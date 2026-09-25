"""Integration tests for the Nucleus-Delegate v0.1 facade.

Cross-mode coverage: pair_register / pair_status / pair_fire / pair_stop /
audit_pair tied together with the L3 daemon.

Subprocess (Sonnet/Haiku via Claude Code) is mocked. The relay layer and
event-emission paths are exercised for real against a temp `.brain/` so
events.jsonl rollup is honest.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

import pytest

# Import the module under test from staged location during dev; production
# import path is `mcp_server_nucleus.tools._pair_actions`.
try:
    from mcp_server_nucleus.tools import _pair_actions as actions
except ImportError:  # dev path
    actions_path = Path(__file__).resolve().parents[2] / "src" / "mcp_server_nucleus" / "tools" / "_pair_actions.py"
    if not actions_path.exists():
        pytest.skip(f"_pair_actions.py not yet on disk at {actions_path}",
                    allow_module_level=True)
    import importlib.util
    spec = importlib.util.spec_from_file_location("nd_actions", actions_path)
    actions = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(actions)  # type: ignore[union-attr]


# ─── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def staged_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Stand up a minimal repo skeleton in tmp + chdir into it.

    Creates: .brain/{daemon,relay,ledger}/, scripts/{start,stop}_sonnet_pair.sh,
    docs/org/charters/sonnet_pair_peer.md, docs/org/charters/sonnet_pair_main.md.
    """
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".brain" / "daemon").mkdir(parents=True)
    (tmp_path / ".brain" / "relay").mkdir(parents=True)
    (tmp_path / ".brain" / "ledger").mkdir(parents=True)
    (tmp_path / ".brain" / "ledger" / "events.jsonl").touch()
    (tmp_path / ".brain" / "relay" / "sonnet_peer").mkdir()
    (tmp_path / ".brain" / "relay" / "sonnet_main").mkdir()

    charters = tmp_path / "docs" / "org" / "charters"
    charters.mkdir(parents=True)
    (charters / "sonnet_pair_peer.md").write_text("# stub charter")
    (charters / "sonnet_pair_main.md").write_text("# stub charter")

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    # Stub launcher: writes a fake pid, session_id, log line; no real daemon.
    start_stub = scripts / "start_sonnet_pair.sh"
    start_stub.write_text(
        "#!/bin/bash\n"
        "set -e\n"
        "lane=\"$1\"\n"
        "mkdir -p .brain/daemon\n"
        "echo 99999 > .brain/daemon/sonnet_pair_${lane}.pid\n"
        "echo 'fake-uuid-' >> .brain/daemon/sonnet_pair_${lane}.session_id\n"
        "echo 'started' >> .brain/daemon/sonnet_pair_${lane}.log\n"
    )
    start_stub.chmod(0o755)

    stop_stub = scripts / "stop_sonnet_pair.sh"
    stop_stub.write_text(
        "#!/bin/bash\n"
        "lane=\"$1\"\n"
        "rm -f .brain/daemon/sonnet_pair_${lane}.pid\n"
    )
    stop_stub.chmod(0o755)

    yield tmp_path


@pytest.fixture(autouse=True)
def _patch_repo_root(staged_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """The actions module captures _REPO_ROOT at import. Patch it for tests."""
    monkeypatch.setattr(actions, "_REPO_ROOT", staged_repo)


# ─── pair_register lifecycle ──────────────────────────────────────────────


def test_pair_register_starts_and_writes_state(staged_repo: Path) -> None:
    out = json.loads(actions.pair_register("peer"))
    assert out["ok"] is True
    data = out["data"]
    assert data["lane"] == "peer"
    assert data["started"] is True
    assert (staged_repo / ".brain" / "daemon" / "sonnet_pair_peer.pid").exists()
    assert data["pid"] == 99999  # from stub launcher
    assert data["session_id"] is not None


def test_pair_register_rejects_when_already_running(staged_repo: Path) -> None:
    pid_file = staged_repo / ".brain" / "daemon" / "sonnet_pair_peer.pid"
    pid_file.write_text(str(os.getpid()))  # use our own pid (guaranteed alive)

    out = json.loads(actions.pair_register("peer"))
    assert out["ok"] is False
    assert out["error"]["code"] == "ALREADY_RUNNING"


def test_pair_register_rejects_invalid_lane() -> None:
    out = json.loads(actions.pair_register("cc_tb"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_LANE"


# ─── pair_stop ────────────────────────────────────────────────────────────


def test_pair_stop_clears_pid(staged_repo: Path) -> None:
    actions.pair_register("peer")
    out = json.loads(actions.pair_stop("peer"))
    assert out["ok"] is True
    assert not (staged_repo / ".brain" / "daemon" / "sonnet_pair_peer.pid").exists()


# ─── pair_status ──────────────────────────────────────────────────────────


def test_pair_status_reports_running_state(staged_repo: Path) -> None:
    actions.pair_register("peer")
    out = json.loads(actions.pair_status("peer"))
    assert out["ok"] is True
    pairs = out["data"]["pairs"]
    assert len(pairs) == 1
    assert pairs[0]["lane"] == "peer"
    # pid 99999 from stub probably isn't actually running, but the field is populated
    assert pairs[0]["pid"] == 99999
    assert pairs[0]["queue_depth"] == 0


def test_pair_status_lane_default_returns_both(staged_repo: Path) -> None:
    out = json.loads(actions.pair_status())
    assert out["ok"] is True
    lanes = [p["lane"] for p in out["data"]["pairs"]]
    assert lanes == ["peer", "main"]


def test_pair_status_picks_up_heartbeat(staged_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a pair_heartbeat event and verify status surfaces busy_pct."""
    actions.pair_register("peer")
    events = staged_repo / ".brain" / "ledger" / "events.jsonl"
    now_ms = int(time.time() * 1000)
    hb = {
        "event_id": "evt-test-1",
        "timestamp": "2026-05-09T03:00:00Z",
        "type": "pair_heartbeat",
        "emitter": "sonnet_peer",
        "data": {
            "lane": "peer",
            "session_id": "test-session",
            "pid": 99999,
            "busy_pct_1h": 12.5,
            "events_in_window": 3,
            "started_at_ms": now_ms - 60000,
            "now_ms": now_ms,
        },
    }
    with events.open("a") as f:
        f.write(json.dumps(hb) + "\n")

    out = json.loads(actions.pair_status("peer"))
    hb_data = out["data"]["pairs"][0]["latest_heartbeat"]
    assert hb_data is not None
    assert hb_data["busy_pct_1h"] == 12.5
    assert hb_data["events_in_window"] == 3


# ─── pair_fire ────────────────────────────────────────────────────────────


def test_pair_fire_posts_relay(staged_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    posted: List[Dict[str, Any]] = []

    def fake_relay_post(**kw):
        posted.append(kw)
        return {"sent": True, "message_id": "fake_001"}

    monkeypatch.setitem(sys.modules, "mcp_server_nucleus.runtime.relay_ops",
                       type("M", (), {"relay_post": fake_relay_post}))

    out = json.loads(actions.pair_fire(
        lane="peer",
        brief="Read README.md and summarize",
        model="haiku",
    ))
    assert out["ok"] is True
    assert out["data"]["fired_to"] == "sonnet_peer"
    assert out["data"]["model"] == "haiku"
    assert len(posted) == 1
    assert posted[0]["to"] == "sonnet_peer"
    assert posted[0]["subject"].startswith("[DELEGATE:haiku]")


def test_default_sonnet_subject_omits_tier_tag(staged_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    posted: List[Dict[str, Any]] = []
    monkeypatch.setitem(
        sys.modules, "mcp_server_nucleus.runtime.relay_ops",
        type("M", (), {"relay_post":
                       lambda **kw: posted.append(kw) or {"sent": True, "message_id": "x"}}),
    )

    actions.pair_fire(lane="peer", brief="hello")
    assert posted[0]["subject"].startswith("[DELEGATE]")
    assert ":sonnet" not in posted[0]["subject"]


def test_invalid_inputs_rejected(staged_repo: Path) -> None:
    out = json.loads(actions.pair_fire(lane="bogus", brief="x"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_LANE"

    out = json.loads(actions.pair_fire(lane="peer", brief="x", model="opus"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_MODEL"

    out = json.loads(actions.pair_fire(lane="peer", brief=""))
    assert out["ok"] is False
    assert out["error"]["code"] == "EMPTY_BRIEF"


# ─── audit_pair ───────────────────────────────────────────────────────────


def test_audit_pair_rolls_up_events(staged_repo: Path) -> None:
    """Inject one spawn+return pair + one heartbeat; verify rollup math."""
    events = staged_repo / ".brain" / "ledger" / "events.jsonl"
    from datetime import datetime, timezone
    # Use current time so events fall inside the 1h audit window regardless
    # of when the test runs (was failing on stale hardcoded timestamp).
    base_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ms = int(time.time() * 1000)
    spawn_ev = {
        "event_id": "evt-spawn-1",
        "timestamp": base_iso,
        "type": "agent_spawn",
        "emitter": "sonnet_peer",
        "data": {
            "spawn_id": "spawn_test_1",
            "role": "sonnet_pair_peer",
            "model": "claude-haiku-4-5",
            "model_key": "haiku",
            "parent": "claude_code_peer",
            "prompt_chars": 100,
            "brief_chars": 50,
        },
    }
    return_ev = {
        "event_id": "evt-return-1",
        "timestamp": base_iso,
        "type": "agent_return",
        "emitter": "sonnet_peer",
        "data": {
            "spawn_id": "spawn_test_1",
            "role": "sonnet_pair_peer",
            "model": "claude-haiku-4-5",
            "parent": "claude_code_peer",
            "response_chars": 200,
            "duration_ms": 5000,
            "success": True,
        },
    }
    hb_ev = {
        "event_id": "evt-hb-1",
        "timestamp": base_iso,
        "type": "pair_heartbeat",
        "emitter": "sonnet_peer",
        "data": {
            "lane": "peer",
            "session_id": "test-uuid",
            "pid": 99999,
            "busy_pct_1h": 7.5,
            "events_in_window": 1,
            "started_at_ms": now_ms - 60000,
            "now_ms": now_ms,
        },
    }
    with events.open("a") as f:
        for ev in (spawn_ev, return_ev, hb_ev):
            f.write(json.dumps(ev) + "\n")

    # Note: audit_pair imports scripts/audit_token_cost.py at runtime.
    # In the staged repo there's no such script — copy/symlink the real one.
    real_script = Path(__file__).resolve().parents[2] / "scripts" / "audit_token_cost.py"
    if not real_script.exists():
        pytest.skip("audit_token_cost.py not present in repo; integration test deferred")
    target = staged_repo / "scripts" / "audit_token_cost.py"
    target.write_text(real_script.read_text())

    out = json.loads(actions.audit_pair(window_hours=1.0))
    assert out["ok"] is True
    assert out["data"]["events_in_window"] >= 2  # spawn + return at minimum
    pair_rollup = out["data"]["pair_rollup"]
    assert any(r["parent"] == "claude_code_peer" and r["role"] == "sonnet_pair_peer"
              for r in pair_rollup)
    util = out["data"]["utilization"]
    assert any(u["lane"] == "peer" and u["busy_pct_1h"] == 7.5 for u in util)
