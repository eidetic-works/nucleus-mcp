"""_parse_task_checkboxes must tolerate markdown-bolded "Task N:" labels.

THE DEFECT (four confirmed occurrences, most recently 2026-08-16): the
plan-author stage's own output legitimately bolds the task label
(`**Task 0:**`), which the old strict-plaintext regex did not match at all --
zero tasks parsed from a real, well-formed plan, silently reported as
"no unchecked Task N: checkboxes found", exit 0, nothing built.

Each test states its failure direction; a check that can only pass is not a
check.
"""

import tempfile
from pathlib import Path

from mcp_server_nucleus.runtime.build_runner import _parse_task_checkboxes


def _write(text: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    f.write(text)
    f.close()
    return Path(f.name)


def test_plain_format_still_parses():
    """POSITIVE: the original, always-worked format must not regress."""
    p = _write("- [ ] Task 1: do the thing\n- [x] Task 2: already done\n")
    tasks = _parse_task_checkboxes(p)
    assert tasks == [(1, "do the thing")], (
        "plain '- [ ] Task N:' format regressed — checked Task 2 must be excluded"
    )


def test_bold_format_now_parses():
    """THE BUG: devin's real output bolds the label. Must no longer be zero."""
    p = _write("- [ ] **Task 0:** Confirm the path of `receipt_gate.py`.\n")
    tasks = _parse_task_checkboxes(p)
    assert tasks == [(0, "Confirm the path of `receipt_gate.py`.")], (
        f"bold '**Task N:**' still fails to parse — got {tasks!r}"
    )


def test_asterisks_inside_description_are_preserved():
    """OPPOSED: only the marker adjacent to 'Task N:' is consumed, not every '*'."""
    p = _write("- [ ] **Task 5:** **Important:** verify `a * b` still works\n")
    tasks = _parse_task_checkboxes(p)
    assert tasks == [(5, "**Important:** verify `a * b` still works")], (
        f"description content was mangled — got {tasks!r}"
    )


def test_real_devin_plan_from_this_session_parses_nonzero():
    """The actual plan that triggered the original false-negative bug report."""
    real_plan_lines = [
        "- [ ] **Task 0:** Confirm the path of `.claude/hooks/receipt_gate.py`.",
        "- [ ] **Task 1:** Add three fields to each hook's per-session state.",
        "- [x] **Task 2:** Already-completed task must be excluded.",
    ]
    p = _write("\n".join(real_plan_lines) + "\n")
    tasks = _parse_task_checkboxes(p)
    assert len(tasks) == 2, f"expected 2 unchecked tasks, got {len(tasks)}: {tasks!r}"
    assert tasks[0][0] == 0 and tasks[1][0] == 1
