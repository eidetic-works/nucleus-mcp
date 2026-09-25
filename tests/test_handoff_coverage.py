"""Coverage tests for runtime/handoff.py."""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import handoff as handoff_mod
from mcp_server_nucleus.runtime.handoff import HandoffLedger, HandoffToken
from mcp_server_nucleus.runtime.auth import signature_guard as sg_mod


@pytest.fixture(autouse=True)
def _reset_guard():
    # reset singleton so each test uses the current brain path
    sg_mod._guard = None
    yield
    sg_mod._guard = None


def test_handoff_token_basic():
    t = HandoffToken(session_id="s1", source_agent="a", target_agent="b", intent="do x")
    assert t.handoff_id.startswith("hnd-")
    assert t.session_id == "s1"
    assert t.source_agent == "a"
    assert t.target_agent == "b"
    assert t.intent == "do x"
    assert t.memory_pointer is None
    assert t.metadata == {}
    assert t.signature  # non-empty


def test_handoff_token_with_optional_fields():
    t = HandoffToken(
        session_id="s1",
        source_agent="a",
        target_agent="b",
        intent="do x",
        memory_pointer="mem://x",
        metadata={"k": "v"},
    )
    assert t.memory_pointer == "mem://x"
    assert t.metadata == {"k": "v"}


def test_handoff_token_to_dict():
    t = HandoffToken(session_id="s1", source_agent="a", target_agent="b", intent="x")
    d = t.to_dict()
    assert d["session_id"] == "s1"
    assert d["source_agent"] == "a"
    assert d["target_agent"] == "b"
    assert d["intent"] == "x"
    assert "signature" not in d


def test_handoff_token_to_signed_json():
    t = HandoffToken(session_id="s1", source_agent="a", target_agent="b", intent="x")
    s = t.to_signed_json()
    data = json.loads(s)
    assert data["signature"] == t.signature
    assert data["session_id"] == "s1"


def test_handoff_token_unique_ids():
    t1 = HandoffToken(session_id="s", source_agent="a", target_agent="b", intent="x")
    t2 = HandoffToken(session_id="s", source_agent="a", target_agent="b", intent="x")
    assert t1.handoff_id != t2.handoff_id


def test_ledger_record_and_list(tmp_path):
    ledger = HandoffLedger(session_id="sess1", brain_path=tmp_path)
    t = HandoffToken(session_id="sess1", source_agent="a", target_agent="b", intent="x")
    ledger.record_handoff(t)
    history = ledger.list_history()
    assert len(history) == 1
    assert history[0]["handoff_id"] == t.handoff_id


def test_ledger_list_history_empty(tmp_path):
    ledger = HandoffLedger(session_id="sess2", brain_path=tmp_path)
    assert ledger.list_history() == []


def test_ledger_list_history_skips_bad_lines(tmp_path):
    ledger = HandoffLedger(session_id="sess3", brain_path=tmp_path)
    ledger.ledger_file.write_text("not json\n\n{bad}\n")
    assert ledger.list_history() == []


def test_verify_and_load_valid(tmp_path):
    ledger = HandoffLedger(session_id="sess4", brain_path=tmp_path)
    t = HandoffToken(session_id="sess4", source_agent="a", target_agent="b", intent="x")
    signed = t.to_signed_json()
    data = ledger.verify_and_load(signed)
    assert data is not None
    assert data["handoff_id"] == t.handoff_id


def test_verify_and_load_missing_signature(tmp_path):
    ledger = HandoffLedger(session_id="sess5", brain_path=tmp_path)
    payload = json.dumps({"handoff_id": "x", "session_id": "s"})
    assert ledger.verify_and_load(payload) is None


def test_verify_and_load_bad_signature(tmp_path):
    ledger = HandoffLedger(session_id="sess6", brain_path=tmp_path)
    t = HandoffToken(session_id="sess6", source_agent="a", target_agent="b", intent="x")
    signed = t.to_signed_json()
    # tamper signature
    data = json.loads(signed)
    data["signature"] = "a" * 32
    assert ledger.verify_and_load(json.dumps(data)) is None


def test_verify_and_load_invalid_json(tmp_path):
    ledger = HandoffLedger(session_id="sess7", brain_path=tmp_path)
    assert ledger.verify_and_load("not json") is None


def test_ledger_uses_default_brain_path(tmp_path, monkeypatch):
    monkeypatch.setattr(handoff_mod, "get_brain_path", lambda: tmp_path)
    ledger = HandoffLedger(session_id="sess8")
    assert ledger.brain_path == tmp_path
