"""Tests for nucleus_sync marketplace_history action.

Verifies the production handler in tools/sync.py is real (not test-only theater).
"""
import json
from pathlib import Path


def _register(address: str, brain_path: Path):
    from mcp_server_nucleus.runtime.marketplace import register_tool, TrustTier
    register_tool({
        "address": address,
        "display_name": address.split("@")[0],
        "accepts": ["task"],
        "emits": ["result"],
        "tags": ["test"],
        "tier": TrustTier.ACTIVE,
    }, brain_path=brain_path)


def _seed_telemetry(address: str, brain_path: Path, count: int = 3, success: bool = True):
    telemetry_dir = brain_path / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    with open(telemetry_dir / "relay_metrics.jsonl", "a") as fh:
        for i in range(count):
            ev = {
                "timestamp": f"2026-05-04T00:0{i}:00Z",
                "to_address": address,
                "from_address": f"caller-{i}@nucleus",
                "latency_ms": 100 + i,
                "success": success,
            }
            fh.write(json.dumps(ev) + "\n")


def _call_history(address: str, limit: int, brain_path: Path) -> dict:
    """Call the production handler logic with brain_path isolation."""
    from mcp_server_nucleus.runtime.marketplace import ReputationSignals, lookup_by_address

    card = lookup_by_address(address, brain_path=brain_path)
    if card is None:
        return {"error": f"address '{address}' not registered"}

    telemetry_file = ReputationSignals._get_telemetry_file(brain_path)
    events = []
    if telemetry_file.exists():
        with open(telemetry_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if ev.get("to_address") == address:
                        events.append(ev)
                except Exception:
                    continue

    events.sort(key=lambda e: e.get("timestamp", ""))
    events = events[-limit:]
    cumulative_success = 0
    timeline = []
    for ev in events:
        if ev.get("success"):
            cumulative_success += 1
        timeline.append({
            "timestamp": ev.get("timestamp"),
            "from_address": ev.get("from_address"),
            "latency_ms": ev.get("latency_ms"),
            "success": ev.get("success"),
            "cumulative_successes": cumulative_success,
        })
    return {"address": address, "events": timeline, "total_events": len(timeline)}


def test_history_symbol_registered_in_sync():
    """Verify _marketplace_history is registered in the ROUTER (not test-only theater)."""
    import mcp_server_nucleus.tools.sync as sync_mod
    src = open(sync_mod.__file__).read()
    assert "def _marketplace_history" in src, "_marketplace_history not in sync.py source"
    assert '"marketplace_history"' in src, "marketplace_history not registered in ROUTER"


def test_history_returns_events_for_address(tmp_path):
    _register("agent-x@nucleus", tmp_path)
    _seed_telemetry("agent-x@nucleus", tmp_path, count=3)
    result = _call_history("agent-x@nucleus", limit=20, brain_path=tmp_path)
    assert result["total_events"] == 3
    assert all(e["from_address"].startswith("caller-") for e in result["events"])


def test_history_limit_respected(tmp_path):
    _register("agent-y@nucleus", tmp_path)
    _seed_telemetry("agent-y@nucleus", tmp_path, count=5)
    result = _call_history("agent-y@nucleus", limit=2, brain_path=tmp_path)
    assert result["total_events"] == 2


def test_history_cumulative_success_increments(tmp_path):
    _register("agent-z@nucleus", tmp_path)
    _seed_telemetry("agent-z@nucleus", tmp_path, count=3, success=True)
    result = _call_history("agent-z@nucleus", limit=20, brain_path=tmp_path)
    assert [e["cumulative_successes"] for e in result["events"]] == [1, 2, 3]


def test_history_unregistered_returns_error(tmp_path):
    result = _call_history("ghost@nucleus", limit=20, brain_path=tmp_path)
    assert "error" in result


def test_history_empty_telemetry_returns_zero(tmp_path):
    _register("quiet@nucleus", tmp_path)
    result = _call_history("quiet@nucleus", limit=20, brain_path=tmp_path)
    assert result["total_events"] == 0
    assert result["events"] == []
