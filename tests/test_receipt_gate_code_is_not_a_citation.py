"""Brackets inside code are syntax, not citations.

Why this exists: on 2026-08-21 the receipt gate blocked a response with

    receipt gate BLOCK -- this response cites source(s) with bracket syntax

The response made ZERO citations. It contained Python:

    decidable = [s for s in t1_sigs if not s.get("insufficient")]

`_CITATION_RE` matches `[ anything ]`, which is also list/subscript syntax.
Verified against the live regex: that comprehension MATCHES; `all([])` does not
(empty brackets).

The fix narrows the SCAN REGION, never the pattern. That distinction is the
whole point -- weakening `_CITATION_RE` would cost real detection, while
excluding code costs none. The gate already made exactly this move: it scans
only the answer so the receipt's own [VERDICT] brackets are not read as new
citations. Code is the second region where brackets mean something else.

The tests that matter here are the MUST-BLOCK ones. A guard relaxed to stop
being annoying is how a real guard becomes decorative, and this file exists so
that relaxation is caught rather than discovered later.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_GATE = _REPO / ".brain/strategy/north_star/agent_integration/receipt_gate.py"
_LIB = _REPO / ".brain/strategy/north_star/research_vertical/lib"

pytestmark = pytest.mark.skipif(
    not _GATE.exists() or not _LIB.exists(),
    reason="receipt gate lives under .brain (gitignored); absent in a fresh clone",
)


def _load():
    sys.path.insert(0, str(_LIB))
    import claim_extract as ce
    spec = importlib.util.spec_from_file_location("receipt_gate", _GATE)
    rg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rg)
    return ce, rg


def _blocks(text: str) -> bool:
    ce, rg = _load()
    return bool(ce._CITATION_RE.search(rg._strip_code_regions(text)))


def test_a_fenced_python_block_is_not_a_citation():
    """THE FALSE POSITIVE, verbatim from the response that was blocked."""
    text = ('Here is the fix:\n```python\n'
            'decidable = [s for s in t1_sigs if not s.get("insufficient")]\n'
            '```\nThat is all.')
    assert not _blocks(text)


def test_inline_code_is_not_a_citation():
    assert not _blocks("The verdict is `[s for s in sigs]` at line 108.")


def test_a_real_citation_in_prose_still_blocks():
    """MUST BLOCK. If this fails the guard has been gutted, not narrowed."""
    assert _blocks('The sky is blue [doc1: "the sky is blue"].')


def test_a_bare_bracket_id_still_blocks():
    """MUST BLOCK: the `[id]` form carries no quote and is easy to lose."""
    assert _blocks("Revocation is handled elsewhere [jwt_provider].")


def test_a_citation_ALONGSIDE_code_still_blocks():
    """MUST BLOCK, and the sharpest control: stripping code must not create a
    hiding place. A response that cites a source AND shows code still owes a
    receipt."""
    assert _blocks("Per [doc1], see:\n```py\nx = [1]\n```")


def test_the_premise_the_regex_really_does_match_a_comprehension():
    """CONTROL: the entire fix rests on this. If _CITATION_RE stops matching
    list syntax, the scan-region narrowing is unnecessary and should be
    revisited rather than left as cargo."""
    ce, _ = _load()
    assert ce._CITATION_RE.search('[s for s in t1_sigs if not s.get("x")]')
    assert not ce._CITATION_RE.search("all([])")
