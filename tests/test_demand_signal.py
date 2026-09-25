"""Demand Signal Registry -- "does anyone want this" as a first-class, third-
state ledger, orthogonal to CSR ("did we build it correctly").

THE DEFECT THIS GUARDS AGAINST (found 2026-08-16/17/18, the reason this
module exists): a ~200-file self-congratulatory doc pile described dozens of
"shipped" features with zero external evidence any of them were ever wanted
or used. `brain_patterns` was referenced in three separate strategy docs and
built in none. There was no mechanism that made the absence of demand
evidence visible -- shipping silently read as "wanted".

Each test states its failure direction; a check that can only pass is not a
check.
"""

import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.flywheel import demand_signal as ds


def test_confirmed_verdict_requires_and_stores_evidence():
    """POSITIVE: a CONFIRMED record with real evidence round-trips correctly."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        rec = ds.record_signal(
            brain, artifact="gq_stage0_install_gate", verdict="confirmed",
            source="operator_assertion",
            evidence="Operator directly confirmed 250+ installs/users, 2026-08-18.",
        )
        assert rec["verdict"] == "confirmed"
        latest = ds.latest_verdict(brain, "gq_stage0_install_gate")
        assert latest is not None
        assert latest["verdict"] == "confirmed"
        assert "250" in latest["evidence"]


def test_confirmed_without_evidence_is_rejected():
    """OPPOSED: a verdict claiming real evidence exists, with none supplied,
    must be refused -- a verdict with no evidence is a guess, not a finding."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        with pytest.raises(ValueError, match="evidence"):
            ds.record_signal(
                brain, artifact="unverified_thing", verdict="confirmed",
                source="analytics", evidence="",
            )


def test_none_verdict_also_requires_evidence():
    """OPPOSED: NONE ('checked, found nothing') is a real claim too and must
    show what was checked -- an empty NONE is indistinguishable from never
    having looked, which defeats the whole point of distinguishing them."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        with pytest.raises(ValueError, match="evidence"):
            ds.record_signal(
                brain, artifact="brain_patterns", verdict="none",
                source="agent_search", evidence="",
            )
        # the correct form, for contrast -- must succeed
        rec = ds.record_signal(
            brain, artifact="brain_patterns", verdict="none",
            source="agent_search",
            evidence="grep across mcp-server-nucleus/src and nucleus-mcp/src: "
                     "zero implementation, only a heading in generated index.html.",
        )
        assert rec["verdict"] == "none"


def test_unknown_verdict_does_not_require_evidence():
    """OPPOSED in the other direction: UNKNOWN must NOT be blocked by the
    evidence requirement -- it is the legitimate default for 'never checked',
    and forcing evidence onto it would just train people to write junk text
    to satisfy the validator instead of leaving it honestly unknown."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        rec = ds.record_signal(
            brain, artifact="never_looked_at_this_yet", verdict="unknown",
            source="agent_search",
        )
        assert rec["verdict"] == "unknown"
        assert rec["evidence"] == ""


def test_invalid_verdict_and_source_are_rejected():
    """OPPOSED: the enum guards are real, not decorative."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        with pytest.raises(ValueError):
            ds.record_signal(brain, artifact="x", verdict="probably", source="agent_search")
        with pytest.raises(ValueError):
            ds.record_signal(brain, artifact="x", verdict="unknown", source="vibes")


def test_latest_verdict_is_most_recent_not_first():
    """POSITIVE: an artifact re-checked over time returns its LATEST verdict,
    not its first -- demand status can change (unknown -> none -> confirmed
    as evidence accumulates), and stale early verdicts must not stick."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        ds.record_signal(brain, artifact="feature_x", verdict="unknown", source="agent_search")
        ds.record_signal(
            brain, artifact="feature_x", verdict="none", source="agent_search",
            evidence="checked GA4 and GitHub, nothing found as of first pass",
        )
        ds.record_signal(
            brain, artifact="feature_x", verdict="confirmed", source="direct_feedback",
            evidence="a real support ticket referencing this feature landed 2026-08-20",
        )
        latest = ds.latest_verdict(brain, "feature_x")
        assert latest["verdict"] == "confirmed", "returned a stale earlier verdict, not the latest"


def test_never_checked_artifact_returns_none_not_a_fake_unknown_record():
    """OPPOSED: an artifact with ZERO records must return Python None from
    latest_verdict -- distinct from a real logged verdict of 'unknown' (which
    means 'someone explicitly checked and couldn't determine'). Conflating
    these would erase the difference between 'never asked' and 'asked, no
    answer', which is exactly the distinction this module exists to keep."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        ds.record_signal(brain, artifact="other_thing", verdict="unknown", source="agent_search")
        assert ds.latest_verdict(brain, "totally_different_artifact_never_touched") is None


def test_summarize_counts_are_real_not_vacuous():
    """OPPOSED: summarize() must reflect an EMPTY ledger honestly (all
    zeros, not fabricated numbers), and then reflect real counts after
    records are added -- proving the counter actually counts rather than
    always returning some default-looking shape."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        empty = ds.summarize(brain)
        assert empty == {
            "total_artifacts_checked": 0, "confirmed": 0, "none": 0,
            "unknown": 0, "last_updated": None,
        }
        ds.record_signal(brain, artifact="a", verdict="confirmed", source="analytics", evidence="202 installs, GA4")
        ds.record_signal(brain, artifact="b", verdict="none", source="agent_search", evidence="grep: 0 matches")
        ds.record_signal(brain, artifact="c", verdict="none", source="agent_search", evidence="grep: 0 matches")
        ds.record_signal(brain, artifact="d", verdict="unknown", source="agent_search")
        summary = ds.summarize(brain)
        assert summary["total_artifacts_checked"] == 4
        assert summary["confirmed"] == 1
        assert summary["none"] == 2
        assert summary["unknown"] == 1
        assert summary["last_updated"] is not None


def test_corrupt_line_is_skipped_not_fatal():
    """OPPOSED: a corrupted JSONL line must not crash the whole read, and
    must not be silently counted as a valid record either -- it's dropped,
    the rest of the ledger still reads."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        ds.record_signal(brain, artifact="ok_one", verdict="unknown", source="agent_search")
        ledger_path = brain / "flywheel" / "demand_signal.jsonl"
        with ledger_path.open("a") as fh:
            fh.write("{not valid json at all\n")
        ds.record_signal(brain, artifact="ok_two", verdict="unknown", source="agent_search")
        records = ds.read_signal_ledger(brain)
        assert len(records) == 2, f"expected the 2 valid records, corrupt line should be skipped, got {len(records)}"
