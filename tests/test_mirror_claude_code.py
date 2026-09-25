"""Tests for the Claude Code JSONL watcher + parser surface.

Covers:
- Parser handles user, assistant, attachment, queue-operation, last-prompt,
  and unknown envelope types
- Parser preserves content blocks (text, thinking, tool_use)
- Parser skips empty + malformed lines silently
- READ-ONLY contract: parser never opens the file in write mode
- Watcher emits deltas only (append-only JSONL semantics)
- Watcher throttle per project-slug
- ``default_claude_code_root()`` derives from Path.home() (no hardcoded user)
"""

from __future__ import annotations

import os
import pathlib
import shutil
import stat
from queue import Queue
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.mirror.claude_code_watcher import (
    MAX_EVENTS_PER_SEC_PER_PROJECT,
    ClaudeCodeEventHandler,
    ClaudeCodeWatcher,
    default_claude_code_root,
)
from mcp_server_nucleus.mirror.parsers import EngramEvent
from mcp_server_nucleus.mirror.parsers.claude_code import parse_session_file

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "parsers" / "claude_code"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parser_basic_session_yields_expected_events():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    # u1 (user), a1 (assistant text), u2 (user list), a2 (assistant
    # thinking+tool_use), u3 (user tool_result)
    # queue-operation + last-prompt are skipped.
    assert len(events) == 5
    roles = [e.role for e in events]
    assert roles == ["user", "assistant", "user", "assistant", "user"]


def test_parser_extracts_string_user_content():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    assert events[0].content == "hello assistant"
    assert events[0].surface == "claude_code"


def test_parser_extracts_list_user_content():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    # u2 has content as list-of-text-blocks
    assert events[2].content == "call a tool"


def test_parser_extracts_assistant_text_block():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    assert events[1].content == "hello user"


def test_parser_summarizes_tool_use():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    a2 = events[3]
    assert "[thinking]" in a2.content
    assert "[tool_use: Bash(" in a2.content


def test_parser_includes_tool_result_in_user_content():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    u3 = events[4]
    assert "[tool_result]" in u3.content
    assert "file1.txt" in u3.content


def test_parser_includes_model_in_extra():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    a1 = events[1]
    assert a1.extra.get("model") == "claude-opus-4-7"


def test_parser_session_id_extracted():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    assert all(e.session_id == "sess-1" for e in events)


def test_parser_attachment_emits_system_event():
    events = list(parse_session_file(FIXTURES / "with_attachment.jsonl"))
    attachments = [e for e in events if e.role == "system"]
    assert len(attachments) == 1
    assert "screenshot.png" in attachments[0].content


def test_parser_empty_file_yields_nothing():
    events = list(parse_session_file(FIXTURES / "empty.jsonl"))
    assert events == []


def test_parser_skips_malformed_lines_continues_parsing():
    """Malformed lines should be skipped silently; subsequent valid lines parsed."""
    events = list(parse_session_file(FIXTURES / "malformed_lines.jsonl"))
    # First user line + final assistant line should both parse
    assert len(events) == 2
    assert events[0].content == "first valid line"
    assert events[1].content == "after the malformed lines"


def test_parser_unknown_envelope_type_emits_system_event():
    """Forward compatibility: unknown 'type' values become system events."""
    events = list(parse_session_file(FIXTURES / "unknown_type.jsonl"))
    assert len(events) == 2
    assert all(e.role == "system" for e in events)
    assert events[0].extra["envelope_type"] == "future-event-type"


def test_parser_nonexistent_file_yields_nothing():
    events = list(parse_session_file(FIXTURES / "does-not-exist.jsonl"))
    assert events == []


def test_default_root_uses_home_not_hardcoded(monkeypatch, tmp_path):
    """Pseudonymity contract."""
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    root = default_claude_code_root()
    assert str(tmp_path) in str(root)
    import re
    user_segments = re.findall(r"/Users/([^/]+)", str(root))
    assert all(seg == tmp_path.parts[-1] for seg in user_segments), (
        f"Unexpected hardcoded user segment in {root!r}"
    )


def test_default_root_is_dot_claude_projects(monkeypatch, tmp_path):
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    root = default_claude_code_root()
    assert root.name == "projects"
    assert root.parent.name == ".claude"


def test_parser_does_not_write_to_file(tmp_path):
    """READ-ONLY contract: parser must not modify the source file."""
    src = FIXTURES / "basic_session.jsonl"
    target = tmp_path / "session.jsonl"
    shutil.copy(src, target)
    before_mtime = target.stat().st_mtime
    before_content = target.read_bytes()

    # Mark file read-only via permissions
    target.chmod(0o400)
    try:
        events = list(parse_session_file(target))
        assert len(events) > 0  # Parser still worked
        # File unchanged
        assert target.read_bytes() == before_content
    finally:
        target.chmod(0o600)  # Restore for cleanup


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
        del e.dest_path
    return e


def test_handler_ignores_non_jsonl_suffix():
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    h.on_modified(_make_fs_event("/tmp/projects/foo/session.json"))
    assert q.empty()


def test_handler_emits_for_jsonl(tmp_path):
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "session-abc.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_modified(_make_fs_event(str(f)))
    # 5 events expected
    assert q.qsize() == 5


def test_handler_delta_no_duplicates_on_same_file(tmp_path):
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_modified(_make_fs_event(str(f)))
    first = q.qsize()
    h.on_modified(_make_fs_event(str(f)))
    assert q.qsize() == first


def test_handler_emits_only_appended_lines(tmp_path):
    """JSONL is append-only; new lines = new events, old lines stay seen."""
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_modified(_make_fs_event(str(f)))
    initial = q.qsize()

    # Append two new lines
    appended = (
        '{"type":"user","uuid":"u4","sessionId":"sess-1","timestamp":"2026-05-21T11:00:00Z",'
        '"message":{"role":"user","content":"appended user"}}\n'
        '{"type":"assistant","uuid":"a4","sessionId":"sess-1","timestamp":"2026-05-21T11:00:01Z",'
        '"message":{"role":"assistant","content":[{"type":"text","text":"appended reply"}]}}\n'
    )
    with f.open("a") as fp:
        fp.write(appended)
    h.on_modified(_make_fs_event(str(f)))
    final = q.qsize()
    assert final - initial == 2


def test_handler_throttle_drops_excess(tmp_path):
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q, throttle_cap=3)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_modified(_make_fs_event(str(f)))
    # 5 events available, cap=3
    assert q.qsize() == 3


def test_handler_per_project_throttle_independent(tmp_path):
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q, throttle_cap=2)
    for slug in ("proj-A", "proj-B"):
        d = tmp_path / slug
        d.mkdir()
        f = d / "session.jsonl"
        shutil.copy(FIXTURES / "basic_session.jsonl", f)
        h.on_modified(_make_fs_event(str(f)))
    # 2 from each project = 4 total (cap=2 each)
    assert q.qsize() == 4


def test_handler_ignores_directory_events():
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    h.on_modified(_make_fs_event("/some/dir", is_dir=True))
    assert q.empty()


def test_handler_handles_on_created_event(tmp_path):
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "new-session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_created(_make_fs_event(str(f)))
    assert q.qsize() == 5


def test_watcher_construct_and_emit_helper(tmp_path):
    q: Queue = Queue()
    w = ClaudeCodeWatcher(q, root=tmp_path)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    w.emit_for_path(f)
    assert q.qsize() == 5


def test_watcher_skips_start_when_root_missing(tmp_path):
    q: Queue = Queue()
    missing = tmp_path / "no-claude"
    w = ClaudeCodeWatcher(q, root=missing)
    w.start()
    w.stop()


def test_handler_does_not_open_file_for_write(tmp_path, monkeypatch):
    """Belt-and-braces: assert parser open()s file with read-only mode only."""
    q: Queue = Queue()
    h = ClaudeCodeEventHandler(q)
    project = tmp_path / "proj-slug"
    project.mkdir()
    f = project / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)

    real_open = pathlib.Path.open
    opens_seen: list = []

    def spy_open(self, mode="r", *args, **kwargs):
        opens_seen.append((str(self), mode))
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "open", spy_open)
    h.on_modified(_make_fs_event(str(f)))

    # Verify every open() on the .jsonl was read-mode
    jsonl_opens = [(p, m) for (p, m) in opens_seen if p.endswith(".jsonl")]
    assert jsonl_opens, "Parser must have opened the file"
    for p, m in jsonl_opens:
        assert m in ("r", "rb"), f"READ-ONLY VIOLATION: opened {p} with mode={m!r}"
