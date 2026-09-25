"""Tests for runtime.hygiene — stale GC + year-bug guard + sprint alerts."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import hygiene


NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def brain(tmp_path) -> Path:
    root = tmp_path / ".brain"
    root.mkdir()
    return root


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------


def test_parse_duration_days():
    assert hygiene.parse_duration("14d") == timedelta(days=14)
    assert hygiene.parse_duration("30d") == timedelta(days=30)


def test_parse_duration_units():
    assert hygiene.parse_duration("30s") == timedelta(seconds=30)
    assert hygiene.parse_duration("2h") == timedelta(hours=2)
    assert hygiene.parse_duration("1w") == timedelta(weeks=1)


def test_parse_duration_bad_returns_none():
    assert hygiene.parse_duration("abc") is None
    assert hygiene.parse_duration(None) is None
    assert hygiene.parse_duration("") is None


# ---------------------------------------------------------------------------
# Year-bug guard
# ---------------------------------------------------------------------------


def test_normalize_date_bumps_prior_year():
    # 2025-01-10 is >1 year before 2026-04-20 -> bump to 2026
    out = hygiene.normalize_date("2025-01-10T00:00:00Z", now=NOW)
    assert "2026-01-10" in out


def test_normalize_date_leaves_current_year_alone():
    out = hygiene.normalize_date("2026-04-01T12:00:00Z", now=NOW)
    assert out == "2026-04-01T12:00:00Z"


def test_normalize_date_leaves_last_year_alone():
    # 2025-12 is within 1 year of 2026-04 — don't touch.
    # (current_year - 1 = 2025, so parsed.year < 2025 would trigger; 2025 itself doesn't)
    out = hygiene.normalize_date("2025-12-31T23:59:00Z", now=NOW)
    assert out == "2025-12-31T23:59:00Z"


def test_normalize_date_ignores_non_string():
    assert hygiene.normalize_date(42, now=NOW) == 42
    assert hygiene.normalize_date(None, now=NOW) is None


def test_normalize_date_ignores_unparseable():
    assert hygiene.normalize_date("not a date", now=NOW) == "not a date"


# ---------------------------------------------------------------------------
# Staleness evaluation
# ---------------------------------------------------------------------------


def test_is_stale_expires_at_past():
    r = {"expires_at": "2026-04-01T00:00:00Z"}
    assert hygiene.is_stale(r, now=NOW) is True


def test_is_stale_expires_at_future():
    r = {"expires_at": "2026-05-01T00:00:00Z"}
    assert hygiene.is_stale(r, now=NOW) is False


def test_is_stale_stale_after_respected():
    r = {"stale_after": "7d", "updated_at": "2026-04-01T00:00:00Z"}
    # 19 days elapsed > 7d
    assert hygiene.is_stale(r, now=NOW) is True


def test_is_stale_stale_after_within_window():
    r = {"stale_after": "14d", "updated_at": "2026-04-15T00:00:00Z"}
    # 5 days elapsed < 14d
    assert hygiene.is_stale(r, now=NOW) is False


def test_is_stale_default_for_priorities():
    # No stale_after, no expires_at, created_at 20d ago (> 14d default for priorities)
    r = {"created_at": "2026-03-31T12:00:00Z"}
    assert hygiene.is_stale(r, now=NOW, default_stale_after="14d") is True


def test_is_stale_no_timestamps_is_not_stale():
    assert hygiene.is_stale({"name": "x"}, now=NOW) is False


def test_filter_stale_removes_by_default():
    records = [
        {"name": "fresh", "updated_at": "2026-04-19T00:00:00Z"},
        {"name": "old", "updated_at": "2026-01-01T00:00:00Z"},
    ]
    out = hygiene.filter_stale(records, now=NOW, default_stale_after="14d")
    assert len(out) == 1
    assert out[0]["name"] == "fresh"


def test_filter_stale_include_stale_true_keeps_all():
    records = [
        {"name": "fresh", "updated_at": "2026-04-19T00:00:00Z"},
        {"name": "old", "updated_at": "2026-01-01T00:00:00Z"},
    ]
    out = hygiene.filter_stale(records, include_stale=True, now=NOW)
    assert len(out) == 2


# ---------------------------------------------------------------------------
# run_hygiene — archiving + persistence
# ---------------------------------------------------------------------------


def _write_state(brain: Path, state: dict) -> None:
    (brain / "state.json").write_text(json.dumps(state, indent=2))


def test_run_hygiene_archives_stale_priorities(brain):
    _write_state(brain, {
        "priorities": [
            {"id": "p1", "updated_at": "2026-04-19T00:00:00Z"},  # fresh
            {"id": "p2", "updated_at": "2026-01-01T00:00:00Z"},  # stale
        ],
    })
    report = hygiene.run_hygiene(brain, now=NOW)
    assert len(report["archived"]) == 1
    assert report["archived"][0]["record"]["id"] == "p2"

    # State was mutated
    new_state = json.loads((brain / "state.json").read_text())
    assert len(new_state["priorities"]) == 1
    assert new_state["priorities"][0]["id"] == "p1"

    # Archive was written
    archive_file = brain / "ledger" / "archive" / "2026-04-20.jsonl"
    assert archive_file.exists()
    entries = [json.loads(l) for l in archive_file.read_text().splitlines()]
    assert len(entries) == 1
    assert entries[0]["record"]["id"] == "p2"


def test_run_hygiene_dry_run_no_mutation(brain):
    _write_state(brain, {
        "priorities": [{"id": "p1", "updated_at": "2026-01-01T00:00:00Z"}],
    })
    report = hygiene.run_hygiene(brain, dry_run=True, now=NOW)
    assert len(report["archived"]) == 1

    new_state = json.loads((brain / "state.json").read_text())
    assert len(new_state["priorities"]) == 1  # unchanged
    assert not (brain / "ledger" / "archive" / "2026-04-20.jsonl").exists()


def test_run_hygiene_year_bug_counted(brain):
    _write_state(brain, {
        "meta": {"generated_at": "2024-01-10T00:00:00Z"},
    })
    report = hygiene.run_hygiene(brain, now=NOW)
    assert report["year_bugs_fixed"] >= 1


def test_run_hygiene_sprint_gap_alert(brain):
    _write_state(brain, {
        "current_sprint": {
            "sprint_id": "s-40",
            "status": "COMPLETE",
            "ended_at": "2026-04-01T00:00:00Z",  # 19d ago
        },
    })
    report = hygiene.run_hygiene(brain, now=NOW)
    assert report["sprint_gap_alert"] is not None
    assert report["sprint_gap_alert"]["alert_type"] == "sprint_gap"
    assert report["sprint_gap_alert"]["sprint_id"] == "s-40"

    alerts = (brain / "ledger" / "alerts.jsonl").read_text().splitlines()
    assert len(alerts) == 1


def test_run_hygiene_no_sprint_gap_when_fresh(brain):
    _write_state(brain, {
        "current_sprint": {
            "sprint_id": "s-40",
            "status": "COMPLETE",
            "ended_at": "2026-04-18T00:00:00Z",  # 2d ago — within threshold
        },
    })
    report = hygiene.run_hygiene(brain, now=NOW)
    assert report["sprint_gap_alert"] is None


def test_run_hygiene_no_sprint_gap_when_successor_set(brain):
    _write_state(brain, {
        "current_sprint": {
            "sprint_id": "s-40",
            "status": "COMPLETE",
            "ended_at": "2026-04-01T00:00:00Z",
            "successor_sprint_id": "s-41",
        },
    })
    report = hygiene.run_hygiene(brain, now=NOW)
    assert report["sprint_gap_alert"] is None


def test_run_hygiene_missing_state_noop(brain):
    report = hygiene.run_hygiene(brain, now=NOW)
    assert report["archived"] == []
    assert report["sprint_gap_alert"] is None


# ---------------------------------------------------------------------------
# Concurrency — review risk #3 acceptance
# ---------------------------------------------------------------------------


def test_run_hygiene_serialized_under_concurrent_runs(brain):
    """Two concurrent hygiene runs should serialize via flock; no partial archives."""
    _write_state(brain, {
        "priorities": [
            {"id": f"p{i}", "updated_at": "2026-01-01T00:00:00Z"}
            for i in range(5)
        ],
    })
    reports = []

    def run():
        reports.append(hygiene.run_hygiene(brain, now=NOW))

    threads = [threading.Thread(target=run) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly 5 records archived across all runs (the first run grabs them).
    total_archived = sum(len(r["archived"]) for r in reports)
    assert total_archived == 5

    # Post-state: priorities empty
    new_state = json.loads((brain / "state.json").read_text())
    assert new_state["priorities"] == []

    # Archive file exists and is well-formed JSONL
    archive = brain / "ledger" / "archive" / "2026-04-20.jsonl"
    entries = [json.loads(l) for l in archive.read_text().splitlines()]
    assert len(entries) == 5
