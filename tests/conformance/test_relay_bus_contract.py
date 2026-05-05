"""Conformance harness for relay-bus primitive contract.

Exercises each of the 5 consumer surfaces against their seeded fixture envelope,
asserting the three primitive relay-bus semantics:

  1. relay_inbox called exactly once at turn-0 with the correct recipient
  2. relay_ack properly marks the seeded envelope as acknowledged
  3. Every outbound relay_post includes explicit sender matching recipient

Shape: 1 test per surface. 1 fixture `seeded_bus` that loads from
`tests/conformance/fixtures/relay/*.json`.

Reference: mcp-server-nucleus/docs/relay_bus_contract.md
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# ── src path injection ──────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_server_nucleus.runtime.relay_ops import (
    relay_ack,
    relay_inbox,
    relay_post,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "relay"

@dataclass
class SurfaceSpec:
    recipient: str
    sender: str

SURFACES = [
    SurfaceSpec(recipient="gemini_cli", sender="gemini_cli"),
    SurfaceSpec(recipient="cursor", sender="cursor"),
    SurfaceSpec(recipient="codex", sender="codex"),
    SurfaceSpec(recipient="windsurf", sender="windsurf"),
    SurfaceSpec(recipient="claude_code_main", sender="claude_code_main"),
]

# ── Mock agent logic ──────────────────────────────────────────────

@dataclass
class MockRelayAgentCallLog:
    relay_inbox_calls: List[Dict[str, Any]] = field(default_factory=list)
    relay_ack_calls: List[Dict[str, Any]] = field(default_factory=list)
    relay_post_calls: List[Dict[str, Any]] = field(default_factory=list)

class MockRelayAgent:
    def __init__(self, spec: SurfaceSpec):
        self.spec = spec
        self.log = MockRelayAgentCallLog()

    def execute_turn_0(self) -> Dict[str, Any]:
        inbox_result = relay_inbox(
            recipient=self.spec.recipient,
            unread_only=True,
        )
        self.log.relay_inbox_calls.append({
            "recipient": self.spec.recipient,
            "unread_only": True,
            "result": inbox_result,
        })

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

        post_result = relay_post(
            to="cowork",
            subject=f"[ACK] Relay-bus test ({self.spec.recipient})",
            body=json.dumps({"status": "ok"}),
            sender=self.spec.sender,
        )
        self.log.relay_post_calls.append({
            "to": "cowork",
            "sender": self.spec.sender,
            "result": post_result,
        })

        return inbox_result

# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def seeded_bus(tmp_path, monkeypatch):
    """Seed the isolated brain from JSON fixture files."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_STRICT", raising=False)

    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True, exist_ok=True)

    seeded_ids = {}
    
    for spec in SURFACES:
        recipient = spec.recipient
        fixture_file = FIXTURES_DIR / f"{recipient}.json"
        
        if not fixture_file.exists():
            continue
            
        envelope = json.loads(fixture_file.read_text(encoding="utf-8"))
        
        inbox = relay_dir / recipient
        inbox.mkdir(parents=True, exist_ok=True)
        
        path = inbox / f"seeded_{envelope['id']}.json"
        path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        
        seeded_ids[recipient] = envelope["id"]

    return tmp_path, seeded_ids

def _read_envelope(brain_path: Path, recipient: str, msg_id: str) -> Optional[Dict]:
    inbox = brain_path / "relay" / recipient
    for f in inbox.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("id") == msg_id:
                return data
        except Exception:
            continue
    return None

# ── Tests ─────────────────────────────────────────────────────────

def _run_surface_assertions(brain_path: Path, seeded_ids: Dict, spec: SurfaceSpec):
    agent = MockRelayAgent(spec)
    inbox_result = agent.execute_turn_0()

    # 1. Inbox
    assert len(agent.log.relay_inbox_calls) == 1
    call = agent.log.relay_inbox_calls[0]
    assert call["recipient"] == spec.recipient
    assert call["unread_only"] is True
    assert inbox_result["count"] >= 1

    # 2. Ack
    assert len(agent.log.relay_ack_calls) == inbox_result["count"]
    for ack_call in agent.log.relay_ack_calls:
        assert ack_call["result"]["acknowledged"] is True

    # 3. Post (explicit sender)
    for post_call in agent.log.relay_post_calls:
        assert post_call["sender"] == spec.sender
        assert post_call["result"]["sent"] is True

    # 4. On-disk read status
    msg_id = seeded_ids[spec.recipient]
    disk_envelope = _read_envelope(brain_path, spec.recipient, msg_id)
    assert disk_envelope is not None
    assert disk_envelope["read"] is True


class TestRelayBus_GeminiCLI:
    def test_gemini_cli(self, seeded_bus):
        brain_path, seeded_ids = seeded_bus
        _run_surface_assertions(brain_path, seeded_ids, SURFACES[0])

class TestRelayBus_Cursor:
    def test_cursor(self, seeded_bus):
        brain_path, seeded_ids = seeded_bus
        _run_surface_assertions(brain_path, seeded_ids, SURFACES[1])

class TestRelayBus_Codex:
    def test_codex(self, seeded_bus):
        brain_path, seeded_ids = seeded_bus
        _run_surface_assertions(brain_path, seeded_ids, SURFACES[2])

class TestRelayBus_Windsurf:
    def test_windsurf(self, seeded_bus):
        brain_path, seeded_ids = seeded_bus
        _run_surface_assertions(brain_path, seeded_ids, SURFACES[3])

class TestRelayBus_ClaudeCode:
    def test_claude_code(self, seeded_bus):
        brain_path, seeded_ids = seeded_bus
        _run_surface_assertions(brain_path, seeded_ids, SURFACES[4])
