"""The GentleQuest content-exclusion preset, in opposed pairs.

Why this exists: on 2026-08-19 the sweep queue was generated with a hand-written
signature -- 'gentlequest|crisis detection|PHQ-9|GAD-7' -- and FIVE GentleQuest
docs went into the nucleus lane anyway. Not one of the five contains the string
"GentleQuest". They are written in the product's DOMAIN vocabulary: mental
health, crisis line, hotline, self-harm, counsellor. A name-based filter over a
corpus that does not use the name is a correct check pointed at the wrong
object: it ran every time and could never fire.

Every test names its failure direction. Over-exclusion is tested as carefully as
under-exclusion -- a signature that quietly eats nucleus docs shrinks the sweep
set while still reporting a clean run, which is the same failure wearing the
opposite sign.
"""

import importlib.util
import re
from pathlib import Path

_SPEC_GEN = Path(__file__).resolve().parents[2] / "scripts" / "spec_gen.py"


def _load():
    spec = importlib.util.spec_from_file_location("spec_gen", _SPEC_GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gq():
    return re.compile(_load().EXCLUDE_PRESETS["gq"]["pattern"], re.IGNORECASE)


def _is_gq(text: str) -> bool:
    """The shipped decision: ABOUT GentleQuest, not merely mentioning it."""
    pre = _load().EXCLUDE_PRESETS["gq"]
    rx = re.compile(pre["pattern"], re.IGNORECASE)
    head = next((l for l in text.splitlines() if l.startswith("# ")), "")
    return bool(head and rx.search(head)) or len(rx.findall(text)) >= pre["min_hits"]


# Verbatim lines from the five docs that actually leaked into the queue.
LEAKED_REAL_TEXT = {
    "CRISIS_KEYWORD_COMPREHENSIVE_LIST.md": "# Comprehensive Crisis Keyword List\n- suicidal ideation\n",
    "MARKET_ENTRY_CHECKLISTS.md": "- [ ] Crisis: 1393 (Mental Health), 109 (Suicide Prevention)\n",
    "API_ALERTS.md": "counselor alerts for self-harm signals\n",
    "API_RESOURCES.md": "a library of mental health resources (articles, crisis lines)\n",
    "data_inventory.md": "# Data Inventory Snapshot - AI Mental Health Assistant\n",
}


def test_preset_catches_every_doc_that_actually_leaked():
    """POSITIVE: all five real leaks must now be excluded."""
    rx = _gq()
    missed = [n for n, t in LEAKED_REAL_TEXT.items() if not rx.search(t)]
    assert not missed, f"preset still leaks GentleQuest docs: {missed}"


def test_the_old_signature_really_did_miss_them():
    """CONTROL: proves the fix changed something. If the old name-based
    signature had caught these, the new preset would be pointless ceremony --
    and this test would say so."""
    old = re.compile(r"gentlequest|crisis detection|PHQ-9|GAD-7", re.IGNORECASE)
    caught = [n for n, t in LEAKED_REAL_TEXT.items() if old.search(t)]
    assert not caught, (
        f"the old signature already caught {caught} -- the premise of this fix "
        f"is wrong and the preset needs rejustifying"
    )


def test_preset_does_not_eat_ordinary_nucleus_docs():
    """OPPOSED: over-exclusion silently shrinks the sweep set while still
    reporting a clean run. These are real nucleus subjects and must survive."""
    rx = _gq()
    nucleus_text = [
        "# Lane Architecture\nThe ExecutorDaemon claims a task atomically.",
        "# Vendor Dispatch\nNUCLEUS_VENDOR_MAX_CONCURRENT caps concurrency at 3.",
        "# Flywheel\nrecord_survived() bumps the claim survival rate.",
        "# Proof Gate\nThe third state is PROVEN / REFUTED / INSUFFICIENT.",
        "# Install\npip install nucleus-mcp registers the MCP server.",
    ]
    eaten = [t.splitlines()[0] for t in nucleus_text if rx.search(t)]
    assert not eaten, f"preset over-excludes nucleus docs: {eaten}"


def test_preset_is_case_insensitive_in_use():
    """OPPOSED: the docs capitalize inconsistently ('Mental Health', 'Counselor
    Alerts'). A case-sensitive application would leak most of them."""
    rx = _gq()
    assert rx.search("Quests, Resources, Counselor Alerts implementation")
    assert rx.search("AI MENTAL HEALTH ASSISTANT")


def test_manual_signature_and_preset_are_combined_not_replaced():
    """OPPOSED: passing both --exclude-preset and --exclude-matching must OR
    them. Silently honouring only one would drop half the caller's intent while
    still reporting an exclusion count."""
    src = _SPEC_GEN.read_text()
    assert "content_signature" in src, "combined-signature variable is gone"
    combined = re.compile("|".join(
        f"(?:{x})" for x in (_load().EXCLUDE_PRESETS["gq"], r"my-own-term")
    ), re.IGNORECASE)
    assert combined.search("this mentions my-own-term only")
    assert combined.search("this mentions a crisis line only")


# --- aboutness, not presence ------------------------------------------------
# Widening the signature to catch the five leaked docs over-corrected: a single
# passing mention excluded core nucleus docs, shrinking a "complete pass" to a
# third of the corpus while still reporting a clean run. Under-exclusion leaks
# GentleQuest docs into the wrong lane; over-exclusion silently narrows the set.
# Both directions are tested because only one of them is visible in a report.

def test_one_passing_mention_does_not_make_a_doc_gentlequest():
    """THE OVER-CORRECTION: these are core nucleus docs that happen to name
    GentleQuest or crisis detection once."""
    wrongly_excluded = {
        "ADRS.md": "# Architecture Decisions\n\nADR-12 covers crisis detection for a downstream app.\n",
        "TESTING.md": "# Testing\n\nRun pytest. One suite covers crisis detection.\n",
        "NUCLEUS_GROWTH_STRATEGY.md": "# Nucleus Growth\n\nGentleQuest was the first dogfood target.\n",
    }
    leaked = [n for n, t in wrongly_excluded.items() if _is_gq(t)]
    assert not leaked, f"nucleus docs excluded on a single mention: {leaked}"


def test_a_doc_whose_TITLE_names_the_product_is_still_excluded():
    """OPPOSED: aboutness shows up in the title with a single hit.
    'Contributing to GentleQuest backend' and 'Data Inventory Snapshot - AI
    Mental Health Assistant' are GentleQuest docs and score 1 in the body."""
    assert _is_gq("# Contributing to GentleQuest backend\n\n## Setup\n")
    assert _is_gq("# Data Inventory Snapshot - AI Mental Health Assistant\n\nrows: 4\n")


def test_dense_domain_language_is_still_excluded_without_a_title_hit():
    """OPPOSED: the leaked docs never say 'GentleQuest' anywhere, including the
    title. Density is what catches them."""
    body = ("# Comprehensive Keyword List\n\n- suicide\n- self-harm\n"
            "- hotline\n- crisis line\n")
    assert _is_gq(body)


def test_a_pure_nucleus_doc_is_untouched():
    """The control that makes the others meaningful."""
    assert not _is_gq("# Lane Architecture\n\nThe ExecutorDaemon claims a task atomically.\n")


def test_the_products_own_feature_nouns_are_gentlequest():
    """This signature has now missed a whole CATEGORY three times: clinical
    vocabulary, then safety vocabulary, then game mechanics. Quests, XP and a
    Flutter app are GentleQuest's product surface; nucleus ships none of them."""
    for title in ("# Quest System API Documentation",
                  "# XP & Undo Test Checklist (Quest Screen)",
                  "# Deep Link & Notification Routing (Flutter)"):
        assert _is_gq(title + "\n\nbody\n"), f"GentleQuest app doc leaked: {title}"


def test_quest_is_word_bounded_so_request_does_not_match():
    """OPPOSED: an unanchored 'quest' matches 'request', which appears in
    essentially every nucleus API doc -- that would exclude the entire corpus
    while still reporting a clean run."""
    nucleus = ("# Relay API\n\nEach request is claimed atomically. The request "
               "queue requests a lock, and a request that requests twice is "
               "rejected.\n")
    assert not _is_gq(nucleus), "'request' matched the 'quest' term"
