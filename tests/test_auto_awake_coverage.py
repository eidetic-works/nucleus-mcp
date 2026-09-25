"""Comprehensive tests for runtime/auto_awake.py."""
import json
import sys
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.auto_awake import (
    _resolve_brain_path,
    _dedup_path,
    _subject_prefixes,
    _provider_env_key,
    _command_for_provider,
    _bucket_whitelist,
    _env_float,
    _load_provider_bucket_map,
    _read_dedup,
    _write_dedup,
    _matches_prefix,
    _scan_bucket,
    _dispatch,
    _resolve_bucket_targets,
    _now_iso,
    _poll_once,
    _install_signal_handlers,
    _Stop,
    run,
    _cli,
    _DEFAULT_POLL_SECS,
    _DEFAULT_SUBJECT_PREFIXES,
)


# ── Path resolution ──────────────────────────────────────────────

class TestResolveBrainPath:
    def test_explicit_path(self, tmp_path):
        result = _resolve_brain_path(tmp_path)
        assert result == tmp_path.resolve()

    def test_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _resolve_brain_path()
        assert result == tmp_path.resolve()

    def test_no_brain_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        # Mock __file__ to point to a location with no .brain ancestor
        fake_file = tmp_path / "fake_module.py"
        fake_file.write_text("# fake")
        with patch("mcp_server_nucleus.runtime.auto_awake.__file__", str(fake_file)):
            with pytest.raises(RuntimeError, match="not set and no .brain"):
                _resolve_brain_path()

    def test_explicit_takes_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/some/other/path")
        result = _resolve_brain_path(tmp_path)
        assert result == tmp_path.resolve()


# ── Dedup path ───────────────────────────────────────────────────

class TestDedupPath:
    def test_default_path(self, tmp_path):
        result = _dedup_path(tmp_path)
        assert result == tmp_path / "state" / "auto_awake_dispatched.json"

    def test_env_override(self, tmp_path, monkeypatch):
        custom = tmp_path / "custom" / "dedup.json"
        monkeypatch.setenv("NUCLEUS_AWAKE_DEDUP_PATH", str(custom))
        result = _dedup_path(tmp_path)
        assert result == custom.resolve()


# ── Subject prefixes ─────────────────────────────────────────────

class TestSubjectPrefixes:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_AWAKE_SUBJECT_PREFIXES", raising=False)
        result = _subject_prefixes()
        assert result == _DEFAULT_SUBJECT_PREFIXES

    def test_custom(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_SUBJECT_PREFIXES", "[DIRECTIVE],[CUSTOM]")
        result = _subject_prefixes()
        assert "[DIRECTIVE]" in result
        assert "[CUSTOM]" in result

    def test_empty_env(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_SUBJECT_PREFIXES", "")
        result = _subject_prefixes()
        assert result == _DEFAULT_SUBJECT_PREFIXES

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_SUBJECT_PREFIXES", " [A] , [B] ")
        result = _subject_prefixes()
        assert result == ("[A]", "[B]")


# ── Provider env key ─────────────────────────────────────────────

class TestProviderEnvKey:
    def test_simple(self):
        assert _provider_env_key("anthropic") == "NUCLEUS_AWAKE_CMD_ANTHROPIC"

    def test_with_spaces(self):
        assert _provider_env_key("claude code") == "NUCLEUS_AWAKE_CMD_CLAUDE_CODE"

    def test_with_special_chars(self):
        assert _provider_env_key("provider-1.0") == "NUCLEUS_AWAKE_CMD_PROVIDER_1_0"


# ── Command for provider ─────────────────────────────────────────

class TestCommandForProvider:
    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_AWAKE_CMD_TEST", raising=False)
        assert _command_for_provider("test") is None

    def test_with_env(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_CMD_TEST", "claude -p --verbose")
        result = _command_for_provider("test")
        assert result == ["claude", "-p", "--verbose"]

    def test_empty_env(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_CMD_TEST", "")
        assert _command_for_provider("test") is None


# ── Bucket whitelist ─────────────────────────────────────────────

class TestBucketWhitelist:
    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_AWAKE_BUCKETS", raising=False)
        assert _bucket_whitelist() is None

    def test_with_env(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_BUCKETS", "bucket1,bucket2")
        result = _bucket_whitelist()
        assert result == ("bucket1", "bucket2")

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_BUCKETS", " a , b , c ")
        result = _bucket_whitelist()
        assert result == ("a", "b", "c")

    def test_empty_env(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_AWAKE_BUCKETS", "")
        assert _bucket_whitelist() is None


# ── Env float ────────────────────────────────────────────────────

class TestEnvFloat:
    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT", raising=False)
        assert _env_float("TEST_FLOAT", 42.0) == 42.0

    def test_valid_float(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "3.14")
        assert _env_float("TEST_FLOAT", 42.0) == 3.14

    def test_invalid_float(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "not_a_number")
        assert _env_float("TEST_FLOAT", 42.0) == 42.0

    def test_empty_env(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "")
        assert _env_float("TEST_FLOAT", 42.0) == 42.0


# ── Provider bucket map ──────────────────────────────────────────

class TestLoadProviderBucketMap:
    def test_loads_from_registry(self, monkeypatch):
        mock_providers = [
            {"prefix": "claude_code_peer", "provider": "anthropic_claude_code", "default_role": "worker"},
            {"prefix": "gemini_peer", "provider": "google_gemini", "default_role": "worker"},
        ]
        with patch("mcp_server_nucleus.runtime.providers.list_providers", return_value=mock_providers):
            result = _load_provider_bucket_map()
        assert result["claude_code_peer"] == "anthropic_claude_code"
        assert result["gemini_peer"] == "google_gemini"

    def test_first_entry_wins(self, monkeypatch):
        mock_providers = [
            {"prefix": "same_prefix", "provider": "first", "default_role": "w"},
            {"prefix": "same_prefix", "provider": "second", "default_role": "w"},
        ]
        with patch("mcp_server_nucleus.runtime.providers.list_providers", return_value=mock_providers):
            result = _load_provider_bucket_map()
        assert result["same_prefix"] == "first"


# ── Dedup read/write ─────────────────────────────────────────────

class TestDedupReadWrite:
    def test_read_no_file(self, tmp_path):
        path = tmp_path / "dedup.json"
        assert _read_dedup(path) == {}

    def test_write_and_read(self, tmp_path):
        path = tmp_path / "dedup.json"
        state = {"id1": {"bucket": "b1", "dispatched_at": "2026-01-01T00:00:00Z"}}
        _write_dedup(path, state)
        loaded = _read_dedup(path)
        assert loaded == state

    def test_read_corrupt(self, tmp_path):
        path = tmp_path / "dedup.json"
        path.write_text("not valid json{{{")
        assert _read_dedup(path) == {}

    def test_read_non_dict(self, tmp_path):
        path = tmp_path / "dedup.json"
        path.write_text("[1, 2, 3]")
        assert _read_dedup(path) == {}

    def test_write_creates_parent(self, tmp_path):
        path = tmp_path / "subdir" / "dedup.json"
        _write_dedup(path, {})
        assert path.exists()


# ── Matches prefix ───────────────────────────────────────────────

class TestMatchesPrefix:
    def test_matches(self):
        assert _matches_prefix("[DIRECTIVE] hello", ("[DIRECTIVE]",)) is True

    def test_no_match(self):
        assert _matches_prefix("hello", ("[DIRECTIVE]",)) is False

    def test_empty_subject(self):
        assert _matches_prefix("", ("[DIRECTIVE]",)) is False

    def test_none_subject(self):
        assert _matches_prefix(None, ("[DIRECTIVE]",)) is False

    def test_multiple_prefixes(self):
        assert _matches_prefix("[DIRECTIVE-ON-WAKE] test", ("[DIRECTIVE]", "[DIRECTIVE-ON-WAKE]")) is True


# ── Scan bucket ──────────────────────────────────────────────────

class TestScanBucket:
    def test_no_dir(self, tmp_path):
        result = _scan_bucket(tmp_path / "nonexistent", ("[DIRECTIVE]",), {})
        assert result == []

    def test_empty_dir(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert result == []

    def test_finds_matching(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        envelope = {"id": "relay1", "subject": "[DIRECTIVE] do something"}
        (bucket / "relay1.json").write_text(json.dumps(envelope))
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert len(result) == 1
        assert result[0][1]["id"] == "relay1"

    def test_skips_dispatched(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        envelope = {"id": "relay1", "subject": "[DIRECTIVE] do something"}
        (bucket / "relay1.json").write_text(json.dumps(envelope))
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {"relay1": {}})
        assert result == []

    def test_skips_non_matching_prefix(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        envelope = {"id": "relay1", "subject": "not a directive"}
        (bucket / "relay1.json").write_text(json.dumps(envelope))
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert result == []

    def test_skips_corrupt_json(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        (bucket / "corrupt.json").write_text("not valid json{{{")
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert result == []

    def test_skips_non_dict(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        (bucket / "list.json").write_text("[1, 2, 3]")
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert result == []

    def test_uses_path_stem_as_id_fallback(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        envelope = {"subject": "[DIRECTIVE] test"}  # no "id" field
        (bucket / "fallback_id.json").write_text(json.dumps(envelope))
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert len(result) == 1
        # The relay_id should be the path stem
        assert result[0][0].stem == "fallback_id"

    def test_sorted_order(self, tmp_path):
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        for name in ["c.json", "a.json", "b.json"]:
            (bucket / name).write_text(json.dumps({"id": name, "subject": "[DIRECTIVE] test"}))
        result = _scan_bucket(bucket, ("[DIRECTIVE]",), {})
        assert [r[0].name for r in result] == ["a.json", "b.json", "c.json"]


# ── Dispatch ─────────────────────────────────────────────────────

class TestDispatch:
    def test_dispatch_returns_proc(self):
        proc = _dispatch([sys.executable, "-c", "import sys; sys.exit(0)"], {"test": "data"})
        assert isinstance(proc, subprocess.Popen)
        proc.wait()

    def test_dispatch_pipes_stdin(self):
        # _dispatch closes stdin immediately, so we verify the process runs
        # and exits successfully by using a command that reads stdin quickly
        proc = _dispatch(
            [sys.executable, "-c", "import sys; data = sys.stdin.read(); sys.exit(0)"],
            {"test": "value"},
        )
        proc.wait(timeout=5)
        assert proc.returncode == 0

    def test_dispatch_broken_pipe(self):
        # This command exits immediately, potentially causing BrokenPipeError
        proc = _dispatch([sys.executable, "-c", "import sys; sys.exit(0)"], {"x": "y"})
        # Should not raise even if pipe is broken
        proc.wait()


# ── Resolve bucket targets ───────────────────────────────────────

class TestResolveBucketTargets:
    def test_no_whitelist(self, tmp_path):
        provider_map = {"b1": "p1", "b2": "p2"}
        targets = _resolve_bucket_targets(tmp_path, provider_map, None)
        assert len(targets) == 2
        assert targets[0][0] == "b1"
        assert targets[0][2] == tmp_path / "relay" / "b1"

    def test_with_whitelist(self, tmp_path):
        provider_map = {"b1": "p1", "b2": "p2", "b3": "p3"}
        targets = _resolve_bucket_targets(tmp_path, provider_map, ("b1", "b3"))
        assert len(targets) == 2
        bucket_names = [t[0] for t in targets]
        assert "b2" not in bucket_names


# ── Now ISO ──────────────────────────────────────────────────────

class TestNowIso:
    def test_format(self):
        result = _now_iso()
        assert result.endswith("Z")
        assert "T" in result


# ── Poll once ────────────────────────────────────────────────────

class TestPollOnce:
    def test_no_targets(self, tmp_path):
        dedup = tmp_path / "dedup.json"
        result = _poll_once(tmp_path, [], ("[DIRECTIVE]",), dedup)
        assert result == 0

    def test_no_pending(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        bucket_dir = brain / "relay" / "b1"
        bucket_dir.mkdir(parents=True)
        dedup = tmp_path / "dedup.json"
        targets = [("b1", "p1", bucket_dir)]
        result = _poll_once(brain, targets, ("[DIRECTIVE]",), dedup)
        assert result == 0

    def test_dispatches_envelope(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        bucket_dir = brain / "relay" / "b1"
        bucket_dir.mkdir(parents=True)
        envelope = {"id": "r1", "subject": "[DIRECTIVE] test"}
        (bucket_dir / "r1.json").write_text(json.dumps(envelope))
        monkeypatch.setenv("NUCLEUS_AWAKE_CMD_P1", f"{sys.executable} -c 'import sys; sys.exit(0)'")
        dedup = tmp_path / "dedup.json"
        targets = [("b1", "p1", bucket_dir)]
        result = _poll_once(brain, targets, ("[DIRECTIVE]",), dedup)
        assert result == 1
        # Verify dedup state
        state = _read_dedup(dedup)
        assert "r1" in state
        assert "pid" in state["r1"]

    def test_no_cli_configured(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        bucket_dir = brain / "relay" / "b1"
        bucket_dir.mkdir(parents=True)
        envelope = {"id": "r1", "subject": "[DIRECTIVE] test"}
        (bucket_dir / "r1.json").write_text(json.dumps(envelope))
        monkeypatch.delenv("NUCLEUS_AWAKE_CMD_P1", raising=False)
        dedup = tmp_path / "dedup.json"
        targets = [("b1", "p1", bucket_dir)]
        result = _poll_once(brain, targets, ("[DIRECTIVE]",), dedup)
        assert result == 0
        state = _read_dedup(dedup)
        assert state["r1"]["skipped"] == "no-cli-configured"


# ── Signal handlers ──────────────────────────────────────────────

class TestInstallSignalHandlers:
    def test_does_not_raise(self):
        import signal
        # _install_signal_handlers() sets SIGCHLD=SIG_IGN so the daemon's
        # fire-and-forget children are auto-reaped by the kernel. Left installed
        # in the pytest process it corrupts subprocess.run() returncodes in every
        # later test (waitpid -> ECHILD -> Python assumes returncode 0). Save the
        # handlers this call replaces and restore them so it cannot leak.
        saved = {}
        for _name in ("SIGINT", "SIGTERM", "SIGCHLD"):
            _sig = getattr(signal, _name, None)
            if _sig is not None:
                saved[_sig] = signal.getsignal(_sig)
        try:
            _install_signal_handlers()
        finally:
            for _sig, _handler in saved.items():
                try:
                    signal.signal(_sig, _handler)
                except (ValueError, OSError):
                    pass


# ── Run ──────────────────────────────────────────────────────────

class TestRun:
    def test_run_max_iters_zero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        mock_providers = []
        with patch("mcp_server_nucleus.runtime.auto_awake._load_provider_bucket_map", return_value={}):
            with patch("mcp_server_nucleus.runtime.auto_awake._install_signal_handlers"):
                result = run(brain=tmp_path, max_iters=0)
        assert result == 0

    def test_run_single_iter(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch("mcp_server_nucleus.runtime.auto_awake._load_provider_bucket_map", return_value={}):
            with patch("mcp_server_nucleus.runtime.auto_awake._install_signal_handlers"):
                result = run(brain=brain, max_iters=1, poll_secs=0)
        assert result == 0

    def test_run_with_dispatch(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        bucket_dir = brain / "relay" / "b1"
        bucket_dir.mkdir(parents=True)
        envelope = {"id": "r1", "subject": "[DIRECTIVE] test"}
        (bucket_dir / "r1.json").write_text(json.dumps(envelope))
        monkeypatch.setenv("NUCLEUS_AWAKE_CMD_P1", f"{sys.executable} -c 'import sys; sys.exit(0)'")
        with patch("mcp_server_nucleus.runtime.auto_awake._load_provider_bucket_map", return_value={"b1": "p1"}):
            with patch("mcp_server_nucleus.runtime.auto_awake._install_signal_handlers"):
                result = run(brain=brain, max_iters=1, poll_secs=0)
        assert result == 1


# ── CLI ──────────────────────────────────────────────────────────

class TestCli:
    def test_cli_once(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.auto_awake._load_provider_bucket_map", return_value={}):
            with patch("mcp_server_nucleus.runtime.auto_awake._install_signal_handlers"):
                result = _cli(["--brain", str(tmp_path), "--once"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dispatched=0" in captured.out

    def test_cli_with_poll_secs(self, tmp_path, monkeypatch, capsys):
        with patch("mcp_server_nucleus.runtime.auto_awake._load_provider_bucket_map", return_value={}):
            with patch("mcp_server_nucleus.runtime.auto_awake._install_signal_handlers"):
                result = _cli(["--brain", str(tmp_path), "--once", "--poll-secs", "5"])
        assert result == 0
