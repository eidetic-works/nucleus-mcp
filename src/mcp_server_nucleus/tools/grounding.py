"""Grounding MCP tool — C' harness exposed as nucleus_ground.

Lets any MCP client (Devin, Claude Code, Gemini, etc.) get oriented on
the current project state by retrieving RAG chunks from .brain/. This is
the C' harness (Devin + RAG, no TB) validated in the A/B/C/D context
reconstruction test (2026-08-06): 6s latency, accurate, no TB needed.

Phase 7 §2: passes project from manifest.yaml for cross-product filtering.
Phase 7 §3: passes agent_role for multi-agent identity filtering.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def register(mcp, helpers):
    """Register the nucleus_ground MCP tool."""

    make_response = helpers["make_response"]
    get_brain_path = helpers["get_brain_path"]

    @mcp.tool()
    async def nucleus_ground(
        task_context: str = "",
        session_id: str = "",
        agent_role: str = "",
        include_plan: bool = True,
        include_codebase: bool = True,
        topk: int = 5,
        include_recent_commits: bool = True,
    ) -> str:
        """Get oriented on the current project state by retrieving relevant context from .brain/. WHEN TO USE: at session start, when you feel lost mid-session, or before starting a new task — this retrieves recent decisions, plan context, and codebase patterns so you don't repeat work or miss prior decisions. Fast (~6s), no TB needed. Cross-product filtered (Phase 7 §2) + agent-role filtered (Phase 7 §3) so you only see chunks from this project + this agent role.

        Args:
            task_context: What you're about to do or want context on. More specific = better retrieval. Example: "fix the relay notification bug" or "what's the current state of the agent loop?".
            session_id: Current session ID. When provided, chunks from this session get a 0.15 RRF boost (session-scoped context injection). Empty = no session boost.
            agent_role: Agent role for identity filtering (Phase 7 §3). Uses relay canonical vocabulary: claude_code_main, claude_code_gq, devin, agy, cowork. When provided, cross-role chunks get demoted. Empty = no role filtering.
            include_plan: Retrieve plan/strategy context (default: true).
            include_codebase: Retrieve codebase patterns (default: true).
            topk: Number of chunks per section (default: 5).
            include_recent_commits: Retrieve recent git commits from the brain's parent repo (default: true). Surfaces commits from the last 48h so you don't duplicate work a concurrent agent already shipped. Degrades gracefully if the directory is not a git repo.

        Returns:
            JSON string with grounding brief: session_context, plan_context, codebase_context, conversation_context, and recent_commits sections.
        """
        try:
            brain_path = Path(get_brain_path())

            # Import the grounding logic from scripts/agent_grounding.py
            # We inline the logic here to avoid depending on scripts/ dir
            # (scripts/ is repo-internal, not part of the shipped package)
            providers_path = brain_path.parent / "providers"
            if str(providers_path) not in sys.path:
                sys.path.insert(0, str(providers_path.parent))

            from providers.brain_rag import search_brain, BRAIN_PATH, _read_brain_owner

            # Phase 7 §2: project identity from manifest.yaml
            project = _read_brain_owner(brain_path)

            # Phase 7 §3: agent_role — infer from env if not provided
            if not agent_role:
                agent_role = os.environ.get("CC_SESSION_ROLE", "") or os.environ.get("CONVERSATION_RAG_ROLE", "")

            # Use Mac Ollama for embeddings (fast, reliable)
            embed_url = os.environ.get("EMBED_OLLAMA_URL", "http://localhost:11434")
            original_url = os.environ.get("OLLAMA_URL", "")
            import providers.brain_rag as br
            br.OLLAMA_URL = embed_url

            import time
            start = time.time()

            brief = {
                "timestamp": time.time(),
                "session_id": session_id or "unknown",
                "agent_role": agent_role or "unknown",
                "task_context": task_context,
                "sections": {},
            }

            # 1. Session context (if session_id provided)
            if session_id:
                session_results = search_brain(
                    task_context or "recent decisions and actions in this session",
                    brain_path=brain_path,
                    session_id=session_id,
                    topk=topk,
                    project=project,
                    project_filter="demote",
                    agent_role=agent_role or None,
                    role_filter="demote" if agent_role else "off",
                )
                session_chunks = [r for r in session_results if r.get("session_id") == session_id]
                if session_chunks:
                    brief["sections"]["session_context"] = {
                        "chunks": len(session_chunks),
                        "items": [
                            {
                                "source": r.get("source", ""),
                                "content": r.get("content", "")[:200],
                                "age": r.get("time_band", ""),
                                "agent_role": r.get("agent_role", ""),
                            }
                            for r in session_chunks[:topk]
                        ],
                    }

            # 2. Plan context
            if include_plan:
                plan_results = search_brain(
                    task_context or "project plan next steps priorities",
                    brain_path=brain_path,
                    scope="life",
                    topk=3,
                    project=project,
                    project_filter="demote",
                    agent_role=agent_role or None,
                    role_filter="demote" if agent_role else "off",
                )
                if plan_results:
                    brief["sections"]["plan_context"] = {
                        "chunks": len(plan_results),
                        "items": [
                            {
                                "source": r.get("source", ""),
                                "content": r.get("content", "")[:200],
                                "age": r.get("time_band", ""),
                                "agent_role": r.get("agent_role", ""),
                            }
                            for r in plan_results[:3]
                        ],
                    }

            # 3. Codebase context
            if include_codebase and task_context:
                code_results = search_brain(
                    task_context,
                    brain_path=brain_path,
                    scope="code",
                    topk=3,
                    project=project,
                    project_filter="demote",
                    agent_role=agent_role or None,
                    role_filter="demote" if agent_role else "off",
                )
                if code_results:
                    brief["sections"]["codebase_context"] = {
                        "chunks": len(code_results),
                        "items": [
                            {
                                "source": r.get("source", ""),
                                "content": r.get("content", "")[:200],
                                "age": r.get("time_band", ""),
                                "agent_role": r.get("agent_role", ""),
                            }
                            for r in code_results[:3]
                        ],
                    }

            # 4. Conversation context (Phase 7 §4) — what agents discussed
            # recently about this topic. This is the harness's core assistive
            # function: surface relevant conversation history so the agent
            # doesn't repeat work or miss prior decisions.
            if task_context:
                conv_results = search_brain(
                    task_context,
                    brain_path=brain_path,
                    scope="conversation",
                    topk=5,
                    project=project,
                    project_filter="demote",
                    agent_role=agent_role or None,
                    role_filter="demote" if agent_role else "off",
                )
                if conv_results:
                    brief["sections"]["conversation_context"] = {
                        "chunks": len(conv_results),
                        "items": [
                            {
                                "source": r.get("source", ""),
                                "content": r.get("content", "")[:200],
                                "age": r.get("time_band", ""),
                                "agent_role": r.get("agent_role", ""),
                                "repo_id": r.get("repo_id", ""),
                            }
                            for r in conv_results[:5]
                        ],
                    }

            # 5. Recent commits (Phase 7 §5) — surface commits from the
            # last 48h so the agent doesn't duplicate work a concurrent
            # agent already shipped. Degrades gracefully (None = omit).
            if include_recent_commits:
                from ..selfhealer import _collect_recent_commits
                items = _collect_recent_commits(brain_path.parent)
                if items is not None:
                    brief["sections"]["recent_commits"] = {
                        "count": len(items),
                        "items": items,
                    }

            brief["latency_s"] = round(time.time() - start, 2)

            # Restore Ollama URL
            br.OLLAMA_URL = original_url

            return make_response(True, data=brief)

        except Exception as e:
            return make_response(False, error=f"Grounding failed: {e}")

    return [nucleus_ground]
