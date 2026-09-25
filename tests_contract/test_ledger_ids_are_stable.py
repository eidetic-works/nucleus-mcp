"""Ledger finding IDs must be unique, and every citation must resolve.

`docs/AUDIT_LEDGER.md` is described in CLAUDE.md as the live record of audited
defects with **stable IDs**, and the codebase cites those IDs in comments as the
provenance for a guard or a fallback. That only works if one ID means one thing.

It did not. `CP-5` was assigned twice — once to the `grounding` facade never
registering, once to `_envelope.py` contradicting itself about its own default —
and the two are unrelated findings of different severity. Six citations across
four files pointed at that ID, so roughly half of them resolved to the wrong
finding. Nothing noticed, because nothing was checking. The envelope one was
renumbered to the free `CP-6`.

Two checks here, both cheap and both about the same failure mode: an ID that
does not identify.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "AUDIT_LEDGER.md"

pytestmark = pytest.mark.skipif(not LEDGER.exists(), reason="ledger not in this export")

# A summary-table row: `| CP-5 | major | hours | fixed | ... |`
ROW = re.compile(r"^\|\s*([A-Z]{2}-\d+)\s*\|\s*(\w+)\s*\|", re.M)

# Where findings get cited as provenance. Not the whole tree: a bare two-letter
# code is too common in prose to chase everywhere.
CITING = ("src", "tests_contract", "tests_security", "tests_onboarding", ".github")

# Guard the boundary so ADR-0043 does not read as "DR-0043".
CITATION = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2}-\d+)(?![\d-])")


@pytest.fixture(scope="module")
def ledger_ids():
    rows = ROW.findall(LEDGER.read_text(encoding="utf-8"))
    assert rows, "no finding rows parsed out of the ledger; has the table shape changed?"
    return [ident for ident, _status in rows]


def test_every_finding_id_is_used_once(ledger_ids):
    dupes = {i: n for i, n in Counter(ledger_ids).items() if n > 1}
    assert not dupes, (
        f"these ledger IDs are assigned to more than one finding: {dupes}. "
        "IDs are cited from source comments as provenance, so a reused ID sends "
        "half those readers to the wrong finding. Give the newer one a free number."
    )


def test_the_ledger_has_findings_to_check(ledger_ids):
    """Guards the two tests above against silently parsing nothing."""
    assert len(ledger_ids) >= 50, f"only {len(ledger_ids)} findings parsed; the regex is stale"


def test_every_cited_finding_exists_in_the_ledger(ledger_ids):
    """A comment citing a finding that was renamed or dropped is worse than none."""
    known = set(ledger_ids)
    # Prefixes the ledger actually uses. Anything else in the tree (ADR, RFC,
    # an enum member) is not a finding citation and is not our business.
    prefixes = {i.split("-")[0] for i in known}

    dangling: dict[str, list[str]] = {}
    for area in CITING:
        base = ROOT / area
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.suffix not in (".py", ".md", ".yml", ".yaml") or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for ident in set(CITATION.findall(text)):
                if ident.split("-")[0] in prefixes and ident not in known:
                    dangling.setdefault(ident, []).append(str(path.relative_to(ROOT)))

    assert not dangling, (
        f"these files cite ledger findings that do not exist: {dangling}. "
        "Either the finding was renumbered without updating its citations, or "
        "the ID is a typo. Both leave a comment pointing at nothing."
    )
