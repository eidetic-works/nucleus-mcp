"""The relay read/ack/status routes must check mailbox ownership (RL-1).

`post_relay` has always compared the envelope's sender against the token owner.
The read, ack and status handlers only checked that the token existed in the map,
so any valid token could read any other agent's inbox, ack their messages out from
under them, or enumerate their traffic. `docs/relay_bus_contract.md` publishes the
recipient names in use on a shared deployment, so there was nothing to guess.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROUTE = (Path(__file__).resolve().parents[1] / "src" / "mcp_server_nucleus"
         / "http_transport" / "relay_route.py")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Reads or mutates a named mailbox, so it must prove the caller owns it.
GUARDED = ["get_relay", "ack_relay", "get_relay_status"]


def _handler(name: str) -> ast.AST:
    tree = ast.parse(ROUTE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    pytest.fail(f"relay_route.py has no {name}()")


@pytest.mark.parametrize("name", GUARDED)
def test_mailbox_handlers_check_ownership(name):
    calls = [
        n for n in ast.walk(_handler(name))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "_owns_inbox"
    ]
    assert calls, (
        f"{name}() never calls _owns_inbox. It resolves a recipient from the URL "
        f"path and serves it on nothing but 'this token exists', so any valid token "
        f"reaches any agent's mailbox."
    )


def test_post_relay_is_not_ownership_guarded():
    """post_relay must NOT have this guard — you post TO someone else's inbox.

    Written because the first attempt at the fix inserted the guard by pattern
    match and hit post_relay too, which would have made it impossible to send a
    message to anyone but yourself. The whole point of a relay.
    """
    calls = [
        n for n in ast.walk(_handler("post_relay"))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "_owns_inbox"
    ]
    assert not calls, (
        "post_relay checks the envelope's sender against the token owner, which is "
        "a different question from owning the destination mailbox. Guarding it on "
        "_owns_inbox would allow sending only to yourself."
    )


def test_owns_inbox_canonicalises_both_sides():
    from mcp_server_nucleus.http_transport import relay_route

    assert relay_route._owns_inbox("agent-a", "agent-a") is True
    assert relay_route._owns_inbox("agent-a", "agent-b") is False


def test_post_relay_still_compares_sender_to_token_owner():
    """The check RL-1 said was already there must stay there."""
    src = ast.unparse(_handler("post_relay"))
    assert "token_owner" in src and "resolve_canonical_inbox_name" in src, (
        "post_relay's sender-vs-owner comparison is the only thing stopping one "
        "agent forging another's messages"
    )
