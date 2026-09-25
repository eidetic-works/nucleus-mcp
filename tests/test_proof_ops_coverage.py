"""Coverage tests for runtime/proof_ops.py."""
import json
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import proof_ops


def test_brain_generate_proof_impl_success(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._generate_proof.return_value = {"success": True, "path": "x"}
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_generate_proof_impl(
            feature_id="f1",
            thinking="t",
            deployed_url="http://x",
            files_changed=["a.py"],
            risk_level="low",
            rollback_time="5m",
        )
    data = json.loads(out)
    assert data["success"] is True


def test_brain_generate_proof_impl_returns_string(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._generate_proof.return_value = "plain string"
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_generate_proof_impl(
            feature_id="f1", thinking="t", deployed_url="u",
            files_changed=[], risk_level="low", rollback_time="1m",
        )
    assert out == "plain string"


def test_brain_generate_proof_impl_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._generate_proof.side_effect = RuntimeError("boom")
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_generate_proof_impl(
            feature_id="f1", thinking="t", deployed_url="u",
            files_changed=[], risk_level="low", rollback_time="1m",
        )
    assert "Error generating proof" in out


def test_brain_get_proof_impl_success(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._get_proof.return_value = "proof content"
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_get_proof_impl("f1")
    assert out == "proof content"


def test_brain_get_proof_impl_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._get_proof.side_effect = RuntimeError("boom")
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_get_proof_impl("f1")
    assert "Error getting proof" in out


def test_brain_list_proofs_impl_success(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._list_proofs.return_value = ["a.md", "b.md"]
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_list_proofs_impl()
    assert out == ["a.md", "b.md"]


def test_brain_list_proofs_impl_error_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    mock_sys = MagicMock()
    mock_sys._list_proofs.side_effect = RuntimeError("boom")
    with patch.object(proof_ops, "_get_proof_system", return_value=mock_sys):
        out = proof_ops._brain_list_proofs_impl()
    assert out == []


def test_get_proof_system_returns_instance(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    sys = proof_ops._get_proof_system()
    assert sys is not None
