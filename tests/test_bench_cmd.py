"""Tests for ``nucleus_wedge.bench_cmd.do_bench`` (Phase 6, criterion #1).

Covers: subprocess timing mode, manual-duration mode, mutual-exclusion
validation, run_id resolution (env var vs minted), append semantics,
brain-path flag.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nucleus_wedge.bench_cmd import do_bench


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_subprocess_mode_writes_row_with_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BENCH_RUN_ID", "TESTRUN1")

    rc = do_bench("clone", ["true"], None, brain_path_arg=str(brain))

    assert rc == 0
    out_path = brain / "metrics" / "week2_timing_TESTRUN1.jsonl"
    rows = _read_rows(out_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["segment"] == "clone"
    assert row["run_id"] == "TESTRUN1"
    assert row["command"] == ["true"]
    assert row["exit_code"] == 0
    assert row["manual"] is False
    assert row["duration_seconds"] >= 0.0


def test_subprocess_mode_propagates_nonzero_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BENCH_RUN_ID", "TESTRUN2")

    rc = do_bench("init", ["false"], None, brain_path_arg=str(brain))

    assert rc == 1
    rows = _read_rows(brain / "metrics" / "week2_timing_TESTRUN2.jsonl")
    assert rows[0]["exit_code"] == 1


def test_manual_duration_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BENCH_RUN_ID", "TESTRUN3")

    rc = do_bench("cc_restart", None, 12.5, brain_path_arg=str(brain))

    assert rc == 0
    rows = _read_rows(brain / "metrics" / "week2_timing_TESTRUN3.jsonl")
    assert rows[0]["segment"] == "cc_restart"
    assert rows[0]["duration_seconds"] == 12.5
    assert rows[0]["manual"] is True
    assert rows[0]["command"] is None
    assert rows[0]["exit_code"] is None


def test_neither_mode_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brain = tmp_path / ".brain"
    rc = do_bench("clone", None, None, brain_path_arg=str(brain))
    assert rc == 2
    err = capsys.readouterr().err
    assert "either '-- <command>' OR '--manual-duration <sec>'" in err


def test_both_modes_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brain = tmp_path / ".brain"
    rc = do_bench("clone", ["true"], 1.0, brain_path_arg=str(brain))
    assert rc == 2
    err = capsys.readouterr().err
    assert "either '-- <command>' OR '--manual-duration <sec>'" in err


def test_run_id_minted_when_env_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    brain = tmp_path / ".brain"
    monkeypatch.delenv("NUCLEUS_BENCH_RUN_ID", raising=False)

    rc = do_bench("clone", ["true"], None, brain_path_arg=str(brain))

    assert rc == 0
    err = capsys.readouterr().err
    assert "NUCLEUS_BENCH_RUN_ID not set; minted:" in err
    assert "export NUCLEUS_BENCH_RUN_ID=" in err
    files = list((brain / "metrics").glob("week2_timing_*.jsonl"))
    assert len(files) == 1
    assert files[0].name.startswith("week2_timing_")


def test_multiple_calls_append_to_same_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BENCH_RUN_ID", "TESTRUN4")

    do_bench("clone", ["true"], None, brain_path_arg=str(brain))
    do_bench("init", ["true"], None, brain_path_arg=str(brain))
    do_bench("first_recall", None, 0.42, brain_path_arg=str(brain))

    rows = _read_rows(brain / "metrics" / "week2_timing_TESTRUN4.jsonl")
    assert [r["segment"] for r in rows] == ["clone", "init", "first_recall"]
    assert rows[2]["duration_seconds"] == 0.42


def test_brain_path_resolution_via_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = tmp_path / "custom_brain"
    monkeypatch.setenv("NUCLEUS_BENCH_RUN_ID", "TESTRUN5")

    do_bench("clone", ["true"], None, brain_path_arg=str(brain))

    assert (brain / "metrics" / "week2_timing_TESTRUN5.jsonl").exists()


def test_cli_argv_split_preserves_command_after_dashdash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: bench flags BEFORE ``--`` must not be consumed by the command after.
    Burned during live-fire 2026-04-19: REMAINDER consumed --brain-path as part of command."""
    from nucleus_wedge.__main__ import _split_bench_argv, main

    raw, command = _split_bench_argv(["clone", "--brain-path", "/x", "--", "echo", "hi"])
    assert raw == ["clone", "--brain-path", "/x"]
    assert command == ["echo", "hi"]

    raw2, command2 = _split_bench_argv(["clone", "--manual-duration", "1.0"])
    assert command2 is None
    assert raw2 == ["clone", "--manual-duration", "1.0"]

    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BENCH_RUN_ID", "TESTRUN6")
    rc = main(["bench", "clone", "--brain-path", str(brain), "--", "true"])
    assert rc == 0
    rows = _read_rows(brain / "metrics" / "week2_timing_TESTRUN6.jsonl")
    assert rows[0]["command"] == ["true"]
    assert rows[0]["exit_code"] == 0
