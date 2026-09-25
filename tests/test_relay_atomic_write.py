"""Regression tests for atomic relay message writes (audit finding H7).

Bug: `relay_post` wrote each message with a single `path.write_text(...)`
straight to the final `<ts>_<id>.json` path. A subscriber globbing `*.json`
could read the file mid-write (empty/partial JSON) and permanently drop the
message on a parse failure.

Fix: stage to a hidden sibling `.<name>.tmp` (never matches the readers'
`*.json` glob) then `os.replace()` (atomic on POSIX and Windows). Readers
therefore see either nothing or a complete file — never a partial one.
"""

import json

import pytest

from mcp_server_nucleus.runtime.relay_ops import relay_post


@pytest.fixture
def brain(tmp_path, monkeypatch):
    b = tmp_path / "brain"
    b.mkdir()
    (b / "relay").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


def test_post_lands_complete_and_leaves_no_tmp(brain):
    """Happy path: the message is a complete *.json with no leftover staging file."""
    relay_post(to="cowork", subject="s", body="hello-atomic",
               sender="test_sender", force_fs=True)
    inbox = brain / "relay" / "cowork"

    json_files = list(inbox.glob("*.json"))
    assert len(json_files) == 1
    msg = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert msg["body"] == "hello-atomic"

    # No staging artifacts left behind (hidden .tmp siblings).
    assert list(inbox.glob("*.tmp")) == []
    assert [p for p in inbox.iterdir() if p.name.endswith(".tmp")] == []


def test_failed_rename_leaves_no_partial_json(brain, monkeypatch):
    """If the atomic publish step fails, readers must see ZERO *.json files.

    This is the core reader-safety invariant: a partial write must never be
    visible under the `*.json` glob that every reader uses.
    """
    from mcp_server_nucleus.runtime.relay import core

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated crash during atomic publish")

    monkeypatch.setattr(core.os, "replace", _boom)

    # Tolerate either propagation or internal handling — the invariant below
    # is what matters.
    try:
        relay_post(to="cowork", subject="s", body="should-not-be-visible",
                   sender="test_sender", force_fs=True)
    except Exception:
        pass

    inbox = brain / "relay" / "cowork"
    if inbox.exists():
        assert list(inbox.glob("*.json")) == [], \
            "a partial/never-published message leaked into the readers' glob"
