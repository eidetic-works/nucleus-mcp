"""Regression test: plan_review_loop output round-trips through plan_ops.

Verifies that a plan file formatted per the ``_AUTHOR_PREAMBLE`` template in
``mcp_server_nucleus.tools.plan_review_loop`` (i.e. ``## Implementation Steps``
with ``- [ ] Task N: <description>`` checkboxes) is correctly parsed by the
REAL ``plan_ops.import_plan_as_tasks`` path and ``_TASKS_CHECKBOX_RE`` regex.

No mocks or stubs of the parser are used — the exercise is end-to-end through
the production ``import_plan_as_tasks`` → ``_parse_plan`` → ``_TASKS_CHECKBOX_RE``
→ ``task_ops._add_task`` chain.

Context: ``plan_review_loop.py`` previously instructed authors to emit bare
``- [ ] <description>`` checkboxes, but ``plan_ops._TASKS_CHECKBOX_RE`` requires
the explicit ``Task N:`` prefix. The mismatch caused
``import_plan_as_tasks`` to parse zero tasks and fail with
``No parseable tasks found``. This test pins the corrected format.
"""

import os
from pathlib import Path

import pytest


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Isolated brain directory so task_ops._add_task writes to tmp, not prod."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "sessions").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


def test_plan_review_loop_format_imports_via_plan_ops(brain_path, tmp_path):
    """A plan_review_loop-formatted plan must round-trip through plan_ops.

    Builds a markdown sample matching the corrected ``_AUTHOR_PREAMBLE``
    template (``- [ ] Task N: <description>`` under ``## Implementation Steps``),
    runs it through the REAL ``plan_ops.import_plan_as_tasks`` /
    ``_TASKS_CHECKBOX_RE`` path (no parser mocks), and asserts:
      - ``success`` is ``True``
      - exactly 3 tasks are extracted (``count == 3``)
      - task descriptions match the expected text WITHOUT the ``Task N:`` prefix
    """
    from mcp_server_nucleus.runtime import plan_ops

    plan_md = """# Implementation Plan: Add Foo Module

## Context & Problem Statement
We need a foo module with an entry point, tests, and docs.

## Solution Strategy
Build ``src/foo.py``, add unit tests, and document usage.

## Implementation Steps

- [ ] Task 1: Create src/foo.py with the entry point
- [ ] Task 2: Add unit tests in tests/test_foo.py
- [ ] Task 3: Update README.md with usage docs

## Verification Plan
Run ``pytest tests/test_foo.py`` and confirm the entry point works.
"""
    plan_file = tmp_path / "sample_plan.md"
    plan_file.write_text(plan_md, encoding="utf-8")

    # Sanity: the regex itself recognizes each line (no parser stubs anywhere).
    re_compiled = plan_ops._TASKS_CHECKBOX_RE
    matches = [re_compiled.match(line) for line in plan_md.splitlines()]
    matched_lines = [m for m in matches if m]
    assert len(matched_lines) == 3, (
        f"_TASKS_CHECKBOX_RE should match all 3 Task N: lines, got {len(matched_lines)}"
    )
    expected_descriptions = [
        "Create src/foo.py with the entry point",
        "Add unit tests in tests/test_foo.py",
        "Update README.md with usage docs",
    ]
    actual_descriptions = [m.group(1).strip() for m in matched_lines]
    assert actual_descriptions == expected_descriptions

    # End-to-end: real import_plan_as_tasks → _parse_plan → _add_task.
    result = plan_ops.import_plan_as_tasks(str(plan_file))

    assert result.get("success") is True, (
        f"import_plan_as_tasks should succeed; got: {result}"
    )
    assert result.get("count") == 3, (
        f"expected 3 tasks imported, got count={result.get('count')}: {result}"
    )
    task_ids = result.get("task_ids", [])
    assert len(task_ids) == 3, (
        f"expected 3 task_ids, got {len(task_ids)}: {result}"
    )

    # Confirm the descriptions landed in the task store without the Task N: prefix.
    from mcp_server_nucleus.runtime import task_ops
    for tid, expected in zip(task_ids, expected_descriptions):
        stored = task_ops._list_tasks()
        found = next((t for t in stored if t.get("id") == tid), None)
        assert found is not None, f"task {tid} not found in store"
        assert found["description"] == expected, (
            f"task description mismatch: expected {expected!r}, "
            f"got {found['description']!r}"
        )


def test_bare_checkbox_format_is_not_misimported(brain_path, tmp_path):
    """Negative control: the OLD bare ``- [ ] <desc>`` format must NOT import.

    This pins the contract that ``_TASKS_CHECKBOX_RE`` requires the
    ``Task N:`` prefix — loosening it would mis-import arbitrary checklists.
    """
    from mcp_server_nucleus.runtime import plan_ops

    plan_md = """# Plan

## Implementation Steps
- [ ] Create src/foo.py with the entry point
- [ ] Add unit tests in tests/test_foo.py
- [ ] Update README.md with usage docs
"""
    plan_file = tmp_path / "bare_plan.md"
    plan_file.write_text(plan_md, encoding="utf-8")

    result = plan_ops.import_plan_as_tasks(str(plan_file))
    assert result.get("success") is False, (
        f"bare checkbox format must NOT import (would mis-import checklists); "
        f"got: {result}"
    )
