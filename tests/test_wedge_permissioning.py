"""Write scopes: an agent must not be able to rewrite org-wide context.

The talk is blunt about why this is the dangerous one: "think about one agent
running into a problem and deciding to write to the organizational wide context
which every other agent is currently reading from. If something was incorrect
there, that would scale to all of your agents and be pretty disastrous." The
prescription is tiers — org-wide read-only to agents, a scratchpad writable.

Measured before this change: 0 hits for read_only|immutable|write_protect
anywhere in nucleus_wedge. There were no tiers at all; every writer could write
anything.

THE BYPASS THIS MUST CLOSE. If an agent can choose the scope it writes at, the
guard is theatre — it just writes `scope="agent"` over an org key, or declares
its own new key org-scoped. So the scope is FIXED AT KEY CREATION, inherited by
every later write to that key, and only the operator may create an org key.
An agent cannot escalate, cannot downgrade, and cannot launder.

BACKWARD COMPATIBILITY IS NOT OPTIONAL HERE. 30,744 records already exist with
no scope field. A missing scope must read as permissive, exactly as this repo
already treats a missing `origin` ("unknown origin means unknown, not 'other
repo'"). A guard that bricks the existing corpus gets deleted, and then there is
no guard.
"""
from __future__ import annotations

import pytest

from nucleus_wedge.store import PermissionDenied, Store


@pytest.fixture()
def brain(tmp_path):
    return tmp_path / ".brain"


def _agent(brain):
    return Store(brain_path=brain, writer="agent")


def _operator(brain):
    return Store(brain_path=brain, writer="operator")


# ── MUST REFUSE ────────────────────────────────────────────────────────────


def test_an_agent_cannot_write_an_existing_org_key(brain):
    _operator(brain).append("the house style", key="style", scope="org")
    with pytest.raises(PermissionDenied):
        _agent(brain).append("my own idea of style", key="style")


def test_an_agent_cannot_create_an_org_key(brain):
    """The obvious bypass: declare your own key org-scoped."""
    with pytest.raises(PermissionDenied):
        _agent(brain).append("pretending to be policy", key="new", scope="org")


def test_an_agent_cannot_escalate_an_existing_key(brain):
    _agent(brain).append("scratch", key="k")
    with pytest.raises(PermissionDenied):
        _agent(brain).append("now it is policy", key="k", scope="org")


def test_an_agent_cannot_downgrade_an_org_key(brain):
    """The subtler bypass: relabel it agent-scoped, then write it freely."""
    _operator(brain).append("the house style", key="style", scope="org")
    with pytest.raises(PermissionDenied):
        _agent(brain).append("mine now", key="style", scope="agent")


def test_a_refused_write_appends_nothing(brain):
    _operator(brain).append("the house style", key="style", scope="org")
    before = len(list(_operator(brain).rows()))
    with pytest.raises(PermissionDenied):
        _agent(brain).append("nope", key="style")
    assert len(list(_operator(brain).rows())) == before


def test_the_refusal_names_the_scope_and_the_writer(brain):
    _operator(brain).append("x", key="style", scope="org")
    with pytest.raises(PermissionDenied) as e:
        _agent(brain).append("y", key="style")
    assert "org" in str(e.value) and "agent" in str(e.value)


# ── MUST ALLOW ─────────────────────────────────────────────────────────────


def test_an_agent_writes_its_own_scratchpad(brain):
    _agent(brain).append("a note to self", key="scratch")
    assert _agent(brain).head_value("scratch") == "a note to self"


def test_the_operator_writes_org(brain):
    _operator(brain).append("the house style", key="style", scope="org")
    assert _operator(brain).head_value("style") == "the house style"


def test_an_agent_can_READ_org(brain):
    """Reads are never gated. Org context exists to be read by everyone."""
    _operator(brain).append("the house style", key="style", scope="org")
    assert _agent(brain).head_value("style") == "the house style"
    assert _agent(brain).head_hash("style") != "absent"


def test_the_operator_may_still_update_an_agent_key(brain):
    _agent(brain).append("scratch", key="k")
    _operator(brain).append("corrected", key="k")
    assert _operator(brain).head_value("k") == "corrected"


# ── backward compatibility ─────────────────────────────────────────────────


def test_the_default_writer_is_unrestricted(brain):
    """CONTROL. Every existing caller constructs Store() with no writer and must
    be unaffected — 30,744 records and dozens of call sites."""
    s = Store(brain_path=brain)
    s.append("anything", key="k")
    assert s.head_value("k") == "anything"


def test_a_record_with_no_scope_is_writable(brain):
    """The existing corpus has no scope field. Missing must read as permissive,
    like a missing `origin` already does here."""
    Store(brain_path=brain).append("legacy row", key="old")
    _agent(brain).append("an agent updates it", key="old")
    assert _agent(brain).head_value("old") == "an agent updates it"


def test_scope_defaults_to_agent_on_a_new_key(brain):
    _agent(brain).append("v", key="fresh")
    rec = [r for r in _agent(brain).rows() if r["key"] == "fresh"][-1]
    assert rec["snapshot"]["scope"] == "agent"


# ── interaction with the gates already shipped ─────────────────────────────


def test_permissioning_does_not_break_compare_and_swap(brain):
    o = _operator(brain)
    o.append("v1", key="style", scope="org")
    h = o.head_hash("style")
    o.append("v2", key="style", expected_hash=h)
    assert o.head_value("style") == "v2"


def test_an_agent_cannot_rollback_an_org_key(brain):
    """Rollback is an append. It must obey the same rule, or it is the bypass."""
    o = _operator(brain)
    o.append("good", key="style", scope="org")
    o.append("bad", key="style")
    with pytest.raises(PermissionDenied):
        _agent(brain).rollback(key="style", to_version=1)
