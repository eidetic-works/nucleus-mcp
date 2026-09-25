"""
Opposed-pair tests for ``_classify_completed`` ``intent_only`` detection.

Each pair keeps the same intent phrase and only adds or removes a concrete
execution marker, proving the classifier distinguishes intention-to-act from
actual output.
"""

import pytest

from mcp_server_nucleus.runtime import vendor_dispatch as vd


# ── Opposed pair: code fence defeats intent_only ─────────────────────

@pytest.mark.parametrize(
    "output,expected",
    [
        (
            "I will update the configuration to enable the new feature.",
            "intent_only",
        ),
        (
            "I will update the configuration.\n"
            "```json\n"
            '{"feature_enabled": true}\n'
            "```",
            "ok",
        ),
    ],
    ids=["intent_without_code_fence", "intent_with_code_fence"],
)
def test_code_fence_opposed_pair(output, expected):
    assert vd._classify_completed(0, output) == expected


# ── Opposed pair: diff markers defeat intent_only ────────────────────

@pytest.mark.parametrize(
    "output,expected",
    [
        (
            "I am going to edit the file to correct the typo.",
            "intent_only",
        ),
        (
            "I am going to edit the file.\n"
            "--- a/config.txt\n"
            "+++ b/config.txt\n"
            "@@ -1,3 +1,3 @@\n"
            " old\n"
            " new",
            "ok",
        ),
    ],
    ids=["intent_without_diff", "intent_with_diff"],
)
def test_diff_markers_opposed_pair(output, expected):
    assert vd._classify_completed(0, output) == expected


# ── Opposed pair: file-change label defeats intent_only ──────────────

@pytest.mark.parametrize(
    "output,expected",
    [
        (
            "I'll create the missing module for the new handler.",
            "intent_only",
        ),
        (
            "I'll create the missing module.\n"
            "created: src/mcp_server_nucleus/handler.py",
            "ok",
        ),
    ],
    ids=["intent_without_created_label", "intent_with_created_label"],
)
def test_created_label_opposed_pair(output, expected):
    assert vd._classify_completed(0, output) == expected


# ── Opposed pair: completion word defeats intent_only ────────────────

@pytest.mark.parametrize(
    "output,expected",
    [
        (
            "I intend to finish the refactor of the dispatch loop.",
            "intent_only",
        ),
        (
            "I intend to finish the refactor of the dispatch loop. done.",
            "ok",
        ),
    ],
    ids=["intent_without_done", "intent_with_done"],
)
def test_done_word_opposed_pair(output, expected):
    assert vd._classify_completed(0, output) == expected
