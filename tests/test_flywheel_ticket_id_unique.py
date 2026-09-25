"""Flywheel ticket-id uniqueness test.

Shared fixtures:
  - no_live_gh (autouse): monkeypatches subprocess.run so flywheel never
    shells out to a real `gh` (matches the pattern in test_flywheel_integration.py).
  - brain: creates a minimal .brain directory under tmp_path and points the
    default brain path resolver at it via NUCLEUS_BRAIN_PATH.
"""

import re
import subprocess
import time
import pytest
from datetime import datetime, timezone
from pathlib import Path

from mcp_server_nucleus.flywheel.core import _generate_ticket_id, parse_ticket_epoch


@pytest.fixture(autouse=True)
def no_live_gh(monkeypatch):
    """Never let flywheel tests shell out to a real `gh` — they must not
    create or touch live GitHub issues regardless of local `gh` auth state."""

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="https://github.com/example/repo/issues/1\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)


@pytest.fixture(autouse=True)
def brain(tmp_path, monkeypatch):
    """Create a minimal .brain directory for flywheel tests and point the
    default brain path resolver at it via NUCLEUS_BRAIN_PATH."""
    b = tmp_path / ".brain"
    b.mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


def test_uniqueness_under_same_second_collision():
    # Core regression: 50 ticket ids generated in a tight loop must all be
    # distinct even when they fall in the same wall-clock second.
    #
    # The pre-fix implementation `f'fw-{int(datetime.now(timezone.utc).timestamp())}'`
    # would have produced exactly 1 unique id across these 50 calls — 7 such
    # collisions exist in the live backlog — so this assertion is the real
    # regression guard.
    ids = [_generate_ticket_id() for _ in range(50)]
    epochs = [id.split("-")[1] for id in ids]
    assert len(set(epochs)) == 1  # proves same wall-clock second — the test
    # cannot silently pass by being slow.
    assert len(set(ids)) == 50  # all distinct despite same epoch.


def test_id_shape():
    # Structural contract for a single ticket id: the shape produced by
    # _generate_ticket_id must be exactly `fw-<epoch>-<counter>-<hex4>` with
    # no extra/missing segments, a now-current epoch, and a 4-char lowercase
    # hex tail (the output of secrets.token_hex(2)).
    ticket_id = _generate_ticket_id()
    assert ticket_id.startswith("fw-")
    segments = ticket_id.split("-")
    assert len(segments) == 4, f"expected 4 segments, got {segments}"
    prefix, epoch, counter, hex4 = segments
    assert prefix == "fw"
    assert epoch.isdigit(), f"epoch not numeric: {epoch!r}"
    assert len(epoch) == 10, f"epoch not 10 digits: {epoch!r}"
    assert abs(int(epoch) - int(time.time())) <= 5, (
        f"epoch {epoch} not within 5s of now ({int(time.time())})"
    )
    assert counter.isdigit(), f"counter not numeric: {counter!r}"
    assert re.fullmatch(r"[0-9a-f]{4}", hex4) is not None, (
        f"hex4 not 4 lowercase hex chars: {hex4!r}"
    )


def test_monotonic_counter_does_not_reset_within_process():
    # The per-process counter must be monotonic across consecutive calls — it
    # never resets within a run. Two back-to-back calls must yield consecutive
    # counters (counter2 == counter1 + 1), proving the counter is a true
    # process-global sequence rather than re-initialized per call.
    ticket1 = _generate_ticket_id()
    ticket2 = _generate_ticket_id()
    segments1 = ticket1.split("-")
    segments2 = ticket2.split("-")
    assert len(segments1) == 4, f"expected 4 segments, got {segments1}"
    assert len(segments2) == 4, f"expected 4 segments, got {segments2}"
    counter1 = segments1[2]
    counter2 = segments2[2]
    assert counter1.isdigit(), f"counter1 not numeric: {counter1!r}"
    assert counter2.isdigit(), f"counter2 not numeric: {counter2!r}"
    assert int(counter2) != int(counter1), (
        f"counters did not differ: {counter1} == {counter2}"
    )
    assert int(counter2) == int(counter1) + 1, (
        f"counters not consecutive: {counter1} -> {counter2} "
        f"(expected {int(counter1) + 1})"
    )


def test_legacy_ticket_ids_still_accepted():
    # Guards backward compatibility for pre-existing bare ids.
    # Legacy ticket ids (174 rows in live backlog) use bare format fw-<epoch>
    # and must remain parseable after migration to new format fw-<epoch>-<counter>-<hex4>.

    # Case 1: Legacy bare id parses to correct epoch.
    legacy_id = "fw-1786207260"
    epoch = parse_ticket_epoch(legacy_id)
    assert epoch == 1786207260, f"expected 1786207260, got {epoch!r}"

    # Case 2: New-shape id parses to recent epoch.
    new_id = _generate_ticket_id()
    epoch = parse_ticket_epoch(new_id)
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    assert epoch is not None, f"new id {new_id!r} parsed to None"
    assert isinstance(epoch, int), f"epoch should be int, got {type(epoch).__name__}"
    assert abs(epoch - now_epoch) <= 120, (
        f"new id epoch {epoch} not within 120s of now ({now_epoch})"
    )

    # Case 3: Garbage inputs return None without raising.
    garbage = ["not-a-ticket", "", "fw-", "fw-notanumber", None]
    for bad_input in garbage:
        result = parse_ticket_epoch(bad_input)
        assert result is None, (
            f"expected None for garbage input {bad_input!r}, got {result!r}"
        )
