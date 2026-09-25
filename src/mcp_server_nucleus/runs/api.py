"""Headless REST API for the Nucleus run engine."""
from __future__ import annotations

import dataclasses
import uuid
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .mcp_adapter import RunMcpAdapter


CAPABILITIES = {
    "runners": ["agy"],
    "models": ["gemini-3.6-flash-high"],
}


def _bad_request(message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=400)


def _not_found(resource: str, ident: str) -> JSONResponse:
    return JSONResponse({"error": f"{resource} {ident!r} not found"}, status_code=404)


def _resolve_artifact_bytes(artifact, brain_path: Path) -> bytes | None:
    """Load artifact bytes safely, keeping paths under the brain root."""
    if not artifact.path:
        return None

    root = brain_path.resolve()
    candidate = Path(artifact.path)

    if candidate.is_absolute():
        target = candidate.resolve()
    else:
        target = (root / candidate).resolve()
        if not target.is_file():
            target = (root / "artifacts" / candidate).resolve()

    try:
        if not target.is_relative_to(root) or not target.is_file():
            return None
        return target.read_bytes()
    except OSError:
        return None


def build_app(adapter: RunMcpAdapter, brain_path: Path | None = None) -> Starlette:
    """Build a Starlette app serving the headless run API."""
    if brain_path is None:
        brain_path = Path(adapter._store._db_path).parent.parent

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def capabilities(request: Request) -> JSONResponse:
        return JSONResponse(CAPABILITIES)

    async def list_runs(request: Request) -> JSONResponse:
        return JSONResponse(adapter.list_runs())

    async def show_run(request: Request) -> JSONResponse:
        run_id = request.path_params["id"]
        try:
            data = adapter.show_run(run_id)
        except ValueError:
            return _not_found("Run", run_id)
        return JSONResponse(data)

    async def create_run(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}

        if not isinstance(body, dict):
            return _bad_request("JSON body must be an object")

        project_root = body.get("project_root")
        prompt = body.get("prompt")
        if project_root is None or prompt is None:
            return _bad_request("project_root and prompt are required")

        runner_id = body.get("runner_id", "agy")
        model_id = body.get("model_id", "")
        mode = body.get("mode", "write")
        execution_target = body.get("execution_target", "local")
        trust_mode = body.get("trust_mode", "default")

        try:
            project_id = adapter.get_or_create_project(
                f"file://{Path(project_root).resolve()}", str(trust_mode)
            )
            conversation_id = adapter.create_conversation(project_id, str(prompt)[:120])
            run_id = adapter.create_run(
                conversation_id=conversation_id,
                prompt=str(prompt),
                runner_id=str(runner_id),
                model_id=str(model_id),
                execution_target=str(execution_target),
                mode=str(mode),
                idempotency_key=str(uuid.uuid4()),
            )
            run = adapter._store.get_run(run_id)
        except Exception as exc:
            return _bad_request(str(exc))

        return JSONResponse({"run_id": run_id, "state": run.state.value})

    async def execute_run(request: Request) -> JSONResponse:
        run_id = request.path_params["id"]

        try:
            body = await request.json()
        except Exception:
            body = {}

        if not isinstance(body, dict):
            return _bad_request("JSON body must be an object")

        target = body.get("target", "in-process")

        try:
            data = adapter.execute_run(run_id, target)
        except ValueError as exc:
            if "not found" in str(exc).lower():
                return _not_found("Run", run_id)
            return _bad_request(str(exc))
        except Exception as exc:
            return _bad_request(str(exc))

        return JSONResponse(data)

    async def cancel_run(request: Request) -> JSONResponse:
        run_id = request.path_params["id"]
        resp = adapter.cancel_run(run_id)
        status = 200 if resp.success else 400
        return JSONResponse(dataclasses.asdict(resp), status_code=status)

    async def apply_run(request: Request) -> JSONResponse:
        run_id = request.path_params["id"]
        resp = adapter.apply_run(run_id)
        status = 200 if resp.success else 400
        return JSONResponse(dataclasses.asdict(resp), status_code=status)

    async def dismiss_run(request: Request) -> JSONResponse:
        run_id = request.path_params["id"]
        resp = adapter.dismiss_run(run_id)
        status = 200 if resp.success else 400
        return JSONResponse(dataclasses.asdict(resp), status_code=status)

    async def get_artifact(request: Request) -> Response:
        artifact_id = request.path_params["id"]

        try:
            artifact = adapter._store.get_artifact(artifact_id)
        except ValueError:
            return _not_found("Artifact", artifact_id)

        content = _resolve_artifact_bytes(artifact, brain_path)
        if content is None:
            return Response(status_code=404, content=b"artifact content not found")

        return Response(
            content=content,
            media_type=artifact.mime_type,
            headers={"content-type": artifact.mime_type},
        )

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/capabilities", capabilities, methods=["GET"]),
        Route("/runs", list_runs, methods=["GET"]),
        Route("/runs", create_run, methods=["POST"]),
        Route("/runs/{id}", show_run, methods=["GET"]),
        Route("/runs/{id}/execute", execute_run, methods=["POST"]),
        Route("/runs/{id}/cancel", cancel_run, methods=["POST"]),
        Route("/runs/{id}/apply", apply_run, methods=["POST"]),
        Route("/runs/{id}/dismiss", dismiss_run, methods=["POST"]),
        Route("/artifacts/{id}", get_artifact, methods=["GET"]),
    ]

    return Starlette(debug=False, routes=routes)
