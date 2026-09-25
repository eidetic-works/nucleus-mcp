"""record_survived() must auto-stamp an UNKNOWN demand-signal entry when none
exists -- closing the exact gap demand_signal.py was built to prevent: CSR
going green (correctness proven) must never silently pass as evidence of
demand (nobody has to ask). Before this wiring, the two ledgers were
independent -- an artifact could be marked survived forever with total
silence on whether anyone wanted it, which is precisely the shape of the
failure this session spent hours finding in the existing corpus.

Each test states its failure direction; a check that can only pass is not a
check.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from mcp_server_nucleus.flywheel.core import Flywheel
from mcp_server_nucleus.flywheel import demand_signal as ds


def test_survived_with_no_prior_demand_record_gets_stamped_unknown():
    """POSITIVE: a fresh artifact, never checked for demand, gets an
    automatic UNKNOWN record the moment it's marked survived."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        Flywheel(brain).record_survived(phase="test", step="fresh_artifact")
        latest = ds.latest_verdict(brain, "test:fresh_artifact")
        assert latest is not None, "record_survived did not create any demand-signal entry"
        assert latest["verdict"] == "unknown"
        assert latest["source"] == "agent_search"


def test_survived_does_not_clobber_an_existing_real_verdict():
    """OPPOSED: an artifact that ALREADY has a real demand verdict (e.g.
    CONFIRMED) must not be silently downgraded to UNKNOWN just because CSR
    bumped again -- that would erase real evidence someone already recorded."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        ds.record_signal(
            brain, artifact="test:known_wanted_thing", verdict="confirmed",
            source="analytics", evidence="real GA4 number, 500 active users",
        )
        Flywheel(brain).record_survived(phase="test", step="known_wanted_thing")
        latest = ds.latest_verdict(brain, "test:known_wanted_thing")
        assert latest["verdict"] == "confirmed", (
            f"a real CONFIRMED verdict was overwritten by the auto-stamp -- "
            f"got {latest['verdict']!r}"
        )


def test_demand_ledger_write_failure_never_costs_the_csr_bump():
    """OPPOSED: if the demand-ledger write blows up for any reason, the CSR
    bump -- the load-bearing half -- must still succeed. Verified by making
    record_signal genuinely raise, not by mocking away the failure path."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        fw = Flywheel(brain)
        before = fw.csr().get("claims_survived", 0)
        with patch(
            "mcp_server_nucleus.flywheel.core.record_signal",
            side_effect=RuntimeError("simulated demand-ledger failure"),
        ):
            fw.record_survived(phase="test", step="csr_must_survive_this")
        after = fw.csr()["claims_survived"]
        assert after == before + 1, (
            "a demand-ledger write failure cost the CSR bump -- the load-bearing "
            "half must never depend on the bookkeeping half"
        )


def test_repeated_survived_calls_on_same_artifact_do_not_duplicate_unknown_stamps():
    """OPPOSED: calling record_survived twice on the same never-checked
    artifact must not spam the ledger with duplicate UNKNOWN entries -- the
    second call sees the first's UNKNOWN record already exists and skips."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        fw = Flywheel(brain)
        fw.record_survived(phase="test", step="repeated_thing")
        fw.record_survived(phase="test", step="repeated_thing")
        records = [r for r in ds.read_signal_ledger(brain) if r["artifact"] == "test:repeated_thing"]
        assert len(records) == 1, (
            f"expected exactly 1 auto-stamped UNKNOWN record, got {len(records)} -- "
            f"repeated CSR bumps are spamming the demand ledger"
        )
