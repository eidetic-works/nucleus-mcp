"""MCP facade exposing the Renaissance run engine to ACP clients."""
from __future__ import annotations

import json
from pathlib import Path

from ..runs.mcp_adapter import RunMcpAdapter


def _adapter(helpers) -> RunMcpAdapter:
    brain = Path(helpers["get_brain_path"]())
    db = brain / "runs" / "store.sqlite"
    return RunMcpAdapter(db)


def _register_tools(mcp, helpers):
    adapter = _adapter(helpers)

    @mcp.tool(
        title="Run Engine",
        annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    )
    def nucleus_runs(action: str, params: dict | None = None) -> str:
        """Run engine facade.

        Actions:
          create_project  {root_uri, trust_mode?}
          create_conversation {project_id, title}
          create_run      {conversation_id, prompt, runner_id?, model_id?, execution_target?, mode?, idempotency_key?}
          list_runs       {conversation_id?}
          show_run        {run_id}
          apply_run       {run_id}
          dismiss_run     {run_id}
          cancel_run      {run_id, issuer?}
        """
        params = params or {}
        try:
            if action == "create_project":
                return json.dumps({
                    "success": True,
                    "project_id": adapter.create_project(
                        params["root_uri"], params.get("trust_mode", "default")
                    ),
                })
            if action == "create_conversation":
                return json.dumps({
                    "success": True,
                    "conversation_id": adapter.create_conversation(
                        params["project_id"], params["title"]
                    ),
                })
            if action == "create_run":
                return json.dumps({
                    "success": True,
                    "run_id": adapter.create_run(
                        conversation_id=params["conversation_id"],
                        prompt=params.get("prompt", ""),
                        runner_id=params.get("runner_id", "agy"),
                        model_id=params.get("model_id", ""),
                        execution_target=params.get("execution_target", "local"),
                        mode=params.get("mode", "write"),
                        idempotency_key=params.get("idempotency_key", ""),
                    ),
                })
            if action == "list_runs":
                return json.dumps({"success": True, "runs": adapter.list_runs(params.get("conversation_id"))})
            if action == "show_run":
                return json.dumps({"success": True, "data": adapter.show_run(params["run_id"])})
            if action == "apply_run":
                return adapter.apply_run(params["run_id"]).to_json()
            if action == "dismiss_run":
                return adapter.dismiss_run(params["run_id"]).to_json()
            if action == "cancel_run":
                return adapter.cancel_run(params["run_id"], params.get("issuer", "user")).to_json()
            return json.dumps({"success": False, "error": f"unknown action: {action!r}"})
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"success": False, "error": str(exc)})

    return [("nucleus_runs", nucleus_runs)]


def register(mcp, helpers):
    return _register_tools(mcp, helpers)
