"""Activity gate — opposed pairs.

The claim under test is negative: that TIME cannot fire this trigger. A test
suite that only ever shows it firing on activity would pass just as happily
against a nightly cron.
"""

import json
import os
import time

import pytest

from mcp_server_nucleus.flywheel import trigger


def _sessions(tmp_path, n, mtime=None):
    root = tmp_path / "projects" / "proj"
    root.mkdir(parents=True, exist_ok=True)
    made = []
    for i in range(n):
        f = root / f"s{i}-{time.time_ns()}.jsonl"
        f.write_text(json.dumps({"message": {"content": "x"}}) + "\n")
        if mtime is not None:
            os.utime(f, (mtime, mtime))
        made.append(f)
    return made


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / "brain"
    b.mkdir()
    return b


# --- THE CENTRAL REFUSAL: a clock cannot fire this -------------------------

def test_elapsed_time_alone_never_fires_the_trigger(tmp_path, brain):
    """The whole point of item 62.

    Set the last pass a year in the past and add NO new work. A calendar
    trigger fires here. This one must not.
    """
    roots = [tmp_path / "projects"]
    _sessions(tmp_path, 5, mtime=time.time() - 400 * 86400)
    trigger.record_pass(brain, watermark=time.time() - 365 * 86400)
    d = trigger.should_run(brain, roots=roots, min_new_sessions=3)
    assert d.should_run is False
    assert d.new_sessions == 0
    assert "Time passing does not change this" in d.reason


def test_new_work_fires_it_with_no_time_having_passed(tmp_path, brain):
    """The opposed half: no elapsed time, but real new sessions."""
    roots = [tmp_path / "projects"]
    trigger.record_pass(brain, watermark=time.time() - 1)
    _sessions(tmp_path, 4)  # created now, after the watermark
    d = trigger.should_run(brain, roots=roots, min_new_sessions=3)
    assert d.should_run is True
    assert d.new_sessions == 4


# --- thresholds ------------------------------------------------------------

def test_below_the_floor_does_not_fire(tmp_path, brain):
    roots = [tmp_path / "projects"]
    trigger.record_pass(brain, watermark=time.time() - 1)
    _sessions(tmp_path, 2)
    assert trigger.should_run(brain, roots=roots, min_new_sessions=5).should_run is False


def test_exactly_at_the_floor_fires(tmp_path, brain):
    roots = [tmp_path / "projects"]
    trigger.record_pass(brain, watermark=time.time() - 1)
    _sessions(tmp_path, 5)
    assert trigger.should_run(brain, roots=roots, min_new_sessions=5).should_run is True


# --- first run and the empty case ------------------------------------------

def test_first_ever_run_treats_the_corpus_as_accumulated_activity(tmp_path, brain):
    roots = [tmp_path / "projects"]
    _sessions(tmp_path, 3)
    d = trigger.should_run(brain, roots=roots, min_new_sessions=100)
    assert d.should_run is True
    assert "No pass has ever run" in d.reason


def test_no_corpus_is_reported_as_no_corpus_not_as_no_activity(tmp_path, brain):
    """0 of 0 is not evidence of quiet."""
    d = trigger.should_run(brain, roots=[tmp_path / "nothing"], min_new_sessions=1)
    assert d.should_run is False
    assert "no visible corpus" in d.reason


def test_a_corrupt_watermark_refuses_rather_than_treating_all_as_new(tmp_path, brain):
    roots = [tmp_path / "projects"]
    _sessions(tmp_path, 10)
    (brain / trigger.STATE_FILE).write_text(json.dumps({"watermark": "not-a-time"}))
    d = trigger.should_run(brain, roots=roots, min_new_sessions=1)
    assert d.should_run is False
    assert "not a timestamp" in d.reason


# --- the watermark advances ------------------------------------------------

def test_recording_a_pass_stops_the_same_work_firing_twice(tmp_path, brain):
    roots = [tmp_path / "projects"]
    _sessions(tmp_path, 6)
    first = trigger.should_run(brain, roots=roots, min_new_sessions=3)
    assert first.should_run is True
    trigger.record_pass(brain)
    second = trigger.should_run(brain, roots=roots, min_new_sessions=3)
    assert second.should_run is False, "the same sessions fired a second pass"
    assert second.new_sessions == 0


def test_a_pass_that_found_nothing_still_advances_the_watermark(tmp_path, brain):
    """Otherwise an unproductive pass re-reads the same corpus forever."""
    roots = [tmp_path / "projects"]
    _sessions(tmp_path, 4)
    trigger.record_pass(brain, proposals_made=0)
    assert trigger.should_run(brain, roots=roots, min_new_sessions=1).should_run is False


def test_an_unreadable_state_file_does_not_crash_the_gate(tmp_path, brain):
    roots = [tmp_path / "projects"]
    _sessions(tmp_path, 3)
    (brain / trigger.STATE_FILE).write_text("{not json")
    d = trigger.should_run(brain, roots=roots, min_new_sessions=1)
    assert d.should_run is True  # falls back to "never run"
