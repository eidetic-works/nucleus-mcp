"""Tests for the weekly self-digest instrument (PRINCIPAL G1 criterion 5).

Authority: docs/PRINCIPAL.md:86,129,149.

The instrument wires EXISTING nucleus capabilities (engram ledger,
relay.core.relay_status, scheduler_state.json) to make the substrate report
on itself. These tests assert the three acceptance criteria:

  1. The scheduled instrument has a committed definition and observable run
     ledger — the instrument appends a record to
     .brain/evidence/self_digest_runs/run_log.jsonl on every run.
  2. Two consecutive untouched weekly firings are measurable without
     self-report — measure_consecutive_weekly_firings is a pure function
     over the run ledger that counts consecutive PASS records within the
     weekly cadence; no human input.
  3. Failures alert without counting as a successful firing — a FAIL record
     breaks the consecutive streak; the job wrapper returns ok=False on
     exception so the daemon's notifier.send fires.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.self_digest_instrument import (
    INSTRUMENT_NAME,
    run_self_digest_instrument,
    measure_consecutive_weekly_firings,
    _run_log_path,
    _read_run_log,
    _append_run_log,
    MAX_WEEK_GAP_DAYS,
)


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    """Isolated brain + env so the instrument doesn't touch the real .brain.

    Also resets cwd — the seeded_block instrument (a sibling G1 instrument)
    leaves the process cwd pointing at a deleted TemporaryDirectory after its
    run, which would make relay_status's Path.cwd() resolution raise. We chdir
    defensively (the prior cwd may already be deleted, so plain
    monkeypatch.chdir would fail recording it) and then let monkeypatch own the
    teardown back to tmp_path.
    """
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Defensive chdir: a prior test may have left cwd at a deleted temp dir,
    # in which case os.getcwd() raises and monkeypatch.chdir can't snapshot.
    # chdir to a known-good dir first, then hand ownership to monkeypatch.
    os.chdir(tmp_path)
    monkeypatch._cwd = str(tmp_path)  # tell monkeypatch teardown to stay here
    # relay_status uses project-spine detection; keep it OFF so the FS rollup
    # is byte-identical to the default path.
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    return brain


def _seed_substrate_artifacts(brain: Path) -> None:
    """Create the minimum substrate artifacts so the instrument can report.

    The instrument reads three EXISTING artifacts: the engram ledger, the
    relay mailboxes (via relay_status), and the scheduler state. Seed all
    three so the substrate has something honest to report.
    """
    # engram ledger
    eng_dir = brain / "engrams"
    eng_dir.mkdir(parents=True, exist_ok=True)
    (eng_dir / "ledger.jsonl").write_text(
        json.dumps({"key": "k1", "value": "v1",
                    "timestamp": datetime.now(timezone.utc).isoformat()}) + "\n",
        encoding="utf-8",
    )
    # relay mailbox (one envelope)
    relay_dir = brain / "relay" / "claude_code_main"
    relay_dir.mkdir(parents=True, exist_ok=True)
    (relay_dir / "msg1.json").write_text(
        json.dumps({"id": "m1", "subject": "s", "body": "b", "sender": "x",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "read": False}),
        encoding="utf-8",
    )
    # scheduler state
    sched_dir = brain / "daemon"
    sched_dir.mkdir(parents=True, exist_ok=True)
    (sched_dir / "scheduler_state.json").write_text(
        json.dumps({"self_digest_instrument": {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "last_result": "ok", "enabled": True}}),
        encoding="utf-8",
    )


def _read_run_log(brain: Path) -> list[dict]:
    path = _run_log_path(brain)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().strip().splitlines() if line]


def test_substrate_reports_and_appends_run_ledger(isolated_brain):
    """Criterion 1: a PASS run appends a record to the observable run ledger."""
    _seed_substrate_artifacts(isolated_brain)
    result = run_self_digest_instrument(brain_path=isolated_brain)
    assert result["verdict"] == "PASS", result
    assert result["substrate_reported"] is True
    records = _read_run_log(isolated_brain)
    assert len(records) >= 1
    last = records[-1]
    assert last["instrument"] == INSTRUMENT_NAME
    assert last["verdict"] == "PASS"
    assert last["authority"] == "docs/PRINCIPAL.md:86,129,149"
    assert last["immutable_source"] == "docs/PRINCIPAL.md@principal-v3"
    assert "digest" in last
    assert "engrams" in last["digest"]
    assert "relay" in last["digest"]
    assert "scheduler" in last["digest"]


def test_rerunnable_produces_fresh_record(isolated_brain):
    """A second run appends a new record (rerunnable, not one-shot)."""
    _seed_substrate_artifacts(isolated_brain)
    r1 = run_self_digest_instrument(brain_path=isolated_brain)
    r2 = run_self_digest_instrument(brain_path=isolated_brain)
    assert r1["run_id"] != r2["run_id"]
    records = _read_run_log(isolated_brain)
    assert len(records) >= 2
    assert records[-1]["run_id"] == r2["run_id"]


def test_missing_substrate_artifact_fails(isolated_brain):
    """Criterion 3 (negative): a missing substrate artifact => FAIL, not PASS.

    An empty brain (no engram ledger, no relay, no scheduler state) cannot
    report on itself — the instrument MUST return FAIL. Silence / missing
    artifacts cannot satisfy the check.
    """
    result = run_self_digest_instrument(brain_path=isolated_brain)
    assert result["verdict"] == "FAIL", result
    assert result["substrate_reported"] is False
    assert result.get("error")
    records = _read_run_log(isolated_brain)
    assert records[-1]["verdict"] == "FAIL"


def test_two_consecutive_weekly_firings_measurable(isolated_brain):
    """Criterion 2: two PASS records 7 days apart => two_consecutive_untouched.

    measure_consecutive_weekly_firings is a pure function over the run
    ledger — no human input, no self-report. Two PASS records within the
    weekly cadence window (<= MAX_WEEK_GAP_DAYS) yield a streak of 2.
    """
    _seed_substrate_artifacts(isolated_brain)
    now = datetime.now(timezone.utc)
    # Seed two PASS records 7 days apart (synthetic ledger entries that
    # mimic two untouched weekly firings).
    _append_run_log({
        "run_id": "sd_synthetic_w1",
        "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "started_at_utc": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at_utc": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "PASS",
    }, brain_path=isolated_brain)
    _append_run_log({
        "run_id": "sd_synthetic_w2",
        "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "started_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "PASS",
    }, brain_path=isolated_brain)

    measurement = measure_consecutive_weekly_firings(brain_path=isolated_brain)
    assert measurement["consecutive_pass_firings"] >= 2, measurement
    assert measurement["two_consecutive_untouched"] is True
    assert measurement["last_verdict"] == "PASS"
    assert measurement["total_pass_firings"] >= 2


def test_fail_record_breaks_consecutive_streak(isolated_brain):
    """Criterion 3: a FAIL record breaks the consecutive streak.

    Two PASS records then a FAIL: the trailing streak is 0 (the last record
    is FAIL). The FAIL does NOT count as a successful firing.
    """
    _seed_substrate_artifacts(isolated_brain)
    now = datetime.now(timezone.utc)
    _append_run_log({
        "run_id": "sd_w1", "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "finished_at_utc": (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "PASS",
    }, brain_path=isolated_brain)
    _append_run_log({
        "run_id": "sd_w2", "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "finished_at_utc": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "PASS",
    }, brain_path=isolated_brain)
    _append_run_log({
        "run_id": "sd_w3_fail", "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "finished_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "FAIL",
    }, brain_path=isolated_brain)

    measurement = measure_consecutive_weekly_firings(brain_path=isolated_brain)
    assert measurement["consecutive_pass_firings"] == 0, measurement
    assert measurement["two_consecutive_untouched"] is False
    assert measurement["last_verdict"] == "FAIL"
    assert measurement["total_pass_firings"] == 2
    # The streak-break is recorded with the FAIL reason.
    assert any("verdict=FAIL" in (b.get("reason") or "") for b in measurement["streak_breaks"])


def test_cadence_gap_breaks_streak(isolated_brain):
    """Criterion 2 (negative): a cadence gap > MAX_WEEK_GAP_DAYS breaks the streak.

    Two PASS records 20 days apart: the second does NOT extend the streak
    (gap exceeds the weekly cadence tolerance).
    """
    _seed_substrate_artifacts(isolated_brain)
    now = datetime.now(timezone.utc)
    _append_run_log({
        "run_id": "sd_old", "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "finished_at_utc": (now - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "PASS",
    }, brain_path=isolated_brain)
    _append_run_log({
        "run_id": "sd_recent", "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:86,129,149",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "finished_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "PASS",
    }, brain_path=isolated_brain)

    measurement = measure_consecutive_weekly_firings(brain_path=isolated_brain)
    # The gap (20d) > MAX_WEEK_GAP_DAYS (8d) resets the streak to 1 (only the
    # most recent PASS counts).
    assert measurement["consecutive_pass_firings"] == 1, measurement
    assert measurement["two_consecutive_untouched"] is False
    assert any("cadence_gap" in (b.get("reason") or "") for b in measurement["streak_breaks"])


def test_empty_ledger_measures_zero(isolated_brain):
    """An empty run ledger measures zero consecutive firings (not 2)."""
    measurement = measure_consecutive_weekly_firings(brain_path=isolated_brain)
    assert measurement["consecutive_pass_firings"] == 0
    assert measurement["two_consecutive_untouched"] is False
    assert measurement["total_records"] == 0
    assert measurement["last_verdict"] == "none"


def test_instrument_named_and_authority_cited(isolated_brain):
    """The instrument is named and cites its principal authority in every record."""
    _seed_substrate_artifacts(isolated_brain)
    run_self_digest_instrument(brain_path=isolated_brain)
    records = _read_run_log(isolated_brain)
    last = records[-1]
    assert last["instrument"] == "self_digest_instrument"
    assert "PRINCIPAL.md" in last["authority"]
    assert last["immutable_source"] == "docs/PRINCIPAL.md@principal-v3"
