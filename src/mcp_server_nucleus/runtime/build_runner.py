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
    _redact_secrets,
    cross_vendor_enabled,
    dispatch_and_capture,
    is_multi_vendor_available,
)

logger = logging.getLogger("nucleus.build_runner")

# ── Polling constants ────────────────────────────────────────────────────────
_PLAN_POLL_INTERVAL_S = 2
# Vendor failure output is arbitrary CLI text — the PLAN-stage failure message
# carries only this many chars of it (redacted), never the whole blob.
_PLAN_FAIL_EXCERPT_MAX = 500
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

# Scope-path token matcher. The (?:.../)+ group guarantees at least one ``/``
# (so bare ``foo.py`` does not match — only paths like ``src/foo.py``); the
# negative lookahead (?![\w.]) ensures the extension is the end of the token
# (so ``foo.yaml.bak`` does not match as ``foo.yaml``).
_SCOPE_PATH_RE = re.compile(
    r'(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:py|sh|md|json|toml|yaml|yml)(?![\w.])',
    re.IGNORECASE,
)
_SCOPE_EXTS = frozenset({"py", "sh", "md", "json", "toml", "yaml", "yml"})

# Cues marking a segment as a PROHIBITION rather than a declaration. Paths in
# such a segment are subtracted from the declared scope instead of added to it
# — see _declared_scope. Deliberately phrase-level, not word-level: bare "not"
# appears in plenty of ordinary instructions and would over-trigger.
_SCOPE_NEGATIVE_RE = re.compile(
    r"deny[\s-]*list|do\s+not\s+(?:touch|modify|change|edit|alter)"
    r"|don't\s+(?:touch|modify|change|edit|alter)|never\s+(?:touch|modify|edit)"
    r"|leave\s+\S+\s+(?:alone|untouched)|must\s+not\s+(?:touch|modify|change)",
    re.IGNORECASE,
)

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


def _working_tree_files() -> set[str]:
    """Set of modified + untracked files in the working tree (not commit diff).

    Runs ``git status --porcelain`` and parses each line: the path starts at
    index 3. Renames (``R``/``C``) carry the form ``old -> new`` — the RHS is
    taken as the current path. Surrounding quotes (used by git when paths
    contain special characters) are stripped. Paths are repo-root-relative.

    Returns an empty set on any git error (best-effort, matches ``_git_head``).
    """
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("git status --porcelain failed: %s", exc)
        return set()

    files: set[str] = set()
    for line in out.splitlines():
        if len(line) < 3:
            continue
        path = line[3:]
        # Renames/copies: "old -> new" — keep the new (RHS) path.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
            path = path[1:-1]
        if path:
            files.add(path)
    return files


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


def _mark_stale_plans_error(plan_ids: List[str], reason: str = "") -> int:
    """Mark a batch of stale plans as ERROR in their respective state.json files.

    Called when a build run discovers plans left IN_PROGRESS from a prior
    crashed/timed-out run (e.g. on startup sweep). Distinct from
    :func:`_mark_plan_orphaned` which marks a single plan on process exit;
    this handles a sweep of multiple stale plans discovered after the fact.

    Skips plans already in a terminal status (APPROVED, SINGLE_VENDOR_PLAN,
    ORPHANED, ERROR) so it is idempotent across repeated sweeps. Returns the
    count of plans actually transitioned to ERROR.
    """
    terminal = {"APPROVED", "SINGLE_VENDOR_PLAN", "ORPHANED", "ERROR"}
    transitioned = 0
    for plan_id in plan_ids:
        if not plan_id:
            continue
        state = _read_state(plan_id)
        if not state:
            continue
        if state.get("status") in terminal:
            continue
        state["status"] = "ERROR"
        state["error_at"] = int(time.time())
        if reason:
            state["error_reason"] = reason
        _write_state(plan_id, state)
        transitioned += 1
        logger.warning(
            "plan %s marked ERROR (stale sweep%s)",
            plan_id,
            f": {reason}" if reason else "",
        )
    return transitioned


#: A plan with no live owner is only presumed dead after this long without an
#: update. Generous on purpose: sweeping early kills healthy work, while
#: sweeping late merely delays cleanup of something already broken.
_STALE_AFTER_S = 1800  # 30 minutes


def _process_alive(pid: Optional[int]) -> bool:
    """Is ``pid`` a live process? ``False`` for None, junk, or a dead pid."""
    try:
        os.kill(int(pid), 0)
    except (TypeError, ValueError, ProcessLookupError):
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def _find_stale_plans() -> List[str]:
    """Scan ``.brain/plans/*/state.json`` for plans genuinely left behind.

    ``status == "IN_PROGRESS"`` is NOT sufficient. That set is the dead plans
    UNION the live ones, and the first version of this function swept all of
    it — so the second build to start silently marked a concurrently-running
    build's healthy plan ERROR. The victim reported "PLAN stage failed — plan
    review aborted: status=ERROR" and pointed the reader at the plan-review
    subsystem, which was not involved at all. Builds could not run in parallel.

    Liveness is now established two ways, cheapest first:

    ``owner_pid`` alive
        The plan records the pid that owns it. If that process still exists,
        the plan is being worked on. Decisive.
    no owner, recently updated
        Plans written before ``owner_pid`` existed carry no owner. Falling
        back to "sweep it" would reintroduce the bug for exactly those, so
        they are given ``_STALE_AFTER_S`` of quiet before being presumed dead.

    A plan is returned only when BOTH say it is gone.
    """
    plans_dir = _brain_path() / "plans"
    if not plans_dir.is_dir():
        return []
    now = time.time()
    stale: List[str] = []
    for entry in plans_dir.iterdir():
        if not entry.is_dir():
            continue
        state = _read_state(entry.name)
        if state.get("status") != "IN_PROGRESS":
            continue
        if _process_alive(state.get("owner_pid")):
            continue
        if now - _state_mtime(entry.name, state) < _STALE_AFTER_S:
            continue
        stale.append(entry.name)
    return stale


def _state_mtime(plan_id: str, state: Dict[str, Any]) -> float:
    """Best-effort "when was this plan last touched", as a unix timestamp.

    Prefers the state file's mtime, which every write updates regardless of
    which key changed. Falls back to ``updated_at``/``created_at``, then to 0
    so an unreadable timestamp means "old" rather than "forever young" — an
    unparseable date must not make a plan permanently unsweepable.
    """
    try:
        return (_brain_path() / "plans" / plan_id / "state.json").stat().st_mtime
    except OSError:
        pass
    for key in ("updated_at", "created_at"):
        raw = state.get(key)
        if not raw:
            continue
        try:
            from datetime import datetime
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            continue
    return 0.0


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

    Tolerates the plan-authoring model wrapping the "Task N:" label in
    markdown bold/italic (``**Task 0:**``, ``_Task 0:_``) — confirmed live
    output from devin's plan-author stage, and the exact cause of four
    consecutive "no unchecked Task N: checkboxes found" false-negative
    EXECUTE-stage failures (fw-1786416289-1-5e94 and this session's repro):
    the strict-plaintext version of this regex requires the literal string
    "Task" immediately after "[ ]", so a single stray ``**`` silently zeroed
    every task in an otherwise well-formed 19-task plan.
    """
    tasks: List[Tuple[int, str]] = []
    pattern = re.compile(
        r"^\s*-\s*\[\s*\]\s*[*_]{0,2}\s*Task\s+(\d+)\s*:\s*[*_]{0,2}\s*(.+?)\s*$",
        re.IGNORECASE,
    )
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


def _mark_task_done(final_plan_path: Path, task_num: int) -> bool:
    """Mark task ``task_num`` as done in *final_plan_path* (``- [ ]`` → ``- [x]``).

    On resume, :func:`_parse_task_checkboxes` only returns unchecked tasks,
    so a task flipped to ``- [x]`` here is naturally skipped without any
    separate completion tracking. Atomic write (temp + rename) so a crash
    mid-edit cannot leave a truncated plan file — same discipline as
    :func:`_write_state`.

    Returns ``True`` iff the line was found and updated.
    """
    try:
        text = final_plan_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("final_plan.md read failed for task-done mark: %s", exc)
        return False
    # Match the same flexible label format as _parse_task_checkboxes, scoped
    # to the specific task_num, and flip the checkbox to [x]. re.MULTILINE so
    # ^ and $ anchor per line (the plan file is multi-line; without it the
    # pattern could only match a single-line file).
    pattern = re.compile(
        r"^(\s*-\s*\[)\s*(\]\s*[*_]{0,2}\s*Task\s+"
        + re.escape(str(task_num))
        + r"\s*:\s*[*_]{0,2}\s*.+?\s*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    new_text, count = pattern.subn(r"\1x\2", text)
    if count == 0:
        return False
    try:
        fd, tmp = tempfile.mkstemp(dir=str(final_plan_path.parent), suffix=".md.tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp, str(final_plan_path))
    except Exception as exc:  # noqa: BLE001 — best-effort, same as _write_state
        logger.warning("final_plan.md atomic write failed for task-done mark: %s", exc)
        final_plan_path.write_text(new_text, encoding="utf-8")
    return True


def _record_task_completed(
    plan_id: Optional[str], final_plan_path: Path, task_num: int,
) -> None:
    """Record task completion for resume: mark ``- [x]`` in final_plan.md and
    append *task_num* to ``completed_tasks`` in state.json.

    No-op when *plan_id* is ``None`` (a non-resumable run that did not
    persist a plan_id). Best-effort: a state.json write failure does not
    block the build — the ``- [x]`` in final_plan.md is the primary resume
    signal, and state.json's ``completed_tasks`` is observability.
    """
    if plan_id is None:
        return
    _mark_task_done(final_plan_path, task_num)
    state = _read_state(plan_id)
    if not state:
        return
    completed = state.get("completed_tasks", [])
    if task_num not in completed:
        completed.append(task_num)
        state["completed_tasks"] = completed
        state["updated_at"] = int(time.time())
        _write_state(plan_id, state)


# ── Single-vendor lane selection ─────────────────────────────────────────────

# Cost order for the single-vendor (degraded) path: FREE lanes first, the paid
# `claude` lane only when every free lane is missing. See fw-1786104704 — the
# previous order preferred claude and treated devin/agy as the fallback "if
# claude is not installed", which never fires in practice because claude is the
# CLI running the session. Net effect was that any degraded build billed the
# paid tier for its entire execute stage while a healthy free vendor idled.
_SINGLE_VENDOR_ORDER = ("devin", "agy", "claude")


def _pick_single_vendor(stage: str) -> Optional[str]:
    """Pick the cheapest available CLI for a single-vendor dispatch.

    Honours the ``NUCLEUS_SINGLE_VENDOR`` override when that vendor is on
    PATH; otherwise walks :data:`_SINGLE_VENDOR_ORDER` (free before paid).
    Returns ``None`` when no known CLI is installed.
    """
    forced = os.environ.get("NUCLEUS_SINGLE_VENDOR", "").strip()
    if forced:
        if shutil.which(forced):
            logger.info("single-vendor %s: using %s (NUCLEUS_SINGLE_VENDOR)",
                        stage, forced)
            return forced
        logger.warning(
            "NUCLEUS_SINGLE_VENDOR=%s not found on PATH, falling back to "
            "cost order %s", forced, "/".join(_SINGLE_VENDOR_ORDER))
    for vendor in _SINGLE_VENDOR_ORDER:
        if shutil.which(vendor):
            if vendor == "claude":
                logger.warning(
                    "single-vendor %s: no free vendor on PATH, falling back to "
                    "PAID claude", stage)
            else:
                logger.info("single-vendor %s: using free vendor %s",
                            stage, vendor)
            return vendor
    return None


def _single_vendor_candidates() -> List[str]:
    """All installed CLIs in cost order — the fallback pool for plan
    dispatch. ``NUCLEUS_SINGLE_VENDOR`` narrows it to one entry when the
    named vendor is on PATH (an explicit pick is not a fallback target).
    """
    forced = os.environ.get("NUCLEUS_SINGLE_VENDOR", "").strip()
    if forced:
        if shutil.which(forced):
            return [forced]
        logger.warning(
            "NUCLEUS_SINGLE_VENDOR=%s not found on PATH, falling back to "
            "cost order %s", forced, "/".join(_SINGLE_VENDOR_ORDER))
    return [v for v in _SINGLE_VENDOR_ORDER if shutil.which(v)]


# ── PLAN stage ───────────────────────────────────────────────────────────────

def _run_single_vendor_plan_stage(task_prompt: str) -> Tuple[bool, str, Optional[Path]]:
    """Single-vendor plan: one real dispatch per available vendor, in cost
    order, until one produces a concrete task-decomposition plan — written
    to ``final_plan.md`` with status ``SINGLE_VENDOR_PLAN`` (NOT
    ``APPROVED`` — no adversarial review round ran, there being no second
    vendor to review). Reuses the SAME ``dispatch_and_capture`` subprocess
    path the dual-vendor execute stage uses, so the plan text is a real
    captured vendor result, not a passthrough. Returns
    ``(ok, message, final_plan_path)``.
    """
    # Detect available CLI for plan dispatch. ARBITRAGE ORDER (fw-1786104704):
    # FREE vendors first, paid `claude` only as last resort. The old order
    # preferred claude and fell back to devin/agy "if claude is not installed"
    # — but claude is always on PATH (it is the CLI running the session), so
    # the free branches were dead code and every degraded build silently
    # billed the paid tier while a healthy free lane sat idle.
    # Override with NUCLEUS_SINGLE_VENDOR (devin|agy|claude).
    plan_vendor = _pick_single_vendor("plan")
    if plan_vendor is None:
        return (
            False,
            "no coding agent CLI found on PATH. Install one of: "
            "`claude` (npm i -g @anthropic-ai/claude-code), "
            "`devin` (pip install devin-cli), or "
            "`agy` (pip install agy-cli)",
            None,
        )

    # Vendor fallback (EID-488): the pick is the first attempt, then every
    # remaining installed CLI in cost order. A stranger's first vendor can be
    # quota-dead or auth-expired while another works — the old code died on
    # the first failure even when a healthy lane was installed.
    candidates = [plan_vendor] + [
        v for v in _single_vendor_candidates() if v != plan_vendor
    ]

    plan_id = f"build_single_{int(time.time())}"
    plan_dir = _brain_path() / "plans" / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    # RAG context is now injected upstream in _run_plan_stage (default ON
    # for both single-vendor and dual-vendor paths). task_prompt already
    # contains the RAG context if it was available.

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
        f"BUILD TASK:\n{task_prompt}"
    )
    # Each attempt's excerpt shares the excerpt budget — with N vendors the
    # all-fail message stays bounded. Each `result` is arbitrary CLI output:
    # cap it, and re-run secret redaction at this boundary even though capture
    # already redacts — this string reaches the user's terminal and can be
    # copied into logs/comments.
    per_attempt_max = max(
        80, _PLAN_FAIL_EXCERPT_MAX // max(1, len(candidates))
    )
    attempts: List[str] = []
    res: Dict[str, Any] = {}
    for vendor in candidates:
        res = dispatch_and_capture(
            vendor, plan_prompt,
            artifact_ref=str(plan_dir),
            mode="write",
        )
        if res.get("status") == "ok" and res.get("produced_output") is True:
            plan_vendor = vendor
            break
        raw = res.get("result") or ""
        excerpt, _n = _redact_secrets(raw[:per_attempt_max])
        detail = (
            f"status={res.get('status')!r} "
            f"produced_output={res.get('produced_output')!r} "
            f"rc={res.get('rc')!r}"
        )
        if excerpt.strip():
            detail += f" output={excerpt.strip()!r}"
        attempts.append(f"{vendor} ({detail})")
        logger.warning("single-vendor plan dispatch failed on %s: %s",
                       vendor, detail[:200])
    else:
        # Surface EVERY attempt's real reason (EID-388 + EID-488): which
        # vendor died and how — quota, auth, malformed output — so a stranger
        # can tell whether to install another CLI or fix the first.
        return (
            False,
            "single-vendor plan dispatch failed on "
            + "; ".join(attempts),
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
        "task_prompt": task_prompt,
        "created_at": int(time.time()),
    }
    _write_state(plan_id, state)
    return True, _SINGLE_VENDOR_PLAN_STATUS, final_plan_path


def _persist_task_prompt(plan_id: str, state: Dict[str, Any], task_prompt: str) -> None:
    """Augment *state* with ``task_prompt`` if absent, so resume can rebuild
    the verify stage's provenance scope.

    The dual-vendor plan state is written by ``execute_plan_review_loop``,
    not by this module, so ``task_prompt`` is not in it by default.
    Best-effort: a write failure does not block the build — resume falls
    back to an empty prompt (permissive scope).
    """
    if not task_prompt or state.get("task_prompt"):
        return
    try:
        state["task_prompt"] = task_prompt
        _write_state(plan_id, state)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("could not persist task_prompt for plan %s: %s", plan_id, exc)


def _run_plan_stage(task_prompt: str) -> Tuple[bool, str, Optional[Path], str]:
    """Run the plan stage; returns ``(ok, message, final_plan_path, execution_mode)``.

    When :func:`is_multi_vendor_available` is True, runs the existing
    dual-vendor adversarial plan review loop (status ``APPROVED``) —
    byte-identical to prior behavior. When False, runs the single-vendor
    ``claude`` plan dispatch (status ``SINGLE_VENDOR_PLAN``, no review round).
    *execution_mode* is ``"dual-vendor"`` or ``"single-vendor"`` and threads
    through to the execute + verdict stages.

    RAG context injection (Phase 7 §4) is the DEFAULT for both paths —
    non-interactive one-shot builds benefit most from prior context because
    there's no human in the loop to catch "you already built this" errors.
    The injection is graceful: if RAG is unavailable, the build proceeds
    without context. Override with ``NUCLEUS_BUILD_RAG_CONTEXT=off``.
    """
    # RAG context injection — default ON for all plan paths.
    # Non-interactive one-shot builds need this most: no human catches
    # "you already built this" or "that was already decided" mid-run.
    rag_enabled = os.environ.get("NUCLEUS_BUILD_RAG_CONTEXT", "on").lower() not in ("off", "0", "false")
    if rag_enabled:
        rag_context = _gather_rag_context(task_prompt)
        if rag_context:
            task_prompt = f"{rag_context}\n{task_prompt}"

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
    # back to devin's own default model (swe-2-max).
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
    # fw-1786036802: author and reviewer vendors default to DIFFERENT values
    # to prevent self-review. The plan_review_loop tool's own defaults are both
    # "agy", which ran self-review (same vendor reviewing its own plan). Now
    # the build_runner explicitly sets author=devin, reviewer=agy by default,
    # and the tool's own same-vendor guard is no longer dead code.
    author_vendor = os.environ.get("NUCLEUS_PLAN_REVIEW_AUTHOR_VENDOR", "devin").strip() or "devin"
    reviewer_vendor = os.environ.get("NUCLEUS_PLAN_REVIEWER", "agy").strip() or "agy"
    # Auto-default reviewer_model to None when the reviewer vendor differs
    # from the author vendor — the tool's _DEFAULT_REVIEWER_MODEL is
    # Anthropic-specific and sending it to devin/gemini causes silent
    # failures. This makes the fix automatic instead of requiring caller
    # discipline.
    reviewer_model = None  # vendor_dispatch picks the right default per vendor
    params = {
        "prompt": task_prompt,
        "author_vendor": author_vendor,
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

    # Claim ownership so a CONCURRENT build's stale sweep can tell this plan is
    # alive. Without an owner the sweep can only guess from status, and
    # IN_PROGRESS covers live plans as well as dead ones — which is precisely
    # how a healthy parallel build used to get marked ERROR by whichever run
    # started second. Best-effort: a plan that fails to record its owner falls
    # back to the sweep's age threshold rather than losing protection outright.
    try:
        _claim = _read_state(plan_id)
        if _claim:
            _claim["owner_pid"] = os.getpid()
            _write_state(plan_id, _claim)
    except Exception as exc:  # pragma: no cover — never block the build on this
        logger.debug("could not record owner_pid for plan %s: %s", plan_id, exc)

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
                _persist_task_prompt(plan_id, state, task_prompt)
                return True, "APPROVED", fp, _MODE_DUAL_VENDOR
            if status == "SINGLE_VENDOR_PLAN":
                # fw-1786036802: tool produced a single-vendor fallback plan
                # (same vendor default). Use the tool's final_plan_path.
                fp = _resolve_final_plan_path(plan_id, state)
                if fp is None:
                    return False, "SINGLE_VENDOR_PLAN but final_plan_path missing on disk", None, _MODE_SINGLE_VENDOR
                _persist_task_prompt(plan_id, state, task_prompt)
                return True, "SINGLE_VENDOR_PLAN", fp, _MODE_SINGLE_VENDOR
            if status in _ABORT_STATUSES:
                return False, f"plan review aborted: status={status}", None, _MODE_DUAL_VENDOR
            time.sleep(_PLAN_POLL_INTERVAL_S)

        return False, f"plan review timed out after {_PLAN_POLL_TIMEOUT_S}s (last={last_status})", None, _MODE_DUAL_VENDOR
    finally:
        # Clear active plan and restore signal handlers on clean exit
        _active_plan_id = None
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)


# ── Scope enforcement ─────────────────────────────────────────────────────────

def _declared_scope(task_prompt: str) -> set[str]:
    """Extract the set of file paths declared in a task prompt.

    Scans *task_prompt* for path-like tokens — substrings containing at least
    one ``/`` and ending in one of the whitelisted extensions (``.py``, ``.sh``,
    ``.md``, ``.json``, ``.toml``, ``.yaml``, ``.yml``) — using ``_SCOPE_PATH_RE``.

    Returns an empty set when no such paths are found. An empty result is
    *permissive*, not *restrictive*: it signals that the prompt declared no
    explicit file scope, so callers must NOT treat it as "scope is empty /
    nothing may be touched." An empty set means "no constraint was declared,"
    i.e. fall back to the caller's default (typically unrestricted) policy.

    **Polarity matters.** Harvesting every path token regardless of the words
    around it meant a prompt reading ``In A ONLY. DENY-LIST: do not touch B``
    declared BOTH A and B as in-scope, so editing B raised no violation. The
    sentence written to tighten the constraint was the one that loosened it —
    and the build skill instructs authors to write exactly that sentence, so
    the more carefully a prompt was scoped, the weaker the guard became.

    Each segment is therefore classified before its paths are harvested: a
    segment carrying a negative cue contributes to the DENIED set, everything
    else to the ALLOWED set, and denied paths are subtracted at the end. A
    path named on both sides resolves to denied, because an explicit
    prohibition is the more specific statement.
    """
    text = task_prompt or ""
    allowed: set[str] = set()
    denied: set[str] = set()
    # Split on line breaks and sentence boundaries. ". " cannot split a path:
    # the dot in "brain_rag.py" is followed by "p", never by a space.
    for line in text.splitlines():
        for segment in re.split(r"(?<=\.)\s+|;\s+", line):
            if not segment.strip():
                continue
            found = _SCOPE_PATH_RE.findall(segment)
            if not found:
                continue
            target = denied if _SCOPE_NEGATIVE_RE.search(segment) else allowed
            target.update(found)
    return allowed - denied


def _resolve_expect_paths(declared: set[str]) -> Optional[list[str]]:
    """Keep only *declared* tokens that resolve to an existing path.

    Each token is resolved relative to :func:`Path.cwd`, or used as-is when it
    is already absolute and exists. Tokens that do not resolve are dropped.
    Returns the survivors as a sorted list of absolute path strings, or
    ``None`` when nothing resolves (so callers can distinguish "no constraint"
    from "constraint present but unresolvable").

    This helper does NOT stat the repo root or invent paths — it only checks
    what was explicitly declared.
    """
    resolved: list[str] = []
    for token in declared:
        p = Path(token)
        if not p.is_absolute():
            p = Path.cwd() / token
        if p.exists():
            resolved.append(str(p.resolve()))
    if not resolved:
        return None
    return sorted(resolved)


def _scope_violations(changed_files, declared) -> list[str]:
    """Return the subset of *changed_files* outside the *declared* scope.

    *declared* is the set returned by :func:`_declared_scope`. Consistent
    with that function's contract, an **empty** *declared* set is
    *permissive* — it means no explicit file scope was declared, so every
    changed file is allowed and this returns ``[]``. Callers must NOT
    interpret an empty result here as "everything violates."

    When *declared* is non-empty, any changed path that does not match a
    declared path is a violation. Matching is ROOT-VS-MIRROR TOLERANT: this
    repo carries the same module under two roots (``mcp-server-nucleus/src/...``
    and ``nucleus-mcp/src/...``), and prompts name one while ``git status``
    reports the other. Two paths match when one is a whole-component suffix
    of the other, so ``runtime/build_runner.py`` declared in a prompt covers
    ``mcp-server-nucleus/src/mcp_server_nucleus/runtime/build_runner.py``.
    That direction of error is deliberate: a scope check that fires on a
    legitimate mirror edit would be turned off within a day.

    The returned list is de-duplicated and sorted for stable output.
    """
    if not declared:
        return []

    norm_declared = [_norm_scope_path(p) for p in declared]
    violations: set[str] = set()
    for f in changed_files or ():
        if f is None:
            continue
        norm = _norm_scope_path(f)
        if not any(_paths_equivalent(norm, d) for d in norm_declared):
            violations.add(f)
    return sorted(violations)


# The same package is vendored under two roots in this repo. A path under
# either root names the same logical file, so both reduce to a common form
# before comparison — otherwise every legitimate mirror edit reads as a
# violation and the check gets switched off.
_SCOPE_MIRROR_ROOTS = ("mcp-server-nucleus/src/", "nucleus-mcp/src/",
                       "mcp-server-nucleus/", "nucleus-mcp/")


def _norm_scope_path(path: str) -> str:
    """Normalize a path for scope comparison.

    Strips ``./`` prefixes and any mirror-root prefix. Uses an explicit
    prefix loop rather than ``lstrip("./")`` — ``lstrip`` takes a CHARACTER
    SET, so ``".claude/x.md".lstrip("./")`` yields ``"claude/x.md"``,
    silently corrupting every dotfile path.
    """
    p = (path or "").strip()
    while p.startswith("./"):
        p = p[2:]
    p = p.strip("/")
    for root in _SCOPE_MIRROR_ROOTS:
        if p.startswith(root):
            return p[len(root):]
    return p


def _paths_equivalent(a: str, b: str) -> bool:
    """True when *a* and *b* name the same file under either repo root.

    Component-wise suffix match in both directions, so a prompt may name a
    path at any depth and still match the working-tree path git reports.
    """
    if a == b:
        return True
    pa, pb = a.split("/"), b.split("/")
    shorter, longer = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
    return longer[-len(shorter):] == shorter


_SCOPE_MODES = ("off", "warn", "fail")


def _scope_mode() -> str:
    """Read ``NUCLEUS_SCOPE_ENFORCEMENT``: ``off`` | ``warn`` (default) | ``fail``.

    Defaults to ``warn`` because this check has never run in the wild. A
    post-condition whose false-positive rate is unmeasured must not be able
    to fail a build on its first day; ``warn`` collects the evidence that
    would justify promoting it to ``fail``.
    """
    raw = os.environ.get("NUCLEUS_SCOPE_ENFORCEMENT", "").strip().lower()
    if raw in _SCOPE_MODES:
        return raw
    if raw:
        logger.warning("ignoring NUCLEUS_SCOPE_ENFORCEMENT=%r (expected one of %s)",
                       raw, "/".join(_SCOPE_MODES))
    return "warn"


def _enforce_scope(
    before_files: set,
    declared: set,
    task_num: int,
    mode: Optional[str] = None,
) -> Tuple[set, bool, str]:
    """Post-condition on one dispatch: did it touch files outside *declared*?

    *before_files* is the working-tree file set snapshotted BEFORE the
    dispatch. This re-snapshots now and treats the delta as what this
    dispatch touched, so pre-existing dirty files (this tree is shared with
    concurrent agents) are never blamed on the vendor.

    Returns ``(after_files, blocked, message)``. *after_files* is the fresh
    snapshot and MUST be threaded into the next call as *before_files*.
    *blocked* is True only in ``fail`` mode with real violations.
    """
    after_files = _working_tree_files()
    mode = mode or _scope_mode()
    if mode == "off" or not declared:
        return after_files, False, ""

    touched = after_files - (before_files or set())
    violations = _scope_violations(sorted(touched), declared)
    if not violations:
        return after_files, False, ""

    msg = (
        f"task {task_num} touched {len(violations)} file(s) outside its declared "
        f"scope: {', '.join(violations[:10])}"
        + (" …" if len(violations) > 10 else "")
    )
    if mode == "fail":
        logger.error("scope violation (fail): %s", msg)
        return after_files, True, msg
    logger.warning("scope violation (warn): %s", msg)
    return after_files, False, msg


# ── EXECUTE stage ────────────────────────────────────────────────────────────

def _run_execute_stage(
    task_prompt: str,
    final_plan_path: Path,
    execution_mode: str = _MODE_DUAL_VENDOR,
    plan_id: Optional[str] = None,
) -> Tuple[bool, str, str, str, List[Dict[str, Any]]]:
    """Dispatch each parsed task checkbox to a vendor (write mode), fail-stop.

    Vendor selection by *execution_mode*: ``"dual-vendor"`` → ``devin``
    (requires :func:`cross_vendor_enabled`, byte-identical to prior behavior);
    ``"single-vendor"`` → ``claude`` (the native-fallback path, no
    cross-vendor gate). Both paths reuse the SAME :func:`dispatch_and_capture`
    subprocess dispatch, so pre_head/post_head git-diff provenance and the
    verify-stage machinery work completely unchanged.

    When *plan_id* is non-None, each successfully dispatched task is marked
    ``- [x]`` in *final_plan_path* (via :func:`_record_task_completed`) so
    that :func:`resume_build_pipeline` can re-parse the plan and skip
    already-completed tasks. When *plan_id* is ``None`` (the default), no
    progress is persisted — byte-identical to prior behavior.

    Returns ``(ok, message, pre_head, post_head, dispatch_results)``.
    *pre_head* is captured before the first dispatch; *post_head* after the
    last. On fail-stop *post_head* equals *pre_head* (no further dispatch ran).
    """
    if execution_mode == _MODE_SINGLE_VENDOR:
        # Cost-ordered lane selection (fw-1786104704): free vendors before the
        # paid claude lane. This is the stage that actually spends money — a
        # degraded build dispatches EVERY task here, so preferring claude meant
        # a single dead free vendor turned the whole execute stage paid.
        vendor = _pick_single_vendor("execute")
        if vendor is None:
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
    scope_mode = _scope_mode()
    # Snapshot once before the loop; _enforce_scope returns the next snapshot.
    scope_before = _working_tree_files() if scope_mode != "off" else set()
    # Target-file-presence check: always snapshot, regardless of scope mode.
    # The check that declared target files were actually modified is
    # independent of scope enforcement (which checks the opposite — that
    # the vendor didn't touch files OUTSIDE scope).
    target_before = _working_tree_files()
    for task_num, task_desc in tasks:
        logger.info("dispatching task %d (%s): %s", task_num, vendor, task_desc)
        # Compute declared scope ONCE per task, before dispatch, so the
        # dispatch evidence (expect_paths) and the scope post-condition
        # cannot disagree. Falls back to the overall prompt when the task
        # names no paths — an empty declared set is permissive, never
        # restrictive.
        declared = _declared_scope(task_desc) or _declared_scope(task_prompt)
        expect_paths = _resolve_expect_paths(declared)
        res = dispatch_and_capture(
            vendor, task_desc,
            artifact_ref=str(final_plan_path),
            mode="write",
            expect_paths=expect_paths,
        )
        results.append({"task_num": task_num, "task_desc": task_desc, "result": res, "vendor": vendor})

        # Scope post-condition (fw-1786125011). The preamble ASKS a vendor to
        # stay in scope; this CHECKS it. Reuses the SAME `declared` set
        # computed before dispatch above — no recomputation, so dispatch
        # evidence and scope check cannot diverge.
        if scope_mode != "off":
            scope_before, scope_blocked, scope_msg = _enforce_scope(
                scope_before, declared, task_num, mode=scope_mode,
            )
            if scope_msg:
                results[-1]["scope_violation"] = scope_msg
            if scope_blocked:
                return (
                    False,
                    f"scope violation at task {task_num}: {scope_msg}",
                    pre_head, pre_head, results,
                )
        # Fail-stop predicate: status == "ok" AND produced_output is True.
        if not (res.get("status") == "ok" and res.get("produced_output") is True):
            # Dynamic model fallback (Phase 7 §5): before fail-stopping,
            # try the next model in the fallback chain. The health registry
            # already recorded the failure via _record_dispatch_health in
            # vendor_dispatch.py, so the fallback chain will skip the
            # failed model and try the next-best one for this task type.
            fallback = _try_model_fallback(
                vendor, task_desc, task_prompt, final_plan_path, results, task_num,
            )
            if fallback is None:
                return (
                    False,
                    f"fail-stop at task {task_num}: status={res.get('status')!r} "
                    f"produced_output={res.get('produced_output')!r}",
                    pre_head,
                    pre_head,
                    results,
                )
            # Fallback succeeded — fall through to the target-file check
            # below (the fallback's output needs the same verification as
            # the primary dispatch).

        # Target-file presence check: verify that each declared target file
        # was actually modified (or confirmed absent-for-reason) before this
        # task counts as passed. Closes the defect where a vendor reports
        # success without touching its tasked target files — the fail-stop
        # predicate above only checks status/produced_output, neither of
        # which proves the declared target files were touched.
        target_after = _working_tree_files()
        target_touched = target_after - target_before
        from . import execution_verifier
        target_sig = execution_verifier.verify_target_files_present(
            declared, sorted(target_touched), Path.cwd(),
        )
        results[-1]["target_files_check"] = target_sig
        target_before = target_after
        if not target_sig["passed"]:
            return (
                False,
                f"fail-stop at task {task_num}: declared target files not "
                f"modified: {', '.join(target_sig['not_modified'][:5])}",
                pre_head,
                pre_head,
                results,
            )
        # Dispatch succeeded (primary or fallback) and target files verified —
        # record progress for resume.
        _record_task_completed(plan_id, final_plan_path, task_num)

    post_head = _git_head()
    return True, f"executed {len(tasks)} task(s) via {vendor}", pre_head, post_head, results


def _try_model_fallback(
    failed_vendor: str,
    task_desc: str,
    task_prompt: str,
    final_plan_path: Path,
    results: List[Dict[str, Any]],
    task_num: int,
    max_attempts: int = 3,
) -> Optional[Dict[str, Any]]:
    """Try the next model in the fallback chain after a dispatch failure.

    Phase 7 §5: instead of fail-stopping on the first vendor failure, query
    the model_registry for the next-best available model and retry. The
    health registry already recorded the failure (via _record_dispatch_health
    in vendor_dispatch.py), so the fallback chain will skip the failed model.

    Returns the successful result dict if a fallback model succeeded, or
    None if all fallback attempts also failed (caller fail-stops).

    max_attempts caps the total fallback tries to avoid infinite loops.
    """
    try:
        from .model_registry import next_model_after_failure, discover_models
    except ImportError:
        logger.debug("model_registry not available for fallback")
        return None

    # Compute declared scope the same way as the primary dispatch path
    # (see _run_execute_stage): task_desc first, then the overall prompt as
    # a permissive fallback. The fallback shares task_desc and final_plan_path
    # from the caller; the prompt context is the same, so the same resolution
    # applies and the fallback's expect_paths cannot disagree with the
    # primary dispatch's evidence.
    declared = _declared_scope(task_desc) or _declared_scope(task_prompt)
    expect_paths = _resolve_expect_paths(declared)

    # Determine task type from the task description (simple heuristic)
    task_type = "code_executor"  # execute stage is always code execution

    discovered = discover_models()
    if not discovered:
        return None

    # Get the failed model id from the last result
    last_result = results[-1].get("result", {}) if results else {}
    failed_model = last_result.get("model_id", "")

    for attempt in range(max_attempts):
        next_model = next_model_after_failure(
            failed_vendor, failed_model, task_type, discovered,
        )
        if next_model is None:
            logger.info("fallback: no more models to try after %d attempts", attempt)
            return None

        logger.info(
            "fallback attempt %d: %s:%s (score=%.3f) for task %d",
            attempt + 1, next_model.vendor, next_model.model_id,
            next_model.score, task_num,
        )

        res = dispatch_and_capture(
            next_model.vendor, task_desc,
            artifact_ref=str(final_plan_path),
            mode="write",
            model=next_model.model_id,
            expect_paths=expect_paths,
        )
        results.append({
            "task_num": task_num,
            "task_desc": task_desc,
            "result": res,
            "vendor": next_model.vendor,
            "model_id": next_model.model_id,
            "fallback_attempt": attempt + 1,
        })

        if res.get("status") == "ok" and res.get("produced_output") is True:
            logger.info(
                "fallback succeeded: %s:%s for task %d",
                next_model.vendor, next_model.model_id, task_num,
            )
            return res

        # Update for next iteration — this model also failed
        failed_vendor = next_model.vendor
        failed_model = next_model.model_id

    return None


# ── Pseudonymity preflight (fw-1786120486) ──────────────────────────────────
#
# The build pipeline has verification tiers for diff, syntax, imports and
# tests, but none for the guards that actually gate landing. A build can
# report a clean verdict on work that cannot enter the repo because the
# pre-commit pseudonymity-guard rejects it. This scan surfaces blocked
# terms in the build's changed files BEFORE the verdict card, so the
# vendor spend is not wasted on uncommittable output.

# Blocked terms are NOT stored here. They are LOADED AT RUNTIME from the
# canonical guard, .githooks/pre-commit-pseudonymity-guard, which lives outside
# the packaged tree.
#
# WHY: this module ships to PyPI. A previous version hardcoded the operator's
# real name, two email addresses, employer, company and three absolute home
# paths as its blocklist -- so the guard built to stop identity reaching public
# artifacts would have published the complete set. Caught by scanning a built
# artifact, not by any check on the source.
#
#     A DETECTOR MAY CONTAIN PATTERNS OF WHAT IT DETECTS.
#     IT MAY NEVER CONTAIN INSTANCES.
#
# If the canonical guard cannot be read, this returns INSUFFICIENT rather than
# an empty list. An empty blocklist would make every scan pass, silently, which
# is the failure this whole mechanism exists to prevent.

_PSEUDONYMITY_GUARD_REL = ".githooks/pre-commit-pseudonymity-guard"


def _load_pseudonymity_terms(project_root) -> tuple[list[str], list[str], str | None]:
    """Return (terms, ci_terms, error). A non-None error means INSUFFICIENT.

    Never returns empty lists with error=None -- that would read as 'clean'.
    """
    import os
    from pathlib import Path

    override = os.environ.get("NUCLEUS_PSEUDONYMITY_TERMS_FILE")
    candidates = [Path(override)] if override else []
    if project_root:
        candidates.append(Path(project_root) / _PSEUDONYMITY_GUARD_REL)

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        terms = sorted({
            m for m in re.findall(r'"([^"\n]{4,60})"', text) + re.findall(r"'([^'\n]{4,60})'", text)
            if any(c.isalpha() for c in m)
        })
        if terms:
            return terms, [t.lower() for t in terms], None
    return [], [], (
        f"pseudonymity blocklist unavailable (looked for {_PSEUDONYMITY_GUARD_REL}); "
        "scan is INSUFFICIENT, not clean"
    )


def _pseudonymity_scan(changed_files: list[str], project_root) -> list[dict]:
    """Scan changed files' diffs for pseudonymity-blocked terms.

    Returns a list of violation dicts: ``{file, term, line}``. Empty list
    means no violations. Only checks ADDED lines (lines starting with '+'
    in the diff), matching the guard's additions-only policy.
    """
    import subprocess
    violations = []

    # The blocklist is LOADED, not hardcoded (see _load_pseudonymity_terms above).
    # If it cannot be read, say so LOUDLY -- returning [] here would read as
    # "no violations" and make this preflight silently useless, which is the
    # exact failure this mechanism exists to prevent.
    terms, ci_terms, load_error = _load_pseudonymity_terms(project_root)
    if load_error:
        return [{
            "file": "<blocklist>",
            "term": "<INSUFFICIENT>",
            "line": load_error,
        }]
    all_terms = terms + ci_terms
    for relpath in changed_files:
        try:
            r = subprocess.run(
                ["git", "diff", "--unified=0", "--", relpath],
                capture_output=True, text=True, timeout=5,
                cwd=str(project_root),
            )
        except Exception:
            logger.debug("Swallowed exception in _pseudonymity_scan", exc_info=True)
            continue
        if r.returncode != 0:
            continue
        for line_num, line in enumerate(r.stdout.splitlines(), 1):
            if not line.startswith("+") or line.startswith("+++"):
                continue
            line_lower = line.lower()
            for term in all_terms:
                if term.lower() in line_lower:
                    violations.append({
                        "file": relpath,
                        "term": term,
                        "line": line.strip()[:120],
                    })
                    break  # one violation per line is enough
    return violations


# ── Comment-to-code ratio check (fw-1786154034) ──────────────────────────────
#
# A vendor shipped a 158-line deploy script with 36 code lines where the
# comments described features the code did not implement. Every keyword-
# based check passed because every missing feature was named in a comment.
# This check surfaces the code-vs-total ratio as a warning signal.

# Threshold: if code lines < 40% of total non-blank lines, flag the file.
# 40% catches the 4:1 comment-to-code ratio (36/158 = 23%) while allowing
# well-documented modules (typically 60-70% code).
_CODE_RATIO_THRESHOLD = 0.40


def _comment_code_ratio_check(changed_files: list[str], project_root) -> list[dict]:
    """Check comment-to-code ratio of changed script files.

    Returns a list of warning dicts: ``{file, total_lines, code_lines,
    code_ratio}``. Empty list means no warnings. Only checks .sh, .py,
    .js, .ts files. A file with <40% code lines (by the threshold above)
    is flagged — a large gap between prose and code is the smell.
    """
    import subprocess
    warnings = []
    checkable_exts = (".sh", ".py", ".js", ".ts")
    for relpath in changed_files:
        if not relpath.endswith(checkable_exts):
            continue
        fpath = project_root / relpath
        if not fpath.exists():
            continue
        try:
            content = fpath.read_text(errors="replace")
        except Exception:
            logger.debug("Swallowed exception in _comment_code_ratio_check", exc_info=True)
            continue
        lines = content.splitlines()
        total = 0
        code = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            total += 1
            # Count as comment if the line starts with # (after strip)
            # or is inside a /* */ block (simplified: single-line /* ... */)
            if stripped.startswith("#"):
                continue
            if stripped.startswith("//"):
                continue
            if stripped.startswith("/*") and stripped.endswith("*/"):
                continue
            code += 1
        if total == 0:
            continue
        ratio = code / total
        if ratio < _CODE_RATIO_THRESHOLD:
            warnings.append({
                "file": relpath,
                "total_lines": total,
                "code_lines": code,
                "code_ratio": round(ratio, 2),
            })
    return warnings


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

    Provenance isolation (fw-1786116954): the changed-file set from
    ``_get_changed_files`` includes ``git diff --name-only pre_head``, which
    compares pre_head to the WORKING TREE. When another agent or the operator
    commits to the same working tree while a build is running, those commits
    ARE in the working tree and get incorrectly attributed as build output.
    To prevent this, the declared scope (from ``_declared_scope``) is used to
    split changed files into ``attributed_files`` (within declared scope) and
    ``unattributed_files`` (outside). Only attributed files are verified by
    tiers 1–3; unattributed files are reported in the details but do not
    participate in verification. When the declared scope is empty
    (deny-by-default — no paths declared), no files are attributed and
    tier 0 fails: a build that declares no scope provably changed
    nothing in scope, so concurrent same-worktree commits cannot sneak
    in as attributed build output.

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
    all_changed_files = execution_verifier._get_changed_files("", pre_head, project_root)

    # ── Provenance isolation (fw-1786116954) ──────────────────────────────
    # Split changed files into attributed (within declared scope) and
    # unattributed (concurrent commits from the same working tree). Only
    # attributed files are verified; unattributed files are reported but
    # do not participate in tier 1–3 verification. An empty declared scope
    # is deny-by-default — no files are claimed, so every changed file is
    # unattributed and tier 0 fails (the build provably changed nothing in
    # scope). Empty scope must NOT be permissive: treating "no files
    # claimed" as "everything allowed" lets concurrent same-worktree
    # commits be attributed as build output, which is the exact failure
    # provenance isolation exists to prevent.
    declared = _declared_scope(task_prompt)
    attributed_files = [f for f in all_changed_files if f in declared]
    unattributed_files = [f for f in all_changed_files if f not in declared]

    # Tier 0 checks the ATTRIBUTED set, not the raw diff. A build that
    # produced no attributed files but has unattributed ones (concurrent
    # commits) is still a tier-0 failure — the build itself changed nothing.
    changed_files = attributed_files

    details: Dict[str, Any] = {
        "changed_files": changed_files,
        "unattributed_files": unattributed_files,
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

    # ── Pseudonymity preflight (fw-1786120486) ─────────────────────────────
    # Scan changed files for blocked terms BEFORE spending tier 1-3 budget.
    # Violations are reported in the details but do not block verification
    # — the build may still produce correct code that just needs a term
    # scrubbed before commit. The verdict card surfaces them prominently.
    pseudo_violations = _pseudonymity_scan(changed_files, project_root)
    if pseudo_violations:
        details["pseudonymity_violations"] = pseudo_violations

    # ── Comment-to-code ratio check (fw-1786154034) ───────────────────────
    # A vendor once shipped a 158-line deploy script with 36 code lines
    # (4:1 comment-to-code ratio) where the comments described features
    # the code did not implement. Every keyword-based check passed because
    # every missing feature was named in a comment. This check surfaces
    # the ratio as a warning so the verdict card distinguishes "all code"
    # from "all prose."
    ratio_warnings = _comment_code_ratio_check(changed_files, project_root)
    if ratio_warnings:
        details["comment_code_ratio_warnings"] = ratio_warnings

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
    single_vendor: Optional[str] = None,
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
    unattributed_files = verify_details.get("unattributed_files", [])
    tier0 = verify_details.get("tier0", {})
    tier1 = verify_details.get("tier1", {})
    tier2 = verify_details.get("tier2", {})
    tier3 = verify_details.get("tier3", {})

    if execution_mode == _MODE_SINGLE_VENDOR:
        vendor_name = single_vendor or (results[0]["vendor"] if results else "claude")
        mode_label = f"single-vendor ({vendor_name} only, no adversarial review)"
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
    if unattributed_files:
        print(f"  UNATTRIBUTED ({len(unattributed_files)}) — concurrent commits, NOT build output:", flush=True)
        for f in unattributed_files:
            print(f"    - {f}", flush=True)
    pseudo_violations = verify_details.get("pseudonymity_violations", [])
    if pseudo_violations:
        print(f"  PSEUDONYMITY WARN ({len(pseudo_violations)}) — blocked terms in build output, will fail commit:", flush=True)
        for v in pseudo_violations:
            print(f"    - {v['file']}: term '{v['term']}' in: {v['line'][:80]}", flush=True)
    ratio_warnings = verify_details.get("comment_code_ratio_warnings", [])
    if ratio_warnings:
        print(f"  CODE RATIO WARN ({len(ratio_warnings)}) — low code-to-comment ratio, comments may describe unimplemented features:", flush=True)
        for w in ratio_warnings:
            print(f"    - {w['file']}: {w['code_lines']}/{w['total_lines']} code lines ({w['code_ratio']:.0%})", flush=True)
    print("  VERIFICATION STATUS:", flush=True)

    def _print_tier_line(tier_num: int, desc: str, tier: Dict[str, Any]) -> None:
        """Print one VERIFICATION STATUS tier line.

        PASSED/SKIPPED → bare status, byte-identical to the original
        hardcoded lines. FAILED → Tier 3 surfaces ``unrunnable`` (pytest
        missing) as ``FAILED (UNRUNNABLE — pytest not available in
        <python>)``; every FAILED tier also prints an indented tail (last
        200 chars) of each signal's ``output`` (falling back to ``error``
        when ``output`` is absent).
        """
        label = f"Tier {tier_num} ({desc})"
        prefix = f"    {label.ljust(22)} : "
        status = tier.get("status", "SKIPPED")
        if status in ("PASSED", "SKIPPED"):
            print(f"{prefix}{status}", flush=True)
            return
        # FAILED — Tier 3 unrunnable gets a named verdict.
        signals = tier.get("signals") or []
        if tier_num == 3 and any(s.get("unrunnable") for s in signals):
            py = next(
                (s.get("python", "(unknown)") for s in signals if s.get("unrunnable")),
                "(unknown)",
            )
            print(f"{prefix}FAILED (UNRUNNABLE — pytest not available in {py})", flush=True)
        else:
            print(f"{prefix}{status}", flush=True)
        # Indented tail (last 200 chars) of each signal's output, falling
        # back to ``error`` when ``output`` is absent.
        for sig in signals:
            tail = (sig.get("output") or sig.get("error") or "").strip()
            if tail:
                print(f"        {tail[-200:]}", flush=True)

    _print_tier_line(0, "diff nonempty", tier0)
    _print_tier_line(1, "syntax", tier1)
    _print_tier_line(2, "imports", tier2)
    _print_tier_line(3, "tests", tier3)
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

    # ── STALE-PLAN SWEEP ──────────────────────────────────────────────────────
    # Clean up plans left IN_PROGRESS by a prior crashed/timed-out run before
    # this run creates its own plan. Idempotent — skips already-terminal plans.
    stale = _find_stale_plans()
    if stale:
        n = _mark_stale_plans_error(stale, reason="stale on new build run")
        if n:
            print(f"build: marked {n} stale plan(s) ERROR", flush=True)

    # ── PLAN ─────────────────────────────────────────────────────────────────
    ok, msg, final_plan_path, execution_mode = _run_plan_stage(task_prompt)
    if not ok or final_plan_path is None:
        print(f"build: PLAN stage failed — {msg}", flush=True)
        return 1

    # Derive the plan_id from the final_plan_path's parent directory name
    # (.brain/plans/<plan_id>/final_plan.md) so the execute stage can
    # persist per-task completion for resume. This is the standard layout
    # for both single-vendor and dual-vendor paths.
    plan_id = final_plan_path.parent.name

    # ── EXECUTE ──────────────────────────────────────────────────────────────
    ok, msg, pre_head, post_head, results = _run_execute_stage(
        task_prompt, final_plan_path, execution_mode=execution_mode,
        plan_id=plan_id,
    )
    if not ok:
        print(f"build: EXECUTE stage failed — {msg}", flush=True)
        return 1

    # ── VERIFY ───────────────────────────────────────────────────────────────
    verification_passed, verify_details = _run_verify_stage(task_prompt, pre_head, post_head)

    # ── VERDICT ──────────────────────────────────────────────────────────────
    # In single-vendor mode, derive the vendor name from the first execute
    # result so the verdict card labels the run with the actual vendor that
    # ran it (not just the default "claude" fallback).
    single_vendor = (
        results[0]["vendor"]
        if execution_mode == _MODE_SINGLE_VENDOR and results
        else None
    )
    return _render_verdict_card(
        task_prompt=task_prompt,
        final_plan_path=final_plan_path,
        pre_head=pre_head,
        post_head=post_head,
        results=results,
        verification_passed=verification_passed,
        verify_details=verify_details,
        execution_mode=execution_mode,
        single_vendor=single_vendor,
    )


def resume_build_pipeline(plan_id: str) -> int:
    """Resume an ORPHANED plan from its persisted state (EXECUTE → VERIFY → VERDICT).

    The defect this fixes: when the build process exits (timeout, Ctrl-C,
    crash) while a plan is IN_PROGRESS, :func:`_mark_plan_orphaned`
    stamps the plan ORPHANED — a terminal status with no resume path.
    The completed plan-authoring work (the approved ``final_plan.md``)
    and any partially-completed execute-stage tasks were unrecoverable;
    the only option was to start a fresh build with a new plan_id.

    This entry point reloads the ORPHANED plan's persisted state and
    re-enters the pipeline at the EXECUTE stage. Tasks already completed
    during the prior run were marked ``- [x]`` in ``final_plan.md`` (by
    :func:`_record_task_completed`), so :func:`_parse_task_checkboxes`
    naturally skips them — execution continues from the first unchecked
    task instead of restarting from task 0.

    Only ORPHANED plans are resumable. APPROVED / SINGLE_VENDOR_PLAN are
    success (use :func:`run_build_pipeline` for a fresh run); ERROR is
    for stale-plan sweeps and is not resumable (re-run the build instead).

    Returns a process exit code (``0`` = success, non-zero = failure/abort).
    """
    if not plan_id or not plan_id.strip():
        print("resume: empty plan_id", flush=True)
        return 2

    state = _read_state(plan_id)
    if not state:
        print(f"resume: no state found for plan {plan_id}", flush=True)
        return 2

    if state.get("status") != "ORPHANED":
        print(
            f"resume: plan {plan_id} is not ORPHANED (status={state.get('status')}) "
            "— only ORPHANED plans can be resumed",
            flush=True,
        )
        return 2

    final_plan_path = _resolve_final_plan_path(plan_id, state)
    if final_plan_path is None:
        print(f"resume: plan {plan_id} has no final_plan.md on disk", flush=True)
        return 2

    execution_mode = state.get("execution_mode", _MODE_DUAL_VENDOR)
    task_prompt = state.get("task_prompt", "")

    # Transition ORPHANED → IN_PROGRESS (resuming) and claim ownership so
    # a concurrent build's stale sweep can tell this plan is alive.
    state["status"] = "IN_PROGRESS"
    state["resumed_at"] = int(time.time())
    state["owner_pid"] = os.getpid()
    _write_state(plan_id, state)

    # Register orphan cleanup so that if THIS process exits while the
    # resumed execute stage is running, the plan is re-stamped ORPHANED
    # (resumable again) rather than left IN_PROGRESS for the stale sweep
    # to mark ERROR (not resumable). Mirrors the plan-stage cleanup in
    # _run_plan_stage.
    _active_plan_id: Optional[str] = None

    def _orphan_cleanup(*_args: Any) -> None:
        if _active_plan_id:
            _mark_plan_orphaned(_active_plan_id)

    atexit.register(_orphan_cleanup)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    old_sigint = signal.getsignal(signal.SIGINT)

    def _signal_handler(signum: int, frame: Any) -> None:
        _orphan_cleanup()
        signal.signal(signum, old_sigterm if signum == signal.SIGTERM else old_sigint)
        if signum == signal.SIGTERM:
            raise SystemExit(143)
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    _active_plan_id = plan_id
    try:
        # ── EXECUTE (resume) ───────────────────────────────────────────────
        # _parse_task_checkboxes only returns unchecked tasks, so tasks
        # already marked - [x] by the prior run are skipped automatically.
        ok, msg, pre_head, post_head, results = _run_execute_stage(
            task_prompt, final_plan_path, execution_mode=execution_mode,
            plan_id=plan_id,
        )
        if not ok:
            print(f"resume: EXECUTE stage failed — {msg}", flush=True)
            return 1

        # ── VERIFY ─────────────────────────────────────────────────────────
        verification_passed, verify_details = _run_verify_stage(
            task_prompt, pre_head, post_head,
        )

        # ── VERDICT ────────────────────────────────────────────────────────
        single_vendor = (
            results[0]["vendor"]
            if execution_mode == _MODE_SINGLE_VENDOR and results
            else None
        )
        return _render_verdict_card(
            task_prompt=task_prompt,
            final_plan_path=final_plan_path,
            pre_head=pre_head,
            post_head=post_head,
            results=results,
            verification_passed=verification_passed,
            verify_details=verify_details,
            execution_mode=execution_mode,
            single_vendor=single_vendor,
        )
    finally:
        _active_plan_id = None
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)
