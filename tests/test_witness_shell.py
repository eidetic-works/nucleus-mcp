"""test_witness_shell.py — Tests for the shell-execution witness.

Tests:
  - log_shell_exec writes to .brain/witness/shell_log.jsonl
  - query_shell_exec finds matching commands (substring match)
  - query_shell_exec returns False for no match
  - query_shell_exec filters by agent_id
  - query_shell_exec filters by since_timestamp
  - Agents cannot write to the witness (the OS owns it)
  - get_witness_entries returns entries in order
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.agent_os.witness_shell import (
    log_shell_exec,
    query_shell_exec,
    get_witness_entries,
    _witness_path,
)


@pytest.fixture
def tmp_brain(tmp_path):
    """Create a temp brain with a witness directory."""
    return tmp_path


class TestLogShellExec:
    """Test log_shell_exec writes to the witness file."""

    def test_log_creates_witness_file(self, tmp_brain):
        """log_shell_exec creates .brain/witness/shell_log.jsonl."""
        witness_file = tmp_brain / "witness" / "shell_log.jsonl"
        assert not witness_file.exists()

        log_shell_exec(
            command="pytest tests/test_foo.py",
            pid=12345,
            exit_code=0,
            brain_path=str(tmp_brain),
        )

        assert witness_file.exists()

    def test_log_writes_valid_json(self, tmp_brain):
        """Each log entry is valid JSON with the required fields."""
        entry_id = log_shell_exec(
            command="npm run build",
            pid=67890,
            exit_code=0,
            agent_id="cell-1",
            brain_path=str(tmp_brain),
        )

        witness_file = _witness_path(str(tmp_brain))
        with witness_file.open() as f:
            entry = json.loads(f.readline())

        assert entry["witness_id"] == entry_id
        assert entry["command"] == "npm run build"
        assert entry["pid"] == 67890
        assert entry["exit_code"] == 0
        assert entry["agent_id"] == "cell-1"
        assert "timestamp" in entry
        assert "iso_timestamp" in entry

    def test_log_appends_not_overwrites(self, tmp_brain):
        """Multiple logs append to the same file."""
        log_shell_exec(command="echo hello", brain_path=str(tmp_brain))
        log_shell_exec(command="echo world", brain_path=str(tmp_brain))

        witness_file = _witness_path(str(tmp_brain))
        with witness_file.open() as f:
            lines = f.readlines()
        assert len(lines) == 2


class TestQueryShellExec:
    """Test query_shell_exec finds matching commands."""

    def test_query_finds_matching_command(self, tmp_brain):
        """query_shell_exec returns True for a logged command."""
        log_shell_exec(command="pytest tests/test_foo.py -v", brain_path=str(tmp_brain))

        found = query_shell_exec("pytest", brain_path=str(tmp_brain))
        assert found is True

    def test_query_returns_false_for_no_match(self, tmp_brain):
        """query_shell_exec returns False when no command matches."""
        log_shell_exec(command="npm run build", brain_path=str(tmp_brain))

        found = query_shell_exec("pytest", brain_path=str(tmp_brain))
        assert found is False

    def test_query_substring_match(self, tmp_brain):
        """query_shell_exec matches substrings, not exact commands."""
        log_shell_exec(command="python3 scripts/foo.py --bar baz", brain_path=str(tmp_brain))

        found = query_shell_exec("foo.py", brain_path=str(tmp_brain))
        assert found is True

    def test_query_filters_by_agent_id(self, tmp_brain):
        """query_shell_exec filters by agent_id when specified."""
        log_shell_exec(command="pytest", agent_id="cell-A", brain_path=str(tmp_brain))
        log_shell_exec(command="npm run build", agent_id="cell-B", brain_path=str(tmp_brain))

        found_a = query_shell_exec("pytest", agent_id="cell-A", brain_path=str(tmp_brain))
        found_b = query_shell_exec("pytest", agent_id="cell-B", brain_path=str(tmp_brain))
        assert found_a is True
        assert found_b is False

    def test_query_filters_by_timestamp(self, tmp_brain):
        """query_shell_exec filters by since_timestamp."""
        old_ts = time.time() - 100
        log_shell_exec(command="pytest", brain_path=str(tmp_brain))

        # Query with a timestamp before the log → should find it
        found_before = query_shell_exec("pytest", since_timestamp=old_ts, brain_path=str(tmp_brain))
        assert found_before is True

        # Query with a timestamp after the log → should not find it
        future_ts = time.time() + 100
        found_after = query_shell_exec("pytest", since_timestamp=future_ts, brain_path=str(tmp_brain))
        assert found_after is False

    def test_query_empty_brain_returns_insufficient_not_false(self, tmp_brain):
        """No witness file means INSUFFICIENT (None), not False.

        This test previously asserted `found is False` and was renamed rather
        than deleted, because it encoded the bug as an expectation: False means
        "that command did not run", which is a definitive negative
        manufactured from a file that was never written.

        The distinction is not academic here. The witness log is written only by
        scripts/witness_bridge.py, and nothing invokes that bridge -- so in the
        live system this was the ONLY branch, and every referee query returned a
        confident False about commands it had no record of either way.
        """
        found = query_shell_exec("pytest", brain_path=str(tmp_brain))
        assert found is None, f"absent log returned {found!r}; None means INSUFFICIENT"

    def test_query_real_miss_is_still_false(self, tmp_brain):
        """OPPOSED, and the control that makes the change above safe: with a log
        PRESENT and the command genuinely absent from it, the answer really is
        no. A referee that can no longer say False would be worse than one that
        says it too often."""
        log_shell_exec(command="npm run build", brain_path=str(tmp_brain))
        assert query_shell_exec("pytest", brain_path=str(tmp_brain)) is False


class TestGetWitnessEntries:
    """Test get_witness_entries for debugging / inspection."""

    def test_get_entries_returns_all(self, tmp_brain):
        """get_witness_entries returns all entries."""
        log_shell_exec(command="cmd1", brain_path=str(tmp_brain))
        log_shell_exec(command="cmd2", brain_path=str(tmp_brain))
        log_shell_exec(command="cmd3", brain_path=str(tmp_brain))

        entries = get_witness_entries(brain_path=str(tmp_brain))
        assert len(entries) == 3
        assert entries[0]["command"] == "cmd1"
        assert entries[2]["command"] == "cmd3"

    def test_get_entries_filters_by_agent(self, tmp_brain):
        """get_witness_entries filters by agent_id."""
        log_shell_exec(command="cmd1", agent_id="A", brain_path=str(tmp_brain))
        log_shell_exec(command="cmd2", agent_id="B", brain_path=str(tmp_brain))

        entries = get_witness_entries(agent_id="A", brain_path=str(tmp_brain))
        assert len(entries) == 1
        assert entries[0]["agent_id"] == "A"

    def test_get_entries_respects_limit(self, tmp_brain):
        """get_witness_entries respects the limit parameter."""
        for i in range(10):
            log_shell_exec(command=f"cmd{i}", brain_path=str(tmp_brain))

        entries = get_witness_entries(limit=3, brain_path=str(tmp_brain))
        assert len(entries) == 3
        # Should return the LAST 3 (most recent)
        assert entries[0]["command"] == "cmd7"
        assert entries[2]["command"] == "cmd9"


class TestWitnessAuthority:
    """Test that the witness is outside agent authority."""

    def test_witness_dir_is_separate_from_training(self, tmp_brain):
        """The witness directory is separate from the training directory."""
        log_shell_exec(command="pytest", brain_path=str(tmp_brain))

        witness_dir = tmp_brain / "witness"
        training_dir = tmp_brain / "training"

        assert witness_dir.exists()
        assert witness_dir != training_dir
