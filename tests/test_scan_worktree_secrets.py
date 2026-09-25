"""The secret scanner must fire on a real key and stay silent on a test fixture.

`publish_readiness.sh` step 1 FAILED on a clean tree: the anthropic pattern was
`sk-ant-[A-Za-z0-9\\-_]{20,}`, and this repo's own fixtures — `sk-ant-oat01-AbCdEfGh-`,
`sk-ant-...-SCRUBBED`, `sk-ant-sid02-stub` — matched it. A gate that cannot pass on
a clean tree is a gate people learn to bypass, and then it is off for the real case
too.

The fix narrows on the property that separates a real key from a fixture — LENGTH,
~100 characters against a fixture's 17 to 51 — rather than on which file the string
sits in. A path allowlist would exempt exactly these three test files, which is
where someone is most likely to paste a genuine token while debugging; length
narrowing keeps every path covered.

No literal full-length key is written to this file. The positive control builds one
at runtime from parts, so the scanner cannot be made to fire on its own test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "scan_worktree_secrets", PKG_ROOT / "scripts" / "scan_worktree_secrets.py")
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


def _pattern(name: str):
    for label, rx in scanner.PATTERNS:
        if label == name:
            return rx
    raise AssertionError(f"no pattern named {name!r}; the scanner lost a rule")


def _realistic_anthropic_key() -> str:
    """Assembled at runtime so no literal key exists in this file."""
    body = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789" * 3   # 108 chars
    return "sk-" + "ant-" + "api03-" + body


# --- the positive control: a real-shaped key MUST be caught ----------------

def test_a_realistic_key_is_detected():
    assert _pattern("anthropic key").search(_realistic_anthropic_key()), (
        "the pattern no longer matches a real-shaped Anthropic key — narrowing "
        "went too far and the scanner is now decorative"
    )


def test_a_realistic_key_is_detected_inside_surrounding_text():
    line = f'ANTHROPIC_API_KEY = "{_realistic_anthropic_key()}"  # do not commit'
    assert _pattern("anthropic key").search(line)


# --- the opposed half: this repo's own fixtures must NOT be caught ---------

@pytest.mark.parametrize("fixture", [
    "sk-ant-oat01-AbCdEfGh-",
    "sk-ant-oat01-SCRUBBED",
    "sk-ant-ort01-RefreshToken",
    "sk-ant-sid02-stub",
    "sk-ant-sid02-VERY-SECRET-SESSION-ID",
    "sk-ant-VERY-SECRET-WAKE-TOKEN-VALUE",
])
def test_short_test_fixtures_are_not_flagged(fixture):
    assert not _pattern("anthropic key").search(fixture), (
        f"{fixture!r} is a test fixture, not a key; flagging it is what made "
        "publish_readiness.sh unable to pass on a clean tree"
    )


def test_the_boundary_is_where_it_is_claimed_to_be():
    """Pin the threshold so a later edit cannot quietly move it."""
    rx = _pattern("anthropic key")
    assert not rx.search("sk-ant-" + "A" * 79)
    assert rx.search("sk-ant-" + "A" * 80)


# --- the rules the scanner must not silently lose --------------------------

def test_every_expected_provider_still_has_a_rule():
    have = {label for label, _ in scanner.PATTERNS}
    for expected in ("anthropic key", "openai key", "aws access key",
                     "github token", "private key block"):
        assert expected in have, f"the scanner lost its {expected!r} rule"


def test_matches_are_masked_and_never_printed_whole():
    key = _realistic_anthropic_key()
    masked = scanner.mask(key)
    assert key not in masked, "the scanner's own report must not become the leak"
    assert str(len(key)) in masked
