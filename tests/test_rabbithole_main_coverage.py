"""Tests for mcp_server_nucleus.rabbithole.__main__ entry point.

Covers the trivial entry point module — verifies it imports correctly
and exposes the ``main`` callable. Also exercises the
``if __name__ == "__main__"`` guard via runpy with a mocked main.
"""
import importlib
import runpy
from unittest.mock import patch

import pytest


class TestRabbitholeMainModuleImport:
    """Verify the rabbithole __main__ module can be imported and exposes main()."""

    def test_module_imports(self):
        mod = importlib.import_module("mcp_server_nucleus.rabbithole.__main__")
        assert mod is not None

    def test_main_callable_exists(self):
        mod = importlib.import_module("mcp_server_nucleus.rabbithole.__main__")
        assert callable(getattr(mod, "main", None))

    def test_module_has_name_guard(self):
        """The module should have the if __name__ == '__main__' guard."""
        import inspect
        mod = importlib.import_module("mcp_server_nucleus.rabbithole.__main__")
        source = inspect.getsource(mod)
        assert "__name__" in source
        assert "__main__" in source

    def test_main_is_rabbithole_server_main(self):
        """main should be the same function as rabbithole.server.main."""
        from mcp_server_nucleus.rabbithole.server import main as server_main
        mod = importlib.import_module("mcp_server_nucleus.rabbithole.__main__")
        assert mod.main is server_main

    def test_main_guard_calls_main(self):
        """Running the module as __main__ should call main()."""
        with patch("mcp_server_nucleus.rabbithole.server.main") as mock_main:
            runpy.run_module("mcp_server_nucleus.rabbithole", run_name="__main__")
        mock_main.assert_called_once()
