"""Opposed pairs for the pseudonymity blocklist externalisation.

Two distinct defects are guarded here, and BOTH have shipped:

  1. v<=1.16.5 hardcoded the operator's real name, two emails, employer and three
     absolute home paths as this module's blocklist -- in a module that ships to
     PyPI. The guard built to stop identity reaching public artifacts carried the
     complete set.  ->  test_no_identity_instances_in_source

  2. v1.16.6 externalised the DATA and never repointed the CONSUMER:
     _pseudonymity_scan still referenced the deleted constants, so it raised
     NameError on every call and `nucleus build` died in its verify stage.
     ->  test_scan_finds_planted_violation

The second is the one worth remembering: the loader was verified in isolation
and read correct. The check was aimed at the producer; the defect was in the
caller. A passing control says nothing about the set it was not run over.
"""
import re
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import build_runner

SOURCE = Path(build_runner.__file__).read_text(encoding="utf-8")

# The identity set is NEVER written here. It is derived from the canonical
# guard at test time, so this file contains no instance of anything it checks
# for -- the same rule the module under test now obeys. It also means the test
# tracks the guard automatically instead of drifting from it.
#
# One filter, stated narrowly so it cannot quietly widen: the guard's quoted
# strings include shell format artifacts (e.g. a printf specifier) that are not
# identity terms. An identity term never contains "%" or a backslash escape.

_REPO_ROOT = Path(build_runner.__file__).resolve().parents[4]
_CANONICAL_GUARD = _REPO_ROOT / ".githooks" / "pre-commit-pseudonymity-guard"


def _guard_terms() -> list[str]:
    assert _CANONICAL_GUARD.exists(), (
        f"canonical guard missing at {_CANONICAL_GUARD} -- this test cannot run "
        "without it, and passing without it would be indistinguishable from clean"
    )
    text = _CANONICAL_GUARD.read_text(encoding="utf-8", errors="replace")
    quoted = re.findall(r'"([^"\n]{4,60})"', text) + re.findall(r"'([^'\n]{4,60})'", text)
    return sorted({
        t for t in quoted
        if any(c.isalpha() for c in t) and "%" not in t and "\\" not in t
    })


def _guard_text(*terms: str) -> str:
    """A minimal file shaped like .githooks/pre-commit-pseudonymity-guard."""
    body = "\n".join(f'    "{t}"' for t in terms)
    return f"BLOCKED=(\n{body}\n)\n"


@pytest.fixture
def repo(tmp_path):
    """A real git repo -- _pseudonymity_scan shells out to `git diff`."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "f.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    return tmp_path


# ── Defect 1: the module must not carry instances ────────────────────────────

def test_no_identity_instances_in_source():
    """FAILS on <=1.16.5, which hardcoded the full identity set."""
    terms = _guard_terms()
    assert len(terms) > 10, f"guard parsed to only {len(terms)} terms -- parser broken"
    lowered = SOURCE.lower()
    found = sorted({t for t in terms if t.lower() in lowered})
    assert not found, (
        f"{len(found)} identity instance(s) present in a PyPI-shipped module "
        f"(first: {found[0]!r})"
    )


def test_loader_exists_and_constants_do_not():
    assert hasattr(build_runner, "_load_pseudonymity_terms")
    assert not hasattr(build_runner, "_PSEUDONYMITY_BLOCKED_TERMS")
    assert not hasattr(build_runner, "_PSEUDONYMITY_CI_BLOCKED_TERMS")


# ── Defect 2: the CONSUMER must actually use the loader ──────────────────────

def test_scan_finds_planted_violation(repo, monkeypatch):
    """FAILS on 1.16.6 with NameError -- the consumer was never repointed."""
    guard = repo / "guard"
    guard.write_text(_guard_text("Blocked" + "Person", "acme-corp"))
    monkeypatch.setenv("NUCLEUS_PSEUDONYMITY_TERMS_FILE", str(guard))

    (repo / "f.py").write_text("x = 1\nowner = 'Blocked" + "Person'\n")

    hits = build_runner._pseudonymity_scan(["f.py"], repo)
    assert hits, "a planted blocked term was not reported"
    assert hits[0]["file"] == "f.py"
    assert hits[0]["term"] != "<INSUFFICIENT>"


def test_scan_clean_file_reports_nothing(repo, monkeypatch):
    """Opposed half: the scan must be able to say 'nothing here'."""
    guard = repo / "guard"
    guard.write_text(_guard_text("Blocked" + "Person", "acme-corp"))
    monkeypatch.setenv("NUCLEUS_PSEUDONYMITY_TERMS_FILE", str(guard))

    (repo / "f.py").write_text("x = 1\ny = 2\n")

    assert build_runner._pseudonymity_scan(["f.py"], repo) == []


# ── The third state: unreadable blocklist is INSUFFICIENT, never clean ───────

def test_missing_blocklist_is_insufficient_not_clean(repo, monkeypatch):
    """An empty blocklist would make every scan pass. It must not read clean."""
    monkeypatch.delenv("NUCLEUS_PSEUDONYMITY_TERMS_FILE", raising=False)
    (repo / "f.py").write_text("x = 1\nowner = 'anything'\n")

    hits = build_runner._pseudonymity_scan(["f.py"], repo)  # no guard at repo root
    assert hits, "unreadable blocklist returned [] -- indistinguishable from clean"
    assert hits[0]["term"] == "<INSUFFICIENT>"


def test_loader_reports_error_when_unreachable(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_PSEUDONYMITY_TERMS_FILE", raising=False)
    terms, ci_terms, err = build_runner._load_pseudonymity_terms(tmp_path)
    assert terms == [] and ci_terms == []
    assert err, "loader returned empty lists with no error -- reads as clean"


def test_loader_reads_the_real_guard():
    """Positive control: the canonical guard must actually parse into terms."""
    root = Path(build_runner.__file__).resolve().parents[4]
    guard = root / ".githooks" / "pre-commit-pseudonymity-guard"
    if not guard.exists():
        pytest.skip(f"canonical guard not present at {guard}")
    terms, ci_terms, err = build_runner._load_pseudonymity_terms(root)
    assert err is None
    assert len(terms) > 10, f"guard parsed to only {len(terms)} terms"
