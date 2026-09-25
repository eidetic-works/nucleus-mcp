"""Tests for mcp_server_nucleus.core.orchestrator module.

Covers the lazy-loaded orchestrator singleton accessor.
"""
import importlib
from unittest.mock import patch, MagicMock

import pytest


class TestOrchestratorModuleImport:
    """Verify the orchestrator module imports correctly."""

    def test_module_imports(self):
        mod = importlib.import_module("mcp_server_nucleus.core.orchestrator")
        assert mod is not None

    def test_get_orchestrator_callable(self):
        mod = importlib.import_module("mcp_server_nucleus.core.orchestrator")
        assert callable(getattr(mod, "get_orchestrator", None))

    def test_module_has_docstring(self):
        mod = importlib.import_module("mcp_server_nucleus.core.orchestrator")
        assert mod.__doc__ is not None
        assert "Orchestrator" in mod.__doc__

    def test_get_orchestrator_has_docstring(self):
        mod = importlib.import_module("mcp_server_nucleus.core.orchestrator")
        assert mod.get_orchestrator.__doc__ is not None

    def test_get_orchestrator_delegates_to_unified(self):
        """get_orchestrator should delegate to orchestrator_unified.get_orchestrator."""
        import sys
        from types import ModuleType

        mock_orchestrator = MagicMock(name="unified_orchestrator")
        mock_get = MagicMock(return_value=mock_orchestrator)
        fake_module = ModuleType("mcp_server_nucleus.runtime.orchestrator_unified")
        fake_module.get_orchestrator = mock_get

        with patch.dict(sys.modules, {
            "mcp_server_nucleus.runtime.orchestrator_unified": fake_module
        }):
            mod = importlib.import_module("mcp_server_nucleus.core.orchestrator")
            result = mod.get_orchestrator()

        assert result is mock_orchestrator
        mock_get.assert_called_once()
