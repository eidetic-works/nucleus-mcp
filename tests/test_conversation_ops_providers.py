"""Multi-provider parser fixtures for Layer 0: Conversation Capture.

These fixtures provide structural approximations of conversational transcripts
from various agent surfaces (Windsurf, Cursor, Gemini CLI, Codex). 
They lay the groundwork for expanding `conversation_ops.py` to route and parse
different proprietary JSONL schemas.
"""

import json
import pytest
from pathlib import Path


# ── Windsurf Fixtures ──────────────────────────────────────────────────

def _make_windsurf_event(content: str, role: str = "human", ts: str = "2026-04-08T10:00:00Z", sid: str = "ws-session-123"):
    """Create a mock Windsurf transcript event.
    
    Assumes a schema using 'role': 'human'/'agent' and nested 'text'.
    """
    return json.dumps({
        "session_id": sid,
        "provider": "windsurf",
        "timestamp": ts,
        "turn": {
            "role": role,
            "text": content,
            "tool_calls": [] if role == "agent" else None
        }
    })

@pytest.fixture
def windsurf_jsonl(tmp_path: Path):
    lines = [
        _make_windsurf_event("Help me fix this bug", role="human"),
        _make_windsurf_event("I will check the logs", role="agent")
    ]
    f = tmp_path / "windsurf_mock.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


# ── Cursor Fixtures ────────────────────────────────────────────────────

def _make_cursor_event(content: str, is_user: bool = True, ts: str = "2026-04-08T10:00:00Z", sid: str = "cursor-session-456"):
    """Create a mock Cursor transcript event.
    
    Assumes a schema using boolean flags or 'author' types.
    """
    return json.dumps({
        "id": sid,
        "source": "cursor",
        "time": ts,
        "message": {
            "is_user": is_user,
            "content": content
        }
    })

@pytest.fixture
def cursor_jsonl(tmp_path: Path):
    lines = [
        _make_cursor_event("Generate a Python script", is_user=True),
        _make_cursor_event("Here is the script...", is_user=False)
    ]
    f = tmp_path / "cursor_mock.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


# ── Gemini CLI Fixtures ────────────────────────────────────────────────

def _make_gemini_event(content: str, author: str = "user", ts: str = "2026-04-08T10:00:00Z", sid: str = "gemini-session-789"):
    """Create a mock Gemini CLI transcript event.
    
    Assumes a schema using 'author' and 'parts' array.
    """
    return json.dumps({
        "sessionId": sid,
        "agent": "gemini_cli",
        "createdAt": ts,
        "history": [
            {
                "author": author,
                "parts": [content]
            }
        ]
    })

@pytest.fixture
def gemini_jsonl(tmp_path: Path):
    lines = [
        _make_gemini_event("Explain quantum computing", author="user"),
        _make_gemini_event("Quantum computing relies on qubits...", author="model")
    ]
    f = tmp_path / "gemini_mock.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


# ── Codex Fixtures ─────────────────────────────────────────────────────

def _make_codex_event(content: str, speaker: str = "user", ts: str = "2026-04-08T10:00:00Z", sid: str = "codex-session-000"):
    """Create a mock Codex transcript event.
    
    Assumes a minimal schema with 'speaker' and 'message'.
    """
    return json.dumps({
        "session": sid,
        "log_type": "codex",
        "timestamp": ts,
        "dialogue": {
            "speaker": speaker,
            "message": content
        }
    })

@pytest.fixture
def codex_jsonl(tmp_path: Path):
    lines = [
        _make_codex_event("Write a React component", speaker="user"),
        _make_codex_event("```jsx\nexport default function App() {}\n```", speaker="assistant")
    ]
    f = tmp_path / "codex_mock.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


# ── Tests to ensure fixtures generate valid JSONL ──────────────────────

class TestProviderFixtures:
    def test_windsurf_fixture_validity(self, windsurf_jsonl):
        with open(windsurf_jsonl, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2
            parsed = json.loads(lines[0])
            assert parsed["provider"] == "windsurf"
            assert parsed["turn"]["role"] == "human"

    def test_cursor_fixture_validity(self, cursor_jsonl):
        with open(cursor_jsonl, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2
            parsed = json.loads(lines[0])
            assert parsed["source"] == "cursor"
            assert parsed["message"]["is_user"] is True

    def test_gemini_fixture_validity(self, gemini_jsonl):
        with open(gemini_jsonl, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2
            parsed = json.loads(lines[0])
            assert parsed["agent"] == "gemini_cli"
            assert parsed["history"][0]["author"] == "user"

    def test_codex_fixture_validity(self, codex_jsonl):
        with open(codex_jsonl, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2
            parsed = json.loads(lines[0])
            assert parsed["log_type"] == "codex"
            assert parsed["dialogue"]["speaker"] == "user"
