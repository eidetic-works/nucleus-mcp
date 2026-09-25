"""Tests for the standing cross-vendor seam-floor query (PRINCIPAL G1 crit 3).

Authority: docs/PRINCIPAL.md:74,149. Verifies the three acceptance criteria:
  1. Counts genuine vendor surfaces with a minimum of two vendors.
  2. Computes rolling seven-day envelope volume and two-week sustainment.
  3. Caller-authored vendor labels cannot satisfy the count (anchor gate).

Sandboxed: every test builds a tmp .brain tree (no live substrate reads).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp_server_nucleus.runtime import seam_query as sq


def _ts(days_ago: float, hour: int = 0) -> str:
    """ISO-8601 UTC created_at string `days_ago` days before the test as_of.

    Uses hour=0 (midnight UTC) so the timestamp is always <= now regardless of
    when the test runs (fixes time-of-day-dependent failures where days_ago=0
    at hour=12 could be in the future if the test runs before noon UTC).
    """
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _env(rid: str, bucket: str, from_agent: str = "cc_main",
         to_agent: str = "antigravity", from_provider: str | None = None,
         from_verified: bool | None = None, days_ago: float = 1.0) -> dict:
    """Build a relay envelope. from_verified=None omits the key (anchor OFF)."""
    msg = {
        "id": rid,
        "from": from_agent,
        "to": to_agent,
        "from_role": "worker",
        "subject": "s",
        "body": "b",
        "priority": "normal",
        "read": False,
        "created_at": _ts(days_ago),
    }
    if from_provider is not None:
        msg["from_provider"] = from_provider
    if from_verified is not None:
        msg["from_verified"] = from_verified
    return msg


def _build_brain(tmp_path: Path, relay_buckets: dict[str, list[dict]]) -> Path:
    brain = tmp_path / ".brain"
    relay_root = brain / "relay"
    relay_root.mkdir(parents=True)
    for bucket, msgs in relay_buckets.items():
        bdir = relay_root / bucket
        bdir.mkdir()
        for i, msg in enumerate(msgs):
            (bdir / f"msg_{i}.json").write_text(json.dumps(msg))
    return brain


# ── criterion 3: caller-authored vendor labels cannot satisfy the count ────

def test_forged_vendor_label_does_not_count(tmp_path):
    """A caller types from='antigravity' but from_verified is False -> excluded.

    This is the core forge-rejection: the caller-authored vendor label cannot
    move the gated count because the anchor verdict (kernel oracle) is False.
    """
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main",
                                  from_agent="claude_code_main",
                                  to_agent="claude_code_main",
                                  from_verified=True, days_ago=1)],
        # FORGED: caller typed from='antigravity' but anchor says False
        "antigravity": [_env("r2", "antigravity", from_agent="antigravity",
                             to_agent="antigravity", from_verified=False,
                             days_ago=1)],
    })
    report = sq.run_seam_query(brain)
    # Only the anchored claude_code envelope qualifies -> 1 vendor, NOT 2.
    assert report["vendor_surfaces"]["distinct_anchored_vendor_count"] == 1
    assert report["vendor_surfaces"]["anchored_vendor_surfaces"] == [
        "anthropic_claude_code"
    ]
    assert report["verdict"]["seam_floor_met"] is False
    # The forged envelope shows up in the unanchored diagnostic but NOT the verdict.
    assert "antigravity" in report["diagnostic_unanchored_exposure"]["vendor_surfaces_unanchored"]


def test_anchor_absent_fail_closed(tmp_path):
    """No from_verified key on any envelope (anchor flag OFF) -> 0 qualifying,
    seam_floor_met=False, anchor_active=False. This is the correct fail-closed
    state per PRINCIPAL.md:83 (pre-anchor envelopes are non-qualifying)."""
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main", from_verified=None)],
        "antigravity": [_env("r2", "antigravity", from_verified=None)],
    })
    report = sq.run_seam_query(brain)
    assert report["anchor"]["anchor_active"] is False
    assert report["anchor"]["anchor_absent_count"] == 2
    assert report["vendor_surfaces"]["distinct_anchored_vendor_count"] == 0
    assert report["verdict"]["seam_floor_met"] is False
    assert report["verdict"]["fail_closed_reason"] == "anchor not active"


def test_from_verified_false_excluded_even_with_vendor_label(tmp_path):
    """from_verified=False (anchor ran, mismatch) is excluded — distinct from
    anchor-absent. Both fail-closed, but the counter distinction matters."""
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main", from_verified=True)],
        "glm_main_agent": [_env("r2", "glm_main_agent", from_verified=False)],
    })
    report = sq.run_seam_query(brain)
    assert report["anchor"]["anchor_active"] is True  # at least one True
    assert report["anchor"]["anchor_false_count"] == 1
    assert report["vendor_surfaces"]["distinct_anchored_vendor_count"] == 1
    assert "glm" not in report["vendor_surfaces"]["anchored_vendor_surfaces"]


# ── criterion 1: counts genuine vendor surfaces, min 2 vendors ─────────────

def test_two_anchored_vendors_meets_vendor_floor(tmp_path):
    """Two distinct genuine vendor surfaces with from_verified=True -> floor met."""
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main",
                                  from_verified=True, days_ago=1)],
        "antigravity": [_env("r2", "antigravity", from_verified=True, days_ago=1)],
    })
    report = sq.run_seam_query(brain)
    assert report["vendor_surfaces"]["distinct_anchored_vendor_count"] == 2
    assert report["vendor_surfaces"]["min_two_vendors_met"] is True


def test_single_anchored_vendor_fails_floor(tmp_path):
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main", from_verified=True)],
    })
    report = sq.run_seam_query(brain)
    assert report["vendor_surfaces"]["min_two_vendors_met"] is False
    assert report["verdict"]["seam_floor_met"] is False


def test_test_fixture_buckets_excluded(tmp_path):
    """acme_corp (test fixture) envelopes do not count as a vendor surface."""
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main", from_verified=True)],
        "acme_corp": [_env("r2", "acme_corp", from_verified=True)],
    })
    report = sq.run_seam_query(brain)
    assert "test_fixture" not in report["vendor_surfaces"]["anchored_vendor_surfaces"]
    assert report["vendor_surfaces"]["distinct_anchored_vendor_count"] == 1


# ── criterion 2: rolling 7-day volume + 2-week sustainment ─────────────────

def test_rolling_window_counts_only_recent_envelopes(tmp_path):
    """Envelopes older than the rolling window are excluded from the volume."""
    # 3 envelopes in the last 7 days, 30 outside.
    msgs = ([_env(f"r{i}", "claude_code_main", from_verified=True, days_ago=i)
             for i in range(3)] +
            [_env(f"old{i}", "claude_code_main", from_verified=True, days_ago=30 + i)
             for i in range(30)])
    brain = _build_brain(tmp_path, {"claude_code_main": msgs})
    report = sq.run_seam_query(brain, volume_threshold=2)
    assert report["rolling_window"]["qualifying_volume"] == 3
    assert report["rolling_window"]["met_threshold"] is True


def test_sustainment_two_weeks_met(tmp_path):
    """Volume >= threshold in BOTH the trailing 7-day window AND the prior
    7-day window (days 7-14) -> sustained=True."""
    cc_msgs = []
    # week 0 (days 0-6): 5 anchored envelopes
    for i in range(5):
        cc_msgs.append(_env(f"w0_{i}", "claude_code_main", from_verified=True, days_ago=i))
    # week 1 (days 7-13): 5 anchored envelopes
    for i in range(5):
        cc_msgs.append(_env(f"w1_{i}", "claude_code_main", from_verified=True, days_ago=7 + i))
    brain = _build_brain(tmp_path, {
        "claude_code_main": cc_msgs,
        "antigravity": [_env("v2", "antigravity", from_verified=True, days_ago=1)],
    })
    report = sq.run_seam_query(brain, volume_threshold=5, sustain_weeks=2)
    assert report["sustainment"]["sustained"] is True
    assert len(report["sustainment"]["weeks"]) == 2
    assert all(w["met_threshold"] for w in report["sustainment"]["weeks"])


def test_sustainment_fails_when_second_week_below_threshold(tmp_path):
    """Volume met in week 0 but NOT in week 1 -> sustained=False."""
    msgs = ([_env(f"w0_{i}", "claude_code_main", from_verified=True, days_ago=i)
             for i in range(5)] +
            [_env(f"w1_{i}", "claude_code_main", from_verified=True, days_ago=7 + i)
             for i in range(2)])  # only 2 in week 1
    brain = _build_brain(tmp_path, {
        "claude_code_main": msgs,
        "antigravity": [_env("v2", "antigravity", from_verified=True, days_ago=1)],
    })
    report = sq.run_seam_query(brain, volume_threshold=5, sustain_weeks=2)
    assert report["sustainment"]["sustained"] is False
    assert report["verdict"]["seam_floor_met"] is False


# ── full verdict: all four criteria must align ──────────────────────────────

def test_seam_floor_met_when_all_criteria_pass(tmp_path):
    """All four criteria (anchor, 2 vendors, rolling volume, 2-week sustain)
    pass -> seam_floor_met=True."""
    msgs = []
    # 26 anchored claude_code envelopes per week (>=25/wk both weeks)
    for i in range(26):
        msgs.append(_env(f"w0_{i}", "claude_code_main", from_verified=True, days_ago=i % 7))
    for i in range(26):
        msgs.append(_env(f"w1_{i}", "claude_code_main", from_verified=True, days_ago=7 + (i % 7)))
    brain = _build_brain(tmp_path, {
        "claude_code_main": msgs,
        "antigravity": [_env("v2", "antigravity", from_verified=True, days_ago=1)],
        "glm_main_agent": [_env("v3", "glm_main_agent", from_verified=True, days_ago=2)],
    })
    report = sq.run_seam_query(brain, volume_threshold=25, sustain_weeks=2)
    assert report["anchor"]["anchor_active"] is True
    assert report["vendor_surfaces"]["min_two_vendors_met"] is True
    assert report["rolling_window"]["met_threshold"] is True
    assert report["sustainment"]["sustained"] is True
    assert report["verdict"]["seam_floor_met"] is True
    assert report["verdict"]["fail_closed_reason"] == "all criteria met"


def test_seam_floor_not_met_if_volume_passes_but_anchor_off(tmp_path):
    """High volume + 2 vendors but anchor OFF -> NOT met. Proves the anchor
    gate is load-bearing, not decorative."""
    msgs = ([_env(f"r{i}", "claude_code_main", from_verified=None, days_ago=i % 7)
             for i in range(30)])
    brain = _build_brain(tmp_path, {
        "claude_code_main": msgs,
        "antigravity": [_env("a1", "antigravity", from_verified=None, days_ago=1)],
    })
    report = sq.run_seam_query(brain, volume_threshold=25)
    # diagnostic shows the forgeable exposure is large...
    assert report["diagnostic_unanchored_exposure"]["rolling_volume_unanchored"] >= 25
    # ...but the gated verdict is fail-closed
    assert report["verdict"]["seam_floor_met"] is False
    assert report["verdict"]["fail_closed_reason"] == "anchor not active"


# ── idempotent rerun (pure measurement) ─────────────────────────────────────

def test_idempotent_rerun_identical_verdict(tmp_path):
    brain = _build_brain(tmp_path, {
        "claude_code_main": [_env("r1", "claude_code_main", from_verified=True)],
        "antigravity": [_env("r2", "antigravity", from_verified=True)],
    })
    as_of = datetime.now(timezone.utc)
    r1 = sq.run_seam_query(brain, as_of=as_of)
    r2 = sq.run_seam_query(brain, as_of=as_of)
    assert r1["verdict"] == r2["verdict"]
    assert r1["vendor_surfaces"]["anchored_vendor_surfaces"] == r2["vendor_surfaces"]["anchored_vendor_surfaces"]


# ── timestamp parsing ───────────────────────────────────────────────────────

def test_unparseable_timestamp_excluded(tmp_path):
    """An anchored envelope with a garbage created_at is excluded from
    time-windowed counts (fail-closed), not crashed on."""
    msg = _env("r1", "claude_code_main", from_verified=True)
    msg["created_at"] = "not-a-date"
    brain = _build_brain(tmp_path, {"claude_code_main": [msg]})
    report = sq.run_seam_query(brain)
    assert report["scan_stats"]["unparseable_timestamps"] == 1
    assert report["rolling_window"]["qualifying_volume"] == 0
