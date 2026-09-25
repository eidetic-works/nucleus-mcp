"""
Coverage tests for mcp_server_nucleus.runtime.critic.

Targets 90%+ line coverage. Uses tmp_path for filesystem, monkeypatch for
env vars, and mocks DualEngineLLM. No real network/subprocess.
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import critic as critic_mod
from mcp_server_nucleus.runtime.critic import _critique_code, get_brain_path


# ──────────────────────────────────────────────────────────────────────
# get_brain_path
# ──────────────────────────────────────────────────────────────────────

def test_get_brain_path_from_env(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    assert get_brain_path() == brain


def test_get_brain_path_env_not_set_finds_brain_in_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.chdir(tmp_path)
    assert get_brain_path() == brain


def test_get_brain_path_env_not_set_finds_brain_in_parent(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.chdir(sub)
    assert get_brain_path() == brain


def test_get_brain_path_env_not_set_no_brain_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    with pytest.raises(ValueError, match="not set"):
        get_brain_path()


def test_get_brain_path_env_path_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "nope"))
    with pytest.raises(ValueError, match="does not exist"):
        get_brain_path()


# ──────────────────────────────────────────────────────────────────────
# _critique_code — error paths
# ──────────────────────────────────────────────────────────────────────

def _setup_brain(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "agents").mkdir()
    (brain / "artifacts" / "reviews").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


def test_critique_file_not_found(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    result = _critique_code("missing.py")
    assert result["success"] is False
    assert "File not found" in result["error"]


def test_critique_critic_persona_missing(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    # remove agents dir content
    target = brain.parent / "target.py"
    target.write_text("print('hi')")
    # critic.md not present
    result = _critique_code("target.py")
    assert result["success"] is False
    assert "Critic persona not found" in result["error"]


def test_critique_llm_unavailable(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")
    with patch.object(critic_mod, "DualEngineLLM", None):
        result = _critique_code("target.py")
    assert result["success"] is False
    assert "LLM Client not available" in result["error"]


def test_critique_llm_init_fails(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    fake_llm_cls = MagicMock(side_effect=RuntimeError("no key"))
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is False
    assert "LLM Init failed" in result["error"]


def test_critique_llm_empty_response(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = None
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is False
    assert "empty response" in result["error"]


def test_critique_llm_response_no_text_attr(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = object()  # no .text
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is False
    assert "empty response" in result["error"]


def test_critique_no_json_in_response(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    resp = MagicMock()
    resp.text = "This is just plain text, no JSON here."
    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = resp
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is False
    assert "No JSON found" in result["error"]
    assert result["raw"] == resp.text


def test_critique_invalid_json_in_response(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    resp = MagicMock()
    resp.text = "{not valid json}"
    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = resp
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is False
    assert "Invalid JSON" in result["error"]


def test_critique_success_approved(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    critique_data = {
        "event_type": "review_approved",
        "severity": "ROUTINE",
        "payload": {"target": "target.py", "notes": "LGTM"},
    }
    resp = MagicMock()
    resp.text = f"Here is my review:\n{json.dumps(critique_data)}\nDone."
    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = resp
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is True
    assert result["status"] == "APPROVED"
    assert result["critique"] == critique_data
    # artifact written
    review_path = Path(result["review_path"])
    assert review_path.exists()
    assert json.loads(review_path.read_text()) == critique_data


def test_critique_success_blocked(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = brain.parent / "target.py"
    target.write_text("print('hi')")

    critique_data = {
        "event_type": "review_blocked",
        "severity": "HIGH",
        "payload": {"issues": ["bug1"]},
    }
    resp = MagicMock()
    resp.text = json.dumps(critique_data)
    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = resp
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code("target.py")
    assert result["success"] is True
    assert result["status"] == "BLOCKED"


def test_critique_absolute_path(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path, monkeypatch)
    (brain / "agents" / "critic.md").write_text("You are a critic.")
    target = tmp_path / "abs_target.py"
    target.write_text("x = 1")

    critique_data = {"event_type": "review_approved", "severity": "ROUTINE", "payload": {}}
    resp = MagicMock()
    resp.text = json.dumps(critique_data)
    llm_instance = MagicMock()
    llm_instance.generate_content.return_value = resp
    fake_llm_cls = MagicMock(return_value=llm_instance)
    with patch.object(critic_mod, "DualEngineLLM", fake_llm_cls):
        result = _critique_code(str(target))
    assert result["success"] is True


def test_critique_outer_exception_returns_error(tmp_path, monkeypatch):
    # Force get_brain_path to raise to hit the outer try/except
    def boom():
        raise RuntimeError("brain exploded")
    monkeypatch.setattr(critic_mod, "get_brain_path", boom)
    result = _critique_code("anything.py")
    assert result["success"] is False
    assert "Critique generation failed" in result["error"]
