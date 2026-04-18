"""Tests for Layer 0: Conversation Capture (conversation_ops.py)."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_user_event(content, ts="2026-04-08T10:00:00Z", sid="test-session-001"):
    """Create a user event with string content."""
    return json.dumps({
        "type": "user",
        "message": {"role": "user", "content": content},
        "uuid": f"u-{hash(content) % 10000:04d}",
        "timestamp": ts,
        "sessionId": sid,
    })


def _make_user_tool_result(tool_use_id="toolu_abc", output="file contents here"):
    """Create a user event with tool_result array content."""
    return json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": output}],
        },
        "uuid": "u-tool-result",
        "timestamp": "2026-04-08T10:01:00Z",
        "sessionId": "test-session-001",
    })


def _make_assistant_event(text="Here is the answer", tools=None, thinking=None,
                          ts="2026-04-08T10:00:30Z"):
    """Create an assistant event with text, optional tool_use and thinking blocks."""
    content = []
    if thinking:
        content.append({"type": "thinking", "thinking": thinking})
    if tools:
        for t in tools:
            content.append({"type": "tool_use", "id": f"toolu_{t}", "name": t, "input": {}})
    content.append({"type": "text", "text": text})

    return json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": content,
            "model": "claude-opus-4-6",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
        "uuid": f"a-{hash(text) % 10000:04d}",
        "timestamp": ts,
        "sessionId": "test-session-001",
    })


def _make_noise_events():
    """Create noise events that should be filtered out."""
    return [
        json.dumps({"type": "progress", "data": {"type": "agent_progress"}, "uuid": "n1"}),
        json.dumps({"type": "file-history-snapshot", "snapshot": {}, "uuid": "n2"}),
        json.dumps({"type": "queue-operation", "uuid": "n3"}),
        json.dumps({"type": "last-prompt", "uuid": "n4"}),
    ]


def _make_compact_boundary():
    """Create a compaction boundary event."""
    return json.dumps({
        "type": "system",
        "subtype": "compact_boundary",
        "content": "Conversation compacted",
        "uuid": "sys-compact",
    })


def _make_sidechain_event():
    """Create a sidechain (subagent) message that should be excluded."""
    return json.dumps({
        "type": "assistant",
        "isSidechain": True,
        "agentId": "agent-123",
        "message": {"role": "assistant", "content": [{"type": "text", "text": "subagent output"}]},
        "uuid": "sc-1",
    })


def _make_meta_event():
    """Create a meta user event (command output)."""
    return json.dumps({
        "type": "user",
        "isMeta": True,
        "message": {"role": "user", "content": "<command-name>help</command-name>"},
        "uuid": "meta-1",
    })


@pytest.fixture
def sample_jsonl(tmp_path):
    """Create a sample JSONL file with mixed event types."""
    lines = [
        _make_user_event("How do I fix the auth bug?", ts="2026-04-08T10:00:00Z"),
        _make_assistant_event("Let me look at the auth module.", tools=["Read"], ts="2026-04-08T10:00:30Z"),
        _make_user_tool_result(output="def authenticate(): pass"),
        _make_assistant_event("The auth function is empty. Let me fix it.", tools=["Edit"],
                              thinking="The function body is missing", ts="2026-04-08T10:01:30Z"),
        *_make_noise_events(),
        _make_user_event("Great, now add tests", ts="2026-04-08T10:02:00Z"),
        _make_assistant_event("I'll add pytest tests for the auth module.", tools=["Write"],
                              ts="2026-04-08T10:02:30Z"),
        _make_sidechain_event(),
        _make_meta_event(),
        _make_user_event("Looks good, thanks!", ts="2026-04-08T10:03:00Z"),
        _make_assistant_event("You're welcome!", ts="2026-04-08T10:03:30Z"),
    ]
    f = tmp_path / "test-session-001.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


@pytest.fixture
def brain_path(tmp_path):
    """Create a minimal brain directory structure."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "training").mkdir()
    (brain / "engrams").mkdir()
    (brain / "ledger").mkdir()
    os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)
    yield brain
    os.environ.pop("NUCLEAR_BRAIN_PATH", None)


# ── Test: Streaming Parser ────────────────────────────────────────────

class TestStreamParser:
    def test_stream_parse_yields_all_lines(self, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import _stream_parse_jsonl
        events = list(_stream_parse_jsonl(sample_jsonl))
        assert len(events) >= 10  # all valid JSON lines

    def test_stream_parse_skips_malformed(self, tmp_path):
        from mcp_server_nucleus.runtime.conversation_ops import _stream_parse_jsonl
        f = tmp_path / "bad.jsonl"
        f.write_text('{"valid": true}\nnot json\n{"also": "valid"}\n\n')
        events = list(_stream_parse_jsonl(f))
        assert len(events) == 2


class TestSignalFilter:
    def test_is_signal_filters_noise(self):
        from mcp_server_nucleus.runtime.conversation_ops import _is_signal_message
        assert _is_signal_message({"type": "user"}) is True
        assert _is_signal_message({"type": "assistant"}) is True
        assert _is_signal_message({"type": "progress"}) is False
        assert _is_signal_message({"type": "file-history-snapshot"}) is False
        assert _is_signal_message({"type": "queue-operation"}) is False
        assert _is_signal_message({"type": "assistant", "isSidechain": True}) is False
        assert _is_signal_message({"type": "user", "isMeta": True}) is False


class TestExtractUserText:
    def test_extract_user_text_string(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_user_text
        event = {"message": {"content": "Hello world"}}
        assert _extract_user_text(event) == "Hello world"

    def test_extract_user_text_array_returns_none(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_user_text
        event = {"message": {"content": [{"type": "tool_result", "content": "output"}]}}
        assert _extract_user_text(event) is None

    def test_extract_user_text_meta_returns_none(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_user_text
        event = {"message": {"content": "<command-name>help</command-name>"}}
        assert _extract_user_text(event) is None

    def test_extract_user_text_empty_returns_none(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_user_text
        assert _extract_user_text({"message": {"content": ""}}) is None
        assert _extract_user_text({"message": {"content": "   "}}) is None


class TestExtractAssistantText:
    def test_extract_assistant_text_blocks(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_assistant_text
        event = {"message": {"content": [
            {"type": "thinking", "thinking": "Let me consider..."},
            {"type": "tool_use", "name": "Read", "id": "t1", "input": {}},
            {"type": "tool_use", "name": "Bash", "id": "t2", "input": {}},
            {"type": "text", "text": "Here is the answer."},
        ]}}
        text, tools, thinking = _extract_assistant_text(event)
        assert text == "Here is the answer."
        assert tools == ["Read", "Bash"]
        assert thinking == "Let me consider..."

    def test_extract_assistant_text_no_tools(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_assistant_text
        event = {"message": {"content": [{"type": "text", "text": "Simple response"}]}}
        text, tools, thinking = _extract_assistant_text(event)
        assert text == "Simple response"
        assert tools == []
        assert thinking is None

    def test_extract_assistant_string_content(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_assistant_text
        event = {"message": {"content": "Just a string"}}
        text, tools, thinking = _extract_assistant_text(event)
        assert text == "Just a string"


# ── Test: Conversation Building ───────────────────────────────────────

class TestBuildConversation:
    def test_build_conversation_stream(self, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import _build_conversation_stream
        messages = _build_conversation_stream(sample_jsonl)
        # Should have: 4 user texts + 4 assistant texts = 8
        # (tool_result user, sidechain, meta, noise are excluded)
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles
        # No segment markers (no compaction in this file)
        assert "__segment__" not in roles

    def test_compaction_boundary_segments(self, tmp_path):
        from mcp_server_nucleus.runtime.conversation_ops import _build_conversation_stream
        lines = [
            _make_user_event("First question"),
            _make_assistant_event("First answer"),
            _make_compact_boundary(),
            _make_user_event("After compaction"),
            _make_assistant_event("Post-compaction answer"),
        ]
        f = tmp_path / "compact.jsonl"
        f.write_text("\n".join(lines) + "\n")
        messages = _build_conversation_stream(f)
        # Should have segment marker between the two parts
        roles = [m["role"] for m in messages]
        assert "__segment__" in roles


# ── Test: Chunking ────────────────────────────────────────────────────

class TestChunking:
    def test_chunk_window_and_overlap(self):
        from mcp_server_nucleus.runtime.conversation_ops import _chunk_conversation
        # 10 messages, window=6, overlap=2
        messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
                    for i in range(10)]
        chunks = _chunk_conversation(messages, window=6, overlap=2)
        # Step = 6 - 2 = 4. Chunks: [0:6], [4:10] = 2 chunks
        assert len(chunks) == 2
        assert len(chunks[0]) == 6
        assert len(chunks[1]) == 6

    def test_chunk_respects_segments(self):
        from mcp_server_nucleus.runtime.conversation_ops import (
            _chunk_conversation, _SEGMENT_MARKER,
        )
        messages = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
            {"role": "assistant", "content": "d"},
            {"role": "user", "content": "e"},
            _SEGMENT_MARKER,
            {"role": "user", "content": "f"},
            {"role": "assistant", "content": "g"},
            {"role": "user", "content": "h"},
            {"role": "assistant", "content": "i"},
            {"role": "user", "content": "j"},
        ]
        chunks = _chunk_conversation(messages, window=20, overlap=0)
        # Two segments, each 5 messages, both meet MIN_CHUNK_SIZE
        assert len(chunks) == 2

    def test_chunk_discards_tiny(self):
        from mcp_server_nucleus.runtime.conversation_ops import _chunk_conversation
        messages = [
            {"role": "user", "content": "short"},
            {"role": "assistant", "content": "chat"},
        ]
        chunks = _chunk_conversation(messages, window=20, overlap=0)
        assert len(chunks) == 0  # Only 2 messages < MIN_CHUNK_SIZE=4


# ── Test: DPO Correction Detection ───────────────────────────────────

class TestCorrections:
    def test_detect_corrections(self):
        from mcp_server_nucleus.runtime.conversation_ops import _detect_corrections
        messages = [
            {"role": "user", "content": "Fix the login page"},
            {"role": "assistant", "content": "I'll change the CSS styling..."},
            {"role": "user", "content": "no, actually fix the auth logic not the CSS"},
            {"role": "assistant", "content": "You're right, let me fix the authentication..."},
        ]
        corrections = _detect_corrections(messages)
        assert len(corrections) == 1
        assert corrections[0]["rejected"] == "I'll change the CSS styling..."
        assert "authentication" in corrections[0]["chosen"]
        assert corrections[0]["prompt"] == "Fix the login page"

    def test_no_false_positive_corrections(self):
        from mcp_server_nucleus.runtime.conversation_ops import _detect_corrections
        messages = [
            {"role": "user", "content": "Search for errors in the log"},
            {"role": "assistant", "content": "No errors found in the log."},
            {"role": "user", "content": "Ok, check the database logs then"},
            {"role": "assistant", "content": "Found 3 errors in db logs."},
        ]
        corrections = _detect_corrections(messages)
        assert len(corrections) == 0  # "Ok" doesn't start with correction prefix


# ── Test: Reasoning Chains ────────────────────────────────────────────

class TestReasoningChains:
    def test_extract_reasoning_chains(self):
        from mcp_server_nucleus.runtime.conversation_ops import _extract_reasoning_chains
        messages = [
            {"role": "user", "content": "What's in server.py?", "tools": [], "thinking": None},
            {"role": "assistant", "content": "Let me read it.", "tools": ["Read"],
             "thinking": "I need to check the server file"},
            {"role": "user", "content": "File contents: def main(): pass", "tools": [], "thinking": None},
            {"role": "assistant", "content": "The server has a main function.", "tools": [],
             "thinking": None},
        ]
        chains = _extract_reasoning_chains(messages)
        assert len(chains) == 1
        assert chains[0]["prompt"] == "What's in server.py?"
        assert len(chains[0]["steps"]) == 1
        assert chains[0]["steps"][0]["action"] == "Read"
        assert "main function" in chains[0]["final_answer"]


# ── Test: Secret Redaction ────────────────────────────────────────────

class TestSecretRedaction:
    def test_scan_and_redact(self):
        from mcp_server_nucleus.runtime.conversation_ops import _scan_and_redact
        text = "Use api_key=sk-abc123xyz456 and Bearer eyJtoken to authenticate"
        result = _scan_and_redact(text)
        assert "sk-abc123xyz456" not in result
        assert "[REDACTED:" in result


# ── Test: Cursor Management ───────────────────────────────────────────

class TestCursor:
    def test_cursor_round_trip(self, brain_path):
        from mcp_server_nucleus.runtime.conversation_ops import (
            _load_cursor, _save_cursor, _session_needs_processing,
        )
        # Empty cursor
        cursor = _load_cursor()
        assert cursor["processed_sessions"] == {}

        # Save with a processed session
        cursor["processed_sessions"]["session-abc"] = {
            "file_size": 1000,
            "mtime": "2026-04-08T10:00:00Z",
        }
        _save_cursor(cursor)

        # Reload
        cursor2 = _load_cursor()
        assert "session-abc" in cursor2["processed_sessions"]

        # Session needs processing (new session)
        assert _session_needs_processing("new-session", Path("/tmp/fake"), cursor2) is True

    def test_session_needs_reprocessing_if_grown(self, brain_path, tmp_path):
        from mcp_server_nucleus.runtime.conversation_ops import (
            _save_cursor, _session_needs_processing, _load_cursor,
        )
        f = tmp_path / "growing.jsonl"
        f.write_text("small")

        cursor = _load_cursor()
        cursor["processed_sessions"]["growing"] = {"file_size": 3, "mtime": ""}
        _save_cursor(cursor)

        cursor = _load_cursor()
        # File is now 5 bytes > cursor's 3 bytes
        assert _session_needs_processing("growing", f, cursor) is True


# ── Test: End-to-End Ingest ───────────────────────────────────────────

class TestIngest:
    def test_ingest_incremental(self, brain_path, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import (
            ingest_conversations, _load_cursor,
        )
        # Mock _discover_transcripts to return our sample
        with patch("mcp_server_nucleus.runtime.conversation_ops._discover_transcripts") as mock_disc:
            mock_disc.return_value = [("test-session-001", sample_jsonl)]
            result = ingest_conversations(mode="batch", limit=1)

        assert result["sessions_processed"] == 1
        assert result["turns_created"] >= 1
        assert "errors" in result

        # Cursor should be updated
        cursor = _load_cursor()
        assert "test-session-001" in cursor["processed_sessions"]

    def test_ingest_dedup(self, brain_path, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import ingest_conversations

        with patch("mcp_server_nucleus.runtime.conversation_ops._discover_transcripts") as mock_disc:
            mock_disc.return_value = [("test-session-001", sample_jsonl)]

            # First ingest
            r1 = ingest_conversations(mode="batch")
            # Second ingest (same session, same size → cursor skip)
            r2 = ingest_conversations(mode="batch")

        assert r1["sessions_processed"] == 1
        assert r2["sessions_processed"] == 0  # Already in cursor


# ── Test: Search ──────────────────────────────────────────────────────

class TestSearch:
    def test_search_keyword_match(self, brain_path, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import (
            ingest_conversations, search_conversations,
        )
        with patch("mcp_server_nucleus.runtime.conversation_ops._discover_transcripts") as mock_disc:
            mock_disc.return_value = [("test-session-001", sample_jsonl)]
            ingest_conversations(mode="batch")

        results = search_conversations(query="auth bug")
        assert results["total_matches"] >= 1
        assert results["results"][0]["score"] > 0

    def test_search_empty_query(self, brain_path):
        from mcp_server_nucleus.runtime.conversation_ops import search_conversations
        results = search_conversations(query="")
        assert results["results"] == []


# ── Test: Stats and List ──────────────────────────────────────────────

class TestStatsAndList:
    def test_conversation_stats(self, brain_path, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import (
            ingest_conversations, conversation_stats,
        )
        with patch("mcp_server_nucleus.runtime.conversation_ops._discover_transcripts") as mock_disc:
            mock_disc.return_value = [("test-session-001", sample_jsonl)]
            ingest_conversations(mode="batch")

        stats = conversation_stats()
        assert stats["total_sessions_ingested"] == 1
        assert stats["total_turns"] >= 1

    def test_list_conversations(self, brain_path, sample_jsonl):
        from mcp_server_nucleus.runtime.conversation_ops import (
            ingest_conversations, list_conversations,
        )
        with patch("mcp_server_nucleus.runtime.conversation_ops._discover_transcripts") as mock_disc:
            mock_disc.return_value = [("test-session-001", sample_jsonl)]
            ingest_conversations(mode="batch")

        listing = list_conversations()
        assert listing["total"] == 1
        assert listing["conversations"][0]["session_id"] == "test-session"  # truncated to 12 chars
