"""Agent OS — External Agent Boot Path (Stage 4 platform).

Exposes ``nucleus_agent_os_boot`` — an MCP tool that lets ANY external agent
boot into the Nucleus Agent OS for one turn. The external agent connects via
MCP, calls this tool with a prompt, and gets back:

  1. Recalled memory (injected before thinking)
  2. A mediated model response (through the Nucleus gateway)
  3. A verified label (the referee's verdict on the response)
  4. A recorded turn (in the flywheel)

This is the Stage 4 platform primitive: external agents can boot into Nucleus
without being internal agents. The OS mediates their cognition, verifies their
claims, and records their turns — they live inside for one turn.

ADR-0047 Workstream E1: the external boot path.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("nucleus.tool.agent_os_boot")

_BOOT_FLAG = "NUCLEUS_AGENT_OS_BOOT"
_VERIFIED_RECORD_FLAG = "NUCLEUS_AGENT_OS_VERIFIED_RECORD"


def register(mcp, helpers):
    """Register the nucleus_agent_os_boot facade tool."""
    make_response = resolve_make_response(helpers)

    def _agent_os_boot(
        prompt: str,
        *,
        recall_query: Optional[str] = None,
        agent_id: str = "external-agent",
        session_id: str = "external-session",
        capability: str = "any",
        brain_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Boot an external agent into the Nucleus OS for one turn.

        The external agent provides a prompt. The OS:
          1. Recalls memory relevant to the prompt
          2. Injects it before thinking
          3. Mediates the model call through the Nucleus gateway
          4. Labels the response with a referee verdict
          5. Records the turn to the flywheel

        Returns a dict with:
          - response: the mediated model response
          - engine: which engine was used
          - mediated: True if the gateway mediated the call
          - recalled_count: number of memory rows recalled
          - verified_label: the referee's verdict
          - turn_id: the recorded turn ID
        """
        resolved_brain = brain_path or os.environ.get("NUCLEUS_BRAIN_PATH")
        if not resolved_brain:
            return make_response(
                error="NUCLEUS_BRAIN_PATH not set — cannot boot without a brain path"
            )

        # Set boot/verified-record flags only for the duration of boot_cell,
        # then unconditionally pop them so a successful boot does not leak
        # NUCLEUS_AGENT_OS_BOOT=1 into the process env (which would silently
        # flip subsequent non-boot calls into the Agent OS code path).
        os.environ[_BOOT_FLAG] = "1"
        os.environ[_VERIFIED_RECORD_FLAG] = "1"
        try:
            from ..runtime.agent_os import boot
            result = boot.boot_cell(
                prompt,
                recall_query=recall_query or prompt,
                brain_path=resolved_brain,
                tools_used=["external_boot", agent_id],
            )

            g = result.gateway_result
            verified = None
            if hasattr(result, "verified_label") and result.verified_label:
                verified = result.verified_label
            elif hasattr(result, "turn") and result.turn:
                turn_data = getattr(result.turn, "__dict__", {})
                verified = turn_data.get("verified_label")

            turn_id = getattr(result.turn, "turn_id", None) if result.turn else None

            return make_response(
                result={
                    "response": g.text,
                    "engine": g.engine,
                    "mediated": g.mediated,
                    "stubbed": g.stubbed,
                    "recalled_count": len(result.recalled_rows),
                    "verified_label": verified,
                    "turn_id": turn_id,
                    "event_id": g.event_id,
                }
            )
        except Exception as exc:
            logger.exception("agent_os_boot failed")
            return make_response(error=f"boot failed: {exc}")
        finally:
            os.environ.pop(_BOOT_FLAG, None)
            os.environ.pop(_VERIFIED_RECORD_FLAG, None)

    @mcp.tool(
        name="nucleus_agent_os_boot",
        description=(
            "Boot an external agent into the Nucleus Agent OS for one turn. "
            "The OS recalls memory, mediates the model call, labels the response "
            "with a referee verdict, and records the turn. Stage 4 platform primitive."
        ),
        # NOT read-only: this boots the agent OS, mediates a model call and
        # RECORDS the turn, so it writes. destructiveHint stays False because it
        # appends rather than removing or overwriting anything.
        annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    )
    def nucleus_agent_os_boot(
        prompt: str,
        recall_query: Optional[str] = None,
        agent_id: str = "external-agent",
        session_id: str = "external-session",
        capability: str = "any",
        brain_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Boot an external agent into the Nucleus OS for one turn."""
        return _agent_os_boot(
            prompt,
            recall_query=recall_query,
            agent_id=agent_id,
            session_id=session_id,
            capability=capability,
            brain_path=brain_path,
        )

    return [("nucleus_agent_os_boot", nucleus_agent_os_boot)]


def resolve_make_response(helpers):
    """Resolve the make_response helper from the server helpers."""
    if helpers and "make_response" in helpers:
        return helpers["make_response"]

    def _make(result=None, error=None):
        if error:
            return {"error": error}
        return {"result": result}
    return _make


__all__ = ["register"]
