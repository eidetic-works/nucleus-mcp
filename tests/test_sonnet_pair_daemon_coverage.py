"""Coverage tests for mcp_server_nucleus.runtime.sonnet_pair_daemon."""
import asyncio
import json
import os
import time
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.runtime import sonnet_pair_daemon as spd


@pytest.fixture
def fake_brain(tmp_path, monkeypatch):
    """Set up a fake .brain directory."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "daemon").mkdir()
    (brain / "relay").mkdir()
    (brain / "ops_queue").mkdir()
    monkeypatch.chdir(tmp_path)
    return brain


# ── _brain_root, _daemon_dir, _processed_dir ────────────────────

def test_brain_root(fake_brain):
    assert spd._brain_root() == fake_brain


def test_daemon_dir(fake_brain):
    d = spd._daemon_dir()
    assert d.exists()
    assert d.name == "daemon"


def test_processed_dir(fake_brain):
    d = spd._processed_dir("peer")
    assert d.exists()
    assert d.name == "processed"
    assert d.parent.name == "sonnet_peer"


# ── _ensure_session_id ──────────────────────────────────────────

def test_ensure_session_id(fake_brain):
    sid = spd._ensure_session_id("peer")
    assert len(sid) == 36  # UUID length
    # File should be written
    f = fake_brain / "daemon" / "sonnet_pair_peer.session_id"
    assert f.read_text() == sid


# ── _write_pid ──────────────────────────────────────────────────

def test_write_pid(fake_brain):
    p = spd._write_pid("main")
    assert p.exists()
    assert p.read_text() == str(os.getpid())


# ── _emit ───────────────────────────────────────────────────────

def test_emit_success(fake_brain):
    with mock.patch("mcp_server_nucleus.runtime.event_ops._emit_event") as mock_emit:
        spd._emit("test_event", "test_emitter", {"key": "val"})
        mock_emit.assert_called_once()


def test_emit_failure(fake_brain):
    with mock.patch("mcp_server_nucleus.runtime.event_ops._emit_event", side_effect=Exception("fail")):
        # Should not raise
        spd._emit("test_event", "test_emitter", {"key": "val"})


# ── is_escalate ─────────────────────────────────────────────────

def test_is_escalate_found():
    assert spd.is_escalate("founder decision", "") is True
    assert spd.is_escalate("", "git push force") is True
    assert spd.is_escalate("DISPUTE about design", "") is True


def test_is_escalate_not_found():
    assert spd.is_escalate("normal delegate task", "just do the work") is False
    assert spd.is_escalate("", "") is False


def test_is_escalate_case_insensitive():
    assert spd.is_escalate("FOUNDER", "") is True
    assert spd.is_escalate("", "BUDGET BREACH") is True


# ── parse_envelope ──────────────────────────────────────────────

def test_parse_envelope_valid(tmp_path):
    f = tmp_path / "env.json"
    f.write_text(json.dumps({"id": "m1", "subject": "test"}))
    result = spd.parse_envelope(f)
    assert result["id"] == "m1"


def test_parse_envelope_invalid(tmp_path):
    f = tmp_path / "env.json"
    f.write_text("not json")
    result = spd.parse_envelope(f)
    assert result is None


# ── list_pending ────────────────────────────────────────────────

def test_list_pending_empty(fake_brain):
    with mock.patch("mcp_server_nucleus.runtime.relay_ops._iter_inbox_dirs", return_value=[]):
        result = spd.list_pending("peer")
    assert result == []


def test_list_pending_with_files(fake_brain):
    inbox = fake_brain / "relay" / "sonnet_peer" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "msg1.json").write_text("{}")
    (inbox / "msg2.json").write_text("{}")
    (inbox / ".hidden").write_text("{}")
    processed = inbox / "processed"
    processed.mkdir()
    (processed / "old.json").write_text("{}")
    with mock.patch.object(spd, "_iter_inbox_dirs", return_value=[inbox]):
        result = spd.list_pending("peer")
    assert len(result) == 2
    names = [p.name for p in result]
    assert "msg1.json" in names
    assert "msg2.json" in names


# ── archive ─────────────────────────────────────────────────────

def test_archive_success(fake_brain):
    src = fake_brain / "relay" / "sonnet_peer" / "msg.json"
    src.parent.mkdir(parents=True)
    src.write_text("{}")
    spd.archive(src, "peer")
    assert not src.exists()
    assert (fake_brain / "relay" / "sonnet_peer" / "processed" / "msg.json").exists()


def test_archive_failure(fake_brain, tmp_path):
    src = tmp_path / "nonexistent.json"
    # Should not raise
    spd.archive(src, "peer")


# ── parent_lane_for ─────────────────────────────────────────────

def test_parent_lane_for_claude_code():
    env = {"from": "claude_code_main"}
    assert spd.parent_lane_for(env) == "claude_code_main"


def test_parent_lane_for_other():
    env = {"from": "some_other_sender"}
    assert spd.parent_lane_for(env) == "claude_code_main"


def test_parent_lane_for_empty():
    env = {}
    assert spd.parent_lane_for(env) == "claude_code_main"


# ── _spawn_via_claude_code ──────────────────────────────────────

def test_spawn_via_claude_code_success(tmp_path):
    charter = tmp_path / "charter.md"
    charter.write_text("charter")
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="result", stderr="")
        success, output = spd._spawn_via_claude_code(charter, "do work")
    assert success is True
    assert output == "result"


def test_spawn_via_claude_code_failure(tmp_path):
    charter = tmp_path / "charter.md"
    charter.write_text("charter")
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=1, stdout="", stderr="error")
        success, output = spd._spawn_via_claude_code(charter, "do work")
    assert success is False
    assert "rc=1" in output


def test_spawn_via_claude_code_timeout(tmp_path):
    import subprocess
    charter = tmp_path / "charter.md"
    charter.write_text("charter")
    with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)):
        success, output = spd._spawn_via_claude_code(charter, "do work")
    assert success is False
    assert "timeout" in output


def test_spawn_via_claude_code_not_found(tmp_path):
    charter = tmp_path / "charter.md"
    charter.write_text("charter")
    with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
        success, output = spd._spawn_via_claude_code(charter, "do work")
    assert success is False
    assert "not found" in output


# ── _BusyTracker ────────────────────────────────────────────────

def test_busy_tracker_initial():
    bt = spd._BusyTracker()
    assert bt.busy_pct() == 0.0


def test_busy_tracker_with_events():
    bt = spd._BusyTracker()
    now = time.time()
    bt.add(now - 1800, 600)  # 10 min event 30 min ago
    pct = bt.busy_pct(now=now)
    assert pct > 0
    assert pct <= 100


def test_busy_tracker_old_events_evicted():
    bt = spd._BusyTracker()
    now = time.time()
    bt.add(now - 7200, 100)  # 2 hours ago, outside window
    pct = bt.busy_pct(now=now)
    assert pct == 0.0


# ── handle_one ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_one_non_delegate(fake_brain):
    env = {"id": "m1", "subject": "normal subject", "body": "hello", "from": "cc"}
    bt = spd._BusyTracker()
    with mock.patch.object(spd, "relay_post") as mock_post:
        await spd.handle_one(env, "peer", Path("/charter"), "sid", "sender", bt)
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_handle_one_escalate(fake_brain):
    env = {"id": "m1", "subject": "[DELEGATE] founder decision", "body": "do something", "from": "cc"}
    bt = spd._BusyTracker()
    with mock.patch.object(spd, "relay_post") as mock_post:
        await spd.handle_one(env, "peer", Path("/charter"), "sid", "sender", bt)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "[ESCALATE]" in call_kwargs["subject"]


@pytest.mark.asyncio
async def test_handle_one_lateral_ok(fake_brain):
    env = {"id": "m1", "subject": "[DELEGATE] normal task", "body": "just do it", "from": "cc"}
    bt = spd._BusyTracker()
    with mock.patch.object(spd, "_spawn_via_claude_code", return_value=(True, "done")):
        with mock.patch.object(spd, "_emit"):
            with mock.patch.object(spd, "relay_post") as mock_post:
                await spd.handle_one(env, "peer", Path("/charter"), "sid", "sender", bt)
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args.kwargs
                assert "[DELEGATE-RESULT]" in call_kwargs["subject"]


@pytest.mark.asyncio
async def test_handle_one_spawn_fails(fake_brain):
    env = {"id": "m1", "subject": "[DELEGATE] normal task", "body": "just do it", "from": "cc"}
    bt = spd._BusyTracker()
    with mock.patch.object(spd, "_spawn_via_claude_code", return_value=(False, "error")):
        with mock.patch.object(spd, "_emit"):
            with mock.patch.object(spd, "relay_post") as mock_post:
                await spd.handle_one(env, "peer", Path("/charter"), "sid", "sender", bt)
                mock_post.assert_called_once()
                assert mock_post.call_args.kwargs["priority"] == "high"


# ── _ops_queue_dir, list_pending_ops, _archive_ops ──────────────

def test_ops_queue_dir(fake_brain):
    d = spd._ops_queue_dir()
    assert d.exists()
    assert d.name == "ops_queue"


def test_list_pending_ops_empty(fake_brain):
    with mock.patch("mcp_server_nucleus.runtime.relay_ops._get_relay_dir", return_value=fake_brain / "nonexistent"):
        result = spd.list_pending_ops()
    assert result == []


def test_list_pending_ops_with_files(fake_brain):
    inbox = fake_brain / "relay" / "claude_code_operator_assistant"
    inbox.mkdir(parents=True)
    (inbox / "ops1.json").write_text("{}")
    with mock.patch("mcp_server_nucleus.runtime.relay_ops._get_relay_dir", return_value=inbox):
        result = spd.list_pending_ops()
    assert len(result) == 1


def test_archive_ops_success(fake_brain):
    inbox = fake_brain / "relay" / "ops"
    inbox.mkdir(parents=True)
    f = inbox / "msg.json"
    f.write_text("{}")
    spd._archive_ops(f)
    assert not f.exists()
    assert (inbox / "processed" / "msg.json").exists()


def test_archive_ops_failure(tmp_path):
    f = tmp_path / "nonexistent.json"
    # Should not raise
    spd._archive_ops(f)


# ── _notify_macos ───────────────────────────────────────────────

def test_notify_macos_non_darwin():
    with mock.patch("platform.system", return_value="Linux"):
        # Should be noop
        spd._notify_macos("title", "message")


def test_notify_macos_darwin_no_osascript():
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("shutil.which", return_value=None):
            spd._notify_macos("title", "message")


def test_notify_macos_darwin_with_osascript():
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("shutil.which", return_value="/usr/bin/osascript"):
            with mock.patch("subprocess.run") as mock_run:
                spd._notify_macos("title", "message")
                mock_run.assert_called_once()


def test_notify_macos_exception():
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("shutil.which", return_value="/usr/bin/osascript"):
            with mock.patch("subprocess.run", side_effect=Exception("fail")):
                # Should not raise
                spd._notify_macos("title", "message")


# ── handle_ops_handoff ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_ops_handoff_non_ops(fake_brain):
    env = {"id": "m1", "subject": "normal subject", "body": "hello", "from": "cc"}
    with mock.patch.object(spd, "_emit") as mock_emit:
        await spd.handle_ops_handoff(env, "sid")
        mock_emit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_ops_handoff_success(fake_brain):
    env = {"id": "m1", "subject": "[OPS-HANDOFF] do something", "body": "the brief", "from": "cc"}
    with mock.patch.object(spd, "_emit"):
        with mock.patch.object(spd, "_notify_macos"):
            await spd.handle_ops_handoff(env, "sid")
    # File should be written to ops_queue
    files = list((fake_brain / "ops_queue").glob("*.md"))
    assert len(files) == 1


@pytest.mark.asyncio
async def test_handle_ops_handoff_write_fails(fake_brain):
    env = {"id": "m1", "subject": "[OPS-HANDOFF] do something", "body": "the brief", "from": "cc"}
    with mock.patch.object(spd, "_emit"):
        with mock.patch.object(spd, "_notify_macos"):
            with mock.patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
                # Should not raise (write error is caught)
                await spd.handle_ops_handoff(env, "sid")


# ── main ────────────────────────────────────────────────────────

def test_main_no_args():
    result = spd.main([])
    assert result == 1


def test_main_help():
    result = spd.main(["--help"])
    assert result == 1


def test_main_invalid_lane():
    with mock.patch("logging.basicConfig"):
        result = spd.main(["invalid_lane"])
    # run() returns 2 for invalid lane
    assert result == 2


# ── Additional coverage tests ────────────────────────────────────

def test_list_pending_nonexistent_dir(fake_brain):
    """Test list_pending when inbox dir doesn't exist (line 122)."""
    with mock.patch.object(spd, "_iter_inbox_dirs", return_value=[fake_brain / "nonexistent"]):
        result = spd.list_pending("peer")
    assert result == []


def test_list_pending_skips_processed_and_dotfiles(fake_brain):
    """Test list_pending skips processed/ and dotfiles (line 125)."""
    inbox = fake_brain / "relay" / "sonnet_peer" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "msg1.json").write_text("{}")
    (inbox / ".hidden.json").write_text("{}")
    processed = inbox / "processed"
    processed.mkdir()
    (processed / "old.json").write_text("{}")
    acks = inbox / "acks"
    acks.mkdir()
    (acks / "ack1.json").write_text("{}")
    with mock.patch.object(spd, "_iter_inbox_dirs", return_value=[inbox]):
        result = spd.list_pending("peer")
    assert len(result) == 1
    assert result[0].name == "msg1.json"


def test_list_pending_ops_skips_dotfiles(fake_brain):
    """Test list_pending_ops skips dotfiles and processed (line 345)."""
    inbox = fake_brain / "relay" / "claude_code_operator_assistant"
    inbox.mkdir(parents=True)
    (inbox / "ops1.json").write_text("{}")
    (inbox / ".hidden.json").write_text("{}")
    processed = inbox / "processed"
    processed.mkdir()
    (processed / "old.json").write_text("{}")
    with mock.patch("mcp_server_nucleus.runtime.relay_ops._get_relay_dir", return_value=inbox):
        result = spd.list_pending_ops()
    assert len(result) == 1
    assert result[0].name == "ops1.json"


@pytest.mark.asyncio
async def test_heartbeat_loop_one_iteration(fake_brain):
    """Test heartbeat_loop emits one heartbeat then stops."""
    bt = spd._BusyTracker()
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "_emit") as mock_emit:
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.heartbeat_loop("peer", "sonnet_peer", "sid", bt, 12345)
    mock_emit.assert_called_once()


@pytest.mark.asyncio
async def test_poll_loop_one_cycle(fake_brain):
    """Test poll_loop processes one cycle then stops."""
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending", return_value=[]):
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.poll_loop("peer", Path("/charter"), "sonnet_peer", "sid", spd._BusyTracker())


@pytest.mark.asyncio
async def test_poll_loop_with_envelope(fake_brain):
    """Test poll_loop processes an envelope."""
    inbox = fake_brain / "relay" / "sonnet_peer" / "inbox"
    inbox.mkdir(parents=True)
    env_file = inbox / "msg1.json"
    env_file.write_text(json.dumps({"id": "m1", "subject": "test", "body": "hello", "from": "cc"}))

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending", return_value=[env_file]):
        with mock.patch.object(spd, "handle_one", new_callable=mock.AsyncMock):
            with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await spd.poll_loop("peer", Path("/charter"), "sonnet_peer", "sid", spd._BusyTracker())


@pytest.mark.asyncio
async def test_poll_loop_with_invalid_envelope(fake_brain):
    """Test poll_loop archives invalid envelope."""
    inbox = fake_brain / "relay" / "sonnet_peer" / "inbox"
    inbox.mkdir(parents=True)
    processed = fake_brain / "relay" / "sonnet_peer" / "processed"
    processed.mkdir(parents=True)
    env_file = inbox / "bad.json"
    env_file.write_text("not json")

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending", return_value=[env_file]):
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.poll_loop("peer", Path("/charter"), "sonnet_peer", "sid", spd._BusyTracker())
    # File should be archived
    assert not env_file.exists()


@pytest.mark.asyncio
async def test_poll_loop_handler_exception(fake_brain):
    """Test poll_loop catches handler exception."""
    inbox = fake_brain / "relay" / "sonnet_peer" / "inbox"
    inbox.mkdir(parents=True)
    processed = fake_brain / "relay" / "sonnet_peer" / "processed"
    processed.mkdir(parents=True)
    env_file = inbox / "msg1.json"
    env_file.write_text(json.dumps({"id": "m1", "subject": "test", "body": "hello", "from": "cc"}))

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending", return_value=[env_file]):
        with mock.patch.object(spd, "handle_one", side_effect=Exception("handler fail")):
            with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await spd.poll_loop("peer", Path("/charter"), "sonnet_peer", "sid", spd._BusyTracker())


@pytest.mark.asyncio
async def test_poll_loop_operator_assistant_one_cycle(fake_brain):
    """Test poll_loop_operator_assistant processes one cycle."""
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending_ops", return_value=[]):
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.poll_loop_operator_assistant("sid")


@pytest.mark.asyncio
async def test_poll_loop_operator_assistant_with_envelope(fake_brain):
    """Test poll_loop_operator_assistant processes an envelope."""
    inbox = fake_brain / "relay" / "claude_code_operator_assistant"
    inbox.mkdir(parents=True)
    processed = inbox / "processed"
    processed.mkdir()
    env_file = inbox / "ops1.json"
    env_file.write_text(json.dumps({"id": "m1", "subject": "[OPS-HANDOFF] do something", "body": "brief", "from": "cc"}))

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending_ops", return_value=[env_file]):
        with mock.patch.object(spd, "_notify_macos"):
            with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await spd.poll_loop_operator_assistant("sid")


@pytest.mark.asyncio
async def test_poll_loop_operator_assistant_invalid_envelope(fake_brain):
    """Test poll_loop_operator_assistant archives invalid envelope."""
    inbox = fake_brain / "relay" / "claude_code_operator_assistant"
    inbox.mkdir(parents=True)
    processed = inbox / "processed"
    processed.mkdir()
    env_file = inbox / "bad.json"
    env_file.write_text("not json")

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending_ops", return_value=[env_file]):
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.poll_loop_operator_assistant("sid")
    assert not env_file.exists()


@pytest.mark.asyncio
async def test_poll_loop_operator_assistant_handler_exception(fake_brain):
    """Test poll_loop_operator_assistant catches handler exception."""
    inbox = fake_brain / "relay" / "claude_code_operator_assistant"
    inbox.mkdir(parents=True)
    processed = inbox / "processed"
    processed.mkdir()
    env_file = inbox / "ops1.json"
    env_file.write_text(json.dumps({"id": "m1", "subject": "[OPS-HANDOFF] do something", "body": "brief", "from": "cc"}))

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending_ops", return_value=[env_file]):
        with mock.patch.object(spd, "handle_ops_handoff", side_effect=Exception("handler fail")):
            with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await spd.poll_loop_operator_assistant("sid")


@pytest.mark.asyncio
async def test_run_operator_assistant(fake_brain):
    """Test run() with operator_assistant lane."""
    stop_event = asyncio.Event()
    stop_event.set()

    with mock.patch.object(spd, "_write_pid"):
        with mock.patch.object(spd, "_ensure_session_id", return_value="test-sid"):
            with mock.patch.object(asyncio, "Event", return_value=stop_event):
                with mock.patch.object(spd, "poll_loop_operator_assistant", new_callable=mock.AsyncMock):
                    result = await spd.run("operator_assistant")
    assert result == 0


@pytest.mark.asyncio
async def test_run_peer_lane(fake_brain):
    """Test run() with peer lane."""
    # Create charter
    charter_dir = fake_brain.parent / "docs" / "org" / "charters"
    charter_dir.mkdir(parents=True)
    charter = charter_dir / "sonnet_pair_peer.md"
    charter.write_text("charter")

    stop_event = asyncio.Event()
    stop_event.set()

    with mock.patch.object(spd, "_write_pid"):
        with mock.patch.object(spd, "_ensure_session_id", return_value="test-sid"):
            with mock.patch.object(asyncio, "Event", return_value=stop_event):
                with mock.patch.object(spd, "poll_loop", new_callable=mock.AsyncMock):
                    with mock.patch.object(spd, "heartbeat_loop", new_callable=mock.AsyncMock):
                        result = await spd.run("peer")
    assert result == 0


@pytest.mark.asyncio
async def test_run_main_lane(fake_brain):
    """Test run() with main lane."""
    charter_dir = fake_brain.parent / "docs" / "org" / "charters"
    charter_dir.mkdir(parents=True)
    charter = charter_dir / "sonnet_pair_main.md"
    charter.write_text("charter")

    stop_event = asyncio.Event()
    stop_event.set()

    with mock.patch.object(spd, "_write_pid"):
        with mock.patch.object(spd, "_ensure_session_id", return_value="test-sid"):
            with mock.patch.object(asyncio, "Event", return_value=stop_event):
                with mock.patch.object(spd, "poll_loop", new_callable=mock.AsyncMock):
                    with mock.patch.object(spd, "heartbeat_loop", new_callable=mock.AsyncMock):
                        result = await spd.run("main")
    assert result == 0


@pytest.mark.asyncio
async def test_run_missing_charter(fake_brain):
    """Test run() with missing charter returns 3."""
    with mock.patch("logging.basicConfig"):
        result = await spd.run("peer")
    assert result == 3


def test_main_module_block():
    """Test __main__ block execution.

    timeout was 5s and the module needs ~5.5s just to reach its own usage error
    (measured 5.13s / 5.79s / 5.92s over three consecutive runs) -- importing
    mcp_server_nucleus is what costs it. So this failed essentially always, and
    it looked like a broken __main__ block rather than a too-tight clock.

    Raised well clear of that, and switched to sys.executable: bare "python3"
    resolves off PATH, which need not be the interpreter running the tests or
    the one that can import this package.
    """
    import subprocess
    import sys as _sys
    result = subprocess.run(
        [_sys.executable, "-m", "mcp_server_nucleus.runtime.sonnet_pair_daemon"],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 1
    assert "usage" in result.stderr


@pytest.mark.asyncio
async def test_poll_loop_outer_exception(fake_brain):
    """Test poll_loop catches outer exception (lines 324-325)."""
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending", side_effect=Exception("list fail")):
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.poll_loop("peer", Path("/charter"), "sonnet_peer", "sid", spd._BusyTracker())


@pytest.mark.asyncio
async def test_poll_loop_operator_assistant_outer_exception(fake_brain):
    """Test poll_loop_operator_assistant catches outer exception (lines 435-436)."""
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch.object(spd, "list_pending_ops", side_effect=Exception("list fail")):
        with mock.patch.object(asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(asyncio.CancelledError):
                await spd.poll_loop_operator_assistant("sid")


@pytest.mark.asyncio
async def test_run_peer_signal_not_implemented(fake_brain):
    """Test run() handles NotImplementedError for signal handlers (lines 473-474)."""
    charter_dir = fake_brain.parent / "docs" / "org" / "charters"
    charter_dir.mkdir(parents=True)
    charter = charter_dir / "sonnet_pair_peer.md"
    charter.write_text("charter")

    stop_event = asyncio.Event()
    stop_event.set()

    mock_loop = mock.MagicMock()
    mock_loop.add_signal_handler.side_effect = NotImplementedError("not supported")

    with mock.patch.object(spd, "_write_pid"):
        with mock.patch.object(spd, "_ensure_session_id", return_value="test-sid"):
            with mock.patch.object(asyncio, "Event", return_value=stop_event):
                with mock.patch.object(spd, "poll_loop", new_callable=mock.AsyncMock):
                    with mock.patch.object(spd, "heartbeat_loop", new_callable=mock.AsyncMock):
                        with mock.patch("asyncio.get_running_loop", return_value=mock_loop):
                            result = await spd.run("peer")
    assert result == 0


@pytest.mark.asyncio
async def test_run_operator_assistant_signal_not_implemented(fake_brain):
    """Test _run_operator_assistant handles NotImplementedError for signal handlers (lines 515-516)."""
    stop_event = asyncio.Event()
    stop_event.set()

    mock_loop = mock.MagicMock()
    mock_loop.add_signal_handler.side_effect = NotImplementedError("not supported")

    with mock.patch.object(spd, "_write_pid"):
        with mock.patch.object(spd, "_ensure_session_id", return_value="test-sid"):
            with mock.patch.object(asyncio, "Event", return_value=stop_event):
                with mock.patch.object(spd, "poll_loop_operator_assistant", new_callable=mock.AsyncMock):
                    with mock.patch("asyncio.get_running_loop", return_value=mock_loop):
                        result = await spd.run("operator_assistant")
    assert result == 0
