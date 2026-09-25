"""Coverage tests for runtime/fetcher.py."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.fetcher import GitFetcher


def test_init():
    f = GitFetcher()
    assert isinstance(f, GitFetcher)


def test_fetch_success(tmp_path):
    f = GitFetcher()
    dest = tmp_path / "dest"

    def fake_check_call(cmd, **kw):
        if cmd[1] == "clone":
            dest.mkdir(exist_ok=True)
            (dest / ".git").mkdir()
        return 0

    with patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_call", side_effect=fake_check_call), \
         patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_output", return_value=b"abc123\n"), \
         patch("mcp_server_nucleus.runtime.fetcher.shutil.rmtree") as mock_rmtree:
        result = f.fetch("https://example.com/r", dest, "abc123")
        assert result == dest
        mock_rmtree.assert_called()  # called for .git cleanup


def test_fetch_cleans_existing_destination(tmp_path):
    f = GitFetcher()
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "old.txt").write_text("old")

    def fake_check_call(cmd, **kw):
        if cmd[1] == "clone":
            (dest / ".git").mkdir(exist_ok=True)
        return 0

    with patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_call", side_effect=fake_check_call), \
         patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_output", return_value=b"abc123\n"):
        f.fetch("https://example.com/r", dest, "abc123")
        # old file should be gone after cleanup+recreate
        assert not (dest / "old.txt").exists()


def test_fetch_hash_mismatch_raises(tmp_path):
    f = GitFetcher()
    dest = tmp_path / "dest"
    with patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_call", return_value=0), \
         patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_output", return_value=b"different\n"), \
         patch("mcp_server_nucleus.runtime.fetcher.shutil.rmtree"):
        with pytest.raises(ValueError, match="Hash Mismatch"):
            f.fetch("https://example.com/r", dest, "abc123")


def test_fetch_called_process_error_raises_runtime(tmp_path):
    f = GitFetcher()
    dest = tmp_path / "dest"
    err = subprocess.CalledProcessError(1, "git")
    with patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_call", side_effect=err), \
         patch("mcp_server_nucleus.runtime.fetcher.shutil.rmtree"):
        with pytest.raises(RuntimeError, match="Git Command Failed"):
            f.fetch("https://example.com/r", dest, "abc123")


def test_fetch_generic_exception_cleans_destination(tmp_path):
    f = GitFetcher()
    dest = tmp_path / "dest"
    with patch("mcp_server_nucleus.runtime.fetcher.subprocess.check_call", side_effect=Exception("boom")), \
         patch("mcp_server_nucleus.runtime.fetcher.shutil.rmtree") as mock_rmtree:
        with pytest.raises(Exception, match="boom"):
            f.fetch("https://example.com/r", dest, "abc123")
        # destination cleaned up on generic exception
        mock_rmtree.assert_called()
