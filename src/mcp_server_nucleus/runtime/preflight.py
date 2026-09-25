"""Assert what a check is pointed at, before believing what it reports.

Mining one week of this project's session transcripts measured the problem this
module exists for: 11.3% of success claims were retracted within five messages,
and 31% of a year's accumulated notes describe a single failure shape — a
correct check aimed at the wrong object. Examples from that week alone:

* a history rewrite reported success having run on an empty repository
* `git archive` dropped 12 of 363 files, exit 0, no message
* a bundle passed `git bundle verify` and could not be cloned
* a test suite ran on the wrong branch and reported 2,894 passes for a tree that
  no longer existed
* a reference checker flagged 100% of references and nearly produced a
  reassuring "no new breaks"

Every one was caught by a second look rather than by design. These assertions
are that design.

Two rules the module holds itself to:

1. **Every assertion names its object, on success as well as failure.** A green
   line reading `preflight: branch=main head=4f568e19 inputs=1701` is evidence.
   A green line reading `OK` is not.
2. **Nothing returns a bool.** A bool gets ignored; an unhandled exception exits
   non-zero. Failure is the loud path.

Usable from Python or from shell:

    from mcp_server_nucleus.runtime.preflight import assert_branch, assert_non_empty
    python3 -m mcp_server_nucleus.runtime.preflight --repo . --branch main
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Collection, Sequence
from pathlib import Path


class PreflightError(RuntimeError):
    """A check was about to run against something other than what was claimed."""


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise PreflightError(f"git {' '.join(args)} failed in {repo}: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def assert_repo_root(marker: str = ".brain", start: Path | None = None) -> Path:
    """Nearest ancestor holding `marker`. Raises naming every directory tried."""
    here = (start or Path.cwd()).resolve()
    tried: list[Path] = []
    for candidate in (here, *here.parents):
        tried.append(candidate)
        if (candidate / marker).exists():
            print(f"preflight: repo_root={candidate} (marker {marker})")
            return candidate
    raise PreflightError(
        f"no ancestor of {here} contains {marker}. Looked in: "
        + ", ".join(str(p) for p in tried[:8])
    )


def assert_branch(expected: str, repo: Path | None = None) -> str:
    """The suite that reported 2,894 passes was on a branch nobody had named."""
    repo = (repo or Path.cwd()).resolve()
    actual = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if actual == "HEAD":
        raise PreflightError(
            f"{repo} is in detached HEAD; expected branch {expected!r}. "
            "A detached checkout is not the branch you think you are testing."
        )
    if actual != expected:
        raise PreflightError(f"{repo} is on branch {actual!r}, expected {expected!r}")
    print(f"preflight: branch={actual} repo={repo}")
    return actual


def assert_commit(expected_sha: str, repo: Path | None = None) -> str:
    repo = (repo or Path.cwd()).resolve()
    if not expected_sha or len(expected_sha) < 7:
        raise PreflightError(
            f"expected_sha={expected_sha!r} is too short to identify a commit "
            "(7 characters minimum); an empty pin silently matches nothing"
        )
    actual = _git(repo, "rev-parse", "HEAD")
    if not actual.startswith(expected_sha):
        raise PreflightError(
            f"{repo} is at {actual[:12]}, expected {expected_sha[:12]}. "
            "Results from a different commit are not the results you asked for."
        )
    print(f"preflight: commit={actual[:12]} repo={repo}")
    return actual


def assert_clean_worktree(repo: Path | None = None) -> None:
    repo = (repo or Path.cwd()).resolve()
    dirty = [ln for ln in _git(repo, "status", "--porcelain").splitlines() if ln.strip()]
    if dirty:
        raise PreflightError(
            f"{repo} has {len(dirty)} uncommitted change(s); an artifact built from "
            f"it is not reproducible. First: {dirty[0][:80]}"
        )
    print(f"preflight: worktree=clean repo={repo}")


def assert_non_empty(label: str, items: Collection, minimum: int = 1) -> Collection:
    """An empty input set is a failure, never a pass.

    This is the filter-repo-on-an-empty-repo case: the tool exited 0 having done
    nothing, and the exit code was believed.
    """
    n = len(items)
    if n < minimum:
        raise PreflightError(
            f"{label}: {n} item(s), expected at least {minimum}. "
            "A check over an empty set cannot fail, so its pass means nothing."
        )
    print(f"preflight: {label}={n}")
    return items


def assert_count_preserved(label: str, before: Collection, after: Collection,
                           explained: Collection = (), sample: int = 10) -> None:
    """Compare SETS, not counts, so a mismatch can name what went missing.

    Counts are what let `git archive` lose 12 of 363 files quietly; names are
    what make it impossible.
    """
    b, a, e = set(before), set(after), set(explained)
    missing = b - a - e
    added = a - b
    if missing or added:
        parts = [f"{label}: {len(b)} before, {len(a)} after"]
        if e:
            parts.append(f"{len(e)} explained")
        if missing:
            shown = sorted(str(m) for m in missing)[:sample]
            parts.append(f"MISSING {len(missing)}: " + ", ".join(shown)
                         + ("…" if len(missing) > sample else ""))
        if added:
            shown = sorted(str(x) for x in added)[:sample]
            parts.append(f"UNEXPECTED {len(added)}: " + ", ".join(shown))
        raise PreflightError(" | ".join(parts))
    print(f"preflight: {label} preserved ({len(b)} items"
          + (f", {len(e)} explained" if e else "") + ")")


def require_can_fail(name: str, probe, planted) -> None:
    """A gate is unproven until a known-bad input makes it say so.

    `probe(planted)` must return False (or raise) for the planted input. If it
    returns a pass, the gate cannot fail and every green reading from it is
    uninformative.
    """
    try:
        verdict = probe(planted)
    except Exception:
        print(f"preflight: control {name!r} rejected the planted input (raised)")
        return
    if verdict:
        raise PreflightError(
            f"control {name!r} PASSED a deliberately broken input, so it cannot "
            "fail — every green reading from it is uninformative"
        )
    print(f"preflight: control {name!r} rejected the planted input")


def banner(repo: Path | None = None, inputs: Sequence | None = None) -> None:
    """One line saying what this run is pointed at. Cheap, and it ends arguments."""
    repo = (repo or Path.cwd()).resolve()
    try:
        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        head = _git(repo, "rev-parse", "--short", "HEAD")
        tracked = len(_git(repo, "ls-files").splitlines())
    except PreflightError:
        branch, head, tracked = "?", "?", 0
    extra = f" inputs={len(inputs)}" if inputs is not None else ""
    print(f"preflight: repo={repo} branch={branch} head={head} tracked={tracked}{extra}")


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="assert what this run is pointed at")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--branch")
    ap.add_argument("--commit")
    ap.add_argument("--clean", action="store_true", help="require a clean worktree")
    ap.add_argument("--banner", action="store_true")
    args = ap.parse_args(argv[1:])
    repo = Path(args.repo).resolve()
    try:
        if args.banner or not (args.branch or args.commit or args.clean):
            banner(repo)
        if args.branch:
            assert_branch(args.branch, repo)
        if args.commit:
            assert_commit(args.commit, repo)
        if args.clean:
            assert_clean_worktree(repo)
    except PreflightError as e:
        print(f"PREFLIGHT FAILED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
