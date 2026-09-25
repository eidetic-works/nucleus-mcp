"""Agent OS — propose a safe first PR from a scanned task.

Sequences the existing safe-first-pr, explain-changes, and safe-gate modules
into a single CLI verb: scan, pick, verify, patch, and optionally create a
local branch + commit. All heavy lifting is delegated to the modules this
verb exposes; this module only wires them together and prints human-readable
output at each step.


Spec: ``.brain/strategy/BRIEFS/AGENT_OS_SAFE_FIRST_PR.md`` (Track S4 + this entrypoint).
That path is gitignored (``.gitignore`` ignores ``.brain/*`` with explicit
negations), so the brief is local-only by policy -- it is NOT missing from
the branch, and it is not recoverable from a fresh clone. If you are reading
this without it: the guardrails it sets are docs/examples only, deny by
default on path, one minimal test-result anchor, and NO automated push or
merge -- PR creation stays a human act.
"""

from __future__ import annotations

import difflib
import os
import secrets
import uuid
from pathlib import Path
from typing import List, Optional

from .explain_changes import emit_claims, snapshot, summarize, verify_claims
from .safe_first_pr import (
    apply_patch,
    create_branch_and_commit,
    is_safe_target,
    pr_description,
    propose_patch,
    scan_for_safe_tasks,
)
from .safe_gate import evaluate


def propose(
    repo_path: Optional[str] = None,
    apply: bool = False,
    task_index: int = 0,
    branch: Optional[str] = None,
) -> int:
    """Scan for a safe documentation fix, propose a patch, and verify it.

    Returns:
        0 -- no tasks, dry-run, or a safe change that was applied.
        1 -- the change was applied but the gate says it is not safe.
        2 -- the chosen task fails the safe-target gate.
    """
    # SCRATCH KEY: this is the only place a key may be minted. The witness
    # module itself refuses to sign without one, because a hardcoded fallback
    # would make every signature forgeable. The verb tells the operator when it
    # is using a throwaway key so the process is not mistaken for a witnessed
    # CI run.
    if not os.environ.get("NUCLEUS_WITNESS_SIGN_KEY"):
        os.environ["NUCLEUS_WITNESS_SIGN_KEY"] = secrets.token_hex(16)
        print(
            "witness: no NUCLEUS_WITNESS_SIGN_KEY in the environment; minted a "
            "scratch key for this run. Entries signed with it prove nothing "
            "beyond this process."
        )

    repo = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()

    # 1. scan
    tasks = scan_for_safe_tasks(repo)
    if not tasks:
        print("no safe tasks found")
        return 0

    # 2. pick
    try:
        task = tasks[task_index]
    except IndexError:
        print(f"task index {task_index} out of range (found {len(tasks)} tasks)")
        return 2

    print(f"task: {task.path} ({task.kind})")
    print(f"evidence: {task.evidence}")

    # 3. target gate
    allowed, path_reason = is_safe_target(task.path, repo)
    if not allowed:
        print(path_reason)
        return 2

    # 4. propose patch and show diff
    patch = propose_patch(repo, task)
    diff = list(
        difflib.unified_diff(
            patch.original_text.splitlines(),
            patch.patched_text.splitlines(),
            fromfile=f"a/{patch.path}",
            tofile=f"b/{patch.path}",
            lineterm="",
        )
    )
    print("--- proposed diff ---")
    print("\n".join(diff))

    # 5. dry run exit
    if not apply:
        print("dry run -- nothing written. Re-run with --apply.")
        return 0

    # 6-9. apply, branch, commit, snapshot, emit claims
    before = snapshot(repo)
    apply_patch(repo, patch)
    branch_name = branch or f"safe-pr/{task.kind}-{uuid.uuid4().hex[:8]}"
    new_sha = create_branch_and_commit(repo, patch, branch_name)
    after = snapshot(repo)

    modified: List[str] = []
    unanchorable: List[str] = []
    claims = emit_claims(before, after, modified=modified, unanchorable=unanchorable)

    # `emit_claims` emits a GIT BRANCH EXISTS claim for a brand-new branch, but
    # not a GIT COMMIT EXISTS claim (it only emits commits for branches that
    # existed in both snapshots with a changed tip). The commit is real and
    # created by `create_branch_and_commit`, so we add the claim explicitly so
    # the verdict and PR body can refer to it.
    claims.append(f"GIT COMMIT EXISTS: {new_sha} on branch {branch_name}")

    # 10-12. verify and evaluate
    verified = verify_claims(claims, repo_root=repo)
    verdict = evaluate(verified, path_allowed=True, path_reason=path_reason)

    # 13-15. summarize and report
    print(summarize(verified, unanchorable=unanchorable, modified=modified))
    print(verdict.explain())
    print(pr_description(patch, verified, verdict))

    return 0 if verdict.safe else 1
