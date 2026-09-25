"""Comprehensive tests for storage module."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import storage
from mcp_server_nucleus.runtime.storage import (
    _path_to_id,
    read_brain_file,
    write_brain_file,
    brain_file_exists,
    get_firestore_client,
)


@pytest.fixture(autouse=True)
def reset_storage_state(monkeypatch):
    """Reset storage module state before each test."""
    # Reset STORAGE_TYPE to local
    monkeypatch.setattr(storage, "STORAGE_TYPE", "local")
    # Reset singleton
    storage._firestore_client = None
    yield
    storage._firestore_client = None


# ── _path_to_id ──────────────────────────────────────────────────

class TestPathToId:
    def test_simple_path(self):
        result = _path_to_id("ledger/tasks.json")
        assert result == "ledger__tasks_json"

    def test_absolute_path(self):
        result = _path_to_id("/abs/path/file.json")
        assert result == "abs__path__file_json"

    def test_with_dots(self):
        result = _path_to_id("config/nucleus.yaml")
        assert result == "config__nucleus_yaml"

    def test_path_object(self):
        result = _path_to_id(Path("ledger/tasks.json"))
        assert result == "ledger__tasks_json"

    def test_strips_leading_slash(self):
        result = _path_to_id("/test/file.txt")
        assert not result.startswith("_")


# ── read_brain_file (local mode) ─────────────────────────────────

class TestReadBrainFile:
    def test_read_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        assert read_brain_file(f) == "hello world"

    def test_read_nonexistent_raises(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            read_brain_file(f)

    def test_read_with_path_object(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        assert read_brain_file(Path(f)) == "content"


# ── write_brain_file (local mode) ────────────────────────────────

class TestWriteBrainFile:
    def test_write_creates_file(self, tmp_path):
        f = tmp_path / "output.txt"
        write_brain_file(f, "test content")
        assert f.read_text() == "test content"

    def test_write_creates_parent_dirs(self, tmp_path):
        f = tmp_path / "sub" / "dir" / "file.txt"
        write_brain_file(f, "nested")
        assert f.read_text() == "nested"
        assert f.parent.exists()

    def test_write_overwrites(self, tmp_path):
        f = tmp_path / "file.txt"
        write_brain_file(f, "first")
        write_brain_file(f, "second")
        assert f.read_text() == "second"

    def test_write_with_path_object(self, tmp_path):
        f = tmp_path / "file.txt"
        write_brain_file(Path(f), "path obj")
        assert f.read_text() == "path obj"


# ── brain_file_exists (local mode) ───────────────────────────────

class TestBrainFileExists:
    def test_exists_true(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("content")
        assert brain_file_exists(f) is True

    def test_not_exists_false(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        assert brain_file_exists(f) is False

    def test_with_path_object(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("content")
        assert brain_file_exists(Path(f)) is True


# ── Firestore mode ───────────────────────────────────────────────

class TestFirestoreMode:
    def test_get_firestore_client_not_installed(self, monkeypatch):
        monkeypatch.setattr(storage, "firestore", None)
        with pytest.raises(ImportError, match="not found"):
            get_firestore_client()

    def test_get_firestore_client_creates_singleton(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        storage._firestore_client = None
        client1 = get_firestore_client()
        client2 = get_firestore_client()
        assert client1 is client2
        assert client1 is mock_client

    def test_get_firestore_client_init_failure(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_firestore.Client.side_effect = Exception("auth failed")
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        storage._firestore_client = None
        with pytest.raises(Exception, match="auth failed"):
            get_firestore_client()

    def test_read_firestore_existing(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_client = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"content": "firestore content"}
        mock_client.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.Client.return_value = mock_client
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        monkeypatch.setattr(storage, "STORAGE_TYPE", "firestore")
        storage._firestore_client = None
        result = read_brain_file("test/path.json")
        assert result == "firestore content"

    def test_read_firestore_not_found(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_client = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_client.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.Client.return_value = mock_client
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        monkeypatch.setattr(storage, "STORAGE_TYPE", "firestore")
        storage._firestore_client = None
        with pytest.raises(FileNotFoundError, match="not found"):
            read_brain_file("test/path.json")

    def test_write_firestore(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_client = MagicMock()
        mock_doc_ref = MagicMock()
        mock_client.collection.return_value.document.return_value = mock_doc_ref
        mock_firestore.Client.return_value = mock_client
        mock_firestore.SERVER_TIMESTAMP = "SERVER_TIMESTAMP"
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        monkeypatch.setattr(storage, "STORAGE_TYPE", "firestore")
        storage._firestore_client = None
        write_brain_file("test/path.json", "content")
        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["content"] == "content"
        assert call_args["path"] == "test/path.json"

    def test_brain_file_exists_firestore_true(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_client = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_client.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.Client.return_value = mock_client
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        monkeypatch.setattr(storage, "STORAGE_TYPE", "firestore")
        storage._firestore_client = None
        assert brain_file_exists("test/path.json") is True

    def test_brain_file_exists_firestore_false(self, monkeypatch):
        mock_firestore = MagicMock()
        mock_client = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_client.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.Client.return_value = mock_client
        monkeypatch.setattr(storage, "firestore", mock_firestore)
        monkeypatch.setattr(storage, "STORAGE_TYPE", "firestore")
        storage._firestore_client = None
        assert brain_file_exists("test/path.json") is False
