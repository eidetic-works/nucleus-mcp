"""Conformance harness for agent adapter contract (PR #140, T2.5).

Exercises each of the 5 appendices (A Gemini / B Cursor / C Codex /
D Windsurf / E Claude Code) against a seeded substrate, asserting the
three primitive contract actions fire correctly:

  1. relay_inbox(recipient=<recipient>, unread_only=True) called once at turn-0
  2. relay_ack called for every processed envelope
  3. Every relay_post includes explicit sender=<recipient>
  4. Substrate tag-log shows read:true after ack

Shape: 1 test per appendix, 1 fixture ``seeded_substrate``, 1 mock agent
class.  All in-process mocks — no live CLI invocation.

Reference: mcp-server-nucleus/docs/agent_adapter_contract.md §Conformance harness
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# ── src path injection (same pattern as existing tests) ──────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_server_nucleus.runtime.relay_ops import (
    relay_ack,
    relay_inbox,
    relay_post,
)


# ── Appendix definitions ─────────────────────────────────────────

@dataclass
class AppendixSpec:
    """Minimal spec for one appendix's turn-0 protocol."""
    name: str               # e.g. "Appendix A — Gemini CLI"
    recipient: str          # inbox token (e.g. "gemini_cli")
    sender: str             # explicit sender value for relay_post
    provider: str           # provider string for identify_agent
    role: str               # role string for identify_agent


APPENDICES: List[AppendixSpec] = [
    AppendixSpec(
        name="Appendix A — Gemini CLI",
        recipient="gemini_cli",
        sender="gemini_cli",
        provider="google_gemini",
        role="primary",
    ),
    AppendixSpec(
        name="Appendix B — Cursor",
        recipient="cursor",
        sender="cursor",
        provider="cursor",
        role="primary",
    ),
    AppendixSpec(
        name="Appendix C — Codex",
        recipient="codex",
        sender="codex",
        provider="openai_codex",
        role="worker",
    ),
    AppendixSpec(
        name="Appendix D — Windsurf",
        recipient="windsurf",
        sender="windsurf",
        provider="windsurf",
        role="primary",
    ),
    AppendixSpec(
        name="Appendix E — Claude Code",
        recipient="claude_code_main",
        sender="claude_code_main",
        provider="anthropic_claude_code",
        role="primary",
    ),
]


# ── Mock agent ────────────────────────────────────────────────────

@dataclass
class MockAgentCallLog:
    """Records calls made by MockAdapterAgent for assertion."""
    identify_agent_calls: List[Dict[str, Any]] = field(default_factory=list)
    relay_inbox_calls: List[Dict[str, Any]] = field(default_factory=list)
    relay_ack_calls: List[Dict[str, Any]] = field(default_factory=list)
    relay_post_calls: List[Dict[str, Any]] = field(default_factory=list)


class MockAdapterAgent:
    """Simulates a conformant agent's turn-0 protocol.

    Executes the three MCP tool calls specified by the appendix:
      1. relay_inbox(recipient=..., unread_only=True)
      2. relay_ack(message_id=..., recipient=...)  — for each envelope
      3. relay_post(..., sender=<explicit>)         — optional outbound

    Does NOT cold-boot any real CLI.  All calls use the relay_ops
    functions directly against the tmp_path-based substrate.
    """

    def __init__(self, spec: AppendixSpec):
        self.spec = spec
        self.log = MockAgentCallLog()

    def execute_turn_0(self, send_reply: bool = True) -> Dict[str, Any]:
        """Run the turn-0 protocol and return inbox results."""
        # Step 1: identify_agent (recorded but not exercised against
        # the real identify_agent function — that's sync_ops, not relay)
        self.log.identify_agent_calls.append({
            "role": self.spec.role,
            "provider": self.spec.provider,
        })

        # Step 2: relay_inbox — mandatory exactly-once call
        inbox_result = relay_inbox(
            recipient=self.spec.recipient,
            unread_only=True,
        )
        self.log.relay_inbox_calls.append({
            "recipient": self.spec.recipient,
            "unread_only": True,
            "result": inbox_result,
        })

        # Step 3: ack each envelope
        for msg in inbox_result.get("messages", []):
            msg_id = msg.get("id")
            if msg_id:
                ack_result = relay_ack(
                    message_id=msg_id,
                    recipient=self.spec.recipient,
                )
                self.log.relay_ack_calls.append({
                    "message_id": msg_id,
                    "recipient": self.spec.recipient,
                    "result": ack_result,
                })

        # Step 4 (optional): fire a reply relay_post with explicit sender
        if send_reply:
            post_result = relay_post(
                to="cowork",
                subject=f"[ACK] Turn-0 inbox processed ({self.spec.name})",
                body=json.dumps({
                    "summary": f"Processed {inbox_result.get('count', 0)} envelope(s)",
                    "artifact_refs": [],
                }),
                sender=self.spec.sender,
            )
            self.log.relay_post_calls.append({
                "to": "cowork",
                "sender": self.spec.sender,
                "result": post_result,
            })

        return inbox_result


# ── Fixtures ──────────────────────────────────────────────────────

def _seed_envelope(relay_dir: Path, recipient: str) -> Dict[str, Any]:
    """Seed a known envelope into .brain/relay/<recipient>/."""
    inbox = relay_dir / recipient
    inbox.mkdir(parents=True, exist_ok=True)

    envelope = {
        "id": f"relay_20260422_120000_deadbeef",
        "from": "cowork",
        "from_role": None,
        "from_session_id": None,
        "to": recipient,
        "to_session_id": None,
        "subject": f"[COORD] Conformance seed for {recipient}",
        "body": json.dumps({
            "summary": "Seeded test envelope for T2.5 conformance harness",
            "artifact_refs": ["mcp-server-nucleus/docs/agent_adapter_contract.md"],
        }),
        "priority": "normal",
        "context": {},
        "created_at": "2026-04-22T12:00:00Z",
        "read": False,
        "read_at": None,
        "read_by": None,
        "read_by_sessions": {},
    }

    filename = f"20260422_120000_relay_20260422_120000_deadbeef.json"
    path = inbox / filename
    path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return envelope


@pytest.fixture
def seeded_substrate(tmp_path, monkeypatch):
    """Create an isolated .brain/ with seeded envelopes for all appendices.

    Sets NUCLEUS_BRAIN_PATH so relay_ops resolves to tmp_path.
    Returns (tmp_path, {recipient: envelope_dict}).
    """
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    # Also clear any strict-mode gate so posts succeed
    monkeypatch.delenv("NUCLEUS_RELAY_STRICT", raising=False)

    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True, exist_ok=True)

    seeded = {}
    for spec in APPENDICES:
        envelope = _seed_envelope(relay_dir, spec.recipient)
        seeded[spec.recipient] = envelope

    return tmp_path, seeded


# ── Helpers ───────────────────────────────────────────────────────

def _read_envelope_from_disk(brain_path: Path, recipient: str, msg_id: str) -> Optional[Dict]:
    """Read envelope JSON from disk by scanning the recipient's inbox."""
    inbox = brain_path / "relay" / recipient
    for f in inbox.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("id") == msg_id:
                return data
        except Exception:
            continue
    return None


# ── Tests (1 per appendix) ────────────────────────────────────────


class TestAppendixA_GeminiCLI:
    """Appendix A — Gemini CLI (Context-File + Skill Injection)."""

    def test_turn_0_conformance(self, seeded_substrate):
        brain_path, seeded = seeded_substrate
        spec = APPENDICES[0]
        agent = MockAdapterAgent(spec)

        inbox_result = agent.execute_turn_0()

        # 1. relay_inbox called exactly once at turn-0
        assert len(agent.log.relay_inbox_calls) == 1
        call = agent.log.relay_inbox_calls[0]
        assert call["recipient"] == "gemini_cli"
        assert call["unread_only"] is True

        # 2. At least one message returned (the seeded envelope)
        assert inbox_result["count"] >= 1

        # 3. relay_ack called for each processed envelope
        assert len(agent.log.relay_ack_calls) == inbox_result["count"]
        for ack_call in agent.log.relay_ack_calls:
            assert ack_call["result"]["acknowledged"] is True

        # 4. Every relay_post includes explicit sender=<recipient>
        for post_call in agent.log.relay_post_calls:
            assert post_call["sender"] == "gemini_cli"
            assert post_call["result"]["sent"] is True

        # 5. Substrate tag-log shows read:true after ack
        msg_id = seeded["gemini_cli"]["id"]
        disk_envelope = _read_envelope_from_disk(brain_path, "gemini_cli", msg_id)
        assert disk_envelope is not None
        assert disk_envelope["read"] is True


class TestAppendixB_Cursor:
    """Appendix B — Cursor (settings-based rules)."""

    def test_turn_0_conformance(self, seeded_substrate):
        brain_path, seeded = seeded_substrate
        spec = APPENDICES[1]
        agent = MockAdapterAgent(spec)

        inbox_result = agent.execute_turn_0()

        # 1. relay_inbox called exactly once at turn-0
        assert len(agent.log.relay_inbox_calls) == 1
        call = agent.log.relay_inbox_calls[0]
        assert call["recipient"] == "cursor"
        assert call["unread_only"] is True

        # 2. At least one message returned
        assert inbox_result["count"] >= 1

        # 3. relay_ack called for each processed envelope
        assert len(agent.log.relay_ack_calls) == inbox_result["count"]
        for ack_call in agent.log.relay_ack_calls:
            assert ack_call["result"]["acknowledged"] is True

        # 4. Every relay_post includes explicit sender="cursor"
        for post_call in agent.log.relay_post_calls:
            assert post_call["sender"] == "cursor"
            assert post_call["result"]["sent"] is True

        # 5. Substrate tag-log shows read:true after ack
        msg_id = seeded["cursor"]["id"]
        disk_envelope = _read_envelope_from_disk(brain_path, "cursor", msg_id)
        assert disk_envelope is not None
        assert disk_envelope["read"] is True


class TestAppendixC_Codex:
    """Appendix C — Codex (skill file)."""

    def test_turn_0_conformance(self, seeded_substrate):
        brain_path, seeded = seeded_substrate
        spec = APPENDICES[2]
        agent = MockAdapterAgent(spec)

        inbox_result = agent.execute_turn_0()

        # 1. relay_inbox called exactly once at turn-0
        assert len(agent.log.relay_inbox_calls) == 1
        call = agent.log.relay_inbox_calls[0]
        assert call["recipient"] == "codex"
        assert call["unread_only"] is True

        # 2. At least one message returned
        assert inbox_result["count"] >= 1

        # 3. relay_ack called for each
        assert len(agent.log.relay_ack_calls) == inbox_result["count"]
        for ack_call in agent.log.relay_ack_calls:
            assert ack_call["result"]["acknowledged"] is True

        # 4. Every relay_post includes explicit sender="codex"
        for post_call in agent.log.relay_post_calls:
            assert post_call["sender"] == "codex"
            assert post_call["result"]["sent"] is True

        # 5. Substrate tag-log shows read:true after ack
        msg_id = seeded["codex"]["id"]
        disk_envelope = _read_envelope_from_disk(brain_path, "codex", msg_id)
        assert disk_envelope is not None
        assert disk_envelope["read"] is True


class TestAppendixD_Windsurf:
    """Appendix D — Windsurf (rules-based, user-global)."""

    def test_turn_0_conformance(self, seeded_substrate):
        brain_path, seeded = seeded_substrate
        spec = APPENDICES[3]
        agent = MockAdapterAgent(spec)

        inbox_result = agent.execute_turn_0()

        # 1. relay_inbox called exactly once at turn-0
        assert len(agent.log.relay_inbox_calls) == 1
        call = agent.log.relay_inbox_calls[0]
        assert call["recipient"] == "windsurf"
        assert call["unread_only"] is True

        # 2. At least one message returned
        assert inbox_result["count"] >= 1

        # 3. relay_ack called for each
        assert len(agent.log.relay_ack_calls) == inbox_result["count"]
        for ack_call in agent.log.relay_ack_calls:
            assert ack_call["result"]["acknowledged"] is True

        # 4. Every relay_post includes explicit sender="windsurf"
        for post_call in agent.log.relay_post_calls:
            assert post_call["sender"] == "windsurf"
            assert post_call["result"]["sent"] is True

        # 5. Substrate tag-log shows read:true after ack
        msg_id = seeded["windsurf"]["id"]
        disk_envelope = _read_envelope_from_disk(brain_path, "windsurf", msg_id)
        assert disk_envelope is not None
        assert disk_envelope["read"] is True


class TestAppendixE_ClaudeCode:
    """Appendix E — Claude Code (pre-turn-hook)."""

    def test_turn_0_conformance(self, seeded_substrate):
        brain_path, seeded = seeded_substrate
        spec = APPENDICES[4]
        agent = MockAdapterAgent(spec)

        inbox_result = agent.execute_turn_0()

        # 1. relay_inbox called exactly once at turn-0
        assert len(agent.log.relay_inbox_calls) == 1
        call = agent.log.relay_inbox_calls[0]
        assert call["recipient"] == "claude_code_main"
        assert call["unread_only"] is True

        # 2. At least one message returned
        assert inbox_result["count"] >= 1

        # 3. relay_ack called for each
        assert len(agent.log.relay_ack_calls) == inbox_result["count"]
        for ack_call in agent.log.relay_ack_calls:
            assert ack_call["result"]["acknowledged"] is True

        # 4. Every relay_post includes explicit sender="claude_code_main"
        for post_call in agent.log.relay_post_calls:
            assert post_call["sender"] == "claude_code_main"
            assert post_call["result"]["sent"] is True

        # 5. Substrate tag-log shows read:true after ack
        msg_id = seeded["claude_code_main"]["id"]
        disk_envelope = _read_envelope_from_disk(
            brain_path, "claude_code_main", msg_id,
        )
        assert disk_envelope is not None
        assert disk_envelope["read"] is True
