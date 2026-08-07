"""``nucleus build --merge`` — sequences System A (build_runner) into System B (merge_gate).

Composes the two existing systems end-to-end: task prompt in, merged-and-audited
PR out. This is INTEGRATION via SEQUENCING and STEROIDING — no existing
functionality in either system is deleted, weakened, simplified, or removed.

SYSTEM A — ``build_runner.run_build_pipeline``:
    PLAN (dual-vendor adversarial plan review) → EXECUTE (cross-vendor build
    dispatch) → VERIFY (multi-tier check) → VERDICT card + exit code. Stops at
    the verdict — never creates a PR, never merges, never touches main.

SYSTEM B — merge_gate trust split (``scripts/merge_gate.py`` +
``scripts/merge_gate_authorize.py``):
    witness-signed, hash-chain-audited, trust-boundary-split autonomous merge.
    ``merge_gate_authorize.py`` does its OWN fresh GROUND verify + its OWN
    adversarial review dispatch + signs a witness + calls the gate.
    ``merge_gate_execute.sh`` mechanically executes the pre-verified merge
    steps. Then reconcile + verify-chain independently confirm the outcome.

THE GAP: System A gets you from a task prompt to a verified, verdict-passed
change sitting in a local git worktree — but then stops. System B gets a PR
from adversarial-review to a cryptographically-audited merge — but has no
path INTO it from a task prompt.

THE SHIM:
    After System A's VERDICT returns PASS, the shim:
      1. Commits the changed files on a fresh branch.
      2. Pushes the branch and opens a real PR (``gh pr create``).
      3. Hands the PR number to ``merge_gate_authorize.py authorize``.
      4. Threads System A's plan-review context into System B's diff-review
         prompt (STEROID 1) via the ``NUCLEUS_BUILD_PLAN_CONTEXT`` env var.
      5. Passes System A's verify receipt forward as audit evidence
         (STEROID 2) via the ``NUCLEUS_BUILD_VERIFY_RECEIPT_PATH`` env var.

    If the verdict is NOT a pass, the shim refuses before touching git/GitHub
    at all — no branch, no commit, no push, no PR.

The shim calls System A's individual stage functions (``_run_plan_stage``,
``_run_execute_stage``, ``_run_verify_stage``, ``_render_verdict_card``) so it
can capture the intermediate artifacts (``final_plan_path``, ``verify_details``)
that ``run_build_pipeline`` discards after printing the verdict card. System A's
behavior is byte-identical — the same stages run in the same order with the
same arguments.

The git/gh operations are factored into small helper functions
(``_create_branch``, ``_commit_changed_files``, ``_push_branch``,
``_create_pr``, ``_run_authorize``) so tests can monkeypatch each seam
independently without touching real git/GitHub.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# NOTE: System A's stage functions are imported LAZILY inside
# run_build_and_merge_pipeline, not at module level. This is deliberate:
# scripts/merge_gate.py (System B) evicts all mcp_server_nucleus.* entries
# from sys.modules at import time (a pre-existing import hack on lines
# 82-84 of that script). A module-level import here would hold stale
# references to the pre-eviction module object, so patch() in tests would
# patch a different module than the one these functions actually call.
# Lazy import ensures each call resolves from the current sys.modules.

logger = __import__("logging").getLogger("nucleus.build_and_merge")

# Default repo for the merge gate. Overridable via --repo on the CLI.
_DEFAULT_REPO = "eidetic-works/mcp-server-nucleus"


# ── Git / GitHub helpers (each is a monkeypatchable seam for tests) ───────────

def _create_branch(branch_name: str) -> bool:
    """Create and checkout a fresh branch from current HEAD. Returns True on
    success, False on failure. Refuses if the branch already exists."""
    try:
        subprocess.run(["git", "checkout", "-b", branch_name], check=True,
                       capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        # CalledProcessError = git exited non-zero (stderr on exc).
        # OSError (incl. FileNotFoundError) = git binary not installed / not
        # executable. Both are graceful failures, not crashes.
        detail = getattr(exc, "stderr", str(exc))
        print(f"[build_and_merge] git checkout -b failed: {detail}", file=sys.stderr)
        return False


def _commit_changed_files(changed_files: List[str], message: str) -> bool:
    """Stage and commit the given changed files. Returns True on success."""
    if not changed_files:
        print("[build_and_merge] no changed files to commit", file=sys.stderr)
        return False
    try:
        subprocess.run(["git", "add", "--"] + changed_files, check=True,
                       capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", message], check=True,
                       capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = getattr(exc, "stderr", str(exc))
        print(f"[build_and_merge] git commit failed: {detail}", file=sys.stderr)
        return False


def _push_branch(branch_name: str) -> bool:
    """Push the branch to origin. Returns True on success."""
    try:
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True,
                       capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = getattr(exc, "stderr", str(exc))
        print(f"[build_and_merge] git push failed: {detail}", file=sys.stderr)
        return False


def _create_pr(branch_name: str, title: str, body: str, base: str) -> Optional[int]:
    """Open a PR via ``gh pr create``. Returns the PR number on success, None
    on failure. Parses the PR number from gh's stdout URL."""
    try:
        result = subprocess.run(
            ["gh", "pr", "create", "--head", branch_name, "--base", base,
             "--title", title, "--body", body],
            check=True, capture_output=True, text=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        # CalledProcessError = gh exited non-zero (stderr on exc).
        # OSError (incl. FileNotFoundError) = gh binary not installed / not
        # executable. Both are graceful failures, not crashes.
        detail = getattr(exc, "stderr", str(exc))
        print(f"[build_and_merge] gh pr create failed: {detail}", file=sys.stderr)
        return None
    # gh pr create prints the PR URL to stdout, e.g.:
    #   https://github.com/owner/repo/pull/42
    out = result.stdout.strip()
    # Extract the trailing integer (the PR number) from the URL.
    import re
    m = re.search(r"/pull/(\d+)", out)
    if m:
        return int(m.group(1))
    print(f"[build_and_merge] could not parse PR number from gh output: {out!r}",
          file=sys.stderr)
    return None


def _check_gh_auth() -> bool:
    """Best-effort check that the ``gh`` CLI is installed and authenticated.
    Returns True on exit 0, False on non-zero exit / ``TimeoutExpired`` /
    ``OSError`` (incl. FileNotFoundError when gh is not installed). Never
    raises — safe to call as a preflight before any gh operation."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def _check_origin_reachable() -> bool:
    """Best-effort check that the ``origin`` git remote is reachable over the
    network. Runs ``git ls-remote --heads origin`` with a 5s timeout. Returns
    True on exit 0, False on non-zero exit / ``TimeoutExpired`` / ``OSError``
    (incl. FileNotFoundError when git is not installed, or network/auth
    failure reaching the remote). Never raises — safe to call as a preflight
    before any operation that needs to push or open a PR against origin."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def _auth_preflight() -> bool:
    """Orchestrate both auth/network preflight probes before any git/gh
    operation that needs them. Calls ``_check_gh_auth`` and
    ``_check_origin_reachable``; on either failure, prints the
    remediation command(s) to stderr and returns False. Returns True only
    when both pass. Never raises — both probes are exception-safe."""
    ok = True
    if not _check_gh_auth():
        print("[build_and_merge] gh CLI not authenticated — run: gh auth login",
              file=sys.stderr)
        ok = False
    if not _check_origin_reachable():
        print("[build_and_merge] origin remote not reachable — check network "
              "and that a remote is configured. Inspect with: git remote -v  "
              "| add one with: git remote add origin <url>",
              file=sys.stderr)
        ok = False
    return ok


def _run_authorize(pr_number: int, repo: str, review_vendor: str,
                   dry_run: bool) -> int:
    """Shell out to ``merge_gate_authorize.py authorize <PR>``. Returns the
    subprocess exit code. The NUCLEUS_BUILD_PLAN_CONTEXT and
    NUCLEUS_BUILD_VERIFY_RECEIPT_PATH env vars are inherited from this
    process (set by the caller before invoking this function)."""
    script = str(Path(__file__).resolve().parents[4] / "scripts" / "merge_gate_authorize.py")
    cmd = [sys.executable, script, "authorize", str(pr_number),
           "--repo", repo, "--review-vendor", review_vendor]
    if dry_run:
        cmd.append("--dry-run")
    print(f"[build_and_merge] dispatching: {' '.join(cmd)}", file=sys.stderr)
    return subprocess.call(cmd)


# ── Steroid payload builders ──────────────────────────────────────────────────

def _build_plan_context(task_prompt: str, final_plan_path: Path,
                        execution_mode: str) -> str:
    """STEROID 1: build the plan-context string that will be prepended to
    System B's diff-review prompt. Includes the original task prompt, the
    execution mode (dual-vendor adversarial vs single-vendor), and the
    approved plan text."""
    parts = [
        f"TASK PROMPT: {task_prompt}",
        f"EXECUTION MODE: {execution_mode}",
        "APPROVED PLAN:",
    ]
    try:
        plan_text = final_plan_path.read_text(encoding="utf-8").strip()
        parts.append(plan_text if plan_text else "(empty plan file)")
    except Exception as exc:  # noqa: BLE001
        parts.append(f"(could not read plan file: {exc})")
    return "\n".join(parts)


def _build_verify_receipt(task_prompt: str, verify_details: Dict[str, Any],
                          execution_mode: str) -> str:
    """STEROID 2: build the verify-receipt JSON that will be appended to
    System B's audit metadata. Captures System A's in-process verification
    outcome (tier statuses, changed files, summary) as supplementary
    evidence. This does NOT replace the gate's own fresh GROUND re-check."""
    receipt = {
        "source": "nucleus_build_verify_stage",
        "task_prompt": task_prompt,
        "execution_mode": execution_mode,
        "summary_status": verify_details.get("summary_status"),
        "passed_count": verify_details.get("passed_count"),
        "failed_count": verify_details.get("failed_count"),
        "skipped_count": verify_details.get("skipped_count"),
        "changed_files": verify_details.get("changed_files", []),
        "tier0": verify_details.get("tier0", {}),
        "tier1": verify_details.get("tier1", {}),
        "tier2": verify_details.get("tier2", {}),
        "tier3": verify_details.get("tier3", {}),
    }
    return json.dumps(receipt, indent=2, default=str)


def _cwd_origin_repo() -> Optional[str]:
    """Best-effort ``owner/name`` parsed from `git remote get-url origin` run
    in the current working directory. Returns None on any failure (not a git
    repo, no origin remote, git unavailable) — never raises."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
    except Exception:
        return None
    import re
    m = re.search(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


# ── Entry point ───────────────────────────────────────────────────────────────

def run_build_and_merge_pipeline(
    task_prompt: str,
    *,
    repo: str = _DEFAULT_REPO,
    review_vendor: str = "devin",
    base_branch: str = "main",
    dry_run: bool = False,
) -> int:
    """Run the full build-and-merge pipeline.

    Sequences System A (PLAN → EXECUTE → VERIFY → VERDICT) then, on a PASS
    verdict, commits → pushes → opens a PR → hands the PR to System B's
    ``merge_gate_authorize.py authorize``. On a non-PASS verdict, refuses
    before touching git/GitHub at all.

    Returns a process exit code (``0`` = success through the merge gate,
    non-zero = failure at any stage).
    """
    if not task_prompt or not task_prompt.strip():
        print("build --merge: empty task prompt", flush=True)
        return 2

    # fw-1785863543: --repo only ever targeted the merge gate's PR/merge
    # step — it never changed the build phase's working directory, so
    # `nucleus build --merge --repo other/repo "..."` silently built against
    # the CURRENT cwd's repo while the merge gate pointed at `other/repo`.
    # Making --repo actually switch directories is a bigger behavior change
    # than this shim should make unasked; the safe minimal fix is to warn
    # loudly the moment the mismatch is knowable, before any stage runs.
    cwd_repo = _cwd_origin_repo()
    if cwd_repo and repo and cwd_repo != repo:
        print(
            f"[build --merge] WARNING: --repo={repo!r} targets the merge "
            f"gate only. The build phase runs in the current working "
            f"directory, whose origin is {cwd_repo!r} — the build will "
            f"read/write files in {cwd_repo!r}, NOT {repo!r}. cd into the "
            f"target repo before running `nucleus build --merge` if that "
            f"is not what you want.",
            file=sys.stderr, flush=True,
        )

    # Auth/network preflight — refuse before any stage runs if gh CLI is not
    # authenticated or the origin remote is unreachable. Skipped entirely in
    # dry-run mode (no git/gh operations will be attempted anyway).
    if not dry_run:
        if not _auth_preflight():
            print("[build_and_merge] auth/network preflight failed — "
                  "see remediation above; aborting before build stages.",
                  file=sys.stderr, flush=True)
            return 2

    # Lazy import System A's stage functions (see module-level comment about
    # merge_gate.py's sys.modules eviction).
    from .build_runner import (
        _render_verdict_card,
        _run_execute_stage,
        _run_plan_stage,
        _run_verify_stage,
    )

    # ── SYSTEM A: PLAN → EXECUTE → VERIFY → VERDICT ────────────────────────
    # Call the individual stage functions so we can capture the intermediate
    # artifacts (final_plan_path, verify_details) that run_build_pipeline
    # discards after printing the verdict card. The stages run in the same
    # order with the same arguments — byte-identical behavior.
    ok, msg, final_plan_path, execution_mode = _run_plan_stage(task_prompt)
    if not ok or final_plan_path is None:
        print(f"build --merge: PLAN stage failed — {msg}", flush=True)
        return 1

    ok, msg, pre_head, post_head, results = _run_execute_stage(
        task_prompt, final_plan_path, execution_mode=execution_mode,
    )
    if not ok:
        print(f"build --merge: EXECUTE stage failed — {msg}", flush=True)
        return 1

    verification_passed, verify_details = _run_verify_stage(
        task_prompt, pre_head, post_head,
    )

    # Compute all_tasks_succeeded (same logic as _render_verdict_card).
    claimed = len(results)
    succeeded = sum(
        1 for r in results
        if r.get("result", {}).get("status") == "ok"
        and r.get("result", {}).get("produced_output") is True
    )
    all_tasks_succeeded = succeeded == claimed and claimed > 0
    verdict_pass = all_tasks_succeeded and verification_passed

    # Print the verdict card (same as run_build_pipeline does).
    rc = _render_verdict_card(
        task_prompt=task_prompt,
        final_plan_path=final_plan_path,
        pre_head=pre_head,
        post_head=post_head,
        results=results,
        verification_passed=verification_passed,
        verify_details=verify_details,
        execution_mode=execution_mode,
    )

    # ── REFUSE on non-PASS before touching git/GitHub ──────────────────────
    if not verdict_pass:
        print("[build_and_merge] VERDICT is not a PASS — refusing before "
              "touching git/GitHub. No branch, no commit, no push, no PR.",
              file=sys.stderr)
        return rc  # 1

    # ── SYSTEM A PASSED → commit, push, PR, hand to System B ───────────────
    # dry_run (fw-1785944533, fw-1785907050): skip ALL live git/gh effects —
    # no branch, no commit, no push, no PR, no merge gate. The verdict card
    # above already printed the result. Previously --dry-run only skipped the
    # merge_gate side, leaving build_runner to commit+push to local main,
    # creating test-artifact commits that had to be manually reset.
    if dry_run:
        print("[build_and_merge] VERDICT PASS — --dry-run set, skipping "
              "commit + push + PR + merge gate", file=sys.stderr)
        return rc  # 0

    print("[build_and_merge] VERDICT PASS — proceeding to commit + push + PR "
          "+ merge gate", file=sys.stderr)

    changed_files = verify_details.get("changed_files", [])
    branch_name = f"build-merge/{int(time.time())}"
    commit_msg = f"build --merge: {task_prompt[:72]}"
    pr_title = f"build --merge: {task_prompt[:72]}"
    pr_body = (
        f"## Summary\n\nAuto-generated by `nucleus build --merge` from task prompt:\n\n"
        f"> {task_prompt}\n\n"
        f"Execution mode: {execution_mode}\n\n"
        f"Verification: {verify_details.get('passed_count', 0)} PASSED, "
        f"{verify_details.get('failed_count', 0)} FAILED, "
        f"{verify_details.get('skipped_count', 0)} SKIPPED — "
        f"{verify_details.get('summary_status', 'UNKNOWN')}\n\n"
        f"Plan: `{final_plan_path}`\n"
    )

    if not _create_branch(branch_name):
        return 1
    if not _commit_changed_files(changed_files, commit_msg):
        return 1
    if not _push_branch(branch_name):
        return 1
    pr_number = _create_pr(branch_name, pr_title, pr_body, base_branch)
    if pr_number is None:
        return 1

    print(f"[build_and_merge] PR #{pr_number} opened on {repo}", file=sys.stderr)

    # ── STEROIDS: thread plan context + verify receipt into System B ──────
    # Write both to temp files and set env vars that merge_gate_authorize.py
    # reads (STEROID 1: NUCLEUS_BUILD_PLAN_CONTEXT prepended to review prompt;
    # STEROID 2: NUCLEUS_BUILD_VERIFY_RECEIPT_PATH forwarded to gate audit).
    plan_context = _build_plan_context(task_prompt, final_plan_path, execution_mode)
    verify_receipt = _build_verify_receipt(task_prompt, verify_details, execution_mode)

    tmpdir = tempfile.mkdtemp(prefix="build_and_merge_")
    plan_context_path = Path(tmpdir) / "plan_context.txt"
    verify_receipt_path = Path(tmpdir) / "verify_receipt.json"
    plan_context_path.write_text(plan_context, encoding="utf-8")
    verify_receipt_path.write_text(verify_receipt, encoding="utf-8")

    # Set env vars for the authorize subprocess. NUCLEUS_BUILD_PLAN_CONTEXT
    # is read directly by merge_gate_authorize.py's _dispatch_review.
    # NUCLEUS_BUILD_VERIFY_RECEIPT_PATH is forwarded by _run_gate to
    # merge_gate.py's --build-verify-receipt-path.
    os.environ["NUCLEUS_BUILD_PLAN_CONTEXT"] = plan_context
    os.environ["NUCLEUS_BUILD_VERIFY_RECEIPT_PATH"] = str(verify_receipt_path)

    # ── SYSTEM B: merge_gate_authorize.py authorize <PR> ───────────────────
    auth_rc = _run_authorize(pr_number, repo, review_vendor, dry_run)

    # Clean up env vars so they don't leak into subsequent calls in the
    # same process (e.g. test runs).
    os.environ.pop("NUCLEUS_BUILD_PLAN_CONTEXT", None)
    os.environ.pop("NUCLEUS_BUILD_VERIFY_RECEIPT_PATH", None)

    if auth_rc != 0:
        print(f"[build_and_merge] merge_gate_authorize exited {auth_rc} — "
              f"PR #{pr_number} was opened but the gate refused or failed. "
              f"The PR is still open on GitHub; investigate manually.",
              file=sys.stderr)
        return auth_rc

    print(f"[build_and_merge] merge gate authorized PR #{pr_number} — "
          f"executor + reconcile steps remain (run merge_gate_execute.sh + "
          f"merge_gate_authorize.py reconcile to complete the merge).",
          file=sys.stderr)
    return 0
