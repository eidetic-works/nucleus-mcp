"""Agent-OS cognition scheduler — fall-through behavior tests.

Proves the scheduler (MEMBRANE §1) correctly:
  1. Falls through to the next provider when one fails
  2. Respects the skip list (providers that already failed)
  3. Respects capability hints (cheap vs reasoning vs any)
  4. Falls back to forced provider when NUCLEUS_LLM_PROVIDER is set
  5. Returns None with attempts log when no provider is available

Uses monkeypatching to simulate provider availability/failure without
needing real credentials.
"""
from __future__ import annotations

import os

import pytest

from mcp_server_nucleus.runtime.agent_os import scheduler as sched


def test_priority_order_any():
    """CAP_ANY uses the default cheapest-first order."""
    order = sched._priority_order(sched.CAP_ANY)
    assert order[0] == "antigravity"
    assert "groq" in order
    assert "anthropic" in order
    assert len(order) == 5


def test_priority_order_cheap():
    """CAP_CHEAP prefers Groq first (fastest free)."""
    order = sched._priority_order(sched.CAP_CHEAP)
    assert order[0] == "groq"


def test_priority_order_reasoning():
    """CAP_REASONING prefers Claude (frontier) first."""
    order = sched._priority_order(sched.CAP_REASONING)
    assert order[0] == "claude_oauth"


def test_provider_available_groq_with_key(monkeypatch):
    """Groq is available when NUCLEUS_GROQ_API_KEY is set."""
    monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "test-key")
    assert sched._provider_available("groq") is True


def test_provider_available_groq_without_key(monkeypatch):
    """Groq is unavailable when NUCLEUS_GROQ_API_KEY is not set."""
    monkeypatch.delenv("NUCLEUS_GROQ_API_KEY", raising=False)
    assert sched._provider_available("groq") is False


def test_schedule_engine_falls_through_on_failure(monkeypatch):
    """When the first provider fails, the scheduler falls through to the next."""
    # Make only Groq available
    monkeypatch.delenv("NUCLEUS_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "test-key")

    # Mock _provider_available: only groq
    monkeypatch.setattr(sched, "_provider_available", lambda p: p == "groq")

    # Mock get_llm_client to succeed for groq
    class MockClient:
        engine = "GROQ"
        def generate_content(self, prompt):
            return type("Resp", (), {"text": "test response"})()

    def mock_get_llm_client(provider, system_instruction=None):
        if provider == "groq":
            return MockClient()
        raise Exception(f"provider {provider} not available")

    monkeypatch.setattr("mcp_server_nucleus.runtime.agent_os.scheduler.get_llm_client", mock_get_llm_client, raising=False)
    # Also patch where it's imported inside schedule_engine
    import mcp_server_nucleus.runtime.llm_client as llm_client_mod
    monkeypatch.setattr(llm_client_mod, "get_llm_client", mock_get_llm_client)

    client, engine, attempts = sched.schedule_engine(sched.CAP_ANY)

    assert client is not None
    assert engine == "GROQ"
    # The scheduler should have tried antigravity (no creds) then groq (success)
    tried_providers = [a.provider for a in attempts]
    assert "groq" in tried_providers
    # The successful attempt should be the last one
    assert attempts[-1].provider == "groq"
    assert attempts[-1].error == ""


def test_schedule_engine_respects_skip(monkeypatch):
    """The skip list prevents re-trying a provider that already failed."""
    monkeypatch.delenv("NUCLEUS_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "test-key")

    # Mock: groq and gemini available
    monkeypatch.setattr(sched, "_provider_available", lambda p: p in ("groq", "gemini"))

    call_log = []
    class MockClient:
        def __init__(self, engine):
            self.engine = engine
        def generate_content(self, prompt):
            return type("Resp", (), {"text": "test"})()

    def mock_get_llm_client(provider, system_instruction=None):
        call_log.append(provider)
        if provider == "groq":
            raise Exception("429 rate limited")
        if provider == "gemini":
            return MockClient("GEMINI")
        raise Exception(f"unknown {provider}")

    import mcp_server_nucleus.runtime.llm_client as llm_client_mod
    monkeypatch.setattr(llm_client_mod, "get_llm_client", mock_get_llm_client)

    # Skip groq (already failed) → should go straight to gemini
    client, engine, attempts = sched.schedule_engine(
        sched.CAP_CHEAP, skip=["groq"]
    )

    assert client is not None
    assert engine == "GEMINI"
    assert "groq" not in call_log  # groq was skipped, never constructed


def test_schedule_engine_no_provider_available(monkeypatch):
    """When no provider has credentials, returns None with attempts log."""
    monkeypatch.delenv("NUCLEUS_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(sched, "_provider_available", lambda p: False)

    client, engine, attempts = sched.schedule_engine(sched.CAP_ANY)

    assert client is None
    assert engine == ""
    assert len(attempts) == 5  # all 5 providers tried, all "no credentials"
    for a in attempts:
        assert a.error == "no credentials"


def test_schedule_engine_forced_provider_bypasses(monkeypatch):
    """NUCLEUS_LLM_PROVIDER env var bypasses the scheduler."""
    monkeypatch.setenv("NUCLEUS_LLM_PROVIDER", "groq")
    monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "test-key")

    class MockClient:
        engine = "GROQ"
        def generate_content(self, prompt):
            return type("Resp", (), {"text": "test"})()

    def mock_get_llm_client(provider, system_instruction=None):
        if provider == "groq":
            return MockClient()
        raise Exception(f"unexpected {provider}")

    import mcp_server_nucleus.runtime.llm_client as llm_client_mod
    monkeypatch.setattr(llm_client_mod, "get_llm_client", mock_get_llm_client)

    client, engine, attempts = sched.schedule_engine(sched.CAP_ANY)

    assert client is not None
    assert engine == "GROQ"
    assert len(attempts) == 1  # only the forced provider
    assert attempts[0].provider == "groq"


# ─── capability-hint routing with all providers MOCK-available ──────────────
# These prove schedule_engine actually routes to the first-priority provider
# for each capability hint when every provider is constructible — not just that
# _priority_order returns the right list (covered above). Same mock seams as the
# fall-through test: _provider_available → True for all; get_llm_client returns a
# distinct MockClient per provider so we can tell which one was selected.

_ENGINE_BY_PROVIDER = {
    "antigravity": "ANTIGRAVITY",
    "groq": "GROQ",
    "gemini": "GEMINI",
    "claude_oauth": "CLAUDE_OAUTH",
    "anthropic": "ANTHROPIC",
}


def _mock_all_available(monkeypatch):
    """Make every provider available + constructible; record construction order."""
    monkeypatch.delenv("NUCLEUS_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(sched, "_provider_available", lambda p: True)

    constructed = []

    class MockClient:
        def __init__(self, engine):
            self.engine = engine

        def generate_content(self, prompt):
            return type("Resp", (), {"text": "ok"})()

    def mock_get_llm_client(provider, system_instruction=None):
        constructed.append(provider)
        return MockClient(_ENGINE_BY_PROVIDER[provider])

    import mcp_server_nucleus.runtime.llm_client as llm_client_mod
    monkeypatch.setattr(llm_client_mod, "get_llm_client", mock_get_llm_client)
    return constructed


def test_capability_hint_cheap_routes_to_groq_first(monkeypatch):
    """CAP_CHEAP selects Groq first when all providers are available."""
    constructed = _mock_all_available(monkeypatch)

    client, engine, attempts = sched.schedule_engine(sched.CAP_CHEAP)

    assert client is not None
    assert engine == "GROQ"
    assert attempts[0].provider == "groq"
    assert attempts[0].error == ""
    # Only the first provider is constructed — scheduler returns immediately on success.
    assert constructed == ["groq"]


def test_capability_hint_reasoning_routes_to_claude_first(monkeypatch):
    """CAP_REASONING selects Claude (claude_oauth) first when all providers are available."""
    constructed = _mock_all_available(monkeypatch)

    client, engine, attempts = sched.schedule_engine(sched.CAP_REASONING)

    assert client is not None
    assert engine == "CLAUDE_OAUTH"
    assert attempts[0].provider == "claude_oauth"
    assert attempts[0].error == ""
    assert constructed == ["claude_oauth"]


def test_capability_hint_any_routes_to_antigravity_first(monkeypatch):
    """CAP_ANY selects Antigravity first (default cheapest-first order)."""
    constructed = _mock_all_available(monkeypatch)

    client, engine, attempts = sched.schedule_engine(sched.CAP_ANY)

    assert client is not None
    assert engine == "ANTIGRAVITY"
    assert attempts[0].provider == "antigravity"
    assert attempts[0].error == ""
    assert constructed == ["antigravity"]
