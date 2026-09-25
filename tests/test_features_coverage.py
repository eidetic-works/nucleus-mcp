"""Coverage tests for mcp_server_nucleus/tools/features.py — the
nucleus_features facade tool (feature tracking, proof, mounter actions)."""
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from mcp_server_nucleus.tools import features


# ── helpers ─────────────────────────────────────────────────────────

def _make_mcp():
    """Create a mock MCP that captures the decorated tool function."""
    captured = {}

    def tool_decorator(*args, **kwargs):
        def wrapper(func):
            captured["func"] = func
            return func
        return wrapper

    mcp = MagicMock()
    mcp.tool = tool_decorator
    mcp._captured = captured
    return mcp


def _run(coro):
    return asyncio.run(coro)


def _make_tf():
    """Register the features facade and return the captured tool function.

    Patches on the underlying runtime impls must be active BEFORE calling
    this, because register() imports them into local scope.
    """
    mcp = _make_mcp()
    make_response = lambda ok, data=None, error=None: json.dumps({"success": ok, "data": data, "error": error})
    helpers = {"make_response": make_response}
    features.register(mcp, helpers)
    return mcp._captured["func"]


# ── register ────────────────────────────────────────────────────────

class TestRegister:
    def test_returns_tool_list(self):
        mcp = _make_mcp()
        helpers = {"make_response": lambda ok, data=None, error=None: "{}"}
        result = features.register(mcp, helpers)
        assert len(result) == 1
        name, func = result[0]
        assert name == "nucleus_features"
        assert asyncio.iscoroutinefunction(func)


# ── _h_add ──────────────────────────────────────────────────────────

class TestHAdd:
    def test_add_without_tags(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._add_feature", return_value={"success": True}) as m:
            tf = _make_tf()
            _run(tf("add", {"product": "p", "name": "n", "description": "d", "source": "s",
                            "version": "v", "how_to_test": "test", "expected_result": "r"}))
        args, kwargs = m.call_args
        assert "tags" not in kwargs

    def test_add_with_tags(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._add_feature", return_value={"success": True}) as m:
            tf = _make_tf()
            _run(tf("add", {"product": "p", "name": "n", "description": "d", "source": "s",
                            "version": "v", "how_to_test": "test", "expected_result": "r",
                            "tags": ["x"]}))
        args, kwargs = m.call_args
        assert kwargs.get("tags") == ["x"]


# ── _h_update ───────────────────────────────────────────────────────

class TestHUpdate:
    def test_update_no_fields(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._update_feature") as m:
            tf = _make_tf()
            _run(tf("update", {"feature_id": "f1"}))
        m.assert_not_called()

    def test_update_with_fields(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._update_feature", return_value={"success": True}) as m:
            tf = _make_tf()
            _run(tf("update", {"feature_id": "f1", "status": "done", "version": "2"}))
        args, kwargs = m.call_args
        assert kwargs == {"status": "done", "version": "2"}


# ── mounter handlers (async) ────────────────────────────────────────

class TestMounterHandlers:
    def test_mount_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_mount_server_impl",
                   new_callable=AsyncMock, return_value="mounted") as m:
            tf = _make_tf()
            r = _run(tf("mount_server", {"name": "srv", "command": "cmd"}))
        m.assert_called_once_with("srv", "cmd", [])

    def test_mount_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_mount_server_impl",
                   new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("mount_server", {"name": "srv", "command": "cmd"}))
        assert '"success": false' in r and "boom" in r  # structured envelope, not an "Error mounting" prefix

    def test_thanos_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_thanos_snap_impl",
                   new_callable=AsyncMock, return_value="snapped"):
            tf = _make_tf()
            r = _run(tf("thanos_snap", {}))
        assert "snapped" in r

    def test_thanos_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_thanos_snap_impl",
                   new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("thanos_snap", {}))
        assert '"success": false' in r and "boom" in r  # structured envelope, not an "Error during Thanos" prefix

    def test_unmount_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_unmount_server_impl",
                   new_callable=AsyncMock, return_value="unmounted"):
            tf = _make_tf()
            r = _run(tf("unmount_server", {"server_id": "s1"}))
        assert "unmounted" in r

    def test_unmount_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_unmount_server_impl",
                   new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("unmount_server", {"server_id": "s1"}))
        assert '"success": false' in r and "boom" in r  # structured envelope, not an "Error unmounting" prefix

    def test_discover_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_discover_mounted_tools_impl",
                   new_callable=AsyncMock, return_value={"tools": []}):
            tf = _make_tf()
            r = _run(tf("discover_tools", {}))
        assert "tools" in r

    def test_discover_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_discover_mounted_tools_impl",
                   new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("discover_tools", {}))
        assert "boom" in r

    def test_invoke_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_invoke_mounted_tool_impl",
                   new_callable=AsyncMock, return_value="result"):
            tf = _make_tf()
            r = _run(tf("invoke_tool", {"server_id": "s1", "tool_name": "t"}))
        assert "result" in r

    def test_invoke_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_invoke_mounted_tool_impl",
                   new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("invoke_tool", {"server_id": "s1", "tool_name": "t"}))
        assert "boom" in r
        assert "success" in r

    def test_traverse_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_traverse_and_mount_impl",
                   new_callable=AsyncMock, return_value="traversed"):
            tf = _make_tf()
            r = _run(tf("traverse_mount", {"root_mount_id": "r1"}))
        assert "traversed" in r

    def test_traverse_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_traverse_and_mount_impl",
                   new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("traverse_mount", {"root_mount_id": "r1"}))
        assert "boom" in r

    def test_list_mounted_success(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_list_mounted_impl",
                   return_value={"servers": []}):
            tf = _make_tf()
            r = _run(tf("list_mounted", {}))
        assert "servers" in r

    def test_list_mounted_exception(self):
        with patch("mcp_server_nucleus.runtime.mounter_ops._brain_list_mounted_impl",
                   side_effect=RuntimeError("boom")):
            tf = _make_tf()
            r = _run(tf("list_mounted", {}))
        assert "boom" in r


# ── proof handlers ──────────────────────────────────────────────────

class TestProofHandlers:
    def test_generate_proof(self):
        with patch("mcp_server_nucleus.runtime.proof_ops._brain_generate_proof_impl",
                   return_value="proof doc") as m:
            tf = _make_tf()
            r = _run(tf("generate_proof", {"feature_id": "f1", "files_changed": ["a.py"]}))
        args, kwargs = m.call_args
        assert args[0] == "f1"
        assert args[3] == ["a.py"]

    def test_get_proof(self):
        with patch("mcp_server_nucleus.runtime.proof_ops._brain_get_proof_impl", return_value="proof") as m:
            tf = _make_tf()
            r = _run(tf("get_proof", {"feature_id": "f1"}))
        m.assert_called_once_with("f1")

    def test_list_proofs(self):
        with patch("mcp_server_nucleus.runtime.proof_ops._brain_list_proofs_impl", return_value=["p1", "p2"]):
            tf = _make_tf()
            r = _run(tf("list_proofs", {}))
        assert "p1" in r


# ── list / get / validate / search ──────────────────────────────────

class TestFeatureCRUD:
    def test_list(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._list_features", return_value={"features": []}) as m:
            tf = _make_tf()
            _run(tf("list", {"product": "p"}))
        args, kwargs = m.call_args
        assert args[0] == "p"

    def test_get(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._get_feature", return_value={"id": "f1"}) as m:
            tf = _make_tf()
            _run(tf("get", {"feature_id": "f1"}))
        m.assert_called_once_with("f1")

    def test_validate(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._mark_validated", return_value={"ok": True}) as m:
            tf = _make_tf()
            _run(tf("validate", {"feature_id": "f1", "result": "passed"}))
        m.assert_called_once_with("f1", "passed")

    def test_search(self):
        with patch("mcp_server_nucleus.runtime.feature_ops._search_features", return_value=[]) as m:
            tf = _make_tf()
            _run(tf("search", {"query": "auth"}))
        m.assert_called_once_with("auth")


# ── unknown action ──────────────────────────────────────────────────

class TestUnknownAction:
    def test_unknown_returns_error(self):
        tf = _make_tf()
        r = _run(tf("nonexistent", {}))
        assert "Unknown action" in r or "error" in r
