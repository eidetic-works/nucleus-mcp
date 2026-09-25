"""Explain verified repo changes after AI runs.

Tracks E1+E2 of AGENT_OS_EXPLAIN_AI_CHANGES.md: snapshot a git repo and
emit deterministic claim strings the verifier can parse.

Tracks E3+E4: route each claim through the verifier and build a
plain-English summary that only states confirmed facts, while still
surfacing refuted/unverifiable claims and unanchorable paths.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..verifier import Claim, ProbeEngine, RuleReasoner


def _run_git(argv: List[str], cwd: Union[str, Path]) -> subprocess.CompletedProcess[str]:
    """Run a git command with a list argv and capture output."""
    return subprocess.run(
        ["git", *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _git_output_or_raise(argv: List[str], cwd: Union[str, Path]) -> str:
    """Run a git command and raise an explicit error on failure."""
    result = _run_git(argv, cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(argv)} failed in {cwd} "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def snapshot(repo_root: Union[str, Path]) -> Dict[str, Any]:
    """Capture a JSON-serialisable snapshot of the repo.

    Uses git subprocesses (not filesystem walks) so .gitignore is respected.
    """
    repo = Path(repo_root).resolve()
    if not repo.is_dir():
        raise RuntimeError(f"repo_root is not a directory: {repo}")

    branch = _git_output_or_raise(["rev-parse", "--abbrev-ref", "HEAD"], repo).strip()
    head_sha = _git_output_or_raise(["rev-parse", "HEAD"], repo).strip()

    tracked: Dict[str, str] = {}
    ls = _git_output_or_raise(["ls-files", "-s"], repo)
    for line in ls.splitlines():
        if "\t" not in line:
            continue
        info, path = line.split("\t", 1)
        parts = info.strip().split()
        if len(parts) < 3:
            continue
        if parts[2] != "0":
            continue
        tracked[path] = parts[1]

    branches: Dict[str, str] = {}
    refs = _git_output_or_raise(
        ["for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads"],
        repo,
    )
    for line in refs.splitlines():
        if " " not in line:
            continue
        name, sha = line.split(" ", 1)
        branches[name] = sha.strip()

    return {
        "repo_root": str(repo),
        "branch": branch,
        "head_sha": head_sha,
        "tracked": tracked,
        "branches": branches,
    }


def save_snapshot(snap: Dict[str, Any], path: Union[str, Path]) -> None:
    """Persist a snapshot to disk as JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snap, indent=2, sort_keys=True), encoding="utf-8")


def load_snapshot(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a snapshot from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _new_commits_on_branch(
    repo: Path, before_sha: str, after_sha: str
) -> List[str]:
    """Return full SHAs of commits between two branch tips.

    Raises RuntimeError if git commands fail. Returns an empty list if
    before_sha is not an ancestor of after_sha (e.g. a reset or diverge),
    because we cannot substantiate individual new commits in that case.
    """
    if before_sha == after_sha:
        return []

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", before_sha, after_sha],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        return []

    rev_list = subprocess.run(
        ["git", "rev-list", f"{before_sha}..{after_sha}"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if rev_list.returncode != 0:
        raise RuntimeError(
            f"git rev-list {before_sha}..{after_sha} failed: {rev_list.stderr.strip()}"
        )
    return [sha for sha in rev_list.stdout.splitlines() if sha]


# The verifier's FILE-EXISTS detector only recognises paths carrying one of a
# fixed set of extensions (verifier.py, the fs-anchor path regex). Measured:
# "FILE EXISTS: src/foo.py" yields 1 fs anchor; "FILE EXISTS: Makefile",
# "LICENSE" and "Dockerfile" each yield 0. Such a claim parses as a sentence but
# anchors to nothing, so it can never be CONFIRMED -- it lands as UNVERIFIABLE
# while LOOKING like a verified statement in a summary. Emitting one would be
# manufacturing an unanchorable claim, which the brief forbids.
def is_anchorable_path(path: str) -> bool:
    """True when a FILE EXISTS claim for ``path`` can actually reach an anchor.

    Asks the verifier rather than keeping a suffix allowlist beside it. An
    allowlist can only contain what someone already thought of: the previous one
    omitted Makefile, LICENSE, Dockerfile, .gitignore and every extensionless
    path, so real additions were silently reported as unclaimable.

    But "the verifier produced an fs anchor" is NOT sufficient on its own. The
    FILE EXISTS regex takes the first whitespace-delimited token, so
    "FILE EXISTS: a b.py" anchors the path ``a`` -- which does not exist, and the
    claim REFUTES even though ``a b.py`` is right there on disk. A path is only
    anchorable when the anchor the verifier derives is the SAME path we asked
    about; anything that truncates is worse than unanchored, because it fails
    with a confident wrong answer instead of an honest one.
    """
    if not path or path.strip() != path:
        return False
    from ..verifier import Claim, RuleReasoner

    anchors = RuleReasoner().decompose(Claim("c", "p", "a", f"FILE EXISTS: {path}"))
    return any(
        a.kind == "fs" and (a.spec or {}).get("path") == path for a in anchors
    )


def emit_claims(
    before: Dict[str, Any],
    after: Dict[str, Any],
    run_id: Optional[str] = None,
    unanchorable: Optional[List[str]] = None,
    modified: Optional[List[str]] = None,
) -> List[str]:
    """Diff two snapshots and emit verifier-parseable claim strings.

    Added files whose path cannot reach an fs anchor are NOT claimed. Pass a
    list as ``unanchorable`` to collect them: they are a real part of the diff
    and the caller should say "also changed, not verifiable here" rather than
    let them vanish. A silent skip is how a summary comes to imply it covered
    everything when it did not.
    """
    claims: List[str] = []

    before_files = before.get("tracked", {})
    after_files = after.get("tracked", {})
    for path in sorted(set(after_files) - set(before_files)):
        if is_anchorable_path(path):
            claims.append(f"FILE EXISTS: {path}")
        elif unanchorable is not None:
            unanchorable.append(path)

    # MODIFIED files (same path, different blob) get no claim of their own.
    # "FILE EXISTS: x" proves x exists -- it says nothing about x having
    # CHANGED, so claiming it here would anchor to the wrong fact and report
    # CONFIRMED for a question never asked.
    #
    # They must still be reported. Found by dogfooding this module on its own
    # commit: that commit modified two files and added none, so emit_claims
    # returned [] and summarize() said "Nothing was confirmed as changed. No
    # changes were found to verify." -- a confident summary of nothing,
    # indistinguishable from a genuinely clean diff. That is exactly the
    # failure this brief exists to prevent, produced by the brief's own tool.
    if modified is not None:
        for path in sorted(set(after_files) & set(before_files)):
            if before_files[path] != after_files[path]:
                modified.append(path)

    before_branches = before.get("branches", {})
    after_branches = after.get("branches", {})

    for name in sorted(set(after_branches) - set(before_branches)):
        claims.append(f"GIT BRANCH EXISTS: {name}")

    repo_root = after.get("repo_root") or before.get("repo_root")
    repo = Path(repo_root) if repo_root else None

    for name in sorted(set(after_branches) & set(before_branches)):
        before_sha = before_branches[name]
        after_sha = after_branches[name]
        if before_sha != after_sha and repo and repo.is_dir():
            for sha in _new_commits_on_branch(repo, before_sha, after_sha):
                claims.append(f"GIT COMMIT EXISTS: {sha} on branch {name}")

    if run_id:
        claims.append(f"TESTS PASSED: {run_id}")

    return claims


def _plain_change_description(claim: str) -> str:
    """Convert a verifier claim string into plain-English, no git jargon."""
    m = re.match(r"^FILE\s+EXISTS\s*:\s*(.+)$", claim, re.IGNORECASE)
    if m:
        return f"the file {m.group(1).strip()}"

    m = re.match(r"^GIT\s+BRANCH\s+EXISTS\s*:\s*(.+)$", claim, re.IGNORECASE)
    if m:
        return f"the branch {m.group(1).strip()}"

    m = re.match(
        r"^GIT\s+COMMIT\s+EXISTS\s*:\s*([0-9a-fA-F]+)(?:\s+on\s+branch\s+(.+))?$",
        claim,
        re.IGNORECASE,
    )
    if m:
        branch = (m.group(2) or "").strip()
        if branch:
            return f"a commit on branch {branch}"
        return "a commit"

    m = re.match(r"^TESTS\s+PASSED\s*:\s*(.+)$", claim, re.IGNORECASE)
    if m:
        return f"tests passed for run {m.group(1).strip()}"

    return claim


def verify_claims(claims: List[str], repo_root: Optional[Union[str, Path]] = None) -> Dict[str, List[str]]:
    """Route each claim string through the existing verifier.

    Returns ``{"confirmed": [...], "refuted": [...], "unverifiable": [...]}``
    keyed by ``verdict.status``. Any verdict status other than CONFIRMED or
    REFUTED is bucketed as ``unverifiable`` so nothing is silently dropped.
    """
    reasoner = RuleReasoner()
    probe = ProbeEngine(default_repo=str(repo_root) if repo_root else None)

    result: Dict[str, List[str]] = {"confirmed": [], "refuted": [], "unverifiable": []}
    for idx, text in enumerate(claims):
        claim = Claim(f"claim-{idx}", "pipeline", "agent", text)
        anchors = reasoner.decompose(claim)
        evidence = [probe.run_anchor(a) for a in anchors]
        reasoner._anchor_index = {a.anchor_id: a for a in anchors}
        verdict = reasoner.adjudicate(claim, evidence, anchors=anchors)

        if verdict.status == "CONFIRMED":
            result["confirmed"].append(text)
        elif verdict.status == "REFUTED":
            result["refuted"].append(text)
        else:
            result["unverifiable"].append(text)

    return result


def summarize(
    verified: Dict[str, List[str]],
    unanchorable: Optional[List[str]] = None,
    modified: Optional[List[str]] = None,
) -> str:
    """Plain-English summary of verified changes.

    Only confirmed claims are stated as facts. Refuted and unverifiable claims
    are still surfaced by count and labelled as not verified. Unanchorable
    paths (changed but unclaimable) are mentioned separately. If nothing was
    confirmed, the summary says so plainly.
    """
    confirmed = verified.get("confirmed") or []
    refuted = verified.get("refuted") or []
    unverifiable = verified.get("unverifiable") or []
    unanchorable = unanchorable or []

    not_verified_count = len(refuted) + len(unverifiable)
    parts: List[str] = []

    if confirmed:
        if len(confirmed) == 1:
            parts.append(f"Verified 1 change: {_plain_change_description(confirmed[0])}.")
        else:
            descriptions = ", ".join(_plain_change_description(c) for c in confirmed)
            parts.append(f"Verified {len(confirmed)} changes: {descriptions}.")
    else:
        parts.append("Nothing was confirmed as changed.")

    # Modified files are reported but NOT claimed: existence does not prove
    # change, so there is no anchor that could confirm them here. Saying
    # nothing about them is what made this tool report "no changes" over a
    # two-file diff.
    if modified:
        listed = ", ".join(sorted(modified))
        parts.append(
            f"{len(modified)} existing file(s) were modified ({listed}) -- "
            f"changed, but not verifiable as a change by file-existence alone."
        )

    if not_verified_count:
        qualifier = "other " if confirmed else ""
        were = "were" if not_verified_count > 1 else "was"
        are = "are" if not_verified_count > 1 else "is"
        parts.append(
            f"{not_verified_count} {qualifier}claim{'s' if not_verified_count > 1 else ''} "
            f"{were} not verified and {are} not stated as facts."
        )

    if unanchorable:
        parts.append(f"Also changed, not verifiable here: {', '.join(unanchorable)}.")

    if not confirmed and not not_verified_count and not unanchorable:
        parts.append("No changes were found to verify." if not modified else "")

    return " ".join(parts)
