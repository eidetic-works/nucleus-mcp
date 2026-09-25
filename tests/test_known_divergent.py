"""The expected-divergence allowlist must suppress only what it lists.

23 of the 66 paths shared with a sibling differ, and most differ correctly: each
repo needs its own CI, its own ignore rules, its own README. Printing all 23
every run is how a real signal gets muted wholesale — so they are listed in
`.known-divergent.txt` and suppressed.

An allowlist is the shape that most reliably reads clean while missing the thing
it exists to catch (a narrow allowlist made a working scanner report nothing,
twice in this project). So the control here is the broken input: a path that is
NOT listed must still be reported. Without that, `.known-divergent.txt` could be
emptied, or the reader could be pointed at a missing file, and every run would
still look calm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
DIVERGENT = PKG_ROOT / ".known-divergent.txt"
TWINS = PKG_ROOT / ".known-twins.txt"

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "twin_drift", PKG_ROOT.parent / "scripts" / "twin_drift.py")
twin_drift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(twin_drift)


def _entries(p: Path) -> set[str]:
    return {ln.strip() for ln in p.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")}


def test_listed_path_is_suppressed(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text("# reason\na/b.yml\n")
    assert twin_drift._listed(f) == {"a/b.yml"}


def test_unlisted_path_is_not_suppressed(tmp_path):
    """The control: the allowlist must not swallow what it does not name."""
    f = tmp_path / "list.txt"
    f.write_text("a/b.yml\n")
    assert "c/d.py" not in twin_drift._listed(f), (
        "an allowlist that suppresses an unlisted path suppresses everything"
    )


def test_missing_file_suppresses_nothing(tmp_path):
    """A missing allowlist must report every divergence, not none of them.

    Returning the whole world on a missing file is the silent-degradation shape:
    the report goes quiet and looks like good news.
    """
    assert twin_drift._listed(tmp_path / "absent.txt") == set()


def test_comments_and_blanks_are_not_entries(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text("# a comment\n\n   \nreal/path.py\n")
    assert twin_drift._listed(f) == {"real/path.py"}


def test_the_report_suppresses_only_listed_paths():
    """The consumer, not just the parser.

    A correct reader feeding a classifier that drops everything is the defect
    this pair exists for; the reader tests above cannot see it.
    """
    diverged = [("ci.yml", "sib"), ("nucleus/state.py", "sib")]
    got = twin_drift.unexpected_divergences(diverged, {"ci.yml"})
    assert got == [("nucleus/state.py", "sib")], (
        "the listed path must be suppressed and the unlisted one reported; "
        f"got {got}"
    )


def test_an_empty_allowlist_reports_everything():
    diverged = [("a.py", "sib"), ("b.py", "sib")]
    assert twin_drift.unexpected_divergences(diverged, set()) == diverged, (
        "with nothing allowlisted, nothing may be suppressed"
    )


@pytest.mark.skipif(not DIVERGENT.exists(), reason="no allowlist in this checkout")
def test_every_entry_carries_a_reason():
    """Each entry must have a comment above its block, so the list stays auditable."""
    lines = DIVERGENT.read_text().splitlines()
    entries = [i for i, ln in enumerate(lines) if ln.strip() and not ln.startswith("#")]
    assert entries, "the allowlist is empty; it should not exist rather than be empty"
    for i in entries:
        # Walk back to the nearest non-entry line; it must be a comment.
        j = i - 1
        while j >= 0 and lines[j].strip() and not lines[j].startswith("#"):
            j -= 1
        assert j >= 0 and lines[j].startswith("#"), (
            f"{lines[i]!r} has no reason above it — an unexplained allowlist entry "
            "is indistinguishable from one added to silence a real finding"
        )


@pytest.mark.skipif(not (DIVERGENT.exists() and TWINS.exists()),
                    reason="both lists needed")
def test_a_path_is_never_both_a_twin_and_expected_to_differ():
    """The two lists make opposite claims; an overlap means one is wrong."""
    overlap = _entries(DIVERGENT) & _entries(TWINS)
    assert not overlap, (
        "these paths are recorded as byte-identical AND as expected to differ: "
        + ", ".join(sorted(overlap))
    )
