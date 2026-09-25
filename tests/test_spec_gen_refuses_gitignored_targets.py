"""The sweep must refuse git-ignored targets.

Why this exists: on 2026-08-20 the first code-side wave was pointed at
.brain/strategy/north_star/agent_integration/*.py. Every one of the 8 tasks
paused, and it looked like the vendors were bad at the task. They were not. The
target tree is covered by `.gitignore:94: .brain/*`, and the lane's entire
verification chain is built on git, so the wave was impossible by construction
in three places at once:

  1. `git status --porcelain` never reports ignored files, so the executor
     cannot see a vendor's edit, cannot attribute it, and cannot commit it.
  2. judge_clean requires >=3 git-TRACKED cited paths, so a CLEAN verdict about
     ignored code can never be corroborated -- tasks failed with "0 of 4 cited
     paths are git-tracked" regardless of audit quality.
  3. The commit scope gate only guards TRACKED files, so a vendor roaming an
     ignored tree can delete things unnoticed. It did: 11 relay files under
     .brain/relay/ were deleted during that wave and restored from HEAD.

None of it surfaced as an error. The generator happily emitted 8 tasks for work
that could not possibly be verified -- which is the same shape as everything
else this sweep has found, one layer up: a correct mechanism pointed at objects
it cannot operate on.
"""

import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SPEC_GEN = _REPO / "scripts" / "spec_gen.py"
_TARGET = _REPO / ".brain/strategy/north_star/agent_integration/receipt_gate.py"


def _require_target():
    """The guard can only be exercised where the ignored tree actually exists.

    `.brain/` is git-ignored, so a worktree checkout does not contain it. There
    the sweep reports "No files matched" and these tests fail for a reason that
    is not a defect -- the guard was never reached. That is INSUFFICIENT, not
    FAIL, and it must say so rather than read as a broken guard.
    """
    if not _TARGET.exists():
        pytest.skip(
            f"target tree absent at {_TARGET} -- .brain/ is git-ignored so a "
            "worktree checkout has no copy. The refusal guard cannot be "
            "exercised here; run this in the main checkout."
        )


def _run(glob: str):
    return subprocess.run(
        ["python3", str(_SPEC_GEN), "--glob", glob, "--template",
         "dead-instrument", "--dry-run"],
        capture_output=True, text=True, cwd=str(_REPO),
    )


def test_a_gitignored_target_is_refused():
    """THE BUG: the real tree that produced 8 impossible tasks."""
    _require_target()
    out = _run(".brain/strategy/north_star/agent_integration/*.py")
    combined = out.stdout + out.stderr
    assert "REFUSING" in combined, "git-ignored targets were accepted"
    assert "Nothing to generate" in combined


def test_the_refusal_names_the_files():
    """A silent drop is indistinguishable from the glob matching nothing --
    which is how this failed the first time."""
    _require_target()
    out = _run(".brain/strategy/north_star/agent_integration/*.py")
    assert "receipt_gate.py" in (out.stdout + out.stderr)


def test_a_tracked_target_still_generates():
    """OPPOSED, load-bearing: if this ever fails, the guard has stopped the
    sweep entirely rather than stopping the impossible part of it -- a cure
    strictly worse than the disease."""
    out = _run("mcp-server-nucleus/src/mcp_server_nucleus/runtime/lane/*.py")
    combined = out.stdout + out.stderr
    assert "REFUSING" not in combined
    assert "tasks from" in combined


def test_the_premise_holds_the_target_really_is_ignored():
    """CONTROL: if .brain/ stops being git-ignored, this whole guard is moot and
    should be revisited rather than left as cargo.

    Checks BOTH halves of the premise. `git check-ignore` answers a pattern
    question, not an existence one: it returns 0 for a path covered by
    .gitignore whether or not any such file is on disk. On its own it therefore
    passes in a worktree that contains no .brain/ at all -- so the control
    reported the premise holding while the two guard tests above failed because
    the target was missing. A control that cannot tell "ignored and present"
    from "ignored and absent" is not controlling the thing it names.
    """
    _require_target()
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(_TARGET.relative_to(_REPO))],
        cwd=str(_REPO),
    )
    assert r.returncode == 0, ".brain/ is no longer git-ignored -- revisit this guard"
