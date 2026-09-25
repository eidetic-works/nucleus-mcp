"""Artifact-ref attribution tests for ``dispatch_and_capture``.

These tests pin the v3.3 attribution logic in
:func:`mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture` — the
code that decides whether a dispatch ``qualifies`` as a vendor-derived causal
increment, and which ``artifact_ref_source`` / ``nonqualifying_reason`` label
the capture envelope carries.

PRINCIPAL v3 (line 77) requires the artifact-ref be VENDOR-DERIVED, stamped
from the vendor worktree's git-reported SHA — never accepted as caller input.
v3.1 closed the "cd-chosen SHA" hole (ambient HEAD does not qualify). v3.2
(2026-08-09) closed the empty-commit hole: ``head_moved`` alone is insufficient
because ``git commit --allow-empty`` moves HEAD without touching any file, and
a mid-range git failure can hide what the commits touched. v3.3 (2026-08-09)
closed the foreign-concurrent-commit hole: when the caller provides
``expect_paths``, the moved HEAD's commit_paths are intersected with the
dispatch's own changed_paths to attribute the increment. The qualifying
predicate is now:

    qualifies <=> mode is write
                  AND HEAD moved while the vendor ran
                  AND _commits_changed_paths(pre, post) is not None
                  AND that set is non-empty
                  AND (if expect_paths provided) the intersection of
                      commit_paths and the dispatch's changed_paths is non-empty

When no ``expect_paths`` is provided, the intersection check is skipped and
the instrument falls back to the v3.2 check (head moved + commit_paths
non-empty) — the v3.3 intersection is a TIGHTENING for callers who opt into
path evidence, not a breaking change for those who don't.

Every other combination is captured (relay + engram still written) but labelled
``no_vendor_increment`` with a precise reason, so it is visible and uncountable
rather than invisible. When git is unavailable the capture FAILS CLOSED — no
artifact_ref, no envelope.

Harness (per task spec):
  * Each test builds a throwaway git repo under ``tmp_path`` (``git init`` +
    ``git config user.email/name`` inside that repo only, commits via
    ``subprocess.run`` with ``cwd=repo``).
  * The vendor executor is stubbed (``monkeypatch`` of ``VendorCLIExecutor``)
    so NO real vendor CLI runs; the stub's ``run()`` performs the configured
    git action in the throwaway repo (commit a file / empty commit / nothing)
    and returns a canned ``VendorResult``.
  * The git helpers ``_read_worktree_head_sha`` and ``_commits_changed_paths``
    are routed to the throwaway repo by monkeypatching their ``cwd`` argument,
    so the real implementations run against real git — the attribution logic is
    genuinely exercised, not stubbed around.

These tests NEVER touch the real ``agy``/``devin`` binaries, never mutate the
process cwd, and never write to a production brain (conftest's autouse
``_ensure_brain_path`` pins ``NUCLEUS_BRAIN_PATH`` to a temp dir).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest

from mcp_server_nucleus.runtime import vendor_dispatch as vd


# ── throwaway git repo helper ─────────────────────────────────────────────────
def _init_repo(tmp_path: Path, name: str = "repo") -> Path:
    """A temp git repo with one seed commit; returned as a Path.

    All git commands run with ``cwd=repo`` so the repo is fully self-contained
    and never touches the process cwd or any ambient worktree.
    """
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
    """Read the current HEAD SHA of *repo* (40 chars)."""
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    )
    assert r.returncode == 0, f"git rev-parse HEAD failed in {repo}: {r.stderr}"
    return r.stdout.strip()


# ── git-helper routing ────────────────────────────────────────────────────────
def _route_git_to(monkeypatch, repo: Path) -> None:
    """Route ``_read_worktree_head_sha``, ``_commits_changed_paths``, and
    ``_repo_relative_posix`` to *repo* by injecting ``cwd=str(repo)`` into
    every call.

    The real implementations are preserved — only the cwd argument is pinned —
    so the v3.2 attribution logic runs against real git, not a stub. This is
    hermetic: the process cwd is never changed, so no ambient worktree can
    leak a SHA into the stamp.
    """
    _real_read = vd._read_worktree_head_sha
    _real_commits = vd._commits_changed_paths
    _real_relpos = vd._repo_relative_posix
    monkeypatch.setattr(
        vd, "_read_worktree_head_sha",
        lambda cwd=None: _real_read(cwd=str(repo)),
    )
    monkeypatch.setattr(
        vd, "_commits_changed_paths",
        lambda pre, post, cwd=None: _real_commits(pre, post, cwd=str(repo)),
    )
    monkeypatch.setattr(
        vd, "_repo_relative_posix",
        lambda path, cwd=None: _real_relpos(path, cwd=str(repo)),
    )


# ── stubbed vendor executor ───────────────────────────────────────────────────
def _git_action(repo: Path, action: str) -> None:
    """Perform the git side-effect the stubbed vendor "produced".

    * ``commit_file``  — append + commit a real file (HEAD moves, files change).
    * ``empty_commit`` — ``git commit --allow-empty`` (HEAD moves, NO files).
    * ``nothing``      — no git action (HEAD unchanged).
    """
    if action == "commit_file":
        (repo / "vendor_work.txt").write_text("increment\n")
        subprocess.run(["git", "add", "vendor_work.txt"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "vendor increment"], cwd=repo, capture_output=True
        )
    elif action == "empty_commit":
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "empty"],
            cwd=repo, capture_output=True,
        )
    elif action == "nothing":
        pass
    else:  # pragma: no cover — defensive
        raise ValueError(f"unknown stub git action {action!r}")


def _stub_executor_cls(repo: Path, action: str):
    """Return a class that replaces ``VendorCLIExecutor`` for one test.

    The stub's ``run()`` performs the configured git action in *repo* and
    returns a canned successful ``VendorResult``. No real vendor CLI is ever
    invoked. The constructor signature mirrors the real
    ``VendorCLIExecutor.__init__`` so ``dispatch_and_capture`` can build it
    unchanged.
    """

    class _StubExecutor:
        def __init__(self, vendor, prompt, *, timeout_s, budget_usd, model, mode):
            self.vendor = vendor
            self.mode = mode

        def run(self):
            _git_action(repo, action)
            spec = vd.VENDOR_SPECS[self.vendor]
            return vd.VendorResult(
                vendor=self.vendor,
                model=spec.model,
                rc=0,
                status="ok",
                result="stub vendor output",
                duration=0.0,
                model_id=spec.default_model,
            )

    return _StubExecutor


# ── shared fixture: stub the observability side-effects we are NOT testing ────
@pytest.fixture(autouse=True)
def _isolate_attribution(monkeypatch):
    """Pin the cross-vendor flag on, STRICT relay on, and neutralize the two
    best-effort git guards (stale-checkout / rebase-in-progress) and the
    model-health recorder so they cannot add noise or mutate global state.

    These guards are exercised by their own tests in ``test_vendor_dispatch``;
    here they are not under test and shelling out to git in the process cwd
    would be non-hermetic. The attribution logic itself runs against the
    throwaway repo via :func:`_route_git_to`.
    """
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    monkeypatch.setattr(vd, "_count_behind_upstream", lambda *a, **k: 0)
    monkeypatch.setattr(vd, "_rebase_or_merge_in_progress", lambda *a, **k: None)
    monkeypatch.setattr(vd, "_record_dispatch_health", lambda *a, **k: None)


# ── envelope inspection helper ────────────────────────────────────────────────
def _relay_envelopes():
    """All parsed vendor capture envelopes on disk for the current temp brain."""
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


# ── 1. qualifying: write mode + HEAD moved + files changed ───────────────────
def test_write_mode_head_moved_files_changed_qualifies(tmp_path, monkeypatch):
    """The one qualifying path: a write-mode dispatch where the vendor moves
    HEAD and the new commit touches at least one file.

    ``artifact_ref_source`` MUST be ``vendor_derived``; the stamped
    ``artifact_ref`` is the POST-dispatch SHA; the caller's ref is discarded;
    the relay envelope carries the vendor-derived SHA.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))

    caller_ref = "caller_provided_ref_123"
    out = vd.dispatch_and_capture(
        "agy", "build the thing", caller_ref, to_role="peer",
        timeout_s=10, mode="write",
        expect_paths=[str(repo / "vendor_work.txt")],
    )

    assert out["status"] == "ok", out
    assert out["artifact_ref_source"] == "vendor_derived"
    assert "artifact_ref_nonqualifying_reason" not in out
    # The stamped ref is the POST-dispatch SHA, and HEAD genuinely moved.
    assert out["artifact_ref"] == out["head_after"]
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    assert len(out["artifact_ref"]) == 40
    # The caller's string is discarded everywhere it could hide.
    assert out["artifact_ref"] != caller_ref
    assert out["capture"]["relay"].get("sent") is True
    _msg, body = _relay_envelopes()[-1]
    assert body["artifact_refs"] == [out["artifact_ref"]]
    assert caller_ref not in json.dumps(body)


# ── 2. read mode never qualifies, even when HEAD moved ───────────────────────
def test_read_mode_never_qualifies_even_when_head_moved(tmp_path, monkeypatch):
    """A read-mode dispatch produces no increment by definition. Even if the
    stub "moved" HEAD (it won't here, but the point holds), read mode can never
    mint a causal edge. The reason is ``read_mode_no_increment`` and the
    envelope is still captured (visible + uncountable, not hidden).
    """
    repo = _init_repo(tmp_path)
    _route_git_to(monkeypatch, repo)
    # The stub commits a file, but mode=read means it does not count.
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))

    out = vd.dispatch_and_capture(
        "agy", "review the code", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="read",
    )

    assert out["status"] == "ok", out
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "read_mode_no_increment"
    # Still captured — labelling closes the hole, suppressing capture would
    # close the relay pathway instead.
    assert out["capture"]["relay"] is not None
    assert out["capture"]["relay"].get("sent") is True


# ── 3. write mode + HEAD unchanged (vendor committed nothing) ────────────────
def test_write_mode_head_unchanged_is_head_unchanged(tmp_path, monkeypatch):
    """A write-mode dispatch that commits nothing leaves HEAD where it was.
    The reason is ``head_unchanged``; the envelope is still captured.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "nothing"))

    out = vd.dispatch_and_capture(
        "agy", "build but skip", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="write",
    )

    assert out["status"] == "ok", out
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "head_unchanged"
    assert out["head_before"] == head_before
    assert out["head_after"] == head_before
    assert out["capture"]["relay"].get("sent") is True


# ── 4. write mode + empty commit (HEAD moved, no files) ──────────────────────
def test_write_mode_empty_commit_is_empty_commit_no_files(tmp_path, monkeypatch):
    """v3.2 hole: ``git commit --allow-empty`` moves HEAD without touching any
    file. ``head_moved`` alone must NOT qualify — the instrument can only
    qualify an increment whose touched paths it can verify, and an empty commit
    touches nothing. The reason is ``empty_commit_no_files``.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "empty_commit"))

    out = vd.dispatch_and_capture(
        "agy", "build nothing", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="write",
    )

    assert out["status"] == "ok", out
    # HEAD genuinely moved — this is what makes the v3.2 guard necessary.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    # ...yet it does NOT qualify, because no files were touched.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "empty_commit_no_files"
    assert out["capture"]["relay"].get("sent") is True


# ── 5. write mode + HEAD moved + _commits_changed_paths unavailable ──────────
def test_write_mode_changed_paths_unavailable_when_helper_fails(tmp_path, monkeypatch):
    """If ``_commits_changed_paths`` returns ``None`` (git failure mid-range,
    bad rev, not a repo) the instrument FAILS CLOSED: it cannot verify what the
    commits touched, so it must not qualify the increment. The reason is
    ``changed_paths_unavailable``. HEAD moved and files may have changed, but
    the inability to VERIFY is itself disqualifying.
    """
    repo = _init_repo(tmp_path)
    _route_git_to(monkeypatch, repo)
    # Override the changed-paths helper to simulate a git failure AFTER the
    # routing patch (so _read_worktree_head_sha still reads the real repo).
    monkeypatch.setattr(vd, "_commits_changed_paths", lambda *a, **k: None)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))

    out = vd.dispatch_and_capture(
        "agy", "build the thing", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="write",
    )

    assert out["status"] == "ok", out
    # HEAD moved (the stub committed a real file)...
    assert out["head_after"] != out["head_before"]
    # ...but the changed-paths verifier returned None, so it does not qualify.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "changed_paths_unavailable"
    assert out["capture"]["relay"].get("sent") is True


# ── 6. no git SHA → fail closed (no artifact_ref, no capture) ────────────────
def test_no_git_sha_fails_closed(tmp_path, monkeypatch):
    """When ``_read_worktree_head_sha`` returns None (git unavailable / not a
    repo) the capture FAILS CLOSED: ``artifact_ref`` is None, the source is
    ``vendor_derived_failed``, and NO relay envelope is written. It must NEVER
    fall back to the caller's value — that is precisely the forgeable path
    PRINCIPAL v3 line 77 forbids.
    """
    repo = _init_repo(tmp_path)
    # No routing: force the stamp to return None on both reads.
    monkeypatch.setattr(vd, "_read_worktree_head_sha", lambda *a, **k: None)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))

    caller_ref = "caller_provided_ref_456"
    out = vd.dispatch_and_capture(
        "agy", "review", caller_ref, to_role="peer", timeout_s=10, mode="write",
    )

    assert out["artifact_ref"] is None
    assert out["artifact_ref_source"] == "vendor_derived_failed"
    assert out["capture"]["relay"] is None
    assert out["capture"]["error"] == "worktree_sha_unavailable"
    # The caller's string must not survive the fail-closed path either.
    assert caller_ref not in json.dumps(out, default=str)


# ── 7. caller's artifact_ref is discarded from the envelope (regression) ─────
def test_caller_artifact_ref_discarded_from_envelope(tmp_path, monkeypatch):
    """REGRESSION GUARD for the unconditional discard (2026-07-31): with NO
    artifact-ref env flag set, the caller's ``artifact_ref`` is ignored and the
    stamped SHA wins. The envelope must carry the stamped SHA and must NOT
    contain the caller's string anywhere.
    """
    repo = _init_repo(tmp_path)
    _route_git_to(monkeypatch, repo)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))
    # Belt-and-suspenders: the conftest already deletes this, but the invariant
    # must hold even if someone re-exportsed it.
    monkeypatch.delenv("NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED", raising=False)

    caller_ref = "FORGEABLE_CALLER_REF_xyz"
    out = vd.dispatch_and_capture(
        "agy", "build", caller_ref, to_role="peer", timeout_s=10, mode="write",
        expect_paths=[str(repo / "vendor_work.txt")],
    )

    assert out["artifact_ref_source"] == "vendor_derived"
    assert out["artifact_ref"] != caller_ref
    assert len(out["artifact_ref"]) == 40
    _msg, body = _relay_envelopes()[-1]
    assert body["artifact_refs"] == [out["artifact_ref"]]
    assert caller_ref not in json.dumps(body)


# ── 8. CONTROL (written first): foreign concurrent commit, dispatch commits nothing ──
def test_foreign_commit_is_head_moved_by_foreign_commit(tmp_path, monkeypatch):
    """THE CONTROL — written first, before the fix it pins was trusted.

    Scenario: a write-mode dispatch commits NOTHING of its own (it touches
    ``dispatch_work.txt`` in the working tree but does not commit it), while a
    FOREIGN concurrent commit touches only ``Y_foreign.txt`` and moves HEAD.

    Pre-fix (v3.2) rule returned True here: ``head_moved`` was True (the
    foreign commit moved HEAD) and ``commit_paths`` was non-empty
    (``{Y_foreign.txt}``), so the v3.2 predicate — which only checked
    ``head_moved`` + non-empty ``commit_paths`` — qualified the envelope,
    crediting the foreign lane's commit to a dispatch that produced no commit
    of its own. That was the foreign-concurrent-commit hole (v3.3 comment,
    vendor_dispatch.py lines 1415-1443): the cheapest attack on crit-3 needed
    no cd and no confederate — just run a dispatch while any other lane
    commits, and the ambient HEAD movement scores the envelope for free.

    The v3.3 intersection check closes it: the dispatch's own ``changed_paths``
    (``{dispatch_work.txt}``, captured via ``expect_paths``) are intersected
    with the commit's touched paths (``{Y_foreign.txt}``). The intersection is
    empty → ``qualifies`` is False, reason ``head_moved_by_foreign_commit``.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    # _repo_relative_posix is called without cwd in the attribution block
    # (vendor_dispatch.py line ~1456). Without routing it to the repo, path
    # normalization runs against the process cwd and every path falls outside
    # the repo toplevel (returns None), collapsing normalized_changed to the
    # empty set — which would correctly label the reason as
    # attribution_unprovable (normalization failure), NOT the
    # head_moved_by_foreign_commit we are testing here. Routing ensures
    # normalization succeeds so the intersection is genuinely empty (foreign
    # commit), proving the foreign-commit detection works.
    _real_rel = vd._repo_relative_posix
    monkeypatch.setattr(
        vd, "_repo_relative_posix",
        lambda p, cwd=None: _real_rel(p, cwd=str(repo)),
    )

    dispatch_file = repo / "dispatch_work.txt"

    class _ForeignConcurrentStub:
        def __init__(self, vendor, prompt, *, timeout_s, budget_usd, model, mode):
            self.vendor = vendor
            self.mode = mode

        def run(self):
            # The dispatch touches its own working file but commits NOTHING.
            dispatch_file.write_text("dispatch output\n")
            # A FOREIGN concurrent commit touches only Y_foreign.txt.
            (repo / "Y_foreign.txt").write_text("foreign\n")
            subprocess.run(
                ["git", "add", "Y_foreign.txt"], cwd=repo, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "foreign concurrent commit"],
                cwd=repo, capture_output=True,
            )
            spec = vd.VENDOR_SPECS[self.vendor]
            return vd.VendorResult(
                vendor=self.vendor,
                model=spec.model,
                rc=0,
                status="ok",
                result="stub vendor output",
                duration=0.0,
                model_id=spec.default_model,
            )

    monkeypatch.setattr(vd, "VendorCLIExecutor", _ForeignConcurrentStub)

    out = vd.dispatch_and_capture(
        "agy", "build the thing", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="write",
        expect_paths=[str(dispatch_file)],
    )

    assert out["status"] == "ok", out
    # HEAD genuinely moved — the foreign commit moved it.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    # ...but the dispatch does NOT qualify: the only commit is foreign.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "head_moved_by_foreign_commit"
    assert out["capture"]["relay"].get("sent") is True


# ── 9. FOREIGN COMMIT + UNRELATED LOCAL EDIT (test (2)) ───────────────────────
def test_foreign_commit_unrelated_local_edit_is_head_moved_by_foreign_commit(
    tmp_path, monkeypatch,
):
    """test (2) — FOREIGN COMMIT + UNRELATED LOCAL EDIT.

    Scenario: a write-mode dispatch modifies ``X.txt`` in the working tree
    (declared via ``expect_paths``) but does NOT commit it, while a FOREIGN
    concurrent commit touches only ``Y_foreign.txt`` and moves HEAD.

    The dispatch's own ``changed_paths`` (``{X.txt}``, captured via
    ``expect_paths``) are intersected with the moved HEAD's commit paths
    (``{Y_foreign.txt}``). The intersection is empty — the dispatch touched
    nothing the foreign commit touched — so ``qualifies`` is False and the
    reason is ``head_moved_by_foreign_commit``. HEAD genuinely moved (the
    foreign commit moved it), yet the envelope must not be credited to the
    dispatch: the only commit in the pre..post range is foreign and shares no
    path with the dispatch's own work.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    # _repo_relative_posix is called without cwd in the attribution block
    # (vendor_dispatch.py line ~1456). Without routing it to the repo, path
    # normalization runs against the process cwd and every path falls outside
    # the repo toplevel (returns None), collapsing normalized_changed to the
    # empty set — which would correctly label the reason as
    # attribution_unprovable (normalization failure), NOT the
    # head_moved_by_foreign_commit we are testing here. Routing ensures
    # normalization succeeds so the intersection is genuinely empty (foreign
    # commit), proving the foreign-commit detection works.
    _real_rel = vd._repo_relative_posix
    monkeypatch.setattr(
        vd, "_repo_relative_posix",
        lambda p, cwd=None: _real_rel(p, cwd=str(repo)),
    )

    x_file = repo / "X.txt"

    class _ForeignConcurrentStub:
        def __init__(self, vendor, prompt, *, timeout_s, budget_usd, model, mode):
            self.vendor = vendor
            self.mode = mode

        def run(self):
            # The dispatch modifies X.txt in the working tree but commits NOTHING.
            x_file.write_text("dispatch output\n")
            # A FOREIGN concurrent commit touches only Y_foreign.txt.
            (repo / "Y_foreign.txt").write_text("foreign\n")
            subprocess.run(
                ["git", "add", "Y_foreign.txt"], cwd=repo, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "foreign concurrent commit"],
                cwd=repo, capture_output=True,
            )
            spec = vd.VENDOR_SPECS[self.vendor]
            return vd.VendorResult(
                vendor=self.vendor,
                model=spec.model,
                rc=0,
                status="ok",
                result="stub vendor output",
                duration=0.0,
                model_id=spec.default_model,
            )

    monkeypatch.setattr(vd, "VendorCLIExecutor", _ForeignConcurrentStub)

    out = vd.dispatch_and_capture(
        "agy", "build the thing", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="write",
        expect_paths=[str(x_file)],
    )

    assert out["status"] == "ok", out
    # HEAD genuinely moved — the foreign commit moved it.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    # ...but the dispatch does NOT qualify: its X.txt is unrelated to the
    # foreign commit's Y_foreign.txt, so the intersection is empty.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "head_moved_by_foreign_commit"
    assert out["capture"]["relay"].get("sent") is True


# ── 10. POSITIVE CONTROL (test (3)): dispatch commits its own X.txt ──────────
def test_dispatch_commits_own_x_txt_qualifies_vendor_derived(tmp_path, monkeypatch):
    """test (3) — POSITIVE CONTROL for the v3.3 intersection check.

    The v3.3 fix (tests 8 and 9 above) closes the foreign-concurrent-commit
    hole by intersecting the moved HEAD's ``commit_paths`` with THIS
    dispatch's own ``changed_paths`` (captured via ``expect_paths``). That
    intersection is empty when the only commit is foreign, so the envelope
    does not qualify. This test proves the same check does NOT break
    qualification permanently: when the dispatch modifies ``X.txt`` AND
    commits that change itself, the commit's touched paths (``{X.txt}``)
    intersect the dispatch's own ``changed_paths`` (``{X.txt}``) — the
    intersection is non-empty, so ``qualifies`` is True and
    ``artifact_ref_source == "vendor_derived"``.

    Without this control, a regression that collapsed every intersection
    to the empty set (e.g. a normalization bug that returned ``None`` for
    every path) would pass tests 8 and 9 (both assert the empty-intersection
    outcome) while silently breaking the one path that must qualify. This
    test is the guard against that: it asserts the NON-empty-intersection
    outcome, so a global break is caught.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    # _repo_relative_posix is called without cwd in the attribution block
    # (vendor_dispatch.py line ~1456). Without routing it to the repo, path
    # normalization runs against the process cwd and every path falls outside
    # the repo toplevel (returns None), collapsing normalized_changed to the
    # empty set — which would label this positive control as
    # attribution_unprovable (normalization failure) instead of the
    # vendor_derived we are testing here. Route it the same way tests 8 and 9
    # do so normalization succeeds and the intersection is genuinely non-empty.
    _real_rel = vd._repo_relative_posix
    monkeypatch.setattr(
        vd, "_repo_relative_posix",
        lambda p, cwd=None: _real_rel(p, cwd=str(repo)),
    )

    x_file = repo / "X.txt"

    class _CommitsOwnXStub:
        def __init__(self, vendor, prompt, *, timeout_s, budget_usd, model, mode):
            self.vendor = vendor
            self.mode = mode

        def run(self):
            # The dispatch modifies X.txt AND commits that change itself.
            x_file.write_text("dispatch increment\n")
            subprocess.run(["git", "add", "X.txt"], cwd=repo, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "dispatch commits its own X.txt"],
                cwd=repo, capture_output=True,
            )
            spec = vd.VENDOR_SPECS[self.vendor]
            return vd.VendorResult(
                vendor=self.vendor,
                model=spec.model,
                rc=0,
                status="ok",
                result="stub vendor output",
                duration=0.0,
                model_id=spec.default_model,
            )

    monkeypatch.setattr(vd, "VendorCLIExecutor", _CommitsOwnXStub)

    caller_ref = "caller_provided_ref_posctrl"
    out = vd.dispatch_and_capture(
        "agy", "build the thing", caller_ref, to_role="peer",
        timeout_s=10, mode="write",
        expect_paths=[str(x_file)],
    )

    assert out["status"] == "ok", out
    # HEAD genuinely moved — the dispatch's own commit moved it.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    # The intersection is non-empty (X.txt is in both commit_paths and the
    # dispatch's own changed_paths), so the envelope QUALIFIES.
    assert out["artifact_ref_source"] == "vendor_derived"
    assert "artifact_ref_nonqualifying_reason" not in out
    # The stamped ref is the POST-dispatch SHA; the caller's ref is discarded.
    assert out["artifact_ref"] == out["head_after"]
    assert len(out["artifact_ref"]) == 40
    assert out["artifact_ref"] != caller_ref
    assert out["capture"]["relay"].get("sent") is True
    _msg, body = _relay_envelopes()[-1]
    assert body["artifact_refs"] == [out["artifact_ref"]]
    assert caller_ref not in json.dumps(body)


# ── 11. NO expect_paths → ATTRIBUTION UNPROVABLE (test (4)): write mode, head moved, no expect_paths ─
def test_write_mode_head_moved_no_expect_paths_is_attribution_unprovable(
    tmp_path, monkeypatch,
):
    """test (4) — NO expect_paths → ATTRIBUTION UNPROVABLE.

    Permanent guard against the v3.2 fallback hole returning.

    Scenario: a write-mode dispatch commits a real file (HEAD moves, the
    commit touches a path), but the caller passed NO ``expect_paths`` — so
    the instrument has no evidence of which paths THIS dispatch modified.

    The v3.3 intersection check needs the dispatch's own ``changed_paths``
    (captured via ``expect_paths``) to attribute the moved HEAD's commits to
    this dispatch. With no ``expect_paths``, ``changed_paths`` is ``[]`` and
    the intersection cannot be computed. The v3.2 fallback (head moved +
    commit_paths non-empty → qualify) was a hole: a foreign concurrent commit
    could ride along on the moved HEAD and get attributed to this dispatch.
    That fallback is now CLOSED. With no path evidence, attribution is
    UNPROVABLE — the instrument does NOT qualify the envelope, does NOT stamp
    a vendor-derived ref, and the caller's ref is discarded.

    This test is a permanent guard: if the v3.2 fallback ever returns, this
    test fails. The dispatch still succeeds (HEAD genuinely moved), but
    ``artifact_ref_source == "no_vendor_increment"`` and
    ``artifact_ref_nonqualifying_reason == "attribution_unprovable"``. The
    hole IS closed for any caller who provides ``expect_paths`` (see tests 8,
    9, and the positive control 10).
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))

    caller_ref = "caller_provided_ref_no_expect"
    out = vd.dispatch_and_capture(
        "agy", "build the thing", caller_ref, to_role="peer",
        timeout_s=10, mode="write",
        # NOTE: no expect_paths — the caller opted out of path evidence.
    )

    assert out["status"] == "ok", out
    # HEAD genuinely moved — the stub committed a real file.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    # No expect_paths → no path evidence → attribution UNPROVABLE. The v3.2
    # fallback (head moved + commit_paths non-empty → qualify) is closed.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "attribution_unprovable"
    # The caller's ref is discarded — never stamped as the artifact_ref.
    assert out["artifact_ref"] != caller_ref
    assert out["capture"]["relay"].get("sent") is True
    _msg, body = _relay_envelopes()[-1]
    assert caller_ref not in json.dumps(body)


# ── 12. REGRESSION RE-RUN GUARD (test (5)) ────────────────────────────────────
# Re-executes every one of the original 7 scenarios in a single parametrized
# sweep and asserts (a) the v3.2/v3.3 attribution verdict is unchanged and
# (b) the capture/relay side-effect fires in every NON-qualifying case (and
# is correctly absent on the fail-closed path). This is the guard that catches
# a regression in any one of the 7 without needing to read 7 separate test
# reports — one parametrized id, one verdict per case, one relay assertion.
#
# The 7 cases mirror tests 1–7 above EXACTLY (same stub action, same mode,
# same git-helper routing). The existing 7 tests are left untouched; this
# test re-derives their invariants independently so a future change that
# breaks one is caught twice.
_QUALIFYING = "vendor_derived"
_NONQUAL = "no_vendor_increment"
_FAILED = "vendor_derived_failed"


@pytest.mark.parametrize(
    "case_id, action, mode, override_changed_paths, override_no_sha, "
    "expect_source, expect_reason, expect_relay_sent, expect_paths",
    [
        # 1. qualifying: write + HEAD moved + files changed → vendor_derived, relay sent.
        #    expect_paths carries the stub's committed filename (resolved to an
        #    absolute list in the body, where repo is in scope) so the verdict is
        #    proven via the path intersection, not the closed v3.2 fallback.
        ("1_qualifying", "commit_file", "write", False, False, _QUALIFYING, None, True,
         "vendor_work.txt"),
        # 2. read mode never qualifies → read_mode_no_increment, relay STILL sent.
        ("2_read_mode", "commit_file", "read", False, False, _NONQUAL,
         "read_mode_no_increment", True, None),
        # 3. head unchanged → head_unchanged, relay STILL sent.
        ("3_head_unchanged", "nothing", "write", False, False, _NONQUAL,
         "head_unchanged", True, None),
        # 4. empty commit → empty_commit_no_files, relay STILL sent.
        ("4_empty_commit", "empty_commit", "write", False, False, _NONQUAL,
         "empty_commit_no_files", True, None),
        # 5. helper failure (changed_paths None) → changed_paths_unavailable, relay STILL sent.
        ("5_helper_failure", "commit_file", "write", True, False, _NONQUAL,
         "changed_paths_unavailable", True, None),
        # 6. no SHA → fail closed: vendor_derived_failed, relay NOT sent (None).
        ("6_no_sha_fail_closed", "commit_file", "write", False, True, _FAILED,
         None, False, None),
        # 7. caller-ref discarded → qualifying, relay sent, caller ref gone.
        ("7_caller_ref_discarded", "commit_file", "write", False, False, _QUALIFYING,
         None, True, "vendor_work.txt"),
    ],
    ids=[
        "qualifying",
        "read_mode",
        "head_unchanged",
        "empty_commit",
        "helper_failure",
        "no_sha_fail_closed",
        "caller_ref_discarded",
    ],
)
def test_regression_rerun_guard_for_original_seven(
    tmp_path, monkeypatch, case_id, action, mode,
    override_changed_paths, override_no_sha,
    expect_source, expect_reason, expect_relay_sent, expect_paths,
):
    """test (5) — REGRESSION RE-RUN GUARD.

    Re-runs all 7 original scenarios in one parametrized sweep and asserts:
      * the attribution verdict (``artifact_ref_source`` + reason) is unchanged;
      * capture/relay fires in EVERY non-qualifying case (read mode, head
        unchanged, empty commit, helper failure) — labelling closes the hole,
        suppressing capture would close the relay pathway instead;
      * the fail-closed path (no SHA) correctly suppresses relay (``None``);
      * the qualifying + caller-ref-discard cases still mint a vendor-derived
        SHA and relay it.

    The existing 7 tests are NOT modified. This guard re-derives their
    invariants independently so a regression in any one is caught twice.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)

    if override_no_sha:
        # Case 6: force the SHA reader to return None on both reads.
        monkeypatch.setattr(vd, "_read_worktree_head_sha", lambda *a, **k: None)
    else:
        _route_git_to(monkeypatch, repo)

    if override_changed_paths:
        # Case 5: simulate a git failure AFTER routing so the SHA reader still
        # works but _commits_changed_paths returns None.
        monkeypatch.setattr(vd, "_commits_changed_paths", lambda *a, **k: None)

    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, action))

    caller_ref = "FORGEABLE_CALLER_REF_guard"
    # expect_paths carries a filename sentinel for the qualifying cases (1, 7);
    # repo is a function-local, not in scope at parametrize collection time, so
    # the absolute list is resolved here. Non-qualifying cases pass None.
    if expect_paths is not None:
        expect_paths = [str(repo / expect_paths)]
    out = vd.dispatch_and_capture(
        "agy", "build the thing", caller_ref, to_role="peer",
        timeout_s=10, mode=mode,
        expect_paths=expect_paths,
    )

    assert out["status"] == "ok", f"{case_id}: status not ok: {out}"

    # ── attribution verdict ──────────────────────────────────────────────
    assert out["artifact_ref_source"] == expect_source, (
        f"{case_id}: expected source {expect_source!r}, "
        f"got {out['artifact_ref_source']!r}"
    )
    if expect_reason is not None:
        assert out.get("artifact_ref_nonqualifying_reason") == expect_reason, (
            f"{case_id}: expected reason {expect_reason!r}, "
            f"got {out.get('artifact_ref_nonqualifying_reason')!r}"
        )
    else:
        # Qualifying / fail-closed paths carry NO nonqualifying reason.
        assert "artifact_ref_nonqualifying_reason" not in out, (
            f"{case_id}: unexpected reason key on a qualifying/fail-closed path: "
            f"{out.get('artifact_ref_nonqualifying_reason')!r}"
        )

    # ── relay / capture side-effect ──────────────────────────────────────
    relay = out["capture"]["relay"]
    if expect_relay_sent:
        # Relay MUST have fired (the non-qualifying cases are captured, not
        # suppressed; the qualifying cases relay the stamped SHA).
        assert relay is not None, f"{case_id}: relay is None, expected sent"
        assert relay.get("sent") is True, (
            f"{case_id}: relay.sent is not True: {relay}"
        )
    else:
        # The fail-closed path (no SHA) suppresses relay entirely — no
        # envelope, no artifact_ref. This is the one case where capture does
        # NOT fire, and that is the correct behaviour.
        assert relay is None, (
            f"{case_id}: expected relay None on fail-closed path, got {relay}"
        )
        assert out["artifact_ref"] is None, (
            f"{case_id}: expected artifact_ref None on fail-closed path, "
            f"got {out['artifact_ref']!r}"
        )

    # ── caller-ref discard (cases 1, 7 are qualifying; case 6 fails closed) ──
    if expect_source == _QUALIFYING:
        assert out["artifact_ref"] is not None, f"{case_id}: qualifying but no ref"
        assert len(out["artifact_ref"]) == 40, (
            f"{case_id}: qualifying ref not a 40-char SHA: {out['artifact_ref']!r}"
        )
        assert out["artifact_ref"] != caller_ref, (
            f"{case_id}: caller ref survived into artifact_ref — forgeable path open"
        )
        assert out["artifact_ref"] == out["head_after"], (
            f"{case_id}: stamped ref != head_after"
        )
        # The relay envelope must carry the stamped SHA, never the caller's string.
        _msg, body = _relay_envelopes()[-1]
        assert body["artifact_refs"] == [out["artifact_ref"]], (
            f"{case_id}: envelope artifact_refs mismatch"
        )
        assert caller_ref not in json.dumps(body), (
            f"{case_id}: caller ref leaked into relay envelope body"
        )
    elif expect_source == _FAILED:
        # Fail-closed: the caller's string must not survive anywhere in the output.
        assert caller_ref not in json.dumps(out, default=str), (
            f"{case_id}: caller ref survived the fail-closed path"
        )


# ── 13. NORMALIZATION FAILURE → attribution_unprovable ────────────────────────
def test_normalization_failure_is_attribution_unprovable(tmp_path, monkeypatch):
    """v3.3 edge case: when the caller provides ``expect_paths`` AND HEAD moved
    AND ``commit_paths`` is non-empty, but EVERY path in ``changed_paths``
    fails ``_repo_relative_posix`` normalization (returns None), the
    intersection is vacuously empty. The cause is NOT a foreign commit — it is
    that the instrument could not map the dispatch's changed_paths into the
    repo's coordinate space (e.g. process cwd outside the repo, paths outside
    the repo root). The honest label is ``attribution_unprovable``, NOT
    ``head_moved_by_foreign_commit`` — we don't know whether the commit was
    foreign because we couldn't normalize the evidence to compare.

    This test forces ``_repo_relative_posix`` to return None for every path
    (simulating normalization failure) while keeping the real git helpers
    routed to the throwaway repo. The dispatch commits its own file (so HEAD
    genuinely moved and commit_paths is non-empty), and ``expect_paths`` is
    provided (so ``has_path_evidence`` is True). The intersection collapses
    to empty because normalization failed, and the reason must be
    ``attribution_unprovable``.
    """
    repo = _init_repo(tmp_path)
    head_before = _head_sha(repo)
    _route_git_to(monkeypatch, repo)
    # Force _repo_relative_posix to return None for every path — simulates
    # normalization failure (process cwd outside repo, paths outside repo root).
    monkeypatch.setattr(vd, "_repo_relative_posix", lambda p, cwd=None: None)
    monkeypatch.setattr(vd, "VendorCLIExecutor", _stub_executor_cls(repo, "commit_file"))

    # The stub's commit_file action writes vendor_work.txt; declare it as the
    # expected path so changed_paths is non-empty (has_path_evidence=True).
    # Normalization is forced to None, so the intersection collapses to empty.
    vendor_file = repo / "vendor_work.txt"

    out = vd.dispatch_and_capture(
        "agy", "build the thing", "ignored_caller_ref", to_role="peer",
        timeout_s=10, mode="write",
        expect_paths=[str(vendor_file)],
    )

    assert out["status"] == "ok", out
    # HEAD genuinely moved — the stub committed a real file.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    # The dispatch does NOT qualify: normalization failed for every path, so
    # the intersection is empty and the reason is attribution_unprovable.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "attribution_unprovable"
    assert out["capture"]["relay"].get("sent") is True
