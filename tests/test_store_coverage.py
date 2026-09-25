"""Coverage tests for mcp_server_nucleus/rabbithole/store.py — the SQLite
depth-tracker store (depth stack, context switches, open loops, weekly review,
hook state)."""
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from mcp_server_nucleus.rabbithole import store


# ── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "test.db"
    c = store.connect(db)
    yield c
    c.close()


@pytest.fixture
def conn_env(tmp_path, monkeypatch):
    """Connection with env-driven config overrides."""
    monkeypatch.setenv("RABBITHOLE_MAX_DEPTH", "4")
    monkeypatch.setenv("RABBITHOLE_SWITCH_WINDOW_MINUTES", "30")
    monkeypatch.setenv("RABBITHOLE_SWITCH_THRESHOLD", "5")
    db = tmp_path / "test.db"
    c = store.connect(db)
    yield c
    c.close()


# ── paths ───────────────────────────────────────────────────────────

class TestPaths:
    def test_data_dir_xdg(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        d = store.data_dir()
        assert d == tmp_path / "rabbithole"
        assert d.exists()

    def test_data_dir_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        d = store.data_dir()
        assert d == tmp_path / ".local" / "share" / "rabbithole"

    def test_default_db_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        p = store.default_db_path()
        assert p == tmp_path / "rabbithole" / "store.db"


# ── connect / schema ────────────────────────────────────────────────

class TestConnect:
    def test_connect_creates_schema(self, tmp_path):
        c = store.connect(tmp_path / "x.db")
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {r["name"] for r in tables}
        assert {"meta", "frames", "switches", "loops", "hook_state"} <= names
        c.close()

    def test_connect_default_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        c = store.connect()
        assert c is not None
        c.close()

    def test_row_factory(self, conn):
        row = conn.execute("SELECT 1 as val").fetchone()
        assert row["val"] == 1


# ── helpers ─────────────────────────────────────────────────────────

class TestHelpers:
    def test_now_is_utc(self):
        assert store._now().tzinfo == timezone.utc

    def test_iso_roundtrip(self):
        dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        s = store._iso(dt)
        assert "2026-01-01" in s

    def test_parse_naive_adds_utc(self):
        dt = store._parse("2026-01-01T12:00:00")
        assert dt.tzinfo == timezone.utc

    def test_parse_aware_preserves(self):
        dt = store._parse("2026-01-01T12:00:00+02:00")
        assert dt.tzinfo is not None

    def test_meta_get_set(self, conn):
        assert store._meta_get(conn, "k") is None
        store._meta_set(conn, "k", "v")
        assert store._meta_get(conn, "k") == "v"
        store._meta_set(conn, "k", "v2")
        assert store._meta_get(conn, "k") == "v2"

    def test_current_session_creates(self, conn):
        s1 = store.current_session(conn)
        s2 = store.current_session(conn)
        assert s1 == s2
        assert s1.startswith("sess-")

    def test_env_int_default(self, monkeypatch):
        monkeypatch.delenv("X", raising=False)
        assert store._env_int("X", 42) == 42

    def test_env_int_valid(self, monkeypatch):
        monkeypatch.setenv("X", "99")
        assert store._env_int("X", 42) == 99

    def test_env_int_invalid(self, monkeypatch):
        monkeypatch.setenv("X", "notanint")
        assert store._env_int("X", 42) == 42

    def test_config(self, monkeypatch):
        monkeypatch.setenv("RABBITHOLE_MAX_DEPTH", "7")
        monkeypatch.setenv("RABBITHOLE_SWITCH_WINDOW_MINUTES", "15")
        monkeypatch.setenv("RABBITHOLE_SWITCH_THRESHOLD", "3")
        cfg = store.config()
        assert cfg == {"max_depth": 7, "switch_window_minutes": 15, "switch_threshold": 3}


# ── depth status / indicator ────────────────────────────────────────

class TestDepthStatus:
    def test_rabbit_hole(self):
        assert store._depth_status(4, 4) == "RABBIT HOLE"

    def test_danger_zone(self):
        assert store._depth_status(3, 4) == "DANGER ZONE"

    def test_caution(self):
        assert store._depth_status(2, 4) == "CAUTION"

    def test_ok(self):
        assert store._depth_status(1, 4) == "OK"

    def test_caution_min_2(self):
        # max_depth - 2 could be < 2; ensure max(2, ...) kicks in
        assert store._depth_status(1, 3) == "OK"

    def test_indicator_normal(self):
        ind = store._indicator(2, 4)
        assert ind == "[##..]"

    def test_indicator_over_max(self):
        ind = store._indicator(6, 4)
        assert "(!)" in ind

    def test_indicator_zero(self):
        ind = store._indicator(0, 4)
        assert ind == "[....]"


# ── depth_push ──────────────────────────────────────────────────────

class TestDepthPush:
    def test_push_empty_topic(self, conn):
        r = store.depth_push(conn, "")
        assert "error" in r

    def test_push_none_topic(self, conn):
        r = store.depth_push(conn, None)
        assert "error" in r

    def test_push_first(self, conn_env):
        r = store.depth_push(conn_env, "topic1")
        assert r["current_depth"] == 1
        assert r["status"] == "OK"
        assert r["breadcrumbs"] == "topic1"
        assert r["warning"] is None

    def test_push_caution(self, conn_env):
        store.depth_push(conn_env, "t1")
        r = store.depth_push(conn_env, "t2")
        assert r["status"] == "CAUTION"
        assert r["warning"] is not None

    def test_push_danger(self, conn_env):
        store.depth_push(conn_env, "t1")
        store.depth_push(conn_env, "t2")
        r = store.depth_push(conn_env, "t3")
        assert r["status"] == "DANGER ZONE"
        assert "near the edge" in r["warning"]

    def test_push_rabbit_hole(self, conn_env):
        store.depth_push(conn_env, "t1")
        store.depth_push(conn_env, "t2")
        store.depth_push(conn_env, "t3")
        r = store.depth_push(conn_env, "t4")
        assert r["status"] == "RABBIT HOLE"
        assert "RABBIT HOLE" in r["warning"]


# ── depth_pop ───────────────────────────────────────────────────────

class TestDepthPop:
    def test_pop_empty(self, conn_env):
        r = store.depth_pop(conn_env)
        assert r["current_depth"] == 0
        assert "Nothing to pop" in r["message"]

    def test_pop_returns_to_root(self, conn_env):
        store.depth_push(conn_env, "t1")
        store.depth_push(conn_env, "t2")
        r = store.depth_pop(conn_env)
        assert r["popped_topic"] == "t2"
        assert r["returned_to"] == "t1"
        assert r["current_depth"] == 1

    def test_pop_to_root(self, conn_env):
        store.depth_push(conn_env, "t1")
        r = store.depth_pop(conn_env)
        assert r["current_depth"] == 0
        assert r["returned_to"] == "(root)"
        assert r["breadcrumbs"] == "(root)"


# ── depth_show ──────────────────────────────────────────────────────

class TestDepthShow:
    def test_show_empty(self, conn_env):
        r = store.depth_show(conn_env)
        assert r["current_depth"] == 0
        assert "at root" in r["tree"]

    def test_show_with_frames(self, conn_env):
        store.depth_push(conn_env, "t1")
        store.depth_push(conn_env, "t2")
        r = store.depth_show(conn_env)
        assert r["current_depth"] == 2
        assert "t1" in r["tree"]
        assert "t2" in r["tree"]
        assert "<- here" in r["tree"]
        assert r["breadcrumbs"] == "t1 > t2"


# ── depth_map ───────────────────────────────────────────────────────

class TestDepthMap:
    def test_map_empty(self, conn_env):
        r = store.depth_map(conn_env)
        assert r["node_count"] == 0
        assert "START" in r["map"]

    def test_map_with_resurfaced(self, conn_env):
        store.depth_push(conn_env, "t1")
        store.depth_push(conn_env, "t2")
        store.depth_pop(conn_env)
        store.depth_push(conn_env, "t3")
        r = store.depth_map(conn_env)
        assert r["node_count"] == 3
        assert "resurfaced" in r["map"]
        assert "active" in r["map"]
        assert "t3" in r["active_path"]


# ── switch_context ──────────────────────────────────────────────────

class TestSwitchContext:
    def test_switch_empty(self, conn_env):
        r = store.switch_context(conn_env, "")
        assert "error" in r

    def test_switch_first(self, conn_env):
        r = store.switch_context(conn_env, "ctx1")
        assert r["current_context"] == "ctx1"
        assert r["was_switch"] is True
        assert r["switches_in_window"] == 1

    def test_switch_same_noop(self, conn_env):
        store.switch_context(conn_env, "ctx1")
        r = store.switch_context(conn_env, "ctx1")
        assert r["was_switch"] is False
        assert r["switches_in_window"] == 1

    def test_switch_thrash_signal(self, monkeypatch, tmp_path):
        monkeypatch.setenv("RABBITHOLE_SWITCH_THRESHOLD", "2")
        monkeypatch.setenv("RABBITHOLE_SWITCH_WINDOW_MINUTES", "60")
        c = store.connect(tmp_path / "t.db")
        store.switch_context(c, "a")
        store.switch_context(c, "b")
        r = store.switch_context(c, "c")
        assert r["signal"] is not None
        c.close()

    def test_switch_no_thrash(self, conn_env):
        store.switch_context(conn_env, "a")
        r = store.switch_context(conn_env, "b")
        assert r["signal"] is None


# ── loops ───────────────────────────────────────────────────────────

class TestLoops:
    def test_add_loop_empty(self, conn):
        r = store.add_loop(conn, "")
        assert "error" in r

    def test_add_loop_success(self, conn):
        r = store.add_loop(conn, "fix the bug")
        assert r["status"] == "open"
        assert r["id"] == 1
        assert "fix the bug" in r["message"]

    def test_list_loops_open_only(self, conn):
        store.add_loop(conn, "l1")
        store.add_loop(conn, "l2")
        r = store.list_loops(conn)
        assert r["count"] == 2
        assert r["open_count"] == 2

    def test_list_loops_include_closed(self, conn):
        store.add_loop(conn, "l1")
        store.add_loop(conn, "l2")
        store.close_loop(conn, 1)
        r = store.list_loops(conn, include_closed=True)
        assert r["count"] == 2
        assert r["open_count"] == 1

    def test_close_loop_invalid_id(self, conn):
        r = store.close_loop(conn, "abc")
        assert "error" in r

    def test_close_loop_not_found(self, conn):
        r = store.close_loop(conn, 999)
        assert "error" in r

    def test_close_loop_already_closed(self, conn):
        store.add_loop(conn, "l1")
        store.close_loop(conn, 1)
        r = store.close_loop(conn, 1)
        assert r["status"] == "closed"
        assert "already closed" in r["message"]

    def test_close_loop_success(self, conn):
        store.add_loop(conn, "l1")
        r = store.close_loop(conn, 1)
        assert r["status"] == "closed"
        assert "l1" in r["message"]


# ── weekly_review ───────────────────────────────────────────────────

class TestWeeklyReview:
    def test_empty_review(self, conn_env):
        r = store.weekly_review(conn_env)
        assert r["switch_count"] == 0
        assert "No dives recorded" in r["narrative"]
        assert "No open loops" in r["narrative"]

    def test_review_with_activity(self, conn_env):
        store.depth_push(conn_env, "t1")
        store.switch_context(conn_env, "ctx1")
        store.switch_context(conn_env, "ctx2")
        store.switch_context(conn_env, "ctx3")
        store.add_loop(conn_env, "open loop 1")
        r = store.weekly_review(conn_env)
        assert r["switch_count"] == 3
        assert r["distinct_contexts"] == 3
        assert "thrashing" not in r["narrative"] or "bouncing" in r["narrative"]
        assert "Still open" in r["narrative"]
        assert "t1" in r["active_stack"]

    def test_review_with_closed_loops(self, conn_env):
        store.add_loop(conn_env, "l1")
        store.close_loop(conn_env, 1)
        r = store.weekly_review(conn_env)
        assert r["closed_this_week"] == 1
        assert "Closed 1 loop" in r["narrative"]

    def test_review_no_switches(self, conn_env):
        store.depth_push(conn_env, "t1")
        r = store.weekly_review(conn_env)
        assert "nicely focused" in r["narrative"]

    def test_review_many_threads(self, conn_env):
        for i in range(10):
            store.depth_push(conn_env, f"t{i}")
            store.depth_pop(conn_env)
        r = store.weekly_review(conn_env)
        assert "more)" in r["narrative"]

    def test_review_many_open_loops(self, conn_env):
        for i in range(12):
            store.add_loop(conn_env, f"loop {i}")
        r = store.weekly_review(conn_env)
        assert "more" in r["narrative"]


# ── hook state ──────────────────────────────────────────────────────

class TestHookState:
    def test_get_state_missing(self, conn):
        r = store.hook_get_state(conn, "s1")
        assert r == {"depth": 0, "streak": []}

    def test_increment_new(self, conn):
        r = store.hook_increment(conn, "s1", "file.py")
        assert r["depth"] == 1
        assert r["streak"] == ["file.py"]

    def test_increment_existing(self, conn):
        store.hook_increment(conn, "s1", "a.py")
        r = store.hook_increment(conn, "s1", "b.py")
        assert r["depth"] == 2
        assert r["streak"] == ["a.py", "b.py"]

    def test_increment_streak_cap(self, conn):
        for i in range(store._HOOK_STREAK_CAP + 5):
            store.hook_increment(conn, "s1", f"f{i}.py")
        r = store.hook_get_state(conn, "s1")
        assert len(r["streak"]) == store._HOOK_STREAK_CAP

    def test_reset(self, conn):
        store.hook_increment(conn, "s1", "a.py")
        store.hook_reset(conn, "s1")
        r = store.hook_get_state(conn, "s1")
        assert r["depth"] == 0
        assert r["streak"] == []

    def test_reset_when_missing(self, conn):
        # Reset on a session that doesn't exist yet should still work
        store.hook_reset(conn, "new-session")
        r = store.hook_get_state(conn, "new-session")
        assert r["depth"] == 0
