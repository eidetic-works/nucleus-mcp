"""Weekly self-digest instrument (PRINCIPAL G1 criterion 5).

Authority: docs/PRINCIPAL.md:86,129,149 (G1 criterion 5; "self-digest + census
| substrate reports on itself, cross-repo netted | scheduled | weekly").
Immutable source: docs/PRINCIPAL.md@principal-v3.

Acceptance (rerunnable evidence, not narration):
  - The scheduled instrument has a committed definition and observable run
    ledger. (This module IS the committed definition; the append-only JSONL
    run log under ``.brain/evidence/self_digest_runs/run_log.jsonl`` IS the
    observable ledger. The daemon scheduler also persists ``last_run`` /
    ``last_result`` to ``scheduler_state.json``.)
  - Two consecutive untouched weekly firings are measurable without
    self-report. (``measure_consecutive_weekly_firings`` is a pure function
    over the committed run ledger — it counts consecutive PASS records whose
    adjacent timestamps fall within the weekly cadence window. No human
    input; no self-report.)
  - Failures alert without counting as a successful firing. (The job wrapper
    returns ``verdict: FAIL`` on any exception; the daemon's
    ``_run_job_safe`` calls ``notifier.send`` on ``ok=False``; the run ledger
    records ``verdict: FAIL``; the consecutive-firings counter resets on any
    FAIL or any cadence gap > ``MAX_WEEK_GAP_DAYS``.)

Mechanism
---------
This instrument wires EXISTING nucleus capabilities to make the substrate
report on itself for the trailing 7-day window:

  1. ``engram_ops`` ledger — counts engrams written in the window by reading
     ``.brain/engrams/ledger.jsonl`` and filtering by the engram timestamp.
  2. ``relay.core.relay_status(force_fs=True)`` — counts relay envelopes
     across all mailboxes (total + unread) using the EXISTING status rollup.
  3. ``scheduler`` persisted state — counts scheduled jobs and reports the
     last-result of each from ``.brain/daemon/scheduler_state.json``.

It does NOT re-implement any of those counts — it reads the EXISTING
substrate artifacts. The digest is the substrate's own self-report.

Silence cannot satisfy the check: the instrument FAILS when (a) the engram
ledger is missing or unreadable (substrate never ran), (b) the relay status
call raises, or (c) the scheduler state is absent. A no-op brain with zero
engrams and zero relay envelopes still PASSES (the substrate reports zeros
honestly) — but a MISSING substrate artifact fails. The PASS/FAIL bar is
"did the substrate report on itself without crashing", not "was there
activity".
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NucleusJobs.self_digest")

INSTRUMENT_NAME = "self_digest_instrument"
EVIDENCE_DIRNAME = "self_digest_runs"
RUN_LOG_NAME = "run_log.jsonl"
AUTHORITY = "docs/PRINCIPAL.md:86,129,149"
IMMUTABLE_SOURCE = "docs/PRINCIPAL.md@principal-v3"

# Weekly cadence. Two firings count as "consecutive untouched weekly" iff
# their adjacent timestamps are within MAX_WEEK_GAP_DAYS of each other. 8
# days = 7-day schedule + 1-day tolerance (catch-up / clock skew).
WEEKLY_WINDOW_DAYS = 7
MAX_WEEK_GAP_DAYS = 8


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _evidence_dir(brain_path: Optional[Path] = None) -> Path:
    from .common import get_brain_path

    root = brain_path or get_brain_path()
    d = root / "evidence" / EVIDENCE_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run_log_path(brain_path: Optional[Path] = None) -> Path:
    return _evidence_dir(brain_path) / RUN_LOG_NAME


def _append_run_log(record: Dict[str, Any], brain_path: Optional[Path] = None) -> Path:
    path = _run_log_path(brain_path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def _read_run_log(brain_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = _run_log_path(brain_path)
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# ── Substrate self-report: counts from EXISTING artifacts ──


def _count_engrams_in_window(brain: Path, since: datetime) -> Dict[str, Any]:
    """Count engrams written since `since` by reading the EXISTING ledger.jsonl.

    Reads .brain/engrams/ledger.jsonl (the same file _brain_write_engram_impl
    appends to via MemoryPipeline). Returns a count + the raw ledger size.
    Missing ledger is reported honestly (count=0) but the substrate-artifact
    presence flag lets the verdict distinguish "empty substrate" from
    "substrate never ran".
    """
    ledger = brain / "engrams" / "ledger.jsonl"
    if not ledger.exists():
        return {"present": False, "count_in_window": 0, "total": 0, "error": "ledger.jsonl missing"}
    total = 0
    in_window = 0
    parse_errors = 0
    with ledger.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            ts = _parse_iso(rec.get("timestamp") or rec.get("created_at") or rec.get("ts") or "")
            if ts is None:
                continue
            if ts >= since:
                in_window += 1
    out: Dict[str, Any] = {
        "present": True,
        "count_in_window": in_window,
        "total": total,
    }
    if parse_errors:
        out["parse_errors"] = parse_errors
    return out


def _count_relay_envelopes(brain: Path) -> Dict[str, Any]:
    """Count relay envelopes across all mailboxes via the EXISTING relay_status.

    Uses relay.core.relay_status(force_fs=True) so the count is the
    authoritative FS rollup, not an HTTP fan-out. Failure to read is reported
    as an error (the substrate's own status call raised).
    """
    try:
        from .relay.core import relay_status

        status = relay_status(force_fs=True)
        return {
            "ok": True,
            "total_messages": int(status.get("total_messages", 0)),
            "total_unread": int(status.get("total_unread", 0)),
            "mailbox_count": len(status.get("mailboxes", {})),
        }
    except Exception as e:
        return {"ok": False, "error": f"relay_status raised: {e}"}


def _scheduler_snapshot(brain: Path) -> Dict[str, Any]:
    """Snapshot the EXISTING scheduler_state.json — jobs registered + last_result.

    Reads .brain/daemon/scheduler_state.json (written by
    NucleusScheduler.persist_state). Missing file = daemon never ran under
    this brain; reported honestly.
    """
    state_path = brain / "daemon" / "scheduler_state.json"
    if not state_path.exists():
        return {"present": False, "job_count": 0, "jobs": {}, "error": "scheduler_state.json missing"}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"present": True, "job_count": 0, "jobs": {}, "error": f"unparseable: {e}"}
    jobs: Dict[str, Any] = {}
    for name, info in (state or {}).items():
        jobs[name] = {
            "last_run": info.get("last_run"),
            "last_result": info.get("last_result"),
            "enabled": info.get("enabled", True),
        }
    return {"present": True, "job_count": len(jobs), "jobs": jobs}


# ── Consecutive-firings measurement (pure function over the run ledger) ──


def measure_consecutive_weekly_firings(
    brain_path: Optional[Path] = None,
    *,
    max_gap_days: int = MAX_WEEK_GAP_DAYS,
) -> Dict[str, Any]:
    """Measure consecutive untouched weekly firings from the run ledger.

    Pure function over the committed run ledger — no human input, no
    self-report. Reads ``.brain/evidence/self_digest_runs/run_log.jsonl``,
    considers only records with ``verdict == "PASS"``, orders them by
    ``finished_at_utc`` ascending, and counts the trailing run of PASS
    records where each adjacent pair is within ``max_gap_days`` of each
    other.

    A FAIL record (or a cadence gap > max_gap_days) breaks the streak —
    failures do NOT count as a successful firing.

    Returns:
      - ``consecutive_pass_firings``: the trailing streak length (0 if the
        last record is FAIL or the ledger is empty).
      - ``total_pass_firings``: total PASS records in the ledger.
      - ``total_records``: total records (PASS + FAIL) in the ledger.
      - ``last_verdict``: verdict of the most recent record, or "none".
      - ``last_finished_at``: timestamp of the most recent record.
      - ``streak_breaks``: list of {at, reason} where the streak reset.
      - ``two_consecutive_untouched``: True iff consecutive_pass_firings >= 2.
    """
    records = _read_run_log(brain_path)
    # Sort ascending by finished_at_utc; fall back to started_at_utc.
    def _ts_key(r: Dict[str, Any]) -> str:
        return r.get("finished_at_utc") or r.get("started_at_utc") or ""

    records.sort(key=_ts_key)

    total_records = len(records)
    total_pass = sum(1 for r in records if r.get("verdict") == "PASS")

    streak = 0
    streak_breaks: List[Dict[str, Any]] = []
    prev_ts: Optional[datetime] = None
    for rec in records:
        verdict = rec.get("verdict")
        ts = _parse_iso(rec.get("finished_at_utc") or rec.get("started_at_utc") or "")
        if verdict != "PASS":
            streak_breaks.append({
                "at": rec.get("finished_at_utc") or rec.get("started_at_utc"),
                "reason": f"verdict={verdict}",
            })
            streak = 0
            prev_ts = None
            continue
        if prev_ts is not None and ts is not None:
            gap_days = (ts - prev_ts).total_seconds() / 86400.0
            if gap_days > max_gap_days:
                streak_breaks.append({
                    "at": rec.get("finished_at_utc") or rec.get("started_at_utc"),
                    "reason": f"cadence_gap={gap_days:.2f}d > {max_gap_days}d",
                })
                streak = 0
        streak += 1
        prev_ts = ts

    last_verdict = records[-1].get("verdict", "none") if records else "none"
    last_finished = (records[-1].get("finished_at_utc") or records[-1].get("started_at_utc")) if records else None

    return {
        "consecutive_pass_firings": streak,
        "total_pass_firings": total_pass,
        "total_records": total_records,
        "last_verdict": last_verdict,
        "last_finished_at": last_finished,
        "streak_breaks": streak_breaks,
        "two_consecutive_untouched": streak >= 2,
        "max_gap_days": max_gap_days,
        "instrument": INSTRUMENT_NAME,
        "authority": AUTHORITY,
        "immutable_source": IMMUTABLE_SOURCE,
        "measured_at_utc": _utc_now_iso(),
    }


# ── Main instrument entrypoint ──


def run_self_digest_instrument(
    *,
    brain_path: Optional[Path] = None,
    window_days: int = WEEKLY_WINDOW_DAYS,
) -> Dict[str, Any]:
    """Run the weekly self-digest and append a verdict record to the run ledger.

    Wires EXISTING nucleus capabilities (engram ledger, relay status,
    scheduler state) to make the substrate report on itself for the trailing
    ``window_days`` window. Appends a record to the observable run ledger and
    returns the verdict.

    Returns a verdict dict with:
      - ``substrate_reported``: True iff all three substrate artifacts were
        read without crashing (the PASS bar — the substrate reported on
        itself, regardless of activity volume).
      - ``digest``: the substrate self-report (engram/relay/scheduler counts).
      - ``run_id``: unique run id.
      - ``evidence_log_path``: the append-only run ledger path.
      - ``verdict``: "PASS" iff substrate_reported is True.
    """
    from .common import get_brain_path

    bp = brain_path or get_brain_path()
    run_id = f"sd_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    started_at = _utc_now_iso()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=window_days)

    errors: List[str] = []

    # ── 1. engram ledger count (EXISTING artifact) ──
    try:
        engram_counts = _count_engrams_in_window(bp, since)
    except Exception as e:
        engram_counts = {"present": False, "count_in_window": 0, "total": 0, "error": f"crashed: {e}"}
        errors.append(f"engram_count: {e}")

    # ── 2. relay envelope count (EXISTING relay_status) ──
    try:
        relay_counts = _count_relay_envelopes(bp)
    except Exception as e:
        relay_counts = {"ok": False, "error": f"crashed: {e}"}
        errors.append(f"relay_count: {e}")

    # ── 3. scheduler snapshot (EXISTING scheduler_state.json) ──
    try:
        sched_snap = _scheduler_snapshot(bp)
    except Exception as e:
        sched_snap = {"present": False, "job_count": 0, "jobs": {}, "error": f"crashed: {e}"}
        errors.append(f"scheduler_snap: {e}")

    # ── Verdict: the substrate reported on itself without crashing ──
    # The PASS bar is "all three substrate artifacts were read successfully".
    # Zero activity is honest (and PASS); a missing/crashed artifact is FAIL.
    substrate_reported = (
        bool(engram_counts.get("present"))
        and bool(relay_counts.get("ok"))
        and bool(sched_snap.get("present"))
    )
    verdict = "PASS" if substrate_reported else "FAIL"

    finished_at = _utc_now_iso()
    record: Dict[str, Any] = {
        "run_id": run_id,
        "instrument": INSTRUMENT_NAME,
        "authority": AUTHORITY,
        "immutable_source": IMMUTABLE_SOURCE,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "window_days": window_days,
        "window_since_utc": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "digest": {
            "engrams": engram_counts,
            "relay": relay_counts,
            "scheduler": sched_snap,
        },
        "substrate_reported": substrate_reported,
        "verdict": verdict,
    }
    if errors:
        record["errors"] = errors

    log_path = _append_run_log(record, brain_path=bp)

    out: Dict[str, Any] = {
        "substrate_reported": substrate_reported,
        "digest": record["digest"],
        "run_id": run_id,
        "evidence_log_path": str(log_path),
        "verdict": verdict,
        "window_days": window_days,
    }
    if errors:
        out["error"] = "; ".join(errors)
    elif not substrate_reported:
        missing = []
        if not engram_counts.get("present"):
            missing.append("engram ledger")
        if not relay_counts.get("ok"):
            missing.append("relay status")
        if not sched_snap.get("present"):
            missing.append("scheduler state")
        out["error"] = (
            "SUBSTRATE DID NOT REPORT: missing/crashed artifact(s): "
            + ", ".join(missing)
        )
    return out


if __name__ == "__main__":
    result = run_self_digest_instrument()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("verdict") == "PASS" else 1)
