"""survived.jsonl must be written by code, not by convention.

THE DEFECT THIS GUARDS (2026-08-16): `.brain/flywheel/survived.jsonl` had
accumulated 159 lines with ZERO code references — nothing wrote it, nothing read
it. It was appended by hand while the machine-maintained metric (`csr.json`)
went its own way. Roughly twenty closures recorded on 2026-08-14/15 never moved
the CSR: ratio stayed 0.6375, last_updated frozen at 2026-08-15T08:34.

A ledger nobody writes programmatically and nobody reads is not a ledger. It is
a surface that LOOKS like evidence — the "reported success while doing nothing"
shape, found inside the substrate that exists to name it.

Each test states the failure direction. A check that can only pass is not a
check.
"""

import json
import tempfile
from pathlib import Path

from mcp_server_nucleus.flywheel.core import Flywheel
from mcp_server_nucleus.flywheel.csr import bump_survived, bump_unsurvived


def _rows(brain: Path):
    p = brain / "flywheel" / "survived.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().strip().splitlines() if l.strip()]


def _csr(brain: Path):
    return json.loads((brain / "flywheel" / "csr.json").read_text())


def test_record_survived_writes_the_log():
    """POSITIVE: a closure reaches BOTH csr.json and survived.jsonl.

    Fails if survived.jsonl is orphaned again — the original defect.
    """
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        Flywheel(brain).record_survived(phase="test", step="writes-log")

        rows = _rows(brain)
        assert rows, "survived.jsonl was not written — the file is orphaned again"
        assert rows[-1]["survived"] is True
        assert rows[-1]["source"] == "bump", "must be distinguishable from hand-appended"
        assert _csr(brain)["claims_survived"] >= 1


def test_unsurvived_is_recorded_as_failure():
    """OPPOSED: the instrument must be able to emit a NEGATIVE.

    If a failed claim were logged as survived (or dropped), the log could only
    ever say "success" — the exact instrument-cannot-emit-non-zero defect.
    """
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        bump_survived(brain, "test:good")
        before = _csr(brain)["ratio"]

        bump_unsurvived(brain, "test:bad", reason="deliberate")
        after = _csr(brain)["ratio"]

        assert after < before, "ratio must fall on failure; it cannot only go up"
        last = _rows(brain)[-1]
        assert last["survived"] is False
        assert last["reason"] == "deliberate"


def test_phase_and_step_are_split():
    """A 'phase:step' label is stored as separate fields, matching the
    hand-written rows already in the file."""
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        bump_survived(brain, "composedfit-reliability:cron-green-while-db-down")
        last = _rows(brain)[-1]
        assert last["phase"] == "composedfit-reliability"
        assert last["step"] == "cron-green-while-db-down"


def test_log_failure_never_costs_the_metric():
    """The metric bump is load-bearing; the log is not.

    If the log write raises, the CSR must still move. Verified by making the
    directory unwritable rather than by mocking, so the real OSError path runs.
    """
    import os
    import stat

    with tempfile.TemporaryDirectory() as td:
        brain = Path(td) / ".brain"
        bump_survived(brain, "test:seed")          # create the tree
        fw = brain / "flywheel"
        before = _csr(brain)["claims_survived"]

        mode = fw.stat().st_mode
        os.chmod(fw, stat.S_IRUSR | stat.S_IXUSR)   # read-only dir
        try:
            bump_survived(brain, "test:log-blocked")
        finally:
            os.chmod(fw, mode)

        # csr.json is rewritten in place (already exists), so the metric survives
        # even when a NEW append cannot be made.
        assert _csr(brain)["claims_survived"] == before + 1, (
            "a logging failure must never lose the metric bump"
        )
