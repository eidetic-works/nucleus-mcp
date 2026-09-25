"""Comprehensive tests for runtime/dsor.py — DecisionEntry, DecisionLedger,
EngramVault, SessionStateManager."""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.dsor import (
    DecisionEntry,
    DecisionLedger,
    EngramVault,
    SessionStateManager,
)


# ── DecisionEntry ────────────────────────────────────────────────

class TestDecisionEntry:
    def test_init_defaults(self):
        entry = DecisionEntry(
            decision_id="dec-1",
            intent="test_intent",
            reasoning="because",
            context_hash="abc123",
        )
        assert entry.decision_id == "dec-1"
        assert entry.intent == "test_intent"
        assert entry.reasoning == "because"
        assert entry.context_hash == "abc123"
        assert entry.confidence == 1.0
        assert entry.deterministic_anchor == "NONE"
        assert entry.audit_status == "PENDING"
        assert entry.metadata == {}
        assert entry.timestamp is not None

    def test_init_with_all_params(self):
        entry = DecisionEntry(
            decision_id="dec-2",
            intent="deploy",
            reasoning="all tests pass",
            context_hash="hash456",
            confidence=0.85,
            deterministic_anchor="SHA256",
            audit_status="APPROVED",
            metadata={"env": "prod"},
            timestamp="2026-01-01T00:00:00Z",
        )
        assert entry.confidence == 0.85
        assert entry.deterministic_anchor == "SHA256"
        assert entry.audit_status == "APPROVED"
        assert entry.metadata == {"env": "prod"}
        assert entry.timestamp == "2026-01-01T00:00:00Z"

    def test_init_metadata_none_becomes_empty(self):
        entry = DecisionEntry(
            decision_id="dec-3",
            intent="i",
            reasoning="r",
            context_hash="h",
            metadata=None,
        )
        assert entry.metadata == {}

    def test_to_dict(self):
        entry = DecisionEntry(
            decision_id="dec-x",
            intent="intent_x",
            reasoning="reasoning_x",
            context_hash="hash_x",
            confidence=0.5,
            deterministic_anchor="ANCHOR",
            audit_status="AUDITED",
            metadata={"k": "v"},
            timestamp="ts",
        )
        d = entry.to_dict()
        assert d["decision_id"] == "dec-x"
        assert d["intent"] == "intent_x"
        assert d["reasoning"] == "reasoning_x"
        assert d["context_hash"] == "hash_x"
        assert d["confidence"] == 0.5
        assert d["deterministic_anchor"] == "ANCHOR"
        assert d["audit_status"] == "AUDITED"
        assert d["timestamp"] == "ts"
        assert d["metadata"] == {"k": "v"}

    def test_to_dict_keys_complete(self):
        entry = DecisionEntry("d", "i", "r", "h")
        d = entry.to_dict()
        expected_keys = {
            "decision_id", "intent", "reasoning", "context_hash",
            "confidence", "deterministic_anchor", "audit_status",
            "timestamp", "metadata",
        }
        assert set(d.keys()) == expected_keys


# ── DecisionLedger ───────────────────────────────────────────────

class TestDecisionLedger:
    def test_init_creates_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        assert ledger.ledger_dir.exists()
        assert ledger.ledger_file == brain / "ledger" / "decisions" / "decisions.jsonl"

    def test_record_decision(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(
            intent="test",
            reasoning="because",
            context_hash="hash1",
        )
        assert entry.decision_id.startswith("dec-")
        assert entry.intent == "test"
        assert ledger.ledger_file.exists()
        lines = ledger.ledger_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["decision_id"] == entry.decision_id

    def test_record_decision_with_metadata(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(
            intent="deploy",
            reasoning="ready",
            context_hash="h2",
            confidence=0.9,
            deterministic_anchor="SHA",
            audit_status="APPROVED",
            metadata={"env": "staging"},
        )
        assert entry.confidence == 0.9
        assert entry.deterministic_anchor == "SHA"
        assert entry.audit_status == "APPROVED"
        assert entry.metadata == {"env": "staging"}

    def test_record_multiple_decisions(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        for i in range(5):
            ledger.record_decision(intent=f"i{i}", reasoning="r", context_hash="h")
        all_entries = ledger.list_all()
        assert len(all_entries) == 5

    def test_update_audit_status_found(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="i", reasoning="r", context_hash="h")
        found = ledger.update_audit_status(entry.decision_id, "APPROVED", auditor_notes="ok")
        assert found is True
        retrieved = ledger.get_decision(entry.decision_id)
        assert retrieved.audit_status == "APPROVED"
        assert retrieved.metadata["auditor_notes"] == "ok"

    def test_update_audit_status_not_found(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        found = ledger.update_audit_status("nonexistent", "APPROVED")
        assert found is False

    def test_update_audit_status_no_notes(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="i", reasoning="r", context_hash="h")
        found = ledger.update_audit_status(entry.decision_id, "REJECTED")
        assert found is True
        retrieved = ledger.get_decision(entry.decision_id)
        assert retrieved.audit_status == "REJECTED"

    def test_update_audit_status_file_not_exists(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        # Don't record anything, file doesn't exist yet
        result = ledger.update_audit_status("dec-x", "APPROVED")
        assert result is False

    def test_get_decision_found(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="i", reasoning="r", context_hash="h")
        retrieved = ledger.get_decision(entry.decision_id)
        assert retrieved is not None
        assert retrieved.decision_id == entry.decision_id

    def test_get_decision_not_found(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        retrieved = ledger.get_decision("nonexistent")
        assert retrieved is None

    def test_get_decision_file_not_exists(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        retrieved = ledger.get_decision("x")
        assert retrieved is None

    def test_list_recent(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        for i in range(15):
            ledger.record_decision(intent=f"i{i}", reasoning="r", context_hash="h")
        recent = ledger.list_recent(limit=5)
        assert len(recent) == 5
        # Should be the last 5
        assert recent[-1]["intent"] == "i14"

    def test_list_recent_empty(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        recent = ledger.list_recent()
        assert recent == []

    def test_list_recent_file_not_exists(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        assert ledger.list_recent() == []

    def test_list_all(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        for i in range(3):
            ledger.record_decision(intent=f"i{i}", reasoning="r", context_hash="h")
        all_entries = ledger.list_all()
        assert len(all_entries) == 3

    def test_list_all_empty(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        assert ledger.list_all() == []

    def test_list_all_file_not_exists(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        assert ledger.list_all() == []


# ── EngramVault ──────────────────────────────────────────────────

class TestEngramVault:
    def test_init_creates_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        assert vault.vault_dir.exists()
        assert vault.vault_file == brain / "session" / "sess1" / "vault.jsonl"

    def test_deposit(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        vault.deposit(key="k1", value="v1", source_agent="agent_a")
        assert vault.vault_file.exists()
        lines = vault.vault_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["key"] == "k1"
        assert data["value"] == "v1"
        assert data["source_agent"] == "agent_a"
        assert "timestamp" in data

    def test_deposit_with_metadata(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        vault.deposit(key="k2", value="v2", source_agent="agent_b", metadata={"tag": "test"})
        entries = vault.list_all()
        assert entries[0]["metadata"] == {"tag": "test"}

    def test_deposit_metadata_none(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        vault.deposit(key="k", value="v", source_agent="a", metadata=None)
        entries = vault.list_all()
        assert entries[0]["metadata"] == {}

    def test_list_all(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        for i in range(3):
            vault.deposit(key=f"k{i}", value=f"v{i}", source_agent="a")
        entries = vault.list_all()
        assert len(entries) == 3

    def test_list_all_empty(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        assert vault.list_all() == []

    def test_list_all_file_not_exists(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        assert vault.list_all() == []

    def test_list_all_skips_blank_lines(self, tmp_path):
        brain = tmp_path / "brain"
        vault = EngramVault(session_id="sess1", brain_path=brain)
        vault.deposit(key="k1", value="v1", source_agent="a")
        # Append a blank line
        with open(vault.vault_file, "a") as f:
            f.write("\n")
        entries = vault.list_all()
        assert len(entries) == 1


# ── SessionStateManager ──────────────────────────────────────────

class TestSessionStateManager:
    def test_init_creates_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        mgr = SessionStateManager(session_id="sess1", brain_path=brain)
        assert mgr.state_file.parent.exists()
        assert mgr.state_file == brain / "session" / "sess1" / "state.json"

    def test_save_state(self, tmp_path):
        brain = tmp_path / "brain"
        mgr = SessionStateManager(session_id="sess1", brain_path=brain)
        mgr.save_state(stats={"tasks": 5}, metadata={"env": "test"})
        assert mgr.state_file.exists()
        data = json.loads(mgr.state_file.read_text())
        assert data["session_id"] == "sess1"
        assert data["stats"] == {"tasks": 5}
        assert data["metadata"] == {"env": "test"}
        assert "last_updated" in data

    def test_save_state_no_metadata(self, tmp_path):
        brain = tmp_path / "brain"
        mgr = SessionStateManager(session_id="sess1", brain_path=brain)
        mgr.save_state(stats={"x": 1})
        data = json.loads(mgr.state_file.read_text())
        assert data["metadata"] == {}

    def test_load_state(self, tmp_path):
        brain = tmp_path / "brain"
        mgr = SessionStateManager(session_id="sess1", brain_path=brain)
        mgr.save_state(stats={"tasks": 10})
        loaded = mgr.load_state()
        assert loaded is not None
        assert loaded["stats"] == {"tasks": 10}
        assert loaded["session_id"] == "sess1"

    def test_load_state_not_exists(self, tmp_path):
        brain = tmp_path / "brain"
        mgr = SessionStateManager(session_id="sess1", brain_path=brain)
        assert mgr.load_state() is None

    def test_load_state_corrupt(self, tmp_path):
        brain = tmp_path / "brain"
        mgr = SessionStateManager(session_id="sess1", brain_path=brain)
        mgr.state_file.parent.mkdir(parents=True, exist_ok=True)
        mgr.state_file.write_text("not valid json{{{")
        assert mgr.load_state() is None
