"""Unit tests for `nucleus build` (dogfood-v0 build pipeline) — INVERTED.

Mocks the vendor + plan-review + verification seams — ZERO live vendor calls,
no real git mutations. Uses tmp_path + monkeypatch.chdir for cwd isolation,
matching sibling test idioms.

This is the **inverted** test suite: every test exercises the *opposite* branch
of the conditional it originally exercised (success↔failure, present↔absent,
empty↔non-empty, enabled↔disabled), with assertions flipped to match the new
mocked state so the suite stays green. The original suite tested the "happy"
and "abort" paths; this one tests their complements, doubling branch coverage.

Also updated to align with the current `_run_plan_stage` / `_run_execute_stage`
tuple shapes and the `is_multi_vendor_available` gate (the original suite
leaked into the real `dispatch_and_capture` subprocess in three cases because
it mocked `cross_vendor_enabled` but not `is_multi_vendor_available`).

Covers (inverted):
  (a) plan stage PROCEEDS on APPROVED status (incl. loop-success + file-present)
  (b) all-checked plan → zero dispatches; all-unchecked → all dispatched
  (c) no fail-stop on good dispatch; cross-vendor ENABLED does not abort
  (d) non-empty changed_files → tier-0 PASS, tiers 1–3 run
  (e) tier2 RUNS when .py present; tier3 RUNS when signals non-empty;
      tier1/tier2 evaluate non-empty signal lists
  (f) tier1/tier2/tier3 PASS → exit 0; any tier fail → exit nonzero
  (g) single-vendor plan FAILS when dispatch fails; dual-vendor verdict card
      shows ADVERSARIAL labels; single-vendor path taken when multi-vendor
      unavailable
  (h) regression: claude-present → claude vendor (not devin fallback);
      CLI present → no install instructions; read_state returns {} on miss;
      non-terminal statuses (REVIEWING, SINGLE_VENDOR_PLAN) orphan/preserve
      correctly
"""

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime import build_runner


# ── Isolation ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_brain(tmp_path, monkeypatch):
    """Pin brain resolution to tmp_path and shrink poll budgets.

    get_brain_path() prefers NUCLEUS_BRAIN_PATH over cwd auto-detection, so a
    developer shell with that var pinned to the real .brain would make the
    plan-stage poll spin its full 600s budget looking for test plan_ids that
    only exist under tmp_path.
    """
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    monkeypatch.setattr(build_runner, "_PLAN_POLL_TIMEOUT_S", 3)
    monkeypatch.setattr(build_runner, "_PLAN_POLL_INTERVAL_S", 0.05)


@pytest.fixture(autouse=True)
def _no_real_dispatch(monkeypatch):
    """Never let these tests spawn a real vendor subprocess.

    The dual-vendor path fails over to _run_single_vendor_plan_stage →
    dispatch_and_capture — tests that only mock execute_plan_review_loop
    were reaching the fallback and launching a real vendor CLI (observed:
    30s pytest-timeout kills, ~23 failures). The default fake is a passing
    dispatch; a test that needs a different result can still patch
    dispatch_and_capture itself (inner patch wins inside its with-block).
    """
    monkeypatch.setattr(
        build_runner, "dispatch_and_capture",
        lambda *a, **kw: _ok_dispatch(),
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_response(success: bool, data=None, error=None) -> str:
    return json.dumps({"success": success, "data": data, "error": error})


def _write_state(tmp_path: Path, plan_id: str, status: str,
                 final_plan_path: str = None, *, age_s: float = 7200.0,
                 owner_pid: int = None) -> None:
    """Write .brain/plans/<plan_id>/state.json under tmp_path.

    ``age_s`` back-dates the file's mtime; it defaults to two hours because
    the stale sweep only claims an unowned plan after a grace window. A
    freshly-written fixture is indistinguishable from a plan a concurrent
    build is working on right now, and treating those as stale is the bug
    these tests exist to catch — so "stale" fixtures must actually be old.
    """
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    state = {"status": status}
    if final_plan_path is not None:
        state["final_plan_path"] = final_plan_path
    if owner_pid is not None:
        state["owner_pid"] = owner_pid
    (plans_dir / "state.json").write_text(json.dumps(state))
    if age_s:
        old = time.time() - age_s
        os.utime(plans_dir / "state.json", (old, old))


def _write_plan(tmp_path: Path, plan_id: str, tasks: list) -> Path:
    """Write a final_plan.md with the given task descriptions under tmp_path."""
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    fp = plans_dir / "final_plan.md"
    lines = ["# Plan\n"]
    for n, desc in tasks:
        lines.append(f"- [ ] Task {n}: {desc}")
    fp.write_text("\n".join(lines) + "\n")
    return fp


def _write_plan_checked(tmp_path: Path, plan_id: str, tasks: list) -> Path:
    """Write a final_plan.md with all tasks CHECKED (`- [x]`)."""
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    fp = plans_dir / "final_plan.md"
    lines = ["# Plan\n"]
    for n, desc in tasks:
        lines.append(f"- [x] Task {n}: {desc}")
    fp.write_text("\n".join(lines) + "\n")
    return fp


def _ok_dispatch(status="ok", produced_output=True):
    """A dispatch_and_capture mock returning a passing result."""
    return {"status": status, "produced_output": produced_output,
            "vendor": "devin", "rc": 0}


# ── (a) plan stage PROCEEDS on APPROVED (inverse of abort-on-non-APPROVED) ───

def test_plan_stage_proceeds_on_approved(tmp_path, monkeypatch):
    """APPROVED status → plan stage returns ok=True with a final_plan_path.

    Inverse of the abort-on-non-APPROVED parametrized test: the one status that
    is NOT in _ABORT_STATUSES (APPROVED) must let the plan stage proceed.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "proceed-test"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True):
        ok, msg, fp_out, mode = build_runner._run_plan_stage("do something")

    assert ok is True
    assert msg == "APPROVED"
    assert fp_out is not None and fp_out.exists()
    assert mode == "dual-vendor"


def test_plan_stage_proceeds_on_loop_success(tmp_path, monkeypatch):
    """plan_review_loop returning success=True with a plan_id → plan stage ok.

    Inverse of abort-on-loop-error: a successful loop response must NOT abort.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "loop-ok"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True):
        ok, msg, fp_out, mode = build_runner._run_plan_stage("do something")

    assert ok is True
    assert fp_out is not None and fp_out.exists()


def test_plan_stage_proceeds_when_final_plan_present(tmp_path, monkeypatch):
    """APPROVED state + final_plan.md present on disk → plan stage ok=True.

    Inverse of abort-on-missing-final-plan: when the file IS present, the
    'APPROVED but final_plan_path missing on disk' abort must NOT fire.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "present-plan"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True):
        ok, msg, fp_out, mode = build_runner._run_plan_stage("do something")

    assert ok is True
    assert fp_out == fp


def test_nonempty_task_prompt_does_not_return_2(tmp_path, monkeypatch):
    """Non-empty task prompt → exit code is NOT 2 (arg-validation passes).

    Inverse of empty-task-prompt-returns-2: a real prompt must clear the
    arg-validation gate, so rc != 2 (it may be 0 or 1 from later stages).
    """
    monkeypatch.chdir(tmp_path)

    def fake_loop(params, make_response):
        return _make_response(False, error="forced plan-stage abort for test")

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True):
        rc = build_runner.run_build_pipeline("a real task prompt")
    # Arg-validation passed (rc != 2); pipeline aborted later at plan stage (rc == 1).
    assert rc != 2
    assert rc == 1


# ── (b) all-checked → zero dispatches; all-unchecked → all dispatched ────────

def test_all_checked_tasks_dispatch_zero_times(tmp_path, monkeypatch):
    """All `- [x]` (checked) tasks → dispatch never called, EXECUTE aborts → rc 1.

    Inverse of approved-path-dispatches-per-task: when every task is already
    checked, the parser yields zero unchecked tasks, dispatch is never invoked,
    and the execute stage aborts with 'no unchecked Task N: checkboxes'.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "all-checked"
    fp = _write_plan_checked(tmp_path, plan_id, [(1, "done one"), (2, "done two")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    captured = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(prompt)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"):
        rc = build_runner.run_build_pipeline("build")

    assert captured == []  # no unchecked tasks → no dispatches
    assert rc == 1  # EXECUTE aborts on 'no unchecked checkboxes'


def test_unchecked_tasks_are_all_dispatched(tmp_path, monkeypatch):
    """All `- [ ]` (unchecked) tasks → every task dispatched, rc 0.

    Inverse of checked-tasks-are-skipped: with no checked tasks, nothing is
    skipped and every task is dispatched in order.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "all-unchecked"
    fp = _write_plan(tmp_path, plan_id, [(1, "first"), (2, "second"), (3, "third")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    captured = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(prompt)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")

    assert captured == ["first", "second", "third"]
    assert rc == 0


def test_unchecked_tasks_present_does_not_abort_execute(tmp_path, monkeypatch):
    """≥1 unchecked task → EXECUTE stage does NOT abort at the 'no checkboxes' gate.

    Inverse of no-unchecked-tasks-aborts: drive `_run_execute_stage` directly
    and assert ok=True when at least one unchecked task is present.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "has-unchecked"
    fp = _write_plan(tmp_path, plan_id, [(1, "only task")])

    with patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"):
        ok, msg, pre, post, results = build_runner._run_execute_stage(
            "build", fp, execution_mode="dual-vendor",
        )

    assert ok is True
    assert len(results) == 1
    assert "no unchecked" not in msg


# ── (c) no fail-stop on good dispatch; cross-vendor ENABLED does not abort ────

def test_no_fail_stop_on_good_dispatch(tmp_path, monkeypatch):
    """All dispatches return ok+produced_output → both tasks run, rc 0.

    Inverse of fail-stop-on-bad-dispatch: when every dispatch passes the
    predicate, fail-stop does NOT fire and the second task IS dispatched.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "nostop"
    fp = _write_plan(tmp_path, plan_id, [(1, "first"), (2, "second")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    dispatched = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        dispatched.append(prompt)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/x.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/x.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")

    # Both tasks dispatched — no fail-stop
    assert dispatched == ["first", "second"]
    assert rc == 0


def test_cross_vendor_enabled_does_not_abort(tmp_path, monkeypatch):
    """cross_vendor_enabled() == True → EXECUTE stage does NOT abort at the gate.

    Inverse of cross-vendor-disabled-aborts: with the gate open, the execute
    stage proceeds and dispatches to devin. (Also pins the is_multi_vendor_available
    mock that the original test was missing.)
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "xv-on"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    captured = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")

    assert captured == ["devin"]
    assert rc == 0


# ── (d) non-empty changed_files → tier-0 PASS, tiers 1–3 run ─────────────────

def test_nonempty_changed_files_tier0_pass(tmp_path, monkeypatch):
    """Non-empty changed_files → tier-0 PASS, tiers 1–3 RUN, rc 0.

    Inverse of empty-changed-files-tier0-failure: when changed_files is
    non-empty, tier-0 passes and tiers 1–3 are actually invoked (not
    short-circuited).
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "has-changes"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    tier_calls = {"t1": 0, "t2": 0, "t3": 0}

    def fake_t1(*a, **kw):
        tier_calls["t1"] += 1
        return [{"passed": True}]

    def fake_t2(*a, **kw):
        tier_calls["t2"] += 1
        return [{"passed": True}]

    def fake_t3(*a, **kw):
        tier_calls["t3"] += 1
        return [{"passed": True}]

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               side_effect=fake_t1), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               side_effect=fake_t2), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               side_effect=fake_t3):
        rc = build_runner.run_build_pipeline("build")

    # Tier-0 passed → tiers 1/2/3 all ran
    assert tier_calls == {"t1": 1, "t2": 1, "t3": 1}
    assert rc == 0


# ── (e) tier2 RUNS when .py present; tier3 RUNS when signals non-empty ───────

def test_tier2_runs_when_py_files_present(tmp_path, monkeypatch):
    """.py files present in changed_files → tier2 IS invoked (not SKIPPED).

    Inverse of tier2-skipped-when-no-py-files: when .py files exist, the
    import checker is actually called.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "has-py"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    t2_called = {"v": 0}

    def fake_t2(*a, **kw):
        t2_called["v"] += 1
        return [{"passed": True}]

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py", "src/bar.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py", "src/bar.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               side_effect=fake_t2), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")

    # tier2 called (py files present → not SKIPPED)
    assert t2_called["v"] == 1
    assert rc == 0


def test_tier3_runs_when_signals_nonempty(tmp_path, monkeypatch):
    """Non-empty tier3 signal list → tier3 evaluates (not SKIPPED), rc 0 when passing.

    Inverse of tier3-skipped-when-empty-signals: a non-empty signal list is
    evaluated via all(...), not short-circuited as SKIPPED.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "t3-run"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    t3_called = {"v": 0}

    def fake_t3(*a, **kw):
        t3_called["v"] += 1
        return [{"passed": True}, {"passed": True}]  # non-empty, all pass

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               side_effect=fake_t3):
        rc = build_runner.run_build_pipeline("build")

    assert t3_called["v"] == 1
    assert rc == 0


def test_tier2_nonempty_signals_evaluated(tmp_path, monkeypatch):
    """Non-empty tier2 signal list → evaluated as PASSED (not SKIPPED), rc 0.

    Inverse of tier2-empty-signals-skipped: a non-empty signal list is reduced
    via all(...) and surfaces as PASSED, not SKIPPED.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "t2-eval"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}, {"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")
    assert rc == 0


def test_tier1_nonempty_signals_evaluated(tmp_path, monkeypatch):
    """Non-empty tier1 signal list → evaluated as PASSED (not SKIPPED), rc 0.

    Inverse of tier1-skipped-when-no-syntax-checkable-files: a non-empty
    signal list is reduced via all(...) and surfaces as PASSED.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "t1-eval"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    t1_called = {"v": 0}

    def fake_t1(*a, **kw):
        t1_called["v"] += 1
        return [{"passed": True}, {"passed": True}]  # non-empty, all pass

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py", "src/bar.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py", "src/bar.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               side_effect=fake_t1), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")

    assert t1_called["v"] == 1
    assert rc == 0


# ── (f) tier PASS → exit 0; any tier fail → exit nonzero ─────────────────────

def test_tier1_pass_zero_exit(tmp_path, monkeypatch):
    """tier1 PASSED (all signals pass) → verification_passed True → exit 0.

    Inverse of tier1-failure-nonzero-exit.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "t1-pass"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}, {"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")
    assert rc == 0


def test_tier2_pass_zero_exit(tmp_path, monkeypatch):
    """tier2 PASSED → exit 0. Inverse of tier2-failure-nonzero-exit."""
    monkeypatch.chdir(tmp_path)
    plan_id = "t2-pass"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}, {"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")
    assert rc == 0


def test_tier3_pass_zero_exit(tmp_path, monkeypatch):
    """tier3 PASSED → exit 0. Inverse of tier3-failure-nonzero-exit."""
    monkeypatch.chdir(tmp_path)
    plan_id = "t3-pass"
    fp = _write_plan(tmp_path, plan_id, [(1, "task")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}, {"passed": True}]):
        rc = build_runner.run_build_pipeline("build")
    assert rc == 0


def test_any_tier_fail_nonzero_exit(tmp_path, monkeypatch):
    """All tasks ok but ANY single tier fails → exit nonzero.

    Inverse of all-pass-exit-zero: parametrize over which tier fails and
    assert rc == 1 in each case (the rest of the tiers pass).
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "any-fail"
    fp = _write_plan(tmp_path, plan_id, [(1, "first"), (2, "second")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    def _tier_mocks(failing):
        """Return the per-tier mock return values with exactly `failing` set to
        a failing signal list and the other two passing."""
        passing = [{"passed": True}, {"passed": True}]
        failing_signals = [{"passed": False}]
        return {
            "_tier1_syntax_check": passing if failing != "tier1" else failing_signals,
            "_tier2_import_check": passing if failing != "tier2" else failing_signals,
            "_tier3_test_execution": passing if failing != "tier3" else failing_signals,
        }

    def _run(failing):
        tm = _tier_mocks(failing)
        with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
                   side_effect=fake_loop), \
             patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
                   return_value=True), \
             patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
                   return_value=True), \
             patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
                   return_value=_ok_dispatch()), \
             patch("mcp_server_nucleus.runtime.build_runner._git_head",
                   return_value="abc123"), \
             patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
                   return_value=["src/foo.py", "src/bar.py"]), \
             patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
                   return_value=tm["_tier1_syntax_check"]), \
             patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
                   return_value=tm["_tier2_import_check"]), \
             patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
                   return_value=tm["_tier3_test_execution"]):
            return build_runner.run_build_pipeline("build foo and bar")

    for failing in ("tier1", "tier2", "tier3"):
        assert _run(failing) == 1, f"{failing} failing should give rc==1"


# ── CLI subcommand wire-in (inverted) ────────────────────────────────────────

def test_cli_build_subcommand_registered_and_bogus_verb_absent():
    """`nucleus build` is registered; a bogus verb is NOT.

    Inverse of cli-build-subcommand-registered: assert the positive (build
    registered) AND the negative (a nonexistent handler is absent).

    Imported via ``importlib.import_module`` rather than
    ``from mcp_server_nucleus import cli``: the package ``__getattr__``
    falls through to ``_ensure_initialized()`` (which builds the FastMCP
    singleton and imports fastmcp → beartype), and a prior test in the full
    suite pollutes beartype's decorcache so that import raises
    ``BeartypeDecorWrapperException``. The submodule import path sets the
    attribute on the package directly without triggering ``__getattr__``,
    so the cli module loads without the FastMCP side effects. This test
    only inspects the cli source text, so the MCP singleton is irrelevant.
    """
    import importlib

    cli_mod = importlib.import_module("mcp_server_nucleus.cli")

    assert hasattr(cli_mod, "handle_build_command")
    src = Path(cli_mod.__file__).read_text()
    assert "subparsers.add_parser(\n        'build'," in src or \
           "subparsers.add_parser('build'" in src
    assert "elif cli_command == 'build':" in src
    # Inverted assertion: a bogus verb is NOT wired in.
    assert not hasattr(cli_mod, "handle_nonexistent_verb_command")
    assert "elif cli_command == 'nonexistent_verb':" not in src


def test_cli_build_handler_propagates_nonzero_code(tmp_path, monkeypatch):
    """handle_build_command propagates a nonzero pipeline rc unchanged.

    Inverse of cli-build-handler-lazy-imports-and-returns-code (which asserted
    rc==0 propagation): when the pipeline returns 1, the handler returns 1.
    """
    from mcp_server_nucleus import cli as cli_mod

    class FakeArgs:
        task = "do the thing"

    called = {"v": False}

    def fake_pipeline(task_prompt):
        called["v"] = True
        assert task_prompt == "do the thing"
        return 1  # nonzero

    with patch("mcp_server_nucleus.runtime.build_runner.run_build_pipeline",
               side_effect=fake_pipeline):
        rc = cli_mod.handle_build_command(FakeArgs())
    assert called["v"] is True
    assert rc == 1


# ── (g) single-vendor FAILS on bad dispatch; dual-vendor verdict ADVERSARIAL ──

def test_single_vendor_plan_stage_fails_when_dispatch_fails(tmp_path, monkeypatch):
    """is_multi_vendor_available=False + claude on PATH but dispatch returns
    bad result → plan stage fails cleanly (ok=False), no final_plan.md written.

    Inverse of single-vendor-plan-stage-dispatches-to-claude (which asserted
    ok=True on a successful dispatch).
    """
    monkeypatch.chdir(tmp_path)

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        return {"status": "error", "produced_output": False, "result": ""}

    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               return_value="/usr/local/bin/claude"), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch):
        ok, msg, fp, execution_mode = build_runner._run_plan_stage("build foo")

    assert ok is False
    assert fp is None
    assert execution_mode == "single-vendor"
    assert "single-vendor plan dispatch failed" in msg


def test_single_vendor_plan_stage_no_install_msg_when_cli_present(tmp_path, monkeypatch):
    """claude on PATH + dispatch ok → plan stage ok=True, install instructions NOT in msg.

    Inverse of single-vendor-plan-stage-requires-claude-binary (which asserted
    ok=False + install msg when no CLI present).
    """
    monkeypatch.chdir(tmp_path)
    plan_text = "- [ ] Task 1: write foo\n"

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        return {"status": "ok", "produced_output": True, "result": plan_text}

    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               return_value="/usr/local/bin/claude"), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch):
        ok, msg, fp, execution_mode = build_runner._run_plan_stage("build foo")

    assert ok is True
    assert "no coding agent CLI" not in msg
    assert "npm i -g" not in msg
    assert "pip install" not in msg


def test_single_vendor_execute_uses_devin_when_claude_absent(tmp_path, monkeypatch):
    """execution_mode='single-vendor' + claude missing + devin present →
    execute stage dispatches to devin (NOT claude).

    Inverse of single-vendor-execute-dispatches-to-claude-not-devin.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "sv-exec-invert"
    fp = _write_plan(tmp_path, plan_id, [(1, "write foo"), (2, "write bar")])

    captured = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append({"vendor": vendor, "prompt": prompt, "mode": mode})
        return _ok_dispatch()

    def fake_which(binary):
        if binary == "claude":
            return None
        if binary == "devin":
            return "/usr/local/bin/devin"
        return None

    with patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               side_effect=fake_which), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"):
        ok, msg, pre_head, post_head, results = build_runner._run_execute_stage(
            "build foo and bar", fp, execution_mode="single-vendor",
        )

    assert ok is True
    assert len(captured) == 2
    assert all(c["vendor"] == "devin" for c in captured)
    assert all(c["vendor"] != "claude" for c in captured)
    assert all(c["mode"] == "write" for c in captured)


def test_dual_vendor_verdict_card_labels_adversarial(tmp_path, monkeypatch, capsys):
    """Full dual-vendor pipeline (is_multi_vendor_available=True) → verdict card
    shows DUAL-VENDOR ADVERSARIAL + PROVEN labels, NOT the single-vendor
    UNREVIEWED label, and returns exit 0 on full success.

    Inverse of single-vendor-verdict-card-labels-unreviewed.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "dv-card"
    fp = _write_plan(tmp_path, plan_id, [(1, "write foo")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    captured = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build foo")

    out = capsys.readouterr().out
    assert rc == 0
    assert "DUAL-VENDOR ADVERSARIAL" in out
    assert "PROVEN" in out
    assert "SINGLE-VENDOR UNREVIEWED" not in out
    assert all(v == "devin" for v in captured)


def test_dual_vendor_verdict_card_label_unaffected(tmp_path, capsys):
    """The ``single_vendor`` parameter (added for the single-vendor label path)
    MUST NOT leak into the dual-vendor verdict card.

    Direct unit test of ``_render_verdict_card``: when ``execution_mode`` is
    the dual-vendor mode, passing ``single_vendor="devin"`` (or any value)
    must leave the dual-vendor labels byte-identical — the mode label stays
    ``dual-vendor adversarial``, the confidence stays ``DUAL-VENDOR
    ADVERSARIAL``, the task outcome stays ``PROVEN``, and neither the vendor
    name nor the single-vendor phrasing (``devin only`` /
    ``SINGLE-VENDOR UNREVIEWED`` / ``EXECUTED``) appears anywhere in the card.
    This is the regression guard for the parameter-add boundary: the new
    parameter is scoped to the single-vendor branch only.
    """
    fp = tmp_path / "final_plan.md"
    fp.write_text("# Plan\n- [ ] Task 1: write foo\n", encoding="utf-8")
    results = [{
        "task_num": 1,
        "task_desc": "write foo",
        "vendor": "devin",
        "result": {"status": "ok", "produced_output": True},
    }]
    verify_details = {
        "changed_files": ["src/foo.py"],
        "tier0": {"status": "PASSED"},
        "tier1": {"status": "PASSED"},
        "tier2": {"status": "PASSED"},
        "tier3": {"status": "PASSED"},
        "passed_count": 4, "failed_count": 0, "skipped_count": 0,
        "summary_status": "PASSED",
    }

    rc = build_runner._render_verdict_card(
        task_prompt="build foo",
        final_plan_path=fp,
        pre_head="abc123",
        post_head="def456",
        results=results,
        verification_passed=True,
        verify_details=verify_details,
        execution_mode=build_runner._MODE_DUAL_VENDOR,
        single_vendor="devin",  # the new parameter — must NOT leak
    )

    out = capsys.readouterr().out
    # Exit 0 on a full dual-vendor pass.
    assert rc == 0
    # Dual-vendor labels are unchanged.
    assert "dual-vendor adversarial" in out
    assert "DUAL-VENDOR ADVERSARIAL" in out
    assert "PROVEN" in out
    # The new parameter does not leak: no single-vendor phrasing, no vendor
    # name in the mode label, no EXECUTED/unreviewed outcome.
    assert "SINGLE-VENDOR UNREVIEWED" not in out
    assert "single-vendor" not in out
    assert "devin only" not in out
    assert "EXECUTED" not in out
    assert "unreviewed" not in out


def test_single_vendor_path_when_multi_vendor_unavailable(tmp_path, monkeypatch, capsys):
    """is_multi_vendor_available=False + claude mocked throughout → pipeline
    dispatches to claude (NOT devin), verdict card shows SINGLE-VENDOR
    UNREVIEWED, NOT DUAL-VENDOR ADVERSARIAL, exit 0 on success.

    Inverse of dual-vendor-path-unchanged-when-multi-vendor-available.
    """
    monkeypatch.chdir(tmp_path)
    plan_text = "- [ ] Task 1: write foo\n"

    captured = []

    def fake_dispatch_capture(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        # The plan stage dispatches in mode="write" since 4aa34484 -- in
        # mode="read" the vendor emitted conversational prose instead of the
        # "- [ ] Task N:" checklist, which broke the execute stage's regex
        # three times in one night. Both stages are now mode="write", so the
        # plan call is identified by its prompt, not by its mode.
        if "task planner" in prompt:
            # Keying on the prompt rather than the mode would leave this test
            # blind to a regression back to mode="read", so assert the mode
            # here: that IS the contract 4aa34484 established.
            assert mode == "write", (
                f"plan stage must dispatch in write mode (4aa34484); got {mode!r}"
            )
            return {"status": "ok", "produced_output": True, "result": plan_text}
        return _ok_dispatch()

    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               return_value="/usr/local/bin/claude"), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch_capture), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build foo")

    out = capsys.readouterr().out
    assert rc == 0
    # Degraded (single-vendor) runs must stay on the FREE lane — fw-1786104704.
    # Previously asserted all-claude, which locked the arbitrage inversion in
    # as the contract: a dead free vendor billed the paid tier for every task.
    assert all(v == "devin" for v in captured)
    assert "claude" not in captured
    assert "SINGLE-VENDOR UNREVIEWED" in out
    assert "DUAL-VENDOR ADVERSARIAL" not in out


def test_single_vendor_verdict_card_names_devin(tmp_path, monkeypatch, capsys):
    """Single-vendor verdict card names devin (NOT claude) in its mode label.

    The single-vendor mode label is `single-vendor (<vendor> only, no
    adversarial review)`. fw-1786104704 routed degraded runs onto the FREE
    devin lane, so the card must say `devin only` — not `claude only`, which
    would mislabel a free-lane run as a paid-lane run.
    """
    monkeypatch.chdir(tmp_path)
    plan_text = "- [ ] Task 1: write foo\n"

    captured = []

    def fake_dispatch_capture(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        # The plan stage dispatches in mode="write" since 4aa34484 -- in
        # mode="read" the vendor emitted conversational prose instead of the
        # "- [ ] Task N:" checklist, which broke the execute stage's regex
        # three times in one night. Both stages are now mode="write", so the
        # plan call is identified by its prompt, not by its mode.
        if "task planner" in prompt:
            # Keying on the prompt rather than the mode would leave this test
            # blind to a regression back to mode="read", so assert the mode
            # here: that IS the contract 4aa34484 established.
            assert mode == "write", (
                f"plan stage must dispatch in write mode (4aa34484); got {mode!r}"
            )
            return {"status": "ok", "produced_output": True, "result": plan_text}
        return _ok_dispatch()

    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               return_value="/usr/local/bin/claude"), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch_capture), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build foo")

    out = capsys.readouterr().out
    assert rc == 0
    assert all(v == "devin" for v in captured)
    assert "claude" not in captured
    # The verdict card mode label names the actual vendor used.
    assert "single-vendor (devin only, no adversarial review)" in out
    assert "claude only" not in out
    assert "SINGLE-VENDOR UNREVIEWED" in out
    assert "DUAL-VENDOR ADVERSARIAL" not in out


def test_single_vendor_verdict_card_names_agy(tmp_path, monkeypatch, capsys):
    """Single-vendor verdict card names agy (NOT claude) in its mode label.

    Sibling of the devin test above, covering the other free lane. When
    ``NUCLEUS_SINGLE_VENDOR=agy`` forces the agy lane (and agy is on PATH),
    the verdict card must say `agy only` — not `claude only` or `devin only`,
    which would mislabel which vendor actually ran the work.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_SINGLE_VENDOR", "agy")
    plan_text = "- [ ] Task 1: write foo\n"

    captured = []

    def fake_dispatch_capture(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        # The plan stage dispatches in mode="write" since 4aa34484 -- in
        # mode="read" the vendor emitted conversational prose instead of the
        # "- [ ] Task N:" checklist, which broke the execute stage's regex
        # three times in one night. Both stages are now mode="write", so the
        # plan call is identified by its prompt, not by its mode.
        if "task planner" in prompt:
            # Keying on the prompt rather than the mode would leave this test
            # blind to a regression back to mode="read", so assert the mode
            # here: that IS the contract 4aa34484 established.
            assert mode == "write", (
                f"plan stage must dispatch in write mode (4aa34484); got {mode!r}"
            )
            return {"status": "ok", "produced_output": True, "result": plan_text}
        return _ok_dispatch()

    def fake_which(binary):
        # agy must resolve (forced vendor); claude present but must NOT win.
        if binary == "agy":
            return "/usr/local/bin/agy"
        if binary == "claude":
            return "/usr/local/bin/claude"
        return None

    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               side_effect=fake_which), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch_capture), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build foo")

    out = capsys.readouterr().out
    assert rc == 0
    assert all(v == "agy" for v in captured)
    assert "claude" not in captured
    assert "devin" not in captured
    # The verdict card mode label names the actual vendor used.
    assert "single-vendor (agy only, no adversarial review)" in out
    assert "claude only" not in out
    assert "devin only" not in out
    assert "SINGLE-VENDOR UNREVIEWED" in out
    assert "DUAL-VENDOR ADVERSARIAL" not in out


def test_single_vendor_verdict_card_names_claude(tmp_path, monkeypatch, capsys):
    """Legacy paid-fallback: only claude on PATH → verdict card reads `claude only`.

    Sibling of the devin/agy tests above, covering the last-resort paid lane.
    When NO free vendor is available (devin and agy both absent from PATH) and
    only claude resolves, the pipeline falls back to the paid claude lane and
    the verdict card must honestly label the run `claude only` — not mislabel
    it as a free-lane `devin only`/`agy only` run, and not silently drop the
    vendor name. This is the legacy pre-fw-1786104704 path, retained as the
    honest label for the case where there genuinely is no free lane.
    """
    monkeypatch.chdir(tmp_path)
    plan_text = "- [ ] Task 1: write foo\n"

    captured = []

    def fake_dispatch_capture(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        # The plan stage dispatches in mode="write" since 4aa34484 -- in
        # mode="read" the vendor emitted conversational prose instead of the
        # "- [ ] Task N:" checklist, which broke the execute stage's regex
        # three times in one night. Both stages are now mode="write", so the
        # plan call is identified by its prompt, not by its mode.
        if "task planner" in prompt:
            # Keying on the prompt rather than the mode would leave this test
            # blind to a regression back to mode="read", so assert the mode
            # here: that IS the contract 4aa34484 established.
            assert mode == "write", (
                f"plan stage must dispatch in write mode (4aa34484); got {mode!r}"
            )
            return {"status": "ok", "produced_output": True, "result": plan_text}
        return _ok_dispatch()

    def fake_which(binary):
        # Only claude resolves — no free lane (devin/agy absent).
        if binary == "claude":
            return "/usr/local/bin/claude"
        return None

    monkeypatch.delenv("NUCLEUS_SINGLE_VENDOR", raising=False)
    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               side_effect=fake_which), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch_capture), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build foo")

    out = capsys.readouterr().out
    assert rc == 0
    assert all(v == "claude" for v in captured)
    assert "devin" not in captured
    assert "agy" not in captured
    # The verdict card mode label names the actual (paid-fallback) vendor used.
    assert "single-vendor (claude only, no adversarial review)" in out
    assert "devin only" not in out
    assert "agy only" not in out
    assert "SINGLE-VENDOR UNREVIEWED" in out
    assert "DUAL-VENDOR ADVERSARIAL" not in out


# ── Regression tests for build reliability fixes (inverted) ──────────────────


def test_single_vendor_plan_uses_claude_when_present(tmp_path, monkeypatch):
    """Both CLIs present → plan stage picks the FREE devin, not paid claude.

    Renamed-in-place contract flip (fw-1786104704). This test previously
    asserted `vendor == "claude"`, encoding the arbitrage inversion as the
    expected behavior: claude was preferred and devin/agy were reachable only
    when claude was absent from PATH — which never happens, since claude is the
    CLI running the session. Free lanes must win; claude is last resort.
    """
    monkeypatch.chdir(tmp_path)
    plan_text = "- [ ] Task 1: write foo\n"
    captured = {}

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured["vendor"] = vendor
        return {"status": "ok", "produced_output": True, "result": plan_text}

    def fake_which(binary):
        if binary == "claude":
            return "/usr/local/bin/claude"
        if binary == "devin":
            return "/usr/local/bin/devin"  # free lane present → must win
        return None

    monkeypatch.delenv("NUCLEUS_SINGLE_VENDOR", raising=False)
    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               side_effect=fake_which), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch):
        ok, msg, fp, execution_mode = build_runner._run_plan_stage("build foo")

    assert ok is True
    assert captured["vendor"] == "devin"
    assert captured["vendor"] != "claude"


def test_single_vendor_execute_uses_claude_when_present(tmp_path, monkeypatch):
    """Both CLIs present → execute stage picks the FREE devin, not paid claude.

    Contract flip for fw-1786104704, and this is the stage that actually spends
    money: a degraded build dispatches EVERY task here, so the old
    claude-preferred order turned one dead free vendor into a fully paid
    execute stage while a healthy free lane idled.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "sv-claude"
    fp = _write_plan(tmp_path, plan_id, [(1, "write foo")])
    captured = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        captured.append(vendor)
        return _ok_dispatch()

    def fake_which(binary):
        if binary == "claude":
            return "/usr/local/bin/claude"
        if binary == "devin":
            return "/usr/local/bin/devin"  # free lane present → must win
        return None

    monkeypatch.delenv("NUCLEUS_SINGLE_VENDOR", raising=False)
    with patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               side_effect=fake_which), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"):
        ok, msg, pre, post, results = build_runner._run_execute_stage(
            "build foo", fp, execution_mode="single-vendor",
        )

    assert ok is True
    assert captured == ["devin"]
    assert "claude" not in captured


def test_cli_present_no_install_instructions(tmp_path, monkeypatch):
    """claude on PATH → plan stage ok=True, install commands NOT in msg.

    Inverse of no-cli-found-gives-install-instructions.
    """
    monkeypatch.chdir(tmp_path)
    plan_text = "- [ ] Task 1: write foo\n"

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        return {"status": "ok", "produced_output": True, "result": plan_text}

    with patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=False), \
         patch("mcp_server_nucleus.runtime.build_runner.shutil.which",
               return_value="/usr/local/bin/claude"), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch):
        ok, msg, fp, execution_mode = build_runner._run_plan_stage("build foo")

    assert ok is True
    assert "npm i -g" not in msg
    assert "pip install" not in msg


def test_read_state_returns_empty_on_missing_file(tmp_path, monkeypatch):
    """_read_state on a nonexistent plan_id → {} (empty dict), no exception.

    Inverse of atomic-state-write-survives-crash (which asserted a written
    file reads back as valid JSON): the read/write pair's complement is that
    a missing file reads as {} rather than raising.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    state = build_runner._read_state("never-written-plan-id")
    assert state == {}


def test_mark_plan_orphaned_on_reviewing_state(tmp_path, monkeypatch):
    """_mark_plan_orphaned changes REVIEWING (a non-terminal, non-IN_PROGRESS
    status) → ORPHANED. Inverts the assumption that only IN_PROGRESS gets
    orphaned: ANY status not in (APPROVED, SINGLE_VENDOR_PLAN, ORPHANED) is
    treated as non-terminal and gets marked ORPHANED.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_id = "reviewing-test"
    build_runner._write_state(plan_id, {
        "plan_id": plan_id,
        "status": "REVIEWING",
        "round": 1,
    })

    build_runner._mark_plan_orphaned(plan_id)

    state = build_runner._read_state(plan_id)
    assert state["status"] == "ORPHANED"
    assert "orphaned_at" in state
    # Non-status fields preserved
    assert state["plan_id"] == plan_id
    assert state["round"] == 1


def test_mark_plan_orphaned_skips_single_vendor_plan(tmp_path, monkeypatch):
    """_mark_plan_orphaned does NOT overwrite SINGLE_VENDOR_PLAN (terminal).

    Inverse of mark-plan-orphaned-skips-terminal-state (which tested APPROVED):
    the other terminal status SINGLE_VENDOR_PLAN is also preserved.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_id = "svp-terminal-test"
    build_runner._write_state(plan_id, {
        "plan_id": plan_id,
        "status": "SINGLE_VENDOR_PLAN",
        "round": 1,
    })

    build_runner._mark_plan_orphaned(plan_id)

    state = build_runner._read_state(plan_id)
    # Should still be SINGLE_VENDOR_PLAN, not overwritten to ORPHANED
    assert state["status"] == "SINGLE_VENDOR_PLAN"
    assert "orphaned_at" not in state


# ── summary_status coverage: INSUFFICIENT / PASSED / FAILED ──────────────────
#
# Three tests pinning the three legal `summary_status` outcomes of
# `_run_verify_stage` and the exit code `_render_verdict_card` derives from
# them. Each drives the full `run_build_pipeline` so both the rc and the
# verdict-card label are asserted end-to-end via capsys.
#
# DIVERGENCE NOTES (spec vs. implemented semantics — see _run_verify_stage
# docstring for the authoritative rules):
#
#   (a) spec asked for `rc == 1` with `INSUFFICIENT`. Under the current gate
#       (`verification_passed = failed_count == 0`; `_render_verdict_card`
#       returns `0 if (all_tasks_succeeded and verification_passed) else 1`),
#       an INSUFFICIENT run has `failed_count == 0` → `verification_passed =
#       True` → rc == 0 whenever EXECUTE succeeded. rc == 1 + INSUFFICIENT is
#       NOT reachable through the full pipeline: a task-side failure aborts
#       at EXECUTE and VERIFY never runs (so INSUFFICIENT never appears).
#       RESOLVED 2026-07-26: the derivation WAS changed, exactly as this
#       note prescribed — `verification_passed = failed_count == 0 and
#       passed_count > 0`. An all-skipped run now yields rc == 1. The old
#       predicate was the original tautology surviving the refactor.
#
#   (b) spec asked for "one-PASS tier + skipped tiers" → `PASSED`. With any
#       skipped tier, `skipped_count > 0` → `summary_status = INSUFFICIENT`,
#       not `PASSED`. `PASSED` requires `failed_count == 0 AND skipped_count
#       == 0` (every tier ran and passed). The "one-PASS + skipped" shape is
#       the same family as (a) (it yields INSUFFICIENT); to cover the PASSED
#       label as requested, this test drives all three tiers to a passing
#       signal list.


def test_all_skipped_tiers_yields_insufficient(tmp_path, monkeypatch, capsys):
    """All three verify tiers SKIPPED → summary_status=INSUFFICIENT, rc==1.

    Tier 0 PASS (changed_files non-empty), tier 1 has no syntax-checkable
    files (`_tier1_syntax_check` → []), tier 2 has no `.py` files (SKIPPED
    without invoking the import checker), tier 3 discovers no test files
    (`_tier3_test_execution` → []). passed_count=0, failed_count=0,
    skipped_count=3 → INSUFFICIENT → verification_passed=False → rc==1.

    Covers requested scenario (a). RESOLVED: the gate now requires positive
    evidence, so an all-skipped run is INSUFFICIENT and exits 1.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "all-skip"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    tier2_called = {"v": False}

    def fake_t2(*a, **kw):
        tier2_called["v"] = True
        return [{"passed": True}]  # should never be reached

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"README.md"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["README.md"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               side_effect=fake_t2), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[]):
        rc = build_runner.run_build_pipeline("build")

    out = capsys.readouterr().out
    # No .py files → tier 2 SKIPPED without invoking the import checker.
    assert tier2_called["v"] is False
    # INSUFFICIENT means nothing was actually verified → rc==1.
    assert rc == 1
    assert "Tier 0 (diff nonempty) : PASSED" in out
    assert "Tier 1 (syntax)        : SKIPPED" in out
    assert "Tier 2 (imports)       : SKIPPED" in out
    assert "Tier 3 (tests)         : SKIPPED" in out
    assert "0 PASSED, 0 FAILED, 3 SKIPPED — INSUFFICIENT" in out


def test_all_tiers_pass_yields_passed_rc0(tmp_path, monkeypatch, capsys):
    """All three verify tiers PASS → summary_status=PASSED, rc==0.

    Tier 0 PASS, tier 1 non-empty all-pass, tier 2 (.py present) non-empty
    all-pass, tier 3 non-empty all-pass. passed_count=3, failed_count=0,
    skipped_count=0 → PASSED → verification_passed=True → rc==0.

    Covers requested scenario (b). See module-level DIVERGENCE NOTES for why
    this drives all three tiers to PASS rather than "one-PASS + skipped"
    (the latter yields INSUFFICIENT, same family as scenario (a)).
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "all-pass"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.build_runner._declared_scope",
               return_value={"src/foo.py"}), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.run_build_pipeline("build")

    out = capsys.readouterr().out
    assert rc == 0
    assert "Tier 0 (diff nonempty) : PASSED" in out
    assert "Tier 1 (syntax)        : PASSED" in out
    assert "Tier 2 (imports)       : PASSED" in out
    assert "Tier 3 (tests)         : PASSED" in out
    assert "3 PASSED, 0 FAILED, 0 SKIPPED — PASSED" in out


def test_tier0_failure_yields_failed_rc1(tmp_path, monkeypatch, capsys):
    """Tier 0 failure (changed_files == []) → summary_status=FAILED, rc==1.

    Empty changed_files short-circuits `_run_verify_stage`: tier 0 FAILED,
    tiers 1–3 stay at their initial SKIPPED state and are never invoked.
    failed_count=1 (tier 0), skipped_count=3 (tiers 1–3) → FAILED →
    verification_passed=False → rc==1.

    Covers requested scenario (c) — matches the implemented semantics as
    stated.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "t0-fail"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def fake_loop(params, make_response):
        return _make_response(True, {"plan_id": plan_id})

    tier1_called = {"v": False}
    tier2_called = {"v": False}
    tier3_called = {"v": False}

    def fake_t1(*a, **kw):
        tier1_called["v"] = True
        return [{"passed": True}]

    def fake_t2(*a, **kw):
        tier2_called["v"] = True
        return [{"passed": True}]

    def fake_t3(*a, **kw):
        tier3_called["v"] = True
        return [{"passed": True}]

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=[]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               side_effect=fake_t1), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               side_effect=fake_t2), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               side_effect=fake_t3):
        rc = build_runner.run_build_pipeline("build")

    out = capsys.readouterr().out
    # Tier-0 short-circuit: tiers 1–3 never invoked.
    assert tier1_called["v"] is False
    assert tier2_called["v"] is False
    assert tier3_called["v"] is False
    assert rc == 1
    assert "Tier 0 (diff nonempty) : FAILED" in out
    assert "Tier 1 (syntax)        : SKIPPED" in out
    assert "Tier 2 (imports)       : SKIPPED" in out
    assert "Tier 3 (tests)         : SKIPPED" in out
    assert "0 PASSED, 1 FAILED, 3 SKIPPED — FAILED" in out


# ── Gate requires positive evidence (regression) ─────────────────────────────

def _verify_with(tier1, tier2, tier3):
    """Run _run_verify_stage with the three substantive tiers stubbed.

    ``_declared_scope`` is stubbed to attribute ``a/b.py`` so the
    provenance-isolation split (deny-by-default on an empty declared scope)
    does not short-circuit tier 0 before the substantive tiers run — these
    tests exercise the tier 1–3 aggregation, not the tier-0 gate.
    """
    from unittest.mock import patch as _p
    with _p("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
            return_value=["a/b.py"]), \
         _p("mcp_server_nucleus.runtime.build_runner._declared_scope",
            return_value={"a/b.py"}), \
         _p("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
            return_value=tier1), \
         _p("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
            return_value=tier2), \
         _p("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
            return_value=tier3):
        return build_runner._run_verify_stage("task", "pre", "post")


def test_all_substantive_tiers_skipped_does_not_verify():
    """Zero executed tiers must NOT pass the gate.

    Regression: the predicate was `failed_count == 0`, which a run with every
    substantive tier SKIPPED satisfies vacuously — the original
    "VERIFICATION PASSED: True with tiers 2 and 3 SKIPPED" tautology. Tier 0
    (diff non-empty) passing must not rescue it.
    """
    ok, details = _verify_with([], [], [])
    assert ok is False
    assert details["summary_status"] == "INSUFFICIENT"
    assert details["passed_count"] == 0


def test_one_executed_tier_is_enough_to_verify():
    """At least one substantive tier executing with no failures verifies."""
    ok, details = _verify_with([{"passed": True}], [], [])
    assert ok is True
    assert details["passed_count"] == 1


def test_any_failure_blocks_even_with_a_pass():
    """A single FAILED tier fails the gate regardless of other passes."""
    ok, details = _verify_with([{"passed": True}], [], [{"passed": False}])
    assert ok is False
    assert details["summary_status"] == "FAILED"


# ── Stale plan detection + state updates ─────────────────────────────────────
#
# Coverage for the startup sweep that cleans up plans left IN_PROGRESS by a
# prior crashed/timed-out run, plus the _read_state/_write_state round-trip
# and _mark_plan_orphaned edge cases not already covered above.


def test_find_stale_plans_empty_when_no_plans_dir(tmp_path, monkeypatch):
    """_find_stale_plans returns [] when .brain/plans does not exist.

    No plans directory → no stale plans, no exception.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    assert build_runner._find_stale_plans() == []


def test_find_stale_plans_returns_only_in_progress(tmp_path, monkeypatch):
    """_find_stale_plans returns ONLY plans with status == IN_PROGRESS.

    APPROVED, ORPHANED, ERROR, SINGLE_VENDOR_PLAN, and REVIEWING plans are
    all skipped; only IN_PROGRESS plans are reported as stale.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    # One stale (IN_PROGRESS) plan + several non-stale plans.
    _write_state(tmp_path, "stale-a", "IN_PROGRESS")
    _write_state(tmp_path, "approved-b", "APPROVED")
    _write_state(tmp_path, "orphaned-c", "ORPHANED")
    _write_state(tmp_path, "error-d", "ERROR")
    _write_state(tmp_path, "svp-e", "SINGLE_VENDOR_PLAN")
    _write_state(tmp_path, "reviewing-f", "REVIEWING")

    stale = build_runner._find_stale_plans()
    assert stale == ["stale-a"]


def test_find_stale_plans_skips_non_dir_entries(tmp_path, monkeypatch):
    """_find_stale_plans ignores non-directory entries under .brain/plans.

    A stray file (e.g. a .gitkeep or editor temp) must not crash the scan
    and must not be reported as stale.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plans_dir = tmp_path / ".brain" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "stray-file.txt").write_text("not a plan")
    _write_state(tmp_path, "real-stale", "IN_PROGRESS")

    stale = build_runner._find_stale_plans()
    assert stale == ["real-stale"]


def test_mark_stale_plans_error_transitions_in_progress_to_error(tmp_path, monkeypatch):
    """_mark_stale_plans_error moves IN_PROGRESS plans to ERROR and returns count.

    The transitioned plan gains error_at + error_reason; the count reflects
    the number of plans actually transitioned (not the input length).
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    _write_state(tmp_path, "stale-1", "IN_PROGRESS")
    _write_state(tmp_path, "stale-2", "IN_PROGRESS")

    n = build_runner._mark_stale_plans_error(
        ["stale-1", "stale-2"], reason="test sweep",
    )

    assert n == 2
    for pid in ("stale-1", "stale-2"):
        state = build_runner._read_state(pid)
        assert state["status"] == "ERROR"
        assert state["error_reason"] == "test sweep"
        assert "error_at" in state


def test_mark_stale_plans_error_skips_terminal_statuses(tmp_path, monkeypatch):
    """_mark_stale_plans_error is idempotent — skips already-terminal plans.

    APPROVED, SINGLE_VENDOR_PLAN, ORPHANED, and ERROR plans are NOT
    re-transitioned; only the IN_PROGRESS plan in the batch is moved.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    _write_state(tmp_path, "in-progress", "IN_PROGRESS")
    _write_state(tmp_path, "approved", "APPROVED")
    _write_state(tmp_path, "orphaned", "ORPHANED")
    _write_state(tmp_path, "already-error", "ERROR")
    _write_state(tmp_path, "svp", "SINGLE_VENDOR_PLAN")

    n = build_runner._mark_stale_plans_error(
        ["in-progress", "approved", "orphaned", "already-error", "svp"],
        reason="sweep",
    )

    assert n == 1  # only in-progress transitioned
    assert build_runner._read_state("in-progress")["status"] == "ERROR"
    assert build_runner._read_state("approved")["status"] == "APPROVED"
    assert build_runner._read_state("orphaned")["status"] == "ORPHANED"
    assert build_runner._read_state("already-error")["status"] == "ERROR"
    assert build_runner._read_state("svp")["status"] == "SINGLE_VENDOR_PLAN"


def test_mark_stale_plans_error_skips_empty_and_missing_ids(tmp_path, monkeypatch):
    """_mark_stale_plans_error ignores empty-string and missing-state plan ids.

    An empty string in the batch and a plan_id with no state.json on disk
    are both skipped (no transition, no exception); the count reflects only
    real transitions.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    _write_state(tmp_path, "real-stale", "IN_PROGRESS")

    n = build_runner._mark_stale_plans_error(
        ["", "never-written", "real-stale"], reason="sweep",
    )

    assert n == 1
    assert build_runner._read_state("real-stale")["status"] == "ERROR"
    # missing plan did not create a state file
    assert build_runner._read_state("never-written") == {}


def test_mark_stale_plans_error_empty_batch_returns_zero(tmp_path, monkeypatch):
    """_mark_stale_plans_error([]) → 0, no side effects."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    assert build_runner._mark_stale_plans_error([], reason="sweep") == 0


def test_mark_stale_plans_error_without_reason_omits_field(tmp_path, monkeypatch):
    """_mark_stale_plans_error with empty reason does not set error_reason.

    The error_at timestamp is still stamped; error_reason is only written
    when a non-empty reason is supplied.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    _write_state(tmp_path, "stale", "IN_PROGRESS")

    n = build_runner._mark_stale_plans_error(["stale"])

    assert n == 1
    state = build_runner._read_state("stale")
    assert state["status"] == "ERROR"
    assert "error_at" in state
    assert "error_reason" not in state


def test_write_state_round_trip_preserves_fields(tmp_path, monkeypatch):
    """_write_state then _read_state returns the same dict, fields intact.

    Covers the atomic-write happy path: a non-trivial state dict with
    nested values survives the temp-file + rename round-trip.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_id = "round-trip"
    payload = {
        "plan_id": plan_id,
        "status": "APPROVED",
        "round": 3,
        "final_plan_path": "/some/path.md",
        "nested": {"a": [1, 2, 3], "b": True},
    }
    build_runner._write_state(plan_id, payload)

    read_back = build_runner._read_state(plan_id)
    assert read_back == payload


def test_write_state_overwrites_existing(tmp_path, monkeypatch):
    """_write_state replaces the prior state.json contents entirely.

    A second write with a different status must not merge with or retain
    fields from the first write — the file reflects only the latest payload.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_id = "overwrite"
    build_runner._write_state(plan_id, {"status": "IN_PROGRESS", "round": 1})
    build_runner._write_state(plan_id, {"status": "APPROVED", "round": 2})

    state = build_runner._read_state(plan_id)
    assert state == {"status": "APPROVED", "round": 2}


def test_read_state_returns_empty_on_corrupt_json(tmp_path, monkeypatch):
    """_read_state returns {} when state.json contains invalid JSON.

    Inverse of the round-trip test: a corrupt file must not raise; the
    warning is logged and {} is returned so callers treat it as a miss.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_dir = tmp_path / ".brain" / "plans" / "corrupt"
    plan_dir.mkdir(parents=True)
    (plan_dir / "state.json").write_text("{not valid json")

    assert build_runner._read_state("corrupt") == {}


def test_mark_plan_orphaned_skips_empty_plan_id(tmp_path, monkeypatch):
    """_mark_plan_orphaned('') is a no-op — no file written, no exception.

    Guards the early-return guard at the top of the function.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    build_runner._mark_plan_orphaned("")
    # No plans directory should have been created for an empty plan_id.
    assert not (tmp_path / ".brain" / "plans").exists()


def test_mark_plan_orphaned_skips_missing_state(tmp_path, monkeypatch):
    """_mark_plan_orphaned on a plan with no state.json is a no-op.

    _read_state returns {} for a missing file; the function returns early
    without writing anything.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    build_runner._mark_plan_orphaned("never-written")
    assert build_runner._read_state("never-written") == {}


def test_mark_plan_orphaned_skips_already_orphaned(tmp_path, monkeypatch):
    """_mark_plan_orphaned does not re-stamp an already-ORPHANED plan.

    Idempotency: a second call on an ORPHANED plan must not update
    orphaned_at or otherwise mutate the state.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_id = "already-orphaned"
    build_runner._write_state(plan_id, {
        "status": "ORPHANED",
        "orphaned_at": 1000,
    })

    build_runner._mark_plan_orphaned(plan_id)

    state = build_runner._read_state(plan_id)
    assert state["status"] == "ORPHANED"
    assert state["orphaned_at"] == 1000  # unchanged


def test_mark_plan_orphaned_on_in_progress(tmp_path, monkeypatch):
    """_mark_plan_orphaned transitions IN_PROGRESS → ORPHANED.

    The canonical case: a plan mid-flight when the process exits gets
    stamped ORPHANED with an orphaned_at timestamp.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    plan_id = "in-progress-orphan"
    build_runner._write_state(plan_id, {
        "plan_id": plan_id,
        "status": "IN_PROGRESS",
        "round": 2,
    })

    build_runner._mark_plan_orphaned(plan_id)

    state = build_runner._read_state(plan_id)
    assert state["status"] == "ORPHANED"
    assert "orphaned_at" in state
    assert state["plan_id"] == plan_id
    assert state["round"] == 2


def test_build_pipeline_sweeps_stale_plans_before_new_run(tmp_path, monkeypatch, capsys):
    """run_build_pipeline marks pre-existing IN_PROGRESS plans ERROR on startup.

    The stale-plan sweep runs before the PLAN stage: a leftover IN_PROGRESS
    plan from a prior crashed run is transitioned to ERROR, and the sweep
    count is printed. The new run then proceeds (here it aborts at PLAN
    stage via the mocked loop, so rc == 1 — but the sweep still fired).
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    # Leftover stale plan from a prior run.
    _write_state(tmp_path, "leftover-stale", "IN_PROGRESS")

    def fake_loop(params, make_response):
        return _make_response(False, error="forced plan-stage abort for test")

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True):
        rc = build_runner.run_build_pipeline("a real task prompt")

    # Sweep fired: leftover plan is now ERROR, sweep message printed.
    assert build_runner._read_state("leftover-stale")["status"] == "ERROR"
    out = capsys.readouterr().out
    assert "marked 1 stale plan(s) ERROR" in out
    # PLAN stage aborted (mocked) → rc 1, but AFTER the sweep ran.
    assert rc == 1


def test_build_pipeline_sweep_is_idempotent_across_runs(tmp_path, monkeypatch, capsys):
    """A second run does not re-transition plans already marked ERROR.

    After the first run sweeps a stale plan to ERROR, a second run finds
    zero stale plans (the prior one is now terminal) and prints no sweep
    message.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    _write_state(tmp_path, "stale-once", "IN_PROGRESS")

    def fake_loop(params, make_response):
        return _make_response(False, error="abort")

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_loop), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True):
        build_runner.run_build_pipeline("first run")
        capsys.readouterr()  # drain first run's output
        build_runner.run_build_pipeline("second run")

    second_out = capsys.readouterr().out
    # Second run found no IN_PROGRESS plans → no sweep message.
    assert "stale plan(s) ERROR" not in second_out
    # The plan is still ERROR from the first sweep (not re-stamped).
    assert build_runner._read_state("stale-once")["status"] == "ERROR"


# ── verdict-card tier-line rendering: UNRUNNABLE + FAILED tails ───────────────
#
# Direct unit tests of `_render_verdict_card` covering the inline
# `_print_tier_line` helper:
#   (1) Tier 3 FAILED with an `unrunnable=True` signal renders
#       `FAILED (UNRUNNABLE — pytest not available in <python>)` instead of
#       bare `FAILED`, and still prints the signal's output tail.
#   (2) Any FAILED tier prints an indented tail (last 200 chars) of each
#       signal's `output` (falling back to `error` when `output` is absent).
#   (3) PASSED and SKIPPED tier lines are byte-identical to the original
#       hardcoded format — no tails, no parenthetical.


def _verdict_card_dto(tmp_path, results=None):
    """Build the minimal DTO tuple for a direct `_render_verdict_card` call.

    Returns ``(final_plan_path, results)`` — the caller supplies its own
    ``verify_details`` since each test exercises a different tier shape.
    """
    fp = tmp_path / "final_plan.md"
    fp.write_text("# Plan\n- [ ] Task 1: write foo\n", encoding="utf-8")
    if results is None:
        results = [{
            "task_num": 1,
            "task_desc": "write foo",
            "vendor": "devin",
            "result": {"status": "ok", "produced_output": True},
        }]
    return fp, results


def test_tier3_unrunnable_renders_named_verdict(tmp_path, capsys):
    """Tier 3 FAILED + unrunnable signal → `FAILED (UNRUNNABLE — pytest not
    available in <python>)` plus the signal's output tail.

    The bare `FAILED` substring must NOT appear on the Tier 3 line; the
    UNRUNNABLE parenthetical replaces it. The signal's `output` tail is still
    printed indented beneath the line.
    """
    fp, results = _verdict_card_dto(tmp_path)
    long_output = "X" * 250 + "no module named pytest" + "Y" * 50
    verify_details = {
        "changed_files": ["src/foo.py"],
        "tier0": {"status": "PASSED"},
        "tier1": {"status": "PASSED"},
        "tier2": {"status": "PASSED"},
        "tier3": {
            "status": "FAILED",
            "signals": [{
                "tier": 3, "check": "pytest", "file": "tests/test_foo.py",
                "passed": False, "unrunnable": True,
                "python": "/opt/venv/bin/python3.11",
                "output": long_output,
                "reason": "pytest_not_available",
            }],
        },
        "passed_count": 3, "failed_count": 1, "skipped_count": 0,
        "summary_status": "FAILED",
    }

    rc = build_runner._render_verdict_card(
        task_prompt="build foo",
        final_plan_path=fp,
        pre_head="abc123",
        post_head="def456",
        results=results,
        verification_passed=False,
        verify_details=verify_details,
        execution_mode=build_runner._MODE_DUAL_VENDOR,
    )

    out = capsys.readouterr().out
    assert rc == 1  # FAILED → exit 1
    # The UNRUNNABLE named verdict appears with the python path.
    assert ("Tier 3 (tests)         : FAILED (UNRUNNABLE — pytest not "
            "available in /opt/venv/bin/python3.11)") in out
    # Bare "Tier 3 (tests)         : FAILED" (without the parenthetical) does
    # NOT appear — the unrunnable path replaced it.
    assert "Tier 3 (tests)         : FAILED\n" not in out
    # The signal's output tail is printed indented (last 200 chars of output).
    expected_tail = long_output[-200:]
    assert expected_tail in out


def test_failed_tier_prints_indented_output_tail(tmp_path, capsys):
    """Any FAILED tier prints an indented tail (last 200 chars) of each
    signal's `output`.

    Tier 1 FAILED with two signals: both output tails appear indented beneath
    the tier line. PASSED/SKIPPED tiers emit no tails.
    """
    fp, results = _verdict_card_dto(tmp_path)
    verify_details = {
        "changed_files": ["src/foo.py"],
        "tier0": {"status": "PASSED"},
        "tier1": {
            "status": "FAILED",
            "signals": [
                {"tier": 1, "check": "py_compile", "file": "src/foo.py",
                 "passed": False, "output": "SyntaxError: invalid syntax at line 42"},
                {"tier": 1, "check": "py_compile", "file": "src/bar.py",
                 "passed": False, "output": "IndentationError: unexpected indent"},
            ],
        },
        "tier2": {"status": "SKIPPED", "signals": [], "reason": "no .py files"},
        "tier3": {"status": "SKIPPED", "signals": []},
        "passed_count": 1, "failed_count": 1, "skipped_count": 2,
        "summary_status": "FAILED",
    }

    rc = build_runner._render_verdict_card(
        task_prompt="build foo",
        final_plan_path=fp,
        pre_head="abc123",
        post_head="def456",
        results=results,
        verification_passed=False,
        verify_details=verify_details,
        execution_mode=build_runner._MODE_DUAL_VENDOR,
    )

    out = capsys.readouterr().out
    assert rc == 1
    # Tier 1 FAILED base line is present.
    assert "Tier 1 (syntax)        : FAILED" in out
    # Both signal output tails appear indented (8-space indent).
    assert "        SyntaxError: invalid syntax at line 42" in out
    assert "        IndentationError: unexpected indent" in out
    # SKIPPED tiers emit no tails (no indented lines under them).
    assert "Tier 2 (imports)       : SKIPPED" in out
    assert "Tier 3 (tests)         : SKIPPED" in out


def test_failed_tier_falls_back_to_error_when_no_output(tmp_path, capsys):
    """When a signal has no `output`, the tail falls back to `error`.

    Tier 2 FAILED with a timeout signal (has `error`, no `output`): the
    `error` value appears as the indented tail.
    """
    fp, results = _verdict_card_dto(tmp_path)
    verify_details = {
        "changed_files": ["src/foo.py"],
        "tier0": {"status": "PASSED"},
        "tier1": {"status": "PASSED"},
        "tier2": {
            "status": "FAILED",
            "signals": [{
                "tier": 2, "check": "import", "module": "foo",
                "passed": False, "error": "timeout",
            }],
        },
        "tier3": {"status": "SKIPPED", "signals": []},
        "passed_count": 2, "failed_count": 1, "skipped_count": 1,
        "summary_status": "FAILED",
    }

    rc = build_runner._render_verdict_card(
        task_prompt="build foo",
        final_plan_path=fp,
        pre_head="abc123",
        post_head="def456",
        results=results,
        verification_passed=False,
        verify_details=verify_details,
        execution_mode=build_runner._MODE_DUAL_VENDOR,
    )

    out = capsys.readouterr().out
    assert rc == 1
    assert "Tier 2 (imports)       : FAILED" in out
    # `error` fallback appears indented.
    assert "        timeout" in out


def test_passed_and_skipped_tier_lines_unchanged(tmp_path, capsys):
    """PASSED and SKIPPED tier lines are byte-identical to the original
    hardcoded format — no tails, no parenthetical, even when signals carry
    output.

    Regression guard: the `_print_tier_line` helper must not emit tails or
    alter the status text for non-FAILED tiers.
    """
    fp, results = _verdict_card_dto(tmp_path)
    verify_details = {
        "changed_files": ["src/foo.py"],
        "tier0": {"status": "PASSED"},
        "tier1": {"status": "PASSED", "signals": [{"passed": True, "output": "ok"}]},
        "tier2": {"status": "SKIPPED", "signals": [], "reason": "no .py files"},
        "tier3": {"status": "SKIPPED", "signals": []},
        "passed_count": 2, "failed_count": 0, "skipped_count": 1,
        "summary_status": "INSUFFICIENT",
    }

    build_runner._render_verdict_card(
        task_prompt="build foo",
        final_plan_path=fp,
        pre_head="abc123",
        post_head="def456",
        results=results,
        verification_passed=True,
        verify_details=verify_details,
        execution_mode=build_runner._MODE_DUAL_VENDOR,
    )

    out = capsys.readouterr().out
    # Exact original format — no tails beneath PASSED/SKIPPED lines.
    assert "    Tier 0 (diff nonempty) : PASSED\n" in out
    assert "    Tier 1 (syntax)        : PASSED\n" in out
    assert "    Tier 2 (imports)       : SKIPPED\n" in out
    assert "    Tier 3 (tests)         : SKIPPED\n" in out
    # The PASSED tier's signal output must NOT leak as a tail.
    assert "        ok" not in out


# ── Stale sweep must not kill LIVE concurrent builds ─────────────────────────
#
# Regression guard. The first version of the sweep treated status ==
# IN_PROGRESS as sufficient, which is the dead plans UNION the live ones, so
# whichever build started second silently marked a healthy parallel build's
# plan ERROR. The victim reported "PLAN stage failed — plan review aborted"
# and sent the reader to the wrong subsystem entirely.


def test_find_stale_plans_spares_a_plan_owned_by_a_live_process(tmp_path, monkeypatch):
    """A plan whose owner_pid is alive is being worked on — never sweep it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    # Old enough to trip the age threshold, but explicitly owned by us.
    _write_state(tmp_path, "live-plan", "IN_PROGRESS",
                 age_s=7200, owner_pid=os.getpid())

    assert build_runner._find_stale_plans() == []


def test_find_stale_plans_sweeps_a_plan_whose_owner_is_gone(tmp_path, monkeypatch):
    """The control: a dead owner must STILL be swept.

    Without this, "never sweep anything" would satisfy the test above and
    quietly restore the orphan bug the sweep exists to solve.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    proc = subprocess.Popen(["/usr/bin/true"])
    proc.wait()  # reaped — this pid is genuinely gone
    _write_state(tmp_path, "dead-plan", "IN_PROGRESS",
                 age_s=7200, owner_pid=proc.pid)

    assert build_runner._find_stale_plans() == ["dead-plan"]


def test_find_stale_plans_spares_a_recently_written_unowned_plan(tmp_path, monkeypatch):
    """Plans predating owner_pid get a grace window instead of instant death."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))

    _write_state(tmp_path, "fresh-plan", "IN_PROGRESS", age_s=0)

    assert build_runner._find_stale_plans() == []


# ── Declared scope: polarity ─────────────────────────────────────────────────
#
# _declared_scope harvested every path token regardless of the words around
# it, so "In A ONLY. DENY-LIST: do not touch B" declared BOTH A and B as
# in-scope and editing B raised no violation. The sentence written to tighten
# the constraint was the one that loosened it — and the build skill instructs
# authors to write exactly that sentence.


def test_declared_scope_excludes_deny_listed_paths():
    """A path named in a DENY-LIST segment must not become allowed scope."""
    declared = build_runner._declared_scope(
        "In providers/brain_rag.py ONLY. DENY-LIST: do not touch a/b.py."
    )
    assert declared == {"providers/brain_rag.py"}


def test_deny_listed_path_is_reported_as_a_violation():
    """End to end: editing a deny-listed file must be flagged."""
    prompt = "In providers/brain_rag.py ONLY. DENY-LIST: do not touch a/b.py."
    declared = build_runner._declared_scope(prompt)
    assert build_runner._scope_violations(["a/b.py"], declared) == ["a/b.py"]


def test_declared_scope_without_a_deny_list_is_unchanged():
    """Control: the ordinary positive case must not regress.

    Without this, 'return an empty set always' would satisfy the two tests
    above while disabling scope declaration entirely.
    """
    declared = build_runner._declared_scope("In providers/brain_rag.py ONLY.")
    assert declared == {"providers/brain_rag.py"}


def test_deny_list_naming_no_paths_leaves_scope_intact():
    """A deny-list with no path tokens must not strip the declared scope."""
    declared = build_runner._declared_scope(
        "In providers/brain_rag.py ONLY. DENY-LIST: every other file."
    )
    assert declared == {"providers/brain_rag.py"}


def test_declared_scope_handles_multiline_prompts():
    """Real prompts put the deny-list on its own line."""
    declared = build_runner._declared_scope(
        "In providers/brain_rag.py ONLY.\n"
        "DENY-LIST: do not touch a/b.py, do not touch c/d.py.\n"
        "Add a docstring."
    )
    assert declared == {"providers/brain_rag.py"}


def test_prompt_with_only_a_prohibited_path_declares_nothing():
    """KNOWN LIMITATION, asserted so it is a decision and not a surprise.

    A prompt whose only path sits in a negative clause declares no positive
    scope, so the result is empty — which is PERMISSIVE per this function's
    contract. It does not protect that path. Protecting it would require
    threading a deny-set through to _scope_violations, which this change
    deliberately does not do. Previously the path was treated as ALLOWED,
    which was strictly worse.
    """
    assert build_runner._declared_scope("Do not modify a/b.py.") == set()
