"""Plan Operations — bridge plan files to the task store.

Chains the existing plan-parser formats (``## Tasks`` checkbox format and
``### Slice N — Title (owner)`` slice format) into ``task_ops._add_task`` so a
plan file can be imported as a batch of PENDING tasks ready for the executor
daemon / sprint mission to pick up.

WHY THIS EXISTS
---------------
The codebase has 9 active layers (plan parser, task_ops, sprint_ops,
AutopilotEngine, slot_ops, swarm, lane spec_parser, CLI, MCP tools) that
could form a complete plan→task→execution pipeline, but they're disconnected.
``plan_ops`` is the missing glue: it parses a plan, calls ``_add_task`` for
each item, and returns the resulting task_ids so a downstream caller (CLI,
MCP tool, sprint mission) can execute them.

Public surface
--------------
- ``import_plan_as_tasks(plan_path, plan_ref=None) -> Dict``
- ``list_plans(plans_dir=".brain/plans") -> List[Dict]``
- ``validate_plan(plan_path) -> Dict``

Supported plan formats (see SPEC.md task ``plan_ops_create_module``)
-------------------------------------------------------------------
1. ``## Tasks`` checkbox format::

       ## Tasks
       - [ ] Task 1: do the first thing
       - [x] Task 2: already done (still imported, just recorded)

2. ``### Slice N — Title (owner)`` slice format::

       ### Slice 0 — TOC lock (Cowork + Founder)
       ### Slice 1 — Arch content fill (Cowork)

The first format yields one task per checkbox line (description = text after
the colon). The second yields one task per slice header (description = title,
``required_role`` = owner).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import task_ops

logger = logging.getLogger("nucleus.plan_ops")


# ── Format detection / parsing ──────────────────────────────────────────

# Matches `- [ ] Task 1: description` or `- [x] Task 2: description`.
# The "Task N:" prefix is required by the SPEC; the description is everything
# after the colon (stripped). We accept both checked and unchecked boxes —
# importing an already-checked task is fine, the importer just records it.
_TASKS_CHECKBOX_RE = re.compile(
    r"^\s*-\s*\[(?:x|\s)\]\s*Task\s+\d+\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)

# Matches `### Slice N — Title (owner)`. The em-dash may be a regular hyphen
# in some plans; we accept both. Owner is optional in the regex (some plans
# omit it) but the SPEC format includes it.
_SLICE_HEADER_RE = re.compile(
    r"^###\s+Slice\s+(\d+)\s*[—-]\s*(.+?)(?:\s*\(([^)]+)\))?\s*$",
)


def _detect_format(text: str) -> str:
    """Return 'tasks', 'slice', or 'unknown' based on which markers appear."""
    has_checkbox = any(_TASKS_CHECKBOX_RE.match(line) for line in text.splitlines())
    has_slice = any(_SLICE_HEADER_RE.match(line) for line in text.splitlines())
    if has_checkbox:
        return "tasks"
    if has_slice:
        return "slice"
    return "unknown"


def _parse_tasks_format(text: str) -> List[Dict[str, Any]]:
    """Parse `## Tasks` checkbox format. Returns list of {description, ...}."""
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        m = _TASKS_CHECKBOX_RE.match(line)
        if not m:
            continue
        description = m.group(1).strip()
        if not description:
            continue
        items.append({"description": description, "required_role": None})
    return items


def _parse_slice_format(text: str) -> List[Dict[str, Any]]:
    """Parse `### Slice N — Title (owner)` format. Returns list of items."""
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        m = _SLICE_HEADER_RE.match(line)
        if not m:
            continue
        # group(1) = number, group(2) = title, group(3) = owner (optional)
        title = (m.group(2) or "").strip()
        owner = (m.group(3) or "").strip() or None
        if not title:
            continue
        items.append({"description": title, "required_role": owner})
    return items


def _parse_plan(text: str) -> tuple[str, List[Dict[str, Any]]]:
    """Parse a plan body. Returns (format, items)."""
    fmt = _detect_format(text)
    if fmt == "tasks":
        return "tasks", _parse_tasks_format(text)
    if fmt == "slice":
        return "slice", _parse_slice_format(text)
    return "unknown", []


# ── Public API ──────────────────────────────────────────────────────────


def import_plan_as_tasks(
    plan_path: str,
    plan_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse a plan file and create a task for each item via ``task_ops._add_task``.

    Args:
        plan_path: Path to the plan markdown file.
        plan_ref: Optional override for the ``plan_ref`` field on each created
            task. Defaults to ``plan_path`` itself so tasks carry their origin.

    Returns:
        ``{"success": True, "plan_path": ..., "task_ids": [...], "count": N}``
        on success, or ``{"success": False, "error": "..."}`` on failure
        (file not found, no tasks parsed, etc.).
    """
    try:
        p = Path(plan_path)
        if not p.exists() or not p.is_file():
            return {
                "success": False,
                "error": f"Plan file not found: {plan_path}",
            }

        text = p.read_text(encoding="utf-8", errors="replace")
        fmt, items = _parse_plan(text)
        if not items:
            return {
                "success": False,
                "error": (
                    f"No parseable tasks found in {plan_path} "
                    f"(detected format: {fmt})"
                ),
            }

        ref = plan_ref if plan_ref is not None else str(plan_path)
        task_ids: List[str] = []
        errors: List[str] = []

        for item in items:
            result = task_ops._add_task(
                description=item["description"],
                source="plan_import",
                plan_ref=ref,
                required_role=item.get("required_role"),
            )
            if result.get("success"):
                task = result.get("task") or {}
                tid = task.get("id")
                if tid:
                    task_ids.append(tid)
            else:
                errors.append(
                    f"Failed to add task '{item['description'][:40]}': "
                    f"{result.get('error', 'unknown error')}"
                )

        if not task_ids:
            return {
                "success": False,
                "error": "No tasks were created. " + " | ".join(errors),
            }

        return {
            "success": True,
            "plan_path": str(plan_path),
            "task_ids": task_ids,
            "count": len(task_ids),
        }
    except Exception as exc:
        logger.exception("import_plan_as_tasks failed for %s", plan_path)
        return {"success": False, "error": str(exc)}


def list_plans(plans_dir: str = ".brain/plans") -> List[Dict[str, Any]]:
    """List all ``.md`` plan files in ``plans_dir`` with name, size, task count.

    Args:
        plans_dir: Directory to scan. Defaults to ``.brain/plans``.

    Returns:
        List of dicts: ``{"name", "path", "size_bytes", "task_count", "format"}``
        sorted by name. Missing directory returns ``[]``.
    """
    d = Path(plans_dir)
    if not d.exists() or not d.is_dir():
        return []

    out: List[Dict[str, Any]] = []
    for p in sorted(d.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            fmt, items = _parse_plan(text)
            out.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "size_bytes": p.stat().st_size,
                    "task_count": len(items),
                    "format": fmt,
                }
            )
        except Exception as exc:
            logger.debug("list_plans: failed to read %s: %s", p, exc)
            out.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "size_bytes": p.stat().st_size if p.exists() else 0,
                    "task_count": 0,
                    "format": "unknown",
                    "error": str(exc),
                }
            )
    return out


def validate_plan(plan_path: str) -> Dict[str, Any]:
    """Validate that a plan file has parseable tasks.

    Args:
        plan_path: Path to the plan markdown file.

    Returns:
        ``{"valid": bool, "format": "tasks|slice|unknown", "task_count": N,
        "errors": [...]}``
    """
    errors: List[str] = []
    p = Path(plan_path)
    if not p.exists() or not p.is_file():
        return {
            "valid": False,
            "format": "unknown",
            "task_count": 0,
            "errors": [f"File not found: {plan_path}"],
        }

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "valid": False,
            "format": "unknown",
            "task_count": 0,
            "errors": [f"Could not read file: {exc}"],
        }

    fmt, items = _parse_plan(text)
    if not items:
        errors.append(
            f"No parseable tasks found. Expected '## Tasks' checkbox format "
            f"(- [ ] Task N: ...) or '### Slice N — Title (owner)' headers."
        )

    return {
        "valid": bool(items),
        "format": fmt,
        "task_count": len(items),
        "errors": errors,
    }
