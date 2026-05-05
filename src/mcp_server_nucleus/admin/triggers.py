"""Ledger default-triggers writer — canonical v2.2 bundle.

Ships the Nucleus trigger-routing table into the ledger so downstream
routers can dispatch events without having to ship the list inline. The
bundled v2.2 content is the frozen fleet baseline; use ``write_triggers``
with a caller-supplied dict to override for cycle-specific rollouts.

Env contract:

- ``NUCLEUS_TRIGGERS_PATH`` wins for the output file.
- Fallback: ``<brain>/ledger/triggers.json`` via ``paths.brain_path``.

Usage: ``python -m mcp_server_nucleus.admin.triggers``
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mcp_server_nucleus.paths import brain_path

_VERSION = "2.2"


def default_triggers_v22() -> dict:
    """Return the frozen v2.2 triggers bundle.

    Caller receives a fresh dict so mutating the result does not pollute
    subsequent callers.
    """
    return {
        "version": _VERSION,
        "triggers": [
            {
                "id": "task-state-changed",
                "event_type": "task_state_changed",
                "condition": "always",
                "activates": "synthesizer",
                "description": "Log task state transitions for digest",
            },
            {
                "id": "task-created",
                "event_type": "task_created",
                "condition": "always",
                "activates": "orchestrator",
                "description": "New task added to queue",
            },
            {
                "id": "commitment-created",
                "event_type": "commitment_created",
                "condition": "always",
                "activates": "synthesizer",
                "description": "New commitment for tracking",
            },
            {
                "id": "commitment-closed",
                "event_type": "commitment_closed",
                "condition": "always",
                "activates": "synthesizer",
                "description": "Commitment closed, update velocity",
            },
            {
                "id": "health-check",
                "event_type": "health_status",
                "condition": "always",
                "activates": "synthesizer",
                "description": "Health check results for monitoring",
            },
            {
                "id": "deploy-complete",
                "event_type": "deploy_complete",
                "condition": "always",
                "activates": "tester",
                "description": "Deploy finished, run verification",
            },
            {
                "id": "session-saved",
                "event_type": "session_saved",
                "condition": "always",
                "activates": "synthesizer",
                "description": "Context saved for continuity",
            },
            {
                "id": "critical-escalation",
                "event_type": "*",
                "condition": "severity == 'CRITICAL'",
                "activates": "synthesizer",
                "description": "Any critical event escalates to Synthesizer",
            },
            {
                "id": "trigger-grooming",
                "event_type": "spec_needed",
                "condition": "always",
                "activates": "product_manager",
                "description": "PM grooms backlog and writes specs.",
            },
            {
                "id": "trigger-design",
                "event_type": "spec_ready",
                "condition": "always",
                "activates": "architect",
                "description": "Architect designs system from PM specs.",
            },
            {
                "id": "trigger-implementation",
                "event_type": "design_ready",
                "condition": "always",
                "activates": "developer",
                "description": "Developer implements code from Architecture design.",
            },
            {
                "id": "trigger-deployment",
                "event_type": "deployment_request",
                "condition": "always",
                "activates": "devops",
                "description": "DevOps handles deployment related requests.",
            },
            {
                "id": "trigger-synthesis",
                "event_type": "user_intent",
                "condition": "always",
                "activates": "synthesizer",
                "description": "Synthesizer triages incoming user intent.",
            },
            {
                "id": "trigger-task-assigned",
                "event_type": "task_assigned",
                "condition": "always",
                "activates": "{{payload.target_agent}}",
                "description": "Route task to specified agent.",
            },
        ],
    }


def triggers_path() -> Path:
    env = os.environ.get("NUCLEUS_TRIGGERS_PATH")
    if env:
        return Path(env)
    return brain_path() / "ledger" / "triggers.json"


def write_triggers(path: Path | None = None, content: dict | None = None) -> Path:
    """Atomically write the triggers JSON.

    ``path`` defaults to ``triggers_path()``; ``content`` defaults to
    ``default_triggers_v22()``. Write is atomic via tmp-then-rename so a
    reader racing the writer never observes a truncated file.
    """
    dest = path if path is not None else triggers_path()
    payload = content if content is not None else default_triggers_v22()

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    _ = argv  # accepted for symmetry with other admin entry points
    dest = write_triggers()
    print(f"wrote triggers v{_VERSION} to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
