"""MCP tools for autonomous lane management.

These tools allow any MCP client (Devin, Claude Code, etc.) to manage
autonomous lanes in their repos. They delegate to the core
mcp_server_nucleus.runtime.lane package.

Tools:
    nucleus_lane_init    — initialize a lane in a repo
    nucleus_lane_start   — start lane daemons
    nucleus_lane_stop    — stop lane daemons
    nucleus_lane_status  — get lane status
    nucleus_lane_feedback — submit feedback to the nucleus team
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def register(mcp, helpers):
    """Register the nucleus_lane_* facade tools with the MCP server."""

    @mcp.tool()
    async def nucleus_lane_init(
        repo_path: str = "",
        spec_path: str = "SPEC.md",
        role: str = "lane-g1",
        vendor: str = "devin",
        tag: str = "",
        force: bool = False,
    ) -> str:
        """Set up an autonomous task-execution loop in a git repo. WHEN TO USE: you have a list of tasks (bugs, features, tests) you want executed automatically without manual prompting — the lane runs watcher/executor/secretary daemons that claim tasks, invoke an LLM to implement them, and independently verify the results. Use this when you want to batch-execute a backlog of well-defined tasks. Creates .brain/, SPEC.md template, and pins via git tag.

        Args:
            repo_path: Path to the git repo (default: current directory).
            spec_path: Path to the spec file (default: SPEC.md).
            role: Lane role name (default: lane-g1).
            vendor: Default vendor — devin (GLM) or agy (Gemini).
            tag: Git tag for spec pinning (default: <role>-v1).
            force: Skip isolation guards (for testing only).

        Returns:
            JSON string with initialization result.
        """
        return await _nucleus_lane_init(repo_path, spec_path, role, vendor, tag, force)

    @mcp.tool()
    async def nucleus_lane_start(
        repo_path: str = "",
        executors: Optional[list] = None,
        no_secretary: bool = False,
        no_watcher: bool = False,
    ) -> str:
        """Start autonomous lane daemons (watcher + executor + secretary) in background. WHEN TO USE: after nucleus_lane_init and SPEC.md is written — this launches the loop that autonomously claims and executes tasks. The executor invokes an LLM CLI (devin/agy) per task; the secretary independently verifies each result. Runs until nucleus_lane_stop is called.

        Args:
            repo_path: Path to the git repo (default: current directory).
            executors: List of executor lane names (default: ["lane_devin"]).
            no_secretary: Skip secretary daemon (NOT recommended — disables verification).
            no_watcher: Skip control watcher.

        Returns:
            JSON string with started daemon PIDs.
        """
        return await _nucleus_lane_start(repo_path, executors, no_secretary, no_watcher)

    @mcp.tool()
    async def nucleus_lane_stop(repo_path: str = "") -> str:
        """Stop all running lane daemons. WHEN TO USE: when all tasks are CONFIRMED or you want to pause autonomous execution.

        Args:
            repo_path: Path to the git repo (default: current directory).

        Returns:
            JSON string with stop results.
        """
        return await _nucleus_lane_stop(repo_path)

    @mcp.tool()
    async def nucleus_lane_status(repo_path: str = "") -> str:
        """Check lane status: task counts (PENDING/IN_PROGRESS/DONE/CONFIRMED), daemon health, spec verification. WHEN TO USE: after starting a lane to monitor progress, or before starting to check if a lane is already running.

        Args:
            repo_path: Path to the git repo (default: current directory).

        Returns:
            JSON string with lane status including task projection.
        """
        return await _nucleus_lane_status(repo_path)

    @mcp.tool()
    async def nucleus_lane_feedback(
        feedback_type: str,
        subject: str,
        body: str,
        reporter: str = "",
        repo_path: str = "",
    ) -> str:
        """Report friction/bugs/enhancements to the nucleus team. WHEN TO USE: when the lane misbehaves, a task fails unexpectedly, the SPEC.md format is confusing, or you have an improvement idea. Creates a GitHub issue on the public nucleus-mcp repo (cross-machine visible) AND stores locally. Requires gh CLI auth'd.

        Args:
            feedback_type: "bug", "enhancement", "observation", or "question".
            subject: Short summary.
            body: Detailed description.
            reporter: Your name/project (default: anonymous).
            repo_path: Path to the repo where the feedback was observed.

        Returns:
            JSON string with the submitted feedback item.
        """
        return await _nucleus_lane_feedback(feedback_type, subject, body, reporter, repo_path)

    return [
        ("nucleus_lane_init", nucleus_lane_init),
        ("nucleus_lane_start", nucleus_lane_start),
        ("nucleus_lane_stop", nucleus_lane_stop),
        ("nucleus_lane_status", nucleus_lane_status),
        ("nucleus_lane_feedback", nucleus_lane_feedback),
    ]


async def _nucleus_lane_init(
    repo_path: str = "",
    spec_path: str = "SPEC.md",
    role: str = "lane-g1",
    vendor: str = "devin",
    tag: str = "",
    force: bool = False,
) -> str:
    """Initialize an autonomous lane in a git repository.

    Creates a .brain/ directory, a SPEC.md template, and pins the spec via git tag.

    Args:
        repo_path: Path to the git repo (default: current directory).
        spec_path: Path to the spec file (default: SPEC.md).
        role: Lane role name (default: lane-g1).
        vendor: Default vendor — devin (GLM) or agy (Gemini).
        tag: Git tag for spec pinning (default: <role>-v1).
        force: Skip isolation guards (for testing only).

    Returns:
        JSON string with initialization result.
    """
    from mcp_server_nucleus.runtime.lane import isolate_brain, LaneConfig
    from mcp_server_nucleus.runtime.lane.spec_parser import SpecParser

    repo = Path(repo_path or os.getcwd()).resolve()
    brain = repo / ".brain"
    tag = tag or f"{role}-v1"

    try:
        brain = isolate_brain(repo, brain, force=force)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})

    spec = repo / spec_path
    if not spec.exists():
        spec.write_text(f"""# SPEC: {repo.name}

> Pin via git tag `{tag}`. Do not edit after pinning.

## Gate G1

### Task: {role}_example_task
- **Title:** Example task — replace with your own
- **Authority:** SPEC.md (G1 example)
- **Acceptance:**
  - A committed artifact proves the task is complete.
  - The result is rerunnable from a clean checkout.
- **Priority:** 1
""")
        created_spec = True
    else:
        created_spec = False

    config = LaneConfig(
        repo_root=repo, brain_path=brain, spec_path=spec,
        spec_tag=tag, role=role, vendor=vendor,
    )

    pinned = False
    pin_error = None
    try:
        SpecParser(config).pin_spec()
        pinned = True
    except Exception as e:
        pin_error = str(e)

    if not pinned and not force:
        return json.dumps({
            "success": False,
            "error": f"spec pinning failed: {pin_error}",
            "spec_pinned": False,
            "hint": "pass force=True to initialize with an unpinned spec anyway",
        }, indent=2)

    cfg_path = brain / "state" / "lane_config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(config.to_dict(), indent=2))

    return json.dumps({
        "success": True,
        "role": role,
        "brain_path": str(brain),
        "spec_path": str(spec),
        "spec_created": created_spec,
        "spec_pinned": pinned,
        "config_path": str(cfg_path),
        "next_step": f"Edit {spec}, commit it, then call nucleus_lane_start",
    }, indent=2)


async def _nucleus_lane_start(
    repo_path: str = "",
    executors: Optional[list] = None,
    no_secretary: bool = False,
    no_watcher: bool = False,
) -> str:
    """Start autonomous lane daemons in the background.

    Args:
        repo_path: Path to the git repo (default: current directory).
        executors: List of executor lane names (default: ["lane_devin"]).
        no_secretary: Skip secretary daemon.
        no_watcher: Skip control watcher.

    Returns:
        JSON string with started daemon PIDs.
    """
    from mcp_server_nucleus.runtime.lane import LaneConfig

    repo = Path(repo_path or os.getcwd()).resolve()
    cfg_path = repo / ".brain" / "state" / "lane_config.json"
    if not cfg_path.exists():
        return json.dumps({"success": False, "error": "No lane config. Call nucleus_lane_init first."})

    config = LaneConfig.from_dict(json.loads(cfg_path.read_text()))
    executors = executors or [f"{config.role}_devin"]
    procs = {}

    # Build env with NUCLEUS_BRAIN_PATH so subprocess daemons use the isolated brain
    daemon_env = dict(os.environ)
    daemon_env["NUCLEUS_BRAIN_PATH"] = str(config.brain_path)

    if not no_watcher:
        p = subprocess.Popen(
            [sys.executable, "-c",
             f"from mcp_server_nucleus.runtime.lane import LaneConfig, ControlWatcher; "
             f"import json; c = LaneConfig.from_dict(json.loads(open('{cfg_path}').read())); "
             f"ControlWatcher(c).watch()"],
            stdout=open(config.brain_path / "logs" / "lane_watcher.log", "a"),
            stderr=subprocess.STDOUT,
            env=daemon_env,
        )
        procs["watcher"] = p.pid

    for lane in executors:
        p = subprocess.Popen(
            [sys.executable, "-c",
             f"from mcp_server_nucleus.runtime.lane import LaneConfig, ExecutorDaemon; "
             f"import json; c = LaneConfig.from_dict(json.loads(open('{cfg_path}').read())); "
             f"ExecutorDaemon(c, '{lane}', '{lane}', '{config.vendor}').run()"],
            stdout=open(config.brain_path / "logs" / f"lane_{lane}.log", "a"),
            stderr=subprocess.STDOUT,
            env=daemon_env,
        )
        procs[lane] = p.pid

    if not no_secretary:
        p = subprocess.Popen(
            [sys.executable, "-c",
             f"from mcp_server_nucleus.runtime.lane import LaneConfig, SecretaryDaemon; "
             f"import json; c = LaneConfig.from_dict(json.loads(open('{cfg_path}').read())); "
             f"SecretaryDaemon(c).run()"],
            stdout=open(config.brain_path / "logs" / "lane_secretary.log", "a"),
            stderr=subprocess.STDOUT,
            env=daemon_env,
        )
        procs["secretary"] = p.pid

    (config.brain_path / "state" / "lane_pids.json").write_text(json.dumps(procs, indent=2))

    return json.dumps({
        "success": True,
        "daemons": procs,
        "pid_file": str(config.brain_path / "state" / "lane_pids.json"),
    }, indent=2)


async def _nucleus_lane_stop(repo_path: str = "") -> str:
    """Stop all running lane daemons.

    Args:
        repo_path: Path to the git repo (default: current directory).

    Returns:
        JSON string with stop results.
    """
    repo = Path(repo_path or os.getcwd()).resolve()
    pid_file = repo / ".brain" / "state" / "lane_pids.json"
    if not pid_file.exists():
        return json.dumps({"success": True, "stopped": [], "message": "No running daemons."})

    pids = json.loads(pid_file.read_text())
    stopped = []
    for name, pid in pids.items():
        try:
            os.kill(int(pid), 15)
            stopped.append(name)
        except ProcessLookupError:
            pass
    pid_file.unlink()

    return json.dumps({"success": True, "stopped": stopped}, indent=2)


async def _nucleus_lane_status(repo_path: str = "") -> str:
    """Get the current status of an autonomous lane.

    Args:
        repo_path: Path to the git repo (default: current directory).

    Returns:
        JSON string with lane status including task projection.
    """
    from mcp_server_nucleus.runtime.lane import LaneConfig
    from mcp_server_nucleus.runtime.lane.control_watcher import ControlWatcher

    repo = Path(repo_path or os.getcwd()).resolve()
    cfg_path = repo / ".brain" / "state" / "lane_config.json"
    if not cfg_path.exists():
        return json.dumps({"success": False, "error": "No lane config. Call nucleus_lane_init first."})

    config = LaneConfig.from_dict(json.loads(cfg_path.read_text()))
    watcher = ControlWatcher(config)
    status = watcher.status()

    return json.dumps({"success": True, **status}, indent=2, default=str)


async def _nucleus_lane_feedback(
    feedback_type: str,
    subject: str,
    body: str,
    reporter: str = "",
    repo_path: str = "",
) -> str:
    """Submit feedback (bug/enhancement/observation) to the nucleus team.

    Args:
        feedback_type: "bug", "enhancement", "observation", or "question".
        subject: Short summary.
        body: Detailed description.
        reporter: Your name/project (default: anonymous).
        repo_path: Path to the repo where the feedback was observed.

    Returns:
        JSON string with the submitted feedback item.
    """
    from mcp_server_nucleus.runtime.lane import submit_feedback

    item = submit_feedback(
        feedback_type=feedback_type,
        subject=subject,
        body=body,
        reporter=reporter or os.environ.get("USER", "anonymous"),
        repo=repo_path or os.getcwd(),
    )

    return json.dumps({"success": True, "feedback": item}, indent=2, default=str)
