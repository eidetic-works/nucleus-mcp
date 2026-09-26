"""Plan 6b (2026-09-26): the 30-min heartbeat watches the pool tick's own beat,
so a dead or repeatedly failing tick surfaces without a live Claude session.
Also surfaces the agent-os healthcheck that failed silently since 2026-09-21."""
import json
from datetime import datetime, timedelta, timezone

from mcp_server_nucleus.runtime import heartbeat_ops as h


def _beat(brain, minutes_ago=1, fails=None):
    d = brain / "agent_pool"
    d.mkdir(parents=True, exist_ok=True)
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (d / "tick_beat.json").write_text(json.dumps({"ts": ts, "steps": {}, "consecutive_failures": fails or {}}))


def test_healthy_beat_is_quiet(tmp_path):
    _beat(tmp_path, 2)
    assert h._check_fleet_tick(tmp_path, healthcheck_dir=tmp_path / "hc") == []


def test_stale_beat_triggers(tmp_path):
    _beat(tmp_path, 40)
    sigs = [t["signal"] for t in h._check_fleet_tick(tmp_path, healthcheck_dir=tmp_path / "hc")]
    assert sigs == ["FLEET_TICK_STALE"]


def test_missing_beat_triggers(tmp_path):
    (tmp_path / "agent_pool").mkdir()
    sigs = [t["signal"] for t in h._check_fleet_tick(tmp_path, healthcheck_dir=tmp_path / "hc")]
    assert sigs == ["FLEET_TICK_STALE"]


def test_step_failing_three_times_triggers_but_two_does_not(tmp_path):
    _beat(tmp_path, 1, {"linear-sync": 2})
    assert h._check_fleet_tick(tmp_path, healthcheck_dir=tmp_path / "hc") == []
    _beat(tmp_path, 1, {"linear-sync": 3, "wake": 0})
    t = h._check_fleet_tick(tmp_path, healthcheck_dir=tmp_path / "hc")
    assert [x["signal"] for x in t] == ["FLEET_STEP_FAILING"] and "linear-sync" in t[0]["message"]


def test_red_agent_os_healthcheck_surfaces(tmp_path):
    _beat(tmp_path, 1)
    hc = tmp_path / "hc"
    hc.mkdir()
    (hc / "healthcheck.log").write_text("2026-09-21T18:48:00Z PASS all\n2026-09-26T10:13:16Z FAIL C: test suite=FAIL;\n")
    sigs = [t["signal"] for t in h._check_fleet_tick(tmp_path, healthcheck_dir=hc)]
    assert sigs == ["AGENT_OS_HEALTHCHECK_RED"]
    (hc / "healthcheck.log").write_text("2026-09-26T10:13:16Z FAIL x\n2026-09-26T11:00:00Z PASS all\n")
    assert h._check_fleet_tick(tmp_path, healthcheck_dir=hc) == []  # recovered: quiet


def test_brain_without_a_fleet_is_quiet(tmp_path):
    assert h._check_fleet_tick(tmp_path, healthcheck_dir=tmp_path / "hc") == []
