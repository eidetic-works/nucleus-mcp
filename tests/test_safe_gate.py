"""Opposed-pair battery for the safe-to-propose gate.

Every case here is a way the gate could wrongly say YES. A gate is only worth
having if each of these is proven to say NO.
"""

from mcp_server_nucleus.runtime.agent_os.safe_gate import evaluate


def _v(confirmed=(), refuted=(), unverifiable=()):
    return {
        "confirmed": list(confirmed),
        "refuted": list(refuted),
        "unverifiable": list(unverifiable),
    }


def test_all_confirmed_and_path_allowed_is_safe():
    """POSITIVE: the gate must be able to say YES, or it is not a gate."""
    v = evaluate(_v(confirmed=["FILE EXISTS: docs/a.md"]), path_allowed=True)
    assert v.safe
    assert "verified" in v.explain()


def test_empty_claim_set_is_not_safe():
    """THE one that matters: all([]) is True in Python.

    A caller that emitted no claims -- because of a bug, a bad regex, or a
    silent failure upstream -- must not be handed a green light. This is the
    difference between the gate working and the gate being decorative.
    """
    v = evaluate(_v(), path_allowed=True)
    assert not v.safe
    assert "absence of evidence" in v.reason


def test_one_refuted_blocks_even_with_many_confirmed():
    v = evaluate(
        _v(confirmed=["FILE EXISTS: docs/a.md", "GIT BRANCH EXISTS: main"],
           refuted=["FILE EXISTS: docs/ghost.md"]),
        path_allowed=True,
    )
    assert not v.safe
    assert "REFUTED" in v.reason


def test_one_unverifiable_blocks():
    """UNVERIFIABLE is not a soft pass. Could-not-check is not checked."""
    v = evaluate(
        _v(confirmed=["FILE EXISTS: docs/a.md"],
           unverifiable=["tests passed, probably"]),
        path_allowed=True,
    )
    assert not v.safe
    assert "could NOT be verified" in v.reason


def test_unsafe_path_blocks_regardless_of_confirmed_claims():
    """No quantity of true claims licenses touching a deploy script."""
    v = evaluate(
        _v(confirmed=["FILE EXISTS: scripts/deploy.sh"] * 5),
        path_allowed=False,
        path_reason="scripts/ is denied",
    )
    assert not v.safe
    assert "denied" in v.reason


def test_path_gate_never_consulted_is_denied():
    """OPPOSED: omitting the path check must not read as permission.

    path_allowed=None means the caller never asked. A gate that assumes
    consent it was never given is worse than no gate, because it looks like
    one.
    """
    v = evaluate(_v(confirmed=["FILE EXISTS: docs/a.md"]))
    assert not v.safe
    assert "never consulted" in v.reason


def test_explain_names_the_blocking_claims():
    v = evaluate(
        _v(confirmed=["FILE EXISTS: docs/a.md"], refuted=["FILE EXISTS: nope.md"]),
        path_allowed=True,
    )
    text = v.explain()
    assert "nope.md" in text, "a blocked change must say WHICH claim failed"
    assert "Not safe" in text
