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

import atexit
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .vendor_dispatch import (
    cross_vendor_enabled,
    dispatch_and_capture,
    is_multi_vendor_available,
)

logger = logging.getLogger("nucleus.build_runner")

# ── Polling constants ────────────────────────────────────────────────────────
_PLAN_POLL_INTERVAL_S = 2
# execute_plan_review_loop runs its actual work in a daemon thread inside
# THIS process — if this poll gives up and the CLI process exits, that thread
# dies with it and the plan is orphaned mid-round (observed live: 5 dispatch
# rounds over ~9 min still left the plan IN_PROGRESS at round 3/5 when the
# 600s budget below expired). 1200s gives real headroom over the ~75-140s per
# round observed live, for the max_rounds=3 this module requests below.
# 1 hour, and env-overridable. A dual-vendor review with retries legitimately
# exceeds 1200s once the vendor ceiling itself is 3600s; the old value made the
# build abandon reviews that were still running.
_PLAN_POLL_TIMEOUT_S = int(os.environ.get("NUCLEUS_PLAN_POLL_TIMEOUT_S", "3600"))

# Statuses that abort the build (anything other than APPROVED).
_ABORT_STATUSES = frozenset({
    "CONVERGED_WITH_MINOR_ISSUES",
    "MAX_ROUNDS_EXHAUSTED",
    "BUDGET_EXCEEDED",
    "CANCELLED",
    "ERROR",
    "OSCILLATING",
})

# Single-vendor native-fallback plan status. HONESTLY DISTINCT from the
# dual-vendor ``APPROVED``: a single-vendor run performs ONE real plan
# dispatch to the ``claude`` vendor and skips the adversarial review round
# (there is no second vendor to review). Using ``APPROVED`` here would lie to
# the verdict card by implying an adversarially-reviewed plan; this label
# makes the unreviewed nature explicit. See ADR review rejecting the earlier
# design that mislabeled a raw passthrough as ``APPROVED``.
_SINGLE_VENDOR_PLAN_STATUS = "SINGLE_VENDOR_PLAN"

# Execution-mode labels surfaced on the verdict card.
_MODE_DUAL_VENDOR = "dual-vendor"
_MODE_SINGLE_VENDOR = "single-vendor"

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


def _gather_rag_context(task_prompt: str) -> str:
    """Gather conversation + codebase RAG context for a headless build agent.

    Phase 7 §4: headless agents (build_runner, vendor_dispatch) had no RAG
    context — they planned and executed blind, with no knowledge of prior
    decisions, failures, or conversation history. This function gives them
    the same grounding that ``nucleus_ground`` gives interactive agents.

    Returns a formatted context block to prepend to the plan prompt, or
    an empty string if RAG is unavailable (graceful degradation — the
    build proceeds without context rather than failing).
    """
    try:
        from .common import get_brain_path
        import sys
        brain_path = get_brain_path()
        if brain_path is None:
            brain_path = str(Path.cwd() / ".brain")
        brain_path = str(brain_path)
        # Add the repo root to sys.path so providers.brain_rag is importable
        repo_root = str(Path(brain_path).parent)
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from providers.brain_rag import search_brain, _read_brain_owner
        import providers.brain_rag as br

        # Use Ollama if available, otherwise skip dense search
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        br.OLLAMA_URL = ollama_url

        project = _read_brain_owner(Path(brain_path))

        # Gather conversation context (what agents discussed)
        conv_results = search_brain(
            task_prompt,
            brain_path=str(brain_path),
            scope="conversation",
            topk=3,
            project=project,
            project_filter="demote",
        )

        # Gather codebase context (relevant code patterns)
        code_results = search_brain(
            task_prompt,
            brain_path=str(brain_path),
            scope="code",
            topk=2,
            project=project,
            project_filter="demote",
        )

        parts = []
        if conv_results:
            parts.append("PRIOR CONVERSATION CONTEXT (what agents discussed about this topic):")
            for r in conv_results[:3]:
                role = r.get("agent_role", "") or "unknown"
                age = r.get("time_band", "") or "undated"
                content = (r.get("content", "") or "")[:200]
                parts.append(f"  [{role}] [{age}] {content}")
            parts.append("")

        if code_results:
            parts.append("RELEVANT CODEBASE PATTERNS:")
            for r in code_results[:2]:
                src = (r.get("source", "") or "")[:60]
                content = (r.get("content", "") or "")[:150]
                parts.append(f"  {src}: {content}")
            parts.append("")

        if parts:
            return "\n".join(parts) + "\n"
        return ""
    except Exception as e:
        import traceback
        logger.warning("RAG context gathering failed (proceeding without context): %s\n%s", e, traceback.format_exc())
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


def _write_state(plan_id: str, state: Dict[str, Any]) -> None:
    """Atomically write ``.brain/plans/<plan_id>/state.json``.

    Uses temp-file + rename so that a crash mid-write doesn't leave a
    truncated/partial state file — the root cause of the 'APPROVED but
    final_plan_path missing on disk' friction point.
    """
    plan_dir = _brain_path() / "plans" / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    state_path = plan_dir / "state.json"
    try:
        fd, tmp = tempfile.mkstemp(dir=str(plan_dir), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, str(state_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("state.json atomic write failed for %s: %s", plan_id, exc)


def _mark_plan_orphaned(plan_id: str) -> None:
    """Mark a plan as ORPHANED in state.json.

    Called on process exit / signal so that a timed-out plan isn't left
    IN_PROGRESS forever — the next run can detect and clean up.
    """
    if not plan_id:
        return
    state = _read_state(plan_id)
    if not state:
        return
    if state.get("status") in ("APPROVED", "SINGLE_VENDOR_PLAN", "ORPHANED"):
        return  # Already terminal
    state["status"] = "ORPHANED"
    state["orphaned_at"] = int(time.time())
    _write_state(plan_id, state)
    logger.warning("plan %s marked ORPHANED (process exiting while IN_PROGRESS)", plan_id)


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

def _run_single_vendor_plan_stage(task_prompt: str) -> Tuple[bool, str, Optional[Path]]:
    """Single-vendor plan: ONE real dispatch to the ``claude`` vendor asking
    for a concrete task-decomposition plan, written to ``final_plan.md`` with
    status ``SINGLE_VENDOR_PLAN`` (NOT ``APPROVED`` — no adversarial review
    round ran, there being no second vendor to review). Reuses the SAME
    ``dispatch_and_capture`` subprocess path the dual-vendor execute stage
    uses, so the plan text is a real captured vendor result, not a
    passthrough. Returns ``(ok, message, final_plan_path)``.
    """
    # Detect available CLI for plan dispatch — prefer claude, fall back to
    # devin/agy so single-vendor mode works even if only one CLI is installed.
    if shutil.which("claude"):
        plan_vendor = "claude"
    elif shutil.which("devin"):
        plan_vendor = "devin"
        logger.info("claude CLI not found, using devin for single-vendor plan")
    elif shutil.which("agy"):
        plan_vendor = "agy"
        logger.info("claude CLI not found, using agy for single-vendor plan")
    else:
        return (
            False,
            "no coding agent CLI found on PATH. Install one of: "
            "`claude` (npm i -g @anthropic-ai/claude-code), "
            "`devin` (pip install devin-cli), or "
            "`agy` (pip install agy-cli)",
            None,
        )

    plan_id = f"build_single_{int(time.time())}"
    plan_dir = _brain_path() / "plans" / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    # RAG context injection (Phase 7 §4): ground the headless plan agent in
    # prior conversation context so it doesn't repeat work or miss decisions.
    # Without this, the build agent plans blind — it has no idea what was
    # tried before, what failed, or what was already decided. This is the
    # "context rot" fix: the harness assists the headless agent the same way
    # it assists an interactive agent via nucleus_ground.
    rag_context = _gather_rag_context(task_prompt)

    # Prompt the claude vendor to emit the EXACT checkbox format
    # _parse_task_checkboxes expects, so the execute stage can parse the
    # resulting final_plan.md unchanged.
    plan_prompt = (
        "You are a task planner for the `nucleus build` pipeline. Decompose "
        "the following build task into a numbered list of concrete, "
        "independently-dispatchable sub-tasks. Output ONLY a markdown "
        "checklist using EXACTLY this format for each task (one per line, "
        "no prose, no preamble, no summary):\n"
        "  - [ ] Task N: <one-line description>\n"
        "The tasks must each be executable by a coding agent in write mode "
        "(file edits / shell commands) and together must accomplish the "
        "build task.\n\n"
        f"{rag_context}"
        f"BUILD TASK:\n{task_prompt}"
    )
    res = dispatch_and_capture(
        plan_vendor, plan_prompt,
        artifact_ref=str(plan_dir),
        mode="read",
    )
    if not (res.get("status") == "ok" and res.get("produced_output") is True):
        return (
            False,
            f"single-vendor plan dispatch failed: status={res.get('status')!r} "
            f"produced_output={res.get('produced_output')!r}",
            None,
        )

    plan_text = res.get("result", "") or ""
    final_plan_path = plan_dir / "final_plan.md"
    # Atomic write: temp file + rename so a crash doesn't leave a
    # truncated final_plan.md that causes 'APPROVED but final_plan_path
    # missing on disk' downstream.
    try:
        fd, tmp = tempfile.mkstemp(dir=str(plan_dir), suffix=".md.tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(plan_text)
        os.replace(tmp, str(final_plan_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("final_plan.md atomic write failed: %s", exc)
        final_plan_path.write_text(plan_text, encoding="utf-8")

    # Write state.json atomically with the honestly distinct status label.
    state: Dict[str, Any] = {
        "plan_id": plan_id,
        "status": _SINGLE_VENDOR_PLAN_STATUS,
        "final_plan_path": str(final_plan_path),
        "execution_mode": _MODE_SINGLE_VENDOR,
        "vendor": plan_vendor,
        "created_at": int(time.time()),
    }
    _write_state(plan_id, state)
    return True, _SINGLE_VENDOR_PLAN_STATUS, final_plan_path


def _run_plan_stage(task_prompt: str) -> Tuple[bool, str, Optional[Path], str]:
    """Run the plan stage; returns ``(ok, message, final_plan_path, execution_mode)``.

    When :func:`is_multi_vendor_available` is True, runs the existing
    dual-vendor adversarial plan review loop (status ``APPROVED``) —
    byte-identical to prior behavior. When False, runs the single-vendor
    ``claude`` plan dispatch (status ``SINGLE_VENDOR_PLAN``, no review round).
    *execution_mode* is ``"dual-vendor"`` or ``"single-vendor"`` and threads
    through to the execute + verdict stages.
    """
    if not is_multi_vendor_available():
        ok, msg, fp = _run_single_vendor_plan_stage(task_prompt)
        return ok, msg, fp, _MODE_SINGLE_VENDOR

    # Lazy import to avoid eager import of the tools package at module load.
    from ..tools.plan_review_loop import execute_plan_review_loop

    # reviewer_vendor="devin": the tool's own default (agy authoring, agy also
    # reviewing) failed 3/3 live-fire attempts with "vendor did not produce
    # output" specifically at the reviewer step, while a direct agy read-mode
    # health check succeeded — i.e. agy is up, but agy-self-review is not.
    # agy-author / devin-reviewer succeeded 2/2 in the same session. Pin the
    # working pairing explicitly rather than trust the tool default.
    #
    # reviewer_model=None: the tool's _DEFAULT_REVIEWER_MODEL is an
    # Anthropic-only model id and is applied unconditionally regardless of
    # reviewer_vendor, so overriding reviewer_vendor alone still sends an
    # invalid model to devin. Passing None here makes vendor_dispatch fall
    # back to devin's own default model (glm-5.2).
    # max_rounds: ENV-SELECTABLE. Default raised from 3 to 5 after
    # fw-1785862863 — a well-scoped 6-step deploy_blog.sh task hit
    # MAX_ROUNDS_EXHAUSTED at round 3. The tool's own default is 5; the
    # original pin to 3 was too tight. Override via NUCLEUS_PLAN_MAX_ROUNDS
    # for tight-wall-clock runs.
    max_rounds = 5
    try:
        max_rounds = max(1, int(os.environ.get("NUCLEUS_PLAN_MAX_ROUNDS", "5")))
    except (ValueError, TypeError):
        pass
    # ENV-SELECTABLE, deliberately not hardcoded. The "devin" pin above was
    # adopted after agy appeared to fail self-review 3/3 — but those failures
    # were an expired agy OAuth token (discovered ~30 min later), not a
    # self-review defect. The cause was misattributed and then frozen into
    # source. When devin's own quota later ran out ("/upgrade to access this
    # model") the pin became a single point of failure: 13 of 33 plan runs in
    # 30 hours died as "vendor did not produce output". Vendor availability is
    # a moving target; pinning it in source is itself the bug.
    reviewer_vendor = os.environ.get("NUCLEUS_PLAN_REVIEWER", "agy").strip() or "agy"
    # Auto-default reviewer_model to None when the reviewer vendor differs
    # from the author vendor — the tool's _DEFAULT_REVIEWER_MODEL is
    # Anthropic-specific and sending it to devin/gemini causes silent
    # failures. This makes the fix automatic instead of requiring caller
    # discipline.
    reviewer_model = None  # vendor_dispatch picks the right default per vendor
    params = {
        "prompt": task_prompt,
        "reviewer_vendor": reviewer_vendor,
        "reviewer_model": reviewer_model,
        "max_rounds": max_rounds,
    }
    raw = execute_plan_review_loop(params, _make_response)
    try:
        res = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return False, f"plan_review_loop returned non-JSON: {exc}", None, _MODE_DUAL_VENDOR

    if not res.get("success") or res.get("error"):
        # SINGLE-VENDOR FALLBACK (2026-08-04, flywheel #92).
        # When the dual-vendor plan review fails (agy rate limit, OAuth expiry,
        # empty output, etc.), fall back to single-vendor mode using devin
        # instead of aborting the entire build. This keeps nucleus build --merge
        # usable when one vendor is down. The plan produced is labeled
        # SINGLE_VENDOR_PLAN (not APPROVED) so the merge gate knows it skipped
        # the adversarial review round.
        plan_error = res.get("error") or str(res)
        logger.warning(
            "dual-vendor plan review failed (%s) — falling back to single-vendor", 
            plan_error[:200]
        )
        ok, msg, fp = _run_single_vendor_plan_stage(task_prompt)
        if ok:
            return ok, f"SINGLE_VENDOR_FALLBACK: {msg}", fp, _MODE_SINGLE_VENDOR
        return False, f"plan_review_loop failed: {plan_error} (single-vendor fallback also failed: {msg})", None, _MODE_DUAL_VENDOR

    data = res.get("data") or {}
    plan_id = data.get("plan_id")
    if not plan_id:
        # sync mode returns final state directly — treat as already terminal
        status = data.get("status")
        if status == "APPROVED":
            fp = _resolve_final_plan_path(data.get("plan_id", ""), data)
            if fp is None:
                return False, "APPROVED but final_plan_path missing on disk", None, _MODE_DUAL_VENDOR
            return True, "APPROVED", fp, _MODE_DUAL_VENDOR
        return False, f"plan_review_loop returned no plan_id (status={status})", None, _MODE_DUAL_VENDOR

    # Poll state.json until APPROVED or an abort status fires.
    # Register orphan cleanup so that if THIS process exits (timeout, Ctrl-C,
    # crash) while the plan is still IN_PROGRESS, the plan is marked ORPHANED
    # instead of being left in a zombie state for the next run to stumble on.
    _active_plan_id: Optional[str] = None

    def _orphan_cleanup(*_args: Any) -> None:
        if _active_plan_id:
            _mark_plan_orphaned(_active_plan_id)

    atexit.register(_orphan_cleanup)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    old_sigint = signal.getsignal(signal.SIGINT)

    def _signal_handler(signum: int, frame: Any) -> None:
        _orphan_cleanup()
        # Restore and re-raise so the default handler runs
        signal.signal(signum, old_sigterm if signum == signal.SIGTERM else old_sigint)
        if signum == signal.SIGTERM:
            raise SystemExit(143)
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    deadline = time.monotonic() + _PLAN_POLL_TIMEOUT_S
    last_status: Optional[str] = None
    _active_plan_id = plan_id
    try:
        while time.monotonic() < deadline:
            state = _read_state(plan_id)
            status = state.get("status")
            if status and status != last_status:
                logger.info("plan %s status: %s", plan_id, status)
                last_status = status
            if status == "APPROVED":
                fp = _resolve_final_plan_path(plan_id, state)
                if fp is None:
                    return False, "APPROVED but final_plan_path missing on disk", None, _MODE_DUAL_VENDOR
                return True, "APPROVED", fp, _MODE_DUAL_VENDOR
            if status in _ABORT_STATUSES:
                return False, f"plan review aborted: status={status}", None, _MODE_DUAL_VENDOR
            time.sleep(_PLAN_POLL_INTERVAL_S)

        return False, f"plan review timed out after {_PLAN_POLL_TIMEOUT_S}s (last={last_status})", None, _MODE_DUAL_VENDOR
    finally:
        # Clear active plan and restore signal handlers on clean exit
        _active_plan_id = None
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)


# ── EXECUTE stage ────────────────────────────────────────────────────────────

def _run_execute_stage(
    task_prompt: str,
    final_plan_path: Path,
    execution_mode: str = _MODE_DUAL_VENDOR,
) -> Tuple[bool, str, str, str, List[Dict[str, Any]]]:
    """Dispatch each parsed task checkbox to a vendor (write mode), fail-stop.

    Vendor selection by *execution_mode*: ``"dual-vendor"`` → ``devin``
    (requires :func:`cross_vendor_enabled`, byte-identical to prior behavior);
    ``"single-vendor"`` → ``claude`` (the native-fallback path, no
    cross-vendor gate). Both paths reuse the SAME :func:`dispatch_and_capture`
    subprocess dispatch, so pre_head/post_head git-diff provenance and the
    verify-stage machinery work completely unchanged.

    Returns ``(ok, message, pre_head, post_head, dispatch_results)``.
    *pre_head* is captured before the first dispatch; *post_head* after the
    last. On fail-stop *post_head* equals *pre_head* (no further dispatch ran).
    """
    if execution_mode == _MODE_SINGLE_VENDOR:
        # Detect available CLIs instead of hard-requiring claude. If claude
        # is missing, check for devin/agy as fallbacks so a stranger's first
        # run doesn't hit a wall with a cryptic error.
        if shutil.which("claude"):
            vendor = "claude"
        elif shutil.which("devin"):
            vendor = "devin"
            logger.info("claude CLI not found, falling back to devin for single-vendor execute")
        elif shutil.which("agy"):
            vendor = "agy"
            logger.info("claude CLI not found, falling back to agy for single-vendor execute")
        else:
            return (
                False,
                "no coding agent CLI found on PATH. Install one of: "
                "`claude` (npm i -g @anthropic-ai/claude-code), "
                "`devin` (pip install devin-cli), or "
                "`agy` (pip install agy-cli)",
                "", "", [],
            )
    else:
        if not cross_vendor_enabled():
            return False, "cross-vendor dispatch is disabled (run `nucleus onboard`)", "", "", []
        # ENV-SELECTABLE for the same reason NUCLEUS_PLAN_REVIEWER is: a vendor
        # pinned in source becomes a single point of failure the moment that
        # vendor's quota or auth lapses. Observed: devin returned
        # "/upgrade to access this model" instantly, so every EXECUTE task
        # fail-stopped at task 1 even though the plan had been APPROVED.
        # NOTE: shutil.which()-style PATH detection (used by the single-vendor
        # branch above) cannot catch this — devin IS installed and on PATH; it
        # is the account quota that is exhausted. Availability is only knowable
        # by dispatching, which is why this is an operator-set override rather
        # than an auto-detect.
        vendor = os.environ.get("NUCLEUS_BUILD_EXECUTOR", "devin").strip() or "devin"

    pre_head = _git_head()
    if not pre_head:
        return False, "could not record pre_head (git rev-parse HEAD failed)", "", "", []

    tasks = _parse_task_checkboxes(final_plan_path)
    if not tasks:
        return False, f"no unchecked Task N: checkboxes found in {final_plan_path}", pre_head, pre_head, []

    results: List[Dict[str, Any]] = []
    for task_num, task_desc in tasks:
        logger.info("dispatching task %d (%s): %s", task_num, vendor, task_desc)
        res = dispatch_and_capture(
            vendor, task_desc,
            artifact_ref=str(final_plan_path),
            mode="write",
        )
        results.append({"task_num": task_num, "task_desc": task_desc, "result": res, "vendor": vendor})
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
    return True, f"executed {len(tasks)} task(s) via {vendor}", pre_head, post_head, results


# ── VERIFY stage ─────────────────────────────────────────────────────────────

def _evaluate_tier(
    signals: List[Dict[str, Any]],
    skip_reason: str,
) -> Tuple[Optional[bool], Dict[str, Any]]:
    """Reduce one tier's signal list to a 3-state ``(passed, details)`` verdict.

    This is the shared reducer for tiers 1–3. It enforces the tri-state
    semantics introduced to fix the bug where an empty Tier-1 result list
    was coerced to FAILED (``bool([]) == False``) while Tiers 2/3 correctly
    treated "nothing to check" as SKIPPED — the same shape now applies to
    every tier.

    States (the only three legal values of ``details["status"]``):

    * ``SKIPPED`` — *signals* is empty ("nothing to check" for this tier,
      e.g. no syntax-checkable files, no ``.py`` files, no test files
      discovered). Reported via *passed* = ``None``: "no verdict — does
      not count for or against the gate." *details* carries a ``reason``
      string explaining what was absent.
    * ``PASSED`` — *signals* is non-empty and every entry's ``passed`` flag
      is truthy, aggregated via ``all(r.get("passed", False) for r in signals)``.
      Reported via *passed* = ``True``.
    * ``FAILED`` — *signals* is non-empty and at least one entry's
      ``passed`` flag is falsy. Reported via *passed* = ``False``.

    A SKIPPED tier is never silently counted as a pass and never fails the
    gate on its own; only an explicit FAILED contributes to
    ``failed_count`` in :func:`_run_verify_stage` (and thus to exit code 1).

    Returns ``(passed, details)`` where *details* always carries ``status``
    and the raw ``signals`` list, plus a ``reason`` string on SKIPPED.
    """
    if not signals:
        return None, {"status": "SKIPPED", "signals": signals, "reason": skip_reason}
    passed = all(r.get("passed", False) for r in signals)
    return passed, {
        "status": "PASSED" if passed else "FAILED",
        "signals": signals,
    }


def _run_verify_stage(task_prompt: str, pre_head: str, post_head: str) -> Tuple[bool, Dict[str, Any]]:
    """VERIFY stage — multi-tier verification of changed files.

    Derives the changed-file set via ``execution_verifier._get_changed_files``
    (passing ``""`` as the first positional arg — the function ignores it and
    queries git state directly, including untracked files via
    ``git ls-files --others --exclude-standard`` so newly-created files are
    not invisible). Empty ``changed_files`` is a tier-0 FAILURE (nothing
    provably changed) that short-circuits: tiers 1–3 are left at their
    initial SKIPPED state and never run, and the run is reported as a hard
    ``FAILED`` with ``failed_count=1`` (tier 0) and ``skipped_count=3``
    (tiers 1–3). Otherwise runs tier-1 syntax, tier-2 import, and tier-3
    test checks, each reduced to a 3-state ``(passed, details)`` verdict
    via :func:`_evaluate_tier`.

    Tier 2 is Python-only: when no ``.py`` files are present it is reported
    SKIPPED without invoking the import checker. For all tiers, an empty
    signal list (e.g. no syntax-checkable files, no importable candidates
    after filtering, no test files discovered) is reported as SKIPPED —
    never silently counted as a pass, never failing the gate on its own.

    Count tracking (over tiers 1–3 only; tier 0 is accounted for
    separately in the short-circuit branch above):

    * ``passed_count``  — number of tiers with status ``PASSED``
    * ``failed_count``  — number of tiers with status ``FAILED``
    * ``skipped_count`` — number of tiers with status ``SKIPPED``

    The three counts always sum to 3. ``summary_status`` is then derived:

    * ``FAILED``      — ``failed_count > 0`` (any tier explicitly failed)
    * ``INSUFFICIENT``— ``failed_count == 0`` AND ``skipped_count > 0``
      (no failures, but verification incomplete — at least one tier could
      not run, e.g. no ``.py`` files, no test files discovered)
    * ``PASSED``      — every tier ran and passed
      (``failed_count == 0`` AND ``skipped_count == 0``)

    Gate + exit-code-1 enforcement: ``verification_passed`` is ``True`` iff
    ``failed_count == 0``. Crucially, an ``INSUFFICIENT`` run still returns
    ``verification_passed = True`` — a SKIPPED tier is a warning
    (incomplete verification), not a failure, and does NOT on its own
    force exit code 1. Only a FAILED run (``failed_count > 0``, including
    the tier-0 short-circuit) returns ``verification_passed = False``,
    which :func:`_render_verdict_card` enforces as exit code ``1`` via
    ``return 0 if (all_tasks_succeeded and verification_passed) else 1``.
    A task-side failure (``all_tasks_succeeded`` False) also enforces
    exit 1 independently of verification.

    Returns ``(verification_passed, details)`` where *details* carries
    per-tier status strings (``PASSED``/``FAILED``/``SKIPPED``), raw
    signals, the changed-file list, a ``files_count`` on a passing
    tier-0, the three tier counts, and the derived ``summary_status``.
    """
    # Lazy import — keeps module load stdlib-clean.
    from . import execution_verifier
    from .ground import detect_project_root

    project_root = detect_project_root()
    changed_files = execution_verifier._get_changed_files("", pre_head, project_root)

    details: Dict[str, Any] = {
        "changed_files": changed_files,
        "tier1": {"status": "SKIPPED", "signals": []},
        "tier2": {"status": "SKIPPED", "signals": []},
        "tier3": {"status": "SKIPPED", "signals": []},
    }

    # ── Tier 0: diff nonempty ───────────────────────────────────────────────
    if not changed_files:
        # Tier-0 failure is a hard FAILED: tiers 1–3 stay SKIPPED and never
        # run. failed_count=1 accounts for tier 0; skipped_count=3 accounts
        # for the three tiers that were never exercised.
        details["tier0"] = {"status": "FAILED", "reason": "no changed files"}
        details["summary_status"] = "FAILED"
        details["passed_count"] = 0
        details["failed_count"] = 1
        details["skipped_count"] = 3
        return False, details
    details["tier0"] = {"status": "PASSED", "files_count": len(changed_files)}

    # ── Tier 1: syntax check ────────────────────────────────────────────────
    tier1_signals = execution_verifier._tier1_syntax_check(
        changed_files, project_root, budget_s=30.0,
    )
    # The per-tier passed flag is no longer needed directly — the gate is
    # derived below from the aggregated status counts.
    _, details["tier1"] = _evaluate_tier(
        tier1_signals, skip_reason="no syntax-checkable files",
    )

    # ── Tier 2: import check (only .py files) ───────────────────────────────
    py_files = [f for f in changed_files if f.endswith(".py")]
    if not py_files:
        # No Python files → SKIPPED without invoking the import checker.
        details["tier2"] = {"status": "SKIPPED", "signals": [], "reason": "no .py files"}
    else:
        tier2_signals = execution_verifier._tier2_import_check(
            py_files, project_root, budget_s=30.0,
        )
        _, details["tier2"] = _evaluate_tier(
            tier2_signals, skip_reason="no importable candidates after filtering",
        )

    # ── Tier 3: test execution ──────────────────────────────────────────────
    tier3_signals = execution_verifier._tier3_test_execution(
        changed_files, {"description": task_prompt}, project_root, budget_s=120.0,
    )
    _, details["tier3"] = _evaluate_tier(
        tier3_signals, skip_reason="no test files discovered",
    )

    # ── Aggregate per-tier counts → summary_status ─────────────────────────
    # Counts are over tiers 1–3 (tier 0 is accounted for separately above).
    # A SKIPPED tier (passed is None) never counts for or against the gate;
    # the gate fails iff any tier explicitly returned False (status FAILED).
    tier_statuses = (
        details["tier1"]["status"],
        details["tier2"]["status"],
        details["tier3"]["status"],
    )
    passed_count = sum(1 for s in tier_statuses if s == "PASSED")
    failed_count = sum(1 for s in tier_statuses if s == "FAILED")
    skipped_count = sum(1 for s in tier_statuses if s == "SKIPPED")

    if failed_count > 0:
        summary_status = "FAILED"
    elif skipped_count > 0:
        # No failures, but verification incomplete — at least one tier
        # could not run (e.g. no .py files, no test files discovered).
        summary_status = "INSUFFICIENT"
    else:
        summary_status = "PASSED"

    # The gate requires POSITIVE evidence, not merely the absence of failure.
    # `failed_count == 0` alone is satisfied by a run in which every
    # substantive tier SKIPPED — which is how the original tautology
    # ("VERIFICATION PASSED: True" with tiers 2 and 3 SKIPPED) survived a
    # refactor that fixed everything except this predicate. Verified only if
    # at least one of tiers 1–3 actually executed AND nothing failed; tier 0
    # (diff non-empty) is excluded on purpose, since a changed file proves
    # nothing about correctness.
    verification_passed = failed_count == 0 and passed_count > 0

    # Emit a claim receipt. The verify stage is the substrate's densest source
    # of CLAIMED-vs-PROVEN pairs, so it is the natural first producer for the
    # corpus. Best-effort by construction — `record` never raises, because an
    # observability layer that can break the check it observes is worse than
    # none. Note INSUFFICIENT maps straight through rather than collapsing to
    # REFUTED: "nothing was verified" is not "verification failed".
    try:
        from .receipt import ClaimType, Receipt, Verdict, record

        _verdict = (
            Verdict.PROVEN if summary_status == "PASSED"
            else Verdict.REFUTED if summary_status == "FAILED"
            else Verdict.INSUFFICIENT
        )
        record(Receipt(
            claim_type=ClaimType.BUILD_VERIFIED,
            claim="build changes are verified",
            verdict=_verdict,
            primitive="execution_verifier tiers 1-3 over git-reported changed files",
            claimed="vendor reported task completion",
            observed=(f"{passed_count} PASSED, {failed_count} FAILED, "
                      f"{skipped_count} SKIPPED"),
            source="nucleus_build",
            evidence=str({k: v.get("status") for k, v in details.items()
                          if isinstance(v, dict) and "status" in v}),
            reason=summary_status,
            tags=["build", "verify"],
        ))
    except Exception as exc:  # noqa: BLE001 — receipts never gate the build
        logger.debug("receipt emit skipped: %s", exc)

    details["summary_status"] = summary_status
    details["passed_count"] = passed_count
    details["failed_count"] = failed_count
    details["skipped_count"] = skipped_count
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
    execution_mode: str = _MODE_DUAL_VENDOR,
) -> int:
    """VERDICT stage — format + print the verdict card, return exit code.

    Card sections: EXECUTION MODE + CONFIDENCE (distinguishing dual-vendor
    adversarial runs from single-vendor ``claude``-only runs — a single-vendor
    run is NEVER shown as ``PROVEN`` or counted the same as a dual-vendor
    pass), CLAIMED (tasks parsed), the per-mode task-outcome line, PROVENANCE
    (pre/post HEAD SHAs), CHANGED FILES, and per-tier VERIFICATION STATUS
    (SKIPPED rendered explicitly — a skip is never shown as a pass).

    Returns ``0`` iff every task succeeded AND ``verification_passed`` is
    ``True``; otherwise ``1``. The exit code reflects pipeline completion;
    the CONFIDENCE line is what distinguishes an adversarially-reviewed pass
    from a single-vendor unreviewed run.
    """
    claimed = len(results)
    succeeded = sum(
        1 for r in results
        if r.get("result", {}).get("status") == "ok"
        and r.get("result", {}).get("produced_output") is True
    )
    all_tasks_succeeded = succeeded == claimed and claimed > 0

    changed_files = verify_details.get("changed_files", [])
    tier0 = verify_details.get("tier0", {})
    tier1 = verify_details.get("tier1", {})
    tier2 = verify_details.get("tier2", {})
    tier3 = verify_details.get("tier3", {})

    if execution_mode == _MODE_SINGLE_VENDOR:
        mode_label = "single-vendor (claude only, no adversarial review)"
        confidence_label = "SINGLE-VENDOR UNREVIEWED"
        # Single-vendor runs do NOT show 'PROVEN' — the tasks ran but were
        # never adversarially reviewed. Honest weaker tier.
        task_outcome_label = "EXECUTED"
        task_outcome_suffix = " (single-vendor, unreviewed — NOT adversarially proven)"
    else:
        mode_label = "dual-vendor adversarial"
        confidence_label = "DUAL-VENDOR ADVERSARIAL"
        task_outcome_label = "PROVEN"
        task_outcome_suffix = ""

    print("─" * 72, flush=True)
    print("  NUCLEUS BUILD — VERDICT CARD", flush=True)
    print("─" * 72, flush=True)
    print(f"  TASK PROMPT     : {task_prompt}", flush=True)
    print(f"  PLAN            : {final_plan_path}", flush=True)
    print(f"  EXECUTION MODE  : {mode_label}", flush=True)
    print(f"  CONFIDENCE      : {confidence_label}", flush=True)
    print(f"  CLAIMED         : {claimed} task(s) parsed from plan", flush=True)
    print(f"  {task_outcome_label:<15} : {succeeded}/{claimed} task(s) passed fail-stop predicate{task_outcome_suffix}", flush=True)
    print(f"  PROVENANCE      : pre_head={pre_head or '(unknown)'}", flush=True)
    print(f"                    post_head={post_head or '(unknown)'}", flush=True)
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
    print(f"  VERIFICATION            : {verify_details.get('passed_count', 0)} PASSED, {verify_details.get('failed_count', 0)} FAILED, {verify_details.get('skipped_count', 0)} SKIPPED — {verify_details.get('summary_status', 'UNKNOWN')}", flush=True)
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
    ok, msg, final_plan_path, execution_mode = _run_plan_stage(task_prompt)
    if not ok or final_plan_path is None:
        print(f"build: PLAN stage failed — {msg}", flush=True)
        return 1

    # ── EXECUTE ──────────────────────────────────────────────────────────────
    ok, msg, pre_head, post_head, results = _run_execute_stage(
        task_prompt, final_plan_path, execution_mode=execution_mode,
    )
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
        execution_mode=execution_mode,
    )
