"""Tests for scripts/instrumentation_aggregator.py (treatment sweep #003a).

Synthetic JSONL fixtures -> expected per-(date, tool) summary.
Covers idempotence injection, percentile correctness, error_rate, session_breakdown,
malformed-line tolerance, dry-run, and the no-emit short-circuit when daemon is down.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

# scripts/ aren't a package; load via importlib for test reproducibility.
import importlib.util


def _load_aggregator():
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / "scripts" / "instrumentation_aggregator.py"
    spec = importlib.util.spec_from_file_location("instrumentation_aggregator", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agg = _load_aggregator()


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def test_summarize_day_basic_counts(tmp_path):
    jsonl = tmp_path / "20260611.jsonl"
    _write_jsonl(jsonl, [
        {"ts": "2026-06-11T00:00:00.000Z", "tool": "nucleus_governance", "ms": 5.0},
        {"ts": "2026-06-11T00:00:01.000Z", "tool": "nucleus_governance", "ms": 10.0},
        {"ts": "2026-06-11T00:00:02.000Z", "tool": "nucleus_tasks", "ms": 1.0},
    ])

    s = agg.summarize_day(jsonl)
    assert set(s.keys()) == {"nucleus_governance", "nucleus_tasks"}
    assert s["nucleus_governance"]["count"] == 2
    assert s["nucleus_tasks"]["count"] == 1


def test_summarize_day_percentiles(tmp_path):
    jsonl = tmp_path / "20260611.jsonl"
    # 10 records 1..10ms -> p50=5.5 (linear interp), p95=9.55
    _write_jsonl(jsonl, [
        {"ts": "x", "tool": "t", "ms": float(i)} for i in range(1, 11)
    ])
    s = agg.summarize_day(jsonl)
    assert s["t"]["p50_ms"] == 5.5
    assert s["t"]["p95_ms"] == 9.55
    assert s["t"]["max_ms"] == 10.0


def test_summarize_day_error_rate_and_breakdown(tmp_path):
    jsonl = tmp_path / "20260611.jsonl"
    _write_jsonl(jsonl, [
        {"ts": "x", "tool": "t", "ms": 1.0, "session": "main"},
        {"ts": "x", "tool": "t", "ms": 1.0, "session": "main", "error": "ValueError"},
        {"ts": "x", "tool": "t", "ms": 1.0, "session": "peer"},
        {"ts": "x", "tool": "t", "ms": 1.0},  # no session => unknown
    ])
    s = agg.summarize_day(jsonl)
    assert s["t"]["count"] == 4
    assert s["t"]["error_count"] == 1
    assert s["t"]["error_rate"] == 0.25
    assert s["t"]["session_breakdown"] == {"main": 2, "peer": 1, "unknown": 1}


def test_malformed_lines_skipped(tmp_path):
    jsonl = tmp_path / "20260611.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text(
        '{"tool": "t", "ms": 1.0}\n'
        '{this-is-not-json}\n'
        '\n'  # blank skipped
        '{"tool": "t", "ms": 2.0}\n'
    )
    s = agg.summarize_day(jsonl)
    assert s["t"]["count"] == 2  # malformed + blank skipped, no raise


def test_aggregate_dry_run_writes_to_stdout(tmp_path):
    root = tmp_path / "instr"
    _write_jsonl(root / "20260611.jsonl", [{"tool": "t", "ms": 1.0}])

    buf = io.StringIO()
    stats = agg.aggregate(
        instrumentation_root=root,
        dates=["20260611"],
        dry_run=True,
        stdout=buf,
    )
    assert stats["days_seen"] == 1
    assert stats["tools_summarized"] == 1
    assert "tool=t" in buf.getvalue()
    assert "count=1" in buf.getvalue()


def test_aggregate_calls_emit_function_with_payload_and_meta(tmp_path):
    root = tmp_path / "instr"
    _write_jsonl(root / "20260611.jsonl", [{"tool": "t", "ms": 5.0}])

    seen = []

    def fake_emit(payload, meta):
        seen.append({"payload": payload, "meta": json.loads(meta)})

    stats = agg.aggregate(
        instrumentation_root=root,
        dates=["20260611"],
        emit_engram=fake_emit,
    )
    assert stats["engrams_inserted"] == 1
    assert len(seen) == 1
    assert seen[0]["meta"]["kind"] == "instrumentation-summary"
    assert seen[0]["meta"]["tool"] == "t"
    assert seen[0]["meta"]["date"] == "20260611"
    assert "tool=t" in seen[0]["payload"]


def test_aggregate_emit_failure_does_not_raise(tmp_path):
    root = tmp_path / "instr"
    _write_jsonl(root / "20260611.jsonl", [{"tool": "t", "ms": 5.0}])

    def boom_emit(payload, meta):
        raise RuntimeError("daemon down")

    buf = io.StringIO()
    stats = agg.aggregate(
        instrumentation_root=root,
        dates=["20260611"],
        emit_engram=boom_emit,
        stdout=buf,
    )
    # Should not raise; emit failure is logged + stats.engrams_inserted stays 0.
    assert stats["days_seen"] == 1
    assert stats["tools_summarized"] == 1
    assert stats["engrams_inserted"] == 0
    assert "emit failed" in buf.getvalue()


def test_aggregate_missing_jsonl_skipped(tmp_path):
    root = tmp_path / "instr"
    root.mkdir()
    # No jsonl for 20260611.
    stats = agg.aggregate(
        instrumentation_root=root,
        dates=["20260611", "20260612"],
        dry_run=True,
        stdout=io.StringIO(),
    )
    assert stats["days_seen"] == 0
    assert stats["tools_summarized"] == 0


def test_dates_in_range_single_date():
    out = agg._dates_in_range(None, None, "20260601")
    assert out == ["20260601"]


def test_dates_in_range_explicit_range():
    out = agg._dates_in_range("20260601", "20260603", None)
    assert out == ["20260601", "20260602", "20260603"]


def test_default_emit_writes_sidecar_jsonl(tmp_path):
    """cc-main crack #1 fix: default emit path now writes to a filesystem
    sidecar (no dead engram_client import). Sidecar lives alongside the
    raw daily files."""
    emit = agg._default_emit_engram(tmp_path)
    emit("payload-A", json.dumps({"date": "20260611", "tool": "t1"}))
    emit("payload-B", json.dumps({"date": "20260611", "tool": "t2"}))

    sidecar = tmp_path / "_summaries" / "20260611.jsonl"
    assert sidecar.exists()
    lines = sidecar.read_text().strip().splitlines()
    assert len(lines) == 2
    recs = [json.loads(line) for line in lines]
    assert recs[0]["payload"] == "payload-A"
    assert json.loads(recs[0]["meta"])["tool"] == "t1"


def test_truncate_sidecars_for_dates_idempotence(tmp_path):
    """cc-main crack #2 fix: per-run truncation makes the sidecar idempotent
    even though _emit only appends. Re-running aggregate() for the same
    date produces the same authoritative record (no duplicate engrams)."""
    summaries_dir = tmp_path / "_summaries"
    summaries_dir.mkdir()
    (summaries_dir / "20260611.jsonl").write_text('{"stale": true}\n')
    (summaries_dir / "20260612.jsonl").write_text('{"keep": true}\n')

    # Raw must exist for the date being truncated (peer advisory guard).
    (tmp_path / "20260611.jsonl").write_text('{"tool": "t", "ms": 1.0}\n')

    agg._truncate_sidecars_for_dates(tmp_path, ["20260611"])

    # 20260611 truncated; 20260612 untouched.
    assert not (summaries_dir / "20260611.jsonl").exists()
    assert (summaries_dir / "20260612.jsonl").read_text() == '{"keep": true}\n'


def test_truncation_guard_protects_archived_dates(tmp_path):
    """Peer 2026-06-11T10:31Z advisory: when the raw JSONL for a date has been
    archived/rotated, the existing sidecar summary is the ONLY authoritative
    record for that date. Re-running with the date in range MUST NOT destroy
    that summary — aggregate() would find no raw records to re-emit and
    nothing would replace the truncated record."""
    summaries_dir = tmp_path / "_summaries"
    summaries_dir.mkdir()
    archived_summary = summaries_dir / "20260610.jsonl"
    archived_summary.write_text('{"payload":"archived"}\n')
    # No raw for 20260610 — simulates rotation/archival.

    # Date in range but raw absent -> sidecar MUST survive.
    agg._truncate_sidecars_for_dates(tmp_path, ["20260610"])

    assert archived_summary.exists()
    assert archived_summary.read_text() == '{"payload":"archived"}\n'


def test_aggregate_emit_failures_tracked_in_stats(tmp_path):
    """cc-main minor c: emit_failures + emit_attempts must let main() detect
    'every emit failed' and escalate to exit 1."""
    root = tmp_path / "instr"
    _write_jsonl(root / "20260611.jsonl", [
        {"tool": "t1", "ms": 1.0},
        {"tool": "t2", "ms": 2.0},
    ])

    def all_fail(payload, meta):
        raise RuntimeError("daemon down")

    stats = agg.aggregate(
        instrumentation_root=root,
        dates=["20260611"],
        emit_engram=all_fail,
        stdout=io.StringIO(),
    )
    assert stats["emit_attempts"] == 2
    assert stats["emit_failures"] == 2
    assert stats["engrams_inserted"] == 0


def test_main_returns_1_when_every_emit_failed(tmp_path, monkeypatch):
    """cc-main minor c: nightly silent rot — every emit failing should
    surface as exit 1, not exit 0."""
    root = tmp_path / "instr"
    root.mkdir(parents=True)
    (root / "20260611.jsonl").write_text(
        json.dumps({"tool": "t", "ms": 1.0}) + "\n"
    )

    # Replace _default_emit_engram with one that always raises.
    def fail_emitter(instrumentation_root):
        def _emit(payload, meta):
            raise RuntimeError("forced failure")
        return _emit

    monkeypatch.setattr(agg, "_default_emit_engram", fail_emitter)

    rc = agg.main(["--path", str(root), "--date", "20260611"])
    assert rc == 1


def test_main_returns_0_when_dry_run_succeeds(tmp_path):
    """Dry-run path doesn't attempt emits; rc=0 regardless."""
    root = tmp_path / "instr"
    root.mkdir(parents=True)
    (root / "20260611.jsonl").write_text(
        json.dumps({"tool": "t", "ms": 1.0}) + "\n"
    )

    rc = agg.main(["--path", str(root), "--date", "20260611", "--dry-run"])
    assert rc == 0
