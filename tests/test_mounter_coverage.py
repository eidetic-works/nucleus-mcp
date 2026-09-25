"""Comprehensive coverage tests for runtime/mounter.py.

Tests MountedServer (start/stop/call_tool/list_tools incl. error & timeout
paths) and RecursiveMounter (mount/unmount/list_mounted/load/save + security
checks). All subprocess I/O is mocked — no real processes are spawned.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import mounter as mounter_mod
from mcp_server_nucleus.runtime.mounter import (
    MountedServer,
    RecursiveMounter,
    get_mounter,
)


# ---------------------------------------------------------------------------
# Helpers — fake asyncio subprocess
# ---------------------------------------------------------------------------
def _fake_writer():
    """Return a mock stdin with async write/drain."""
    stdin = MagicMock()
    stdin.write = MagicMock()
    stdin.drain = AsyncMock(return_value=None)
    return stdin


def _fake_stdout(lines: list[bytes]):
    """Return a mock stdout whose readline returns queued lines then EOF."""
    stdout = MagicMock()
    # Each call to readline returns an AsyncMock; queue via side_effect
    async def _readline():
        if lines:
            return lines.pop(0)
        return b""
    stdout.readline = _readline
    return stdout


def _make_process(stdin=None, stdout=None, returncode=None):
    proc = MagicMock()
    proc.stdin = stdin or _fake_writer()
    proc.stdout = stdout or _fake_stdout([b'{"jsonrpc":"2.0","result":{}}\n'])
    proc.returncode = returncode
    proc.terminate = MagicMock()
    proc.wait = AsyncMock(return_value=0)
    return proc


# ---------------------------------------------------------------------------
# MountedServer
# ---------------------------------------------------------------------------
class TestMountedServerInit:
    def test_defaults(self):
        s = MountedServer(name="srv", command="echo", args=["hi"])
        assert s.name == "srv"
        assert s.command == "echo"
        assert s.args == ["hi"]
        assert s.process is None
        assert s.mounted_at == 0.0
        assert s.tools == []
        assert s.id.startswith("mnt-")


class TestMountedServerStart:
    def test_start_sets_process_and_time(self):
        s = MountedServer("srv", "echo", ["hi"])
        fake_proc = _make_process()
        with patch("mcp_server_nucleus.runtime.mounter.asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=fake_proc)) as mock_exec:
            loop = asyncio.new_event_loop()
            try:
                # need running loop time
                result = loop.run_until_complete(s.start())
            finally:
                loop.close()
        assert result is True
        assert s.process is fake_proc
        assert s.mounted_at > 0.0
        mock_exec.assert_awaited_once()


class TestMountedServerStop:
    def test_stop_no_process_is_noop(self):
        s = MountedServer("srv", "echo", ["hi"])
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(s.stop())
        finally:
            loop.close()
        assert s.process is None

    def test_stop_terminates_process(self):
        s = MountedServer("srv", "echo", ["hi"])
        proc = _make_process()
        s.process = proc
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(s.stop())
        finally:
            loop.close()
        proc.terminate.assert_called_once()
        proc.wait.assert_awaited_once()


class TestMountedServerCallTool:
    def test_call_tool_not_running_raises(self):
        s = MountedServer("srv", "echo", ["hi"])
        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(RuntimeError, match="not running"):
                loop.run_until_complete(s.call_tool("t", {}))
        finally:
            loop.close()

    def test_call_tool_success(self):
        s = MountedServer("srv", "echo", ["hi"])
        resp = {"jsonrpc": "2.0", "result": {"ok": True}}
        stdout = _fake_stdout([json.dumps(resp).encode() + b"\n"])
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(s.call_tool("t", {"a": 1}))
        finally:
            loop.close()
        assert result == resp
        s.process.stdin.write.assert_called()

    def test_call_tool_no_response(self):
        s = MountedServer("srv", "echo", ["hi"])
        stdout = _fake_stdout([])  # EOF immediately
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(s.call_tool("t", {}))
        finally:
            loop.close()
        assert result == {"success": False, "error": "No response from mounted server"}


class TestMountedServerListTools:
    def test_list_tools_not_running_returns_empty(self):
        s = MountedServer("srv", "echo", ["hi"])
        loop = asyncio.new_event_loop()
        try:
            assert loop.run_until_complete(s.list_tools()) == []
        finally:
            loop.close()

    def test_list_tools_success(self):
        s = MountedServer("srv", "echo", ["hi"])
        resp = {"jsonrpc": "2.0", "result": {"tools": [{"name": "t1"}]}}
        stdout = _fake_stdout([json.dumps(resp).encode() + b"\n"])
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            tools = loop.run_until_complete(s.list_tools())
        finally:
            loop.close()
        assert tools == [{"name": "t1"}]
        assert s.tools == [{"name": "t1"}]

    def test_list_tools_empty_response(self):
        s = MountedServer("srv", "echo", ["hi"])
        stdout = _fake_stdout([b"\n"])  # empty line -> json.loads fails? Actually b"\n" -> b"" after? no
        # readline returns b"\n"; json.loads(b"\n".decode()) raises -> Exception path
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            tools = loop.run_until_complete(s.list_tools())
        finally:
            loop.close()
        assert tools == []

    def test_list_tools_no_result_key(self):
        s = MountedServer("srv", "echo", ["hi"])
        resp = {"jsonrpc": "2.0", "error": "x"}
        stdout = _fake_stdout([json.dumps(resp).encode() + b"\n"])
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            tools = loop.run_until_complete(s.list_tools())
        finally:
            loop.close()
        assert tools == []

    def test_list_tools_result_no_tools_key(self):
        s = MountedServer("srv", "echo", ["hi"])
        resp = {"jsonrpc": "2.0", "result": {}}
        stdout = _fake_stdout([json.dumps(resp).encode() + b"\n"])
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            tools = loop.run_until_complete(s.list_tools())
        finally:
            loop.close()
        assert tools == []

    def test_list_tools_timeout(self):
        s = MountedServer("srv", "echo", ["hi"])
        s.process = _make_process()
        loop = asyncio.new_event_loop()
        try:
            with patch("mcp_server_nucleus.runtime.mounter.asyncio.wait_for",
                       new=AsyncMock(side_effect=asyncio.TimeoutError)):
                tools = loop.run_until_complete(s.list_tools())
        finally:
            loop.close()
        assert tools == []

    def test_list_tools_eof_returns_empty(self):
        s = MountedServer("srv", "echo", ["hi"])
        stdout = _fake_stdout([])  # b"" -> empty
        s.process = _make_process(stdout=stdout)
        loop = asyncio.new_event_loop()
        try:
            tools = loop.run_until_complete(s.list_tools())
        finally:
            loop.close()
        assert tools == []


# ---------------------------------------------------------------------------
# RecursiveMounter
# ---------------------------------------------------------------------------
class TestRecursiveMounter:
    def test_init_creates_dirs(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        assert (tmp_path / "ledger" / "mounts.json").parent.exists()
        assert m.mounted_servers == {}

    def test_load_mounts_no_file(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        assert m.mounted_servers == {}

    def test_load_mounts_from_file(self, tmp_path):
        mounts_file = tmp_path / "ledger" / "mounts.json"
        mounts_file.parent.mkdir(parents=True, exist_ok=True)
        data = [{"id": "mnt-abc", "name": "srv", "command": "echo", "args": ["hi"]}]
        mounts_file.write_text(json.dumps(data))
        m = RecursiveMounter(tmp_path)
        assert "mnt-abc" in m.mounted_servers
        assert m.mounted_servers["mnt-abc"].name == "srv"
        assert m.mounted_servers["mnt-abc"].id == "mnt-abc"

    def test_load_mounts_invalid_json(self, tmp_path):
        mounts_file = tmp_path / "ledger" / "mounts.json"
        mounts_file.parent.mkdir(parents=True, exist_ok=True)
        mounts_file.write_text("not json")
        m = RecursiveMounter(tmp_path)
        assert m.mounted_servers == {}

    def test_save_mounts(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        s = MountedServer("srv", "echo", ["hi"])
        s.id = "mnt-xyz"
        m.mounted_servers[s.id] = s
        m._save_mounts()
        data = json.loads(m.mounts_file.read_text())
        assert data == [{"id": "mnt-xyz", "name": "srv", "command": "echo", "args": ["hi"]}]

    def test_mount_short_name_rejected(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.mount("a", "echo", []))
        finally:
            loop.close()
        assert "must be at least 2 characters" in res

    def test_mount_empty_name_rejected(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.mount("", "echo", []))
        finally:
            loop.close()
        assert "must be at least 2 characters" in res

    def test_mount_recursive_self_mount_blocked(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.mount("evil", "mcp_server_nucleus", []))
        finally:
            loop.close()
        assert "forbidden" in res

    def test_mount_recursive_self_mount_blocked_dash(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.mount("evil", "python", ["-m", "mcp-server-nucleus"]))
        finally:
            loop.close()
        assert "forbidden" in res

    def test_mount_duplicate_name(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        existing = MountedServer("dup", "echo", ["hi"])
        existing.id = "mnt-1"
        m.mounted_servers[existing.id] = existing
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.mount("dup", "echo", ["hi"]))
        finally:
            loop.close()
        assert "already mounted" in res

    def test_mount_success(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        fake_proc = _make_process()
        with patch("mcp_server_nucleus.runtime.mounter.asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=fake_proc)):
            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(m.mount("mysrv", "echo", ["hi"]))
            finally:
                loop.close()
        assert "Successfully mounted" in res
        assert len(m.mounted_servers) == 1
        # saved to disk
        assert m.mounts_file.exists()

    def test_mount_start_failure(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        with patch("mcp_server_nucleus.runtime.mounter.asyncio.create_subprocess_exec",
                   new=AsyncMock(side_effect=OSError("boom"))):
            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(m.mount("mysrv", "echo", ["hi"]))
            finally:
                loop.close()
        assert "Failed to mount" in res
        assert "boom" in res

    def test_unmount_not_found(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.unmount("nope"))
        finally:
            loop.close()
        assert "not found" in res

    def test_unmount_success(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        s = MountedServer("srv", "echo", ["hi"])
        s.id = "mnt-1"
        s.process = _make_process()
        m.mounted_servers[s.id] = s
        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(m.unmount("mnt-1"))
        finally:
            loop.close()
        assert "Unmounted" in res
        assert "mnt-1" not in m.mounted_servers
        s.process.terminate.assert_called_once()

    def test_list_mounted_empty(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        assert m.list_mounted() == []

    def test_list_mounted_running(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        s = MountedServer("srv", "echo", ["hi"])
        s.id = "mnt-1"
        proc = _make_process(returncode=None)
        s.process = proc
        m.mounted_servers[s.id] = s
        listed = m.list_mounted()
        assert listed == [{"id": "mnt-1", "name": "srv", "command": "echo", "status": "Running"}]

    def test_list_mounted_stopped(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        s = MountedServer("srv", "echo", ["hi"])
        s.id = "mnt-1"
        s.process = None
        m.mounted_servers[s.id] = s
        listed = m.list_mounted()
        assert listed[0]["status"] == "Stopped"

    def test_list_mounted_stopped_with_returncode(self, tmp_path):
        m = RecursiveMounter(tmp_path)
        s = MountedServer("srv", "echo", ["hi"])
        s.id = "mnt-1"
        proc = _make_process(returncode=0)  # exited
        s.process = proc
        m.mounted_servers[s.id] = s
        listed = m.list_mounted()
        assert listed[0]["status"] == "Stopped"


# ---------------------------------------------------------------------------
# get_mounter singleton
# ---------------------------------------------------------------------------
class TestGetMounter:
    def test_creates_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mounter_mod, "_mounter", None)
        m1 = get_mounter(tmp_path)
        m2 = get_mounter(tmp_path)
        assert m1 is m2
