"""Comprehensive tests for mcp_server_nucleus.runtime.strategy.

Covers get_brain_path, _manage_strategy (read/update/append/unknown/error),
and _update_roadmap (read/add/complete/unknown/error).
"""
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import strategy


# ── get_brain_path ──

class TestGetBrainPath:
    def test_env_var_set(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        assert strategy.get_brain_path() == brain

    def test_env_var_not_set_cwd_has_brain(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        cwd = tmp_path / "project"
        cwd.mkdir()
        brain = cwd / ".brain"
        brain.mkdir()
        monkeypatch.chdir(cwd)
        assert strategy.get_brain_path() == brain

    def test_env_var_not_set_parent_has_brain(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        parent = tmp_path / "root"
        child = parent / "sub" / "deep"
        child.mkdir(parents=True)
        brain = parent / ".brain"
        brain.mkdir()
        monkeypatch.chdir(child)
        assert strategy.get_brain_path() == brain

    def test_env_var_not_set_no_brain_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        with pytest.raises(ValueError, match="NUCLEUS_BRAIN_PATH"):
            strategy.get_brain_path()


# ── _manage_strategy ──

class TestManageStrategy:
    def test_read_empty(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("read")
        assert result == {"status": "empty", "content": ""}

    def test_read_success(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "strategy.md").write_text("# My Strategy")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("read")
        assert result == {"status": "success", "content": "# My Strategy"}

    def test_update_success(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("update", content="New strategy")
        assert result == {"status": "success", "message": "Strategy updated"}
        assert (brain / "strategy.md").read_text() == "New strategy"

    def test_update_no_content(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("update")
        assert result == {"error": "Content required for update"}

    def test_update_empty_content(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("update", content="")
        assert result == {"error": "Content required for update"}

    def test_append_to_existing(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "strategy.md").write_text("Original")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("append", content="Appended")
        assert result == {"status": "success", "message": "Strategy appended"}
        content = (brain / "strategy.md").read_text()
        assert "Original" in content
        assert "Appended" in content

    def test_append_to_nonexistent(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("append", content="First")
        assert result == {"status": "success", "message": "Strategy appended"}
        content = (brain / "strategy.md").read_text()
        assert "First" in content

    def test_append_no_content(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("append")
        assert result == {"error": "Content required for append"}

    def test_append_empty_content(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("append", content="")
        assert result == {"error": "Content required for append"}

    def test_unknown_action(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._manage_strategy("delete")
        assert "Unknown action" in result["error"]
        assert "delete" in result["error"]

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        # Force an exception by making brain_path unusable
        monkeypatch.setattr(strategy, "get_brain_path", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        result = strategy._manage_strategy("read")
        assert "error" in result
        assert "boom" in result["error"]


# ── _update_roadmap ──

class TestUpdateRoadmap:
    def test_read_empty(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("read")
        assert result == {"status": "empty", "content": ""}

    def test_read_success(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "roadmap.md").write_text("# Roadmap\n- [ ] task1")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("read")
        assert result == {"status": "success", "content": "# Roadmap\n- [ ] task1"}

    def test_add_to_nonexistent(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("add", item="Build feature X")
        assert result["status"] == "success"
        assert "Build feature X" in result["message"]
        content = (brain / "roadmap.md").read_text()
        assert "# Roadmap" in content
        assert "- [ ] Build feature X" in content

    def test_add_to_existing(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "roadmap.md").write_text("# Roadmap\n- [ ] task1")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("add", item="task2")
        assert result["status"] == "success"
        content = (brain / "roadmap.md").read_text()
        assert "- [ ] task1" in content
        assert "- [ ] task2" in content

    def test_add_no_item(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("add")
        assert result["status"] == "success"
        content = (brain / "roadmap.md").read_text()
        assert "- [ ] None" in content

    def test_complete_success(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "roadmap.md").write_text("# Roadmap\n- [ ] task1\n- [ ] task2")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("complete", item="task1")
        assert result["status"] == "success"
        content = (brain / "roadmap.md").read_text()
        assert "- [x] task1" in content
        assert "- [ ] task2" in content

    def test_complete_roadmap_not_found(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("complete", item="task1")
        assert result == {"error": "Roadmap not found"}

    def test_complete_item_not_found(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "roadmap.md").write_text("# Roadmap\n- [ ] task1")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("complete", item="nonexistent")
        assert "Item not found" in result["error"]
        assert "nonexistent" in result["error"]

    def test_unknown_action(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = strategy._update_roadmap("delete")
        assert "Unknown action" in result["error"]
        assert "delete" in result["error"]

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(strategy, "get_brain_path", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        result = strategy._update_roadmap("read")
        assert "error" in result
        assert "boom" in result["error"]
