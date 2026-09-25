"""Session attribution on engram write — opposed pairs.

Measured on the live corpus 2026-09-20, and the reason this file exists:

* ``~/nucleus/.brain/engrams/history.jsonl`` holds 30,813 rows. Exactly 26
  carry ``snapshot.origin.session``, and all 26 come from a DIFFERENT product
  sharing the brain, using ``<pid>-<epoch>`` ids -- a different id space from
  Claude transcript UUIDs. So the Claude branch of ``_origin`` has never once
  fired.
* It never fired because it read ``CLAUDE_SESSION_ID``. The variable Claude
  Code actually exports is ``CLAUDE_CODE_SESSION_ID``.
* Fixing only the name would have been WORSE than the bug. The live MCP server
  process (pid 67640, 8.6h old) carried ``CLAUDE_CODE_SESSION_ID`` belonging to
  a different, older session: MCP servers outlive the session that spawned them
  (two others were 3 days old with the variable absent entirely). Env-derived
  attribution in that process stamps every write with one stale id, which
  collapses a distinct-session count to 1 -- a confident wrong number where
  there had been an honest blank.

So the rule these tests encode: a session id is recorded only when it can be
justified. An explicit, per-call id is trustworthy. An env-derived one is
recorded but MARKED, and the prevalence counter refuses to count it rather than
report a collapsed number.
"""

import json
import os

import pytest

from nucleus_wedge.store import Store


def _rows(brain):
    path = brain / "engrams" / "history.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _origin_of(brain, key):
    for row in _rows(brain):
        if row.get("key") == key:
            return (row.get("snapshot") or {}).get("origin") or {}
    raise AssertionError(f"no row written for {key!r}")


@pytest.fixture(autouse=True)
def _clear_origin_cache():
    """The cache is process-global; a leaked entry would fake every result."""
    from nucleus_wedge import store as store_mod

    store_mod._ORIGIN_CACHE = None
    yield
    store_mod._ORIGIN_CACHE = None


# --- MUST RECORD -----------------------------------------------------------

def test_explicit_session_is_recorded_and_marked_trustworthy(tmp_path):
    store = Store(tmp_path)
    store.append(value="v", key="k1", session="11111111-2222-3333-4444-555555555555")
    origin = _origin_of(tmp_path, "k1")
    assert origin["session"] == "11111111-2222-3333-4444-555555555555"
    assert origin["session_source"] == "explicit"


def test_reads_the_variable_claude_code_actually_exports(tmp_path, monkeypatch):
    """The whole bug in one line: the old code read CLAUDE_SESSION_ID."""
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "env-session-aaaa")
    store = Store(tmp_path)
    store.append(value="v", key="k2")
    origin = _origin_of(tmp_path, "k2")
    assert origin["session"] == "env-session-aaaa"


def test_env_derived_session_is_marked_env_not_explicit(tmp_path, monkeypatch):
    """Only in a LONG-LIVED writer; a short-lived one's env is current."""
    from nucleus_wedge import store as store_mod

    monkeypatch.setattr(store_mod, "_LONG_LIVED", True)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "env-session-bbbb")
    store = Store(tmp_path)
    store.append(value="v", key="k3")
    assert _origin_of(tmp_path, "k3")["session_source"] == "env"


# --- MUST NOT (the broken inputs) ------------------------------------------

def test_second_write_in_one_process_does_not_inherit_the_first_session(tmp_path):
    """THE staleness bug, in miniature.

    ``_ORIGIN_CACHE`` froze the session for the life of the process. In a
    3-day-old MCP server that means every row ever written carries whichever
    session happened to spawn it. A long-lived writer serves many sessions, so
    the session half of origin must never be cached.
    """
    store = Store(tmp_path)
    store.append(value="v", key="a", session="session-one")
    store.append(value="v", key="b", session="session-two")
    assert _origin_of(tmp_path, "a")["session"] == "session-one"
    assert _origin_of(tmp_path, "b")["session"] == "session-two", (
        "the second write inherited the first write's session: origin is cached"
    )


def test_explicit_session_overrides_a_stale_env_value(tmp_path, monkeypatch):
    """Reproduces the live MCP server: env holds someone else's session."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "9f4b0d5f-stale-server-env")
    store = Store(tmp_path)
    store.append(value="v", key="k4", session="the-real-caller")
    origin = _origin_of(tmp_path, "k4")
    assert origin["session"] == "the-real-caller"
    assert origin["session_source"] == "explicit"


def test_a_write_with_no_session_available_still_succeeds(tmp_path, monkeypatch):
    """Legacy permissiveness: origin must never be able to fail a write."""
    for var in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID", "NUCLEUS_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    store = Store(tmp_path)
    store.append(value="v", key="k5")
    origin = _origin_of(tmp_path, "k5")
    assert origin.get("session") is None
    assert origin.get("session_source") is None


def test_legacy_rows_without_origin_session_remain_readable(tmp_path):
    """The corpus has 30,787 such rows. They must not become unreadable."""
    store = Store(tmp_path)
    store.append(value="old", key="legacy")
    path = tmp_path / "engrams" / "history.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    rows[0]["snapshot"]["origin"] = {"repo": "nucleus"}  # pre-fix shape
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert Store(tmp_path).head_value("legacy") == "old"
    Store(tmp_path).append(value="new", key="legacy")  # must not raise


# --- THE CONSUMER: prevalence must refuse, not collapse --------------------

def test_prevalence_counts_explicit_sessions(tmp_path):
    """Positive control: prove the instrument can emit a non-zero count."""
    from mcp_server_nucleus.flywheel.prevalence import scan_engrams

    store = Store(tmp_path)
    store.append(value="widget exploded", key="x1", session="s-1")
    store.append(value="widget exploded", key="x2", session="s-2")
    result = scan_engrams("widget exploded", history_path=tmp_path / "engrams" / "history.jsonl")
    assert result.sessions_matched == 2
    assert result.complete is True


def test_prevalence_refuses_to_count_env_derived_sessions(tmp_path, monkeypatch):
    """A stale env id would collapse thousands of rows to one session.

    The counter must report INSUFFICIENT rather than a confident 1.
    """
    from mcp_server_nucleus.flywheel.prevalence import scan_engrams

    from nucleus_wedge import store as store_mod

    monkeypatch.setattr(store_mod, "_LONG_LIVED", True)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "9f4b0d5f-stale")
    store = Store(tmp_path)
    store.append(value="widget exploded", key="y1")
    store.append(value="widget exploded", key="y2")
    result = scan_engrams("widget exploded", history_path=tmp_path / "engrams" / "history.jsonl")
    assert result.unattributed_matches == 2
    assert result.complete is False
    assert "INSUFFICIENT" in result.summary()


# --- process lifetime decides whether env can be trusted -------------------

def test_short_lived_process_env_is_trustworthy(tmp_path, monkeypatch):
    """A CLI invocation inherits the CURRENT session's environment.

    This is what makes the fix live rather than merely available: a write from
    a tool-call subprocess is attributed without anyone passing anything.
    """
    from nucleus_wedge import store as store_mod

    monkeypatch.setattr(store_mod, "_LONG_LIVED", False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "fresh-cli-session")
    Store(tmp_path).append(value="v", key="cli")
    origin = _origin_of(tmp_path, "cli")
    assert origin["session"] == "fresh-cli-session"
    assert origin["session_source"] == "explicit"


def test_long_lived_server_env_is_not_trustworthy(tmp_path, monkeypatch):
    """The opposed half: same env, same code, one flag, different verdict."""
    from nucleus_wedge import store as store_mod

    monkeypatch.setattr(store_mod, "_LONG_LIVED", True)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "stale-server-session")
    Store(tmp_path).append(value="v", key="srv")
    origin = _origin_of(tmp_path, "srv")
    assert origin["session"] == "stale-server-session"
    assert origin["session_source"] == "env"


def test_building_the_mcp_server_declares_it_long_lived(monkeypatch):
    """The flag is worthless unless the real server actually sets it."""
    from nucleus_wedge import store as store_mod
    from nucleus_wedge.server import build_server

    monkeypatch.setattr(store_mod, "_LONG_LIVED", False)
    build_server()
    assert store_mod._LONG_LIVED is True
