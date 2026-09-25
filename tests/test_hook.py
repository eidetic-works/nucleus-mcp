"""
Tests for the rabbithole PostToolUse hook (mcp_server_nucleus.rabbithole.hook).

Strategy: each test spawns a fresh subprocess per hook invocation, exactly
mirroring production (Claude Code spawns a new process per tool call).
State persists across calls only via the SQLite DB written to a tmp_path.

Assertions cover:
  - depth increments on Read / Grep / read-only Bash
  - depth resets to 0 on Edit / Write / write Bash
  - systemMessage emitted exactly at threshold crossings (danger=3, rabbithole=5)
  - no output between crossings
  - kill-switch (RABBITHOLE_HOOK_DISABLED=1) suppresses all output
  - malformed JSON input exits 0 silently (fail-safe)
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

# Point subprocess at the source tree, not the installed copy.
_SRC = str(pathlib.Path(__file__).parents[1] / "src")
_MODULE = "mcp_server_nucleus.rabbithole.hook"

# Low thresholds so the test completes in a handful of tool calls.
_THRESHOLDS = {
    "RABBITHOLE_DEPTH_CAUTION": "2",
    "RABBITHOLE_DEPTH_DANGER": "3",
    "RABBITHOLE_DEPTH_RABBITHOLE": "5",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hook(payload: dict, db_path: str, *, extra_env: dict | None = None) -> tuple[int, str, str]:
    """Run the hook subprocess with *payload* on stdin.

    Returns ``(returncode, stdout_stripped, stderr_stripped)``.
    """
    env = {
        **os.environ,
        "PYTHONPATH": _SRC,
        "RABBITHOLE_DB_PATH": db_path,
        **_THRESHOLDS,
        **(extra_env or {}),
    }
    proc = subprocess.run(
        [sys.executable, "-m", _MODULE],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _payload(tool_name: str, session: str, **tool_input) -> dict:
    return {
        "session_id": session,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "hook_event_name": "PostToolUse",
        "cwd": "/project",
    }


def _assert_emit(out: str, *, depth: int) -> dict:
    """Assert *out* is valid hook-output JSON mentioning *depth*.

    Per the Claude Code hook contract the human-visible nudge lives at
    top-level ``systemMessage`` (nested under ``hookSpecificOutput`` it is an
    unrecognized field and silently dropped), while the model-facing context
    stays nested at ``hookSpecificOutput.additionalContext``.
    """
    assert out, f"Expected output at depth {depth} but got empty string"
    parsed = json.loads(out)
    # Human channel: top-level systemMessage
    assert "systemMessage" in parsed, f"Missing top-level systemMessage: {parsed}"
    msg = parsed["systemMessage"]
    assert str(depth) in msg, f"Expected depth {depth} in message: {msg!r}"
    assert "reads" in msg, f"Expected 'reads' in message: {msg!r}"
    # Model channel: nested additionalContext
    hso = parsed["hookSpecificOutput"]
    assert hso.get("hookEventName") == "PostToolUse"
    assert hso.get("additionalContext"), f"Missing additionalContext: {parsed}"
    return parsed


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """Fresh SQLite DB path per test."""
    return str(tmp_path / "hook_test.db")


# ---------------------------------------------------------------------------
# Core escalation path
# ---------------------------------------------------------------------------

class TestDepthEscalation:
    """Depth counter escalates on reads and resets on writes."""

    def test_reads_below_threshold_produce_no_output(self, db):
        session = "below-threshold"
        # depth=1 — silent
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        assert rc == 0 and out == ""
        # depth=2 — still silent (danger=3)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        assert rc == 0 and out == ""

    def test_emit_exactly_at_danger_threshold(self, db):
        session = "at-danger"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        # depth=3 == danger → must emit
        rc, out, _ = _hook(_payload("Grep", session, pattern="TODO", path="/proj/c.py"), db)
        assert rc == 0
        parsed = _assert_emit(out, depth=3)
        assert "DANGER" in parsed["systemMessage"]

    def test_no_emit_between_danger_and_rabbithole(self, db):
        session = "between-thresholds"
        # Bring to depth=3 (emits)
        for f in ("a.py", "b.py", "c.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        # depth=4 — between danger(3) and rabbithole(5), no emit
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/d.py"), db)
        assert rc == 0 and out == ""

    def test_emit_at_rabbithole_threshold(self, db):
        session = "at-rabbithole"
        for f in ("a.py", "b.py", "c.py", "d.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        # depth=5 == rabbithole → must emit with RABBIT HOLE label
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/e.py"), db)
        assert rc == 0
        parsed = _assert_emit(out, depth=5)
        msg = parsed["systemMessage"]
        assert "RABBIT HOLE" in msg

    def test_streak_files_appear_in_message(self, db):
        # Use a fresh session; read three files, last one triggers danger emit
        session = "streak-files-check"
        for f in ("x.py", "y.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/z.py"), db)
        assert rc == 0
        _assert_emit(out, depth=3)
        msg = json.loads(out)["systemMessage"]
        # At least one of the recent filenames should appear in the message
        assert any(name in msg for name in ("x.py", "y.py", "z.py"))


# ---------------------------------------------------------------------------
# Reset on write
# ---------------------------------------------------------------------------

class TestResetOnWrite:
    """Edit / Write / write-Bash reset the depth counter to zero."""

    def test_edit_resets_depth(self, db):
        session = "edit-reset"
        # Build up to danger
        for f in ("a.py", "b.py", "c.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)

        # Edit → reset; no output
        rc, out, _ = _hook(_payload("Edit", session, file_path="/proj/a.py"), db)
        assert rc == 0 and out == ""

        # Post-reset: first read → depth=1, silent
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/new.py"), db)
        assert rc == 0 and out == ""

    def test_write_resets_depth(self, db):
        session = "write-reset"
        for f in ("a.py", "b.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        _hook(_payload("Write", session, file_path="/proj/out.py"), db)
        # depth should be 0 now; next read is depth=1
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""

    def test_re_emit_after_reset_and_second_streak(self, db):
        session = "re-emit"
        # First streak → reaches danger (depth=3) → emit
        last_out = ""
        for f in ("a.py", "b.py", "c.py"):
            rc, out, _ = _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
            if out:
                last_out = out
        assert last_out != "", "Expected emit on first streak at depth=3"

        # Reset via Edit
        _hook(_payload("Edit", session, file_path="/proj/a.py"), db)

        # Second streak → reaches danger again (depth=3) → emit again
        second_out = ""
        for f in ("p.py", "q.py", "r.py"):
            rc, out, _ = _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
            if out:
                second_out = out
        assert second_out != "", "Expected emit on second streak at depth=3"
        _assert_emit(second_out, depth=3)

    def test_bash_write_resets_depth(self, db):
        session = "bash-write"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        # git commit is a write Bash → reset
        rc, out, _ = _hook(_payload("Bash", session, command="git commit -m 'fix'"), db)
        assert rc == 0 and out == ""
        # Post-reset read → depth=1, no emit
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""


# ---------------------------------------------------------------------------
# Bash classification
# ---------------------------------------------------------------------------

class TestBashClassification:
    """Read-only Bash commands increment depth; write/run commands reset."""

    def test_grep_bash_increments_depth(self, db):
        session = "bash-grep"
        _hook(_payload("Bash", session, command="grep -r 'TODO' /proj"), db)
        _hook(_payload("Bash", session, command="cat /proj/foo.py"), db)
        rc, out, _ = _hook(_payload("Bash", session, command="ls /proj"), db)
        assert rc == 0
        _assert_emit(out, depth=3)  # depth=3 == danger

    def test_grep_with_redirect_is_write(self, db):
        session = "bash-redirect"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        # grep with > is a write → reset
        _hook(_payload("Bash", session, command="grep foo bar.py > out.txt"), db)
        # depth now 0; next read is depth=1 (silent)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""

    def test_find_increments_depth(self, db):
        session = "bash-find"
        _hook(_payload("Bash", session, command="find . -name '*.py'"), db)
        _hook(_payload("Bash", session, command="wc -l /proj/big.py"), db)
        rc, out, _ = _hook(_payload("Bash", session, command="diff a.py b.py"), db)
        assert rc == 0
        _assert_emit(out, depth=3)

    # --- stderr-redirect classifier regression (1.14.3) ---
    # 2>/dev/null is extremely common on read-only Bash (e.g. the operator's
    # mandatory inbox-poll prepends `ls … 2>/dev/null` to every Bash call).
    # Without stripping stderr redirects, every such call was misclassified
    # as a write → depth reset → Bash-path rabbit-holing was invisible.

    def test_stderr_redirect_to_dev_null_is_read(self, db):
        """`cat x 2>/dev/null` is a READ, not a write."""
        session = "stderr-dev-null"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        # 2>/dev/null must NOT reset — depth should go to 3 (danger)
        rc, out, _ = _hook(
            _payload("Bash", session, command="cat /proj/c.py 2>/dev/null"), db
        )
        assert rc == 0
        _assert_emit(out, depth=3)

    def test_stderr_append_redirect_is_read(self, db):
        """`ls 2>>/tmp/err` is a READ (append to stderr only)."""
        session = "stderr-append"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        rc, out, _ = _hook(
            _payload("Bash", session, command="ls /proj 2>>/tmp/err.log"), db
        )
        assert rc == 0
        _assert_emit(out, depth=3)

    def test_stderr_to_stdout_redirect_is_read(self, db):
        """`grep foo bar 2>&1` is a READ (stderr→stdout, no file write)."""
        session = "stderr-2-stdout"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        rc, out, _ = _hook(
            _payload("Bash", session, command="grep foo /proj/c.py 2>&1"), db
        )
        assert rc == 0
        _assert_emit(out, depth=3)

    def test_stdout_redirect_still_writes(self, db):
        """`grep foo bar > out.txt` is still a WRITE (regression guard)."""
        session = "stdout-redirect-still-write"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        _hook(_payload("Bash", session, command="grep foo bar.py > out.txt"), db)
        # depth reset to 0; next read is depth=1 (silent)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""

    def test_append_redirect_still_writes(self, db):
        """`grep foo bar >> out.txt` is still a WRITE (append to file)."""
        session = "append-redirect-still-write"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        _hook(_payload("Bash", session, command="grep foo bar.py >> out.txt"), db)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""

    def test_fd1_redirect_still_writes(self, db):
        """`grep foo bar 1> out.txt` is still a WRITE (explicit stdout redirect)."""
        session = "fd1-redirect-still-write"
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        _hook(_payload("Bash", session, command="grep foo bar.py 1> out.txt"), db)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""


# ---------------------------------------------------------------------------
# Devin CLI tool-name compatibility (1.14.3)
# ---------------------------------------------------------------------------

class TestDevinToolNames:
    """The hook classifies Devin CLI tool names (lowercase: read, grep, glob,
    exec, edit) the same way it classifies Claude Code names (Read, Grep,
    Bash, Edit, Write). This lets one hook.py serve both agents."""

    def test_devin_read_increments_depth(self, db):
        """Devin `read` tool increments depth, same as Claude Code `Read`."""
        session = "devin-read"
        _hook(_payload("read", session, file_path="/proj/a.py"), db)
        _hook(_payload("read", session, file_path="/proj/b.py"), db)
        rc, out, _ = _hook(_payload("read", session, file_path="/proj/c.py"), db)
        assert rc == 0
        _assert_emit(out, depth=3)

    def test_devin_exec_read_only_increments(self, db):
        """Devin `exec` with a read-only command increments depth."""
        session = "devin-exec-read"
        _hook(_payload("exec", session, command="cat /proj/a.py"), db)
        _hook(_payload("exec", session, command="ls /proj"), db)
        rc, out, _ = _hook(_payload("exec", session, command="grep TODO /proj/c.py"), db)
        assert rc == 0
        _assert_emit(out, depth=3)

    def test_devin_exec_write_resets(self, db):
        """Devin `exec` with a write command resets depth."""
        session = "devin-exec-write"
        _hook(_payload("read", session, file_path="/proj/a.py"), db)
        _hook(_payload("read", session, file_path="/proj/b.py"), db)
        _hook(_payload("exec", session, command="git commit -m 'fix'"), db)
        rc, out, _ = _hook(_payload("read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""

    def test_devin_edit_resets(self, db):
        """Devin `edit` tool resets depth, same as Claude Code `Edit`."""
        session = "devin-edit"
        _hook(_payload("read", session, file_path="/proj/a.py"), db)
        _hook(_payload("read", session, file_path="/proj/b.py"), db)
        _hook(_payload("edit", session, file_path="/proj/a.py"), db)
        rc, out, _ = _hook(_payload("read", session, file_path="/proj/c.py"), db)
        assert rc == 0 and out == ""

    def test_devin_glob_increments(self, db):
        """Devin `glob` tool (file discovery) increments depth."""
        session = "devin-glob"
        _hook(_payload("glob", session, pattern="*.py", path="/proj"), db)
        _hook(_payload("read", session, file_path="/proj/a.py"), db)
        rc, out, _ = _hook(_payload("read", session, file_path="/proj/b.py"), db)
        assert rc == 0
        _assert_emit(out, depth=3)

    def test_devin_exec_stderr_redirect_is_read(self, db):
        """Devin `exec` with 2>/dev/null is a read (classifier fix applies)."""
        session = "devin-exec-stderr"
        _hook(_payload("read", session, file_path="/proj/a.py"), db)
        _hook(_payload("read", session, file_path="/proj/b.py"), db)
        rc, out, _ = _hook(
            _payload("exec", session, command="cat /proj/c.py 2>/dev/null"), db
        )
        assert rc == 0
        _assert_emit(out, depth=3)


# ---------------------------------------------------------------------------
# Classifier battery — both Devin + Claude Code tool-name dialects
# ---------------------------------------------------------------------------

class TestClassifierBattery:
    """Focused battery covering the full _classify matrix for both Devin
    (read/grep/glob/exec/edit) and Claude Code (Read/Grep/Bash/Edit) tool-name
    dialects. Tests _classify directly (no subprocess) for speed and clarity."""

    def _cls(self, tool_name, **tool_input):
        import sys, pathlib
        _SRC = str(pathlib.Path(__file__).parents[1] / "src")
        if _SRC not in sys.path:
            sys.path.insert(0, _SRC)
        from mcp_server_nucleus.rabbithole.hook import _classify
        return _classify(tool_name, tool_input)

    # --- Devin tool names ---

    def test_devin_read_is_read(self):
        assert self._cls("read", file_path="/proj/a.py") == "read"

    def test_devin_grep_is_read(self):
        assert self._cls("grep", pattern="TODO", path="/proj") == "read"

    def test_devin_glob_is_read(self):
        assert self._cls("glob", pattern="*.py", path="/proj") == "read"

    def test_devin_edit_is_write(self):
        assert self._cls("edit", file_path="/proj/a.py") == "write"

    def test_devin_exec_cat_is_read(self):
        assert self._cls("exec", command="cat /proj/a.py") == "read"

    def test_devin_exec_cat_stderr_is_read(self):
        assert self._cls("exec", command="cat /proj/a.py 2>/dev/null") == "read"

    def test_devin_exec_cat_stdout_redirect_is_write(self):
        assert self._cls("exec", command="cat /proj/a.py > out.txt") == "write"

    def test_devin_exec_python3_is_write(self):
        """Running a script (python3 f.py) is a write/run, not a read."""
        assert self._cls("exec", command="python3 /proj/run_tests.py") == "write"

    def test_devin_exec_git_commit_is_write(self):
        assert self._cls("exec", command="git commit -m 'fix'") == "write"

    # --- Redirect semantics (bash) ---

    def test_bash_append_redirect_is_write(self):
        assert self._cls("Bash", command="cat /proj/a.py >> out.txt") == "write"

    def test_bash_ampersand_redirect_is_write(self):
        """&> redirects stdout AND stderr to a file — it is a write."""
        assert self._cls("Bash", command="cat /proj/a.py &> out.txt") == "write"

    def test_bash_ampersand_append_redirect_is_write(self):
        """&>> appends stdout AND stderr to a file — it is a write."""
        assert self._cls("Bash", command="cat /proj/a.py &>> out.txt") == "write"

    def test_bash_stderr_append_is_read(self):
        """2>> only redirects stderr; the command itself stays a read."""
        assert self._cls("Bash", command="grep TODO /proj 2>> /tmp/err.log") == "read"

    def test_bash_stderr_to_stdout_dup_is_read(self):
        """2>&1 duplicates stderr onto stdout — no file write."""
        assert self._cls("Bash", command="cat /proj/a.py 2>&1") == "read"

    def test_bash_digit_suffixed_word_redirect_is_write(self):
        """In `cat file2> out` bash parses `file2` as a word and `>` as a
        stdout redirect — the trailing digit is not an fd number."""
        assert self._cls("Bash", command="cat file2> out.txt") == "write"

    def test_bash_stdout_redirect_with_stderr_dup_is_write(self):
        assert self._cls("Bash", command="cat /proj/a.py > out.txt 2>&1") == "write"

    # --- Claude Code tool names ---

    def test_cc_read_is_read(self):
        assert self._cls("Read", file_path="/proj/a.py") == "read"

    def test_cc_grep_is_read(self):
        assert self._cls("Grep", pattern="TODO", path="/proj") == "read"

    def test_cc_bash_cat_is_read(self):
        assert self._cls("Bash", command="cat /proj/a.py") == "read"

    def test_cc_bash_cat_stderr_is_read(self):
        assert self._cls("Bash", command="cat /proj/a.py 2>/dev/null") == "read"

    def test_cc_bash_cat_redirect_is_write(self):
        assert self._cls("Bash", command="cat /proj/a.py > out.txt") == "write"

    def test_cc_edit_is_write(self):
        assert self._cls("Edit", file_path="/proj/a.py") == "write"

    def test_cc_write_is_write(self):
        assert self._cls("Write", file_path="/proj/a.py") == "write"

    # --- Neutral ---

    def test_mcp_tool_is_neutral(self):
        assert self._cls("mcp__github__create_issue", title="x") == "neutral"

    def test_webfetch_is_neutral(self):
        assert self._cls("WebFetch", url="https://example.com") == "neutral"


# ---------------------------------------------------------------------------
# Neutral tools
# ---------------------------------------------------------------------------

class TestNeutralTools:
    """MCP and other tools neither increment nor reset depth."""

    def test_mcp_tool_is_neutral(self, db):
        session = "neutral-mcp"
        # 2 reads → depth=2 (below danger=3)
        _hook(_payload("Read", session, file_path="/proj/a.py"), db)
        _hook(_payload("Read", session, file_path="/proj/b.py"), db)
        # WebFetch → neutral
        rc, out, _ = _hook(_payload("WebFetch", session, url="https://example.com"), db)
        assert rc == 0 and out == ""
        # 3rd read should still be depth=3 (neutral didn't reset)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/c.py"), db)
        assert rc == 0
        _assert_emit(out, depth=3)


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    """RABBITHOLE_HOOK_DISABLED=1 suppresses all output at every depth."""

    def test_disabled_no_output_even_past_threshold(self, db):
        session = "disabled"
        for f in ("a.py", "b.py", "c.py", "d.py", "e.py", "f.py"):
            rc, out, _ = _hook(
                _payload("Read", session, file_path=f"/proj/{f}"),
                db,
                extra_env={"RABBITHOLE_HOOK_DISABLED": "1"},
            )
            assert rc == 0 and out == ""


# ---------------------------------------------------------------------------
# Fail-safe
# ---------------------------------------------------------------------------

class TestFailSafe:
    """Malformed or empty input must never crash the hook."""

    def test_malformed_json_exits_zero_silently(self, db):
        env = {**os.environ, "PYTHONPATH": _SRC, "RABBITHOLE_DB_PATH": db, **_THRESHOLDS}
        proc = subprocess.run(
            [sys.executable, "-m", _MODULE],
            input="}{not json at all!!",
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""

    def test_empty_stdin_exits_zero_silently(self, db):
        env = {**os.environ, "PYTHONPATH": _SRC, "RABBITHOLE_DB_PATH": db, **_THRESHOLDS}
        proc = subprocess.run(
            [sys.executable, "-m", _MODULE],
            input="",
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Pattern detection — intelligent nudge classifies the read streak
# ---------------------------------------------------------------------------

class TestPatternDetection:
    """The intelligent nudge classifies the streak into deep_dive / thrashing /
    research_spiral and emits a contextual message + imperative self-rescue
    instruction. Zero tokens — pure heuristics on the streak labels."""

    def test_deep_dive_emits_at_rabbithole(self, db):
        """5 reads sharing a topic stem → deep_dive pattern at rabbithole."""
        session = "deep-dive-rh"
        for f in ("auth.py", "auth_oauth.py", "auth_jwt.py", "auth_session.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        # 5th read → depth=5 == rabbithole → emit with deep_dive pattern
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/auth_test.py"), db)
        assert rc == 0
        parsed = _assert_emit(out, depth=5)
        msg = parsed["systemMessage"]
        assert "deep dive" in msg.lower(), f"Expected 'deep dive' in: {msg!r}"
        # Model channel should have imperative self-rescue
        additional = parsed["hookSpecificOutput"]["additionalContext"]
        assert "STOP" in additional, f"Expected STOP in additionalContext: {additional!r}"
        assert "deep_dive" in additional, f"Expected pattern name in: {additional!r}"

    def test_thrashing_pattern_detected(self, db):
        """5 reads across unrelated files → thrashing pattern."""
        session = "thrashing"
        for f in ("auth.py", "schema.ts", "package.json", "docker-compose.yml"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        # 5th read → depth=5 == rabbithole → emit with thrashing pattern
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/main.go"), db)
        assert rc == 0
        parsed = _assert_emit(out, depth=5)
        msg = parsed["systemMessage"]
        assert "thrashing" in msg.lower(), f"Expected 'thrashing' in: {msg!r}"
        additional = parsed["hookSpecificOutput"]["additionalContext"]
        assert "thrashing" in additional, f"Expected pattern in: {additional!r}"

    def test_research_spiral_pattern_detected(self, db):
        """5 reads of mostly docs → research_spiral pattern."""
        session = "research-spiral"
        for f in ("README.md", "AUTH.md", "rfc6749.txt", "oauth_guide.md"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        # 5th read → depth=5 == rabbithole → emit with research_spiral pattern
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/JWT_SPEC.md"), db)
        assert rc == 0
        parsed = _assert_emit(out, depth=5)
        msg = parsed["systemMessage"]
        assert "research spiral" in msg.lower(), f"Expected 'research spiral' in: {msg!r}"
        additional = parsed["hookSpecificOutput"]["additionalContext"]
        assert "research_spiral" in additional, f"Expected pattern in: {additional!r}"

    def test_model_instruction_is_imperative(self, db):
        """The additionalContext must contain an imperative self-rescue
        instruction — not just a description. This is what makes the agent
        rescue itself."""
        session = "imperative-check"
        for f in ("auth.py", "auth_oauth.py", "auth_jwt.py", "auth_session.py"):
            _hook(_payload("Read", session, file_path=f"/proj/{f}"), db)
        rc, out, _ = _hook(_payload("Read", session, file_path="/proj/auth_test.py"), db)
        assert rc == 0
        parsed = json.loads(out)
        additional = parsed["hookSpecificOutput"]["additionalContext"]
        # Must contain imperative verbs
        assert "STOP" in additional or "Do not" in additional, \
            f"Expected imperative instruction in: {additional!r}"
        # Must mention depth_pop or add_loop or write
        assert any(kw in additional for kw in ("depth_pop", "add_loop", "write")), \
            f"Expected actionable verb in: {additional!r}"


# ---------------------------------------------------------------------------
# Concurrency — busy_timeout prevents lost-increment race
# ---------------------------------------------------------------------------

class TestConcurrency:
    """Fire N concurrent hook_increment calls for one session and assert
    final depth == N. Without PRAGMA busy_timeout, SQLite raises
    OperationalError immediately on lock contention → lost increments.
    With busy_timeout=5000, writers wait → no losses."""

    def test_concurrent_increments_lose_zero_counts(self, tmp_path):
        import sys, pathlib, threading
        _SRC = str(pathlib.Path(__file__).parents[1] / "src")
        if _SRC not in sys.path:
            sys.path.insert(0, _SRC)
        from mcp_server_nucleus.rabbithole import store

        db = str(tmp_path / "concurrent.db")
        conn = store.connect(db)
        session = "concurrent-test"
        n_threads = 20
        n_per_thread = 5  # total = 100 increments

        def worker():
            c = store.connect(db)
            for _ in range(n_per_thread):
                store.hook_increment(c, session, "file.py")
            c.close()

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Read final state
        final = store.hook_state(conn) if hasattr(store, 'hook_state') else None
        # hook_state isn't a function — query directly
        row = conn.execute(
            "SELECT depth FROM hook_state WHERE session_id = ?", (session,)
        ).fetchone()
        conn.close()

        expected = n_threads * n_per_thread
        actual = row[0] if row else 0
        assert actual == expected, \
            f"LOST INCREMENTS: expected {expected}, got {actual} " \
            f"(lost {expected - actual} — busy_timeout not working)"
