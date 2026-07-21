"""SPEC.md validator — checks spec format without raising on soft issues.

The :class:`SpecParser` raises :class:`SpecParseError` on the first problem it
encounters (missing acceptance criteria, malformed blocks, etc.). That is the
right behaviour for the *execution* path — a lane cannot start against a spec
it cannot parse — but it is the wrong behaviour for a *validation* command,
which should collect every issue in one pass so the author can fix them all
before re-running.

This module provides :func:`validate_spec`, a lenient, single-pass validator
that returns a structured result (errors + warnings) instead of raising.

Validation rules (mirrors SPEC.md gate G1 acceptance criteria):

* **duplicate task IDs** → error (exit non-zero)
* **``blocked_by`` referencing a non-existent task ID** → error (exit non-zero)
* **task missing ``Acceptance:`` criteria** → warning (exit zero)
* a spec with no ``### Task:`` blocks at all → error
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

# Reuse the same task-block regex as SpecParser so the validator stays in
# lock-step with the parser's notion of what a "task" is.
_TASK_BLOCK_RE = re.compile(
    r"###\s+Task:\s*(\S+)\s*\n(.*?)(?=\n###\s+Task:|\n##\s|$)",
    re.DOTALL,
)
_FIELD_RE = re.compile(r"\*\*(?P<field>[^*]+):\*\*\s*(?P<value>.+)")
_LIST_RE = re.compile(
    r"\*\*(?P<field>[^*]+):\*\*\s*\n(?P<items>(?:\s*-\s+.+\n?)+)"
)


@dataclass
class ValidationResult:
    """Outcome of a :func:`validate_spec` run.

    Attributes:
        errors: Hard errors — duplicate IDs, dangling ``blocked_by``, no
            tasks. A non-empty list means the spec is invalid and the CLI
            should exit non-zero.
        warnings: Soft warnings — e.g. a task missing acceptance criteria.
            These do not change the exit code.
        task_ids: The ordered list of task IDs found (for inspection/tests).
    """

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when there are no hard errors (warnings are tolerated)."""
        return not self.errors


def _extract_field(body: str, field_name: str) -> str:
    """Extract a ``- **Field:** value`` line from a task body."""
    match = re.search(
        rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)", body
    )
    return match.group(1).strip() if match else ""


def _extract_list(body: str, field_name: str) -> List[str]:
    """Extract a ``- **Field:**`` followed by bullet list items."""
    match = re.search(
        rf"\*\*{re.escape(field_name)}:\*\*\s*\n((?:\s*-\s+.+\n?)+)",
        body,
    )
    if not match:
        return []
    return [item.strip() for item in re.findall(r"-\s+(.+)", match.group(1))]


def validate_spec(spec_path: Path) -> ValidationResult:
    """Validate a SPEC.md file and return a structured result.

    This never raises on spec-content issues — it collects every error and
    warning into the returned :class:`ValidationResult`. The only exception
    is when the file itself cannot be read (missing/unreadable), which is an
    environmental error the caller should surface.

    Args:
        spec_path: Path to the SPEC.md file to validate.

    Returns:
        A :class:`ValidationResult` with ``errors``, ``warnings``, and
        ``task_ids`` populated.
    """
    result = ValidationResult()

    if not spec_path.exists():
        result.errors.append(f"SPEC file not found: {spec_path}")
        return result

    text = spec_path.read_text(encoding="utf-8")

    task_blocks: List[Tuple[str, str]] = _TASK_BLOCK_RE.findall(text)
    if not task_blocks:
        result.errors.append(
            "No tasks found in SPEC.md. Expected '### Task: <task_id>' blocks."
        )
        return result

    # First pass: collect task IDs, bodies, and per-task acceptance/blocked_by.
    seen: dict[str, int] = {}  # task_id -> count
    tasks: List[Tuple[str, str, List[str], Tuple[str, ...]]] = []
    for task_id_raw, body in task_blocks:
        task_id = task_id_raw.strip()
        seen[task_id] = seen.get(task_id, 0) + 1
        body = body.strip()
        acceptance = _extract_list(body, "Acceptance")
        blocked_by_str = _extract_field(body, "Blocked by") or ""
        blocked_by = tuple(
            b.strip() for b in blocked_by_str.split(",") if b.strip()
        )
        tasks.append((task_id, body, acceptance, blocked_by))
        result.task_ids.append(task_id)

    # Duplicate task IDs → error.
    duplicates = sorted(tid for tid, count in seen.items() if count > 1)
    if duplicates:
        result.errors.append(
            "Duplicate task IDs found: " + ", ".join(duplicates)
        )

    # Dangling blocked_by → error. A blocked_by reference must point to a
    # task ID that exists in the spec.
    known_ids = set(seen.keys())
    for task_id, _body, _acceptance, blocked_by in tasks:
        for ref in blocked_by:
            if ref not in known_ids:
                result.errors.append(
                    f"Task {task_id} has 'blocked_by' referencing "
                    f"non-existent task ID: {ref}"
                )

    # Missing acceptance criteria → warning (not an error).
    for task_id, _body, acceptance, _blocked_by in tasks:
        if not acceptance:
            result.warnings.append(
                f"Task {task_id} has no 'Acceptance:' criteria"
            )

    return result
