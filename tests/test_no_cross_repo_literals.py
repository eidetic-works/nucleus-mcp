"""Shipped code must not name a sibling repo by path.

The split moved code into tb, ranit, nucleus-scan, nucleus-nar and gentlequest.
Six nucleus jobs kept shelling out to scripts that had left, and each failure was
a stack trace about a missing file rather than a sentence about a missing repo.
`runtime/sibling_repos.py` is the answer: it resolves a sibling from
NUCLEUS_SIBLING_REPOS or $XDG_CONFIG_HOME/nucleus/siblings, and `require_script`
raises a message naming what is missing and how to configure it.

This test keeps that the only route. A literal `~/tb/...` or `/Users/.../ranit`
in shipped code works on exactly one machine and fails silently everywhere else,
which is what the goal "every cross-repo link either configurable or failing with
a clear message" forbids.

sibling_repos.py itself is exempt: naming the repos is its job.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("src", "scripts")
SIBLINGS = ("tb", "ranit", "nucleus-scan", "nucleus-nar", "gentlequest",
            "ai-mvp-backend", "workspace")
# The resolver's whole purpose is to know these names.
EXEMPT = {"src/mcp_server_nucleus/runtime/sibling_repos.py"}

# A path LITERAL, not a mention: a tilde, a parent walk, or an absolute home
# path, followed by a sibling repo name and a slash.
def _pattern() -> re.Pattern[str]:
    names = "|".join(re.escape(s) for s in SIBLINGS)
    return re.compile(rf"(?:~|\.\.|/Users/[^/\s\"']+)/(?:{names})/")


def _tracked(root: Path) -> list[str]:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", *SCOPE],
                       capture_output=True, text=True)
    return [p for p in r.stdout.split("\0") if p]


def _offenders(root: Path) -> list[str]:
    rx, hits = _pattern(), []
    for rel in _tracked(root):
        if rel in EXEMPT:
            continue
        try:
            if rx.search((root / rel).read_text(errors="replace")):
                hits.append(rel)
        except OSError:
            continue
    return hits


@pytest.mark.skipif(not (PKG_ROOT / ".git").exists()
                    and not (PKG_ROOT.parent / ".git").exists(),
                    reason="not a git checkout")
def test_no_sibling_repo_path_literals_in_shipped_code():
    offenders = _offenders(PKG_ROOT)
    assert not offenders, (
        "these tracked files hard-code a path into a sibling repo instead of "
        "resolving it through runtime.sibling_repos, so they work on one machine "
        "only:\n  " + "\n  ".join(offenders[:15])
    )


def test_the_check_fires_on_a_planted_literal(tmp_path):
    """The control: a planted cross-repo path must be found."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "bad.py").write_text('RUN = "~/tb/scripts/driver.py"\n')
    (tmp_path / "src" / "ok.py").write_text(
        "from .sibling_repos import require_script\n"
        'RUN = require_script("tb", "scripts/driver.py")\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    assert _offenders(tmp_path) == ["src/bad.py"]


def test_naming_a_sibling_in_prose_is_not_a_violation(tmp_path):
    """Opposed half: the rule is about PATH LITERALS, not the words.

    A docstring saying "the tb repo owns this" must not fire, or the check gets
    suppressed in every file that explains itself.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "doc.py").write_text(
        '"""Moved to the tb repo in the 2026-09-17 split; resolve it with\n'
        'sibling_repos.require_script("tb", ...)."""\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    assert _offenders(tmp_path) == []
