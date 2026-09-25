"""Coverage tests for mcp_server_nucleus.diagnostics.core."""
import sys
from unittest import mock

import pytest

from mcp_server_nucleus.diagnostics import core as diag_core


def test_main_import_error(monkeypatch):
    """main() returns 1 when DualEngineLLM cannot be imported."""
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "mcp_server_nucleus.runtime.llm_client":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    # Ensure NUCLEUS_BRAIN_PATH is set so we skip that branch
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/test_brain")
    result = diag_core.main()
    assert result == 1


def test_main_success(monkeypatch):
    """main() returns 0 when DualEngineLLM generates a response."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/test_brain")

    fake_model = mock.MagicMock()
    fake_model.engine = "test"
    fake_model.tier = "RESEARCH"
    fake_model.model_name = "test-model"
    fake_response = mock.MagicMock()
    fake_response.text = "OK"
    fake_model.generate_content.return_value = fake_response

    fake_module = mock.MagicMock()
    fake_module.DualEngineLLM = mock.MagicMock(return_value=fake_model)

    monkeypatch.setitem(sys.modules, "mcp_server_nucleus.runtime.llm_client", fake_module)
    result = diag_core.main()
    assert result == 0


def test_main_none_response(monkeypatch):
    """main() returns 1 when inference returns None."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/test_brain")

    fake_model = mock.MagicMock()
    fake_model.engine = "test"
    fake_model.tier = "RESEARCH"
    fake_model.model_name = "test-model"
    fake_model.generate_content.return_value = None

    fake_module = mock.MagicMock()
    fake_module.DualEngineLLM = mock.MagicMock(return_value=fake_model)

    monkeypatch.setitem(sys.modules, "mcp_server_nucleus.runtime.llm_client", fake_module)
    result = diag_core.main()
    assert result == 1


def test_main_exception(monkeypatch):
    """main() returns 1 when generate_content raises."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/test_brain")

    fake_model = mock.MagicMock()
    fake_model.engine = "test"
    fake_model.tier = "RESEARCH"
    fake_model.model_name = "test-model"
    fake_model.generate_content.side_effect = RuntimeError("boom")

    fake_module = mock.MagicMock()
    fake_module.DualEngineLLM = mock.MagicMock(return_value=fake_model)

    monkeypatch.setitem(sys.modules, "mcp_server_nucleus.runtime.llm_client", fake_module)
    result = diag_core.main()
    assert result == 1


def test_main_sets_brain_path_if_missing(monkeypatch):
    """main() sets NUCLEUS_BRAIN_PATH if not already set."""
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)

    fake_model = mock.MagicMock()
    fake_model.engine = "test"
    fake_model.tier = "RESEARCH"
    fake_model.model_name = "test-model"
    fake_response = mock.MagicMock()
    fake_response.text = "OK"
    fake_model.generate_content.return_value = fake_response

    fake_module = mock.MagicMock()
    fake_module.DualEngineLLM = mock.MagicMock(return_value=fake_model)

    monkeypatch.setitem(sys.modules, "mcp_server_nucleus.runtime.llm_client", fake_module)
    result = diag_core.main()
    assert result == 0
    assert "NUCLEUS_BRAIN_PATH" in __import__("os").environ
