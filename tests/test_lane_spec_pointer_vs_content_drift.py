"""verify_spec() must distinguish POINTER drift from CONTENT drift.

THE INCIDENT (2026-08-03 -> 2026-08-19, 16 days): the autonomous lane system
was completely unrunnable. `nucleus lane status` died in self-heal with
"Spec tag lane-g1-v1 moved from pinned commit ... needs human review".

Diagnosis: verify_spec() ran three checks -- tag commit, spec blob SHA, spec
body SHA-256 -- and raised on the FIRST one. But the tag had merely been
re-pointed from a merge commit onto a same-day docs commit carrying the
IDENTICAL SPEC.md blob. Both content checks passed. The spec had provably not
been tampered with, and the lane was bricked anyway, with no re-pin path --
so any retag disabled it permanently.

The fix must NOT weaken tamper detection. Content drift stays a hard raise.
Only pointer-drift-with-identical-content is downgraded to a warning.

Each test states its failure direction. A guard that only ever passes is not
a guard -- and a guard that only ever fails is not one either.
"""

import hashlib
import subprocess
import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.lane.spec_parser import SpecParser, SpecParseError
from mcp_server_nucleus.runtime.lane.config import LaneConfig


SPEC_TEXT = "# SPEC\n\n## Tasks\n\n- [ ] Task 1: do a thing\n"


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture()
def pinned_repo():
    """A real git repo with a real tag and a really-pinned spec."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t.com")
        _git(repo, "config", "user.name", "t")
        spec = repo / "SPEC.md"
        spec.write_text(SPEC_TEXT)
        _git(repo, "add", "SPEC.md")
        _git(repo, "commit", "-q", "-m", "spec v1")
        _git(repo, "tag", "lane-test-v1")

        cfg = LaneConfig(repo_root=repo, brain_path=repo / ".brain", spec_path=spec)
        cfg.spec_tag = "lane-test-v1"
        cfg.spec_tag_commit = _git(repo, "rev-parse", "lane-test-v1^{commit}")
        cfg.spec_blob = _git(repo, "rev-parse", "lane-test-v1:SPEC.md")
        cfg.spec_body_sha256 = hashlib.sha256(spec.read_bytes()).hexdigest()
        yield repo, cfg


def test_clean_pin_verifies_with_no_drift(pinned_repo):
    """POSITIVE: nothing moved -> verified, and pointer_drift is False."""
    repo, cfg = pinned_repo
    out = SpecParser(cfg).verify_spec()
    assert out["verified"] is True
    assert out["pointer_drift"] is False
    assert "warning" not in out


def test_pointer_drift_with_identical_content_does_not_raise(pinned_repo):
    """THE ACTUAL BUG: retag onto a different commit carrying the SAME spec
    blob. Content is byte-identical. This must NOT raise -- it bricked the
    lane for 16 days."""
    repo, cfg = pinned_repo
    (repo / "unrelated.md").write_text("docs change, nothing to do with the spec\n")
    _git(repo, "add", "unrelated.md")
    _git(repo, "commit", "-q", "-m", "unrelated docs commit")
    _git(repo, "tag", "-f", "lane-test-v1")  # retag onto the new commit

    out = SpecParser(cfg).verify_spec()  # must not raise
    assert out["verified"] is True
    assert out["pointer_drift"] is True, "pointer drift should be reported, not hidden"
    assert "warning" in out and "byte-identical" in out["warning"]


def test_content_drift_STILL_hard_fails(pinned_repo):
    """OPPOSED, and the one that matters most: if the spec CONTENT actually
    changes, this must still raise. If this test ever passes-by-not-raising,
    the fix has destroyed the tamper detection it was supposed to preserve."""
    repo, cfg = pinned_repo
    (repo / "SPEC.md").write_text(SPEC_TEXT + "\n- [ ] Task 2: SMUGGLED IN\n")
    _git(repo, "add", "SPEC.md")
    _git(repo, "commit", "-q", "-m", "spec tampered")
    _git(repo, "tag", "-f", "lane-test-v1")

    with pytest.raises(SpecParseError):
        SpecParser(cfg).verify_spec()


def test_body_drift_on_disk_still_hard_fails(pinned_repo):
    """OPPOSED: spec edited on disk WITHOUT being committed -- git blob still
    matches, only the body hash catches it. Must still raise."""
    repo, cfg = pinned_repo
    (repo / "SPEC.md").write_text(SPEC_TEXT + "\n- [ ] Task 2: uncommitted tamper\n")
    with pytest.raises(SpecParseError):
        SpecParser(cfg).verify_spec()


def test_repin_updates_pointer_when_content_is_unchanged(pinned_repo):
    """POSITIVE: the recovery path that did not exist before."""
    repo, cfg = pinned_repo
    original = cfg.spec_tag_commit
    (repo / "unrelated.md").write_text("x\n")
    _git(repo, "add", "unrelated.md")
    _git(repo, "commit", "-q", "-m", "unrelated")
    _git(repo, "tag", "-f", "lane-test-v1")

    out = SpecParser(cfg).repin_tag_commit()
    assert out["new_commit"] != original
    assert out["content_verified_unchanged"] is True
    # and afterwards there is no drift at all
    assert SpecParser(cfg).verify_spec()["pointer_drift"] is False


def test_repin_REFUSES_when_content_actually_changed(pinned_repo):
    """OPPOSED, load-bearing: re-pin must never be usable to launder a changed
    spec into an accepted one. If this ever stops raising, repin_tag_commit
    has become a tamper-laundering tool."""
    repo, cfg = pinned_repo
    (repo / "SPEC.md").write_text(SPEC_TEXT + "\n- [ ] Task 2: SMUGGLED\n")
    _git(repo, "add", "SPEC.md")
    _git(repo, "commit", "-q", "-m", "tampered")
    _git(repo, "tag", "-f", "lane-test-v1")

    with pytest.raises(SpecParseError, match="REFUSING to re-pin"):
        SpecParser(cfg).repin_tag_commit()
