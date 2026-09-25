"""Subprocess/sandbox entry point for RunWorker."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .policy import ExecutionPolicy
from .runners import VendorCliRunner
from .store import RunStore
from .verifiers import CommandVerifier, NoopVerifier, Verifier
from .worker import RunWorker
from .workspace import WorkspaceResolver


def _vendor_cli_handler(prompt: str, runner_id: str, model_id: str, mode: str, timeout_s: int = 3600):
    def _h(ctx):
        if ctx.workspace is None or ctx.workspace_backend is None:
            raise RuntimeError("no workspace")
        project = ctx._store.get_project_for_run(ctx._run_id)
        policy = ExecutionPolicy.from_trust_mode(project.trust_mode)
        runner = VendorCliRunner(runner_id, model=model_id or None, mode=mode)
        return runner.run(
            prompt,
            ctx.workspace,
            ctx.workspace_backend,
            policy,
            timeout_s=timeout_s,
            cancel_event=ctx.cancel_event,
        )

    return _h


def _verifiers_from_requirements(
    requirements_json: str | None,
) -> list[Verifier]:
    """Build a list of verifiers from the persisted requirements contract.

    Returns ``[NoopVerifier()]`` for legacy runs without requirements so the
    existing behavior is preserved.  For runs with an approved ``check``
    command, returns a ``CommandVerifier`` that runs the check in the
    workspace.
    """
    if not requirements_json:
        return [NoopVerifier()]
    try:
        req = json.loads(requirements_json)
    except (json.JSONDecodeError, TypeError):
        return [NoopVerifier()]

    check = req.get("check")
    if not check or not isinstance(check, dict):
        return [NoopVerifier()]

    argv = check.get("argv")
    if not argv or not isinstance(argv, list):
        return [NoopVerifier()]

    timeout = check.get("timeout", 300)
    name = check.get("name", "approved_check")
    return [CommandVerifier(name=name, command=list(argv), timeout=timeout)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nucleus-run-worker")
    parser.add_argument("--db", required=True, help="RunStore database path")
    parser.add_argument("--run", required=True, help="Run ID")
    parser.add_argument("--owner", default="sandbox-worker", help="Worker owner ID")
    parser.add_argument("--runner", default="agy", help="Vendor CLI runner ID")
    parser.add_argument("--model", default="", help="Model ID")
    args = parser.parse_args(argv)

    store = RunStore(args.db)
    run = store.get_run(args.run)
    prompt = run.prompt
    runner_id = args.runner or run.runner_id
    model_id = args.model or None
    mode = run.mode

    # Load persisted verification requirements so the subprocess worker
    # uses the approved check command instead of the default NoopVerifier.
    verifiers = _verifiers_from_requirements(run.requirements)

    # Extract runner deadline from persisted requirements if present.
    runner_timeout = 3600
    if run.requirements:
        try:
            req = json.loads(run.requirements)
            runner_timeout = req.get("runner_timeout", req.get("timeout", 3600))
        except (json.JSONDecodeError, TypeError):
            pass

    resolver = WorkspaceResolver()
    worker = RunWorker(store, args.run, args.owner, workspace_resolver=resolver)
    handler = _vendor_cli_handler(prompt, runner_id, model_id, mode, timeout_s=runner_timeout)

    try:
        worker.execute(handler, verifiers=verifiers)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1

    run = store.get_run(args.run)
    print(json.dumps({"state": run.state.value}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
