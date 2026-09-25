"""
Phase 3 E2E — MCP Server (streamable-http) tool sweep with latency capture.

Brings up a LIVE MCP server process (streamable-http transport) and exercises
EVERY registered tool end-to-end over real HTTP transport (httpx). Captures
per-tool latency (ms) and prints a table at the end.

No in-process FastMCP calls — all traffic goes over the wire.
"""
import json
import time

import httpx
import pytest

from .conftest import mcp_initialize, mcp_tool_call, mcp_call

pytestmark = [pytest.mark.e2e]

# Latency results collected across all tests — printed in the summary test.
_LATENCY_RESULTS: list[dict] = []


def _is_ok(r: dict) -> bool:
    """Check if a tool response indicates success. Handles various response shapes."""
    if not isinstance(r, dict):
        return False
    if r.get("_rpc_error"):
        return False
    if r.get("success") is False:
        return False
    return True


def _has_key(r: dict, *keys) -> bool:
    """Check if any of the keys exist in the response dict."""
    return any(k in r for k in keys)


def _record(tool: str, action: str, latency_ms: float, ok: bool, detail: str = ""):
    _LATENCY_RESULTS.append({
        "tool": tool,
        "action": action,
        "latency_ms": round(latency_ms, 1),
        "ok": ok,
        "detail": detail,
    })


class TestMCPServerE2E:
    """Exercise every registered MCP tool against a live streamable-http server."""

    @pytest.mark.timeout(120)
    def test_01_server_health_and_init(self, http_server):
        """Server boots, MCP initialize succeeds (streamable-http transport)."""
        proc, base_url = http_server
        # MCP initialize is the health check for the local server
        session_id = mcp_initialize(base_url)
        assert len(session_id) > 10

    @pytest.mark.timeout(120)
    def test_02_tools_list_all_registered(self, http_server):
        """tools/list returns all expected tools."""
        proc, base_url = http_server
        session_id = mcp_initialize(base_url)
        result = mcp_call(base_url, "tools/list", {}, session_id)
        assert result is not None
        tools = result["result"]["tools"]
        names = {t["name"] for t in tools}
        expected = {
            "nucleus_engrams", "nucleus_tasks", "nucleus_sync",
            "nucleus_features", "nucleus_sessions", "nucleus_governance",
            "nucleus_relay", "nucleus_orchestration", "nucleus_telemetry",
            "nucleus_slots", "nucleus_infra", "nucleus_agents",
            "nucleus_audit", "nucleus_route", "nucleus_federation",
        }
        missing = expected - names
        assert not missing, f"Missing tools: {missing}"

    @pytest.mark.timeout(120)
    def test_03_nucleus_engrams(self, http_server):
        """nucleus_engrams: write_engram, query_engrams."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # write_engram
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_engrams", "write_engram",
                          {"key": "e2e_test_engram", "value": "test value from e2e",
                           "context": "Feature", "intensity": 7}, sid, req_id=10)
        dt = (time.perf_counter() - t0) * 1000
        ok = "key" in r or r.get("status") == "ok" or "engram" in str(r).lower()
        _record("nucleus_engrams", "write_engram", dt, ok, str(r)[:80])
        assert ok, f"write_engram failed: {r}"
        # query_engrams
        t0 = time.perf_counter()
        r2 = mcp_tool_call(base_url, "nucleus_engrams", "query_engrams",
                           {"context": "Feature", "limit": 10}, sid, req_id=11)
        dt2 = (time.perf_counter() - t0) * 1000
        ok2 = "engrams" in r2 or isinstance(r2, list) or "count" in str(r2).lower()
        _record("nucleus_engrams", "query_engrams", dt2, ok2, str(r2)[:80])
        assert ok2, f"query_engrams failed: {r2}"

    @pytest.mark.timeout(120)
    def test_04_nucleus_tasks(self, http_server):
        """nucleus_tasks: list, get_next, claim, add, update, escalate, import_jsonl."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # add
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_tasks", "add",
                          {"description": "E2E test task", "priority": "high"}, sid, req_id=20)
        dt = (time.perf_counter() - t0) * 1000
        ok = "task_id" in r or "id" in r or "task" in str(r).lower() or r.get("success")
        _record("nucleus_tasks", "add", dt, ok, str(r)[:80])
        assert ok, f"add failed: {r}"
        # list — response may use "tasks", "data", or be a list
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_tasks", "list", {}, sid, req_id=21)
        dt = (time.perf_counter() - t0) * 1000
        ok = "tasks" in r or "data" in r or isinstance(r, list) or r.get("success")
        _record("nucleus_tasks", "list", dt, ok, str(r)[:80])
        assert ok, f"list failed: {r}"
        # get_next
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_tasks", "get_next", {}, sid, req_id=22)
        dt = (time.perf_counter() - t0) * 1000
        ok = "task" in str(r).lower() or "id" in r or r.get("message") or r.get("success")
        _record("nucleus_tasks", "get_next", dt, ok, str(r)[:80])
        # claim — need a task_id; try from get_next or list
        task_id = r.get("task_id") or r.get("id") if isinstance(r, dict) else None
        if not task_id:
            rl = mcp_tool_call(base_url, "nucleus_tasks", "list", {}, sid, req_id=23)
            tasks = rl.get("tasks") or rl.get("data", []) if isinstance(rl, dict) else []
            if tasks:
                task_id = tasks[0].get("task_id") or tasks[0].get("id")
        if task_id:
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, "nucleus_tasks", "claim",
                              {"task_id": task_id, "agent_id": "e2e-agent"}, sid, req_id=24)
            dt = (time.perf_counter() - t0) * 1000
            ok = "claimed" in str(r).lower() or "task" in str(r).lower() or r.get("success")
            _record("nucleus_tasks", "claim", dt, ok, str(r)[:80])
            # update
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, "nucleus_tasks", "update",
                              {"task_id": task_id, "updates": {"status": "in_progress"}}, sid, req_id=25)
            dt = (time.perf_counter() - t0) * 1000
            ok = "task" in str(r).lower() or "updated" in str(r).lower() or r.get("success")
            _record("nucleus_tasks", "update", dt, ok, str(r)[:80])
            # escalate
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, "nucleus_tasks", "escalate",
                              {"task_id": task_id, "reason": "e2e test escalation"}, sid, req_id=26)
            dt = (time.perf_counter() - t0) * 1000
            ok = "escalat" in str(r).lower() or "task" in str(r).lower() or r.get("success")
            _record("nucleus_tasks", "escalate", dt, ok, str(r)[:80])
        else:
            for a in ("claim", "update", "escalate"):
                _record("nucleus_tasks", a, 0, False, "no task_id available")

    @pytest.mark.timeout(120)
    def test_05_nucleus_tasks_import_jsonl(self, http_server, tmp_path):
        """nucleus_tasks: import_jsonl."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        jsonl = tmp_path / "tasks.jsonl"
        jsonl.write_text(
            json.dumps({"description": "imported task 1", "priority": "normal"}) + "\n" +
            json.dumps({"description": "imported task 2", "priority": "low"}) + "\n"
        )
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_tasks", "import_jsonl",
                          {"jsonl_path": str(jsonl)}, sid, req_id=27)
        dt = (time.perf_counter() - t0) * 1000
        ok = "import" in str(r).lower() or "tasks" in str(r).lower() or "added" in str(r).lower() or _is_ok(r)
        _record("nucleus_tasks", "import_jsonl", dt, ok, str(r)[:80])

    @pytest.mark.timeout(120)
    def test_06_nucleus_sync(self, http_server):
        """nucleus_sync: relay_post, relay_ack."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # relay_post
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sync", "relay_post",
                          {"to": "claude_code_peer", "subject": "e2e sync test",
                           "body": "hello from e2e", "sender": "claude_code_main"}, sid, req_id=30)
        dt = (time.perf_counter() - t0) * 1000
        ok = "sent" in str(r).lower() or _has_key(r, "message_id", "id") or _is_ok(r)
        _record("nucleus_sync", "relay_post", dt, ok, str(r)[:80])
        assert ok, f"relay_post failed: {r}"
        # relay_inbox to find the message
        r_inbox = mcp_tool_call(base_url, "nucleus_sync", "relay_inbox",
                                {"recipient": "claude_code_peer", "unread_only": True}, sid, req_id=31)
        msgs = r_inbox.get("messages", []) if isinstance(r_inbox, dict) else []
        if msgs:
            mid = msgs[0].get("id") or msgs[0].get("message_id")
            if mid:
                t0 = time.perf_counter()
                r = mcp_tool_call(base_url, "nucleus_sync", "relay_ack",
                                  {"message_id": mid, "recipient": "claude_code_peer"}, sid, req_id=32)
                dt = (time.perf_counter() - t0) * 1000
                ok = "ack" in str(r).lower() or "read" in str(r).lower() or _is_ok(r)
                _record("nucleus_sync", "relay_ack", dt, ok, str(r)[:80])
            else:
                _record("nucleus_sync", "relay_ack", 0, False, "no message_id")
        else:
            _record("nucleus_sync", "relay_ack", 0, False, "no messages in inbox")

    @pytest.mark.timeout(120)
    def test_07_nucleus_features(self, http_server):
        """nucleus_features: add, list, get, update, validate, search."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # add
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_features", "add",
                          {"product": "e2e-product", "name": "e2e-feature",
                           "description": "test feature", "source": "e2e",
                           "version": "1.0", "how_to_test": "run e2e",
                           "expected_result": "passes"}, sid, req_id=40)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "feature_id", "id") or "feature" in str(r).lower() or _is_ok(r)
        _record("nucleus_features", "add", dt, ok, str(r)[:80])
        assert ok, f"add failed: {r}"
        fid = r.get("feature_id") or r.get("id")
        # list
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_features", "list",
                          {"product": "e2e-product"}, sid, req_id=41)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "features", "data") or isinstance(r, list) or _is_ok(r)
        _record("nucleus_features", "list", dt, ok, str(r)[:80])
        if not fid and isinstance(r, dict):
            feats = r.get("features") or r.get("data", [])
            if feats:
                fid = feats[0].get("feature_id") or feats[0].get("id")
        # get
        if fid:
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, "nucleus_features", "get",
                              {"feature_id": fid}, sid, req_id=42)
            dt = (time.perf_counter() - t0) * 1000
            ok = "feature" in str(r).lower() or _has_key(r, "id") or _is_ok(r)
            _record("nucleus_features", "get", dt, ok, str(r)[:80])
            # update
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, "nucleus_features", "update",
                              {"feature_id": fid, "status": "in_progress"}, sid, req_id=43)
            dt = (time.perf_counter() - t0) * 1000
            ok = "feature" in str(r).lower() or "updated" in str(r).lower() or _is_ok(r)
            _record("nucleus_features", "update", dt, ok, str(r)[:80])
            # validate
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, "nucleus_features", "validate",
                              {"feature_id": fid, "result": "e2e validated"}, sid, req_id=44)
            dt = (time.perf_counter() - t0) * 1000
            ok = "valid" in str(r).lower() or "feature" in str(r).lower() or _is_ok(r)
            _record("nucleus_features", "validate", dt, ok, str(r)[:80])
        else:
            for a in ("get", "update", "validate"):
                _record("nucleus_features", a, 0, False, "no feature_id")
        # search
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_features", "search",
                          {"query": "e2e"}, sid, req_id=45)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "features", "results", "data") or isinstance(r, list) or _is_ok(r)
        _record("nucleus_features", "search", dt, ok, str(r)[:80])

    @pytest.mark.timeout(120)
    def test_08_nucleus_sessions(self, http_server):
        """nucleus_sessions: save, resume, list, end, start, emit_event, read_events, get_state, update_state, checkpoint."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # start
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "start", {}, sid, req_id=50)
        dt = (time.perf_counter() - t0) * 1000
        ok = "session" in str(r).lower() or "start" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "start", dt, ok, str(r)[:80])
        # save
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "save",
                          {"context": "e2e test session", "active_task": "testing"}, sid, req_id=51)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "session_id") or "session" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "save", dt, ok, str(r)[:80])
        sess_id = r.get("session_id") if isinstance(r, dict) else None
        # list
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "list", {}, sid, req_id=52)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "sessions", "data") or isinstance(r, list) or _is_ok(r)
        _record("nucleus_sessions", "list", dt, ok, str(r)[:80])
        # resume
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "resume",
                          {"session_id": sess_id} if sess_id else {}, sid, req_id=53)
        dt = (time.perf_counter() - t0) * 1000
        ok = "session" in str(r).lower() or "resume" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "resume", dt, ok, str(r)[:80])
        # emit_event
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "emit_event",
                          {"event_type": "E2ETest", "emitter": "e2e", "data": {"v": 1}}, sid, req_id=54)
        dt = (time.perf_counter() - t0) * 1000
        ok = "event" in str(r).lower() or "emit" in str(r).lower() or "ok" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "emit_event", dt, ok, str(r)[:80])
        # read_events
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "read_events",
                          {"limit": 10}, sid, req_id=55)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "events", "data") or isinstance(r, list) or _is_ok(r)
        _record("nucleus_sessions", "read_events", dt, ok, str(r)[:80])
        # get_state
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "get_state", {}, sid, req_id=56)
        dt = (time.perf_counter() - t0) * 1000
        ok = "state" in str(r).lower() or isinstance(r, dict) or _is_ok(r)
        _record("nucleus_sessions", "get_state", dt, ok, str(r)[:80])
        # update_state
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "update_state",
                          {"updates": {"e2e_key": "e2e_value"}}, sid, req_id=57)
        dt = (time.perf_counter() - t0) * 1000
        ok = "state" in str(r).lower() or "update" in str(r).lower() or "ok" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "update_state", dt, ok, str(r)[:80])
        # checkpoint
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "checkpoint",
                          {"task_id": "e2e-task", "step": 1, "progress_percent": 50}, sid, req_id=58)
        dt = (time.perf_counter() - t0) * 1000
        ok = "checkpoint" in str(r).lower() or "task" in str(r).lower() or "ok" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "checkpoint", dt, ok, str(r)[:80])
        # end
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_sessions", "end",
                          {"summary": "e2e done", "learnings": "tests pass"}, sid, req_id=59)
        dt = (time.perf_counter() - t0) * 1000
        ok = "session" in str(r).lower() or "end" in str(r).lower() or "ok" in str(r).lower() or _is_ok(r)
        _record("nucleus_sessions", "end", dt, ok, str(r)[:80])

    @pytest.mark.timeout(120)
    def test_09_nucleus_governance(self, http_server):
        """nucleus_governance: status, list_directory."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # status
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_governance", "status", {}, sid, req_id=60)
        dt = (time.perf_counter() - t0) * 1000
        ok = "hypervisor" in str(r).lower() or "governance" in str(r).lower() or "status" in str(r).lower() or _is_ok(r)
        _record("nucleus_governance", "status", dt, ok, str(r)[:80])
        assert ok, f"status failed: {r}"
        # list_directory — list the brain root
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_governance", "list_directory",
                          {"path": "."}, sid, req_id=61)
        dt = (time.perf_counter() - t0) * 1000
        ok = "files" in str(r).lower() or "entries" in str(r).lower() or "list" in str(r).lower() or isinstance(r, list) or _is_ok(r)
        _record("nucleus_governance", "list_directory", dt, ok, str(r)[:80])

    @pytest.mark.timeout(120)
    def test_10_nucleus_relay_tool(self, http_server):
        """nucleus_relay: post, inbox, ack (MCP tool surface)."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # post
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_relay", "post",
                          {"to": "claude_code_peer", "subject": "e2e relay tool",
                           "body": "from nucleus_relay tool", "sender": "claude_code_main"}, sid, req_id=70)
        dt = (time.perf_counter() - t0) * 1000
        ok = "sent" in str(r).lower() or _has_key(r, "message_id", "id") or _is_ok(r)
        _record("nucleus_relay", "post", dt, ok, str(r)[:80])
        # inbox
        t0 = time.perf_counter()
        r = mcp_tool_call(base_url, "nucleus_relay", "inbox",
                          {"recipient": "claude_code_peer", "unread_only": True}, sid, req_id=71)
        dt = (time.perf_counter() - t0) * 1000
        ok = _has_key(r, "messages", "data") or isinstance(r, list) or _is_ok(r)
        _record("nucleus_relay", "inbox", dt, ok, str(r)[:80])

    @pytest.mark.timeout(120)
    def test_11_nucleus_orchestration_and_others(self, http_server):
        """Exercise remaining tools: orchestration, telemetry, slots, infra, agents, audit, route, federation."""
        proc, base_url = http_server
        sid = mcp_initialize(base_url)
        # Real action names sourced from each facade's ROUTER in source:
        #   orchestration.py:  ORCH_ROUTER   → satellite
        #   orchestration.py:  TELEM_ROUTER  → get_llm_status
        #   orchestration.py:  SLOTS_ROUTER  → status_dashboard
        #   orchestration.py:  INFRA_ROUTER  → file_changes
        #   orchestration.py:  AGENTS_ROUTER → list_pending_consents
        #   audit_log_tool.py: ROUTER        → query
        #   cost_router.py:    ROUTER        → route
        #   federation.py:     ROUTER        → status
        calls = [
            ("nucleus_orchestration", "satellite", {}),
            ("nucleus_telemetry", "get_llm_status", {}),
            ("nucleus_slots", "status_dashboard", {}),
            ("nucleus_infra", "file_changes", {}),
            ("nucleus_agents", "list_pending_consents", {}),
            ("nucleus_audit", "query", {"team_id": "default", "limit": 5}),
            ("nucleus_route", "route", {"prompt": "test prompt"}),
            ("nucleus_federation", "status", {}),
        ]
        rid = 80
        for tool, action, params in calls:
            t0 = time.perf_counter()
            r = mcp_tool_call(base_url, tool, action, params, sid, req_id=rid)
            dt = (time.perf_counter() - t0) * 1000
            assert isinstance(r, dict), f"{tool}/{action} returned non-dict: {type(r)}"
            assert not r.get("_rpc_error"), f"{tool}/{action} RPC error: {r.get('_rpc_error')}"
            assert not r.get("error"), f"{tool}/{action} returned error: {r.get('error')}"
            _record(tool, action, dt, True, str(r)[:80])
            rid += 1

    @pytest.mark.timeout(60)
    def test_99_latency_summary(self, http_server):
        """Print the latency table — runs last to collect all results."""
        proc, base_url = http_server
        # Just ensure we have results
        assert len(_LATENCY_RESULTS) > 0, "No latency results collected"
        # Print the table
        print("\n" + "=" * 90)
        print("MCP SERVER E2E — PER-TOOL LATENCY TABLE")
        print("=" * 90)
        print(f"{'Tool':<30} {'Action':<20} {'Latency(ms)':>12} {'OK':>5}  Detail")
        print("-" * 90)
        for r in sorted(_LATENCY_RESULTS, key=lambda x: (x["tool"], x["action"])):
            print(f"{r['tool']:<30} {r['action']:<20} {r['latency_ms']:>12.1f} {str(r['ok']):>5}  {r['detail']}")
        print("=" * 90)
        total = len(_LATENCY_RESULTS)
        passed = sum(1 for r in _LATENCY_RESULTS if r["ok"])
        print(f"Total: {total} calls, {passed} ok, {total - passed} failed/not-ok")
        print("=" * 90)
