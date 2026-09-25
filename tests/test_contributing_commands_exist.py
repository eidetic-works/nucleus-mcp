"""Every command CONTRIBUTING tells a newcomer to run must exist.

Four repos in this family shipped a README whose documented command could not
work: a test command that could not import the package, an install step omitted,
a pre-commit `rev` tag that was never published, an import path with no module
behind it. Each was written from a run whose caveat never made it into the prose.

Documentation drift is a test failure here, not a reader's problem.
"""

from __future__ import annotations

import re
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]


def _exists(rel: str) -> bool:
    """Documented commands are run from the repo root; some scripts live there."""
    return (PKG_ROOT / rel).exists() or (REPO_ROOT / rel).exists()
DOCS = ["CONTRIBUTING.md", "README.md"]

SCRIPT_RE = re.compile(r"(?:bash|sh)\s+(scripts/[A-Za-z0-9_./-]+\.sh)")
PYTEST_RE = re.compile(r"python3?\s+-m\s+pytest\s+(tests/[A-Za-z0-9_./-]+\.py)")


def _docs():
    return [(name, (PKG_ROOT / name)) for name in DOCS if (PKG_ROOT / name).exists()]


def test_every_documented_script_exists():
    missing = []
    checked = 0
    for name, path in _docs():
        for rel in SCRIPT_RE.findall(path.read_text(errors="replace")):
            checked += 1
            if not _exists(rel):
                missing.append(f"{name} -> {rel}")
    assert checked, "no documented script commands found — this test would pass vacuously"
    assert not missing, "documentation names scripts that do not exist:\n  " + "\n  ".join(missing)


def test_every_documented_test_path_exists():
    missing = []
    checked = 0
    for name, path in _docs():
        for rel in PYTEST_RE.findall(path.read_text(errors="replace")):
            checked += 1
            if not _exists(rel):
                missing.append(f"{name} -> {rel}")
    assert not missing, "documentation names test files that do not exist:\n  " + "\n  ".join(missing)


def test_contributing_points_at_the_entry_points():
    """The gap this file closed: CONTRIBUTING mentioned neither of them."""
    text = (PKG_ROOT / "CONTRIBUTING.md").read_text(errors="replace")
    for needed in ("scripts/verify.sh", "scripts/install_hooks.sh"):
        assert needed in text, f"CONTRIBUTING.md never tells a contributor about {needed}"


def test_the_scanner_would_notice_a_missing_script(tmp_path):
    """Planted: a doc naming a script that is not there must be reported."""
    doc = tmp_path / "CONTRIBUTING.md"
    doc.write_text("Run it:\n\n```bash\nbash scripts/does_not_exist.sh\n```\n")
    found = SCRIPT_RE.findall(doc.read_text())
    assert found == ["scripts/does_not_exist.sh"]
    assert not _exists(found[0]), "fixture assumes this script is absent"
