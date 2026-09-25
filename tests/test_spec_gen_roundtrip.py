"""spec_gen.py output must round-trip through the REAL SpecParser.

THE BUG THIS LOCKS OUT (caught 2026-08-19 during authoring): the generator
emitted "- **Blocked by:**" and "- **Priority:**" AFTER the acceptance bullet
list. spec_parser._extract_list matches a run of consecutive "- " lines and its
leading \\s* absorbs blank lines, so both field lines were swallowed as extra
acceptance criteria — a 7-criterion template parsed as 9.

It looked perfectly fine as markdown. It only surfaced by parsing the output
with the real parser and COUNTING. Had it shipped, every vendor working every
task would have received two junk instructions ("**Blocked by:** (none)") as
acceptance criteria. A blank-line separator did NOT fix it; only moving the
scalar fields ahead of the list did.

Each test states its failure direction.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.lane.spec_parser import SpecParser, SpecParseError
from mcp_server_nucleus.runtime.lane.config import LaneConfig

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "scripts" / "spec_gen.py"

# audit-doc template criterion count. If the template legitimately changes,
# update this — but do it deliberately, because this number is what catches
# list pollution.
AUDIT_DOC_CRITERIA = 7


def _generate(tmpdir, glob="docs/*.md", template="audit-doc", extra=None):
    out = Path(tmpdir) / "GEN_SPEC.md"
    cmd = [sys.executable, str(GEN), "--glob", glob, "--template", template, "--out", str(out)]
    if extra:
        cmd += extra
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, f"generator failed: {r.stderr}"
    return out


def _parse(spec_path):
    cfg = LaneConfig(repo_root=REPO, brain_path=REPO / ".brain", spec_path=spec_path)
    return SpecParser(cfg).parse()


def test_generated_spec_parses_with_the_real_parser():
    """POSITIVE: the actual consumer accepts the output. Not 'looks like valid
    markdown' — the real SpecParser, which is the only opinion that counts."""
    with tempfile.TemporaryDirectory() as td:
        items = _parse(_generate(td))
        assert len(items) > 0, "generator produced a spec the parser found empty"


def test_acceptance_list_is_not_polluted_by_trailing_fields():
    """THE ACTUAL BUG: criteria count must equal the template's, exactly. If
    this reads high, scalar fields are being swallowed into the list again."""
    with tempfile.TemporaryDirectory() as td:
        for item in _parse(_generate(td)):
            assert len(item.acceptance) == AUDIT_DOC_CRITERIA, (
                f"{item.task_id}: {len(item.acceptance)} criteria, expected "
                f"{AUDIT_DOC_CRITERIA} — field lines are leaking into the list"
            )
            for c in item.acceptance:
                assert "**Blocked by:**" not in c
                assert "**Priority:**" not in c


def test_scalar_fields_still_parse_correctly():
    """OPPOSED: fixing the pollution must not break the fields themselves.
    They must still be found, not merely absent from the acceptance list."""
    with tempfile.TemporaryDirectory() as td:
        for item in _parse(_generate(td)):
            assert item.blocked_by == (), f"{item.task_id}: blocked_by={item.blocked_by}"
            assert item.priority == 2, f"{item.task_id}: priority={item.priority}"
            assert item.title and item.title != item.task_id, "title did not parse"


def test_task_ids_are_unique():
    """OPPOSED: colliding ids would silently drop work from the queue — a pass
    would report complete having never run the shadowed tasks."""
    with tempfile.TemporaryDirectory() as td:
        ids = [i.task_id for i in _parse(_generate(td))]
        assert len(ids) == len(set(ids)), "duplicate task ids"


def test_content_exclusion_actually_excludes():
    """OPPOSED: the filter must genuinely reduce the set. A filter that never
    excludes anything is the charter's GentleQuest boundary silently not
    holding."""
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        unfiltered = len(_parse(_generate(td1)))
        filtered = len(_parse(_generate(
            td2, extra=["--exclude-matching", "gentlequest|PHQ-9|GAD-7|quest"])))
        assert filtered < unfiltered, (
            f"content filter excluded nothing ({filtered} vs {unfiltered})"
        )
        assert filtered > 0, "content filter excluded everything"


def test_every_task_has_at_least_one_criterion():
    """The parser REJECTS a task with no acceptance criteria. A generator that
    can emit one produces a spec that dies at parse time."""
    with tempfile.TemporaryDirectory() as td:
        for item in _parse(_generate(td)):
            assert item.acceptance, f"{item.task_id} has no acceptance criteria"


def test_all_templates_produce_parseable_specs():
    """Every template ships working, not just the one that was exercised."""
    for tpl in ("audit-doc", "audit-code", "test-coverage"):
        with tempfile.TemporaryDirectory() as td:
            glob = "docs/*.md" if tpl == "audit-doc" else "scripts/*.py"
            items = _parse(_generate(td, glob=glob, template=tpl,
                                     extra=["--limit", "3"]))
            assert items, f"template {tpl} produced no parseable items"
            for i in items:
                for c in i.acceptance:
                    assert "**Priority:**" not in c, f"{tpl} polluted"
