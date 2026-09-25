"""ACP stdio JSON-RPC server exposing the Nucleus run engine."""
from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

if "--check" in sys.argv:
    try:
        v = _pkg_version("agent-client-protocol")
    except Exception:
        v = "unknown"
    print(v)
    sys.exit(0)

import acp
import acp.helpers as acp_helpers
from acp.schema import (
    AgentCapabilities,
    Implementation,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    SessionInfo,
    SessionInfoUpdate,
    SetSessionModeResponse,
    TextContentBlock,
)

from .mcp_adapter import RunMcpAdapter
from .models import RunState

_TERMINAL_STATES = {
    RunState.READY_FOR_REVIEW.value,
    RunState.COMPLETED.value,
    RunState.APPLIED.value,
    RunState.DISMISSED.value,
    RunState.FAILED.value,
    RunState.CANCELLED.value,
}

_VALID_TRUST_MODES = {"permissive", "default", "strict"}


@dataclass
class _Session:
    session_id: str
    project_id: str
    conversation_id: str
    run_id: str
    cwd: str
    prompt: str
    last_heartbeat: float = field(default_factory=time.time)
    heartbeat_timeout: float = 60.0


def _is_valid_trust_mode(trust_mode: str | None) -> bool:
    return trust_mode in _VALID_TRUST_MODES


class NucleusAgent:
    """ACP agent backed by the Nucleus Renaissance run engine."""

    def __init__(self, conn: Any, adapter: RunMcpAdapter) -> None:
        self._conn = conn
        self._adapter = adapter
        self._sessions: dict[str, _Session] = {}
        self._pending_trust: dict[str, dict[str, Any]] = {}
        self._load_sessions()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

    def _load_sessions(self) -> None:
        timeout = float(os.environ.get("NUCLEUS_HEARTBEAT_TIMEOUT", "60"))
        for session in self._adapter.list_sessions():
            self._sessions[session.id] = _Session(
                session_id=session.id,
                project_id=session.project_id,
                conversation_id=session.conversation_id,
                run_id=session.run_id,
                cwd=session.cwd or "",
                prompt=session.prompt or "",
                last_heartbeat=time.time(),
                heartbeat_timeout=timeout,
            )

    async def _heartbeat_monitor(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            now = time.time()
            for session_id, session in list(self._sessions.items()):
                run = self._adapter._store.get_run(session.run_id)
                if run.state in _TERMINAL_STATES:
                    continue
                if now - session.last_heartbeat > session.heartbeat_timeout:
                    try:
                        await self._adapter.cancel_run(session.run_id)
                    except Exception:
                        pass

    async def _emit_state(self, session_id: str, state: str, meta: dict | None = None) -> None:
        if self._conn is None:
            return
        try:
            field_meta = {"state": state}
            if meta:
                field_meta.update(meta)
            await self._conn.session_update(
                session_id=session_id,
                update=SessionInfoUpdate(
                    session_update="session_info_update",
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    field_meta=field_meta,
                ),
            )
        except Exception:
            pass

    async def _emit_permission_request(self, session_id: str, field_meta: dict) -> None:
        """Emit a raw session/update notification for a trust-mode permission request."""
        if self._conn is None:
            return
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": session_id,
                    "update": {
                        "kind": "request_permission",
                        "session_update": "session_info_update",
                        "field_meta": field_meta,
                    },
                },
            }
            await self._conn._conn.send_notification("session/update", payload["params"])
        except Exception:
            pass

    def _trust_permission_meta(self, session_id: str) -> dict:
        return {
            "permission_type": "trust_mode",
            "choices": ["permissive", "default", "strict"],
            "session_id": session_id,
        }

    def _request_permission_response(self, session_id: str) -> dict:
        field_meta = self._trust_permission_meta(session_id)
        return {
            "sessionId": session_id,
            "stop_reason": "request_permission",
            "field_meta": field_meta,
        }

    def _session_info(
        self,
        session_id: str,
        cwd: str,
        prompt: str,
        updated_at: str,
    ) -> SessionInfo:
        return SessionInfo(
            session_id=session_id,
            cwd=cwd or None,
            title=prompt[:80] if prompt else None,
            updated_at=updated_at,
        )

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: Any | None = None,
        client_info: Any | None = None,
    ) -> InitializeResponse:
        try:
            v = _pkg_version("nucleus-mcp")
        except Exception:
            v = "unknown"
        return InitializeResponse(
            protocol_version=protocol_version,
            agent_info=Implementation(
                name="nucleus-acp",
                title="Nucleus ACP Server",
                version=v,
            ),
            agent_capabilities=AgentCapabilities(
                load_session=True,
            ),
        )

    def _project_for_cwd(self, cwd: str) -> dict | None:
        return self._adapter.get_project_by_root(cwd)

    def _create_run_session(
        self,
        cwd: str,
        prompt: str,
        project_id: str,
        session_id: str | None = None,
    ) -> str:
        conversation_id = self._adapter.create_conversation(project_id, "ACP session")
        run_id = self._adapter.create_run(conversation_id, prompt or "")
        if session_id is None:
            session_id = run_id
        timeout = float(os.environ.get("NUCLEUS_HEARTBEAT_TIMEOUT", "60"))
        self._adapter.create_session(
            session_id=session_id,
            run_id=run_id,
            conversation_id=conversation_id,
            project_id=project_id,
            cwd=cwd,
            prompt=prompt or "",
        )
        self._sessions[session_id] = _Session(
            session_id=session_id,
            project_id=project_id,
            conversation_id=conversation_id,
            run_id=run_id,
            cwd=cwd,
            prompt=prompt or "",
            last_heartbeat=time.time(),
            heartbeat_timeout=timeout,
        )
        return run_id

    async def new_session(
        self,
        cwd: str,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        prompt: str = "",
        **kwargs: Any,
    ) -> NewSessionResponse | dict:
        project = self._project_for_cwd(cwd)

        if project is None or not _is_valid_trust_mode(project.get("trust_mode")):
            default_trust = os.environ.get("NUCLEUS_DEFAULT_TRUST_MODE", "").strip()
            if _is_valid_trust_mode(default_trust):
                project_id = self._adapter.get_or_create_project(cwd, default_trust)
                run_id = self._create_run_session(cwd, prompt, project_id)
                run = self._adapter._store.get_run(run_id)
                asyncio.create_task(self._emit_state(run_id, run.state.value))
                return NewSessionResponse(
                    session_id=run_id,
                    field_meta={
                        "stop_reason": "acceptance",
                        "session_id": run_id,
                        "state": run.state.value,
                    },
                )

            session_id = str(uuid.uuid4())
            self._pending_trust[session_id] = {
                "project_root": cwd,
                "project_id": project.get("id") if project else None,
            }
            field_meta = self._trust_permission_meta(session_id)
            asyncio.create_task(self._emit_permission_request(session_id, field_meta))
            return self._request_permission_response(session_id)

        project_id = project["id"]
        run_id = self._create_run_session(cwd, prompt, project_id)
        run = self._adapter._store.get_run(run_id)
        asyncio.create_task(self._emit_state(run_id, run.state.value))
        return NewSessionResponse(
            session_id=run_id,
            field_meta={
                "stop_reason": "acceptance",
                "session_id": run_id,
                "state": run.state.value,
            },
        )

    async def list_sessions(
        self,
        cwd: str | None = None,
        cursor: str | None = None,
    ) -> ListSessionsResponse:
        sessions_by_id: dict[str, SessionInfo] = {}
        for session in self._adapter.list_sessions():
            try:
                run = self._adapter._store.get_run(session.run_id)
                updated_at = run.updated_at.isoformat()
            except Exception:
                updated_at = session.updated_at.isoformat()
            sessions_by_id[session.id] = self._session_info(
                session.id,
                session.cwd or "",
                session.prompt,
                updated_at,
            )
        for session_id, session in self._sessions.items():
            if session_id in sessions_by_id:
                continue
            try:
                run = self._adapter._store.get_run(session_id)
                updated_at = run.updated_at.isoformat()
            except Exception:
                updated_at = datetime.now(timezone.utc).isoformat()
            sessions_by_id[session_id] = self._session_info(
                session_id,
                session.cwd,
                session.prompt,
                updated_at,
            )
        return ListSessionsResponse(sessions=list(sessions_by_id.values()))

    async def load_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[Any] | None = None,
        additional_directories: list[str] | None = None,
    ) -> LoadSessionResponse:
        if session_id in self._pending_trust:
            pending = self._pending_trust[session_id]
            return LoadSessionResponse(
                field_meta={
                    "session_id": session_id,
                    "state": "request_permission",
                    "cwd": cwd,
                    "project_root": pending["project_root"],
                }
            )

        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            cached = self._sessions[session_id]
            session = cached
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        try:
            run = self._adapter._store.get_run(session_id)
            state = run.state.value
        except Exception:
            state = "unknown"

        if isinstance(session, _Session):
            cwd_val = session.cwd
            prompt_val = session.prompt
        else:
            cwd_val = session.cwd or ""
            prompt_val = session.prompt
        return LoadSessionResponse(
            field_meta={
                "session_id": session_id,
                "state": state,
                "cwd": cwd_val,
                "prompt": prompt_val,
            }
        )

    async def set_session_mode(self, session_id: str, mode_id: str, **kwargs: Any) -> SetSessionModeResponse:
        state = "unknown"
        try:
            run = self._adapter._store.get_run(session_id)
            state = run.state.value
        except Exception:
            pass
        return SetSessionModeResponse(
            field_meta={
                "session_id": session_id,
                "mode_id": mode_id,
                "state": state,
            },
        )

    async def cancel(self, session_id: str) -> dict:
        if session_id in self._pending_trust:
            self._pending_trust.pop(session_id, None)
            await self._emit_state(session_id, "cancelled")
            return {"_meta": {"session_id": session_id, "state": "cancelled"}}

        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        self._adapter.cancel_run(session.run_id)
        try:
            run = self._adapter._store.get_run(session.run_id)
            if run.state not in (RunState.PREPARING, RunState.RUNNING, RunState.VERIFYING):
                self._adapter._store.transition_run(
                    session.run_id,
                    RunState.CANCELLED,
                    "run.cancelled",
                    {"issuer": "acp"},
                )
        except Exception:
            pass

        try:
            run = self._adapter._store.get_run(session.run_id)
            state = run.state.value
        except Exception:
            state = "cancelled"

        await self._emit_state(session_id, state)
        return {"_meta": {"session_id": session_id, "state": state}}

    @staticmethod
    def _extract_prompt_text(prompt: list[Any] | Any) -> str:
        if isinstance(prompt, str):
            return prompt
        if not isinstance(prompt, list):
            return str(prompt)

        parts: list[str] = []
        for block in prompt:
            if isinstance(block, TextContentBlock):
                parts.append(block.text)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content") or ""
                parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
            else:
                # Generic fallback: try common text-bearing attrs.
                for attr in ("text", "content", "value"):
                    if hasattr(block, attr):
                        value = getattr(block, attr)
                        if value:
                            parts.append(str(value))
                            break
        return "\n".join(parts)

    async def _run_prompt_session(self, session_id: str) -> None:
        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            await self._emit_state(session_id, "failed", {"error": "session not found"})
            return

        run_id = session.run_id
        previous_state = self._adapter._store.get_run(run_id).state.value

        def _execute():
            return self._adapter.execute_run(run_id)

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, _execute)

        while not future.done():
            await asyncio.sleep(0.25)
            try:
                run = self._adapter._store.get_run(run_id)
                current_state = run.state.value
                if current_state != previous_state and current_state not in _TERMINAL_STATES:
                    await self._emit_state(session_id, current_state)
                    previous_state = current_state
            except Exception:
                pass

        async def _emit_agent_text(text: str) -> None:
            if self._conn is None:
                return
            try:
                await self._conn.session_update(
                    session_id=session_id,
                    update=acp_helpers.update_agent_message_text(text),
                )
            except Exception:
                pass

        try:
            final = await future
        except Exception as exc:
            try:
                run = self._adapter._store.get_run(run_id)
                current_state = run.state.value
            except Exception:
                current_state = "failed"
            await self._emit_state(session_id, current_state, {"error": str(exc)})
            await _emit_agent_text(f"Run failed: {exc}")
            return

        # Wait for a detached worker to finish, if needed.
        while final["run"]["state"] not in _TERMINAL_STATES:
            await asyncio.sleep(1.0)
            try:
                final = self._adapter.show_run(run_id)
                current_state = final["run"]["state"]
                if current_state != previous_state and current_state not in _TERMINAL_STATES:
                    await self._emit_state(session_id, current_state)
                    previous_state = current_state
            except Exception:
                pass

        run = final["run"]
        result = {
            "state": run["state"],
            "events": len(final.get("events", [])),
        }
        output = ""
        if final.get("bundle"):
            bundle = final["bundle"]
            if isinstance(bundle, dict):
                output = bundle.get("output", "")
                result["output"] = output
                result["status"] = bundle.get("status", "")
        await self._emit_state(session_id, run["state"], {"result": result})
        if output:
            await _emit_agent_text(output)
        else:
            await _emit_agent_text(f"Run finished with state: {run['state']}")

    def _is_acp_sdk(self, kwargs: dict[str, Any]) -> bool:
        """ACP SDK clients pass an idempotency_key; legacy JSON-RPC callers block."""
        return bool(kwargs.get("idempotency_key")) or bool(
            (kwargs.get("field_meta") or {}).get("idempotency_key")
        )

    async def _do_prompt(self, cwd: str, prompt_text: str, **kwargs: Any) -> Any:
        """Shared logic for session/prompt and approve_permission with prompt."""
        new_session = await self.new_session(
            cwd=cwd,
            prompt=prompt_text,
        )
        if isinstance(new_session, dict):
            # Trust request pending; return a Prompt-shaped response.
            return {
                "stopReason": "request_permission",
                "field_meta": new_session.get("field_meta", {}),
            }

        run_id = new_session.session_id
        asyncio.create_task(self._run_prompt_session(run_id))

        run = self._adapter._store.get_run(run_id)
        return PromptResponse(
            stop_reason="end_turn",
            field_meta={
                "session_id": run_id,
                "state": run.state.value,
            },
        )

    async def prompt(
        self,
        session_id: str,
        prompt: list[Any],
        cwd: str | None = None,
        **kwargs: Any,
    ) -> Any:
        prompt_text = self._extract_prompt_text(prompt) or kwargs.get("prompt_text", "")

        if session_id == "new":
            if not cwd:
                raise acp.RequestError.invalid_params({"cwd": "required for new session"})
            return await self._do_prompt(cwd, prompt_text, **kwargs)

        if session_id in self._pending_trust:
            field_meta = self._trust_permission_meta(session_id)
            await self._emit_permission_request(session_id, field_meta)
            return {
                "stopReason": "request_permission",
                "field_meta": field_meta,
            }

        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        try:
            project = self._adapter._store.get_project_for_run(session.run_id)
            if not _is_valid_trust_mode(project.trust_mode):
                field_meta = self._trust_permission_meta(session_id)
                await self._emit_permission_request(session_id, field_meta)
                return {
                    "stopReason": "request_permission",
                    "field_meta": field_meta,
                }
        except Exception:
            pass

        run_id = self._adapter.create_run(
            session.conversation_id,
            prompt_text,
            runner_id=os.environ.get("NUCLEUS_DEFAULT_RUNNER", "agy"),
            idempotency_key=f"{session.conversation_id}-{os.environ.get('NUCLEUS_DEFAULT_RUNNER', 'agy')}-{uuid.uuid4()}",
        )
        self._adapter.update_session(session_id, run_id=run_id, prompt=prompt_text)
        self._sessions[session_id] = _Session(
            session_id=session_id,
            project_id=session.project_id,
            conversation_id=session.conversation_id,
            run_id=run_id,
            cwd=session.cwd or cwd or "",
            prompt=prompt_text,
            last_heartbeat=time.time(),
            heartbeat_timeout=self._sessions[session_id].heartbeat_timeout,
        )

        run_task = asyncio.create_task(self._run_prompt_session(session_id))
        if not self._is_acp_sdk(kwargs):
            try:
                await run_task
            except Exception:
                pass

        run = self._adapter._store.get_run(run_id)
        return PromptResponse(
            stop_reason="end_turn",
            field_meta={
                "session_id": session_id,
                "state": run.state.value,
            },
        )

    async def apply_session(self, session_id: str, **kwargs: Any) -> dict:
        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        run_id = session.run_id
        run = self._adapter._store.get_run(run_id)
        if run.state not in (RunState.READY_FOR_REVIEW, RunState.COMPLETED):
            raise acp.RequestError.invalid_params(
                {"state": f"cannot apply from {run.state.value}"}
            )

        response = self._adapter.apply_run(run_id)
        if not response.success:
            raise acp.RequestError.invalid_params({"apply": response.error or "failed"})

        return {
            "session_id": session_id,
            "run_id": run_id,
            "_meta": {
                "session_id": session_id,
                "run_id": run_id,
                "state": self._adapter._store.get_run(run_id).state.value,
            },
        }

    async def dismiss_session(self, session_id: str, **kwargs: Any) -> dict:
        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        run_id = session.run_id
        run = self._adapter._store.get_run(run_id)
        if run.state not in (
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.APPLYING,
        ):
            raise acp.RequestError.invalid_params(
                {"state": f"cannot dismiss from {run.state.value}"}
            )

        response = self._adapter.dismiss_run(run_id)
        if not response.success:
            raise acp.RequestError.invalid_params({"dismiss": response.error or "failed"})

        return {
            "session_id": session_id,
            "run_id": run_id,
            "_meta": {
                "session_id": session_id,
                "run_id": run_id,
                "state": self._adapter._store.get_run(run_id).state.value,
            },
        }

    async def session_status(self, session_id: str, **kwargs: Any) -> dict:
        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        run_id = session.run_id
        try:
            details = self._adapter.show_run(run_id)
        except Exception as exc:
            raise acp.RequestError.invalid_params({"run_id": str(exc)})

        run_dict = details.get("run", {}) or {}
        state = run_dict.get("state", "unknown")
        bundle = details.get("bundle", {}) or {}
        output = bundle.get("output", "") or ""

        return {
            "session_id": session_id,
            "run_id": run_id,
            "state": state,
            "output": output,
            "_meta": {
                "session_id": session_id,
                "run_id": run_id,
                "state": state,
                "output": output,
            },
        }

    async def heartbeat_session(self, session_id: str, **kwargs: Any) -> dict:
        """Refresh the client heartbeat for a session."""
        if session_id in self._sessions:
            self._sessions[session_id].last_heartbeat = time.time()
        else:
            session = self._adapter.get_session(session_id)
            if session is None:
                raise acp.RequestError.invalid_params({"session_id": "not found"})
            timeout = float(os.environ.get("NUCLEUS_HEARTBEAT_TIMEOUT", "60"))
            self._sessions[session_id] = _Session(
                session_id=session_id,
                project_id=session.project_id,
                conversation_id=session.conversation_id,
                run_id=session.run_id,
                cwd=session.cwd or "",
                prompt=session.prompt or "",
                last_heartbeat=time.time(),
                heartbeat_timeout=timeout,
            )
        return {
            "session_id": session_id,
            "heartbeat": "ok",
            "_meta": {"session_id": session_id, "heartbeat": "ok"},
        }

    async def retry_session(self, session_id: str, **kwargs: Any) -> dict:
        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        prompt_text = session.prompt or ""
        run_id = self._adapter.create_run(
            session.conversation_id,
            prompt_text,
            runner_id=os.environ.get("NUCLEUS_DEFAULT_RUNNER", "agy"),
            idempotency_key=f"{session.conversation_id}-{os.environ.get('NUCLEUS_DEFAULT_RUNNER', 'agy')}-{uuid.uuid4()}",
        )
        self._adapter.update_session(session_id, run_id=run_id, prompt=prompt_text)
        self._sessions[session_id] = _Session(
            session_id=session_id,
            project_id=session.project_id,
            conversation_id=session.conversation_id,
            run_id=run_id,
            cwd=session.cwd or "",
            prompt=prompt_text,
            last_heartbeat=time.time(),
            heartbeat_timeout=self._sessions[session_id].heartbeat_timeout,
        )

        run_task = asyncio.create_task(self._run_prompt_session(session_id))
        try:
            await asyncio.wait_for(run_task, timeout=600)
        except asyncio.TimeoutError:
            pass
        run = self._adapter._store.get_run(run_id)
        return {
            "session_id": session_id,
            "run_id": run_id,
            "_meta": {
                "session_id": session_id,
                "run_id": run_id,
                "state": run.state.value,
            },
        }

    async def fork_session(
        self,
        session_id: str,
        cwd: str | None = None,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        session = self._adapter.get_session(session_id)
        if session is None and session_id in self._sessions:
            session = self._sessions[session_id]
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        new_session_id = self._create_run_session(
            cwd or session.cwd or "",
            session.prompt or "",
            session.project_id,
        )
        return NewSessionResponse(
            session_id=new_session_id,
            field_meta={
                "source_session_id": session_id,
                "session_id": new_session_id,
                "cwd": cwd or session.cwd or "",
            },
        )

    async def resume_session(self, session_id: str, **kwargs: Any) -> dict:
        """Reconnect to an existing session and re-attach to a live run if needed."""
        session = self._adapter.get_session(session_id)
        if session is None:
            raise acp.RequestError.invalid_params({"session_id": "not found"})

        if session_id not in self._sessions:
            timeout = float(os.environ.get("NUCLEUS_HEARTBEAT_TIMEOUT", "60"))
            self._sessions[session_id] = _Session(
                session_id=session_id,
                project_id=session.project_id,
                conversation_id=session.conversation_id,
                run_id=session.run_id,
                cwd=session.cwd or "",
                prompt=session.prompt or "",
                last_heartbeat=time.time(),
                heartbeat_timeout=timeout,
            )
        else:
            self._sessions[session_id].last_heartbeat = time.time()

        run_id = session.run_id
        run = self._adapter._store.get_run(run_id)

        if run.state not in _TERMINAL_STATES:
            asyncio.create_task(self._run_prompt_session(session_id))

        try:
            details = self._adapter.show_run(run_id)
        except Exception:
            details = {}

        run_dict = details.get("run", {}) or {}
        state = run_dict.get("state", run.state.value)
        bundle = details.get("bundle", {}) or {}
        output = bundle.get("output", "") or ""

        return {
            "session_id": session_id,
            "run_id": run_id,
            "state": state,
            "output": output,
            "_meta": {
                "session_id": session_id,
                "run_id": run_id,
                "state": state,
                "output": output,
            },
        }

    async def approve_permission(
        self,
        session_id: str,
        trust_mode: str,
        prompt: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        if not _is_valid_trust_mode(trust_mode):
            raise acp.RequestError.invalid_params(
                {"trust_mode": f"must be one of {_VALID_TRUST_MODES}"}
            )

        if session_id not in self._pending_trust:
            raise acp.RequestError.invalid_params(
                {"session_id": "no pending trust request found"}
            )

        pending = self._pending_trust.pop(session_id)
        project_root = pending["project_root"]
        project_id = self._adapter.get_or_create_project(project_root, trust_mode)

        if prompt is not None and prompt != [] and prompt != "":
            prompt_text = self._extract_prompt_text(prompt) if isinstance(prompt, list) else str(prompt)
            return await self._do_prompt(project_root, prompt_text)

        project = self._adapter._store.get_project(project_id)
        return {
            "stop_reason": "end_turn",
            "field_meta": {
                "session_id": session_id,
                "project_root": project_root,
                "project_id": project_id,
                "trust_mode": project.trust_mode,
            },
        }


async def _main() -> int:
    brain_path = Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")).resolve()
    db_path = brain_path / "runs" / "store.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db_path)

    def factory(conn: Any) -> NucleusAgent:
        return NucleusAgent(conn, adapter)

    from acp.agent import connection as _acp_agent_connection
    from acp.agent import router as _acp_agent_router
    from pydantic import BaseModel, Field

    _original_build_agent_router = _acp_agent_connection.build_agent_router

    class _ApprovePermissionParams(BaseModel):
        session_id: str = Field(alias="sessionId")
        trust_mode: str
        prompt: Any | None = None
        field_meta: dict[str, Any] | None = Field(default=None, alias="_meta")

    class _SessionIdParams(BaseModel):
        session_id: str = Field(alias="sessionId")
        field_meta: dict[str, Any] | None = Field(default=None, alias="_meta")

    class _ForkSessionParams(BaseModel):
        session_id: str = Field(alias="sessionId")
        cwd: str | None = None
        additional_directories: list[str] | None = None
        mcp_servers: list[Any] | None = None
        field_meta: dict[str, Any] | None = Field(default=None, alias="_meta")

    def _build_agent_router_with_approve(agent: Any, use_unstable_protocol: bool = False):
        router = _original_build_agent_router(agent, use_unstable_protocol=use_unstable_protocol)

        async def _handle_approve(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _ApprovePermissionParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.approve_permission(**kw)

        async def _handle_status(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.session_status(**kw)

        async def _handle_retry(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.retry_session(**kw)

        async def _handle_resume(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.resume_session(**kw)

        async def _handle_heartbeat(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.heartbeat_session(**kw)

        async def _handle_fork(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _ForkSessionParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.fork_session(**kw)

        async def _handle_apply(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.apply_session(**kw)

        async def _handle_dismiss(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.dismiss_session(**kw)

        async def _handle_cancel(params: Any) -> Any:
            if isinstance(params, dict):
                validated = _SessionIdParams.model_validate(params)
            else:
                validated = params
            kw = validated.model_dump(exclude_unset=True)
            kw.pop("field_meta", None)
            if validated.field_meta:
                kw.update(validated.field_meta)
            return await agent.cancel(**kw)

        router.add_route(
            _acp_agent_router.Route(
                method="session/approve_permission",
                func=_handle_approve,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/status",
                func=_handle_status,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/retry",
                func=_handle_retry,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/resume",
                func=_handle_resume,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/heartbeat",
                func=_handle_heartbeat,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/fork",
                func=_handle_fork,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/apply",
                func=_handle_apply,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/dismiss",
                func=_handle_dismiss,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        router.add_route(
            _acp_agent_router.Route(
                method="session/cancel",
                func=_handle_cancel,
                kind="request",
                adapt_result=_acp_agent_router.normalize_result,
            )
        )
        return router

    _acp_agent_connection.build_agent_router = _build_agent_router_with_approve

    try:
        await acp.run_agent(factory)
    except asyncio.CancelledError:
        pass
    return 0


def main() -> int:
    if "--check" in sys.argv:
        try:
            v = _pkg_version("agent-client-protocol")
        except Exception:
            v = "unknown"
        print(v)
        return 0
    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
