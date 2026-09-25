"""Guards that keep the 2026-09-17 split from quietly unravelling.

Three things went wrong during the split that no test would have caught:

1. Shipped code hard-coded absolute home paths, so a clone carried paths that
   exist on exactly one machine.
2. Modules reached into a sibling repo by literal path. When that repo moved,
   six scheduled jobs failed at run time pointing at a directory that no longer
   existed — invisible to import analysis, because the calls are importlib and
   subprocess by path, not imports.
3. `git grep` was used to check both of the above. It reads the index, so a file
   that was written but not yet committed passed every check and shipped later.

Each test below is written so it can be aimed at a fixture, and each has a
planted-failure twin: a scanner that has never reported a violation is not known
to work.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
SRC = PKG_ROOT / "src"

HOME_PATH = re.compile(r"/(?:Users|home)/([A-Za-z][A-Za-z0-9_.-]*)")
# Placeholders that are documentation, not somebody's machine.
PLACEHOLDER = re.compile(
    r"^(ubuntu|root|user|username|name|you|me|someone|runner|ec2-user|admin|"
    r"NAME|USER|OPERATOR|\.\.\.)$"
)

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".venv"}


def python_files(root: Path) -> list[Path]:
    """Every .py under root — from the FILESYSTEM, not the git index.

    Deliberately not `git ls-files`: an untracked file under src/ is exactly the
    case that slipped through during the split.
    """
    return [
        p for p in root.rglob("*.py")
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts)
    ]


def home_path_hits(root: Path) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for f in python_files(root):
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            m = HOME_PATH.search(line)
            if m and not PLACEHOLDER.match(m.group(1)):
                hits.append((f, n, line.strip()[:100]))
    return hits


def sibling_literal_hits(root: Path) -> list[tuple[Path, int, str]]:
    """Modules building a path into a companion repo instead of resolving one.

    `runtime/sibling_repos.py` is the sanctioned way: it searches configured
    locations and raises naming every one it tried.
    """
    # Only NON-dotfile children of $HOME: `Path.home() / "tb"` is a sibling repo,
    # while `Path.home() / ".tb"` or `.nucleus` is this tool's own config
    # directory, which is exactly where a CLI should write. A first draft flagged
    # all of them and would have been ignored within a day.
    pattern = re.compile(r"Path\.home\(\)\s*/\s*[\"'](?!\.)[A-Za-z0-9_-]+[\"']")
    allow = {"sibling_repos.py"}
    # Standard OS locations under $HOME are not sibling repos.
    os_dirs = {"Library", "Documents", "Downloads", "Desktop", "Applications", "Pictures"}
    hits: list[tuple[Path, int, str]] = []
    for f in python_files(root):
        if f.name in allow:
            continue
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            m = pattern.search(line)
            if m and m.group(0).split('"')[-2].strip("'") not in os_dirs:
                hits.append((f, n, line.strip()[:100]))
    return hits


# --------------------------------------------------------------------------
# the real assertions
# --------------------------------------------------------------------------

def test_no_absolute_home_paths_in_shipped_code():
    hits = home_path_hits(SRC)
    assert not hits, "absolute home paths in code that SHIPS:\n" + "\n".join(
        f"  {f.relative_to(PKG_ROOT)}:{n}  {line}" for f, n, line in hits
    )


def test_no_sibling_repo_literals_in_shipped_code():
    hits = sibling_literal_hits(SRC)
    assert not hits, (
        "a module builds a path into a sibling repo instead of using "
        "runtime.sibling_repos:\n"
        + "\n".join(f"  {f.relative_to(PKG_ROOT)}:{n}  {line}" for f, n, line in hits)
    )


def test_sibling_repos_resolver_is_the_sanctioned_route():
    """It must search, and must fail with the locations it tried — not guess."""
    from mcp_server_nucleus.runtime import sibling_repos

    assert sibling_repos.find_script("scripts/definitely_not_here.py") is None
    with pytest.raises(FileNotFoundError) as exc:
        sibling_repos.require_script("scripts/definitely_not_here.py")
    msg = str(exc.value)
    assert "definitely_not_here.py" in msg
    assert "NUCLEUS_SIBLING_REPOS" in msg, "the error must say how to configure it"


# --------------------------------------------------------------------------
# planted failures — a scanner that has never fired is not known to work
# --------------------------------------------------------------------------

def test_home_path_scanner_fires_on_a_planted_violation(tmp_path):
    (tmp_path / "clean.py").write_text("X = 1\n")
    planted = tmp_path / "planted.py"
    planted.write_text('HOME = "' + "/" + "Users" + '/plantedstranger/nucleus"\n')
    hits = home_path_hits(tmp_path)
    assert [f for f, _, _ in hits] == [planted], f"scanner missed the planted file: {hits}"


def test_home_path_scanner_ignores_documentation_placeholders(tmp_path):
    (tmp_path / "doc.py").write_text('HELP = "edit ' + "/" + 'home/ubuntu/.env"\n')
    assert home_path_hits(tmp_path) == [], "a placeholder must not be reported as a leak"


def test_scanner_sees_untracked_files(tmp_path):
    """The defect that shipped: `git grep` reads the index, so a new file passes."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = tmp_path / "tracked.py"
    tracked.write_text("X = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.py"], check=True)
    untracked = tmp_path / "untracked.py"
    untracked.write_text('H = "' + "/" + "Users" + '/plantedstranger/x"\n')

    found = {f.name for f, _, _ in home_path_hits(tmp_path)}
    assert "untracked.py" in found, "an untracked file must be scanned, not skipped"


def test_sibling_literal_scanner_fires_on_a_planted_violation(tmp_path):
    planted = tmp_path / "reaches_out.py"
    planted.write_text('from pathlib import Path\nP = Path.home() / "tb" / "scripts"\n')
    hits = sibling_literal_hits(tmp_path)
    assert [f for f, _, _ in hits] == [planted], f"scanner missed the planted file: {hits}"
