"""Tests for mcp_server_nucleus.diagnostics — portability contract.

The diagnostic modules make live calls (LLM, SQLite, MCP server). These tests
cover only the invariants that matter for the primitive gate:

- Each module imports clean with no NUCLEUS_* env set (no import-time side
  effects that require configuration).
- The env-driven path helpers (``_demo_root``, ``_hud_root``, ``_db_path``,
  ``_receipt_path``) honor their env overrides and fall back correctly.
- ``dashboard.main`` exits 1 when ``NUCLEUS_HUD_ROOT`` points at a missing
  tree — the loud-fail contract.
- ``accuracy.verify_nucleus_accuracy`` writes the receipt to the override
  path when ``NUCLEUS_ACCURACY_RECEIPT`` is set.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ENV_KEYS = (
    "NUCLEUS_ROOT",
    "NUCLEUS_BRAIN",
    "NUCLEUS_BRAIN_PATH",
    "NUCLEUS_DEMO_ROOT",
    "NUCLEUS_HUD_ROOT",
    "NUCLEUS_ENGRAM_DB",
    "NUCLEUS_ACCURACY_RECEIPT",
)


@pytest.fixture
def clean_env(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_modules_import_clean(clean_env):
    from mcp_server_nucleus.diagnostics import accuracy, core, dashboard, mcp

    assert callable(core.main)
    assert callable(mcp.main)
    assert callable(dashboard.main)
    assert callable(accuracy.main)


def test_mcp_demo_root_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import mcp as mcp_diag

    clean_env.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path / "demos"))
    assert mcp_diag._demo_root() == tmp_path / "demos"


def test_mcp_demo_root_fallback(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import mcp as mcp_diag

    clean_env.setenv("NUCLEUS_ROOT", str(tmp_path))
    assert mcp_diag._demo_root() == tmp_path / "output" / "demos"


def test_dashboard_hud_root_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import dashboard

    clean_env.setenv("NUCLEUS_HUD_ROOT", str(tmp_path / "hud"))
    assert dashboard._hud_root() == tmp_path / "hud"


def test_dashboard_hud_root_fallback(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import dashboard

    clean_env.setenv("NUCLEUS_ROOT", str(tmp_path))
    assert dashboard._hud_root() == tmp_path / "tools" / "nucleus-hud"


def test_dashboard_main_fails_loud_on_missing_root(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import dashboard

    clean_env.setenv("NUCLEUS_HUD_ROOT", str(tmp_path / "does-not-exist"))
    assert dashboard.main() == 1


def test_accuracy_db_path_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import accuracy

    clean_env.setenv("NUCLEUS_ENGRAM_DB", str(tmp_path / "engrams.db"))
    assert accuracy._db_path() == tmp_path / "engrams.db"


def test_accuracy_receipt_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import accuracy

    clean_env.setenv("NUCLEUS_ACCURACY_RECEIPT", str(tmp_path / "receipt.json"))
    assert accuracy._receipt_path() == tmp_path / "receipt.json"


def test_accuracy_runs_with_missing_db_and_writes_receipt(clean_env, tmp_path):
    from mcp_server_nucleus.diagnostics import accuracy

    clean_env.setenv("NUCLEUS_ENGRAM_DB", str(tmp_path / "nope.db"))
    receipt = tmp_path / "receipt.json"
    clean_env.setenv("NUCLEUS_ACCURACY_RECEIPT", str(receipt))

    summary = accuracy.verify_nucleus_accuracy()

    assert receipt.exists()
    written: dict = json.loads(receipt.read_text())
    assert written == summary
    assert summary["nucleus_accuracy"] == 100.0
