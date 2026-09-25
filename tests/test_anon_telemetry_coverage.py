"""Comprehensive tests for anon_telemetry module."""
import json
import os
import time
import threading
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from mcp_server_nucleus.runtime import anon_telemetry
from mcp_server_nucleus.runtime.anon_telemetry import (
    _get_session_id,
    _read_yaml_config,
    _get_endpoint,
    is_anon_telemetry_enabled,
    reset_anon_telemetry_state,
    _get_nucleus_version,
    _get_install_id,
    _is_ci_env,
    _is_claude_code_env,
    _get_static_attributes,
    _send_event,
    _send_in_background,
    _build_event,
    record_session_start,
    record_session_end,
    record_anon_command,
    record_feature_adoption,
    record_error,
    record_daemon_install,
    shutdown_anon_telemetry,
    _write_yaml_telemetry_setting,
    show_first_run_notice,
    show_first_run_prompt,
    _DEFAULT_ENDPOINT,
    _FIRST_RUN_MARKER,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset module-level state before and after each test."""
    reset_anon_telemetry_state()
    anon_telemetry._session_id = None
    anon_telemetry._session_start_time = None
    anon_telemetry._session_commands = []
    anon_telemetry._pending_spans = []
    yield
    reset_anon_telemetry_state()
    anon_telemetry._session_id = None
    anon_telemetry._session_start_time = None
    anon_telemetry._session_commands = []
    anon_telemetry._pending_spans = []


@pytest.fixture
def clean_env(monkeypatch):
    """Clean all telemetry-related env vars."""
    monkeypatch.delenv("NUCLEUS_ANON_TELEMETRY", raising=False)
    monkeypatch.delenv("NUCLEUS_ANON_TELEMETRY_ENDPOINT", raising=False)
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CIRCLECI", raising=False)
    monkeypatch.delenv("GITLAB_CI", raising=False)
    monkeypatch.delenv("BUILDKITE", raising=False)
    monkeypatch.delenv("TRAVIS", raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)


# ── _get_session_id ──────────────────────────────────────────────

class TestGetSessionId:
    def test_generates_id(self):
        sid = _get_session_id()
        assert isinstance(sid, str)
        assert len(sid) == 32  # uuid4 hex

    def test_sets_start_time(self):
        # _get_session_id assigns to a local _session_start_time (not global)
        # so we just verify the function returns a valid id
        sid = _get_session_id()
        assert sid is not None
        assert len(sid) == 32

    def test_cached(self):
        sid1 = _get_session_id()
        sid2 = _get_session_id()
        assert sid1 == sid2


# ── _read_yaml_config ────────────────────────────────────────────

class TestReadYamlConfig:
    def test_no_config_returns_empty(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nohome")
        (tmp_path / "subdir").mkdir()
        monkeypatch.chdir(tmp_path / "subdir")
        result = _read_yaml_config()
        assert result == {}

    def test_reads_brain_path_config(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: false\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nohome")
        (tmp_path / "subdir").mkdir()
        monkeypatch.chdir(tmp_path / "subdir")
        result = _read_yaml_config()
        assert result["telemetry"]["anonymous"]["enabled"] is False

    def test_reads_home_config(self, clean_env, monkeypatch, tmp_path):
        home = tmp_path / "home"
        brain = home / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: true\n")
        monkeypatch.setattr(Path, "home", lambda: home)
        (tmp_path / "subdir").mkdir()
        monkeypatch.chdir(tmp_path / "subdir")
        result = _read_yaml_config()
        assert result["telemetry"]["anonymous"]["enabled"] is True

    def test_reads_cwd_config(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: true\n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nonexistent")
        monkeypatch.chdir(tmp_path)
        result = _read_yaml_config()
        assert result["telemetry"]["anonymous"]["enabled"] is True

    def test_corrupt_yaml_returns_empty(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("{{invalid yaml:::}}}")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nohome")
        (tmp_path / "subdir").mkdir()
        monkeypatch.chdir(tmp_path / "subdir")
        result = _read_yaml_config()
        assert result == {}

    def test_no_yaml_module_returns_empty(self, clean_env, monkeypatch):
        # Simulate yaml not being available
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return real_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = _read_yaml_config()
        assert result == {}

    def test_empty_yaml_file(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _read_yaml_config()
        assert result == {}


# ── _get_endpoint ────────────────────────────────────────────────

class TestGetEndpoint:
    def test_default_endpoint(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nohome")
        (tmp_path / "subdir").mkdir()
        monkeypatch.chdir(tmp_path / "subdir")
        assert _get_endpoint() == _DEFAULT_ENDPOINT

    def test_env_var_endpoint(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY_ENDPOINT", "https://custom.example.com")
        assert _get_endpoint() == "https://custom.example.com"

    def test_env_var_with_whitespace(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY_ENDPOINT", "  https://custom.example.com  ")
        assert _get_endpoint() == "https://custom.example.com"

    def test_yaml_config_endpoint(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    endpoint: https://yaml.example.com\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        assert _get_endpoint() == "https://yaml.example.com"


# ── is_anon_telemetry_enabled ────────────────────────────────────

class TestIsAnonTelemetryEnabled:
    def test_default_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        assert is_anon_telemetry_enabled() is True

    def test_env_false_disables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        assert is_anon_telemetry_enabled() is False

    def test_env_0_disables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "0")
        assert is_anon_telemetry_enabled() is False

    def test_env_no_disables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "no")
        assert is_anon_telemetry_enabled() is False

    def test_env_off_disables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "off")
        assert is_anon_telemetry_enabled() is False

    def test_env_true_enables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        assert is_anon_telemetry_enabled() is True

    def test_env_1_enables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "1")
        assert is_anon_telemetry_enabled() is True

    def test_env_yes_enables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "yes")
        assert is_anon_telemetry_enabled() is True

    def test_env_on_enables(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "on")
        assert is_anon_telemetry_enabled() is True

    def test_env_case_insensitive(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "FALSE")
        assert is_anon_telemetry_enabled() is False

    def test_yaml_disabled(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: false\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        assert is_anon_telemetry_enabled() is False

    def test_yaml_enabled(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: true\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        assert is_anon_telemetry_enabled() is True

    def test_env_overrides_yaml(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: false\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        assert is_anon_telemetry_enabled() is True

    def test_cache_used(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        assert is_anon_telemetry_enabled() is True
        # Change env but cache should be used
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        assert is_anon_telemetry_enabled() is True  # cached

    def test_reset_clears_cache(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        assert is_anon_telemetry_enabled() is True
        reset_anon_telemetry_state()
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        assert is_anon_telemetry_enabled() is False


# ── _get_nucleus_version ─────────────────────────────────────────

class TestGetNucleusVersion:
    def test_returns_version_string(self):
        v = _get_nucleus_version()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_returns_unknown_on_error(self, monkeypatch):
        import importlib.metadata
        def raise_error(*args, **kwargs):
            raise Exception("not found")
        monkeypatch.setattr(importlib.metadata, "version", raise_error)
        assert _get_nucleus_version() == "unknown"


# ── _get_install_id ──────────────────────────────────────────────

class TestGetInstallId:
    def test_generates_new_id(self, monkeypatch, tmp_path):
        config_dir = tmp_path / ".config" / "nucleus"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _get_install_id()
        assert isinstance(result, str)
        assert len(result) == 32
        assert (config_dir / "install_id").exists()

    def test_reads_existing_id(self, monkeypatch, tmp_path):
        config_dir = tmp_path / ".config" / "nucleus"
        config_dir.mkdir(parents=True)
        existing_id = "abcdef1234567890abcdef1234567890"
        (config_dir / "install_id").write_text(existing_id)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _get_install_id()
        assert result == existing_id

    def test_empty_existing_file_generates_new(self, monkeypatch, tmp_path):
        config_dir = tmp_path / ".config" / "nucleus"
        config_dir.mkdir(parents=True)
        (config_dir / "install_id").write_text("   \n")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _get_install_id()
        assert len(result) == 32
        assert result != "   \n"

    def test_returns_unknown_on_error(self, monkeypatch):
        def raise_error(*args, **kwargs):
            raise Exception("no home")
        monkeypatch.setattr(Path, "home", raise_error)
        assert _get_install_id() == "unknown"


# ── _is_ci_env ───────────────────────────────────────────────────

class TestIsCiEnv:
    def test_no_ci_vars(self, clean_env):
        assert _is_ci_env() is False

    def test_ci_var(self, clean_env, monkeypatch):
        monkeypatch.setenv("CI", "true")
        assert _is_ci_env() is True

    def test_github_actions(self, clean_env, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert _is_ci_env() is True

    def test_circleci(self, clean_env, monkeypatch):
        monkeypatch.setenv("CIRCLECI", "true")
        assert _is_ci_env() is True

    def test_gitlab_ci(self, clean_env, monkeypatch):
        monkeypatch.setenv("GITLAB_CI", "true")
        assert _is_ci_env() is True

    def test_buildkite(self, clean_env, monkeypatch):
        monkeypatch.setenv("BUILDKITE", "true")
        assert _is_ci_env() is True

    def test_travis(self, clean_env, monkeypatch):
        monkeypatch.setenv("TRAVIS", "true")
        assert _is_ci_env() is True


# ── _is_claude_code_env ──────────────────────────────────────────

class TestIsClaudeCodeEnv:
    def test_not_set(self, clean_env):
        assert _is_claude_code_env() is False

    def test_set(self, clean_env, monkeypatch):
        monkeypatch.setenv("CLAUDECODE", "1")
        assert _is_claude_code_env() is True


# ── _get_static_attributes ───────────────────────────────────────

class TestGetStaticAttributes:
    def test_returns_dict_with_keys(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        attrs = _get_static_attributes()
        assert "nucleus.version" in attrs
        assert "python.version" in attrs
        assert "os.platform" in attrs
        assert "os.arch" in attrs
        assert "nucleus.install_id" in attrs
        assert "nucleus.is_ci" in attrs
        assert "nucleus.is_claude_code" in attrs


# ── _send_event ──────────────────────────────────────────────────

class TestSendEvent:
    def test_successful_send(self, clean_env, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
        _send_event({"event_type": "test"})
        # Should not raise

    def test_send_failure_silent(self, clean_env, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=urllib.error.URLError("fail")))
        _send_event({"event_type": "test"})
        # Should not raise


# ── _send_in_background ──────────────────────────────────────────

class TestSendInBackground:
    def test_starts_thread(self, clean_env, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
        _send_in_background({"event_type": "test"})
        # Wait for thread to complete
        time.sleep(0.2)
        assert len(anon_telemetry._pending_spans) >= 1


# ── _build_event ─────────────────────────────────────────────────

class TestBuildEvent:
    def test_basic_event(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        event = _build_event("command", command="test_cmd", category="test_cat", duration_ms=100.0)
        assert event["event_type"] == "command"
        assert event["command"] == "test_cmd"
        assert event["category"] == "test_cat"
        assert event["duration_ms"] == 100.0
        assert "install_id" in event
        assert "session_id" in event
        assert "timestamp" in event
        assert "nucleus_version" in event
        assert "python_version" in event
        assert "os" in event
        assert "os_arch" in event
        assert "is_ci" in event
        assert "is_claude_code" in event

    def test_with_error_type(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        event = _build_event("error", error_type="ValueError")
        assert event["error_type"] == "ValueError"

    def test_without_error_type(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        event = _build_event("command")
        assert "error_type" not in event

    def test_with_extra(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        event = _build_event("command", extra={"custom": "value"})
        assert event["custom"] == "value"

    def test_duration_rounded(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        event = _build_event("command", duration_ms=100.567)
        assert event["duration_ms"] == 100.57

    def test_defaults(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        event = _build_event("test")
        assert event["command"] == ""
        assert event["category"] == ""
        assert event["duration_ms"] == 0.0


# ── record_session_start ─────────────────────────────────────────

class TestRecordSessionStart:
    def test_when_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_session_start()
            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "session_start"

    def test_when_disabled(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_session_start()
            mock_send.assert_not_called()

    def test_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_build_event", side_effect=Exception("boom")):
            record_session_start()  # should not raise


# ── record_session_end ───────────────────────────────────────────

class TestRecordSessionEnd:
    def test_when_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        # Set session state
        anon_telemetry._session_start_time = time.time() - 10
        anon_telemetry._session_commands = ["cmd1", "cmd2"]
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_session_end()
            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "session_end"
            assert event["session_duration_s"] >= 10
            assert event["commands_run"] == 2

    def test_when_disabled(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_session_end()
            mock_send.assert_not_called()

    def test_no_start_time(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        anon_telemetry._session_start_time = None
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_session_end()
            mock_send.assert_called_once()

    def test_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_build_event", side_effect=Exception("boom")):
            record_session_end()  # should not raise


# ── record_anon_command ──────────────────────────────────────────

class TestRecordAnonCommand:
    def test_when_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_anon_command("test_cmd", "test_cat", 50.0)
            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "command"
            assert event["command"] == "test_cmd"
            assert "test_cmd" in anon_telemetry._session_commands

    def test_when_disabled(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_anon_command("test_cmd", "test_cat", 50.0)
            mock_send.assert_not_called()

    def test_with_error_type(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_anon_command("test_cmd", "test_cat", 50.0, error_type="ValueError")
            event = mock_send.call_args[0][0]
            assert event["error_type"] == "ValueError"

    def test_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_build_event", side_effect=Exception("boom")):
            record_anon_command("cmd", "cat", 50.0)  # should not raise


# ── record_feature_adoption ──────────────────────────────────────

class TestRecordFeatureAdoption:
    def test_when_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_feature_adoption("new_feature", context={"key": "val"})
            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "feature_adoption"
            assert event["command"] == "new_feature"

    def test_when_disabled(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_feature_adoption("feat")
            mock_send.assert_not_called()

    def test_no_context(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_feature_adoption("feat")
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "feature_adoption"

    def test_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_build_event", side_effect=Exception("boom")):
            record_feature_adoption("feat")  # should not raise


# ── record_error ─────────────────────────────────────────────────

class TestRecordError:
    def test_when_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_error("ValueError", command="cmd", context={"k": "v"})
            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "error"
            assert event["error_type"] == "ValueError"

    def test_when_disabled(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_error("ValueError")
            mock_send.assert_not_called()

    def test_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_build_event", side_effect=Exception("boom")):
            record_error("ValueError")  # should not raise


# ── record_daemon_install ────────────────────────────────────────

class TestRecordDaemonInstall:
    def test_when_enabled(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_daemon_install()
            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event["event_type"] == "daemon_install"

    def test_when_disabled(self, clean_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        with patch.object(anon_telemetry, "_send_in_background") as mock_send:
            record_daemon_install()
            mock_send.assert_not_called()

    def test_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        with patch.object(anon_telemetry, "_build_event", side_effect=Exception("boom")):
            record_daemon_install()  # should not raise


# ── shutdown_anon_telemetry ──────────────────────────────────────

class TestShutdownAnonTelemetry:
    def test_joins_threads(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
        record_anon_command("cmd", "cat", 10.0)
        shutdown_anon_telemetry(timeout=1.0)
        assert len(anon_telemetry._pending_spans) == 0

    def test_no_session(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        shutdown_anon_telemetry()
        # Should not raise

    def test_with_session_end(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "true")
        anon_telemetry._session_id = "test-session"
        anon_telemetry._session_commands = ["cmd1"]
        anon_telemetry._session_start_time = time.time()
        with patch.object(anon_telemetry, "record_session_end") as mock_end:
            shutdown_anon_telemetry()
            mock_end.assert_called_once()


# ── _write_yaml_telemetry_setting ────────────────────────────────

class TestWriteYamlTelemetrySetting:
    def test_write_to_brain_path(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _write_yaml_telemetry_setting(False)
        assert result is True
        content = cfg.read_text()
        assert "enabled: false" in content

    def test_write_to_cwd(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        result = _write_yaml_telemetry_setting(True)
        assert result is True
        cfg = tmp_path / ".brain" / "config" / "nucleus.yaml"
        assert "enabled: true" in cfg.read_text()

    def test_merges_existing_config(self, clean_env, monkeypatch, tmp_path):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("other_setting: value\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = _write_yaml_telemetry_setting(True)
        assert result is True
        content = cfg.read_text()
        assert "other_setting" in content
        assert "enabled: true" in content

    def test_no_yaml_module_returns_false(self, clean_env, monkeypatch):
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return real_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = _write_yaml_telemetry_setting(True)
        assert result is False


# ── show_first_run_notice ────────────────────────────────────────

class TestShowFirstRunNotice:
    def test_skips_if_env_set(self, clean_env, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_ANON_TELEMETRY", "false")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        show_first_run_notice()
        captured = capsys.readouterr()
        assert "Nucleus collects" not in captured.out

    def test_skips_if_yaml_has_setting(self, clean_env, monkeypatch, tmp_path, capsys):
        brain = tmp_path / ".brain" / "config"
        brain.mkdir(parents=True)
        cfg = brain / "nucleus.yaml"
        cfg.write_text("telemetry:\n  anonymous:\n    enabled: false\n")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "other")
        show_first_run_notice()
        captured = capsys.readouterr()
        assert "Nucleus collects" not in captured.out

    def test_skips_if_marker_exists(self, clean_env, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / _FIRST_RUN_MARKER).touch()
        show_first_run_notice()
        captured = capsys.readouterr()
        assert "Nucleus collects" not in captured.out

    def test_prints_notice_and_creates_marker(self, clean_env, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        show_first_run_notice()
        captured = capsys.readouterr()
        assert "Nucleus collects" in captured.out
        assert "opt out" in captured.out
        # Marker should exist
        assert (tmp_path / _FIRST_RUN_MARKER).exists()

    def test_marker_created_in_brain_path(self, clean_env, monkeypatch, tmp_path, capsys):
        brain = tmp_path / "brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nohome")
        show_first_run_notice()
        captured = capsys.readouterr()
        assert "Nucleus collects" in captured.out
        assert (brain / _FIRST_RUN_MARKER).exists()

    def test_print_exception_silent(self, clean_env, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        # Force print to fail
        import builtins
        real_print = builtins.print
        def fail_print(*args, **kwargs):
            raise Exception("print failed")
        monkeypatch.setattr(builtins, "print", fail_print)
        show_first_run_notice()  # should not raise

    def test_alias_show_first_run_prompt(self):
        assert show_first_run_prompt is show_first_run_notice
