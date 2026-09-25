"""NUCLEUS_REF.md's degradation tiers must match the shipped extension (CS-6).

The document described three tiers — Native Injection, Clipboard + Focus,
Virtual Document, numbered 1/2/3. The `extension.ts` embedded in every tracked
`.vsix` defines:

    enum ExecutionTier {
        NativeChat  = 'Tier 3A (Native)',
        CopilotChat = 'Tier 3A (Copilot)',
        VirtualDoc  = 'Tier 4 (Virtual Doc)',
    }

Different names, different numbers, and one structural difference that matters:
there is no standalone clipboard tier. Clipboard-and-focus happens inside the
Native and Copilot branches as their in-branch fallback, so documenting it as a
separate rung implied a host could land there without first attempting native
injection. No released build does that.

These read the taxonomy out of the `.vsix` itself rather than trusting either
side, because the extension source is export-ignored from this mirror — the
compiled archive is the only copy of the truth here.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "NUCLEUS_REF.md"
BRIDGE = ROOT / "extensions" / "nucleus-bridge"

pytestmark = pytest.mark.skipif(not REF.exists(), reason="NUCLEUS_REF not in this export")


def _extension_source() -> str:
    """The extension.ts embedded in any tracked .vsix, or skip."""
    if not BRIDGE.is_dir():
        pytest.skip("nucleus-bridge not in this export")
    for vsix in sorted(BRIDGE.glob("*.vsix")):
        try:
            with zipfile.ZipFile(vsix) as z:
                for name in z.namelist():
                    if name.endswith("extension.ts"):
                        return z.read(name).decode("utf-8", "replace")
        except zipfile.BadZipFile:
            continue
    pytest.skip("no readable extension.ts inside any tracked .vsix")


@pytest.fixture(scope="module")
def tiers():
    """The tier labels the shipped code actually defines."""
    source = _extension_source()
    block = re.search(r"enum ExecutionTier\s*\{(.*?)\}", source, re.S)
    assert block, "ExecutionTier enum not found in the shipped extension"
    labels = re.findall(r"=\s*'([^']+)'", block.group(1))
    assert labels, "ExecutionTier defines no string labels"
    return labels


@pytest.fixture(scope="module")
def degradation_section():
    text = REF.read_text(encoding="utf-8")
    marker = "Graceful UI Degradation"
    assert marker in text, "NUCLEUS_REF has no degradation section"
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def test_every_shipped_tier_label_appears_in_the_doc(tiers, degradation_section):
    missing = [t for t in tiers if t not in degradation_section]
    assert not missing, (
        f"the shipped extension defines tiers {missing} that the documentation "
        "never names; a reader cannot map what they see in the status bar onto "
        "what this document describes"
    )


def test_the_doc_does_not_use_the_scheme_no_build_implements(degradation_section):
    for stale in ("Tier 1 (Native Injection)", "Tier 2 (Clipboard", "Tier 3 (Virtual Document)"):
        assert stale not in degradation_section, (
            f"the doc still describes {stale!r}; no released .vsix implements "
            "that numbering"
        )


def test_the_doc_says_clipboard_is_not_a_tier_of_its_own(degradation_section):
    """The structural difference, not just the naming one."""
    assert "not a tier of its own" in degradation_section.lower(), (
        "the doc does not say that clipboard-and-focus is an in-branch fallback "
        "rather than a rung, which is what made the old version misleading about "
        "when a host reaches it"
    )


def test_the_clipboard_fallback_really_is_inside_the_native_branches():
    """Pin the claim the doc now makes, against the shipped code."""
    source = _extension_source()
    block = re.search(r"enum ExecutionTier\s*\{(.*?)\}", source, re.S)
    assert "clipboard" not in block.group(1).lower(), (
        "the enum now has a clipboard tier; the documentation says there is "
        "none, so update both together"
    )
    assert "clipboard.writeText" in source, (
        "the extension no longer writes to the clipboard at all — re-check what "
        "the documented fallback chain should say"
    )
