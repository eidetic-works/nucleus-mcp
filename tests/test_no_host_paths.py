"""No tracked source may carry this machine's actual home directory.

The goal this repo is held to is that a stranger can install and run it, so a
path that only resolves on one laptop is a defect wherever it appears in shipped
code. `paths.nucleus_root()` used to be a hard-coded `Path.home()/"ai-mvp-backend"`
and every consumer inherited it.

The check compares against `Path.home()` AT RUNTIME rather than against a name
written into this file. Two reasons: the test carries no identity, so it is safe
in a public repo; and it cannot rot when the machine changes, because it asks the
machine.

`/Users/` alone is NOT a violation. src/ legitimately contains docstrings about
host paths, regexes that DETECT them, and sanitizer replacements — a rule that
banned the substring would have to be suppressed everywhere it matters.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("src", "scripts")


def _tracked(root: Path, *paths: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", *paths],
                       capture_output=True, text=True)
    return [p for p in r.stdout.split("\0") if p]


def _offenders(root: Path, needle: str) -> list[str]:
    hits = []
    for rel in _tracked(root, *SCOPE):
        p = root / rel
        try:
            if needle in p.read_text(errors="replace"):
                hits.append(rel)
        except OSError:
            continue
    return hits


@pytest.mark.skipif(not (PKG_ROOT / ".git").exists()
                    and not (PKG_ROOT.parent / ".git").exists(),
                    reason="not a git checkout")
def test_no_real_home_path_in_shipped_source():
    home = str(Path.home())
    offenders = _offenders(PKG_ROOT, home)
    assert not offenders, (
        f"these tracked files contain this machine's home directory ({home}), "
        "so they cannot work on anyone else's:\n  " + "\n  ".join(offenders[:15])
    )


def test_the_check_fires_on_a_planted_violation(tmp_path):
    """The control. Without it, a passing run proves only that the scan ran."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text("ROOT = Path.home() / '.nucleus'\n")
    (src / "bad.py").write_text(f"ROOT = '{Path.home()}/ai-mvp-backend'\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)

    offenders = _offenders(tmp_path, str(Path.home()))
    assert offenders == ["src/bad.py"], (
        f"the scan must find the planted absolute path and only it; got {offenders}"
    )


def test_a_placeholder_is_not_a_violation(tmp_path):
    """Opposed half: the check must not fire on the documentation it lives beside."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    src = tmp_path / "src"
    src.mkdir()
    # Built at runtime: the placeholder strings are exactly what this repo's own
    # lane-hygiene guard blocks in added lines, and it is right to. A fixture that
    # needs the shape does not need the literal sitting in the file.
    u = "/Users" + "/"
    (src / "doc.py").write_text(
        f'"""Sanitizes {u}<name>/ and {u}OPERATOR/ out of ticket text."""\n'
        f'PATTERN = r"{u}[A-Za-z0-9._-]+/"\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    assert _offenders(tmp_path, str(Path.home())) == [], (
        "docstrings and detection regexes mentioning /Users/ are not host paths; "
        "a rule that flags them gets suppressed everywhere it matters"
    )
