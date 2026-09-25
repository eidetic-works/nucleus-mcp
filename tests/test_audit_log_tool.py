"""Tool-layer tests for nucleus_audit (closes cc-peer C1 on PR #595).

Verifies:
  - query rejects team_id='*' (no implicit cross-tenant read)
  - admin_query without NUCLEUS_AUDIT_ADMIN_TOKEN env -> reject
  - admin_query with wrong token -> reject
  - admin_query with correct token -> success + dogfood log to '__admin__'
  - log_event + verify still work
"""

import asyncio
import json
import os

import pytest

from mcp_server_nucleus.runtime import audit_log as runtime_audit
from mcp_server_nucleus.tools import audit_log_tool


class _StubMcp:
    def __init__(self):
        self.registered = {}

    def tool(self, **kwargs):
        def decorator(fn):
            self.registered[fn.__name__] = fn
            return fn
        return decorator


def _make_response(ok, data=None, error=None):
    return json.dumps({"success": ok, "data": data, "error": error})


@pytest.fixture
def tool_fn(tmp_path, monkeypatch):
    import threading
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    # Reset thread-local conn + init guards so each test gets a clean DB
    runtime_audit._local = threading.local()
    runtime_audit._DB_INITIALIZED.clear()
    runtime_audit._team_locks.clear()
    mcp = _StubMcp()
    helpers = {"make_response": _make_response}
    audit_log_tool.register(mcp, helpers)
    return mcp.registered["nucleus_audit"]


async def _seed(tool_fn, team_id, n=2):
    for i in range(n):
        out = await tool_fn("log_event", {
            "event_type": "tool_call",
            "actor": f"agent-{i}",
            "resource": "nucleus_tasks/claim",
            "outcome": "success",
            "team_id": team_id,
        })
        assert json.loads(out)["success"], out


async def test_query_rejects_wildcard(tool_fn):
    await _seed(tool_fn, "team-a")
    await _seed(tool_fn, "team-b")
    out = json.loads(await tool_fn("query", {"team_id": "*"}))
    assert out["success"] is False
    assert "admin_query" in out["error"]


async def test_query_single_tenant_works(tool_fn):
    await _seed(tool_fn, "team-a", n=3)
    await _seed(tool_fn, "team-b", n=2)
    out = json.loads(await tool_fn("query", {"team_id": "team-a"}))
    assert out["success"] is True
    assert out["data"]["count"] == 3
    assert all(r["team_id"] == "team-a" for r in out["data"]["records"])


async def test_admin_query_no_env_rejects(tool_fn, monkeypatch):
    monkeypatch.delenv("NUCLEUS_AUDIT_ADMIN_TOKEN", raising=False)
    await _seed(tool_fn, "team-a")
    out = json.loads(await tool_fn("admin_query", {"admin_token": "anything", "team_id": "*"}))
    assert out["success"] is False
    assert "admin_token" in out["error"]


async def test_admin_query_empty_env_rejects(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_AUDIT_ADMIN_TOKEN", "")
    await _seed(tool_fn, "team-a")
    out = json.loads(await tool_fn("admin_query", {"admin_token": "", "team_id": "*"}))
    assert out["success"] is False


async def test_admin_query_wrong_token_rejects(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_AUDIT_ADMIN_TOKEN", "correct-secret")
    await _seed(tool_fn, "team-a")
    out = json.loads(await tool_fn("admin_query", {"admin_token": "wrong-secret", "team_id": "*"}))
    assert out["success"] is False
    assert "admin_token" in out["error"]


async def test_admin_query_correct_token_allows_cross_tenant(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_AUDIT_ADMIN_TOKEN", "correct-secret")
    await _seed(tool_fn, "team-a", n=2)
    await _seed(tool_fn, "team-b", n=3)
    out = json.loads(await tool_fn("admin_query", {"admin_token": "correct-secret", "team_id": "*"}))
    assert out["success"] is True
    seen = {r["team_id"] for r in out["data"]["records"] if r["team_id"] != "__admin__"}
    assert seen == {"team-a", "team-b"}


async def test_admin_query_logs_dogfood_to_admin_chain(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_AUDIT_ADMIN_TOKEN", "correct-secret")
    await _seed(tool_fn, "team-a", n=1)
    out = json.loads(await tool_fn("admin_query", {"admin_token": "correct-secret", "team_id": "*"}))
    assert out["success"] is True
    admin_chain = json.loads(await tool_fn("query", {"team_id": "__admin__"}))
    assert admin_chain["success"] is True
    assert admin_chain["data"]["count"] >= 1
    rec = admin_chain["data"]["records"][-1]
    assert rec["event_type"] == "admin_query"
    assert rec["actor"] == "admin"
    assert rec["outcome"] == "success"


async def test_unknown_action_lists_admin_query(tool_fn):
    out = json.loads(await tool_fn("nope", {}))
    assert "error" in out
    assert "admin_query" in out.get("available_actions", []) or "admin_query" in out["error"]


async def test_verify_still_works(tool_fn):
    await _seed(tool_fn, "team-a", n=3)
    out = json.loads(await tool_fn("verify", {"team_id": "team-a"}))
    assert out["success"] is True
    assert out["data"]["chain_ok"] is True
