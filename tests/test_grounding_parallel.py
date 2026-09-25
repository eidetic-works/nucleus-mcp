"""Regression test: search_brain calls in nucleus_ground must run concurrently.

The grounding tool issues 3-4 search_brain calls (session, plan, codebase,
conversation). Before the parallelization fix these ran sequentially, stacking
wall-clock time (~16s measured). After the fix they run concurrently via
asyncio.to_thread + asyncio.gather, so latency is dominated by the slowest
call (~5-6s).

This test installs a fake search_brain that sleeps a fixed delay per call and
records its start timestamp. If the calls are concurrent, all start within a
small window and total latency is ~1x delay; if sequential, starts are spaced
delay apart and total latency is ~N*delay.
"""

import sys
import time
import types
from pathlib import Path

import pytest

from mcp_server_nucleus.tools.grounding import register


# ---------------------------------------------------------------------------
# Helpers / fixtures (mirrors test_grounding_recent_commits.py patterns)
# ---------------------------------------------------------------------------

class _FakeMCP:
    """Minimal MCP stand-in: `.tool()` returns an identity decorator."""

    def tool(self, *args, **kwargs):
        def deco(fn):
            return fn
        return deco


def _install_timed_providers(monkeypatch, brain_path, delay, call_log):
    """Inject a stub providers.brain_rag whose search_brain sleeps `delay`
    seconds, records its monotonic start time in `call_log`, and returns a
    non-empty result list so every section gets populated."""
    def fake_search_brain(*a, **k):
        call_log.append(time.monotonic())
        time.sleep(delay)
        return [{
            "source": "fake.md",
            "content": "x" * 200,
            "time_band": "recent",
            "agent_role": k.get("agent_role") or "test",
            "session_id": k.get("session_id", ""),
            "repo_id": "fake-repo",
        }]

    fake_providers = types.ModuleType("providers")
    fake_brain_rag = types.ModuleType("providers.brain_rag")
    fake_brain_rag.OLLAMA_URL = ""
    fake_brain_rag.BRAIN_PATH = brain_path
    fake_brain_rag._read_brain_owner = lambda bp: "test-project"
    fake_brain_rag.search_brain = fake_search_brain
    fake_providers.brain_rag = fake_brain_rag
    monkeypatch.setitem(sys.modules, "providers", fake_providers)
    monkeypatch.setitem(sys.modules, "providers.brain_rag", fake_brain_rag)


def _build_nucleus_ground(brain_path):
    helpers = {
        "make_response": lambda ok, data=None, error=None: {
            "ok": ok, "data": data, "error": error,
        },
        "get_brain_path": lambda: str(brain_path),
    }
    tools = register(_FakeMCP(), helpers)
    assert tools and isinstance(tools[0], tuple)
    _name, func = tools[0]
    assert _name == "nucleus_ground"
    return func


# ---------------------------------------------------------------------------
# Test: 3 calls (plan, codebase, conversation) run concurrently
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_brain_calls_run_concurrently(tmp_path, monkeypatch):
    """With task_context set and no session_id, nucleus_ground issues 3
    search_brain calls (plan, codebase, conversation). Each fake call sleeps
    0.3s. Sequential would take ~0.9s; concurrent should take ~0.3s."""
    brain_path = tmp_path / ".brain"
    brain_path.mkdir()
    delay = 0.3
    call_log: list[float] = []
    _install_timed_providers(monkeypatch, brain_path, delay, call_log)
    nucleus_ground = _build_nucleus_ground(brain_path)

    result = await nucleus_ground(
        task_context="test query for grounding",
        session_id="",
        include_plan=True,
        include_codebase=True,
        include_recent_commits=False,
    )

    assert result["ok"] is True, f"grounding failed: {result.get('error')}"
    assert len(call_log) == 3, (
        f"expected 3 search_brain calls (plan+codebase+conversation), "
        f"got {len(call_log)}"
    )

    # All 3 calls should start near-simultaneously (concurrent), not spaced
    # `delay` seconds apart (sequential).
    starts_relative = [t - call_log[0] for t in call_log]
    max_start_spread = max(starts_relative)
    assert max_start_spread < delay * 0.5, (
        f"search_brain calls appear sequential: max start spread "
        f"{max_start_spread:.3f}s >= half of per-call delay {delay}s. "
        f"Starts (relative): {starts_relative}"
    )

    # Total wall-clock latency should be well under 3 * delay (sequential),
    # close to a single delay (concurrent).
    latency = result["data"]["latency_s"]
    assert latency < delay * 2, (
        f"latency {latency:.2f}s >= 2x per-call delay {delay}s, "
        "suggesting sequential execution"
    )

    # All 3 sections should be populated with the fake results.
    sections = result["data"]["sections"]
    assert "plan_context" in sections
    assert "codebase_context" in sections
    assert "conversation_context" in sections


# ---------------------------------------------------------------------------
# Test: 4 calls (session + plan + codebase + conversation) run concurrently
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_four_search_brain_calls_run_concurrently(tmp_path, monkeypatch):
    """With session_id + task_context, nucleus_ground issues 4 search_brain
    calls. Each fake call sleeps 0.3s. Sequential would take ~1.2s; concurrent
    should take ~0.3s."""
    brain_path = tmp_path / ".brain"
    brain_path.mkdir()
    delay = 0.3
    call_log: list[float] = []
    _install_timed_providers(monkeypatch, brain_path, delay, call_log)
    nucleus_ground = _build_nucleus_ground(brain_path)

    result = await nucleus_ground(
        task_context="test query for grounding",
        session_id="sess-123",
        include_plan=True,
        include_codebase=True,
        include_recent_commits=False,
    )

    assert result["ok"] is True, f"grounding failed: {result.get('error')}"
    assert len(call_log) == 4, (
        f"expected 4 search_brain calls (session+plan+codebase+conversation), "
        f"got {len(call_log)}"
    )

    starts_relative = [t - call_log[0] for t in call_log]
    max_start_spread = max(starts_relative)
    assert max_start_spread < delay * 0.5, (
        f"search_brain calls appear sequential: max start spread "
        f"{max_start_spread:.3f}s >= half of per-call delay {delay}s. "
        f"Starts (relative): {starts_relative}"
    )

    latency = result["data"]["latency_s"]
    assert latency < delay * 2, (
        f"latency {latency:.2f}s >= 2x per-call delay {delay}s, "
        "suggesting sequential execution"
    )


# ---------------------------------------------------------------------------
# Test: sections still populated correctly (output shape unchanged)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_results_shape_unchanged(tmp_path, monkeypatch):
    """The output brief must have the same section structure as before
    parallelization — concurrent execution is an implementation detail, not
    a contract change."""
    brain_path = tmp_path / ".brain"
    brain_path.mkdir()
    delay = 0.01
    call_log: list[float] = []
    _install_timed_providers(monkeypatch, brain_path, delay, call_log)
    nucleus_ground = _build_nucleus_ground(brain_path)

    result = await nucleus_ground(
        task_context="test query",
        session_id="sess-456",
        include_plan=True,
        include_codebase=True,
        include_recent_commits=False,
    )

    assert result["ok"] is True
    data = result["data"]
    assert "latency_s" in data
    assert "timestamp" in data
    assert "session_id" in data and data["session_id"] == "sess-456"
    assert "task_context" in data and data["task_context"] == "test query"
    assert "sections" in data

    sections = data["sections"]
    # session_context: fake returns session_id="sess-456", so it passes the
    # session_id filter and gets populated.
    assert "session_context" in sections
    assert sections["session_context"]["chunks"] >= 1
    item = sections["session_context"]["items"][0]
    assert "source" in item and "content" in item and "age" in item
    assert "agent_role" in item

    assert "plan_context" in sections
    assert sections["plan_context"]["chunks"] >= 1

    assert "codebase_context" in sections
    assert sections["codebase_context"]["chunks"] >= 1

    assert "conversation_context" in sections
    conv_item = sections["conversation_context"]["items"][0]
    assert "repo_id" in conv_item
