"""Coverage tests for mcp_server_nucleus/rabbithole/hook.py — the PostToolUse
auto-depth-detection hook (classification, pattern detection, output building,
and the main entry point)."""
import io
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.rabbithole import hook
from mcp_server_nucleus.rabbithole import store


# ── _env_int ────────────────────────────────────────────────────────

class TestEnvInt:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("X", raising=False)
        assert hook._env_int("X", 10) == 10

    def test_valid(self, monkeypatch):
        monkeypatch.setenv("X", "42")
        assert hook._env_int("X", 10) == 42

    def test_invalid(self, monkeypatch):
        monkeypatch.setenv("X", "abc")
        assert hook._env_int("X", 10) == 10


# ── _classify ───────────────────────────────────────────────────────

class TestClassify:
    def test_read(self):
        assert hook._classify("Read", {}) == "read"
        assert hook._classify("Grep", {}) == "read"

    def test_write(self):
        assert hook._classify("Edit", {}) == "write"
        assert hook._classify("Write", {}) == "write"
        assert hook._classify("NotebookEdit", {}) == "write"

    def test_neutral(self):
        assert hook._classify("WebFetch", {}) == "neutral"
        assert hook._classify("Unknown", {}) == "neutral"

    def test_bash_read(self):
        assert hook._classify("Bash", {"command": "cat file.py"}) == "read"
        assert hook._classify("Bash", {"command": "grep TODO ."}) == "read"
        assert hook._classify("Bash", {"command": "/bin/ls -la"}) == "read"

    def test_bash_write(self):
        assert hook._classify("Bash", {"command": "rm file.py"}) == "write"
        assert hook._classify("Bash", {"command": "cat file.py > out.txt"}) == "write"
        assert hook._classify("Bash", {"command": "pip install foo"}) == "write"

    def test_bash_empty(self):
        assert hook._classify("Bash", {"command": ""}) == "neutral"
        assert hook._classify("Bash", {}) == "neutral"


# ── _classify_bash ──────────────────────────────────────────────────

class TestClassifyBash:
    def test_empty(self):
        assert hook._classify_bash("") == "neutral"
        assert hook._classify_bash("   ") == "neutral"

    def test_read_word(self):
        assert hook._classify_bash("head -20 file.py") == "read"
        assert hook._classify_bash("wc -l file.py") == "read"
        assert hook._classify_bash("diff a b") == "read"

    def test_write_default(self):
        assert hook._classify_bash("python script.py") == "write"

    def test_read_with_redirect_is_write(self):
        assert hook._classify_bash("cat file.py > out") == "write"


# ── _extract_target ─────────────────────────────────────────────────

class TestExtractTarget:
    def test_read(self):
        assert hook._extract_target("Read", {"file_path": "/a/b/c.py"}) == "c.py"

    def test_read_no_path(self):
        assert hook._extract_target("Read", {}) == "?"

    def test_grep_with_pattern(self):
        t = hook._extract_target("Grep", {"pattern": "TODO", "path": "/x/y"})
        assert t == "grep:TODO"

    def test_grep_no_pattern(self):
        assert hook._extract_target("Grep", {"path": "/x/y"}) == "y"

    def test_grep_empty(self):
        assert hook._extract_target("Grep", {}) == "?"

    def test_bash(self):
        assert hook._extract_target("Bash", {"command": "cat file.py"}) == "cat file.py"

    def test_other(self):
        assert hook._extract_target("WebFetch", {}) == "WebFetch"


# ── _should_emit ────────────────────────────────────────────────────

class TestShouldEmit:
    def test_at_danger(self):
        assert hook._should_emit(10, 10, 15) is True

    def test_at_rabbithole(self):
        assert hook._should_emit(15, 10, 15) is True

    def test_periodic_above_rabbithole(self):
        assert hook._should_emit(20, 10, 15) is True  # (20-15)%5==0
        assert hook._should_emit(25, 10, 15) is True

    def test_not_at_threshold(self):
        assert hook._should_emit(5, 10, 15) is False
        assert hook._should_emit(11, 10, 15) is False
        assert hook._should_emit(17, 10, 15) is False  # (17-15)%5 != 0


# ── _topic_stem ─────────────────────────────────────────────────────

class TestTopicStem:
    def test_strips_extension(self):
        assert hook._topic_stem("auth.py") == "auth"

    def test_strips_grep_prefix(self):
        assert hook._topic_stem("grep:TODO") == "todo"

    def test_strips_path_prefix(self):
        # _topic_stem takes the first whitespace-delimited token
        assert hook._topic_stem("cat config.yml") == "cat"

    def test_strips_underscore_segment(self):
        assert hook._topic_stem("auth_oauth.py") == "auth"

    def test_strips_hyphen_segment(self):
        assert hook._topic_stem("docker-compose.yml") == "docker"

    def test_empty(self):
        assert hook._topic_stem("") == ""

    def test_no_extension(self):
        assert hook._topic_stem("Makefile") == "makefile"


# ── _classify_pattern ───────────────────────────────────────────────

class TestClassifyPattern:
    def test_short_streak(self):
        assert hook._classify_pattern(["a.py"]) == "unknown"
        assert hook._classify_pattern([]) == "unknown"

    def test_deep_dive(self):
        # ≤2 unique stems
        streak = ["auth.py", "auth_test.py", "auth_helper.py"]
        assert hook._classify_pattern(streak) == "deep_dive"

    def test_thrashing(self):
        # ≥4 unique stems
        streak = ["auth.py", "db.py", "api.py", "config.py"]
        assert hook._classify_pattern(streak) == "thrashing"

    def test_research_spiral(self):
        # >60% docs
        streak = ["readme.md", "guide.md", "spec.rst", "auth.py"]
        assert hook._classify_pattern(streak) == "research_spiral"

    def test_unknown_fallback(self):
        # 3 unique stems, not docs
        streak = ["auth.py", "db.py", "api.py"]
        assert hook._classify_pattern(streak) == "unknown"


# ── _build_output ───────────────────────────────────────────────────

class TestBuildOutput:
    def test_danger_level(self):
        out = hook._build_output(12, ["a.py", "b.py"], 10, 15)
        assert out["systemMessage"]
        assert "DANGER" in out["systemMessage"]
        assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" in out["hookSpecificOutput"]

    def test_rabbithole_level(self):
        out = hook._build_output(15, ["a.py", "b.py"], 10, 15)
        assert "RABBIT HOLE" in out["systemMessage"]

    def test_deep_dive_pattern(self):
        streak = ["auth.py", "auth_test.py", "auth_helper.py"]
        out = hook._build_output(10, streak, 10, 15)
        assert "deep dive" in out["systemMessage"]
        assert "STOP reading" in out["hookSpecificOutput"]["additionalContext"]

    def test_thrashing_pattern(self):
        streak = ["auth.py", "db.py", "api.py", "config.py"]
        out = hook._build_output(10, streak, 10, 15)
        assert "thrashing" in out["systemMessage"]
        assert "thrashing" in out["hookSpecificOutput"]["additionalContext"]

    def test_research_spiral_pattern(self):
        streak = ["readme.md", "guide.md", "spec.rst", "auth.py"]
        out = hook._build_output(10, streak, 10, 15)
        assert "research spiral" in out["systemMessage"]
        assert "docs" in out["hookSpecificOutput"]["additionalContext"]

    def test_unknown_pattern(self):
        streak = ["auth.py", "db.py", "api.py"]
        out = hook._build_output(10, streak, 10, 15)
        assert "original task" in out["systemMessage"]
        assert "depth_show" in out["hookSpecificOutput"]["additionalContext"]


# ── main ────────────────────────────────────────────────────────────

class TestMain:
    def test_disabled_exits_zero(self, monkeypatch):
        monkeypatch.setenv("RABBITHOLE_HOOK_DISABLED", "1")
        with pytest.raises(SystemExit) as ei:
            hook.main()
        assert ei.value.code == 0

    def test_neutral_tool_exits_zero(self, monkeypatch):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        payload = json.dumps({"tool_name": "WebFetch", "tool_input": {}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        with pytest.raises(SystemExit) as ei:
            hook.main()
        assert ei.value.code == 0

    def test_write_resets(self, monkeypatch, tmp_path):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        monkeypatch.setenv("RABBITHOLE_DB_PATH", str(tmp_path / "hook.db"))
        payload = json.dumps({"session_id": "s1", "tool_name": "Edit", "tool_input": {}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        # Should not raise / should exit 0 implicitly (no sys.exit for write)
        hook.main()

    def test_read_emits_at_threshold(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        monkeypatch.setenv("RABBITHOLE_DB_PATH", str(tmp_path / "hook.db"))
        monkeypatch.setenv("RABBITHOLE_DEPTH_DANGER", "2")
        monkeypatch.setenv("RABBITHOLE_DEPTH_RABBITHOLE", "5")
        # First read — depth 1, no emit
        p1 = json.dumps({"session_id": "s1", "tool_name": "Read", "tool_input": {"file_path": "/a/b.py"}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(p1))
        hook.main()
        capsys.readouterr()
        # Second read — depth 2 == danger, should emit
        p2 = json.dumps({"session_id": "s1", "tool_name": "Read", "tool_input": {"file_path": "/a/c.py"}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(p2))
        hook.main()
        out = capsys.readouterr().out.strip()
        assert out  # something was emitted
        data = json.loads(out)
        assert "systemMessage" in data

    def test_read_no_emit_below_threshold(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        monkeypatch.setenv("RABBITHOLE_DB_PATH", str(tmp_path / "hook2.db"))
        monkeypatch.setenv("RABBITHOLE_DEPTH_DANGER", "10")
        monkeypatch.setenv("RABBITHOLE_DEPTH_RABBITHOLE", "15")
        payload = json.dumps({"session_id": "s2", "tool_name": "Read", "tool_input": {"file_path": "/a/b.py"}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        hook.main()
        out = capsys.readouterr().out
        assert out == ""

    def test_invalid_json_swallows(self, monkeypatch):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
        # Should not raise
        hook.main()

    def test_exception_swallows(self, monkeypatch):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        monkeypatch.setattr(sys, "stdin", MagicMock(read=MagicMock(side_effect=Exception("boom"))))
        hook.main()

    def test_bash_read_increments(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
        monkeypatch.setenv("RABBITHOLE_DB_PATH", str(tmp_path / "hook3.db"))
        monkeypatch.setenv("RABBITHOLE_DEPTH_DANGER", "1")
        monkeypatch.setenv("RABBITHOLE_DEPTH_RABBITHOLE", "5")
        payload = json.dumps({"session_id": "s3", "tool_name": "Bash", "tool_input": {"command": "cat file.py"}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        hook.main()
        out = capsys.readouterr().out.strip()
        assert out  # depth 1 == danger(1), should emit
