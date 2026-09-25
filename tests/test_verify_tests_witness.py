"""Tests for runtime/agent_os/verify_tests.py — run_and_witness and parse_counts.

All test runs are simulated with ``python3 -c`` subprocesses so the suite
exercises verify_tests without invoking real pytest recursively. Every test
uses an isolated temporary brain directory and monkeypatch for the signing key;
nothing writes to the real ``.brain``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.agent_os.verify_tests import (
    parse_counts,
    run_and_witness,
)
from mcp_server_nucleus.runtime.agent_os.witness_test_results import (
    query_test_result,
)


SIGN_KEY_ENV = "NUCLEUS_WITNESS_SIGN_KEY"


def _witness_file(brain: Path) -> Path:
    return brain / "witness" / "test_results.jsonl"


def _witness_line_count(brain: Path) -> int:
    path = _witness_file(brain)
    if not path.exists():
        return 0
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _passing_summary(n: int = 1) -> list[str]:
    return [
        "python3",
        "-c",
        f"import sys; print('{n} passed in 0.01s'); sys.exit(0)",
    ]


def _failing_summary(failed: int = 1, passed: int = 1, skipped: int = 0) -> list[str]:
    summary = f"{failed} failed, {passed} passed"
    if skipped:
        summary += f", {skipped} skipped"
    summary += " in 0.01s"
    return ["python3", "-c", f"import sys; print({summary!r}); sys.exit(1)"]


class TestRunAndWitness:
    def test_passing_run(self, tmp_path, monkeypatch):
        monkeypatch.setenv(SIGN_KEY_ENV, "test-signing-key")
        brain = tmp_path
        run_id = "run-pass-001"
        command = _passing_summary(120)

        outcome = run_and_witness(
            command, brain_path=str(brain), test_run_id=run_id
        )

        assert outcome.state == "recorded"
        assert outcome.failed == 0
        assert outcome.witness_id is not None
        assert _witness_line_count(brain) == 1

    def test_failing_run(self, tmp_path, monkeypatch):
        monkeypatch.setenv(SIGN_KEY_ENV, "test-signing-key")
        brain = tmp_path
        run_id = "run-fail-001"
        command = _failing_summary(failed=5, passed=120, skipped=3)

        outcome = run_and_witness(
            command, brain_path=str(brain), test_run_id=run_id
        )

        assert outcome.state == "recorded"
        assert outcome.failed > 0
        assert outcome.witness_id is not None
        assert _witness_line_count(brain) == 1

    def test_missing_binary(self, tmp_path, monkeypatch):
        brain = tmp_path
        command = ["definitely-no-such-binary-for-verify-tests"]

        outcome = run_and_witness(command, brain_path=str(brain))

        assert outcome.state == "insufficient"
        assert outcome.witness_id is None
        assert _witness_line_count(brain) == 0

    def test_nonzero_unparseable(self, tmp_path, monkeypatch):
        brain = tmp_path
        command = [
            "python3",
            "-c",
            "import sys; print('unparseable noise'); sys.exit(1)",
        ]

        outcome = run_and_witness(command, brain_path=str(brain))

        assert outcome.state == "insufficient"
        assert outcome.witness_id is None
        assert _witness_line_count(brain) == 0

    def test_exit_zero_with_failures(self, tmp_path, monkeypatch):
        monkeypatch.setenv(SIGN_KEY_ENV, "test-signing-key")
        brain = tmp_path
        run_id = "run-trust-summary"
        command = [
            "python3",
            "-c",
            "import sys; print('5 failed, 120 passed in 4.20s'); sys.exit(0)",
        ]

        outcome = run_and_witness(
            command, brain_path=str(brain), test_run_id=run_id
        )

        assert outcome.state == "recorded"
        assert outcome.failed == 5
        assert outcome.witness_id is not None
        assert _witness_line_count(brain) == 1

    def test_nonzero_with_zero_parsed_failures(self, tmp_path, monkeypatch):
        brain = tmp_path
        command = [
            "python3",
            "-c",
            "import sys; print('120 passed in 0.01s'); sys.exit(1)",
        ]

        outcome = run_and_witness(command, brain_path=str(brain))

        assert outcome.state == "insufficient"
        assert outcome.failed == 0
        assert outcome.witness_id is None
        assert _witness_line_count(brain) == 0

    def test_missing_witness_sign_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv(SIGN_KEY_ENV, raising=False)
        brain = tmp_path
        run_id = "run-no-sign-key"
        command = _passing_summary(1)

        outcome = run_and_witness(
            command, brain_path=str(brain), test_run_id=run_id
        )

        assert outcome.state == "insufficient"
        assert outcome.witness_id is None
        assert "could not be witnessed" in outcome.reason.lower()
        assert _witness_line_count(brain) == 0

    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setenv(SIGN_KEY_ENV, "test-signing-key")
        brain = tmp_path
        pass_id = "run-round-pass"
        fail_id = "run-round-fail"

        pass_out = run_and_witness(
            _passing_summary(2), brain_path=str(brain), test_run_id=pass_id
        )
        fail_out = run_and_witness(
            _failing_summary(failed=1, passed=2),
            brain_path=str(brain),
            test_run_id=fail_id,
        )

        assert pass_out.state == "recorded"
        assert pass_out.failed == 0
        assert fail_out.state == "recorded"
        assert fail_out.failed > 0

        assert (
            query_test_result(
                pass_id, brain_path=str(brain), require_all_passed=True
            )
            is True
        )
        assert (
            query_test_result(
                fail_id, brain_path=str(brain), require_all_passed=True
            )
            is False
        )


class TestParseCounts:
    def test_unparseable_output_returns_none(self):
        assert parse_counts("") is None
        assert parse_counts("No tests here") is None
        assert parse_counts("something went wrong") is None

    def test_parses_pytest_summary(self):
        result = parse_counts("5 failed, 120 passed, 3 skipped in 4.20s")
        assert result == {"passed": 120, "failed": 5, "skipped": 3}
