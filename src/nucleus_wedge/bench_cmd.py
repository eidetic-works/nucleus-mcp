"""``nucleus bench`` implementation per ``track_a_impl_kickoff.md`` Phase 6.

Segmented stopwatch: time each segment of the multi-machine smoke test
(clone, init, register, cc_restart, first_recall) and append one JSONL
row per segment to ``<brain>/metrics/week2_timing_<run_id>.jsonl``.
Binds acceptance criterion #1 (time-to-first-recall ≤5 min, per-segment).

Two modes (mutually exclusive):
- subprocess: ``nucleus-wedge bench <segment> -- <cmd> [args...]`` runs
  cmd, captures wall-clock + exit_code.
- manual: ``nucleus-wedge bench <segment> --manual-duration <sec>`` for
  segments without a subprocess (CC restart, first recall in-CC).

Run grouping via env var ``NUCLEUS_BENCH_RUN_ID``; if unset, a fresh
ISO-stamp is minted and printed for the operator to export.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from nucleus_wedge.store import Store


def _resolve_run_id() -> tuple[str, bool]:
    existing = os.environ.get("NUCLEUS_BENCH_RUN_ID")
    if existing:
        return existing, False
    minted = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return minted, True


def do_bench(
    segment: str,
    command: list[str] | None,
    manual_duration: float | None,
    brain_path_arg: str | None = None,
) -> int:
    if (command is None) == (manual_duration is None):
        print("bench: pass either '-- <command>' OR '--manual-duration <sec>', not both/neither", file=sys.stderr)
        return 2
    try:
        brain = Store.brain_path(brain_path_arg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    run_id, minted = _resolve_run_id()
    if minted:
        print(f"NUCLEUS_BENCH_RUN_ID not set; minted: {run_id}", file=sys.stderr)
        print(f"  export NUCLEUS_BENCH_RUN_ID={run_id}", file=sys.stderr)
    if command is not None:
        start = time.monotonic()
        proc = subprocess.run(command)
        duration = time.monotonic() - start
        exit_code: int | None = proc.returncode
    else:
        duration = float(manual_duration)  # type: ignore[arg-type]
        exit_code = None
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "segment": segment,
        "duration_seconds": round(duration, 3),
        "command": command,
        "exit_code": exit_code,
        "manual": command is None,
    }
    metrics_dir = brain / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    out_path = metrics_dir / f"week2_timing_{run_id}.jsonl"
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    print(f"{segment}: {duration:.3f}s -> {out_path}")
    return exit_code if exit_code is not None else 0
