"""
Test Suite: A9 federation-sync anchoring (NUCLEUS_FEDERATION_ANCHOR)
======================================================================
docs/verifier/HANDOFF_BACKLOG.md §A9 + AUDIT_FINDINGS.md rows #1/#2.

Row #1: NetworkManager._handle_connection's IPC token-verify call was
commented out — every federation RPC dispatched regardless of auth.
Row #2: ConsensusManager.handle_request_vote / handle_append_entries accept
an unbounded/unauthenticated term, so a single crafted RPC with a MAXINT
term can force this node's term arbitrarily high and hijack leader/merge
authority via _become_leader.

Flag NUCLEUS_FEDERATION_ANCHOR gates both fixes; default OFF must remain
byte-identical (legacy hole demonstrably still open) while ON must forge-shut
both holes:
  - an RPC with an invalid/missing IPC token is rejected when flag ON
    (accepted when OFF = legacy);
  - a forged out-of-bounds (MAXINT) term does not clobber state.term /
    leader_id / vote_granted when flag ON (does clobber when OFF = legacy).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.federation import (
    FederationConfig,
    FederationEngine,
    RaftState,
    _MAX_RAFT_TERM,
    _federation_anchor_on,
    _term_in_bounds,
)
from mcp_server_nucleus.runtime.auth.ipc_provider import IPCAuthProvider


@pytest.fixture
def engine(tmp_path):
    config = FederationConfig(brain_id="a9-brain", brain_path=tmp_path / ".brain")
    return FederationEngine(config)


@pytest.fixture
def fresh_auth_provider(tmp_path, monkeypatch):
    """Point federation.get_ipc_auth_manager() at a throwaway provider so
    tokens issued/consumed here never leak into the process-wide singleton
    used by other test modules."""
    import mcp_server_nucleus.runtime.federation as federation_mod

    provider = IPCAuthProvider(brain_path=tmp_path / ".brain_auth")
    monkeypatch.setattr(federation_mod, "get_ipc_auth_manager", lambda: provider)
    return provider


# ─────────────────────────────────────────────────────────────────
# _term_in_bounds unit checks
# ─────────────────────────────────────────────────────────────────

class TestTermInBounds:
    def test_normal_term_in_bounds(self):
        assert _term_in_bounds(0) is True
        assert _term_in_bounds(42) is True
        assert _term_in_bounds(_MAX_RAFT_TERM) is True

    def test_maxint_style_term_rejected(self):
        assert _term_in_bounds(_MAX_RAFT_TERM + 1) is False
        assert _term_in_bounds(2**63 - 1) is False
        assert _term_in_bounds(2**128) is False

    def test_negative_term_rejected(self):
        assert _term_in_bounds(-1) is False

    def test_non_int_term_rejected(self):
        assert _term_in_bounds("999999999999") is False
        assert _term_in_bounds(3.5) is False
        assert _term_in_bounds(None) is False
        assert _term_in_bounds(True) is False  # bool is an int subclass; must not pass


# ─────────────────────────────────────────────────────────────────
# Row #1 — IPC token verification (NetworkManager)
# ─────────────────────────────────────────────────────────────────

class TestIPCTokenVerification:
    def test_flag_off_accepts_missing_token(self, engine, monkeypatch):
        """Legacy no-op: with the flag off, a message with no token dispatches
        (mirrors the historical commented-out check — never enforced)."""
        monkeypatch.delenv("NUCLEUS_FEDERATION_ANCHOR", raising=False)
        assert _federation_anchor_on() is False
        accepted, reason = engine.network._verify_federation_token({"type": "raft_vote"})
        assert accepted is True
        assert reason == "flag-off"

    def test_flag_off_accepts_forged_token(self, engine, monkeypatch):
        monkeypatch.delenv("NUCLEUS_FEDERATION_ANCHOR", raising=False)
        accepted, _ = engine.network._verify_federation_token(
            {"type": "raft_vote", "token": "totally-forged-not-issued"}
        )
        assert accepted is True

    def test_flag_on_rejects_missing_token(self, engine, monkeypatch, fresh_auth_provider):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        assert _federation_anchor_on() is True
        accepted, reason = engine.network._verify_federation_token({"type": "raft_vote"})
        assert accepted is False
        assert "missing" in reason

    def test_flag_on_rejects_forged_token(self, engine, monkeypatch, fresh_auth_provider):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        accepted, reason = engine.network._verify_federation_token(
            {"type": "raft_vote", "token": "ipc-forged-0000000000"}
        )
        assert accepted is False

    def test_flag_on_accepts_valid_single_use_token(self, engine, monkeypatch, fresh_auth_provider):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        token = fresh_auth_provider.issue_token(scope="federation_ipc")

        accepted, reason = engine.network._verify_federation_token(
            {"type": "raft_vote", "token": token.token_id}
        )
        assert accepted is True
        assert reason == "ok"

        # Single-use: the same token cannot be replayed for a second RPC.
        accepted_again, reason_again = engine.network._verify_federation_token(
            {"type": "raft_vote", "token": token.token_id}
        )
        assert accepted_again is False
        assert "consumed" in reason_again.lower()

    def test_stamp_then_verify_roundtrip_when_flag_on(self, engine, monkeypatch, fresh_auth_provider):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        message = {"type": "ping"}
        engine.network._stamp_federation_token(message)
        assert "token" in message

        accepted, _ = engine.network._verify_federation_token(message)
        assert accepted is True

    def test_stamp_is_noop_when_flag_off(self, engine, monkeypatch):
        monkeypatch.delenv("NUCLEUS_FEDERATION_ANCHOR", raising=False)
        message = {"type": "ping"}
        engine.network._stamp_federation_token(message)
        assert "token" not in message


# ─────────────────────────────────────────────────────────────────
# Row #2 — Raft term bounding (ConsensusManager)
# ─────────────────────────────────────────────────────────────────

class TestRaftTermBounding:
    @pytest.mark.asyncio
    async def test_flag_off_forged_maxint_term_clobbers_vote(self, engine, monkeypatch):
        """Demonstrates the legacy hole: with the flag off, a forged MAXINT
        term is adopted verbatim and a vote is granted to an unauthenticated
        candidate_id."""
        monkeypatch.delenv("NUCLEUS_FEDERATION_ANCHOR", raising=False)
        assert engine.state.term == 0

        forged_term = _MAX_RAFT_TERM + 999
        resp = await engine.consensus.handle_request_vote(
            {"term": forged_term, "candidate_id": "attacker", "last_log_index": 0, "last_log_term": 0}
        )
        assert resp["vote_granted"] is True
        assert engine.state.term == forged_term  # clobbered
        assert engine.state.voted_for == "attacker"

    @pytest.mark.asyncio
    async def test_flag_on_forged_maxint_term_rejected_by_vote(self, engine, monkeypatch):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        assert engine.state.term == 0

        forged_term = _MAX_RAFT_TERM + 999
        resp = await engine.consensus.handle_request_vote(
            {"term": forged_term, "candidate_id": "attacker", "last_log_index": 0, "last_log_term": 0}
        )
        assert resp["vote_granted"] is False
        assert engine.state.term == 0  # not clobbered
        assert engine.state.voted_for is None

    @pytest.mark.asyncio
    async def test_flag_on_rejects_negative_and_non_int_term_for_vote(self, engine, monkeypatch):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")

        resp_neg = await engine.consensus.handle_request_vote(
            {"term": -5, "candidate_id": "attacker"}
        )
        assert resp_neg["vote_granted"] is False
        assert engine.state.term == 0

        resp_str = await engine.consensus.handle_request_vote(
            {"term": "99999999999999999999", "candidate_id": "attacker"}
        )
        assert resp_str["vote_granted"] is False
        assert engine.state.term == 0

    @pytest.mark.asyncio
    async def test_flag_on_still_grants_vote_for_legit_term(self, engine, monkeypatch):
        """A9 must not break the legitimate election path."""
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        resp = await engine.consensus.handle_request_vote(
            {"term": 1, "candidate_id": "honest-peer", "last_log_index": 0, "last_log_term": 0}
        )
        assert resp["vote_granted"] is True
        assert engine.state.term == 1
        assert engine.state.voted_for == "honest-peer"

    @pytest.mark.asyncio
    async def test_flag_off_forged_maxint_term_clobbers_append_entries(self, engine, monkeypatch):
        monkeypatch.delenv("NUCLEUS_FEDERATION_ANCHOR", raising=False)
        assert engine.state.term == 0

        forged_term = _MAX_RAFT_TERM + 999
        resp = await engine.consensus.handle_append_entries(
            {"term": forged_term, "leader_id": "attacker", "prev_log_index": 0, "prev_log_term": 0, "entries": []}
        )
        assert resp["success"] is True
        assert engine.state.term == forged_term  # clobbered
        assert engine.state.leader_id == "attacker"  # merge authority hijacked

    @pytest.mark.asyncio
    async def test_flag_on_forged_maxint_term_rejected_by_append_entries(self, engine, monkeypatch):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        assert engine.state.term == 0
        assert engine.state.leader_id is None

        forged_term = _MAX_RAFT_TERM + 999
        resp = await engine.consensus.handle_append_entries(
            {"term": forged_term, "leader_id": "attacker", "prev_log_index": 0, "prev_log_term": 0, "entries": []}
        )
        assert resp["success"] is False
        assert engine.state.term == 0  # not clobbered
        assert engine.state.leader_id is None  # merge authority not hijacked

    @pytest.mark.asyncio
    async def test_flag_on_still_accepts_legit_append_entries(self, engine, monkeypatch):
        monkeypatch.setenv("NUCLEUS_FEDERATION_ANCHOR", "1")
        resp = await engine.consensus.handle_append_entries(
            {"term": 1, "leader_id": "honest-leader", "prev_log_index": 0, "prev_log_term": 0, "entries": []}
        )
        assert resp["success"] is True
        assert engine.state.term == 1
        assert engine.state.leader_id == "honest-leader"
