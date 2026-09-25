"""Comprehensive tests for mcp_server_nucleus.rabbithole.server.

Covers all MCP tool functions: depth_push, depth_pop, depth_show,
depth_map, switch_context, add_loop, list_loops, close_loop,
focus_start, focus_status, focus_resolve, weekly_review, and main.
"""
from unittest.mock import patch

import pytest

from mcp_server_nucleus.rabbithole import server
from mcp_server_nucleus.rabbithole import store


@pytest.fixture
def db_path(tmp_path):
    """Create a temp DB path. Server functions open/close their own
    connections via _conn(), so we patch _conn to return a fresh
    connection from this path each time."""
    path = tmp_path / "test.db"
    conn = store.connect(path)
    conn.close()
    return path


@pytest.fixture
def patched_conn(db_path):
    """Patch server._conn to return a fresh connection to the temp DB."""
    connections = []

    def _make_conn():
        conn = store.connect(db_path)
        connections.append(conn)
        return conn

    with patch.object(server, "_conn", side_effect=_make_conn):
        yield db_path
    for c in connections:
        try:
            c.close()
        except Exception:
            pass


class TestDepthPush:
    def test_success(self, patched_conn):
        result = server.depth_push("topic1")
        assert "depth 1/" in result
        assert "topic1" in result

    def test_error(self, patched_conn):
        with patch.object(store, "depth_push", return_value={"error": "bad topic"}):
            result = server.depth_push("")
        assert "Error: bad topic" in result

    def test_warning_at_max_depth(self, patched_conn):
        with patch.dict("os.environ", {"RABBITHOLE_MAX_DEPTH": "2"}):
            server.depth_push("t1")
            result = server.depth_push("t2")
        assert "RABBIT HOLE" in result or "warning" in result.lower() or "DANGER" in result


class TestDepthPop:
    def test_success(self, patched_conn):
        server.depth_push("topic1")
        result = server.depth_pop()
        assert "Resurfaced" in result

    def test_pop_empty(self, patched_conn):
        result = server.depth_pop()
        assert "root" in result.lower()

    def test_error(self, patched_conn):
        with patch.object(store, "depth_pop", return_value={"error": "fail"}):
            result = server.depth_pop()
        assert "Error: fail" in result


class TestDepthShow:
    def test_empty_stack(self, patched_conn):
        result = server.depth_show()
        assert "depth 0/" in result
        assert "root" in result

    def test_with_frames(self, patched_conn):
        server.depth_push("t1")
        server.depth_push("t2")
        result = server.depth_show()
        assert "t1" in result
        assert "t2" in result
        assert "here" in result

    def test_error(self, patched_conn):
        with patch.object(store, "depth_show", return_value={"error": "fail"}):
            result = server.depth_show()
        assert "Error: fail" in result


class TestDepthMap:
    def test_empty(self, patched_conn):
        result = server.depth_map()
        assert "no dives yet" in result or "START" in result

    def test_with_dives(self, patched_conn):
        server.depth_push("t1")
        result = server.depth_map()
        assert "START" in result
        assert "t1" in result

    def test_error(self, patched_conn):
        with patch.object(store, "depth_map", return_value={"error": "fail"}):
            result = server.depth_map()
        assert "Error: fail" in result


class TestSwitchContext:
    def test_success(self, patched_conn):
        result = server.switch_context("task1")
        assert "task1" in result
        assert "Switches in last" in result

    def test_error(self, patched_conn):
        with patch.object(store, "switch_context", return_value={"error": "bad"}):
            result = server.switch_context("")
        assert "Error: bad" in result

    def test_with_signal(self, patched_conn):
        with patch.dict("os.environ", {"RABBITHOLE_SWITCH_THRESHOLD": "1"}):
            server.switch_context("t1")
            result = server.switch_context("t2")
        assert "switch" in result.lower() or "paus" in result.lower() or "threshold" in result


class TestAddLoop:
    def test_success(self, patched_conn):
        result = server.add_loop("my open loop")
        assert "opened" in result

    def test_error(self, patched_conn):
        with patch.object(store, "add_loop", return_value={"error": "bad"}):
            result = server.add_loop("")
        assert "Error: bad" in result


class TestListLoops:
    def test_empty(self, patched_conn):
        result = server.list_loops()
        assert "No loops" in result

    def test_with_loops(self, patched_conn):
        server.add_loop("loop1")
        server.add_loop("loop2")
        result = server.list_loops()
        assert "loop1" in result
        assert "loop2" in result
        assert "Open loops: 2" in result

    def test_include_closed(self, patched_conn):
        server.add_loop("loop1")
        server.close_loop(1)
        result = server.list_loops(include_closed=True)
        assert "[x]" in result

    def test_error(self, patched_conn):
        with patch.object(store, "list_loops", return_value={"error": "bad"}):
            result = server.list_loops()
        assert "Error: bad" in result


class TestCloseLoop:
    def test_success(self, patched_conn):
        server.add_loop("loop1")
        result = server.close_loop(1)
        assert "closed" in result

    def test_error(self, patched_conn):
        with patch.object(store, "close_loop", return_value={"error": "bad"}):
            result = server.close_loop(999)
        assert "Error: bad" in result


class TestFocusContracts:
    def test_start_status_and_resolve(self, patched_conn):
        started = server.focus_start(
            "Should we change this?",
            "A tested decision",
            3,
            2,
            "Select a valid exit",
            "server-session",
        )
        status = server.focus_status("server-session")
        resolved = server.focus_resolve(
            "ACT",
            "The regression test passes",
            session_id="server-session",
        )

        assert "active" in started
        assert "Should we change this?" in status
        assert "evidence remaining 3/3" in status
        assert "resolved: ACT" in resolved
        assert "No active focus contract" in server.focus_status("server-session")

    def test_start_error(self, patched_conn):
        with patch.object(store, "focus_start", return_value={"error": "bad"}):
            result = server.focus_start("q", "d", 1, 1, "exit")
        assert result == "Error: bad"

    def test_status_error(self, patched_conn):
        with patch.object(store, "focus_status", return_value={"error": "bad"}):
            result = server.focus_status()
        assert result == "Error: bad"

    def test_resolve_error(self, patched_conn):
        with patch.object(store, "focus_resolve", return_value={"error": "bad"}):
            result = server.focus_resolve("ACT", "evidence")
        assert result == "Error: bad"


class TestWeeklyReview:
    def test_empty(self, patched_conn):
        result = server.weekly_review()
        assert "Weekly review" in result

    def test_with_data(self, patched_conn):
        server.depth_push("topic1")
        server.switch_context("ctx1")
        server.add_loop("loop1")
        result = server.weekly_review()
        assert "Weekly review" in result

    def test_error(self, patched_conn):
        with patch.object(store, "weekly_review", return_value={"error": "bad"}):
            result = server.weekly_review()
        assert "Error: bad" in result


class TestMain:
    def test_main_calls_run(self, monkeypatch):
        # main() reads sys.argv[1:] directly, so under pytest it sees pytest's
        # OWN arguments, takes the unknown-argument branch and exits 2. The
        # test must pin argv; without it this asserts nothing about main().
        monkeypatch.setattr(server.sys, "argv", ["rabbithole"])
        with patch.object(server.mcp, "run") as mock_run:
            server.main()
        mock_run.assert_called_once()

    def test_main_rejects_unknown_argument(self, monkeypatch):
        """OPPOSED: argv IS still read, so a bad argument must still exit 2.
        Pinning argv above must not turn the parser into a no-op."""
        monkeypatch.setattr(server.sys, "argv", ["rabbithole", "--nonsense"])
        with patch.object(server.mcp, "run") as mock_run:
            with pytest.raises(SystemExit) as exc:
                server.main()
        assert exc.value.code == 2
        mock_run.assert_not_called()
