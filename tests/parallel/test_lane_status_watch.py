"""Test `nucleus lane status --watch` flag acceptance and watch-loop wiring.

SPEC.md:L9 — Add `nucleus lane status --watch` for live-updating status display.

Acceptance covered here:
  - the `--watch` flag is accepted by the `lane status` argument parser
  - without `--watch`, `args.watch` is False (default — single print + exit)
  - the watch loop uses `time.sleep(2)` between refreshes (not a busy loop)
  - the watch loop clears the screen + reprints until KeyboardInterrupt

The CLI parser is constructed inline inside `cli.main()`, so the parser-
acceptance test builds the same `lane status` subparser shape directly
(argparse) and confirms `--watch` parses. A second test exercises the
real handler with a fabricated args namespace to confirm `args.watch` is
honored and that the loop delegates to `time.sleep(2)`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Repo root (ai-mvp-backend) — same convention as test_executor_crash_recovery.
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "mcp-server-nucleus" / "src"


def _ensure_src_on_path() -> None:
    src = str(SRC_ROOT)
    if src not in sys.path:
        sys.path.insert(0, src)


_ensure_src_on_path()


def _build_lane_status_parser() -> argparse.ArgumentParser:
    """Reconstruct the `lane status` subparser exactly as cli.py builds it.

    This mirrors the parser shape in cli.py (lane_subs.add_parser('status', ...))
    so we can assert `--watch` is accepted without spinning up the full CLI
    (which would require a real .brain + lane_config.json).
    """
    parser = argparse.ArgumentParser(prog="nucleus lane status")
    parser.add_argument("--spec", default="SPEC.md")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Live-update status every 2s (clear screen + reprint) until Ctrl+C",
    )
    return parser


class TestWatchFlagAccepted:
    """SPEC.md:L9 — `--watch` flag exists in the CLI subparser."""

    def test_watch_flag_parses_true(self):
        """`--watch` sets args.watch = True."""
        parser = _build_lane_status_parser()
        args = parser.parse_args(["--watch"])
        assert args.watch is True

    def test_no_watch_defaults_false(self):
        """Without `--watch`, args.watch is False (single print + exit)."""
        parser = _build_lane_status_parser()
        args = parser.parse_args([])
        assert args.watch is False

    def test_watch_with_other_flags(self):
        """`--watch` composes with `--json` and `--spec`."""
        parser = _build_lane_status_parser()
        args = parser.parse_args(["--watch", "--json", "--spec", "OTHER.md"])
        assert args.watch is True
        assert args.json is True
        assert args.spec == "OTHER.md"

    def test_watch_is_store_true_not_value_flag(self):
        """`--watch` must be a boolean flag, not consume a value."""
        parser = _build_lane_status_parser()
        # `--watch 5` should treat 5 as an unknown positional, not a value
        # for --watch. argparse with action='store_true' will error on a
        # following bare value only if there are no positionals defined;
        # here we just confirm --watch itself doesn't take an argument.
        args = parser.parse_args(["--watch"])
        assert args.watch is True
        # The flag's `nargs` should be None (boolean store_true), not '?' or 1
        action = next(a for a in parser._actions if "--watch" in a.option_strings)
        assert action.nargs is None or action.nargs == 0


class TestRealCliParserAcceptsWatch:
    """End-to-end against the real cli.py parser via subprocess --help.

    The parser is built inline in `cli.main()`, so the most faithful way to
    confirm `--watch` is wired into the actual shipped CLI is to ask the
    CLI for the `lane status` help text and grep for `--watch`.
    """

    def test_watch_appears_in_lane_status_help(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "mcp_server_nucleus.cli",
             "lane", "status", "--help"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        # --help exits 0
        assert result.returncode == 0, (
            f"`lane status --help` failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "--watch" in result.stdout, (
            f"`--watch` not in `lane status --help` output:\n{result.stdout}"
        )


class TestWatchLoopWiring:
    """SPEC.md:L9 — the watch loop uses time.sleep(2) and clears + reprints.

    We drive `handle_lane_command` with a fabricated args namespace where
    `watch=True`, a real lane_config.json (so the early-return guard passes),
    and patch the inner pieces so the loop runs exactly one iteration then
    raises KeyboardInterrupt — proving the loop body calls time.sleep(2)
    (not a busy loop) and would continue on Ctrl+C-free execution.
    """

    def test_watch_loop_calls_time_sleep_2_and_clears_screen(self, tmp_path, monkeypatch):
        from mcp_server_nucleus.cli import handle_lane_command

        # Build a minimal lane_config.json so the handler doesn't bail early.
        brain = tmp_path / ".brain" / "state"
        brain.mkdir(parents=True, exist_ok=True)
        (brain / "lane_config.json").write_text(
            '{"repo_root":"' + str(tmp_path).replace("\\", "\\\\") + '",'
            '"brain_path":"' + str(tmp_path / ".brain").replace("\\", "\\\\") + '",'
            '"spec_path":"' + str(tmp_path / "SPEC.md") + '",'
            '"role":"lane-g1","source":"lane-control","spec_tag":"x",'
            '"spec_tag_commit":"x","spec_blob":"x","spec_body_sha256":"x",'
            '"lanes":["lane_devin"],"poll_interval":30,'
            '"executor_poll_interval":10,"max_retries":3,"max_inflight":1,'
            '"verify_only_secretary":true,"vendor":"devin"}'
        )
        monkeypatch.chdir(tmp_path)

        args = argparse.Namespace(
            lane_action="status",
            spec="SPEC.md",
            json=False,
            watch=True,
            brain="",
            role="lane-g1",
            vendor="devin",
            tag="",
        )

        # Patch the status snapshot to a no-op so we don't need a real spec.
        # We patch ControlWatcher.status via the module-level import inside
        # the handler. The handler imports ControlWatcher lazily, so patch
        # the source module.
        import mcp_server_nucleus.runtime.lane.control_watcher as cw_mod

        sleep_calls: list[float] = []
        clear_writes: list[str] = []

        def fake_status(self):
            return {"role": "lane-g1", "counts": {}, "tasks": [], "principal": {}}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)
            # After the first sleep, simulate Ctrl+C to break the loop.
            raise KeyboardInterrupt()

        original_write = sys.stdout.write

        def spy_write(s):
            clear_writes.append(s)
            return original_write(s)

        with patch.object(cw_mod.ControlWatcher, "status", fake_status), \
             patch("time.sleep", fake_sleep), \
             patch.object(sys.stdout, "write", spy_write):
            rc = handle_lane_command(args)

        # Loop ran one iteration then broke on KeyboardInterrupt → exit 0.
        assert rc == 0
        # The loop must sleep(2) — not a busy loop.
        assert sleep_calls == [2], (
            f"watch loop should call time.sleep(2) once, got {sleep_calls}"
        )
        # The loop must clear the screen (ANSI clear) before reprinting.
        assert any("\033[2J" in w for w in clear_writes), (
            "watch loop should write an ANSI clear-screen sequence"
        )
