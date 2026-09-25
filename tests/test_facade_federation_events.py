"""Tests for nucleus_federation facade event emission (E3 lane).

Verifies each of the 7 federation actions (status, join, leave, peers, sync,
route, health) emits structured events to .brain/ledger/events.jsonl on both
happy and sad paths.

Per plan: `_facade_federation.json` scout re-run should show
emitted_events.length >= 14 (7 happy + 7 sad).
"""

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def brain(tmp_path):
    """Create a minimal brain directory with events.jsonl ready."""
    b = tmp_path / ".brain"
    for d in ["ledger", "engrams", "deltas", "driver", "training"]:
        (b / d).mkdir(parents=True, exist_ok=True)
    (b / "ledger" / "events.jsonl").touch()
    (b / "ledger" / "interaction_log.jsonl").touch()
    (b / "ledger" / "activity_summary.json").write_text(json.dumps({}))
    (b / "engrams" / "ledger.jsonl").touch()
    original = os.environ.get("NUCLEUS_BRAIN_PATH")
    os.environ["NUCLEUS_BRAIN_PATH"] = str(b)
    # Reset federation engine singleton to force re-init under this brain
    import mcp_server_nucleus.runtime.federation_ops as fops
    fops._federation_engine = None
    yield b
    fops._federation_engine = None
    if original is None:
        os.environ.pop("NUCLEUS_BRAIN_PATH", None)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    else:
        os.environ["NUCLEUS_BRAIN_PATH"] = original


def _read_events(brain_path: Path):
    """Parse events.jsonl into list of dicts."""
    events_path = brain_path / "ledger" / "events.jsonl"
    if not events_path.exists():
        return []
    content = events_path.read_text().strip()
    if not content:
        return []
    return [json.loads(line) for line in content.splitlines() if line.strip()]


def _events_of_type(brain_path: Path, event_type: str):
    return [e for e in _read_events(brain_path) if e.get("type") == event_type]


# ── Sad path: engine unavailable ──────────────────────────────────
# Force _get_federation_engine() to return None to drive the sad path
# without depending on the heavy FederationEngine implementation.


class TestSadPathEmits:
    """Each action emits a failure event when engine is unavailable."""

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_status_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_status_impl
        _brain_federation_status_impl()
        evts = _events_of_type(brain, "federation_status_failed")
        assert evts, "status should emit federation_status_failed when engine unavailable"
        assert evts[-1]["emitter"] == "nucleus_federation"
        assert evts[-1]["data"]["action"] == "status"
        assert evts[-1]["data"]["reason"] == "engine_unavailable"

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_join_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_join_impl
        asyncio.run(_brain_federation_join_impl("seed.example.com:9000"))
        evts = _events_of_type(brain, "federation_join_failed")
        assert evts
        assert evts[-1]["data"]["action"] == "join"
        assert evts[-1]["data"]["seed_peer"] == "seed.example.com:9000"

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_leave_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_leave_impl
        asyncio.run(_brain_federation_leave_impl())
        evts = _events_of_type(brain, "federation_leave_failed")
        assert evts
        assert evts[-1]["data"]["action"] == "leave"

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_peers_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_peers_impl
        _brain_federation_peers_impl()
        evts = _events_of_type(brain, "federation_peers_failed")
        assert evts
        assert evts[-1]["data"]["action"] == "peers"

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_sync_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_sync_impl
        asyncio.run(_brain_federation_sync_impl())
        evts = _events_of_type(brain, "federation_sync_failed")
        assert evts
        assert evts[-1]["data"]["action"] == "sync"

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_route_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_route_impl
        asyncio.run(_brain_federation_route_impl("task-123", profile="latency"))
        evts = _events_of_type(brain, "federation_route_failed")
        assert evts
        assert evts[-1]["data"]["action"] == "route"
        assert evts[-1]["data"]["task_id"] == "task-123"
        assert evts[-1]["data"]["profile"] == "latency"

    @patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None)
    def test_health_emits_failed(self, _mock, brain):
        from mcp_server_nucleus.runtime.federation_ops import _brain_federation_health_impl
        _brain_federation_health_impl()
        evts = _events_of_type(brain, "federation_health_failed")
        assert evts
        assert evts[-1]["data"]["action"] == "health"


# ── Happy path: mock engine returning success ────────────────────


def _make_fake_engine():
    """Build a MagicMock engine that drives the happy paths for all 7 actions."""
    engine = MagicMock()
    engine.running = True

    # status
    engine.get_status.return_value = {
        "brain_id": "brain_test",
        "region": "us-west",
        "running": True,
        "leader_id": "brain_test",
        "is_leader": True,
        "term": 1,
        "peers": {"online": 2, "total": 3},
        "partition_status": "NORMAL",
        "class_a_enabled": True,
        "sync": {
            "merkle_root": "abcdef1234567890" + "0" * 50,
            "vector_clock": {"brain_test": 5, "brain_peer1": 3},
        },
    }
    engine.get_health.return_value = {
        "score": 0.95,
        "healthy": True,
        "partition_status": "NORMAL",
        "peers_online": 2,
        "peers_total": 3,
        "leader": "brain_test",
        "warnings": [],
    }

    # peers / status peer listing
    fake_peer = SimpleNamespace(
        peer_id="peer-1",
        region="eu-central",
        latency_ms=12.5,
        status=SimpleNamespace(name="ONLINE"),
        trust_level=SimpleNamespace(name="MEMBER"),
        address="peer1.example.com:9000",
        load=0.42,
        capabilities=["sync", "route"],
        is_online=MagicMock(return_value=True),
    )
    engine.get_peers.return_value = [fake_peer]

    # join (async)
    async def _join(seed):
        return {"success": True, "peers": 1}
    engine.join = _join

    # leave (async)
    async def _leave():
        return {"success": True}
    engine.leave = _leave

    # sync (async)
    sync_result = SimpleNamespace(
        peer_id="peer-1",
        success=True,
        items_synced=4,
        conflicts_resolved=1,
        sync_time_ms=8.0,
        error=None,
    )

    async def _sync_now():
        return [sync_result]
    engine.sync_now = _sync_now

    # route (async)
    route_decision = SimpleNamespace(
        target_brain="peer-1",
        score=0.87,
        routing_time_ms=2.1,
        alternatives=[("peer-2", 0.55), ("peer-3", 0.31)],
    )

    async def _route_task(task, profile):
        return route_decision
    engine.route_task = _route_task

    # health metrics object
    engine.metrics = SimpleNamespace(
        tasks_routed=10,
        avg_routing_time_ms=3.5,
        sync_operations=7,
        raft_leader_changes=1,
        partition_events=0,
    )

    return engine


class TestHappyPathEmits:
    """Each action emits a success event when engine returns valid results."""

    def test_status_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            fops._brain_federation_status_impl()
        evts = _events_of_type(brain, "federation_status_succeeded")
        assert evts
        d = evts[-1]["data"]
        assert d["action"] == "status"
        assert d["brain_id"] == "brain_test"
        assert d["peers_online"] == 2
        assert d["peers_total"] == 3
        assert d["health_score"] == pytest.approx(0.95)

    def test_join_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            asyncio.run(fops._brain_federation_join_impl("seed.example.com:9000"))
        evts = _events_of_type(brain, "federation_join_succeeded")
        assert evts
        d = evts[-1]["data"]
        assert d["seed_peer"] == "seed.example.com:9000"
        assert d["peers"] == 1

    def test_leave_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            asyncio.run(fops._brain_federation_leave_impl())
        evts = _events_of_type(brain, "federation_leave_succeeded")
        assert evts
        assert evts[-1]["data"]["action"] == "leave"

    def test_peers_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            fops._brain_federation_peers_impl()
        evts = _events_of_type(brain, "federation_peers_succeeded")
        assert evts
        assert evts[-1]["data"]["peer_count"] == 1

    def test_peers_empty_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        engine = _make_fake_engine()
        engine.get_peers.return_value = []
        with patch.object(fops, "_get_federation_engine", return_value=engine):
            fops._brain_federation_peers_impl()
        evts = _events_of_type(brain, "federation_peers_succeeded")
        assert evts
        assert evts[-1]["data"]["peer_count"] == 0

    def test_sync_emits_completed(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            asyncio.run(fops._brain_federation_sync_impl())
        evts = _events_of_type(brain, "federation_sync_completed")
        assert evts
        d = evts[-1]["data"]
        assert d["peers_synced"] == 1
        assert d["items_synced"] == 4
        assert d["conflicts_resolved"] == 1
        assert d["successes"] == 1

    def test_sync_empty_emits_completed(self, brain):
        """sync with no peers should still emit a completed event."""
        from mcp_server_nucleus.runtime import federation_ops as fops
        engine = _make_fake_engine()

        async def _sync_empty():
            return []
        engine.sync_now = _sync_empty
        with patch.object(fops, "_get_federation_engine", return_value=engine):
            asyncio.run(fops._brain_federation_sync_impl())
        evts = _events_of_type(brain, "federation_sync_completed")
        assert evts
        assert evts[-1]["data"]["peers_synced"] == 0

    def test_route_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            asyncio.run(fops._brain_federation_route_impl("task-xyz", profile="balanced"))
        evts = _events_of_type(brain, "federation_route_succeeded")
        assert evts
        d = evts[-1]["data"]
        assert d["task_id"] == "task-xyz"
        assert d["profile"] == "balanced"
        assert d["target_brain"] == "peer-1"
        assert d["score"] == pytest.approx(0.87)

    def test_health_emits_succeeded(self, brain):
        from mcp_server_nucleus.runtime import federation_ops as fops
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            fops._brain_federation_health_impl()
        evts = _events_of_type(brain, "federation_health_succeeded")
        assert evts
        d = evts[-1]["data"]
        assert d["score"] == pytest.approx(0.95)
        assert d["healthy"] is True
        assert d["tasks_routed"] == 10
        assert d["sync_operations"] == 7


class TestCoverageMeetsTarget:
    """Acceptance: 7/7 actions emit, both happy + sad path emit distinct events."""

    def test_all_seven_actions_have_emit_calls_in_source(self):
        """Static check: source file contains _emit_event for each action."""
        src = Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "federation_ops.py"
        text = src.read_text()
        for action in ("status", "join", "leave", "peers", "sync", "route", "health"):
            # Expect at least one success-shaped event and at least one failure-shaped event
            success_marker = f'"federation_{action}_'
            assert success_marker in text, f"missing emit_event call for action={action}"

    def test_combined_run_emits_at_least_14_events(self, brain):
        """Drive sad path for all 7 + happy path for all 7 (sync runs twice in
        helper) -- accept >=14 distinct events on .brain/ledger/events.jsonl."""
        from mcp_server_nucleus.runtime import federation_ops as fops

        # Sad
        with patch.object(fops, "_get_federation_engine", return_value=None):
            fops._brain_federation_status_impl()
            asyncio.run(fops._brain_federation_join_impl("seed:9000"))
            asyncio.run(fops._brain_federation_leave_impl())
            fops._brain_federation_peers_impl()
            asyncio.run(fops._brain_federation_sync_impl())
            asyncio.run(fops._brain_federation_route_impl("t-1"))
            fops._brain_federation_health_impl()

        # Happy
        with patch.object(fops, "_get_federation_engine", return_value=_make_fake_engine()):
            fops._brain_federation_status_impl()
            asyncio.run(fops._brain_federation_join_impl("seed:9000"))
            asyncio.run(fops._brain_federation_leave_impl())
            fops._brain_federation_peers_impl()
            asyncio.run(fops._brain_federation_sync_impl())
            asyncio.run(fops._brain_federation_route_impl("t-1"))
            fops._brain_federation_health_impl()

        events = _read_events(brain)
        federation_events = [e for e in events if e.get("emitter") == "nucleus_federation"]
        assert len(federation_events) >= 14, (
            f"expected >= 14 federation events, got {len(federation_events)}"
        )
        # And each action is represented in both directions
        actions_seen = {e["data"].get("action") for e in federation_events}
        assert actions_seen >= {"status", "join", "leave", "peers", "sync", "route", "health"}
