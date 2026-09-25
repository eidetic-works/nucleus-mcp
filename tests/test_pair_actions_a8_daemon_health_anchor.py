"""
Test Suite: A8 infra-daemon-health anchoring (NUCLEUS_DAEMON_HEALTH_ANCHOR)
======================================================================
docs/verifier/HANDOFF_BACKLOG.md §A8 + docs/verifier/ADJACENCY_THEOREM.md.

Hole: `pair_status`'s liveness probe was a bare `os.kill(pid, 0)` against a
self-written `.brain/daemon/sonnet_pair_<lane>.pid` file, and `audit_pair`'s
>=40% utilization gate trusted the latest self-emitted `pair_heartbeat`
event's `busy_pct_1h`/`pid` verbatim. Both are claimant-authority state
(Regime-2 per ADJACENCY_THEOREM.md §4): `echo $$ >
.brain/daemon/sonnet_pair_<lane>.pid` plus one fabricated `pair_heartbeat`
line appended to events.jsonl satisfies both checks without the daemon ever
having run — the exact forge row A8 names.

Flag NUCLEUS_DAEMON_HEALTH_ANCHOR gates the fix; default OFF must remain
byte-identical (legacy hole demonstrably still open) while ON must:
  - flip `pair_status`'s `running` to False for a pid with no spawn-time
    create_time witness (accepted when OFF = legacy);
  - flip `audit_pair`'s `gate_pass_at_40_pct` to False for a heartbeat event
    whose pid has no matching witness (accepted when OFF = legacy);
  - stay True/True for a pid `pair_register` (the only legitimate launch
    path) actually recorded a witness for.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from mcp_server_nucleus.tools import _pair_actions as actions


# ─── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def staged_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Minimal repo skeleton in tmp: .brain/{daemon,relay,ledger}/,
    scripts/{start,stop}_sonnet_pair.sh (stub launcher writing THIS test
    process's own pid — guaranteed alive, real kernel create_time — so the
    "genuine spawn" path can be exercised for real), docs/org/charters/.
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
    start_stub = scripts / "start_sonnet_pair.sh"
    start_stub.write_text(
        "#!/bin/bash\n"
        "set -e\n"
        "lane=\"$1\"\n"
        "mkdir -p .brain/daemon\n"
        f"echo {os.getpid()} > .brain/daemon/sonnet_pair_${{lane}}.pid\n"
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

    # audit_pair imports scripts/audit_token_cost.py at runtime — copy the
    # real one in, matching test_nucleus_delegate_integration.py's pattern.
    real_script = Path(__file__).resolve().parents[2] / "scripts" / "audit_token_cost.py"
    if real_script.exists():
        (scripts / "audit_token_cost.py").write_text(real_script.read_text())

    yield tmp_path


@pytest.fixture(autouse=True)
def _patch_repo_root(staged_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """The actions module captures _REPO_ROOT at import. Patch it per-test."""
    monkeypatch.setattr(actions, "_REPO_ROOT", staged_repo)


@pytest.fixture(autouse=True)
def _clean_anchor_env(monkeypatch: pytest.MonkeyPatch):
    """Default OFF unless a test opts in explicitly."""
    monkeypatch.delenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", raising=False)


def _append_event(staged_repo: Path, ev: Dict[str, Any]) -> None:
    events = staged_repo / ".brain" / "ledger" / "events.jsonl"
    with events.open("a") as f:
        f.write(json.dumps(ev) + "\n")


def _fake_heartbeat_event(lane: str, pid: int, busy_pct_1h: float) -> Dict[str, Any]:
    from datetime import datetime, timezone

    now_ms = int(time.time() * 1000)
    return {
        "event_id": f"evt-hb-forge-{pid}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "pair_heartbeat",
        "emitter": f"sonnet_{lane}",
        "data": {
            "lane": lane,
            "session_id": "forged-session",
            "pid": pid,
            "busy_pct_1h": busy_pct_1h,
            "events_in_window": 1,
            "started_at_ms": now_ms - 60000,
            "now_ms": now_ms,
        },
    }


# ─── _pid_create_time — unit sanity (exercises the real ps-fallback path;
# psutil is not a pinned dependency of this package and is not installed in
# the dev venv, so this always runs the subprocess-`ps` shim in practice) ──


class TestPidCreateTime:
    def test_self_pid_returns_stable_value(self):
        a = actions._pid_create_time(os.getpid())
        b = actions._pid_create_time(os.getpid())
        assert a is not None
        assert a == b  # deterministic for a live, unchanged process

    def test_bogus_pid_returns_none(self):
        # PID unlikely to exist on any real system.
        assert actions._pid_create_time(2**30 - 1) is None


# ─── _anchor_verify_alive — unit checks ────────────────────────────────────


class TestAnchorVerifyAlive:
    def test_no_witness_file_fails_closed(self, staged_repo: Path):
        assert actions._anchor_verify_alive("main", os.getpid()) is False

    def test_matching_witness_passes(self, staged_repo: Path):
        actions._write_create_time_witness("main", os.getpid())
        assert actions._anchor_verify_alive("main", os.getpid()) is True

    def test_mismatched_witness_fails(self, staged_repo: Path):
        actions._create_time_witness_path("main").write_text("bogus-create-time-value")
        assert actions._anchor_verify_alive("main", os.getpid()) is False

    def test_dead_pid_fails(self, staged_repo: Path):
        actions._write_create_time_witness("main", os.getpid())
        assert actions._anchor_verify_alive("main", 2**30 - 1) is False

    def test_non_int_pid_fails(self, staged_repo: Path):
        assert actions._anchor_verify_alive("main", None) is False
        assert actions._anchor_verify_alive("main", "99999") is False


# ─── pair_register — witness recording ─────────────────────────────────────


class TestPairRegisterWitness:
    def test_flag_off_no_witness_no_new_keys(self, staged_repo: Path) -> None:
        out = json.loads(actions.pair_register("peer"))
        assert out["ok"] is True
        assert "create_time_witness_recorded" not in out["data"]
        assert not actions._create_time_witness_path("peer").exists()

    def test_flag_on_records_witness(self, staged_repo: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", "true")
        out = json.loads(actions.pair_register("peer"))
        assert out["ok"] is True
        assert out["data"]["create_time_witness_recorded"] is True
        witness = actions._create_time_witness_path("peer")
        assert witness.exists()
        assert witness.read_text().strip() == actions._pid_create_time(os.getpid())


# ─── pair_status — the A8 forge test ───────────────────────────────────────


class TestPairStatusForge:
    def _plant_forged_pid_file(self, staged_repo: Path, lane: str) -> None:
        """Simulates `echo $$ > .brain/daemon/sonnet_pair_<lane>.pid`: a
        genuinely-alive pid (this test process) that was NEVER spawned via
        pair_register, so no create_time witness exists for it.
        """
        pid_file = staged_repo / ".brain" / "daemon" / f"sonnet_pair_{lane}.pid"
        pid_file.write_text(str(os.getpid()))

    def test_forged_pid_passes_under_flag_off_legacy(self, staged_repo: Path) -> None:
        self._plant_forged_pid_file(staged_repo, "main")
        out = json.loads(actions.pair_status("main"))
        assert out["data"]["pairs"][0]["running"] is True  # legacy hole, demonstrated
        assert "anchor_verified" not in out["data"]["pairs"][0]

    def test_forged_pid_fails_under_flag_on(self, staged_repo: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", "1")
        self._plant_forged_pid_file(staged_repo, "main")
        out = json.loads(actions.pair_status("main"))
        row = out["data"]["pairs"][0]
        assert row["anchor_verified"] is False
        assert row["running"] is False  # forge test: does NOT pass health

    def test_genuine_spawn_passes_under_flag_on(self, staged_repo: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", "on")
        actions.pair_register("main")  # stub launcher writes os.getpid() + witness
        out = json.loads(actions.pair_status("main"))
        row = out["data"]["pairs"][0]
        assert row["anchor_verified"] is True
        assert row["running"] is True


# ─── audit_pair — the A8 forge test on the utilization gate ───────────────


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[2] / "scripts" / "audit_token_cost.py").exists(),
    reason="audit_token_cost.py not present in repo; integration test deferred",
)
class TestAuditPairGateForge:
    def test_fabricated_heartbeat_passes_gate_under_flag_off_legacy(
        self, staged_repo: Path,
    ) -> None:
        # Fabricate a pair_heartbeat line claiming 95% busy for a pid that
        # was never registered via pair_register — the historical exploit.
        _append_event(staged_repo, _fake_heartbeat_event("peer", os.getpid(), 95.0))
        out = json.loads(actions.audit_pair(window_hours=1.0))
        assert out["ok"] is True
        util = out["data"]["utilization"]
        row = next(u for u in util if u["lane"] == "peer")
        assert row["gate_pass_at_40_pct"] is True  # legacy hole, demonstrated
        assert "anchor_verified" not in row

    def test_fabricated_heartbeat_fails_gate_under_flag_on(
        self, staged_repo: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", "yes")
        _append_event(staged_repo, _fake_heartbeat_event("peer", os.getpid(), 95.0))
        out = json.loads(actions.audit_pair(window_hours=1.0))
        util = out["data"]["utilization"]
        row = next(u for u in util if u["lane"] == "peer")
        assert row["anchor_verified"] is False
        assert row["gate_pass_at_40_pct"] is False  # forge test: gate denied

    def test_genuine_heartbeat_passes_gate_under_flag_on(
        self, staged_repo: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", "true")
        actions.pair_register("peer")  # records the create_time witness
        _append_event(staged_repo, _fake_heartbeat_event("peer", os.getpid(), 95.0))
        out = json.loads(actions.audit_pair(window_hours=1.0))
        util = out["data"]["utilization"]
        row = next(u for u in util if u["lane"] == "peer")
        assert row["anchor_verified"] is True
        assert row["gate_pass_at_40_pct"] is True

    def test_below_threshold_still_fails_gate_when_anchored(
        self, staged_repo: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Anchor passing does not itself grant the gate — busy_pct still governs."""
        monkeypatch.setenv("NUCLEUS_DAEMON_HEALTH_ANCHOR", "true")
        actions.pair_register("peer")
        _append_event(staged_repo, _fake_heartbeat_event("peer", os.getpid(), 12.5))
        out = json.loads(actions.audit_pair(window_hours=1.0))
        util = out["data"]["utilization"]
        row = next(u for u in util if u["lane"] == "peer")
        assert row["anchor_verified"] is True
        assert row["gate_pass_at_40_pct"] is False


# ─── flag-off byte-identity across the whole facade ────────────────────────


class TestFlagOffByteIdentity:
    def test_pair_register_no_new_keys(self, staged_repo: Path) -> None:
        out = json.loads(actions.pair_register("peer"))
        assert set(out["data"].keys()) == {
            "lane", "pid", "session_id", "charter_path", "started",
        }

    def test_pair_status_no_new_keys(self, staged_repo: Path) -> None:
        actions.pair_register("peer")
        out = json.loads(actions.pair_status("peer"))
        row = out["data"]["pairs"][0]
        assert set(row.keys()) == {
            "lane", "running", "pid", "session_id", "queue_depth",
            "latest_heartbeat", "log_path",
        }

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parents[2] / "scripts" / "audit_token_cost.py").exists(),
        reason="audit_token_cost.py not present in repo; integration test deferred",
    )
    def test_audit_pair_no_new_keys(self, staged_repo: Path) -> None:
        _append_event(staged_repo, _fake_heartbeat_event("peer", os.getpid(), 50.0))
        out = json.loads(actions.audit_pair(window_hours=1.0))
        row = out["data"]["utilization"][0]
        assert set(row.keys()) == {
            "lane", "session_id", "busy_pct_1h", "events_in_window", "pid",
            "gate_pass_at_40_pct",
        }
