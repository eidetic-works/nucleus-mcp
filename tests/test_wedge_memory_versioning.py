"""`version` was a field the schema advertised and never maintained.

`store.py` documents `"version": <int>` in the record shape and then writes a
literal `1` on every append, forever. Measured 2026-09-20: 0 increments and 0
rollback verbs anywhere in `nucleus_wedge`. A reader who trusted the field would
conclude every memory had been written exactly once.

That is worse than the field being absent. An absent field prompts a question; a
field that is always 1 answers it wrongly. It is the same shape as a gate that
cannot fail and a test suite green against a table that does not exist — a value
that looks like information and carries none.

WHAT "REAL" MEANS HERE, given an append-only log. The history is already on
disk: every append for a key is a row, in order. Nothing was lost — only
unnumbered. So `version` becomes the count of live records for that key, and
rollback is a NEW append carrying an older value, never a deletion. The log
stays append-only and an undo is itself auditable, which is the property the
talk's principle 1 actually asks for ("track who or what changed memory ... and
how to roll back").
"""
from __future__ import annotations

import pytest

from nucleus_wedge.store import ABSENT, Store


@pytest.fixture()
def store(tmp_path):
    return Store(brain_path=tmp_path / ".brain")


def _versions(s: Store, key: str):
    return [r["snapshot"]["version"] for r in s.rows() if r.get("key") == key]


# ── the defect ─────────────────────────────────────────────────────────────


def test_version_increments_across_writes(store):
    """THE control. Before this, all three were 1."""
    for v in ("first", "second", "third"):
        store.append(v, key="k")
    assert _versions(store, "k") == [1, 2, 3]


def test_version_is_per_key_not_global(store):
    store.append("a1", key="a")
    store.append("b1", key="b")
    store.append("a2", key="a")
    assert _versions(store, "a") == [1, 2]
    assert _versions(store, "b") == [1]


def test_first_write_is_version_one(store):
    store.append("only", key="k")
    assert _versions(store, "k") == [1]


def test_keyless_appends_do_not_share_a_version_line(store):
    """Auto-generated keys are distinct, so each is its own version 1."""
    store.append("x")
    store.append("y")
    assert all(r["snapshot"]["version"] == 1 for r in store.rows())


# ── rollback ───────────────────────────────────────────────────────────────


def test_rollback_restores_an_earlier_value(store):
    store.append("good", key="k")
    store.append("bad", key="k")
    store.rollback(key="k", to_version=1)
    assert store.head_value("k") == "good"


def test_rollback_appends_rather_than_deleting(store):
    """History is evidence. An undo that erases the mistake erases the record
    of the mistake, which is the opposite of an audit trail."""
    store.append("good", key="k")
    store.append("bad", key="k")
    before = len(list(store.rows()))
    store.rollback(key="k", to_version=1)
    after = list(store.rows())
    assert len(after) == before + 1
    assert any(r["snapshot"]["value"] == "bad" for r in after), "the bad value was erased"


def test_rollback_is_itself_versioned_and_labelled(store):
    store.append("good", key="k")
    store.append("bad", key="k")
    store.rollback(key="k", to_version=1)
    assert _versions(store, "k") == [1, 2, 3]
    head = [r for r in store.rows() if r.get("key") == "k"][-1]
    assert head["op_type"] == "ROLLBACK"


def test_rollback_to_an_unknown_version_is_refused(store):
    store.append("only", key="k")
    with pytest.raises(ValueError):
        store.rollback(key="k", to_version=7)


def test_rollback_on_an_unknown_key_is_refused(store):
    with pytest.raises(ValueError):
        store.rollback(key="never-written", to_version=1)


def test_rollback_is_reversible(store):
    """Rolling back a rollback returns the later value — because it is just
    another append, not a special case."""
    store.append("v1", key="k")
    store.append("v2", key="k")
    store.rollback(key="k", to_version=1)
    store.rollback(key="k", to_version=2)
    assert store.head_value("k") == "v2"


# ── interaction with the CAS gate (c550951c) ───────────────────────────────


def test_rollback_moves_the_head_hash(store):
    store.append("v1", key="k")
    store.append("v2", key="k")
    before = store.head_hash("k")
    store.rollback(key="k", to_version=1)
    assert store.head_hash("k") != before


def test_a_guarded_write_still_works_after_a_rollback(store):
    """CONTROL: versioning must not break compare-and-swap."""
    store.append("v1", key="k")
    store.rollback(key="k", to_version=1)
    h = store.head_hash("k")
    store.append("v2", key="k", expected_hash=h)
    assert store.head_value("k") == "v2"
