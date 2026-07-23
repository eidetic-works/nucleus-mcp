"""``nucleus build`` pipeline — chains plan review loop → vendor execution → verification.

Dogfood-v0 build verb. Composes existing engines as libraries:

  * PLAN    — ``execute_plan_review_loop`` (async; poll ``state.json``)
  * EXECUTE — ``dispatch_and_capture("devin", ...)`` per parsed task checkbox
  * VERIFY  — ``execution_verifier`` multi-tier checks (syntax / import / tests)
  * VERDICT — printed verdict card + exit code

This module is packaging-only — no new subsystems, no env-flag flips,
stdlib + existing runtime imports only.

The entry point :func:`run_build_pipeline` returns a process exit code
(``0`` = success, non-zero = failure/abort), matching the CLI verb contract.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .vendor_dispatch import cross_vendor_enabled, dispatch_and_capture

logger = logging.getLogger("nucleus.build_runner")

# ── Polling constants ────────────────────────────────────────────────────────
_PLAN_POLL_INTERVAL_S = 2
_PLAN_POLL_TIMEOUT_S = 600

# Statuses that abort the build (anything other than APPROVED).
_ABORT_STATUSES = frozenset({
    "CONVERGED_WITH_MINOR_ISSUES",
    "MAX_ROUNDS_EXHAUSTED",
    "BUDGET_EXCEEDED",
    "CANCELLED",
    "ERROR",
    "OSCILLATING",
})

# ── Small state helpers ──────────────────────────────────────────────────────

def _make_response(success: bool, data: Optional[dict] = None,
                   error: Optional[str] = None) -> str:
    """JSON response formatter closure (matches plan_review_loop contract)."""
    return json.dumps({"success": success, "data": data, "error": error})


def _git_head() -> str:
    """Current HEAD commit SHA (40 chars) via ``git rev-parse HEAD``."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception as exc:  # noqa: BLE001 — best-effort; caller aborts on empty
        logger.warning("git rev-parse HEAD failed: %s", exc)
        return ""


def _brain_path() -> Path:
    """Resolve the ``.brain`` directory (lazy core import to stay stdlib-clean)."""
    from .common import get_brain_path
    brain = get_brain_path()
    if brain is None:
        brain = Path.cwd() / ".brain"
    return Path(brain)


def _read_state(plan_id: str) -> Dict[str, Any]:
    """Read ``.brain/plans/<plan_id>/state.json``; returns ``{}`` on miss/error."""
    path = _brain_path() / "plans" / plan_id / "state.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("state.json read failed for %s: %s", plan_id, exc)
        return {}


def _resolve_final_plan_path(plan_id: str, state: Dict[str, Any]) -> Optional[Path]:
    """Resolve the approved plan markdown path.

    Preference: ``state["final_plan_path"]``; fallback
    ``.brain/plans/<plan_id>/final_plan.md``. Returns ``None`` if the file
    does not exist on disk.
    """
    candidate = state.get("final_plan_path") or f".brain/plans/{plan_id}/final_plan.md"
    p = Path(candidate)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p if p.exists() else None


def _parse_task_checkboxes(final_plan_path: Path) -> List[Tuple[int, str]]:
    """Parse ``- [ ] Task N: <desc>`` lines from the approved plan.

    Returns a list of ``(task_number, description)`` tuples in document order.
    Only unchecked tasks (``- [ ]``) are returned — checked tasks are skipped
    (treated as already done).
    """
    tasks: List[Tuple[int, str]] = []
    pattern = re.compile(r"^\s*-\s*\[\s*\]\s*Task\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE)
    try:
        text = final_plan_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("final plan read failed (%s): %s", final_plan_path, exc)
        return tasks
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            tasks.append((int(m.group(1)), m.group(2).strip()))
    return tasks


# ── PLAN stage ───────────────────────────────────────────────────────────────

def _run_plan_stage(task_prompt: str) -> Tuple[bool, str, Optional[Path]]:
    """Run the plan review loop and poll until APPROVED.

    Returns ``(ok, message, final_plan_path)``. On failure *ok* is ``False``,
    *message* describes the abort reason, and *final_plan_path* is ``None``.
    """
    # Lazy import to avoid eager import of the tools package at module load.
    from ..tools.plan_review_loop import execute_plan_review_loop

    params = {"prompt": task_prompt}
    raw = execute_plan_review_loop(params, _make_response)
    try:
        res = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return False, f"plan_review_loop returned non-JSON: {exc}", None

    if not res.get("success") or res.get("error"):
        return False, f"plan_review_loop failed: {res.get('error') or res}", None

    data = res.get("data") or {}
    plan_id = data.get("plan_id")
    if not plan_id:
        # sync mode returns final state directly — treat as already terminal
        status = data.get("status")
        if status == "APPROVED":
            fp = _resolve_final_plan_path(data.get("plan_id", ""), data)
            if fp is None:
                return False, "APPROVED but final_plan_path missing on disk", None
            return True, "APPROVED", fp
        return False, f"plan_review_loop returned no plan_id (status={status})", None

    # Poll state.json until APPROVED or an abort status fires.
    deadline = time.monotonic() + _PLAN_POLL_TIMEOUT_S
    last_status: Optional[str] = None
    while time.monotonic() < deadline:
        state = _read_state(plan_id)
        status = state.get("status")
        if status and status != last_status:
            logger.info("plan %s status: %s", plan_id, status)
            last_status = status
        if status == "APPROVED":
            fp = _resolve_final_plan_path(plan_id, state)
            if fp is None:
                return False, "APPROVED but final_plan_path missing on disk", None
            return True, "APPROVED", fp
        if status in _ABORT_STATUSES:
            return False, f"plan review aborted: status={status}", None
        time.sleep(_PLAN_POLL_INTERVAL_S)

    return False, f"plan review timed out after {_PLAN_POLL_TIMEOUT_S}s (last={last_status})", None


# ── EXECUTE stage ────────────────────────────────────────────────────────────

def _run_execute_stage(task_prompt: str, final_plan_path: Path) -> Tuple[bool, str, str, str, List[Dict[str, Any]]]:
    """Dispatch each parsed task checkbox to devin (write mode), fail-stop.

    Returns ``(ok, message, pre_head, post_head, dispatch_results)``.
    *pre_head* is captured before the first dispatch; *post_head* after the
    last. On fail-stop *post_head* equals *pre_head* (no further dispatch ran).
    """
    if not cross_vendor_enabled():
        return False, "cross-vendor dispatch is disabled (run `nucleus onboard`)", "", "", []

    pre_head = _git_head()
    if not pre_head:
        return False, "could not record pre_head (git rev-parse HEAD failed)", "", "", []

    tasks = _parse_task_checkboxes(final_plan_path)
    if not tasks:
        return False, f"no unchecked Task N: checkboxes found in {final_plan_path}", pre_head, pre_head, []

    results: List[Dict[str, Any]] = []
    for task_num, task_desc in tasks:
        logger.info("dispatching task %d: %s", task_num, task_desc)
        res = dispatch_and_capture(
            "devin", task_desc,
            artifact_ref=str(final_plan_path),
            mode="write",
        )
        results.append({"task_num": task_num, "task_desc": task_desc, "result": res})
        # Fail-stop predicate: status == "ok" AND produced_output is True.
        if not (res.get("status") == "ok" and res.get("produced_output") is True):
            return (
                False,
                f"fail-stop at task {task_num}: status={res.get('status')!r} "
                f"produced_output={res.get('produced_output')!r}",
                pre_head,
                pre_head,
                results,
            )

    post_head = _git_head()
    return True, f"executed {len(tasks)} task(s)", pre_head, post_head, results


# ── VERIFY stage ─────────────────────────────────────────────────────────────

def _run_verify_stage(task_prompt: str, pre_head: str, post_head: str) -> Tuple[bool, Dict[str, Any]]:
    """VERIFY stage — multi-tier verification of changed files.

    Derives the changed-file set via ``execution_verifier._get_changed_files``
    (passing ``""`` as the first positional arg — the function ignores it and
    queries git state directly). Empty ``changed_files`` is a tier-0 FAILURE
    (nothing provably changed → ``verification_passed = False``); all tiers
    reported as SKIPPED. Otherwise runs tier-1 syntax, tier-2 import, and
    tier-3 test checks, aggregating each returned ``list[dict]`` signal list
    via ``all(r.get("passed", False) for r in results)``. An empty tier-2 or
    tier-3 signal list is reported as SKIPPED (never silently counted as a
    pass, never failing the gate on its own).

    Returns ``(verification_passed, details)`` where *details* carries per-tier
    status strings (PASSED/FAILED/SKIPPED), raw signals, and the changed-file
    list.
    """
    # Lazy import — keeps module load stdlib-clean.
    from . import execution_verifier

    project_root = Path.cwd()
    changed_files = execution_verifier._get_changed_files("", pre_head, project_root)

    details: Dict[str, Any] = {
        "changed_files": changed_files,
        "tier1": {"status": "SKIPPED", "signals": []},
        "tier2": {"status": "SKIPPED", "signals": []},
        "tier3": {"status": "SKIPPED", "signals": []},
    }

    if not changed_files:
        # Tier-0 failure: nothing provably changed.
        details["tier0"] = {"status": "FAILED", "reason": "no changed files"}
        return False, details
    details["tier0"] = {"status": "PASSED", "files_count": len(changed_files)}

    # ── Tier 1: syntax check ────────────────────────────────────────────────
    tier1_results = execution_verifier._tier1_syntax_check(
        changed_files, project_root, budget_s=30.0,
    )
    tier1_passed = bool(tier1_results) and all(
        r.get("passed", False) for r in tier1_results
    )
    details["tier1"] = {
        "status": "PASSED" if tier1_passed else "FAILED",
        "signals": tier1_results,
    }

    # ── Tier 2: import check (only .py files) ───────────────────────────────
    py_files = [f for f in changed_files if f.endswith(".py")]
    if not py_files:
        # No Python files → SKIPPED (passes the gate, reported as such).
        tier2_passed = True
        details["tier2"] = {"status": "SKIPPED", "signals": [], "reason": "no .py files"}
    else:
        tier2_results = execution_verifier._tier2_import_check(
            py_files, project_root, budget_s=30.0,
        )
        if not tier2_results:
            # Empty signal list (e.g. all candidates filtered) → SKIPPED.
            tier2_passed = True
            details["tier2"] = {
                "status": "SKIPPED", "signals": tier2_results,
                "reason": "no importable candidates after filtering",
            }
        else:
            tier2_passed = all(r.get("passed", False) for r in tier2_results)
            details["tier2"] = {
                "status": "PASSED" if tier2_passed else "FAILED",
                "signals": tier2_results,
            }

    # ── Tier 3: test execution ──────────────────────────────────────────────
    tier3_results = execution_verifier._tier3_test_execution(
        changed_files, {"description": task_prompt}, project_root, budget_s=120.0,
    )
    if not tier3_results:
        # No test files discovered → SKIPPED (passes the gate, reported as such).
        tier3_passed = True
        details["tier3"] = {
            "status": "SKIPPED", "signals": tier3_results,
            "reason": "no test files discovered",
        }
    else:
        tier3_passed = all(r.get("passed", False) for r in tier3_results)
        details["tier3"] = {
            "status": "PASSED" if tier3_passed else "FAILED",
            "signals": tier3_results,
        }

    verification_passed = tier1_passed and tier2_passed and tier3_passed
    return verification_passed, details


# ── VERDICT stage ────────────────────────────────────────────────────────────

def _render_verdict_card(
    *,
    task_prompt: str,
    final_plan_path: Path,
    pre_head: str,
    post_head: str,
    results: List[Dict[str, Any]],
    verification_passed: bool,
    verify_details: Dict[str, Any],
) -> int:
    """VERDICT stage — format + print the verdict card, return exit code.

    Card sections: CLAIMED (tasks parsed), PROVEN (tasks passing the fail-stop
    predicate), PROVENANCE (pre/post HEAD SHAs), CHANGED FILES, and per-tier
    VERIFICATION STATUS (SKIPPED rendered explicitly — a skip is never shown
    as a pass). Returns ``0`` iff every task succeeded AND
    ``verification_passed`` is ``True``; otherwise ``1``.
    """
    claimed = len(results)
    proven = sum(
        1 for r in results
        if r.get("result", {}).get("status") == "ok"
        and r.get("result", {}).get("produced_output") is True
    )
    all_tasks_succeeded = proven == claimed and claimed > 0

    changed_files = verify_details.get("changed_files", [])
    tier0 = verify_details.get("tier0", {})
    tier1 = verify_details.get("tier1", {})
    tier2 = verify_details.get("tier2", {})
    tier3 = verify_details.get("tier3", {})

    print("─" * 72, flush=True)
    print("  NUCLEUS BUILD — VERDICT CARD", flush=True)
    print("─" * 72, flush=True)
    print(f"  TASK PROMPT : {task_prompt}", flush=True)
    print(f"  PLAN        : {final_plan_path}", flush=True)
    print(f"  CLAIMED     : {claimed} task(s) parsed from plan", flush=True)
    print(f"  PROVEN      : {proven}/{claimed} task(s) passed fail-stop predicate", flush=True)
    print(f"  PROVENANCE  : pre_head={pre_head or '(unknown)'}", flush=True)
    print(f"                post_head={post_head or '(unknown)'}", flush=True)
    print(f"  CHANGED FILES ({len(changed_files)}):", flush=True)
    if changed_files:
        for f in changed_files:
            print(f"    - {f}", flush=True)
    else:
        print("    (none)", flush=True)
    print("  VERIFICATION STATUS:", flush=True)
    print(f"    Tier 0 (diff nonempty) : {tier0.get('status', 'SKIPPED')}", flush=True)
    print(f"    Tier 1 (syntax)        : {tier1.get('status', 'SKIPPED')}", flush=True)
    print(f"    Tier 2 (imports)       : {tier2.get('status', 'SKIPPED')}", flush=True)
    print(f"    Tier 3 (tests)         : {tier3.get('status', 'SKIPPED')}", flush=True)
    print(f"  VERIFICATION PASSED     : {verification_passed}", flush=True)
    print("─" * 72, flush=True)

    return 0 if (all_tasks_succeeded and verification_passed) else 1


# ── Entry point ──────────────────────────────────────────────────────────────

def run_build_pipeline(task_prompt: str) -> int:
    """Run the full ``nucleus build`` pipeline (PLAN → EXECUTE → VERIFY → VERDICT).

    Returns a process exit code (``0`` = success, non-zero = failure/abort).
    """
    if not task_prompt or not task_prompt.strip():
        print("build: empty task prompt", flush=True)
        return 2

    # ── PLAN ─────────────────────────────────────────────────────────────────
    ok, msg, final_plan_path = _run_plan_stage(task_prompt)
    if not ok or final_plan_path is None:
        print(f"build: PLAN stage failed — {msg}", flush=True)
        return 1

    # ── EXECUTE ──────────────────────────────────────────────────────────────
    ok, msg, pre_head, post_head, results = _run_execute_stage(task_prompt, final_plan_path)
    if not ok:
        print(f"build: EXECUTE stage failed — {msg}", flush=True)
        return 1

    # ── VERIFY ───────────────────────────────────────────────────────────────
    verification_passed, verify_details = _run_verify_stage(task_prompt, pre_head, post_head)

    # ── VERDICT ──────────────────────────────────────────────────────────────
    return _render_verdict_card(
        task_prompt=task_prompt,
        final_plan_path=final_plan_path,
        pre_head=pre_head,
        post_head=post_head,
        results=results,
        verification_passed=verification_passed,
        verify_details=verify_details,
    )
