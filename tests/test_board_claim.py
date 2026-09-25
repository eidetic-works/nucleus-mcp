"""Tests for `nucleus_board(action='claim')` — atomic claim sentinel + recall bridge."""

import json
import os
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain"
    (b / "relay" / "board").mkdir(parents=True)
    os.environ["NUCLEUS_BRAIN_PATH"] = str(b)
    yield b
    os.environ.pop("NUCLEUS_BRAIN_PATH", None)
    os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    os.environ.pop("CC_SESSION_ROLE", None)


def _seed_post(brain):
    from mcp_server_nucleus.runtime.board_ops import post

    res = post(
        subject="seed",
        body={"summary": "x"},
        tags=["tribal-knowledge:r2"],
        from_role="main",
    )
    return res["board_id"]


class TestAtomicClaim:
    def test_first_claim_wins(self, brain):
        from mcp_server_nucleus.runtime.board_ops import claim

        bid = _seed_post(brain)
        r1 = claim(board_id=bid, claimer_role="peer")
        assert r1["ok"] is True
        assert r1["claimer_role"] == "peer"
        # Sentinel exists
        sentinel = brain / "relay" / "board" / "_claims" / f"{bid}.claimed"
        assert sentinel.exists() and sentinel.is_dir()

    def test_second_claim_rejected(self, brain):
        from mcp_server_nucleus.runtime.board_ops import claim

        bid = _seed_post(brain)
        claim(board_id=bid, claimer_role="peer")
        r2 = claim(board_id=bid, claimer_role="cc-tb")
        assert r2["ok"] is False
        assert r2["error"] == "already_claimed"
        assert r2["already_claimed_by"] == "peer"

    def test_post_status_updated(self, brain):
        from mcp_server_nucleus.runtime.board_ops import claim, list_posts

        bid = _seed_post(brain)
        claim(board_id=bid, claimer_role="peer")
        posts = list_posts(status="claimed")
        assert len(posts) == 1
        assert posts[0]["board_id"] == bid
        assert posts[0]["claimed_by"] == "peer"
        assert posts[0]["claimed_at"]

    def test_unknown_board_id_returns_not_found(self, brain):
        from mcp_server_nucleus.runtime.board_ops import claim

        r = claim(board_id="board_nope", claimer_role="peer")
        assert r["ok"] is False
        assert r["error"] == "not_found"


class TestRecallBridge:
    def test_no_module_returns_empty_recall(self, brain):
        from mcp_server_nucleus.runtime.board_ops import claim

        bid = _seed_post(brain)
        r = claim(board_id=bid, claimer_role="peer")
        # nucleus_wedge.memories does not expose nucleus_wedge__recall_activity
        # on this branch — should degrade silently to [].
        assert r["recall_results"] == []

    def test_calls_recall_activity_when_available(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime import board_ops

        bid = _seed_post(brain)
        # Monkey-patch the import target the bridge uses.
        from nucleus_wedge import memories as memmod

        captured = {}

        def fake_recall(role, domain):
            captured["role"] = role
            captured["domain"] = domain
            return [{"content": "old r2 lesson", "role": role}]

        monkeypatch.setattr(
            memmod, "nucleus_wedge__recall_activity", fake_recall, raising=False
        )
        try:
            r = board_ops.claim(board_id=bid, claimer_role="peer")
            assert r["ok"] is True
            assert captured["role"] == "peer"
            assert captured["domain"] == "r2"
            assert r["recall_results"] == [
                {"content": "old r2 lesson", "role": "peer"}
            ]
        finally:
            if hasattr(memmod, "nucleus_wedge__recall_activity"):
                delattr(memmod, "nucleus_wedge__recall_activity")


class TestRoleAutofill:
    def test_env_var_used_when_arg_missing(self, brain):
        from mcp_server_nucleus.runtime.board_ops import claim

        bid = _seed_post(brain)
        os.environ["CC_SESSION_ROLE"] = "cc-tb"
        r = claim(board_id=bid)
        assert r["ok"] is True
        assert r["claimer_role"] == "cc-tb"
