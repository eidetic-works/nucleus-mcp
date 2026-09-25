"""Coverage tests for mcp_server_nucleus/diagnostics/mcp.py — the MCP server
import + tool-registration diagnostic."""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.diagnostics import mcp as diag_mcp


# ── _demo_root ──────────────────────────────────────────────────────

class TestDemoRoot:
    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        assert diag_mcp._demo_root() == tmp_path

    def test_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_DEMO_ROOT", raising=False)
        with patch("mcp_server_nucleus.diagnostics.mcp.nucleus_root", return_value=tmp_path):
            r = diag_mcp._demo_root()
        assert r == tmp_path / "output" / "demos"


# ── main ────────────────────────────────────────────────────────────

class TestMain:
    def test_import_failure_returns_1(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            r = diag_mcp.main()
        assert r == 1

    def test_mcp_object_failure(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        fake_mod = MagicMock()
        fake_mod.__version__ = "1.0"
        with patch.dict(sys.modules, {"mcp_server_nucleus": fake_mod}), \
             patch("mcp_server_nucleus.diagnostics.mcp.nucleus_root", return_value=tmp_path):
            # Make the `from mcp_server_nucleus import mcp` fail
            del fake_mod.mcp
            with patch.object(fake_mod, "mcp", create=True, side_effect=ImportError("no mcp")):
                pass
            # Simpler: patch the import to fail at step 2
            orig_import = __import__

            def fake_import(name, *args, **kwargs):
                if name == "mcp_server_nucleus" and args and len(args[0]) > 1 and "mcp" in args[0]:
                    raise ImportError("no mcp attr")
                return orig_import(name, *args, **kwargs)

            r = diag_mcp.main()
        assert r == 1

    def test_successful_run_with_tools_attr(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        # Mock the nucleus module and its tools
        fake_nucleus = MagicMock()
        fake_nucleus.__version__ = "1.0"
        fake_mcp = MagicMock()
        fake_mcp._tools = {"nucleus_list_directory": MagicMock(), "nucleus_delete_file": MagicMock()}
        fake_nucleus.mcp = fake_mcp
        fake_nucleus.nucleus_list_directory = MagicMock(return_value="dir listing")
        fake_nucleus.nucleus_delete_file = MagicMock(return_value="blocked")
        with patch.dict(sys.modules, {"mcp_server_nucleus": fake_nucleus}):
            r = diag_mcp.main()
        assert r == 0
        out = capsys.readouterr().out
        assert "Diagnosis complete" in out
        assert "OK: imported v1.0" in out

    def test_successful_run_without_tools_attr(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        fake_nucleus = MagicMock()
        fake_nucleus.__version__ = "2.0"
        fake_mcp = MagicMock(spec=[])  # no _tools attr
        fake_nucleus.mcp = fake_mcp
        fake_nucleus.nucleus_list_directory = MagicMock(return_value="dir listing")
        fake_nucleus.nucleus_delete_file = MagicMock(return_value="blocked")
        with patch.dict(sys.modules, {"mcp_server_nucleus": fake_nucleus}):
            r = diag_mcp.main()
        assert r == 0
        out = capsys.readouterr().out
        assert "FastMCP: direct import fallback" in out

    def test_live_call_failure(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        fake_nucleus = MagicMock()
        fake_nucleus.__version__ = "1.0"
        fake_mcp = MagicMock()
        fake_mcp._tools = {"nucleus_list_directory": MagicMock(), "nucleus_delete_file": MagicMock()}
        fake_nucleus.mcp = fake_mcp
        fake_nucleus.nucleus_list_directory = MagicMock(side_effect=RuntimeError("boom"))
        fake_nucleus.nucleus_delete_file = MagicMock()
        with patch.dict(sys.modules, {"mcp_server_nucleus": fake_nucleus}):
            r = diag_mcp.main()
        assert r == 1

    def test_sets_brain_path_if_missing(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("NUCLEUS_DEMO_ROOT", str(tmp_path))
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        fake_nucleus = MagicMock()
        fake_nucleus.__version__ = "1.0"
        fake_mcp = MagicMock(spec=[])
        fake_nucleus.mcp = fake_mcp
        fake_nucleus.nucleus_list_directory = MagicMock(return_value="ok")
        fake_nucleus.nucleus_delete_file = MagicMock(return_value="ok")
        with patch.dict(sys.modules, {"mcp_server_nucleus": fake_nucleus}):
            diag_mcp.main()
        assert os.environ["NUCLEUS_BRAIN_PATH"] == str(tmp_path / ".brain")
