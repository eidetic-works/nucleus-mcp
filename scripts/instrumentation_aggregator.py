"""Aggregate per-day instrumentation JSONL into per-(date, tool) summary engrams.

Sweep #003 of the treatment program: consumes the JSONL channel that sweep
#002 (runtime/tool_instrumentation.py) produces. Each day's .brain/
instrumentation/YYYYMMDD.jsonl carries one line per MCP tool invocation
(ts, tool, ms, optional session, optional error). This script collapses
that into ONE engram per (date, tool) tuple with:

  - count (total invocations)
  - p50_ms / p95_ms (latency percentiles)
  - error_rate (errors / count)
  - session_breakdown (counts per CC_SESSION_ROLE)

Discharge criterion 2 ("N>=1 OBSERVED invocations or a deprecation date")
is satisfied when an engram exists for a (date, tool) with count >= 1.
sweep #001's docs/PRIMITIVES.md HOOK-NUDGED ambiguity resolves to either
WIRED-with-N-hits-per-day or DEAD-IN-PRACTICE after a week of these
summaries accumulate.

Idempotent: re-running for a given date REWRITES the sidecar summary file
in place ({date}_summary.jsonl), so concurrent or repeated runs converge
to the same authoritative artifact. The "engram emit" step is now a
sidecar JSONL hop — an MCP host (e.g. a Claude session with the
mcp__eidetic__insert_engram tool) consumes that sidecar and lands the
summaries as engrams when convenient. This decouples the aggregator from
any specific daemon-client import (cc-main crack #1: the previous
runtime/engram_client default emit path imported a module that doesn't
exist).

Daemon-decoupled: the sidecar JSONL keeps accumulating even when the
eidetic daemon is healthy:false. The raw .brain/instrumentation/ files
are the authoritative record of invocations; .brain/instrumentation/
_summaries/{date}.jsonl is the authoritative summary record.

Usage:
    python scripts/instrumentation_aggregator.py [options]

Options:
    --date YYYYMMDD       Aggregate ONLY this date (default: yesterday UTC).
    --since YYYYMMDD      Aggregate from this date forward.
    --until YYYYMMDD      Stop at this date (inclusive). Default: today.
    --dry-run             Print summaries to stdout, do not write sidecar.
    --path PATH           Override .brain/instrumentation/ root.
    --no-emit             Parse + summarize, do not write the sidecar JSONL.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable


def _iter_records(jsonl_path: Path) -> Iterable[dict]:
    """Yield parsed records from a JSONL file, skipping malformed lines."""
    if not jsonl_path.exists():
        return
    with jsonl_path.open() as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                continue


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolated percentile on a SORTED list. 0 <= pct <= 100."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def summarize_day(jsonl_path: Path) -> dict[str, dict]:
    """Collapse one day's JSONL into {tool_name: summary_dict}."""
    by_tool: dict[str, list[dict]] = defaultdict(list)
    for record in _iter_records(jsonl_path):
        tool = record.get("tool")
        if tool:
            by_tool[tool].append(record)

    summaries: dict[str, dict] = {}
    for tool, records in by_tool.items():
        durations = sorted(float(r.get("ms", 0.0)) for r in records)
        errors = [r for r in records if r.get("error")]
        sessions: dict[str, int] = defaultdict(int)
        for r in records:
            sess = r.get("session") or "unknown"
            sessions[sess] += 1

        summaries[tool] = {
            "count": len(records),
            "p50_ms": round(_percentile(durations, 50), 2),
            "p95_ms": round(_percentile(durations, 95), 2),
            "max_ms": round(durations[-1], 2) if durations else 0.0,
            "error_count": len(errors),
            "error_rate": round(len(errors) / len(records), 4) if records else 0.0,
            "session_breakdown": dict(sessions),
        }
    return summaries


def _format_engram_payload(date: str, tool: str, summary: dict) -> str:
    return (
        f"[instrumentation-summary | tool={tool} | date={date}]\n"
        f"count={summary['count']}, p50_ms={summary['p50_ms']}, p95_ms={summary['p95_ms']}, "
        f"max_ms={summary['max_ms']}, error_count={summary['error_count']}, "
        f"error_rate={summary['error_rate']}\n"
        f"sessions={summary['session_breakdown']}"
    )


def _format_engram_meta(date: str, tool: str, summary: dict) -> str:
    return json.dumps({
        "kind": "instrumentation-summary",
        "date": date,
        "tool": tool,
        "count": summary["count"],
        "p50_ms": summary["p50_ms"],
        "p95_ms": summary["p95_ms"],
        "error_rate": summary["error_rate"],
        "arc": "treatment",
        "sweep": "003-aggregator",
    })


def _dates_in_range(since: str | None, until: str | None, single: str | None) -> list[str]:
    """Yield YYYYMMDD strings in [since, until] inclusive, or [single]."""
    if single:
        return [single]
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    start = since or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    end = until or today
    out: list[str] = []
    cur = datetime.strptime(start, "%Y%m%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end, "%Y%m%d").replace(tzinfo=timezone.utc)
    while cur <= end_dt:
        out.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return out


def aggregate(
    *,
    instrumentation_root: Path,
    dates: list[str],
    emit_engram: Callable[[str, str], str | None] | None = None,
    dry_run: bool = False,
    stdout=sys.stdout,
) -> dict[str, int]:
    """Aggregate the listed dates. Returns stats dict.

    cc-main crack #2 (idempotence): per-date sidecar files (_summaries/
    {date}.jsonl) are REWRITTEN each run from the full day's data, so a
    re-run produces the same authoritative artifact (no duplicate emit).

    cc-main minor c: emit_failures count tracks per-tool emit failures;
    main() promotes to exit 1 if every emit failed (nightly silent rot).
    """
    stats = {"days_seen": 0, "tools_summarized": 0,
             "engrams_inserted": 0, "engrams_skipped_no_emit": 0,
             "emit_failures": 0, "emit_attempts": 0}
    for date in dates:
        jsonl = instrumentation_root / f"{date}.jsonl"
        if not jsonl.exists():
            continue
        stats["days_seen"] += 1
        summaries = summarize_day(jsonl)
        for tool, summary in summaries.items():
            stats["tools_summarized"] += 1
            payload = _format_engram_payload(date, tool, summary)
            meta = _format_engram_meta(date, tool, summary)
            if dry_run:
                stdout.write(f"--- {date} {tool} ---\n{payload}\nmeta: {meta}\n\n")
                continue
            if emit_engram is None:
                stats["engrams_skipped_no_emit"] += 1
                continue
            stats["emit_attempts"] += 1
            try:
                emit_engram(payload, meta)
                stats["engrams_inserted"] += 1
            except Exception as exc:
                # Daemon down or other failure — leave the raw JSONL in place.
                stats["emit_failures"] += 1
                stdout.write(f"[aggregator] emit failed for {date}/{tool}: {exc!r}\n")
    return stats


def _default_emit_engram(instrumentation_root: Path) -> Callable[[str, str], None]:
    """Return a sidecar JSONL writer keyed by today's date.

    cc-main crack #1 fix: previous default imported a nonexistent
    mcp_server_nucleus.runtime.engram_client. Switched to a filesystem
    sidecar — daemon-agnostic, idempotent (file is rewritten per run; see
    aggregate() doc), and consumable by any MCP host with engram-insert
    capability. The sidecar lives at instrumentation_root/_summaries/
    {date}.jsonl alongside the raw daily JSONLs.

    Idempotence shape: each main() invocation truncates per-date sidecar
    files BEFORE the per-tool emit loop runs (see main()), so re-runs
    converge to the same record. The closure returned here only APPENDS.
    """
    summaries_dir = instrumentation_root / "_summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    def _emit(payload: str, meta_json: str) -> None:
        try:
            meta = json.loads(meta_json)
            date = meta.get("date", datetime.now(timezone.utc).strftime("%Y%m%d"))
        except (json.JSONDecodeError, AttributeError):
            date = datetime.now(timezone.utc).strftime("%Y%m%d")
        sidecar = summaries_dir / f"{date}.jsonl"
        record = {"payload": payload, "meta": meta_json}
        with sidecar.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

    return _emit


def _truncate_sidecars_for_dates(instrumentation_root: Path, dates: list[str]) -> None:
    """cc-main crack #2: idempotence via per-run truncation. Wipes the
    sidecar files for the dates being aggregated so the subsequent emits
    produce the canonical record for this run (no append-on-rerun).

    Peer 2026-06-11T10:31Z advisory (folded): only truncate when the raw
    JSONL still exists for that date. Otherwise a re-run of a date whose
    raw was archived/rotated would silently destroy the existing summary
    (aggregate() would find no records to re-emit). Truncate exactly the
    dates aggregate() will re-emit, not the calendar range.
    """
    summaries_dir = instrumentation_root / "_summaries"
    if not summaries_dir.exists():
        return
    for date in dates:
        raw = instrumentation_root / f"{date}.jsonl"
        if not raw.exists():
            continue
        f = summaries_dir / f"{date}.jsonl"
        if f.exists():
            f.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="single YYYYMMDD")
    ap.add_argument("--since", help="start YYYYMMDD")
    ap.add_argument("--until", help="end YYYYMMDD (inclusive)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--path", help="override .brain/instrumentation/ root")
    ap.add_argument("--no-emit", action="store_true",
                    help="parse + summarize, do not write the sidecar JSONL")
    args = ap.parse_args(argv)

    if args.path:
        root = Path(args.path)
    else:
        root = Path.cwd() / ".brain" / "instrumentation"

    dates = _dates_in_range(args.since, args.until, args.date)

    if args.no_emit or args.dry_run:
        emit = None
    else:
        # cc-main crack #2: per-run truncation makes the sidecar idempotent.
        _truncate_sidecars_for_dates(root, dates)
        emit = _default_emit_engram(root)

    stats = aggregate(
        instrumentation_root=root,
        dates=dates,
        emit_engram=emit,
        dry_run=args.dry_run,
    )
    print(json.dumps(stats), file=sys.stderr)

    # cc-main minor c: if every emit attempted failed, this is silent rot.
    # Promote to exit 1 so cron picks up the signal.
    if stats["emit_attempts"] > 0 and stats["emit_failures"] == stats["emit_attempts"]:
        print("[aggregator] every emit failed; nightly rot signal -> exit 1.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
