"""Regression tests for ORPHANED-plan resume (``resume_build_pipeline``).

THE DEFECT: ``build_runner`` marks plans ORPHANED (terminal) when the
process exits while a plan is IN_PROGRESS, but there was no resume path —
the completed plan-authoring work (approved ``final_plan.md``) and any
partially-completed execute-stage tasks were unrecoverable. The only
option was to start a fresh build with a new plan_id.

THE FIX: ``resume_build_pipeline(plan_id)`` reloads an ORPHANED plan's
persisted state and re-enters the pipeline at the EXECUTE stage. Tasks
already completed during the prior run were marked ``- [x]`` in
``final_plan.md`` (by ``_record_task_completed``), so
``_parse_task_checkboxes`` naturally skips them — execution continues
from the first unchecked task instead of restarting from task 0.

Each test states its failure direction; a check that can only pass is
not a check. Mocks the vendor + verification seams — ZERO live vendor
calls, no real git mutations. Uses tmp_path + monkeypatch.chdir for cwd
isolation, matching sibling test idioms (``test_cli_build.py``).
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime import build_runner


# ── Isolation ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_brain(tmp_path, monkeypatch):
    """Pin brain resolution to tmp_path so tests never touch the real .brain."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    monkeypatch.setattr(build_runner, "_PLAN_POLL_TIMEOUT_S", 3)
    monkeypatch.setattr(build_runner, "_PLAN_POLL_INTERVAL_S", 0.05)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ok_dispatch():
    """A dispatch_and_capture mock returning a passing result."""
    return {"status": "ok", "produced_output": True, "vendor": "devin", "rc": 0}


def _write_state(tmp_path: Path, plan_id: str, status: str, **extra) -> None:
    """Write .brain/plans/<plan_id>/state.json under tmp_path."""
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    state = {"plan_id": plan_id, "status": status}
    state.update(extra)
    (plans_dir / "state.json").write_text(json.dumps(state))


def _write_plan(tmp_path: Path, plan_id: str, tasks: list) -> Path:
    """Write a final_plan.md with the given (task_num, desc, checked) tuples.

    Each tuple is (task_num, description, checked_bool). Unchecked tasks
    use ``- [ ]``, checked tasks use ``- [x]``.
    """
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    fp = plans_dir / "final_plan.md"
    lines = ["# Plan\n"]
    for n, desc, checked in tasks:
        box = "[x]" if checked else "[ ]"
        lines.append(f"- {box} Task {n}: {desc}")
    fp.write_text("\n".join(lines) + "\n")
    return fp


# ── _mark_task_done unit tests ───────────────────────────────────────────────

def test_mark_task_done_flips_unchecked_to_checked(tmp_path):
    """POSITIVE: _mark_task_done flips - [ ] to - [x] for the named task."""
    fp = tmp_path / "final_plan.md"
    fp.write_text("- [ ] Task 1: do thing one\n- [ ] Task 2: do thing two\n")
    result = build_runner._mark_task_done(fp, 1)
    assert result is True
    text = fp.read_text()
    assert "- [x] Task 1: do thing one" in text
    assert "- [ ] Task 2: do thing two" in text


def test_mark_task_done_tolerates_bold_label(tmp_path):
    """The bold-label format (**Task N:**) that _parse_task_checkboxes
    tolerates must also be flippable by _mark_task_done."""
    fp = tmp_path / "final_plan.md"
    fp.write_text("- [ ] **Task 0:** confirm path\n")
    result = build_runner._mark_task_done(fp, 0)
    assert result is True
    assert "- [x] **Task 0:** confirm path" in fp.read_text()


def test_mark_task_done_returns_false_for_missing_task(tmp_path):
    """NEGATIVE: a task_num not in the file returns False, file unchanged."""
    fp = tmp_path / "final_plan.md"
    original = "- [ ] Task 1: only task\n"
    fp.write_text(original)
    result = build_runner._mark_task_done(fp, 99)
    assert result is False
    assert fp.read_text() == original


def test_mark_task_done_only_flips_named_task(tmp_path):
    """NEGATIVE: marking task 2 must NOT also mark task 1."""
    fp = tmp_path / "final_plan.md"
    fp.write_text("- [ ] Task 1: first\n- [ ] Task 2: second\n")
    build_runner._mark_task_done(fp, 2)
    text = fp.read_text()
    assert "- [ ] Task 1: first" in text
    assert "- [x] Task 2: second" in text


# ── _record_task_completed unit tests ────────────────────────────────────────

def test_record_task_completed_noop_when_plan_id_none(tmp_path):
    """When plan_id is None, no file or state is touched."""
    fp = tmp_path / "final_plan.md"
    fp.write_text("- [ ] Task 1: do thing\n")
    original = fp.read_text()
    build_runner._record_task_completed(None, fp, 1)
    assert fp.read_text() == original


def test_record_task_completed_marks_plan_and_state(tmp_path, monkeypatch):
    """When plan_id is set, final_plan.md gets - [x] and state.json gets
    completed_tasks."""
    monkeypatch.chdir(tmp_path)
    plan_id = "rec-test"
    fp = _write_plan(tmp_path, plan_id, [(1, "first", False), (2, "second", False)])
    _write_state(tmp_path, plan_id, "IN_PROGRESS")

    build_runner._record_task_completed(plan_id, fp, 1)

    # final_plan.md: task 1 is now checked
    text = fp.read_text()
    assert "- [x] Task 1: first" in text
    assert "- [ ] Task 2: second" in text
    # state.json: completed_tasks includes 1
    state = build_runner._read_state(plan_id)
    assert state["completed_tasks"] == [1]


def test_record_task_completed_is_idempotent(tmp_path, monkeypatch):
    """Recording the same task twice does not duplicate it in completed_tasks."""
    monkeypatch.chdir(tmp_path)
    plan_id = "idempotent-test"
    fp = _write_plan(tmp_path, plan_id, [(1, "only", False)])
    _write_state(tmp_path, plan_id, "IN_PROGRESS")

    build_runner._record_task_completed(plan_id, fp, 1)
    build_runner._record_task_completed(plan_id, fp, 1)

    state = build_runner._read_state(plan_id)
    assert state["completed_tasks"] == [1]


# ── resume_build_pipeline integration tests ─────────────────────────────────

def test_resume_skips_completed_tasks(tmp_path, monkeypatch):
    """THE CORE REGRESSION: resume continues from the last completed task.

    A plan with tasks 1-3 where task 1 is already marked - [x] (completed
    in the prior run before it was orphaned). Resume should dispatch
    only tasks 2 and 3, NOT task 1.
    """
    monkeypatch.chdir(tmp_path)
    plan_id = "resume-skip"
    fp = _write_plan(tmp_path, plan_id, [
        (1, "already done", True),
        (2, "needs doing", False),
        (3, "also needs doing", False),
    ])
    _write_state(
        tmp_path, plan_id, "ORPHANED",
        final_plan_path=str(fp),
        execution_mode="dual-vendor",
        task_prompt="build src/foo.py",
        completed_tasks=[1],
    )

    dispatched = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        dispatched.append(prompt)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        rc = build_runner.resume_build_pipeline(plan_id)

    # Task 1 was skipped (already - [x]); only tasks 2 and 3 dispatched.
    assert dispatched == ["needs doing", "also needs doing"], (
        f"expected tasks 2 and 3 only, got {dispatched!r}"
    )
    assert rc == 0


def test_resume_transitions_orphaned_to_in_progress(tmp_path, monkeypatch):
    """Resume transitions the plan from ORPHANED to IN_PROGRESS on entry."""
    monkeypatch.chdir(tmp_path)
    plan_id = "transition-test"
    fp = _write_plan(tmp_path, plan_id, [(1, "only task", False)])
    _write_state(
        tmp_path, plan_id, "ORPHANED",
        final_plan_path=str(fp),
        execution_mode="dual-vendor",
        task_prompt="build",
    )

    captured_status = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        # Read state mid-dispatch to verify it transitioned
        st = build_runner._read_state(plan_id)
        captured_status.append(st.get("status"))
        return _ok_dispatch()

    with patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        build_runner.resume_build_pipeline(plan_id)

    assert captured_status == ["IN_PROGRESS"], (
        f"plan was not IN_PROGRESS during resume, got {captured_status!r}"
    )


def test_resume_marks_remaining_tasks_done(tmp_path, monkeypatch):
    """After resume completes, all remaining tasks are marked - [x] in
    final_plan.md and recorded in state.json completed_tasks."""
    monkeypatch.chdir(tmp_path)
    plan_id = "mark-done-test"
    fp = _write_plan(tmp_path, plan_id, [
        (1, "done before", True),
        (2, "done now", False),
    ])
    _write_state(
        tmp_path, plan_id, "ORPHANED",
        final_plan_path=str(fp),
        execution_mode="dual-vendor",
        task_prompt="build",
        completed_tasks=[1],
    )

    with patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=["src/foo.py"]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
               return_value=[{"passed": True}]), \
         patch("mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
               return_value=[{"passed": True}]):
        build_runner.resume_build_pipeline(plan_id)

    text = fp.read_text()
    assert "- [x] Task 1: done before" in text
    assert "- [x] Task 2: done now" in text
    state = build_runner._read_state(plan_id)
    assert 1 in state.get("completed_tasks", [])
    assert 2 in state.get("completed_tasks", [])


# ── resume_build_pipeline guard tests ───────────────────────────────────────

def test_resume_rejects_empty_plan_id(tmp_path, monkeypatch):
    """NEGATIVE: empty plan_id returns exit code 2, not 0."""
    monkeypatch.chdir(tmp_path)
    rc = build_runner.resume_build_pipeline("")
    assert rc == 2


def test_resume_rejects_missing_state(tmp_path, monkeypatch):
    """NEGATIVE: a plan_id with no state.json returns 2, not 0."""
    monkeypatch.chdir(tmp_path)
    rc = build_runner.resume_build_pipeline("nonexistent-plan")
    assert rc == 2


def test_resume_rejects_non_orphaned_status(tmp_path, monkeypatch):
    """NEGATIVE: APPROVED (success) is not resumable — returns 2."""
    monkeypatch.chdir(tmp_path)
    plan_id = "approved-plan"
    fp = _write_plan(tmp_path, plan_id, [(1, "task", False)])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    rc = build_runner.resume_build_pipeline(plan_id)
    assert rc == 2


def test_resume_rejects_error_status(tmp_path, monkeypatch):
    """NEGATIVE: ERROR (stale sweep) is not resumable — returns 2."""
    monkeypatch.chdir(tmp_path)
    plan_id = "error-plan"
    _write_state(tmp_path, plan_id, "ERROR")

    rc = build_runner.resume_build_pipeline(plan_id)
    assert rc == 2


def test_resume_rejects_orphaned_without_final_plan(tmp_path, monkeypatch):
    """NEGATIVE: ORPHANED but final_plan.md missing on disk returns 2."""
    monkeypatch.chdir(tmp_path)
    plan_id = "orphaned-no-file"
    _write_state(
        tmp_path, plan_id, "ORPHANED",
        final_plan_path=str(tmp_path / ".brain" / "plans" / plan_id / "final_plan.md"),
    )
    # Do NOT write final_plan.md — state references a nonexistent file.

    rc = build_runner.resume_build_pipeline(plan_id)
    assert rc == 2


def test_resume_all_tasks_already_done_aborts_execute(tmp_path, monkeypatch):
    """When ALL tasks are already - [x], resume's execute stage finds zero
    unchecked tasks and aborts (rc 1) — same as run_build_pipeline."""
    monkeypatch.chdir(tmp_path)
    plan_id = "all-done"
    fp = _write_plan(tmp_path, plan_id, [
        (1, "done one", True),
        (2, "done two", True),
    ])
    _write_state(
        tmp_path, plan_id, "ORPHANED",
        final_plan_path=str(fp),
        execution_mode="dual-vendor",
        task_prompt="build",
        completed_tasks=[1, 2],
    )

    dispatched = []

    def fake_dispatch(vendor, prompt, artifact_ref, *, mode=None, **kw):
        dispatched.append(prompt)
        return _ok_dispatch()

    with patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               side_effect=fake_dispatch), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123"):
        rc = build_runner.resume_build_pipeline(plan_id)

    assert dispatched == []  # nothing to dispatch
    assert rc == 1  # EXECUTE aborts: no unchecked checkboxes
