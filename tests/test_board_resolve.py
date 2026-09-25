"""Tests for `nucleus_board(action='resolve')` — status flip + activity engram bridge."""

import json
import os
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


def _seed_and_claim(brain, claimer="peer"):
    from mcp_server_nucleus.runtime.board_ops import claim, post

    r = post(
        subject="seed",
        body={"summary": "x"},
        tags=["tribal-knowledge:r2"],
        from_role="main",
    )
    bid = r["board_id"]
    claim(board_id=bid, claimer_role=claimer)
    return bid


class TestResolve:
    def test_updates_status(self, brain):
        from mcp_server_nucleus.runtime.board_ops import list_posts, resolve

        bid = _seed_and_claim(brain)
        r = resolve(
            board_id=bid, resolution="see PR #999", resolver_role="peer"
        )
        assert r["ok"] is True
        posts = list_posts(status="resolved")
        assert len(posts) == 1
        assert posts[0]["resolved_by"] == "peer"
        assert posts[0]["resolution"] == "see PR #999"

    def test_returns_correct_shape(self, brain):
        from mcp_server_nucleus.runtime.board_ops import resolve

        bid = _seed_and_claim(brain)
        r = resolve(
            board_id=bid, resolution="done", resolver_role="peer"
        )
        assert set(r.keys()) >= {
            "ok",
            "board_id",
            "file_path",
            "resolver_role",
            "engram_written",
        }
        assert Path(r["file_path"]).exists()

    def test_unknown_board_returns_not_found(self, brain):
        from mcp_server_nucleus.runtime.board_ops import resolve

        r = resolve(board_id="nope", resolution="x", resolver_role="peer")
        assert r["ok"] is False
        assert r["error"] == "not_found"


class TestEngramBridge:
    def test_no_module_returns_engram_false(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.board_ops import resolve
        import importlib
        try:
            memmod = importlib.import_module("nucleus_wedge.memories")
            if hasattr(memmod, "nucleus_wedge__write_activity"):
                monkeypatch.delattr(memmod, "nucleus_wedge__write_activity", raising=False)
        except ImportError:
            pass

        bid = _seed_and_claim(brain)
        r = resolve(board_id=bid, resolution="ok", resolver_role="peer")
        assert r["engram_written"] is False

    def test_writes_engram_when_available(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime import board_ops
        from nucleus_wedge import memories as memmod

        captured = {}

        def fake_write(role, content, tags):
            captured["role"] = role
            captured["content"] = content
            captured["tags"] = list(tags)

        monkeypatch.setattr(
            memmod, "nucleus_wedge__write_activity", fake_write, raising=False
        )
        try:
            bid = _seed_and_claim(brain)
            r = board_ops.resolve(
                board_id=bid,
                resolution="rotated keys via op-keyboard",
                resolver_role="peer",
            )
            assert r["engram_written"] is True
            assert captured["role"] == "peer"
            assert "rotated keys" in captured["content"]
            assert "role:peer" in captured["tags"]
            assert "domain:r2" in captured["tags"]
            assert "source:board-resolution" in captured["tags"]
        finally:
            if hasattr(memmod, "nucleus_wedge__write_activity"):
                delattr(memmod, "nucleus_wedge__write_activity")


class TestRoleAutofill:
    def test_env_var_used(self, brain):
        from mcp_server_nucleus.runtime.board_ops import resolve

        bid = _seed_and_claim(brain)
        os.environ["CC_SESSION_ROLE"] = "cc-tb"
        r = resolve(board_id=bid, resolution="done")
        assert r["ok"] is True
        assert r["resolver_role"] == "cc-tb"
