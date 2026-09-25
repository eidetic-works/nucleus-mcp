"""_update_task must persist the fields it accepts, and say so when it drops one.

Why this exists: `_pause_and_ask` was fixed to write `pause_reason`, a test
asserted the fix, the test passed -- and every paused task still read
`pause_reason: None`. The test asserted on the payload handed to _update_task,
not on what came back out of storage. _update_task filters updates against a
`valid_keys` allowlist that did not contain `pause_reason` (nor `claimed_at`),
so the write was accepted, filtered away, and reported as success.

That is the whole failure family in one function: a real call, correct-looking,
pointed at a field that silently did not exist. The lesson encoded here is that
a write test must read the value BACK from storage.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime import task_ops


@pytest.fixture()
def brain():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td) / ".brain"
        b.mkdir(parents=True)
        with patch.object(task_ops, "get_brain_path", return_value=b):
            yield b


def _mk(desc="probe task"):
    r = task_ops._add_task(description=desc, priority=2)
    return r["task"]["id"]


def _read(tid):
    return next((t for t in task_ops._list_tasks() if t["id"] == tid), None)


def test_pause_reason_survives_a_round_trip(brain):
    """THE BUG: written, reported successful, and gone on read-back."""
    tid = _mk()
    task_ops._update_task(tid, {"status": "PAUSED", "pause_reason": "verification found no commit SHA"})
    got = _read(tid)
    assert got["status"] == "PAUSED"
    assert got.get("pause_reason") == "verification found no commit SHA", (
        f"pause_reason did not persist -- got {got.get('pause_reason')!r}. "
        f"A pause that records no reason is an unreadable failure."
    )


def test_claimed_at_survives_a_round_trip(brain):
    """Same allowlist gap: claim-timestamp resets silently no-opped."""
    tid = _mk()
    task_ops._update_task(tid, {"claimed_at": "2026-08-19T10:00:00Z"})
    assert _read(tid).get("claimed_at") == "2026-08-19T10:00:00Z"


def test_an_unknown_field_is_refused_out_loud(brain, caplog):
    """OPPOSED: the allowlist must keep rejecting unknown fields -- widening it
    to 'accept anything' would be the wrong fix. But the rejection has to be
    audible, because silence is what made the original bug invisible."""
    tid = _mk()
    with caplog.at_level("WARNING"):
        task_ops._update_task(tid, {"totally_made_up_field": "x"})
    assert _read(tid).get("totally_made_up_field") is None, "allowlist stopped filtering"
    assert any("totally_made_up_field" in r.getMessage() for r in caplog.records), (
        "unknown field was dropped SILENTLY -- the exact behaviour that hid this bug"
    )


def test_a_valid_field_alongside_an_invalid_one_still_lands(brain):
    """OPPOSED: one bad key must not cost the good keys in the same call."""
    tid = _mk()
    task_ops._update_task(tid, {"status": "BLOCKED", "nonsense_key": "x"})
    assert _read(tid)["status"] == "BLOCKED"
