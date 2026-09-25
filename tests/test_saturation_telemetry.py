"""Tests for task#219 / Bucket B5 saturation telemetry primitive."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import saturation_telemetry as sat


@pytest.fixture(autouse=True)
def _isolated_brain(tmp_path, monkeypatch):
    """Use canonical NUCLEUS_BRAIN_PATH (per PR #172). Delenv legacy alias
    to avoid bleed-through to real brain."""
    test_brain = tmp_path / ".brain"
    (test_brain / "measurement").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(test_brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    yield test_brain


def _write_turn(
    path: Path,
    turn_index: int,
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
    timestamp: str | None = None,
):
    """Append a turn record matching the measurement_proxy schema."""
    if timestamp is None:
        timestamp = (
            datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
            + timedelta(seconds=turn_index)
        ).isoformat().replace("+00:00", "Z")
    record = {
        "schema_version": "v1",
        "turn_index": turn_index,
        "session_id": "test-session",
        "surface": "cc_main",
        "timestamp": timestamp,
        "request_usage_counters": {"content_block_count": 1},
        "response_usage_counters": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# ── _read_recent_turns ─────────────────────────────────────────────────


def test_read_recent_turns_returns_empty_when_file_missing(_isolated_brain):
    assert sat._read_recent_turns(_isolated_brain / "measurement" / "missing.jsonl") == []


def test_read_recent_turns_parses_jsonl(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(5):
        _write_turn(p, i)
    turns = sat._read_recent_turns(p, window_size=100)
    assert len(turns) == 5
    assert turns[0]["turn_index"] == 0
    assert turns[-1]["turn_index"] == 4


def test_read_recent_turns_honors_window(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(10):
        _write_turn(p, i)
    turns = sat._read_recent_turns(p, window_size=3)
    assert len(turns) == 3
    assert [t["turn_index"] for t in turns] == [7, 8, 9]


def test_read_recent_turns_tolerates_malformed_lines(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    _write_turn(p, 0)
    p.open("a").write("not json\n")
    _write_turn(p, 1)
    turns = sat._read_recent_turns(p, window_size=100)
    assert len(turns) == 2  # malformed line skipped


# ── compute_baselines ──────────────────────────────────────────────────


def test_compute_baselines_no_data(_isolated_brain):
    v = sat.compute_baselines(surface="main")
    assert v["data_present"] is False
    assert v["turn_count"] == 0
    assert "no turns" in v["data_warnings"][0]


def test_compute_baselines_low_confidence_warning(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(5):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    v = sat.compute_baselines(surface="main")
    assert v["data_present"] is True
    assert v["turn_count"] == 5
    assert any("low-confidence" in w for w in v["data_warnings"])


def test_compute_baselines_token_median(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    # 10 turns each with 150 total tokens (100 in + 50 out)
    for i in range(10):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    v = sat.compute_baselines(surface="main")
    assert v["tokens_baseline_median"] == 150
    assert v["data_warnings"] == []  # no warnings at exactly 10 turns


def test_compute_baselines_latency_median(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    base = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    # 10 turns at 5s intervals
    for i in range(10):
        ts = (base + timedelta(seconds=i * 5)).isoformat().replace("+00:00", "Z")
        _write_turn(p, i, timestamp=ts)
    v = sat.compute_baselines(surface="main")
    assert v["latency_baseline_median_s"] == 5.0


# ── check_saturation ───────────────────────────────────────────────────


def test_check_saturation_clean_when_under_threshold(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(20):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    v = sat.check_saturation(surface="main", inspect_recent_n=5)
    assert v["saturated"] is False
    assert v["flagged_turns"] == []
    assert v["checked_count"] == 5


def test_check_saturation_flags_token_overrun(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    # 19 baseline turns
    for i in range(19):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    # 1 turn with 5x tokens (well above 2x threshold)
    _write_turn(p, 19, input_tokens=500, output_tokens=250)
    v = sat.check_saturation(surface="main", threshold_factor=2.0, inspect_recent_n=5)
    assert v["saturated"] is True
    flagged = [f for f in v["flagged_turns"] if f["metric"] == "tokens"]
    assert len(flagged) == 1
    assert flagged[0]["turn_index"] == 19
    assert flagged[0]["ratio"] == 5.0


def test_check_saturation_flags_latency_overrun(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    base = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    # 19 baseline turns at 5s intervals
    for i in range(19):
        ts = (base + timedelta(seconds=i * 5)).isoformat().replace("+00:00", "Z")
        _write_turn(p, i, timestamp=ts)
    # turn 19 has a 30s gap from turn 18 — 6x baseline (5s)
    ts_outlier = (
        base + timedelta(seconds=19 * 5 + 30)
    ).isoformat().replace("+00:00", "Z")
    _write_turn(p, 19, timestamp=ts_outlier)
    v = sat.check_saturation(surface="main", threshold_factor=2.0, inspect_recent_n=5)
    assert v["saturated"] is True
    latency_flags = [f for f in v["flagged_turns"] if f["metric"] == "latency"]
    assert len(latency_flags) >= 1


def test_check_saturation_no_data_returns_clean(_isolated_brain):
    v = sat.check_saturation(surface="main")
    assert v["saturated"] is False
    assert v["checked_count"] == 0
    assert "no_data_reason" in v


def test_check_saturation_threshold_factor_respected(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(19):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    # 2.5x — flagged at threshold=2.0, NOT flagged at threshold=3.0
    _write_turn(p, 19, input_tokens=250, output_tokens=125)
    v_strict = sat.check_saturation(surface="main", threshold_factor=2.0, inspect_recent_n=3)
    v_loose = sat.check_saturation(surface="main", threshold_factor=3.0, inspect_recent_n=3)
    assert v_strict["saturated"] is True
    assert v_loose["saturated"] is False


# ── saturation_warning_payload ─────────────────────────────────────────


def test_warning_payload_returns_none_when_clean(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(20):
        _write_turn(p, i)
    verdict = sat.check_saturation(surface="main")
    assert sat.saturation_warning_payload(verdict) is None


def test_warning_payload_builds_when_saturated(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(19):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    _write_turn(p, 19, input_tokens=500, output_tokens=250)
    verdict = sat.check_saturation(surface="main", inspect_recent_n=3)
    payload = sat.saturation_warning_payload(verdict)
    assert payload is not None
    assert "saturation-warning" in payload["tags"]
    assert "task-219" in payload["tags"]
    assert payload["saturated"] is True
    assert payload["auto_generated"] is True
    assert "Saturation flagged" in payload["summary"]


def test_warning_payload_truncates_long_flagged_lists(_isolated_brain):
    p = _isolated_brain / "measurement" / "turns.jsonl"
    for i in range(20):
        _write_turn(p, i, input_tokens=100, output_tokens=50)
    # 10 outlier turns (all should flag)
    for i in range(20, 30):
        _write_turn(p, i, input_tokens=500, output_tokens=250)
    verdict = sat.check_saturation(surface="main", inspect_recent_n=10)
    payload = sat.saturation_warning_payload(verdict)
    # Summary truncates at 5 entries + "and N more"
    assert "and " in payload["summary"]


# ── _percentile ────────────────────────────────────────────────────────


def test_percentile_handles_empty():
    assert sat._percentile([], 95) == 0.0


def test_percentile_handles_single():
    assert sat._percentile([42], 95) == 42.0


def test_percentile_computes_correctly():
    values = list(range(1, 101))  # 1..100
    p50 = sat._percentile(values, 50)
    p95 = sat._percentile(values, 95)
    assert 49 < p50 < 51  # interpolated median ~50.5
    assert 94 < p95 < 96  # interpolated p95 ~95.05
