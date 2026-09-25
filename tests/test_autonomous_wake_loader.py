"""Tests for v0.3.0 — sessions.autonomous_wake_loader.

Per cc-peer 2026-06-09T11:55Z SIGNOFF Q1 test floor:
- test_loader_clears_existing_registry_then_loads
- test_loader_skips_malformed_entries_with_warning
- test_loader_handles_missing_file_silently
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from mcp_server_nucleus.sessions import autonomous_wake_loader as wl
from mcp_server_nucleus.sessions import autonomous_wake_map as wm


@pytest.fixture(autouse=True)
def _clean_registry():
    wm.clear_registry()
    yield
    wm.clear_registry()


def _valid_entry(role="cc_tb"):
    return {
        "role": role,
        "session_id": "cse_abc123def456",
        "org_uuid": "903554b9-org",
    }


def test_loader_handles_missing_file_silently(tmp_path, caplog):
    """No config file → returns 0 + default-off MAP."""
    caplog.set_level(logging.INFO, logger="nucleus.autonomous_wake_loader")
    n = wl.load_autonomous_wake_map(tmp_path / "absent.json")
    assert n == 0
    assert wm.list_autonomous_roles() == []


def test_loader_loads_valid_entries(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps([
        _valid_entry("cc_tb"),
        _valid_entry("cc_peer"),
    ]))
    n = wl.load_autonomous_wake_map(cfg)
    assert n == 2
    assert set(wm.list_autonomous_roles()) == {"cc_tb", "cc_peer"}


def test_loader_clears_existing_registry_then_loads(tmp_path):
    """clear_first=True (default) wipes pre-existing entries."""
    wm.register_autonomous_role(
        "stale_role", wm.AutonomousWakeConfig(
            role="stale_role", session_id="cse_old", org_uuid="o",
        ),
    )
    assert "stale_role" in wm.list_autonomous_roles()

    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps([_valid_entry("cc_tb")]))
    wl.load_autonomous_wake_map(cfg)
    assert "stale_role" not in wm.list_autonomous_roles()
    assert "cc_tb" in wm.list_autonomous_roles()


def test_loader_clear_first_false_merges_additively(tmp_path):
    wm.register_autonomous_role(
        "existing", wm.AutonomousWakeConfig(
            role="existing", session_id="cse_old", org_uuid="o",
        ),
    )
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps([_valid_entry("cc_tb")]))
    wl.load_autonomous_wake_map(cfg, clear_first=False)
    roles = set(wm.list_autonomous_roles())
    assert roles == {"existing", "cc_tb"}


def test_loader_skips_malformed_entries_with_warning(tmp_path, caplog):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps([
        _valid_entry("cc_tb"),
        {"role": "missing_other_keys"},  # missing session_id, org_uuid
        "not-a-dict",
        _valid_entry("cc_peer"),
        {"role": "", "session_id": "cse_x", "org_uuid": "o"},  # empty role
    ]))
    caplog.set_level(logging.WARNING, logger="nucleus.autonomous_wake_loader")
    n = wl.load_autonomous_wake_map(cfg)
    assert n == 2
    assert set(wm.list_autonomous_roles()) == {"cc_tb", "cc_peer"}


def test_loader_handles_invalid_json(tmp_path, caplog):
    cfg = tmp_path / "cfg.json"
    cfg.write_text("not-json{{")
    caplog.set_level(logging.WARNING, logger="nucleus.autonomous_wake_loader")
    n = wl.load_autonomous_wake_map(cfg)
    assert n == 0
    assert any("JSON parse" in r.getMessage() for r in caplog.records)


def test_loader_handles_non_array_json(tmp_path, caplog):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"not": "an array"}))
    caplog.set_level(logging.WARNING, logger="nucleus.autonomous_wake_loader")
    n = wl.load_autonomous_wake_map(cfg)
    assert n == 0


def test_loader_optional_fields_threaded():
    cfg_path = Path("/tmp/_test_loader_cfg.json")
    cfg_path.write_text(json.dumps([{
        "role": "cc_tb",
        "session_id": "cse_x",
        "org_uuid": "o",
        "model": "claude-opus-4-7",
        "max_tokens": 8192,
        "history_limit": 25,
        "prearm": False,
    }]))
    try:
        wl.load_autonomous_wake_map(cfg_path)
        cfg = wm.get_autonomous_config("cc_tb")
        assert cfg is not None
        assert cfg.model == "claude-opus-4-7"
        assert cfg.max_tokens == 8192
        assert cfg.history_limit == 25
        assert cfg.prearm is False
    finally:
        cfg_path.unlink(missing_ok=True)


def test_all_exported():
    assert set(wl.__all__) == {"load_autonomous_wake_map"}


def test_loader_threads_account_uuid_from_config_file(tmp_path):
    """Task #63 wiring: account_uuid in config file -> AutonomousWakeConfig.account_uuid."""
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps([{
        "role": "bespoq_cowork",
        "session_id": "cse_x",
        "org_uuid": "org-1",
        "account_uuid": "acct-bespoq",
    }]))
    n = wl.load_autonomous_wake_map(cfg)
    assert n == 1
    cfg_loaded = wm.get_autonomous_config("bespoq_cowork")
    assert cfg_loaded is not None
    assert cfg_loaded.account_uuid == "acct-bespoq"


def test_loader_account_uuid_absent_stays_none(tmp_path):
    """Backward compat: pre-Task-63 config entries (no account_uuid) work."""
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps([{
        "role": "cc_tb",
        "session_id": "cse_x",
        "org_uuid": "org-1",
    }]))
    wl.load_autonomous_wake_map(cfg)
    cfg_loaded = wm.get_autonomous_config("cc_tb")
    assert cfg_loaded.account_uuid is None
