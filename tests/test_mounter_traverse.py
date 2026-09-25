"""Regression tests for nucleus_features `traverse_mount` action.

Bug: `features.py` referenced `_brain_traverse_and_mount_impl` from
`mounter_ops`, but that module-level function did not exist — only the
`Mounter.traverse_and_mount()` method did. Every `traverse_mount` call
raised `ImportError`. These tests pin the fix: the impl must be importable
and must surface a structured response (never an ImportError).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


def test_traverse_impl_is_importable():
    """Regression: the module-level impl must exist (was missing → ImportError)."""
    from mcp_server_nucleus.runtime.mounter_ops import _brain_traverse_and_mount_impl
    assert callable(_brain_traverse_and_mount_impl)


@pytest.mark.asyncio
async def test_traverse_unknown_root_returns_graceful_error(tmp_path, monkeypatch):
    """Unknown root mount → structured failure, not an unhandled crash."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    from mcp_server_nucleus.runtime import mounter_ops

    # Ensure a clean singleton so prior tests don't leak mounted sessions.
    mounter_ops._mounter = None

    out = await mounter_ops._brain_traverse_and_mount_impl("does-not-exist")
    parsed = json.loads(out)
    assert parsed["success"] is False
    assert parsed["error"]  # non-empty message
    # The Mounter raises ValueError("Root mount '...' not found") for unknown roots.
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_traverse_success_wraps_result(tmp_path, monkeypatch):
    """Successful traversal returns make_response(True, data=<traverse dict>)."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    from mcp_server_nucleus.runtime import mounter_ops

    fake_result = {
        "root": "root1",
        "potential_sub_servers": ["mount_server"],
        "status": "traversal_complete",
    }
    fake_mounter = AsyncMock()
    fake_mounter.traverse_and_mount = AsyncMock(return_value=fake_result)

    with patch.object(mounter_ops, "get_mounter", return_value=fake_mounter):
        out = await mounter_ops._brain_traverse_and_mount_impl("root1")

    parsed = json.loads(out)
    assert parsed["success"] is True
    assert parsed["data"] == fake_result
    fake_mounter.traverse_and_mount.assert_awaited_once_with("root1")
