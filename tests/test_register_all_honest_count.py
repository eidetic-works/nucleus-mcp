"""Regression test: stub modules must not count toward registered-module total.

Defect (c): ``tools/{archive,synthetic_qa,skills,observability}.py`` register()
return empty tool lists yet count toward the startup module total in
``register_all()``.  The startup message previously said
``"Registered N facade tools from M modules"`` where M included stub
modules that contributed zero tools — an dishonest count.

``archive.py``, ``synthetic_qa.py``, and ``skills.py`` were already
removed from the registry (DEAD-IN-REGISTRY).  ``observability.py``
remains as a stub returning ``[]``.  This test verifies that
``register_all`` counts only modules that actually registered at
least one tool, and separately reports stub modules.
"""
from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest


def _make_stub_module(name="observability"):
    """A module whose register() returns [] (zero tools)."""
    mod = MagicMock()
    mod.__name__ = f"mcp_server_nucleus.tools.{name}"
    mod.register = MagicMock(return_value=[])
    return mod


def _make_real_module(name, tool_names):
    """A module whose register() returns [(name, func), ...]."""
    mod = MagicMock()
    mod.__name__ = f"mcp_server_nucleus.tools.{name}"
    tools = [(tn, MagicMock()) for tn in tool_names]
    mod.register = MagicMock(return_value=tools)
    return mod


@pytest.fixture(autouse=True)
def _quiet_off(monkeypatch):
    """Ensure the startup message is printed (not suppressed)."""
    monkeypatch.setenv("NUCLEUS_DEBUG", "1")
    # Clear argv flags that suppress output
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


def test_stub_module_not_counted_in_registered_total(monkeypatch, capsys):
    """A module returning [] is not counted in the 'from N modules' total."""
    import mcp_server_nucleus.tools as tools_init

    stub = _make_stub_module("observability")
    real = _make_real_module("engrams", ["nucleus_engrams"])
    real2 = _make_real_module("tasks", ["nucleus_tasks"])

    monkeypatch.setattr(tools_init, "_get_active_modules", lambda: [stub, real, real2])

    mock_mcp = MagicMock()
    mock_helpers = {"make_response": lambda *a, **k: "{}"}
    tools_init.register_all(mock_mcp, mock_helpers)

    captured = capsys.readouterr()
    # The message must say "from 2 modules" (the two real ones), NOT 3
    assert "from 2 modules" in captured.err, (
        f"expected 'from 2 modules' (stub excluded), got: {captured.err!r}"
    )
    # The stub must be mentioned separately
    assert "stub" in captured.err.lower(), (
        f"expected stub mention in message, got: {captured.err!r}"
    )
    assert "observability" in captured.err, (
        f"expected 'observability' in stub list, got: {captured.err!r}"
    )


def test_no_stub_modules_message_clean(monkeypatch, capsys):
    """When no stubs exist, the message has no 'stub' suffix."""
    import mcp_server_nucleus.tools as tools_init

    real = _make_real_module("engrams", ["nucleus_engrams"])
    real2 = _make_real_module("tasks", ["nucleus_tasks"])

    monkeypatch.setattr(tools_init, "_get_active_modules", lambda: [real, real2])

    mock_mcp = MagicMock()
    mock_helpers = {"make_response": lambda *a, **k: "{}"}
    tools_init.register_all(mock_mcp, mock_helpers)

    captured = capsys.readouterr()
    assert "from 2 modules" in captured.err
    assert "stub" not in captured.err.lower()


def test_all_stub_modules_excluded(monkeypatch, capsys):
    """When all modules are stubs, registered count is 0."""
    import mcp_server_nucleus.tools as tools_init

    stub1 = _make_stub_module("observability")
    stub2 = _make_stub_module("archive")

    monkeypatch.setattr(tools_init, "_get_active_modules", lambda: [stub1, stub2])

    mock_mcp = MagicMock()
    mock_helpers = {"make_response": lambda *a, **k: "{}"}
    tools_init.register_all(mock_mcp, mock_helpers)

    captured = capsys.readouterr()
    assert "from 0 modules" in captured.err, (
        f"expected 'from 0 modules', got: {captured.err!r}"
    )
    assert "2 stub" in captured.err


def test_observability_module_returns_empty_list():
    """The real observability.py register() returns [] (zero tools)."""
    from mcp_server_nucleus.tools import observability

    result = observability.register(MagicMock(), {})
    assert result == [], f"observability.register() should return [], got {result!r}"


def test_observability_not_in_registered_count(monkeypatch, capsys):
    """Integration: real observability stub is excluded from the module count.

    Mocks all OTHER modules to return one tool each, lets the real
    observability stub run, and verifies the count excludes it.
    """
    import mcp_server_nucleus.tools as tools_init
    from mcp_server_nucleus.tools import observability as obs_mod

    # Build a list: one real mock module + the real observability stub
    real = _make_real_module("engrams", ["nucleus_engrams"])
    monkeypatch.setattr(tools_init, "_get_active_modules", lambda: [real, obs_mod])

    mock_mcp = MagicMock()
    mock_helpers = {"make_response": lambda *a, **k: "{}"}
    tools_init.register_all(mock_mcp, mock_helpers)

    captured = capsys.readouterr()
    assert "from 1 modules" in captured.err, (
        f"expected 'from 1 modules' (observability excluded), got: {captured.err!r}"
    )
    assert "observability" in captured.err
