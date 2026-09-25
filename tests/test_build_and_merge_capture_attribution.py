"""Capture-at-the-commit: ``build_and_merge._commit_changed_files`` must emit
a QUALIFYING, machinery-attributed capture envelope on success, and NO
envelope at all on failure.

fw-1786271303 (artifact_attribution_live_wild_positive_still_unproven_
structural_gap) proved live that a plain ``nucleus build`` can never produce
a QUALIFYING ``artifact_ref`` envelope: vendor dispatches during EXECUTE
never commit, and the build's ONLY commit (``build_and_merge.
_commit_changed_files``) ran as a bare ``subprocess.run(["git", "commit"])``
outside :func:`vendor_dispatch.dispatch_and_capture` — the sole code path
that had ever written a capture envelope. 18/18 write dispatches in the wild
proving run read ``head_unchanged``.

fw-1786271394 (attribution_fix_direction_decided) is the chief's decided
fix: "capture-at-the-commit" — on a SUCCESSFUL commit, emit ONE envelope
through the SAME writer machinery ``dispatch_and_capture`` uses
(``vendor_dispatch._capture``, via the new
``vendor_dispatch.capture_machinery_commit``), labelled
``artifact_ref_source="machinery_derived"`` (NEVER ``"vendor_derived"`` —
"never fake a vendor label": no vendor CLI ran here).

These tests exercise the REAL ``_commit_changed_files`` against a real
throwaway git repo (no git/gh mutations of the actual project repo) and
inspect the relay envelope written to disk under an isolated
``NUCLEUS_BRAIN_PATH`` (set by conftest's autouse ``_ensure_brain_path``) —
the same evidence surface ``cross_repo_census`` reads. Classification is run
against the RAW JSON BYTES read back off disk, mirroring the wild proving
run's own methodology ("a FRESH-PROCESS import ... over the real envelope
files ... not the build's own verdict card"), not against any in-memory
return value.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mcp_server_nucleus.runtime import build_and_merge
from mcp_server_nucleus.runtime import cross_repo_census as census
from mcp_server_nucleus.runtime import vendor_dispatch as vd


# ── throwaway git repo helper (mirrors test_vendor_dispatch_artifact_attribution.py) ──
def _init_repo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.email", "t@t.invalid"],
        ["git", "config", "user.name", "t"],
    ):
        subprocess.run(cmd, cwd=repo, capture_output=True)
    (repo / "seed.txt").write_text("seed\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, capture_output=True)
    return repo


def _head_sha(repo: Path) -> str:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"git rev-parse HEAD failed: {r.stderr}"
    return r.stdout.strip()


def _relay_envelopes():
    """Every parsed relay envelope on disk under the isolated test brain, as
    ``(raw_envelope_dict, parsed_body_dict)`` pairs read straight off disk —
    the same artifact ``cross_repo_census`` reads.
    """
    brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
    out = []
    relay = brain / "relay"
    if not relay.exists():
        return out
    for f in relay.rglob("*.json"):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            body = msg.get("body")
            parsed = json.loads(body) if isinstance(body, str) else body
        except Exception:
            continue
        if isinstance(parsed, dict) and "vendor" in parsed:
            out.append((msg, parsed))
    return out


def _machinery_envelopes():
    return [
        (msg, body) for msg, body in _relay_envelopes()
        if body.get("vendor") == "build_and_merge"
    ]


# ── must-now-pass: successful commit → exactly ONE qualifying envelope ────────

def test_successful_commit_emits_exactly_one_machinery_derived_envelope(
    tmp_path, monkeypatch,
):
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    monkeypatch.chdir(repo)

    (repo / "changed.txt").write_text("changed\n")

    ok = build_and_merge._commit_changed_files(
        ["changed.txt"], "build --merge: test commit",
    )
    assert ok is True

    head_after = _head_sha(repo)
    assert head_after != head_before

    envs = _machinery_envelopes()
    assert len(envs) == 1, f"expected exactly ONE envelope, got {len(envs)}: {envs}"
    msg, body = envs[0]

    # Field set the census's qualification logic needs.
    assert body["vendor"] == "build_and_merge"
    assert body["artifact_ref_source"] == "machinery_derived"
    assert body.get("artifact_ref_nonqualifying_reason") is None
    assert body["artifact_refs"] == [head_after]

    # Fresh-process-style classification, read straight off the JSON on disk.
    assert census._is_machinery_derived_artifact_ref(msg) is True
    # Never fakes a vendor label: this must NOT satisfy the vendor-derived
    # predicate crit-(c)'s cross-vendor coordination span relies on.
    assert census._is_vendor_derived_artifact_ref(msg) is False
    assert census._artifact_ref_attribution_unprovable(msg) is False


def test_successful_commit_records_expect_paths_and_heads(tmp_path, monkeypatch):
    """The envelope's changed_paths + head_before/head_after must reflect the
    ACTUAL commit, verified via the same git-evidence machinery
    ``dispatch_and_capture`` uses — not merely echoed from the caller."""
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    monkeypatch.chdir(repo)

    (repo / "changed.txt").write_text("changed\n")
    (repo / "also_changed.txt").write_text("also changed\n")

    ok = build_and_merge._commit_changed_files(
        ["changed.txt", "also_changed.txt"], "build --merge: two files",
    )
    assert ok is True
    head_after = _head_sha(repo)

    envs = _machinery_envelopes()
    assert len(envs) == 1
    _msg, body = envs[0]
    assert body["artifact_ref_source"] == "machinery_derived"
    assert body["artifact_refs"] == [head_after]
    assert head_after != head_before


# ── must-still-fail/hold (a): a FAILED commit emits NO qualifying envelope ────

def test_failed_commit_emits_no_envelope(tmp_path, monkeypatch):
    """``git add`` on a nonexistent path fails the commit before HEAD ever
    moves. ``_commit_changed_files`` must return False, and — because capture
    is only attempted AFTER a successful commit — NO envelope of any kind
    (qualifying or otherwise) is emitted."""
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    monkeypatch.chdir(repo)

    ok = build_and_merge._commit_changed_files(
        ["does_not_exist.txt"], "build --merge: should fail",
    )
    assert ok is False
    assert _head_sha(repo) == head_before, "HEAD must not move on a failed commit"
    assert _machinery_envelopes() == [], "a failed commit must emit NO envelope"


def test_empty_changed_files_emits_no_envelope(tmp_path, monkeypatch):
    """The pre-existing empty-changed-files guard short-circuits before any
    git call — still no envelope."""
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)

    ok = build_and_merge._commit_changed_files([], "build --merge: nothing")
    assert ok is False
    assert _machinery_envelopes() == []


# ── capture_machinery_commit unit-level: qualification predicate itself ──────

def test_capture_machinery_commit_head_unchanged_does_not_qualify(tmp_path):
    """Direct unit test of the reused qualification predicate: if HEAD did
    not move, the envelope must be captured but labelled non-qualifying —
    never ``machinery_derived``."""
    repo = _init_repo(tmp_path)
    sha = _head_sha(repo)

    out = vd.capture_machinery_commit(
        producer="build_and_merge",
        changed_files=["seed.txt"],
        pre_head=sha,
        post_head=sha,
        commit_message="no-op",
    )
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "head_unchanged"


def test_capture_machinery_commit_no_head_fails_closed():
    """No git SHA available (e.g. worktree HEAD unreadable) ⇒ fail closed:
    no artifact_ref, no relay/engram capture attempted."""
    out = vd.capture_machinery_commit(
        producer="build_and_merge",
        changed_files=["x.txt"],
        pre_head=None,
        post_head=None,
        commit_message="unreadable head",
    )
    assert out["artifact_ref"] is None
    assert out["artifact_ref_source"] == "machinery_derived_failed"
    assert out["capture"]["relay"] is None
    assert out["capture"]["engram"] is None
