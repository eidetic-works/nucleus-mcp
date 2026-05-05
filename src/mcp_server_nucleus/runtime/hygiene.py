"""Stale-priority garbage collection for `.brain/`.

Resolves Cascade feedback P0 #3 — the brain was serving stale priorities
as live guidance (the "Jan 10, 2025" vs 2026 year-bug case). This module:

  1. Normalizes dates that appear to be in a wrong year (year-bug guard).
  2. Archives stale priorities/tasks/deadlines to
     `.brain/ledger/archive/YYYY-MM-DD.jsonl` with a reason field.
  3. Emits `sprint_gap` alerts when the current sprint is COMPLETE with
     no successor and >7d old.

Call sites:
  - `brain_weekly_consolidate` (compounding_loop.py) — runs hygiene first.
  - Nightly scheduler hook at 03:00 local.
  - Facade action `nucleus_engrams(action="brain_hygiene", params={dry_run: bool})`.

Read-side filtering:
  Callers of `query_engrams`, `tasks list`, etc. import `is_stale(record)`
  and filter unless `include_stale=True`.

Concurrency discipline (acceptance criterion per 2026-04-18 review risk #3):
  - GC acquires advisory exclusive flock on `.brain/.hygiene.lock` for the
    entire archive-and-remove transaction.
  - Writers use atomic rename (state.json.tmp → state.json).
  - Concurrent readers see either pre-GC or post-GC state; never a
    half-archived view.
"""

from __future__ import annotations

import fcntl
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.hygiene")

# -----------------------------------------------------------------------------
# Tunables — defaults per v1.2.0 plan §1.2
# -----------------------------------------------------------------------------

PRIORITY_DEFAULT_STALE_AFTER = "14d"
TASK_DEFAULT_STALE_AFTER = "30d"
SPRINT_GAP_AGE_THRESHOLD = timedelta(days=7)
HYGIENE_LOCK_FILENAME = ".hygiene.lock"

# -----------------------------------------------------------------------------
# Duration parsing
# -----------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhdw])\s*$", re.IGNORECASE)
_DURATION_UNITS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 86400 * 7,
}


def parse_duration(value: Any) -> Optional[timedelta]:
    """Parse duration strings like '14d', '30d', '2w', '3h'. Returns None on junk."""
    if isinstance(value, timedelta):
        return value
    if not isinstance(value, str):
        return None
    m = _DURATION_RE.match(value)
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2).lower()
    return timedelta(seconds=amount * _DURATION_UNITS[unit])


# -----------------------------------------------------------------------------
# Date normalization — year-bug guard
# -----------------------------------------------------------------------------


def normalize_date(value: Any, *, now: Optional[datetime] = None) -> Any:
    """Normalize a suspect date string.

    Year-bug guard: if the parsed year is more than 1 year in the past
    relative to `now`, treat it as a data-entry error and bump the year
    to the current year. This catches the exact Cascade bug where a 2026
    brain was serving "Jan 10, 2025" as a priority (off-by-one year).

    Preserves the input type on unparseable values. Only acts on strings
    that parse cleanly as ISO8601. No mutation on already-current dates.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(value, str):
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    # Bump if date is more than 365 days stale — catches the Cascade
    # "Jan 10, 2025 vs 2026" off-by-one-year data-entry error while
    # preserving legitimate recent history (e.g., late-2025 entries seen
    # in early-2026 are left alone).
    if (now - parsed) > timedelta(days=365):
        bumped = parsed.replace(year=now.year)
        return bumped.isoformat().replace("+00:00", "Z")
    return value


# -----------------------------------------------------------------------------
# Staleness evaluation
# -----------------------------------------------------------------------------


def is_stale(
    record: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
    default_stale_after: str = PRIORITY_DEFAULT_STALE_AFTER,
) -> bool:
    """Return True if `record` is considered stale.

    Honors (in order):
      1. Explicit `expires_at: ISO8601` — stale iff expires_at < now.
      2. `stale_after: duration` + `created_at`/`updated_at` — stale iff
         now > reference_time + duration.
      3. Default stale_after if neither is present.

    Records without any timestamp are NOT considered stale (can't judge).
    """
    if not isinstance(record, dict):
        return False
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. expires_at (absolute).
    expires_at = record.get("expires_at")
    if isinstance(expires_at, str):
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return exp < now
        except ValueError:
            pass  # fall through to stale_after

    # 2. stale_after (relative).
    duration = parse_duration(record.get("stale_after")) or parse_duration(default_stale_after)
    if duration is None:
        return False
    ref = record.get("updated_at") or record.get("created_at")
    if not isinstance(ref, str):
        return False
    try:
        ref_dt = datetime.fromisoformat(ref.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ref_dt.tzinfo is None:
        ref_dt = ref_dt.replace(tzinfo=timezone.utc)
    return now > ref_dt + duration


def filter_stale(
    records: List[Dict[str, Any]],
    *,
    include_stale: bool = False,
    now: Optional[datetime] = None,
    default_stale_after: str = PRIORITY_DEFAULT_STALE_AFTER,
) -> List[Dict[str, Any]]:
    """Remove stale records unless `include_stale` is True."""
    if include_stale:
        return list(records)
    return [r for r in records if not is_stale(r, now=now, default_stale_after=default_stale_after)]


# -----------------------------------------------------------------------------
# Archive (mutating)
# -----------------------------------------------------------------------------


def _ensure_archive_dir(brain_path: Path) -> Path:
    ledger = brain_path / "ledger" / "archive"
    ledger.mkdir(parents=True, exist_ok=True)
    return ledger


def _today_archive_path(brain_path: Path, now: datetime) -> Path:
    day = now.strftime("%Y-%m-%d")
    return _ensure_archive_dir(brain_path) / f"{day}.jsonl"


def _append_archive(archive_path: Path, entries: List[Dict[str, Any]]) -> None:
    with archive_path.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")


def _emit_alert(brain_path: Path, alert: Dict[str, Any]) -> None:
    alerts_path = brain_path / "ledger" / "alerts.jsonl"
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    with alerts_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert, default=str) + "\n")


def _detect_sprint_gap(
    state: Dict[str, Any],
    *,
    now: datetime,
) -> Optional[Dict[str, Any]]:
    """Return a sprint_gap alert dict if the current sprint is orphaned."""
    sprint = state.get("current_sprint")
    if not isinstance(sprint, dict):
        return None
    if str(sprint.get("status", "")).upper() != "COMPLETE":
        return None
    if sprint.get("successor_sprint_id"):
        return None
    ended = sprint.get("ended_at") or sprint.get("updated_at")
    if not isinstance(ended, str):
        return None
    try:
        ended_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ended_dt.tzinfo is None:
        ended_dt = ended_dt.replace(tzinfo=timezone.utc)
    if now - ended_dt < SPRINT_GAP_AGE_THRESHOLD:
        return None
    return {
        "alert_type": "sprint_gap",
        "sprint_id": sprint.get("sprint_id") or sprint.get("id"),
        "sprint_status": sprint.get("status"),
        "ended_at": ended,
        "age_days": round((now - ended_dt).total_seconds() / 86400, 2),
        "detected_at": now.isoformat().replace("+00:00", "Z"),
        "message": (
            f"Sprint {sprint.get('sprint_id', '?')} marked COMPLETE "
            f"{(now - ended_dt).days}d ago with no successor_sprint_id."
        ),
    }


def run_hygiene(
    brain_path: Path,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Archive stale entries from `.brain/state.json` and related stores.

    Returns a report dict:
        {
          "archived": [...],          # records that were archived
          "year_bugs_fixed": N,       # count of normalized dates
          "sprint_gap_alert": {...}|None,
          "dry_run": bool,
        }

    When `dry_run=True`, no files are mutated — the report shows what
    would happen. Safe to run as a preflight from CLI.

    Concurrency: holds .brain/.hygiene.lock EX for the entire pass.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    brain_path = Path(brain_path)
    lock_path = brain_path / HYGIENE_LOCK_FILENAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    archived: List[Dict[str, Any]] = []
    year_bugs_fixed = 0
    sprint_alert: Optional[Dict[str, Any]] = None

    with lock_path.open("w") as lock_fp:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
        try:
            state_path = brain_path / "state.json"
            state: Dict[str, Any] = {}
            if state_path.exists():
                try:
                    with state_path.open("r") as f:
                        state = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("state.json unreadable; skipping: %s", e)
                    state = {}

            # --- Year-bug normalization on embedded dates ---
            new_state, n_fixed = _apply_year_bug_normalization(state, now=now)
            year_bugs_fixed = n_fixed

            # --- Collect stale records per kind ---
            for kind, stale_default in (
                ("priorities", PRIORITY_DEFAULT_STALE_AFTER),
                ("tasks", TASK_DEFAULT_STALE_AFTER),
                ("deadlines", "1d"),
            ):
                items = new_state.get(kind)
                if not isinstance(items, list):
                    continue
                kept: List[Dict[str, Any]] = []
                for r in items:
                    if isinstance(r, dict) and is_stale(r, now=now, default_stale_after=stale_default):
                        archived.append({
                            "kind": kind,
                            "archived_at": now.isoformat().replace("+00:00", "Z"),
                            "reason": "stale" if r.get("expires_at") or r.get("stale_after") else "stale_default",
                            "record": r,
                        })
                    else:
                        kept.append(r)
                new_state[kind] = kept

            # --- Sprint-gap alert ---
            sprint_alert = _detect_sprint_gap(new_state, now=now)

            # --- Persist (unless dry-run) ---
            if not dry_run:
                if archived:
                    _append_archive(_today_archive_path(brain_path, now), archived)
                if new_state != state:
                    _atomic_write_state(state_path, new_state)
                if sprint_alert is not None:
                    _emit_alert(brain_path, sprint_alert)
        finally:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)

    return {
        "archived": archived,
        "year_bugs_fixed": year_bugs_fixed,
        "sprint_gap_alert": sprint_alert,
        "dry_run": dry_run,
    }


def _atomic_write_state(path: Path, state: Dict[str, Any]) -> None:
    """Write state.json atomically — tmp + fsync + rename."""
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _apply_year_bug_normalization(state: Dict[str, Any], *, now: datetime) -> Tuple[Dict[str, Any], int]:
    """Walk state and normalize obviously-wrong-year dates.

    Returns (new_state, n_changed).
    """
    n_changed = 0

    def walk(obj: Any) -> Any:
        nonlocal n_changed
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if isinstance(obj, str):
            new = normalize_date(obj, now=now)
            if new != obj:
                n_changed += 1
            return new
        return obj

    new_state = walk(state)
    return new_state, n_changed


__all__ = [
    "PRIORITY_DEFAULT_STALE_AFTER",
    "TASK_DEFAULT_STALE_AFTER",
    "SPRINT_GAP_AGE_THRESHOLD",
    "parse_duration",
    "normalize_date",
    "is_stale",
    "filter_stale",
    "run_hygiene",
]
