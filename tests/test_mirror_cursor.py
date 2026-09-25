"""Tests for the Cursor watcher + parser surface.

Covers:
- Parser handles single + multi + empty + malformed + missing-key Cursor JSONs
- Parser tolerates heterogenous response shapes (list-of-dicts, plain string,
  list-of-strings)
- Watcher emits EngramEvents only for chatSessions/*.json files
- Watcher delta tracking: re-handling the same file twice = no duplicate events
- Watcher throttles excess events per workspace
- Watcher safely handles directory events + non-json suffixes
- ``default_cursor_root()`` derives path from Path.home() (no hardcoded user)
"""

from __future__ import annotations

import json
import pathlib
import shutil
from queue import Queue
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.mirror.cursor_watcher import (
    MAX_EVENTS_PER_SEC_PER_WORKSPACE,
    CursorEventHandler,
    CursorWatcher,
    default_cursor_root,
)
from mcp_server_nucleus.mirror.parsers import EngramEvent
from mcp_server_nucleus.mirror.parsers.cursor import parse_session_file

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "parsers" / "cursor"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parser_single_request_yields_user_and_assistant():
    events = list(parse_session_file(FIXTURES / "single_request.json"))
    assert len(events) == 2
    roles = [e.role for e in events]
    assert roles == ["user", "assistant"]
    assert all(e.surface == "cursor" for e in events)
    assert events[0].content == "what is 2+2"
    # Response is concatenated from list-of-{value:...} fragments
    assert events[1].content == "It is four."


def test_parser_session_id_extracted():
    events = list(parse_session_file(FIXTURES / "single_request.json"))
    assert events[0].session_id == "00000000-0000-0000-0000-000000000001"


def test_parser_timestamp_iso_format():
    events = list(parse_session_file(FIXTURES / "single_request.json"))
    # creationDate is 1716000000000 ms → 2024-05-18T03:20:00+00:00 UTC
    assert events[0].timestamp is not None
    assert events[0].timestamp.startswith("2024-")


def test_parser_multi_request_yields_six_events():
    """3 requests × (user + assistant) = 6 events."""
    events = list(parse_session_file(FIXTURES / "multi_request.json"))
    assert len(events) == 6


def test_parser_response_as_plain_string():
    events = list(parse_session_file(FIXTURES / "multi_request.json"))
    second_pair = [e for e in events if e.extra.get("request_id") == "request_222"]
    assistant = [e for e in second_pair if e.role == "assistant"][0]
    assert assistant.content == "second reply as string"


def test_parser_message_as_plain_string():
    events = list(parse_session_file(FIXTURES / "multi_request.json"))
    third_pair = [e for e in events if e.extra.get("request_id") == "request_333"]
    user = [e for e in third_pair if e.role == "user"][0]
    assert user.content == "third prompt as raw string"


def test_parser_empty_requests_yields_nothing():
    events = list(parse_session_file(FIXTURES / "empty_requests.json"))
    assert events == []


def test_parser_malformed_json_yields_nothing():
    """Malformed JSON should not raise, just yield nothing.

    The fixture is named ``malformed.json.broken`` so the repo pre-commit
    json_parse tier doesn't try to validate it as JSON — the whole point of
    this fixture is that it's intentionally invalid.
    """
    events = list(parse_session_file(FIXTURES / "malformed.json.broken"))
    assert events == []


def test_parser_missing_requests_key_yields_nothing():
    events = list(parse_session_file(FIXTURES / "missing_requests.json"))
    assert events == []


def test_parser_nonexistent_file_yields_nothing():
    events = list(parse_session_file(FIXTURES / "does-not-exist.json"))
    assert events == []


def test_parser_request_index_in_extra():
    events = list(parse_session_file(FIXTURES / "multi_request.json"))
    indices = sorted({e.extra["request_index"] for e in events})
    assert indices == [0, 1, 2]


def test_parser_workspace_extracted_from_chatSessions_path(tmp_path):
    """Workspace hash = the parent of the chatSessions/ dir."""
    workspace_dir = tmp_path / "fakehash123" / "chatSessions"
    workspace_dir.mkdir(parents=True)
    src = FIXTURES / "single_request.json"
    target = workspace_dir / src.name
    shutil.copy(src, target)
    events = list(parse_session_file(target))
    assert events[0].workspace == "fakehash123"


def test_default_cursor_root_uses_home_not_hardcoded(monkeypatch, tmp_path):
    """Pseudonymity contract: root must derive from Path.home()."""
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    root = default_cursor_root()
    assert str(tmp_path) in str(root)
    # Must NOT contain a hardcoded build-time username — confirm the patched
    # home is the only Users-path component present.
    import re
    user_segments = re.findall(r"/Users/([^/]+)", str(root))
    assert all(seg == tmp_path.parts[-1] for seg in user_segments), (
        f"Unexpected hardcoded user segment in {root!r}"
    )


# ---------------------------------------------------------------------------
# Handler / Watcher tests
# ---------------------------------------------------------------------------


def _make_fs_event(src_path: str, is_dir: bool = False, dest_path: str = None):
    e = MagicMock()
    e.src_path = src_path
    e.is_directory = is_dir
    if dest_path is not None:
        e.dest_path = dest_path
    else:
        # Use sentinel to indicate absence
        del e.dest_path
    return e


def test_handler_ignores_directory_events():
    q: Queue = Queue()
    h = CursorEventHandler(q)
    h.on_modified(_make_fs_event("/tmp/some_dir", is_dir=True))
    assert q.empty()


def test_handler_ignores_non_json_suffix():
    q: Queue = Queue()
    h = CursorEventHandler(q)
    h.on_modified(_make_fs_event("/tmp/somewhere/chatSessions/file.txt"))
    assert q.empty()


def test_handler_ignores_json_outside_chatSessions(tmp_path):
    q: Queue = Queue()
    h = CursorEventHandler(q)
    # JSON file but not in chatSessions/ dir
    other = tmp_path / "other_dir"
    other.mkdir()
    f = other / "data.json"
    shutil.copy(FIXTURES / "single_request.json", f)
    h.on_modified(_make_fs_event(str(f)))
    assert q.empty()


def test_handler_emits_events_for_chatSessions_json(tmp_path):
    q: Queue = Queue()
    h = CursorEventHandler(q)
    session_dir = tmp_path / "wshash" / "chatSessions"
    session_dir.mkdir(parents=True)
    f = session_dir / "session.json"
    shutil.copy(FIXTURES / "single_request.json", f)
    h.on_modified(_make_fs_event(str(f)))
    # Drain
    items = []
    while not q.empty():
        items.append(q.get_nowait())
    assert len(items) == 2
    assert {i.role for i in items} == {"user", "assistant"}


def test_handler_delta_tracking_no_duplicates(tmp_path):
    """Calling handler twice on the same unchanged file = no duplicates."""
    q: Queue = Queue()
    h = CursorEventHandler(q)
    session_dir = tmp_path / "wshash" / "chatSessions"
    session_dir.mkdir(parents=True)
    f = session_dir / "session.json"
    shutil.copy(FIXTURES / "single_request.json", f)
    h.on_modified(_make_fs_event(str(f)))
    first_count = q.qsize()
    h.on_modified(_make_fs_event(str(f)))
    assert q.qsize() == first_count


def test_handler_delta_emits_new_request_after_edit(tmp_path):
    """If a new request is appended to the JSON, only the new one is emitted."""
    q: Queue = Queue()
    h = CursorEventHandler(q)
    session_dir = tmp_path / "wshash" / "chatSessions"
    session_dir.mkdir(parents=True)
    f = session_dir / "session.json"

    # Start with single-request fixture
    data = json.loads((FIXTURES / "single_request.json").read_text())
    f.write_text(json.dumps(data))
    h.on_modified(_make_fs_event(str(f)))
    initial = q.qsize()

    # Append another request
    data["requests"].append({
        "requestId": "request_added",
        "message": {"text": "new prompt"},
        "response": [{"value": "new reply"}],
    })
    f.write_text(json.dumps(data))
    h.on_modified(_make_fs_event(str(f)))
    after = q.qsize()
    assert after - initial == 2  # new user + new assistant


def test_handler_throttle_drops_excess(tmp_path):
    """With cap=2, only 2 events emit before throttle kicks in."""
    q: Queue = Queue()
    h = CursorEventHandler(q, throttle_cap=2)
    session_dir = tmp_path / "wshash" / "chatSessions"
    session_dir.mkdir(parents=True)
    f = session_dir / "session.json"
    # 3 requests = 6 events; cap=2 keeps 2
    shutil.copy(FIXTURES / "multi_request.json", f)
    h.on_modified(_make_fs_event(str(f)))
    assert q.qsize() == 2


def test_handler_on_moved_handles_dest_path(tmp_path):
    q: Queue = Queue()
    h = CursorEventHandler(q)
    session_dir = tmp_path / "wshash" / "chatSessions"
    session_dir.mkdir(parents=True)
    f = session_dir / "session.json"
    shutil.copy(FIXTURES / "single_request.json", f)
    # Simulate moved event
    e = MagicMock()
    e.src_path = "/tmp/somewhere/old.json"
    e.dest_path = str(f)
    e.is_directory = False
    h.on_moved(e)
    assert q.qsize() == 2


def test_watcher_construct_with_custom_root(tmp_path):
    """Watcher can take any root for testing without watching the real Cursor dir."""
    q: Queue = Queue()
    w = CursorWatcher(q, root=tmp_path)
    assert w.root == tmp_path
    assert w.queue is q


def test_watcher_skips_start_when_root_missing(tmp_path):
    """Non-existent root = warning + no observer started."""
    q: Queue = Queue()
    missing = tmp_path / "definitely-not-here"
    w = CursorWatcher(q, root=missing)
    # Should not raise
    w.start()
    w.stop()


def test_watcher_emit_for_path_test_helper(tmp_path):
    """The emit_for_path test helper produces same results as a real event."""
    q: Queue = Queue()
    w = CursorWatcher(q, root=tmp_path)
    session_dir = tmp_path / "wshash" / "chatSessions"
    session_dir.mkdir(parents=True)
    f = session_dir / "session.json"
    shutil.copy(FIXTURES / "single_request.json", f)
    w.emit_for_path(f)
    assert q.qsize() == 2


def test_handler_per_workspace_throttle_independent(tmp_path):
    """Throttle is per-workspace: hitting cap for ws-A doesn't affect ws-B."""
    q: Queue = Queue()
    h = CursorEventHandler(q, throttle_cap=2)

    for ws in ("wsA", "wsB"):
        d = tmp_path / ws / "chatSessions"
        d.mkdir(parents=True)
        f = d / "session.json"
        shutil.copy(FIXTURES / "multi_request.json", f)
        h.on_modified(_make_fs_event(str(f)))

    # 2 from wsA + 2 from wsB = 4 total
    assert q.qsize() == 4
