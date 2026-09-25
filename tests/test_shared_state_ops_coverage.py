"""Comprehensive tests for shared_state_ops module."""
import json
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import shared_state_ops
from mcp_server_nucleus.runtime.shared_state_ops import (
    _get_shared_dir,
    _sanitize_key,
    brain_sync_read,
    brain_sync_write,
    brain_sync_list,
)


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Create a temporary brain path."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


# ── _sanitize_key ────────────────────────────────────────────────

class TestSanitizeKey:
    def test_valid_key(self):
        assert _sanitize_key("mykey") == "mykey"

    def test_empty_key_raises(self):
        with pytest.raises(ValueError):
            _sanitize_key("")

    def test_whitespace_only_key_raises(self):
        with pytest.raises(ValueError):
            _sanitize_key("   ")

    def test_none_key_raises(self):
        with pytest.raises(ValueError):
            _sanitize_key(None)

    def test_slash_replaced(self):
        result = _sanitize_key("a/b")
        assert "/" not in result
        assert result == "a_b"

    def test_backslash_replaced(self):
        result = _sanitize_key("a\\b")
        assert "\\" not in result
        assert result == "a_b"

    def test_dotdot_replaced(self):
        result = _sanitize_key("..")
        assert result == "_"

    def test_trailing_dots_stripped(self):
        # "key..." -> ".." replaced with "_" -> "key_." -> rstrip(".") -> "key_"
        result = _sanitize_key("key...")
        assert "." not in result

    def test_only_dots_becomes_underscore(self):
        # "..." -> ".." replaced with "_" -> "_.", rstrip(".") -> "_"
        # "_" is not empty and doesn't start with ".", so it passes
        result = _sanitize_key("...")
        assert result == "_"

    def test_leading_dot_raises(self):
        # After sanitization, ".." becomes "_", then rstrip(".") leaves "_"
        # But a key like ".hidden" -> ".hidden" -> starts with "." -> raises
        with pytest.raises(ValueError):
            _sanitize_key(".hidden")

    def test_path_traversal_attempt(self):
        result = _sanitize_key("../../etc/passwd")
        # Should not contain any path separators or ..
        assert "/" not in result
        assert ".." not in result


# ── _get_shared_dir ──────────────────────────────────────────────

class TestGetSharedDir:
    def test_creates_shared_dir(self, brain_path):
        shared = _get_shared_dir()
        assert shared.exists()
        assert shared.name == "shared"
        assert shared.parent == brain_path

    def test_idempotent(self, brain_path):
        d1 = _get_shared_dir()
        d2 = _get_shared_dir()
        assert d1 == d2


# ── brain_sync_write ─────────────────────────────────────────────

class TestBrainSyncWrite:
    def test_write_basic(self, brain_path):
        result = brain_sync_write("test_key", {"data": "value"})
        assert result["written"] is True
        assert result["key"] == "test_key"
        assert result["value"] == {"data": "value"}
        assert "agent_id" in result
        assert "updated_at" in result

    def test_write_with_agent_id(self, brain_path):
        result = brain_sync_write("key1", "val", agent_id="agent-007")
        assert result["agent_id"] == "agent-007"

    def test_write_without_agent_id_uses_sync_ops(self, brain_path, monkeypatch):
        # When no agent_id, it tries to import get_current_agent
        result = brain_sync_write("key2", "val")
        assert "agent_id" in result
        assert result["agent_id"]  # should be non-empty string

    def test_write_persists_to_file(self, brain_path):
        brain_sync_write("persist_key", {"x": 1}, agent_id="a1")
        shared = brain_path / "shared"
        files = list(shared.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["key"] == "persist_key"
        assert data["value"] == {"x": 1}

    def test_write_invalid_key_raises(self, brain_path):
        with pytest.raises(ValueError):
            brain_sync_write("", "val")

    def test_write_none_value(self, brain_path):
        result = brain_sync_write("none_key", None)
        assert result["value"] is None

    def test_write_complex_value(self, brain_path):
        val = {"nested": {"list": [1, 2, 3], "str": "hello"}}
        result = brain_sync_write("complex", val)
        assert result["value"] == val


# ── brain_sync_read ──────────────────────────────────────────────

class TestBrainSyncRead:
    def test_read_not_found(self, brain_path):
        result = brain_sync_read("nonexistent")
        assert result["found"] is False
        assert result["key"] == "nonexistent"

    def test_read_after_write(self, brain_path):
        brain_sync_write("read_key", {"data": 42}, agent_id="reader")
        result = brain_sync_read("read_key")
        assert result["found"] is True
        assert result["key"] == "read_key"
        assert result["value"] == {"data": 42}

    def test_read_invalid_key_raises(self, brain_path):
        with pytest.raises(ValueError):
            brain_sync_read("")

    def test_read_returns_original_key(self, brain_path):
        # Even if key has chars that get sanitized, read returns original key
        brain_sync_write("a_b", "val", agent_id="x")
        result = brain_sync_read("a_b")
        assert result["key"] == "a_b"


# ── brain_sync_list ──────────────────────────────────────────────

class TestBrainSyncList:
    def test_list_empty(self, brain_path):
        result = brain_sync_list()
        assert result["keys"] == []
        assert result["count"] == 0

    def test_list_with_entries(self, brain_path):
        brain_sync_write("key_a", "val_a", agent_id="agent1")
        brain_sync_write("key_b", "val_b", agent_id="agent2")
        result = brain_sync_list()
        assert result["count"] == 2
        keys = [k["key"] for k in result["keys"]]
        assert "key_a" in keys
        assert "key_b" in keys

    def test_list_includes_metadata(self, brain_path):
        brain_sync_write("meta_key", "val", agent_id="meta_agent")
        result = brain_sync_list()
        entry = result["keys"][0]
        assert entry["agent_id"] == "meta_agent"
        assert "updated_at" in entry
        assert entry["updated_at"] != ""

    def test_list_with_corrupt_file(self, brain_path):
        # Write a valid entry
        brain_sync_write("good", "val", agent_id="a")
        # Write a corrupt file
        shared = brain_path / "shared"
        (shared / "corrupt.json").write_text("not valid json{{{")
        result = brain_sync_list()
        # Should include both, corrupt one with defaults
        assert result["count"] == 2
        corrupt_entry = [k for k in result["keys"] if k["key"] == "corrupt"][0]
        assert corrupt_entry["agent_id"] == "unknown"
        assert corrupt_entry["updated_at"] == ""

    def test_list_sorted(self, brain_path):
        brain_sync_write("zebra", "z", agent_id="a")
        brain_sync_write("apple", "a", agent_id="b")
        result = brain_sync_list()
        # Files are sorted by glob (alphabetical filename)
        keys = [k["key"] for k in result["keys"]]
        assert keys == sorted(keys)
