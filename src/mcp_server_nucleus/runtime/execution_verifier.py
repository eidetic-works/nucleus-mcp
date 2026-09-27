"""
Execution Verifier — Frontier 1: GROUND (Machine Truth)
========================================================
Tiered verification of code changes. Breaks Gödel's self-referential trap
by going OUTSIDE the formal system into reality.

Cooper sends signals from inside the black hole.

Tiers:
  0 — Diff non-empty (did anything change?)
  1 — Syntax valid (py_compile, node --check, bash -n)
  2 — Imports work (python -c "import module")
  3 — Tests pass (pytest on related test files)
  4 — Runtime (start server, hit endpoints, verify responses)

Each tier is independent. If a tier can't run, it's skipped (not failed).
Total budget: configurable, default 30s.

This is the canonical engine. scripts/execution_verifier.py re-exports from here.

A Tier 3 signal may carry `unrunnable=True` with
`reason="pytest_not_available"` when the resolved interpreter cannot import
pytest. In that case `passed` stays `False`, because an unrunnable tier must
never read as green. This distinction exists so a reader can tell "the tests
failed" apart from "the tests never ran".
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_execution(git_diff_text: str, pre_head: str, config: dict,
                     project_root: Path) -> dict:
    """Run tiered verification on changed files.

    Returns dict with: verified, tier_reached, tiers_passed, tiers_failed,
    tiers_skipped, signals, duration_s, receipt_id, commit_sha, task_id.
    """
    budget = config.get("execution_verification_timeout_s", 30)
    enabled_tiers = set(config.get("execution_verification_tiers", [0, 1, 2, 3]))
    task = config.get("_current_task", {})
    # Which call site is verifying. Defaults to "build" so every existing
    # caller keeps the build-path file selection with zero config changes.
    verification_context = config.get("_verification_context", "build")

    t0 = time.monotonic()
    signals = []
    tiers_passed = []
    tiers_failed = []
    tiers_skipped = []
    # WHY A REASON PER SKIP. `tiers_skipped` conflated three different facts:
    # the tier ran with nothing eligible, the tier was switched off by config,
    # and the tier never ran because the time budget expired. Merged into one
    # token they are indistinguishable — which is exactly why "has tier 2 ever
    # actually executed?" could not be answered from 3,342 receipts without
    # reading the caller's config by hand.
    skip_reasons: dict = {}

    def _skip(tier: int, why: str) -> None:
        """Record a skip WITH its cause. A tier must never vanish silently."""
        if tier not in tiers_skipped:
            tiers_skipped.append(tier)
        skip_reasons[str(tier)] = why

    # Get clean file paths
    changed = _get_changed_files(git_diff_text, pre_head, project_root,
                                 context=verification_context)

    def remaining():
        return max(0, budget - (time.monotonic() - t0))

    # ── Tier 0: diff non-empty ──
    if 0 in enabled_tiers:
        sig = _tier0_diff_nonempty(changed)
        signals.append(sig)
        (tiers_passed if sig["passed"] else tiers_failed).append(0)
    else:
        _skip(0, "not enabled")
    if 1 in enabled_tiers and remaining() <= 0:
        # Budget expired BEFORE this tier ran. This previously fell
        # through every branch: the tier appeared in NO list —
        # neither passed, failed, nor skipped. A verification tier
        # that simply vanishes reads as a clean run.
        _skip(1, "time budget expired")
    elif 1 in enabled_tiers:
        t1_sigs = _tier1_syntax_check(changed, project_root, remaining())
        signals.extend(t1_sigs)
        if t1_sigs:
            # A signal marked INSUFFICIENT is neither a pass nor a fail: the
            # check could not be RUN, so it says nothing about the file. It is
            # excluded from the verdict rather than counted as a failure.
            # See _tier1_syntax_check — py_compile under a chflags-locked
            # directory cannot write __pycache__, and the old all() read that
            # as a syntax error, blocking commits over files it never parsed.
            decidable = [s for s in t1_sigs if not s.get("insufficient")]
            if not decidable:
                # EVERY signal was insufficient, so nothing was actually
                # checked. `all([])` is True, so this previously recorded the
                # tier as PASSED -- a verification tier that could not run a
                # single check reporting success. That is the exact shape the
                # `insufficient` state was introduced to prevent, reappearing
                # one line below its own fix: the comment above records that
                # counting insufficient as FAILURE was corrected, and the
                # correction created the vacuous-truth pass.
                #
                # Reachable exactly where the comment says: py_compile under a
                # chflags-locked directory cannot write __pycache__, so every
                # file comes back insufficient at once.
                _skip(1, "all Tier-1 signals were insufficient — nothing could be checked")
            elif all(s["passed"] for s in decidable):
                tiers_passed.append(1)
            else:
                tiers_failed.append(1)
        else:
            _skip(1, "no eligible files")
    elif 1 not in enabled_tiers:
        _skip(1, "not enabled")
    python_path = config.get("python_path")
    if 2 in enabled_tiers and remaining() <= 0:
        # Budget expired BEFORE this tier ran. This previously fell
        # through every branch: the tier appeared in NO list —
        # neither passed, failed, nor skipped. A verification tier
        # that simply vanishes reads as a clean run.
        _skip(2, "time budget expired")
    elif 2 in enabled_tiers:
        py_files = [f for f in changed if f.endswith(".py")]
        t2_sigs = _tier2_import_check(py_files, project_root, remaining(), python_path)
        signals.extend(t2_sigs)
        if t2_sigs:
            if all(s["passed"] for s in t2_sigs):
                tiers_passed.append(2)
            else:
                tiers_failed.append(2)
        else:
            # Enabled but collected nothing — an empty .py diff is not a
            # disabled tier. gt40 lever receipts mislabeled this "not enabled"
            # for months, making a quiet-repo skip look like a config bug.
            _skip(2, "no .py files in diff — nothing to import-check")
    elif 2 not in enabled_tiers:
        _skip(2, "not enabled")
    if 3 in enabled_tiers and remaining() <= 0:
        # Budget expired BEFORE this tier ran. This previously fell
        # through every branch: the tier appeared in NO list —
        # neither passed, failed, nor skipped. A verification tier
        # that simply vanishes reads as a clean run.
        _skip(3, "time budget expired")
    elif 3 in enabled_tiers:
        t3_sigs = _tier3_test_execution(changed, task, project_root, remaining(), python_path)
        signals.extend(t3_sigs)
        if t3_sigs:
            if all(s["passed"] for s in t3_sigs):
                tiers_passed.append(3)
            else:
                tiers_failed.append(3)
        else:
            _skip(3, "no test files discovered for the changed files")
    elif 3 not in enabled_tiers:
        _skip(3, "not enabled")
    runtime_checks = config.get("execution_verification_runtime_checks", [])
    runtime_budget = config.get("execution_verification_runtime_timeout_s", 15)
    if 4 in enabled_tiers and runtime_checks:
        t4_sigs = _tier4_runtime_check(runtime_checks, project_root, runtime_budget)
        signals.extend(t4_sigs)
        if t4_sigs:
            if all(s["passed"] for s in t4_sigs):
                tiers_passed.append(4)
            else:
                tiers_failed.append(4)
        else:
            _skip(4, "runtime checks configured but produced no signals")
    elif 4 not in enabled_tiers:
        _skip(4, "not enabled")
    elif not runtime_checks:
        _skip(4, "no runtime checks configured")
    if 5 in enabled_tiers and remaining() <= 0:
        # Budget expired BEFORE this tier ran. This previously fell
        # through every branch: the tier appeared in NO list —
        # neither passed, failed, nor skipped. A verification tier
        # that simply vanishes reads as a clean run.
        _skip(5, "time budget expired")
    elif 5 in enabled_tiers:
        baseline_path = project_root / ".brain" / "driver" / "outcome_baseline.json"
        plan_path = _find_recent_plan(project_root)
        if baseline_path.exists() and plan_path:
            t5_sigs = _tier5_outcome_check(
                plan_path.read_text(), project_root, remaining(), baseline_path,
            )
            signals.extend(t5_sigs)
            if t5_sigs:
                if all(s["passed"] for s in t5_sigs):
                    tiers_passed.append(5)
                else:
                    tiers_failed.append(5)
                # Record goal progress (best-effort)
                try:
                    from .goal_tracker import record_goal_attempt
                    record_goal_attempt(str(plan_path), {}, t5_sigs, project_root)
                except Exception:
                    logger.debug("Swallowed exception in verify_execution", exc_info=True)
                    pass
                # Frontier 4: report Tier 5 outcome to the flywheel — every
                # outcome verification becomes a CSR claim. Best-effort.
                try:
                    from ..flywheel import Flywheel
                    fw = Flywheel(project_root / ".brain")
                    step = f"tier5:{(task or {}).get('id', 'unknown')}"
                    if 5 in tiers_passed:
                        fw.record_survived(phase="ground_tier5", step=step)
                    else:
                        failed_signal = next(
                            (s for s in t5_sigs if not s.get("passed")), {}
                        )
                        # The signal NAME is a stable identifier by
                        # construction, unlike a stack trace or prose, so it is
                        # safe to ask how many sessions have seen it. Without
                        # this the ticket asserts "tier5 outcome failed" with
                        # no way to tell a one-off from a standing problem.
                        signal_name = str(
                            failed_signal.get("name", "tier5 outcome failed")
                        )
                        fw.file_ticket(
                            step=step,
                            error=signal_name,
                            logs=json.dumps(failed_signal, default=str)[:1500],
                            phase="ground_tier5",
                            evidence_pattern=signal_name,
                        )
                except Exception:
                    logger.debug("Swallowed exception in verify_execution", exc_info=True)
                    pass  # flywheel hook is best-effort
            else:
                _skip(5, "not enabled")
        else:
            _skip(5, "not enabled")
    elif 5 not in enabled_tiers:
        _skip(5, "not enabled")

    duration = round(time.monotonic() - t0, 2)
    verified = len(tiers_failed) == 0 and len(tiers_passed) > 0

    # Receipt provenance
    commit_sha = ""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                           text=True, timeout=3, cwd=str(project_root))
        commit_sha = r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        logger.debug("Swallowed exception in verify_execution", exc_info=True)
        pass

    receipt_content = json.dumps(signals, sort_keys=True, default=str) + str(time.time())
    receipt_id = hashlib.sha256(receipt_content.encode()).hexdigest()[:16]

    return {
        "verified": verified,
        "tier_reached": max(tiers_passed) if tiers_passed else -1,
        "tiers_passed": tiers_passed,
        "tiers_failed": tiers_failed,
        "tiers_skipped": tiers_skipped,
        "skip_reasons": skip_reasons,
        "signals": signals,
        "duration_s": duration,
        "receipt_id": receipt_id,
        "commit_sha": commit_sha,
        "task_id": task.get("id", "") if task else "",
    }


def build_calibration_dpo(task: dict, response: dict,
                          verification_result: dict) -> dict | None:
    """Build DPO pair: confident-wrong vs honestly-uncertain. Gold quality.

    Returns None if verification passed (no calibration needed).
    """
    if verification_result.get("verified", True):
        return None

    failed = [s for s in verification_result.get("signals", [])
              if not s.get("passed", True)]
    if not failed:
        return None

    issues = []
    for sig in failed:
        check = sig.get("check", "unknown")
        target = sig.get("file", sig.get("module", ""))
        err = sig.get("error", "")
        issues.append(f"{check} failed on {target}" + (f": {err}" if err else ""))

    rejected = response.get("result", "")
    chosen = (
        rejected + "\n\n"
        "Note: verification found issues that need to be addressed:\n"
        + "\n".join(f"- {i}" for i in issues)
    )

    return {
        "prompt": task.get("description", ""),
        "chosen": chosen,
        "rejected": rejected,
        "metadata": {
            "source": "calibration_dpo",
            "quality": "gold",
            "verification_failures": [s.get("check", "") for s in failed],
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    }


def detect_runtime_checks(project_root: Path) -> list[dict]:
    """Auto-detect Tier 4 runtime checks based on project type.

    Detects:
      - pyproject.toml with uvicorn/fastapi → FastAPI health check
      - package.json with "start" script → Node.js health check
      - Dockerfile with EXPOSE → Docker health check
    """
    checks = []
    root = Path(project_root)

    # FastAPI / Uvicorn detection
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text().lower()
            if "uvicorn" in content or "fastapi" in content:
                checks.append({
                    "type": "http_health",
                    "cmd": [sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", "0"],
                    "url": "/health",
                    "expect_status": 200,
                    "startup_wait_s": 8,
                    "detected_from": "pyproject.toml",
                })
        except Exception:
            logger.debug("Swallowed exception in detect_runtime_checks", exc_info=True)
            pass

    # Node.js detection
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            if "start" in scripts:
                checks.append({
                    "type": "http_health",
                    "cmd": ["npm", "start"],
                    "url": "/",
                    "expect_status": 200,
                    "startup_wait_s": 10,
                    "detected_from": "package.json",
                })
        except Exception:
            logger.debug("Swallowed exception in detect_runtime_checks", exc_info=True)
            pass

    # Dockerfile detection
    dockerfile = root / "Dockerfile"
    if dockerfile.exists():
        try:
            import re
            content = dockerfile.read_text()
            expose_match = re.search(r'EXPOSE\s+(\d+)', content)
            if expose_match:
                port = int(expose_match.group(1))
                checks.append({
                    "type": "http_health",
                    "cmd": ["docker", "run", "--rm", "-p", f"0:{port}",
                            "--name", "ground-check", "."],
                    "url": "/",
                    "expect_status": 200,
                    "startup_wait_s": 15,
                    "detected_from": "Dockerfile",
                })
        except Exception:
            logger.debug("Swallowed exception in detect_runtime_checks", exc_info=True)
            pass

    return checks


# ---------------------------------------------------------------------------
# File extraction
# ---------------------------------------------------------------------------

def _get_submodule_paths(project_root: Path) -> set[str]:
    """Return submodule directory paths from .gitmodules.

    Submodule pointer changes (mode 160000) appear in ``git diff --name-only``
    as just the submodule directory name (e.g. ``nucleus-mcp``). These are
    gitlink pointer bumps, NOT file edits. Counting them as changed files
    produces false-positive Tier 0 passes when the build touched nothing
    real but the submodule pointer moved (fw-1785907505).
    """
    paths: set[str] = set()
    try:
        r = subprocess.run(
            ["git", "config", "--file", ".gitmodules", "--get-regexp", "path"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_root),
        )
        for line in r.stdout.strip().splitlines():
            if line.strip():
                # xvendor catch (agy): split(maxsplit=1) to handle submodule
                # paths containing spaces (e.g. 'vendor/my submodule')
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    paths.add(os.path.normpath(parts[-1].strip()))
    except Exception:
        logger.debug("Swallowed exception in _get_submodule_paths", exc_info=True)
        pass
    return paths


_CHANGED_FILES_CONTEXTS = ("build", "pre_commit")


def _get_changed_files(git_diff_text: str, pre_head: str,
                       project_root: Path, *,
                       context: str = "build") -> list[str]:
    """Extract changed file paths from git state.

    Unions four sources: unstaged (``git diff``), staged
    (``git diff --cached``), working tree vs ``pre_head`` (``git diff
    <pre_head>``, only when ``pre_head`` is set), and untracked-but-not-
    ignored files (``git ls-files --others --exclude-standard``, narrowed to
    genuinely-new paths when ``pre_head`` is set). ``git_diff_text`` is
    accepted for signature compatibility with ``verify_execution`` and is NOT
    read — git is queried directly.

    ``context`` names the CALLER, because the two callers want opposite
    submodule-pointer handling:

    ``"build"`` (default)
        ``build_runner._run_verify_stage``. Submodule paths are filtered out
        of *every* source. A gitlink bump (mode 160000) is a pointer move, not
        a file edit, and nothing in a build is deliberate — the vendor agent
        may bump a pointer as a side effect. INVARIANT (fw-1785907505): a
        build whose only diff is a submodule-pointer bump yields ``[]`` here
        and therefore still FAILS Tier 0 (diff nonempty). Do not relax the
        filter in this context; the false-positive PROVEN verdict it prevents
        is the whole reason the filter exists.

    ``"pre_commit"``
        ``ground.run_ground`` → ``verify_execution``. STAGED submodule paths
        are retained (fw-1786069497): a staged pointer bump was explicitly
        ``git add``ed, so it IS the change being committed. Filtering it left
        Tier 0 with an empty set and blocked legitimate submodule-sync commits
        behind a misleading "Syntax verification failed". Only the staged
        source is exempted — the unstaged and ``pre_head`` sources stay
        filtered in BOTH contexts, so an *unstaged* pointer bump still cannot
        satisfy Tier 0 anywhere.

    Raises ``ValueError`` for any other ``context``. Returns ``[]`` when git
    is unavailable or nothing changed.
    """
    if context not in _CHANGED_FILES_CONTEXTS:
        raise ValueError(
            f"_get_changed_files: unknown context {context!r} "
            f"(expected one of {', '.join(map(repr, _CHANGED_FILES_CONTEXTS))})"
        )

    files = set()

    def _run_git(*args):
        try:
            r = subprocess.run(
                ["git"] + list(args),
                capture_output=True, text=True, timeout=5,
                cwd=str(project_root),
            )
            return [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
        except Exception:
            logger.debug("Swallowed exception in _get_changed_files", exc_info=True)
            return []

    # Submodule pointer changes (mode 160000) are NOT file edits — exclude
    # them so Tier 0 (diff nonempty) doesn't false-positive on a build that
    # touched nothing real but the submodule pointer moved (fw-1785907505).
    submodule_paths = _get_submodule_paths(project_root)

    def _filter_submodules(paths: list[str]) -> list[str]:
        return [p for p in paths if p not in submodule_paths]

    # Unstaged
    files.update(_filter_submodules(_run_git("diff", "--name-only")))
    # Staged. In the pre_commit context a staged submodule-pointer bump is a
    # deliberate, explicitly-`git add`ed change — the very thing being
    # committed — so it must count toward Tier 0 rather than be filtered away
    # (fw-1786069497). Under "build" nothing is explicit, so the filter stays.
    staged = _run_git("diff", "--cached", "--name-only")
    files.update(staged if context == "pre_commit" else _filter_submodules(staged))
    # Changes since pre_head (working tree vs pre_head commit).
    # CONCURRENT COMMIT CONTAMINATION FIX (fw-1786034381): the old code used
    # `git log --name-only pre_head..HEAD` which captures ALL commits between
    # pre_head and HEAD — including commits from OTHER concurrent sessions.
    # This caused false FAILED verdicts when a single-task build's diff was
    # contaminated by unrelated files from other sessions' commits.
    # `git diff --name-only pre_head` compares pre_head to the WORKING TREE
    # (not HEAD), so it only sees changes in THIS session's working tree:
    #   - vendor edits (unstaged/staged) ✓
    #   - vendor commits (working tree reflects new HEAD) ✓
    #   - other sessions' commits (NOT in this working tree) ✗ correctly excluded
    if pre_head:
        files.update(_filter_submodules(
            _run_git("diff", "--name-only", pre_head)))
    # Untracked but not gitignored (newly-created files never staged/committed).
    # Scope check (fw-1785843850): enumerate ALL untracked files unconditionally
    # produced false-positives — a build that touched one real file had its
    # VERIFY tier-2 fail because ~100 PRE-EXISTING untracked files (backup
    # dirs, model weights, doc summaries) sitting in the working tree long
    # before the build started were swept in. The original fix this block
    # absorbed (newly-created untracked files must stay visible to
    # verification) is preserved: when pre_head is available we filter the
    # untracked set to only files that did NOT exist in the tree at pre_head
    # (genuinely NEW since the build started) via `git cat-file -e`. When
    # pre_head is empty there is no comparison point, so we keep the
    # unconditional enumeration (the function's pre-existing behavior) —
    # without pre_head every untracked file is plausibly build-related.
    untracked = _run_git("ls-files", "--others", "--exclude-standard")
    if pre_head:
        genuinely_new = []
        for relpath in untracked:
            # git cat-file -e exits 0 if the path exists at pre_head, non-zero
            # otherwise. A path that already existed (tracked OR untracked) at
            # pre_head is NOT a build artifact and is excluded. cat-file -e on
            # an untracked-at-pre_head path fails the same as for a never-tracked
            # one — both mean "not in the pre_head tree" — which is exactly the
            # signal we want: the file is new since pre_head.
            r = subprocess.run(
                ["git", "cat-file", "-e", f"{pre_head}:{relpath}"],
                capture_output=True, timeout=5, cwd=str(project_root),
            )
            if r.returncode != 0:
                genuinely_new.append(relpath)
        files.update(genuinely_new)
    else:
        files.update(untracked)

    return sorted(files)


# ---------------------------------------------------------------------------
# Tier implementations
# ---------------------------------------------------------------------------

def _tier0_diff_nonempty(changed_files: list[str]) -> dict:
    return {
        "tier": 0,
        "check": "diff_nonempty",
        "passed": len(changed_files) > 0,
        "files_count": len(changed_files),
    }


# ---------------------------------------------------------------------------
# Target-file presence check
# ---------------------------------------------------------------------------

# Mirror roots: the same package is vendored under two roots in this repo.
# A declared path under one root names the same file as a changed path under
# the other, so both reduce to a common form before comparison.
_TARGET_MIRROR_ROOTS = (
    "mcp-server-nucleus/src/", "nucleus-mcp/src/",
    "mcp-server-nucleus/", "nucleus-mcp/",
)


def _strip_target_mirror_root(path: str) -> str:
    """Strip mirror-root prefixes and leading ``./`` for path comparison."""
    p = (path or "").strip()
    while p.startswith("./"):
        p = p[2:]
    p = p.strip("/")
    for root in _TARGET_MIRROR_ROOTS:
        if p.startswith(root):
            return p[len(root):]
    return p


def _target_paths_match(declared: str, changed: str) -> bool:
    """True when *declared* and *changed* name the same file.

    Component-wise suffix match in both directions, so a declared path at any
    depth matches the working-tree path git reports (mirror-root tolerant).
    """
    a = _strip_target_mirror_root(declared)
    b = _strip_target_mirror_root(changed)
    if a == b:
        return True
    pa, pb = a.split("/"), b.split("/")
    shorter, longer = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
    return longer[-len(shorter):] == shorter


def _target_path_exists(declared: str, project_root: Path) -> bool:
    """True if *declared* (or its mirror equivalent) exists on disk."""
    p = Path(declared)
    if not p.is_absolute():
        p = project_root / declared
    if p.exists():
        return True
    stripped = _strip_target_mirror_root(declared)
    for root in _TARGET_MIRROR_ROOTS:
        candidate = project_root / root / stripped
        if candidate.exists():
            return True
    return False


def verify_target_files_present(
    declared_paths, changed_files, project_root: Path,
) -> dict:
    """Verify that each declared target file was actually modified.

    THE DEFECT this closes: a vendor that drops its tasked target files —
    reports ``status == "ok"`` and ``produced_output is True`` without
    touching the files it was supposed to — still passed the fail-stop
    predicate, because neither field proves the declared target files were
    touched.  Tier 0 (diff non-empty) only checks that *something* changed,
    not that the *right* files changed.

    For each declared path:

    * **MODIFIED** — the path (or its mirror equivalent) appears in
      *changed_files*.  The vendor did its job for this file.
    * **NOT_MODIFIED** — the path does NOT appear in *changed_files* but
      EXISTS on disk.  The file was there, the vendor was supposed to edit
      it, and didn't.  This is a hard failure.
    * **ABSENT** — the path does NOT appear in *changed_files* and does NOT
      exist on disk.  This is the "confirmed absent-for-reason" case: the
      absence is confirmed, and the reason is that the file genuinely does
      not exist (it may have been mentioned as context, was supposed to be
      deleted, or is a path that doesn't resolve).  Not a failure.

    Path matching is component-wise suffix tolerant to handle the
    mirror-root case (the same file exists under ``mcp-server-nucleus/src/``
    and ``nucleus-mcp/src/``).

    Returns a signal dict:

    * ``check``        — ``"target_files_present"``
    * ``passed``       — ``True`` iff no existing target file was left unmodified
    * ``modified``     — list of declared paths that were modified
    * ``not_modified``  — list of declared paths that exist but weren't modified
    * ``absent``       — list of declared paths that don't exist (absent-for-reason)
    """
    declared_list = sorted(declared_paths or [])
    if not declared_list:
        return {
            "check": "target_files_present",
            "passed": True,
            "modified": [],
            "not_modified": [],
            "absent": [],
            "reason": "no declared target files — nothing to verify",
        }

    changed_set = set(changed_files or [])
    modified = []
    not_modified = []
    absent = []

    for declared_path in declared_list:
        if any(_target_paths_match(declared_path, c) for c in changed_set):
            modified.append(declared_path)
        elif _target_path_exists(declared_path, project_root):
            not_modified.append(declared_path)
        else:
            absent.append(declared_path)

    return {
        "check": "target_files_present",
        "passed": len(not_modified) == 0,
        "modified": modified,
        "not_modified": not_modified,
        "absent": absent,
    }


# Extension → (command_template, description)
# {file} is replaced with absolute path
_SYNTAX_CHECKS = {
    ".py": ([sys.executable, "-m", "py_compile", "{file}"], "py_compile"),
    ".js": (["node", "--check", "{file}"], "node_check"),
    ".mjs": (["node", "--check", "{file}"], "node_check"),
    ".sh": (["bash", "-n", "{file}"], "bash_syntax"),
    ".bash": (["bash", "-n", "{file}"], "bash_syntax"),
}


def _tier1_syntax_check(changed_files: list[str], project_root: Path,
                        budget_s: float) -> list[dict]:
    """Syntax check each changed file by extension."""
    signals = []
    t0 = time.monotonic()

    for relpath in changed_files:
        if time.monotonic() - t0 > budget_s:
            break

        fpath = project_root / relpath
        if not fpath.exists():
            continue

        ext = fpath.suffix.lower()

        # Claude Code Workflow scripts are an async function BODY, not a module:
        # top-level `return`/`await` are legal and `export const meta` is how the
        # harness reads metadata. Bare `node --check` rejects every one of them
        # (2026-09-23: blocked all four department workflows, and the committed
        # roadmap-redteam.js fails the same way). Check them as the harness runs
        # them — wrapped in an async IIFE with `export` stripped.
        if ext == ".js" and ".claude/workflows/" in relpath.replace("\\", "/"):
            sig = _check_workflow_script(fpath, relpath)
            sig["tier"] = 1
            signals.append(sig)

        # Python: py_compile
        elif ext in _SYNTAX_CHECKS:
            cmd_template, check_name = _SYNTAX_CHECKS[ext]
            cmd = [c.replace("{file}", str(fpath)) for c in cmd_template]
            sig = _run_check(cmd, check_name, relpath, timeout=5)
            sig["tier"] = 1
            # "Could not check" is NOT "check failed".
            #
            # py_compile writes __pycache__ NEXT TO the source. Under a
            # hypervisor-locked (chflags uchg) directory that write raises
            # PermissionError and the file is never parsed. The old code
            # reported it as "GROUND: Syntax verification failed. Commit
            # blocked." — naming a syntax error in a file whose syntax was
            # never examined. It blocked three commits in one day, every time
            # pointing at a perfectly valid file, and the suggested remedy
            # ("fix syntax errors above") could not possibly work.
            #
            # This is the pass/fail collapse the substrate exists to name: an
            # unknown coerced into a verdict. INSUFFICIENT is the honest value,
            # and it is excluded from the tier verdict rather than blocking.
            if not sig.get("passed"):
                err = str(sig.get("error") or "")
                if ("Operation not permitted" in err or "Permission denied" in err
                        or "Errno 1" in err or "Errno 13" in err):
                    sig["insufficient"] = True
                    sig["state"] = "INSUFFICIENT"
                    sig["error"] = (
                        f"could not RUN {check_name} (write blocked — likely a "
                        f"locked directory). Syntax NOT verified. This is not a "
                        f"failure: {err}"
                    )
            signals.append(sig)

        # JSON: load it
        elif ext == ".json":
            sig = _check_json(fpath, relpath)
            sig["tier"] = 1
            signals.append(sig)

        # YAML: safe_load
        elif ext in (".yaml", ".yml"):
            sig = _check_yaml(fpath, relpath)
            sig["tier"] = 1
            signals.append(sig)

    return signals


def _tier2_import_check(py_files: list[str], project_root: Path,
                        budget_s: float, python_path: str = None) -> list[dict]:
    """Try importing each changed Python module."""
    signals = []
    t0 = time.monotonic()

    for relpath in py_files[:5]:  # cap at 5 files
        if time.monotonic() - t0 > budget_s:
            break

        # Skip __init__ and test files
        name = Path(relpath).name
        if name == "__init__.py" or name.startswith("test_"):
            continue

        # Resolve Python per-file: explicit override > nearest venv > system
        python = python_path or _find_venv_python(relpath, project_root) or sys.executable

        parts = Path(relpath).parts
        env = dict(__import__("os").environ)

        if len(parts) > 2:
            cwd = str(project_root / parts[0])
            subrel_parts = parts[1:]
            env["PYTHONPATH"] = cwd + ":" + str(project_root)
        else:
            cwd = str(project_root)
            subrel_parts = parts
            env["PYTHONPATH"] = str(project_root)

        # Process and sanitize subrel components & perform identifier checking
        sanitized_comps = []
        valid = True
        for i, part in enumerate(subrel_parts):
            comp = part[:-3] if (i == len(subrel_parts) - 1 and part.endswith(".py")) else part
            sanitized = comp.replace("-", "_")
            if not sanitized.isidentifier():
                valid = False
                break
            sanitized_comps.append(sanitized)

        if not valid or not sanitized_comps:
            continue

        module = ".".join(sanitized_comps)

        # Build directory-only package registration fallback paths
        fallback_dirs = []
        curr = Path(cwd)
        for j, part in enumerate(subrel_parts[:-1]):
            curr = curr / part
            if curr.is_dir():
                fallback_dirs.append((str(curr), j))

        import_script = f"""import sys, importlib

module_name = {repr(module)}
fallback_dirs = {repr(fallback_dirs)}
sanitized_comps = {repr(sanitized_comps)}

try:
    importlib.import_module(module_name)
except (ImportError, ModuleNotFoundError):
    imported = False
    for d, j in fallback_dirs:
        if d not in sys.path:
            sys.path.insert(0, d)
        rel_mod = ".".join(sanitized_comps[j + 1:])
        if rel_mod:
            try:
                importlib.import_module(rel_mod)
                imported = True
                break
            except (ImportError, ModuleNotFoundError):
                pass
    if not imported:
        raise
"""

        cmd = [python, "-c", import_script]
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5,
                cwd=cwd, env=env,
            )
            signals.append({
                "tier": 2,
                "check": "import",
                "module": module,
                "passed": r.returncode == 0,
                "error": r.stderr.strip()[-200:] if r.returncode != 0 else "",
            })
        except subprocess.TimeoutExpired:
            signals.append({
                "tier": 2, "check": "import", "module": module,
                "passed": False, "error": "timeout",
            })
        except Exception as e:
            logger.debug("Swallowed exception in _tier2_import_check", exc_info=True)
            signals.append({
                "tier": 2, "check": "import", "module": module,
                "passed": False, "error": str(e)[:200],
            })

    return signals


# A full aggregate pass may run up to 60s (see timeout below). Attempting it
# when the caller's overall Tier 3 budget is small (e.g. a short-lived CI
# check) would either starve the per-file phase of its own headroom or get
# truncated before producing a useful signal. 30 mirrors the existing
# per-file timeout cap (``min(30, budget_s)``) below: only once the caller
# affords strictly more than one per-file run's worth of time is a second,
# whole-directory pass worth attempting.
_TIER3_AGGREGATE_MIN_BUDGET_S = 30.0


def _references_changed_stem(text: str, stems: set[str]) -> bool:
    """Cheap static relevance check: does ``text`` mention any of ``stems``
    as a whole word?

    Used to decide whether a discovered (not task-specified, not itself a
    changed file) failing test file is plausibly related to the change, or
    is a pre-existing failure the verifier merely happened to run.
    """
    for stem in stems:
        if not stem:
            continue
        if re.search(rf"\b{re.escape(stem)}\b", text):
            return True
    return False


def _tier3_test_execution(changed_files: list[str], task: dict,
                          project_root: Path, budget_s: float,
                          python_path: str = None) -> list[dict]:
    """Run tests related to changed files.

    Two collection modes are used (fw-1786151929):

    1. **Per-file** (explicit-file collection): runs each test file
       individually via ``pytest <file>``. This is fast and insulated
       from cross-module interactions, but is structurally blind to
       import-order, sys.modules, fixture-scope, and other cross-module
       interaction failures.

    2. **Aggregate** (directory collection): after all per-file tests
       pass, runs ``pytest tests/ -k <filter> --continue-on-collection-errors``
       to collect the full directory. This catches cross-module
       interactions that per-file collection cannot see. Disagreement
       between per-file green and aggregate red is itself the finding
       and surfaces as a distinct signal with ``aggregate_disagreement: True``.
       The aggregate pass only runs when the caller's budget affords it
       (``budget_s > _TIER3_AGGREGATE_MIN_BUDGET_S``); a tight budget skips
       straight to returning the per-file signals.

    Each signal carries a ``collection_mode`` field (``"per_file"`` or
    ``"aggregate"``) so the verdict card can distinguish them.

    **Relevance guard**: a discovered test file (one that is neither
    task-specified nor itself among ``changed_files``) that fails is only
    treated as a genuine regression if its source text mentions one of the
    changed files' stems as a whole word. Otherwise it is reclassified as
    ``classification: "pre_existing_candidate"`` — ``passed`` is flipped to
    ``True`` (it does not fail the verdict) but ``warning: True`` and
    ``test_returncode`` preserve the real outcome for human review. A test
    file that IS task-specified or itself a changed file is always treated
    as relevant and never reclassified.
    """
    signals = []
    test_files = set()

    # Strategy 1: task specifies a test file
    task_test = task.get("test_file", "")
    if task_test and (project_root / task_test).exists():
        test_files.add(task_test)

    # Strategy 2: discover test_<name>.py for each changed file
    for relpath in changed_files:
        if not relpath.endswith(".py"):
            continue
        p = Path(relpath)
        name = p.name
        stem = p.stem
        if name.startswith("test_"):
            # Changed file IS a test — run it directly
            if (project_root / relpath).exists():
                test_files.add(relpath)
            continue

        candidate_dirs = [p.parent, p.parent / "tests", Path("tests")]
        for d in candidate_dirs:
            real_dir = project_root / d
            if not real_dir.is_dir():
                continue
            exact = d / f"test_{name}"
            if (project_root / exact).exists():
                test_files.add(str(exact))
            # Underscore boundary prevents prefix-only matches: stem "cli" must
            # not match "test_clinical.py", only "test_cli_*.py".
            for match in real_dir.glob(f"test_{stem}_*.py"):
                test_files.add(str(d / match.name))

    if not test_files:
        return []

    exact_basenames = {f"test_{Path(f).name}" for f in changed_files if f.endswith(".py")}

    def _sort_key(path_str):
        return (0 if Path(path_str).name in exact_basenames else 1, path_str)

    # Relevance guard bookkeeping: a test file is always relevant (never
    # reclassified as pre_existing_candidate) if it was explicitly
    # task-specified or is itself one of the changed files.
    always_relevant_files = set(changed_files)
    if task_test:
        always_relevant_files.add(task_test)
    changed_stems = {Path(f).stem for f in changed_files if f.endswith(".py")}

    t0 = time.monotonic()
    per_file_all_passed = True
    for test_file in sorted(test_files, key=_sort_key)[:3]:  # cap at 3 test files
        if time.monotonic() - t0 > budget_s:
            break

        python = python_path or _find_venv_python(test_file, project_root) or sys.executable
        cmd = [python, "-m", "pytest", test_file, "-x",
               "-q", "--no-header", "-p", "no:timeout"]
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=min(30, budget_s),
                cwd=str(project_root),
            )
            combined = (r.stdout or "") + (r.stderr or "")
            sig = {
                "tier": 3,
                "check": "pytest",
                "file": test_file,
                "passed": r.returncode == 0,
                "output": combined.strip()[-300:],
                "duration_s": round(time.monotonic() - t0, 1),
                "python": python,
                "collection_mode": "per_file",
            }
            if re.search(r"no module named pytest", combined, re.IGNORECASE):
                sig["passed"] = False
                sig["unrunnable"] = True
                sig["reason"] = "pytest_not_available"

            # Capture the REAL outcome before the relevance guard can flip
            # ``passed`` back to True — the aggregate pass gating below must
            # reflect what actually happened, not the verdict-facing
            # reclassification.
            raw_failed = not sig["passed"]

            # Relevance guard: a failing DISCOVERED test file (not
            # task-specified, not itself a changed file) that never
            # mentions any changed stem is a pre-existing candidate, not a
            # regression attributable to this change. Never applies to the
            # unrunnable case (pytest itself missing is never "irrelevant").
            if (raw_failed and not sig.get("unrunnable")
                    and test_file not in always_relevant_files):
                try:
                    test_text = (project_root / test_file).read_text(
                        encoding="utf-8", errors="ignore")
                except OSError:
                    test_text = None
                if test_text is not None and not _references_changed_stem(
                        test_text, changed_stems):
                    sig["classification"] = "pre_existing_candidate"
                    sig["warning"] = True
                    sig["test_returncode"] = r.returncode
                    sig["passed"] = True

            signals.append(sig)
            if raw_failed:
                per_file_all_passed = False
        except subprocess.TimeoutExpired:
            signals.append({
                "tier": 3, "check": "pytest", "file": test_file,
                "passed": False, "error": "timeout",
                "python": python,
                "collection_mode": "per_file",
            })
            per_file_all_passed = False
        except Exception as e:
            logger.debug("Swallowed exception in _tier3_test_execution", exc_info=True)
            signals.append({
                "tier": 3, "check": "pytest", "file": test_file,
                "passed": False, "error": str(e)[:200],
                "python": python,
                "collection_mode": "per_file",
            })
            per_file_all_passed = False

    # ── Aggregate pass (fw-1786151929) ─────────────────────────────────────
    # After all per-file tests pass, run ONE aggregate pass over the test
    # directory to catch cross-module interactions (sys.modules pollution,
    # import-order dependencies, fixture-scope conflicts) that per-file
    # collection cannot see. Skip if any per-file test already failed —
    # the aggregate won't add signal value in that case. Also skip when the
    # caller's overall budget is too tight to afford a second, potentially
    # up-to-60s pass (see _TIER3_AGGREGATE_MIN_BUDGET_S above).
    if (per_file_all_passed and (time.monotonic() - t0) < budget_s
            and budget_s > _TIER3_AGGREGATE_MIN_BUDGET_S):
        # Determine the test directory from the first test file
        first_test = sorted(test_files, key=_sort_key)[0]
        test_dir = str(Path(first_test).parent)
        if test_dir == ".":
            test_dir = "tests"
        # Build a -k filter from the test file stems to keep the aggregate
        # run focused on the same tests, not the entire suite
        stems = [Path(f).stem for f in sorted(test_files, key=_sort_key)[:3]]
        # Convert test_foo -> foo to match test function names
        k_terms = [s[5:] if s.startswith("test_") else s for s in stems]
        k_filter = " or ".join(k_terms[:3])
        python = python_path or _find_venv_python(first_test, project_root) or sys.executable
        cmd = [
            python, "-m", "pytest", test_dir,
            "-k", k_filter,
            "-q", "--no-header", "-p", "no:timeout",
            "--continue-on-collection-errors",
            "--tb=no",
        ]
        try:
            remaining = max(5, budget_s - (time.monotonic() - t0))
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=min(60, remaining),
                cwd=str(project_root),
            )
            combined = (r.stdout or "") + (r.stderr or "")
            agg_passed = r.returncode == 0
            sig = {
                "tier": 3,
                "check": "pytest",
                "file": f"{test_dir}/ (aggregate)",
                "passed": agg_passed,
                "output": combined.strip()[-300:],
                "duration_s": round(time.monotonic() - t0, 1),
                "python": python,
                "collection_mode": "aggregate",
            }
            # If per-file passed but aggregate failed, flag the disagreement
            if not agg_passed and per_file_all_passed:
                sig["aggregate_disagreement"] = True
                sig["reason"] = "per_file_passed_aggregate_failed"
            signals.append(sig)
        except subprocess.TimeoutExpired:
            signals.append({
                "tier": 3, "check": "pytest",
                "file": f"{test_dir}/ (aggregate)",
                "passed": False, "error": "timeout",
                "python": python,
                "collection_mode": "aggregate",
            })
        except Exception as e:
            logger.debug("Swallowed exception in _tier3_test_execution", exc_info=True)
            signals.append({
                "tier": 3, "check": "pytest",
                "file": f"{test_dir}/ (aggregate)",
                "passed": False, "error": str(e)[:200],
                "python": python,
                "collection_mode": "aggregate",
            })
    else:
        # Record WHY the aggregate pass was skipped so the verdict card
        # can distinguish "not run" from "ran and passed/failed". Without
        # this the skip was silently unrecorded — a skipped tier-3
        # aggregate check left no trace in the signal list.
        if not per_file_all_passed:
            skip_reason = "per_file_failed"
        elif (time.monotonic() - t0) >= budget_s:
            skip_reason = "budget_exhausted"
        else:
            skip_reason = "budget_too_tight"
        signals.append({
            "tier": 3,
            "check": "pytest",
            "file": "(aggregate)",
            "passed": True,
            "skipped": True,
            "reason": skip_reason,
            "collection_mode": "aggregate",
        })

    return signals


# ---------------------------------------------------------------------------
# Tier 4: Runtime verification (The Mann-Killer)
# ---------------------------------------------------------------------------

def _tier4_runtime_check(checks: list[dict], project_root: Path,
                         budget_s: float) -> list[dict]:
    """Start a server, hit endpoints, verify responses, kill server.

    Check types:
      http_health  — GET url, check status code
      http_json    — GET/POST url, validate response keys
      process_exit — run command, check exit code
    """
    import re
    signals = []
    t0 = time.monotonic()

    for check in checks:
        if time.monotonic() - t0 > budget_s:
            break

        check_type = check.get("type", "")
        remaining = max(0, budget_s - (time.monotonic() - t0))

        if check_type == "process_exit":
            sig = _tier4_process_exit(check, project_root, remaining)
            sig["tier"] = 4
            signals.append(sig)
            continue

        # http_health or http_json — need to start a server
        cmd = list(check.get("cmd", []))
        if not cmd:
            continue

        # Resolve bare "python" to nearest venv Python
        cwd_rel = check.get("cwd", "")
        if cmd[0] in ("python", "python3"):
            resolved = _find_venv_python(cwd_rel, project_root) if cwd_rel else None
            if resolved:
                cmd[0] = resolved

        cwd = str(project_root / cwd_rel) if cwd_rel else str(project_root)
        startup_wait = min(check.get("startup_wait_s", 8), remaining)
        url_path = check.get("url", "/health")
        expect_status = check.get("expect_status", 200)

        proc = None
        port = None
        try:
            # Start server with port 0 for OS auto-assign
            # PYTHONUNBUFFERED ensures startup message isn't stuck in buffer
            import os as _os
            popen_env = {**_os.environ, "PYTHONUNBUFFERED": "1"}
            if cwd_rel:
                popen_env["PYTHONPATH"] = cwd + ":" + str(project_root)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=cwd, text=True, env=popen_env,
            )

            # Poll for port in stdout (exponential backoff)
            port = _poll_for_port(proc, startup_wait)
            if port is None:
                signals.append({
                    "tier": 4, "check": check_type, "url": url_path,
                    "passed": False, "error": "server did not start or announce port",
                })
                continue

            base_url = f"http://127.0.0.1:{port}"

            if check_type == "http_health":
                sig = _tier4_http_check(base_url, url_path, expect_status,
                                        remaining)
                sig["tier"] = 4
                sig["port"] = port
                signals.append(sig)

            elif check_type == "http_json":
                method = check.get("method", "GET")
                expect_keys = check.get("expect_keys", [])
                body = check.get("body")
                sig = _tier4_http_json(base_url, url_path, method,
                                       expect_status, expect_keys, body,
                                       remaining)
                sig["tier"] = 4
                sig["port"] = port
                signals.append(sig)

        except Exception as e:
            logger.debug("Swallowed exception in _tier4_runtime_check", exc_info=True)
            signals.append({
                "tier": 4, "check": check_type, "url": url_path,
                "passed": False, "error": str(e)[:200],
            })
        finally:
            if proc is not None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    return signals


def _poll_for_port(proc: subprocess.Popen, timeout_s: float) -> int | None:
    """Read server stdout looking for a port number. Exponential backoff."""
    import re
    import select

    collected = ""
    deadline = time.monotonic() + timeout_s
    wait = 0.1

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            # Process exited before we found a port
            remaining_out = proc.stdout.read() if proc.stdout else ""
            collected += remaining_out
            break

        # Non-blocking read
        try:
            if hasattr(select, 'select'):
                ready, _, _ = select.select([proc.stdout], [], [], wait)
                if ready:
                    line = proc.stdout.readline()
                    if line:
                        collected += line
            else:
                time.sleep(wait)
        except Exception:
            logger.debug("Swallowed exception in _poll_for_port", exc_info=True)
            time.sleep(wait)

        # Look for HTTP server port: "Uvicorn running on http://127.0.0.1:PORT"
        # Match http(s)://host:PORT specifically to avoid DB connection strings
        m = re.search(r'https?://[\w.]+:(\d{4,5})\b', collected, re.IGNORECASE)
        if not m:
            # Fallback: "Serving HTTP on :: port PORT"
            m = re.search(r'(?:serving|listening)\s+.*port\s+(\d{4,5})\b', collected, re.IGNORECASE)
        if m:
            return int(m.group(1))

        wait = min(wait * 2, 1.0)

    return None


def _tier4_http_check(base_url: str, path: str, expect_status: int,
                      timeout_s: float) -> dict:
    """GET a URL, check status code."""
    import urllib.request
    import urllib.error

    url = base_url + path
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=min(timeout_s, 5)) as resp:
            status = resp.status
            latency_ms = round((time.monotonic() - t0) * 1000)
            return {
                "check": "http_health", "url": url, "status": status,
                "latency_ms": latency_ms,
                "passed": status == expect_status,
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.monotonic() - t0) * 1000)
        return {
            "check": "http_health", "url": url, "status": e.code,
            "latency_ms": latency_ms,
            "passed": e.code == expect_status,
        }
    except Exception as e:
        return {
            "check": "http_health", "url": url,
            "passed": False, "error": str(e)[:200],
        }


def _tier4_http_json(base_url: str, path: str, method: str,
                     expect_status: int, expect_keys: list, body: dict | None,
                     timeout_s: float) -> dict:
    """HTTP request with JSON response key validation."""
    import urllib.request
    import urllib.error

    url = base_url + path
    t0 = time.monotonic()
    try:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if body else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=min(timeout_s, 5)) as resp:
            status = resp.status
            resp_body = json.loads(resp.read().decode())
            latency_ms = round((time.monotonic() - t0) * 1000)
            missing_keys = [k for k in expect_keys if k not in resp_body]
            return {
                "check": "http_json", "url": url, "method": method,
                "status": status, "latency_ms": latency_ms,
                "passed": status == expect_status and not missing_keys,
                "missing_keys": missing_keys if missing_keys else [],
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.monotonic() - t0) * 1000)
        return {
            "check": "http_json", "url": url, "method": method,
            "status": e.code, "latency_ms": latency_ms,
            "passed": False, "error": f"HTTP {e.code}",
        }
    except Exception as e:
        return {
            "check": "http_json", "url": url, "method": method,
            "passed": False, "error": str(e)[:200],
        }


def _tier4_process_exit(check: dict, project_root: Path,
                        budget_s: float) -> dict:
    """Run a command, check exit code."""
    cmd = check.get("cmd", [])
    cwd = str(project_root / check.get("cwd", "")) if check.get("cwd") else str(project_root)
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=min(budget_s, 30), cwd=cwd)
        return {
            "check": "process_exit", "cmd": " ".join(cmd),
            "passed": r.returncode == check.get("expect_exit", 0),
            "exit_code": r.returncode,
            "duration_s": round(time.monotonic() - t0, 2),
            "output": (r.stdout + r.stderr).strip()[-200:],
        }
    except subprocess.TimeoutExpired:
        return {"check": "process_exit", "cmd": " ".join(cmd),
                "passed": False, "error": "timeout"}
    except Exception as e:
        return {"check": "process_exit", "cmd": " ".join(cmd),
                "passed": False, "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_check(cmd: list, check_name: str, relpath: str,
               timeout: int = 5) -> dict:
    """Run a subprocess check and return a signal dict."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "check": check_name,
            "file": relpath,
            "passed": r.returncode == 0,
            "error": r.stderr.strip()[-200:] if r.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"check": check_name, "file": relpath,
                "passed": False, "error": "timeout"}
    except FileNotFoundError:
        # A MISSING TOOL IS NOT A PASS. This returned passed=True, so a check
        # that never executed counted toward the tier verdict as though the file
        # had been verified. Uninstall the linter and the tree goes green.
        #
        # This file already has the honest value -- `insufficient`, set at ~L601
        # for permission errors, with the comment "unknown coerced into a
        # verdict. INSUFFICIENT is the honest value". But that scan only inspects
        # signals where passed is FALSE, so a branch claiming passed=True routed
        # around the very state introduced to cover it.
        #
        # passed=False + insufficient=True excludes it from the verdict instead
        # of counting it either way, and Tier 1 reports "nothing could be
        # checked" when every signal lands here.
        return {"check": check_name, "file": relpath,
                "passed": False, "insufficient": True, "state": "INSUFFICIENT",
                "error": f"could not RUN {check_name}: tool not found. "
                         f"NOT verified — this is not a pass and not a failure"}
    except Exception as e:
        return {"check": check_name, "file": relpath,
                "passed": False, "error": str(e)[:200]}


def _check_workflow_script(fpath: Path, relpath: str) -> dict:
    """Syntax-check a Claude Code Workflow script as an async function body.
    Reported line numbers are offset by one (the wrapper line)."""
    import tempfile

    body = re.sub(r"^export\s+(?=(const|let|var|function|async)\b)", "",
                  fpath.read_text(), flags=re.M)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
        tmp.write("(async () => {\n" + body + "\n})\n")
    try:
        sig = _run_check(["node", "--check", tmp.name], "workflow_node_check", relpath)
    finally:
        os.unlink(tmp.name)
    return sig


def _check_json(fpath: Path, relpath: str) -> dict:
    try:
        json.loads(fpath.read_text())
        return {"check": "json_parse", "file": relpath, "passed": True}
    except Exception as e:
        return {"check": "json_parse", "file": relpath,
                "passed": False, "error": str(e)[:200]}


def _find_venv_python(relpath: str, project_root: Path) -> str | None:
    """Walk up from file's directory to project_root looking for a venv Python."""
    fpath = (project_root / relpath).resolve()
    start = fpath.parent if fpath.is_file() else fpath
    root = project_root.resolve()
    current = start
    while True:
        for venv_name in (".venv", "venv"):
            candidate = current / venv_name / "bin" / "python"
            if candidate.exists():
                return str(candidate)
        if current == root or current == current.parent:
            break
        current = current.parent

    # Worktree fallback: when project_root is a linked worktree, the venv
    # typically lives in the main checkout. Resolve it via the git common dir.
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, cwd=str(project_root),
            timeout=5,
        )
        if r.returncode == 0:
            common_dir = Path(r.stdout.strip()).resolve()
            if common_dir.name == ".git":
                main_checkout = common_dir.parent
            else:
                main_checkout = common_dir
            main_venv_python = main_checkout / ".venv" / "bin" / "python"
            if main_venv_python.exists():
                return str(main_venv_python)
    except Exception:
        logger.debug("Swallowed exception in _find_venv_python", exc_info=True)
        pass

    return None


def _check_yaml(fpath: Path, relpath: str) -> dict:
    try:
        import yaml
        yaml.safe_load(fpath.read_text())
        return {"check": "yaml_parse", "file": relpath, "passed": True}
    except ImportError:
        # SAME DEFECT as _run_check's FileNotFoundError branch, in the same
        # file: a missing dependency reported the file as verified. Uninstall
        # pyyaml and every YAML file passes its syntax check without being
        # parsed. Fixing one site and not this one would have been fixing the
        # instance instead of the class.
        return {"check": "yaml_parse", "file": relpath,
                "passed": False, "insufficient": True, "state": "INSUFFICIENT",
                "error": "could not RUN yaml_parse: pyyaml not installed. "
                         "NOT verified — this is not a pass and not a failure"}
    except Exception as e:
        return {"check": "yaml_parse", "file": relpath,
                "passed": False, "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# Tier 5: Outcome Verification (Delta-Based)
# ---------------------------------------------------------------------------

# Regex patterns for extracting measurable claims from plan text.
# Each pattern captures (quantity, unit/context).
_CLAIM_PATTERNS = [
    # "+N tests/files/chunks/items/lines"
    (r'\+\s*(\d+)\s+(tests?|files?|chunks?|items?|lines?|endpoints?|modules?|functions?)',
     "count"),
    # "add N tests/files/..."
    (r'(?:add|create|write|implement)\s+(\d+)\s+(tests?|files?|chunks?|items?|endpoints?|modules?|functions?)',
     "count"),
    # "increase by N"
    (r'increase\s+(?:by\s+)?(\d+)\s+(\w+)',
     "count"),
    # "N new tests/files/..."
    (r'(\d+)\s+new\s+(tests?|files?|chunks?|items?|endpoints?|modules?|functions?)',
     "count"),
    # "create/add/write <filename>" (file existence claim)
    # Supports absolute (/tmp/foo.txt), relative (src/app.py), and quoted paths.
    # Extensions cover code, config, docs, and data files including .txt.
    # NOTE: longer extensions MUST come before shorter prefixes in the
    # alternation (e.g. json before js) so regex ordering doesn't truncate.
    (r'(?:create|add|write)\s+(?:file\s+)?[`"\']?([a-zA-Z0-9_/\-\.]+\.(?:json|yaml|yml|toml|html|css|xml|sql|txt|csv|cfg|ini|py|js|ts|md|sh))[`"\']?',
     "file"),
]

# Map unit words to their singular form for consistency.
_UNIT_NORMALIZE = {
    "tests": "test", "files": "file", "chunks": "chunk",
    "items": "item", "lines": "line", "endpoints": "endpoint",
    "modules": "module", "functions": "function",
}


def extract_claims(plan_text: str) -> list[dict]:
    """Extract measurable claims from plan text.

    Returns list of dicts with: claim_type, quantity (for count), unit,
    target (for file), raw_match.
    """
    claims = []
    seen = set()

    for pattern, claim_type in _CLAIM_PATTERNS:
        for match in re.finditer(pattern, plan_text, re.IGNORECASE):
            raw = match.group(0)
            if raw in seen:
                continue
            seen.add(raw)

            if claim_type == "count":
                qty = int(match.group(1))
                unit = _UNIT_NORMALIZE.get(match.group(2).lower(),
                                           match.group(2).lower())
                if qty > 0:
                    claims.append({
                        "claim_type": "count",
                        "quantity": qty,
                        "unit": unit,
                        "raw_match": raw,
                    })
            elif claim_type == "file":
                target = match.group(1)
                claims.append({
                    "claim_type": "file",
                    "target": target,
                    "raw_match": raw,
                })

    return claims


def _measure_count(unit: str, project_root: Path) -> int:
    """Measure the current count of a unit type in the project."""
    try:
        if unit == "test":
            # Count test functions across all test files
            count = 0
            for tf in project_root.rglob("test_*.py"):
                content = tf.read_text(errors="ignore")
                count += len(re.findall(r'^\s*def\s+test_', content, re.MULTILINE))
            return count
        elif unit == "file":
            return sum(1 for _ in project_root.rglob("*.py"))
        elif unit in ("line", "lines"):
            total = 0
            for pf in project_root.rglob("*.py"):
                try:
                    total += sum(1 for _ in open(pf, errors="ignore"))
                except Exception:
                    logger.debug("Swallowed exception in _measure_count", exc_info=True)
                    pass
            return total
        elif unit == "endpoint":
            count = 0
            for pf in project_root.rglob("*.py"):
                try:
                    content = pf.read_text(errors="ignore")
                    count += len(re.findall(
                        r'@(?:app|router|mcp)\.\s*(?:get|post|put|delete|patch|route|tool)',
                        content, re.IGNORECASE))
                except Exception:
                    logger.debug("Swallowed exception in _measure_count", exc_info=True)
                    pass
            return count
        elif unit == "function":
            count = 0
            for pf in project_root.rglob("*.py"):
                try:
                    content = pf.read_text(errors="ignore")
                    count += len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
                except Exception:
                    logger.debug("Swallowed exception in _measure_count", exc_info=True)
                    pass
            return count
        elif unit == "module":
            return sum(1 for _ in project_root.rglob("*.py")
                       if not _.name.startswith("test_"))
        elif unit == "chunk":
            # Count JSONL entries in common data files
            count = 0
            brain = project_root / ".brain"
            if brain.exists():
                for jl in brain.rglob("*.jsonl"):
                    try:
                        count += sum(1 for line in open(jl, errors="ignore")
                                     if line.strip())
                    except Exception:
                        logger.debug("Swallowed exception in _measure_count", exc_info=True)
                        pass
            return count
    except Exception:
        logger.debug("Swallowed exception in _measure_count", exc_info=True)
        pass
    return 0


def capture_outcome_baseline(plan_text: str, project_root: Path) -> dict:
    """Capture pre-implementation baseline metrics from plan claims.

    Parses plan text for measurable claims (counts, file existence).
    Records current state of each metric.
    Writes to .brain/driver/outcome_baseline.json.

    Returns: {"claims": [...], "captured_at": iso_timestamp, "plan_hash": str}
    """
    project_root = Path(project_root)
    claims = extract_claims(plan_text)

    baseline_claims = []
    for claim in claims:
        if claim["claim_type"] == "count":
            current = _measure_count(claim["unit"], project_root)
            baseline_claims.append({
                "claim_type": "count",
                "unit": claim["unit"],
                "claimed_delta": claim["quantity"],
                "baseline_value": current,
                "raw_match": claim["raw_match"],
            })
        elif claim["claim_type"] == "file":
            target = claim["target"]
            exists = (project_root / target).exists()
            baseline_claims.append({
                "claim_type": "file",
                "target": target,
                "baseline_exists": exists,
                "raw_match": claim["raw_match"],
            })

    plan_hash = hashlib.sha256(plan_text.encode()).hexdigest()[:12]
    result = {
        "claims": baseline_claims,
        "captured_at": datetime.now().isoformat(),
        "plan_hash": plan_hash,
    }

    # Persist
    driver_dir = project_root / ".brain" / "driver"
    driver_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = driver_dir / "outcome_baseline.json"
    baseline_path.write_text(json.dumps(result, indent=2))

    return result


def _tier5_outcome_check(plan_text: str, project_root: Path,
                         budget_s: float,
                         baseline_path: Path) -> list[dict]:
    """Tier 5: Compare post-implementation state against baseline claims.

    For each claimed metric in the baseline:
    - Re-measure the current value
    - Compute delta (current - baseline)
    - Compare delta to claimed improvement
    - Signal passes if actual_delta >= claimed_delta * 0.25 (25% threshold)

    Returns list of signal dicts.
    """
    t0 = time.monotonic()
    signals = []

    try:
        baseline = json.loads(baseline_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    for claim in baseline.get("claims", []):
        if time.monotonic() - t0 > budget_s:
            break

        if claim["claim_type"] == "count":
            current = _measure_count(claim["unit"], project_root)
            baseline_val = claim["baseline_value"]
            claimed_delta = claim["claimed_delta"]
            actual_delta = current - baseline_val
            hit_ratio = actual_delta / claimed_delta if claimed_delta > 0 else 0.0
            passed = hit_ratio >= 0.25  # 25% threshold

            signals.append({
                "tier": 5,
                "check": f"outcome_{claim['unit']}",
                "metric": claim["unit"],
                "claimed_delta": claimed_delta,
                "actual_delta": actual_delta,
                "baseline_value": baseline_val,
                "current_value": current,
                "hit_ratio": round(hit_ratio, 4),
                "passed": passed,
                "error": "" if passed else
                    f"PREMATURE VICTORY: claimed +{claimed_delta} {claim['unit']}, "
                    f"actual +{actual_delta} ({hit_ratio:.0%} of target)",
            })

        elif claim["claim_type"] == "file":
            target = claim["target"]
            exists_now = (project_root / target).exists()
            existed_before = claim.get("baseline_exists", False)
            # Pass if file was created (didn't exist before, exists now)
            # or if it already existed (not a creation claim violation)
            passed = exists_now
            signals.append({
                "tier": 5,
                "check": f"outcome_file",
                "metric": "file_exists",
                "target": target,
                "existed_before": existed_before,
                "exists_now": exists_now,
                "passed": passed,
                "error": "" if passed else
                    f"PREMATURE VICTORY: claimed to create {target}, file not found",
            })

    return signals


def _find_recent_plan(project_root: Path) -> Path | None:
    """Find the most recent plan file.

    Searches:
    1. ~/.claude/plans/*.md (Claude Code plan files)
    2. .brain/driver/current_plan.md (manual plan)
    """
    # Claude Code plans
    claude_plans = Path.home() / ".claude" / "plans"
    if claude_plans.exists():
        plans = sorted(claude_plans.glob("*.md"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        if plans:
            return plans[0]

    # Manual plan in brain
    manual = project_root / ".brain" / "driver" / "current_plan.md"
    if manual.exists():
        return manual

    return None
