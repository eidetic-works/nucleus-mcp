"""MCP tools for plan operations — plan→task→mission bridge.

These tools allow any MCP client (Devin, Claude Code, etc.) to import a
plan file (``.brain/plans/*.md``) as a batch of PENDING tasks and
optionally start a sprint mission against them. They delegate to
``mcp_server_nucleus.runtime.plan_ops`` and
``mcp_server_nucleus.runtime.sprint_ops``.

Tools:
    nucleus_plan_execute — import a plan and start a mission against its tasks
    nucleus_plan_import  — import a plan as PENDING tasks (no execution)
    nucleus_plan_list    — list available plan files with task counts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def register(mcp, helpers):
    """Register the nucleus_plan_* facade tools with the MCP server."""

    @mcp.tool()
    async def nucleus_plan_execute(
        plan_path: str,
        goal: str = "",
        budget_limit: float = 10.0,
        time_limit_hours: float = 4.0,
    ) -> str:
        """Execute a plan file autonomously. WHEN TO USE: you have a plan file (.brain/plans/*.md) you want executed autonomously — parses the plan, creates tasks, starts a mission with budget/time limits. Chains import_plan_as_tasks() then _brain_start_mission_impl() and returns the mission status string.

        Args:
            plan_path: Path to the plan markdown file (.brain/plans/*.md).
            goal: Optional mission goal text. Defaults to empty.
            budget_limit: Mission spend cap in USD (default $10.00).
            time_limit_hours: Mission time cap in hours (default 4.0).

        Returns:
            A status string from the mission starter. On success includes
            the mission ID and a summary of imported task_ids; on failure
            starts with "❌" and describes the error.
        """
        return await _nucleus_plan_execute(plan_path, goal, budget_limit, time_limit_hours)

    @mcp.tool()
    async def nucleus_plan_import(plan_path: str) -> str:
        """Import a plan file as PENDING tasks without starting a mission. WHEN TO USE: you have a plan file (.brain/plans/*.md) you want loaded into the task store so the executor daemon / sprint mission can pick the tasks up later — but you don't want to start a mission right now.

        Args:
            plan_path: Path to the plan markdown file.

        Returns:
            JSON string with ``{"success", "plan_path", "task_ids", "count"}``
            on success, or ``{"success": False, "error": "..."}`` on failure.
        """
        return await _nucleus_plan_import(plan_path)

    @mcp.tool()
    async def nucleus_plan_list() -> str:
        """List available plan files in .brain/plans with task counts. WHEN TO USE: you want to discover which plan files exist and how many tasks each contains before importing or executing one.

        Returns:
            JSON string: a list of dicts each with
            ``{"name", "path", "size_bytes", "task_count", "format"}``.
            Missing directory returns ``[]``.
        """
        return await _nucleus_plan_list()

    return [
        ("nucleus_plan_execute", nucleus_plan_execute),
        ("nucleus_plan_import", nucleus_plan_import),
        ("nucleus_plan_list", nucleus_plan_list),
    ]


# ── Implementations ──────────────────────────────────────────────────────


async def _nucleus_plan_execute(
    plan_path: str,
    goal: str = "",
    budget_limit: float = 10.0,
    time_limit_hours: float = 4.0,
) -> str:
    """Import a plan and start a mission against its tasks.

    Chains ``import_plan_as_tasks()`` then ``_brain_start_mission_impl()``
    and returns the mission status string. On import failure, returns a
    JSON error string (no mission is started).
    """
    from ..runtime.plan_ops import import_plan_as_tasks
    from ..runtime.sprint_ops import _brain_start_mission_impl

    try:
        import_result = import_plan_as_tasks(plan_path)
        if not import_result.get("success"):
            return json.dumps(import_result, indent=2)

        task_ids: List[str] = import_result.get("task_ids", []) or []
        if not task_ids:
            return json.dumps(
                {
                    "success": False,
                    "error": "import produced no task_ids",
                    "plan_path": str(plan_path),
                },
                indent=2,
            )

        # Derive a mission name from the plan file stem so the mission is
        # identifiable in status output.
        name = Path(plan_path).stem or "plan-mission"

        mission_output = _brain_start_mission_impl(
            name=name,
            goal=goal,
            task_ids=task_ids,
            budget_limit=budget_limit,
            time_limit_hours=time_limit_hours,
        )

        # The impl returns a formatted status string. Append a compact
        # import summary so callers can see which task_ids were created.
        summary = (
            f"\nImported {len(task_ids)} task(s) from {plan_path}:\n"
            + "".join(f"  {tid}\n" for tid in task_ids)
        )
        return mission_output + summary
    except Exception as exc:
        return f"❌ plan_execute error: {exc}"


async def _nucleus_plan_import(plan_path: str) -> str:
    """Import a plan file as PENDING tasks (no mission)."""
    from ..runtime.plan_ops import import_plan_as_tasks

    try:
        result = import_plan_as_tasks(plan_path)
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        return json.dumps(
            {"success": False, "error": str(exc), "plan_path": str(plan_path)},
            indent=2,
        )


async def _nucleus_plan_list() -> str:
    """List available plan files in .brain/plans with task counts."""
    from ..runtime.plan_ops import list_plans

    try:
        plans: List[Dict[str, Any]] = list_plans()
        return json.dumps(plans, indent=2, default=str)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, indent=2)
