"""Nucleus Agent OS — Cognition Scheduler (MEMBRANE §1).

The law (MEMBRANE.md §1): *the agent holds no key and picks no model. It emits
a cognition request with a capability hint; the membrane schedules it onto the
cheapest path that clears the bar, invisibly.*

This module implements that policy. ``schedule_engine`` takes a capability hint
("cheap" / "reasoning" / "any") and returns the first available provider in
priority order, trying each one and falling through on failure. The agent loop
is written once and runs on whatever's available — subscription today, free
tier tomorrow, a frontier key when it must.

Priority order (cheapest-capable-first):
  1. ``antigravity`` — Google OAuth (Antigravity / Cloud Code Assist), ~free
  2. ``groq`` — free tier, 30 RPM, llama-3.3-70b (fast, good for "cheap")
  3. ``gemini`` — free API key tier from aistudio.google.com
  4. ``claude_oauth`` — Max plan OAuth (quota-bounded, but frontier quality)
  5. ``anthropic`` — paid API key (most expensive, always-on)

The scheduler is a **policy**, not a feature. It learns from the flywheel
which provider cleared which bar at least cost (MEMBRANE §3 — future). Today
it's a static priority list; tomorrow it's learned.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger("nucleus.agent_os.scheduler")

# Capability hints the agent can emit.
CAP_CHEAP = "cheap"          # classify, summarize, simple extraction
CAP_REASONING = "reasoning"  # multi-step, code generation, analysis
CAP_ANY = "any"              # no hint — use default order

_TRUTHY = frozenset({"1", "true", "yes", "on"})


@dataclass
class ProviderAttempt:
    """One provider tried by the scheduler."""
    provider: str
    engine: str           # real engine label or "" if construction failed
    client: object         # the LLM client, or None
    error: str             # "" on success, error message on failure


def _provider_available(provider: str) -> bool:
    """Check if a provider's credentials are present without constructing it."""
    if provider in ("antigravity", "antigravity_oauth"):
        from pathlib import Path
        return (Path.home() / ".tb" / "oauth_antigravity.json").exists()
    if provider in ("grok", "grok_oauth"):
        from pathlib import Path
        return (Path.home() / ".tb" / "oauth_grok.json").exists()
    if provider == "groq":
        return bool(os.environ.get("NUCLEUS_GROQ_API_KEY"))
    if provider == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY"))
    if provider in ("claude_oauth", "claude_max", "oauth"):
        from pathlib import Path
        return (Path.home() / ".tb" / "oauth_bespoq_cowork.json").exists()
    if provider == "anthropic":
        return bool(os.environ.get("NUCLEUS_ANTHROPIC_API_KEY"))
    return False


def _priority_order(capability: str) -> List[str]:
    """Return the provider priority list for a capability hint.

    The order encodes the MEMBRANE §1 policy: cheapest-capable-first.
    """
    base = ["antigravity", "groq", "gemini", "claude_oauth", "anthropic"]
    if capability == CAP_CHEAP:
        # Cheap tasks: prefer Groq (fastest) then Antigravity then Gemini.
        return ["groq", "antigravity", "gemini", "claude_oauth", "anthropic"]
    if capability == CAP_REASONING:
        # Reasoning tasks: prefer frontier (Claude) then Antigravity (Gemini Pro).
        return ["claude_oauth", "antigravity", "gemini", "groq", "anthropic"]
    return base


def schedule_engine(
    capability: str = CAP_ANY,
    *,
    system_instruction: Optional[str] = None,
    force_provider: Optional[str] = None,
    skip: Optional[List[str]] = None,
) -> Tuple[Optional[object], str, List[ProviderAttempt]]:
    """Schedule a cognition request onto the cheapest capable provider.

    Returns ``(client, engine_label, attempts)``. On success, ``client`` is a
    real LLM client and ``engine_label`` is its engine string. On failure,
    ``client`` is None and ``attempts`` lists every provider tried + why it
    failed.

    If ``force_provider`` is set (or ``NUCLEUS_LLM_PROVIDER`` env var), the
    scheduler is bypassed and that specific provider is used — preserving
    backward compatibility with existing explicit-provider callers.

    ``skip`` is a list of provider names to skip (e.g. providers that already
    failed with 429 in this turn). This lets the gateway retry with the next
    provider without re-trying the one that failed.
    """
    from ..llm_client import get_llm_client

    skip = set(skip or [])

    # Backward compat: explicit provider bypasses the scheduler.
    forced = force_provider or os.environ.get("NUCLEUS_LLM_PROVIDER")
    if forced and forced not in skip:
        try:
            client = get_llm_client(provider=forced, system_instruction=system_instruction)
            return client, getattr(client, "engine", "REAL"), [
                ProviderAttempt(forced, getattr(client, "engine", "REAL"), client, "")
            ]
        except Exception as exc:
            logger.warning("scheduler: forced provider=%s failed: %s", forced, exc)
            return None, "", [ProviderAttempt(forced, "", None, str(exc))]

    order = _priority_order(capability)
    attempts: List[ProviderAttempt] = []

    for provider in order:
        if provider in skip:
            attempts.append(ProviderAttempt(provider, "", None, "skipped"))
            continue
        if not _provider_available(provider):
            attempts.append(ProviderAttempt(provider, "", None, "no credentials"))
            continue
        try:
            client = get_llm_client(provider=provider, system_instruction=system_instruction)
            engine = getattr(client, "engine", "REAL")
            logger.info("scheduler: selected provider=%s engine=%s cap=%s", provider, engine, capability)
            attempts.append(ProviderAttempt(provider, engine, client, ""))
            return client, engine, attempts
        except Exception as exc:
            logger.debug("scheduler: provider=%s failed: %s", provider, exc)
            attempts.append(ProviderAttempt(provider, "", None, str(exc)))
            continue

    logger.warning("scheduler: no provider available (cap=%s, tried %d)", capability, len(attempts))
    return None, "", attempts


__all__ = [
    "schedule_engine",
    "ProviderAttempt",
    "CAP_CHEAP",
    "CAP_REASONING",
    "CAP_ANY",
]
