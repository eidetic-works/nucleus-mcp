"""Per-action event-emission tests for the `nucleus_governance` facade.

Lane E5 acceptance: ≥15/19 governance actions emit events to
`.brain/ledger/events.jsonl` with emitter='nucleus_governance' (or
emitter='nucleus_delete' for the already-emitting delete_file path).

Strategy: register the facade against a stub MCP, mock the heavy
impl callables so the action path is exercised cheaply, then run the
ROUTER lambda via the registered facade and read the resulting event(s)
from the per-test temp brain.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def gov_brain(tmp_path, monkeypatch):
    """Per-test brain dir scoped to this file; isolates events.jsonl writes."""
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True)
    (brain / "engrams").mkdir(parents=True)
    (brain / "sessions").mkdir(parents=True)
    (brain / "meta").mkdir(parents=True)
    (brain / "ledger" / "events.jsonl").write_text("")
    (brain / "ledger" / "interaction_log.jsonl").write_text("")
    (brain / "engrams" / "ledger.jsonl").write_text("")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Disable trigger evaluation to keep tests fast and isolated
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    return brain


def _read_events(brain: Path) -> list[dict]:
    path = brain / "ledger" / "events.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _emitted_action_keys(brain: Path) -> set[str]:
    """Return the set of governance-action prefixes that appeared in events.

    Maps event.type → action key. Our convention is
    `governance_<action>_<verb>`; we strip the prefix and trailing
    verb to recover the action key. For delete_file we look at emitter
    string instead since it goes through nucleus_delete_file_impl.
    """
    actions: set[str] = set()
    for ev in _read_events(brain):
        et = ev.get("type", "")
        if et.startswith("governance_"):
            # governance_auto_fix_loop_started → auto_fix_loop
            # governance_lock_applied → lock
            # governance_egress_curl → curl
            # governance_egress_pip_install → pip_install
            # governance_mode_changed → set_mode (synthetic mapping)
            actions.add(et)
    return actions


def _build_router(monkeypatch):
    """Register the governance facade against a stub MCP and return its ROUTER.

    Stub MCP captures the registered tool callable but never runs an
    actual server. We don't need the @mcp.tool decorator's side effects.
    """
    captured: dict = {}

    class _StubMCP:
        def tool(self, *a, **kw):
            def _decorator(fn):
                captured["tool"] = fn
                return fn
            return _decorator

    # Helpers param is unused by register(); pass empty
    from mcp_server_nucleus.tools import governance as gov_mod
    # Re-import to ensure a fresh closure each test (defensive)
    handler_list = gov_mod.register(_StubMCP(), helpers=None)
    # register() returns [("nucleus_governance", fn)] — but the
    # ROUTER is a closure inside register(). Easiest way to drive
    # actions is via the tool callable, which calls dispatch(action,
    # params, ROUTER, ...).
    return captured["tool"]


# ──────────────────────────────────────────────────────────────
# Per-action emission tests (each asserts ≥1 event for its action)
# ──────────────────────────────────────────────────────────────


async def test_auto_fix_loop_emits_event(gov_brain, monkeypatch):
    """auto_fix_loop emits a started + completed event."""
    # Patch FixerLoop so we don't actually run subprocesses
    fake_loop = MagicMock()
    fake_loop.run.return_value = {"status": "ok", "retries": 0}

    with patch("mcp_server_nucleus.runtime.loops.fixer.FixerLoop", return_value=fake_loop):
        tool = _build_router(monkeypatch)
        result = await tool("auto_fix_loop", {"file_path": "/tmp/x.py", "verification_command": "pytest"})
    assert isinstance(result, str)

    events = _read_events(gov_brain)
    types = [e.get("type") for e in events]
    assert "governance_auto_fix_loop_started" in types, types
    assert "governance_auto_fix_loop_completed" in types, types


async def test_lock_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.hypervisor_ops.lock_resource_impl",
        return_value='{"ok": true}',
    ):
        tool = _build_router(monkeypatch)
        await tool("lock", {"path": "/tmp/test_file"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_lock_applied" in types, types


async def test_unlock_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.hypervisor_ops.unlock_resource_impl",
        return_value='{"ok": true}',
    ):
        tool = _build_router(monkeypatch)
        await tool("unlock", {"path": "/tmp/test_file"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_unlock_applied" in types, types


async def test_set_mode_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.hypervisor_ops.set_hypervisor_mode_impl",
        return_value='{"mode": "blue"}',
    ):
        tool = _build_router(monkeypatch)
        await tool("set_mode", {"mode": "blue"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_mode_changed" in types, types


async def test_list_directory_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.hypervisor_ops.nucleus_list_directory_impl",
        return_value='{"entries": []}',
    ):
        tool = _build_router(monkeypatch)
        await tool("list_directory", {"path": "/tmp"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_directory_listed" in types, types


async def test_delete_file_emits_event(gov_brain, monkeypatch):
    """delete_file already emits via nucleus_delete_file_impl; preserve regression coverage."""
    def _fake_delete(path, emit_event_fn=None, confirm=False):
        # Invoke the passed event-emit fn so we observe the contract
        if emit_event_fn is not None:
            emit_event_fn(
                event_type="file_deleted",
                emitter="nucleus_delete",
                data={"path": path, "confirm": confirm},
            )
        return '{"deleted": true}'

    with patch(
        "mcp_server_nucleus.runtime.hypervisor_ops.nucleus_delete_file_impl",
        side_effect=_fake_delete,
    ):
        tool = _build_router(monkeypatch)
        await tool("delete_file", {"path": "/tmp/x", "confirm": True})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "file_deleted" in types, types


async def test_watch_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.hypervisor_ops.watch_resource_impl",
        return_value='{"watching": "/tmp"}',
    ):
        tool = _build_router(monkeypatch)
        await tool("watch", {"path": "/tmp"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_watch_registered" in types, types


async def test_curl_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.core.egress_proxy.nucleus_curl_impl",
        return_value='{"status": 200}',
    ):
        tool = _build_router(monkeypatch)
        await tool("curl", {"url": "https://example.com/data", "method": "GET"})
    events = _read_events(gov_brain)
    types = [e.get("type") for e in events]
    assert "governance_egress_curl" in types, types
    # Privacy: full URL path must NOT appear in payload — only scheme://host
    egress = [e for e in events if e.get("type") == "governance_egress_curl"][0]
    assert "/data" not in json.dumps(egress.get("data", {})), egress


async def test_curl_redacts_basic_auth_credentials(gov_brain, monkeypatch):
    """URL-embedded basic-auth (user:pass@host) must be stripped from event payload.

    Regression for PR #350 follow-up: parsed.netloc preserves the user:pass@
    prefix, leaking creds into governance events. Use parsed.hostname instead.
    """
    with patch(
        "mcp_server_nucleus.core.egress_proxy.nucleus_curl_impl",
        return_value='{"status": 200}',
    ):
        tool = _build_router(monkeypatch)
        await tool(
            "curl",
            {"url": "https://user:pass@example.com/path", "method": "GET"},
        )
    events = _read_events(gov_brain)
    egress = [e for e in events if e.get("type") == "governance_egress_curl"]
    assert egress, events
    payload = json.dumps(egress[0])
    # Credentials must NOT appear anywhere in the emitted event
    assert "user:pass" not in payload, egress[0]
    assert "user" not in egress[0].get("data", {}).get("host", ""), egress[0]
    assert "pass" not in egress[0].get("data", {}).get("host", ""), egress[0]
    # Host should be reduced to scheme://hostname (no userinfo, no path)
    assert egress[0]["data"]["host"] == "https://example.com", egress[0]


async def test_pip_install_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.core.egress_proxy.nucleus_pip_install_impl",
        return_value='{"installed": "requests"}',
    ):
        tool = _build_router(monkeypatch)
        await tool("pip_install", {"package": "requests"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_egress_pip_install" in types, types


async def test_validate_strategic_plan_emits_event_on_success(gov_brain, monkeypatch):
    tool = _build_router(monkeypatch)
    await tool("validate_strategic_plan", {"plan_text": "use [BB01] insight", "mode": "strategic"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_strategic_plan_validated" in types, types


async def test_validate_strategic_plan_emits_event_on_rejection(gov_brain, monkeypatch):
    tool = _build_router(monkeypatch)
    await tool("validate_strategic_plan", {"plan_text": "no big bang ref here", "mode": "strategic"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_strategic_plan_rejected" in types, types


async def test_comply_apply_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.compliance_config.apply_jurisdiction",
        return_value={"applied": "us"},
    ):
        tool = _build_router(monkeypatch)
        await tool("comply_apply", {"jurisdiction": "us"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_jurisdiction_applied" in types, types


async def test_comply_report_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.compliance_config.generate_compliance_report",
        return_value={"jurisdiction": "us", "status": "ok"},
    ):
        tool = _build_router(monkeypatch)
        await tool("comply_report", {})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_compliance_report_generated" in types, types


async def test_audit_report_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.audit_report.generate_audit_report",
        return_value={"formatted": "report text", "jurisdiction": "us", "sections": {}},
    ):
        tool = _build_router(monkeypatch)
        await tool("audit_report", {"report_format": "text"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_audit_report_generated" in types, types


async def test_kyc_review_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.kyc_demo.run_kyc_review",
        return_value={"verdict": "approved", "application_id": "APP-001"},
    ):
        tool = _build_router(monkeypatch)
        await tool("kyc_review", {"application_id": "APP-001"})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_kyc_review_completed" in types, types


async def test_sovereign_status_emits_event(gov_brain, monkeypatch):
    with patch(
        "mcp_server_nucleus.runtime.sovereign_status.generate_sovereign_status",
        return_value={"sovereignty_score": 7, "details": {}},
    ), patch(
        "mcp_server_nucleus.runtime.sovereign_status.format_sovereign_status",
        return_value="sovereignty report",
    ):
        tool = _build_router(monkeypatch)
        await tool("sovereign_status", {})
    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_sovereign_status_generated" in types, types


# ──────────────────────────────────────────────────────────────
# Coverage gate: ≥15/19 distinct governance actions emit events
# ──────────────────────────────────────────────────────────────


async def test_coverage_gate_at_least_15_of_19(gov_brain, monkeypatch):
    """Drive each instrumented action once; assert ≥15 distinct emitter coverage."""
    mocks = {
        "mcp_server_nucleus.runtime.loops.fixer.FixerLoop": MagicMock(return_value=MagicMock(run=MagicMock(return_value={"ok": True}))),
        "mcp_server_nucleus.runtime.hypervisor_ops.lock_resource_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.runtime.hypervisor_ops.unlock_resource_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.runtime.hypervisor_ops.set_hypervisor_mode_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.runtime.hypervisor_ops.nucleus_list_directory_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.runtime.hypervisor_ops.watch_resource_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.core.egress_proxy.nucleus_curl_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.core.egress_proxy.nucleus_pip_install_impl": MagicMock(return_value='{}'),
        "mcp_server_nucleus.runtime.compliance_config.apply_jurisdiction": MagicMock(return_value={}),
        "mcp_server_nucleus.runtime.compliance_config.generate_compliance_report": MagicMock(return_value={}),
        "mcp_server_nucleus.runtime.audit_report.generate_audit_report": MagicMock(return_value={"formatted": "x", "sections": {}}),
        "mcp_server_nucleus.runtime.kyc_demo.run_kyc_review": MagicMock(return_value={}),
        "mcp_server_nucleus.runtime.sovereign_status.generate_sovereign_status": MagicMock(return_value={"sovereignty_score": 1}),
        "mcp_server_nucleus.runtime.sovereign_status.format_sovereign_status": MagicMock(return_value="x"),
    }

    # delete_file emits via its own path
    def _fake_delete(path, emit_event_fn=None, confirm=False):
        if emit_event_fn is not None:
            emit_event_fn(event_type="file_deleted", emitter="nucleus_delete", data={"path": path})
        return '{}'

    patches = [patch(target, new=mock) for target, mock in mocks.items()]
    patches.append(
        patch("mcp_server_nucleus.runtime.hypervisor_ops.nucleus_delete_file_impl", side_effect=_fake_delete)
    )

    for p in patches:
        p.start()
    try:
        tool = _build_router(monkeypatch)
        # Drive every state-changing action once
        await tool("auto_fix_loop", {"file_path": "/tmp/x.py", "verification_command": "pytest"})
        await tool("lock", {"path": "/tmp/a"})
        await tool("unlock", {"path": "/tmp/a"})
        await tool("set_mode", {"mode": "red"})
        await tool("list_directory", {"path": "/tmp"})
        await tool("delete_file", {"path": "/tmp/x", "confirm": True})
        await tool("watch", {"path": "/tmp"})
        await tool("curl", {"url": "https://example.com/", "method": "GET"})
        await tool("pip_install", {"package": "requests"})
        await tool("validate_strategic_plan", {"plan_text": "with [BB01]", "mode": "strategic"})
        await tool("comply_apply", {"jurisdiction": "us"})
        await tool("comply_report", {})
        await tool("audit_report", {"report_format": "text"})
        await tool("kyc_review", {"application_id": "APP-001"})
        await tool("sovereign_status", {})
    finally:
        for p in patches:
            p.stop()

    events = _read_events(gov_brain)
    # Map each event back to its canonical governance action
    action_for_type = {
        "governance_auto_fix_loop_started": "auto_fix_loop",
        "governance_auto_fix_loop_completed": "auto_fix_loop",
        "governance_auto_fix_loop_failed": "auto_fix_loop",
        "governance_lock_applied": "lock",
        "governance_unlock_applied": "unlock",
        "governance_mode_changed": "set_mode",
        "governance_directory_listed": "list_directory",
        "file_deleted": "delete_file",
        "governance_watch_registered": "watch",
        "governance_egress_curl": "curl",
        "governance_egress_pip_install": "pip_install",
        "governance_strategic_plan_validated": "validate_strategic_plan",
        "governance_strategic_plan_rejected": "validate_strategic_plan",
        "governance_jurisdiction_applied": "comply_apply",
        "governance_compliance_report_generated": "comply_report",
        "governance_audit_report_generated": "audit_report",
        "governance_kyc_review_completed": "kyc_review",
        "governance_sovereign_status_generated": "sovereign_status",
    }
    actions_emitted = {action_for_type[e["type"]] for e in events if e.get("type") in action_for_type}
    assert len(actions_emitted) >= 15, (
        f"Coverage gate failed: only {len(actions_emitted)} of 19 actions emit events. "
        f"Emitted actions: {sorted(actions_emitted)}"
    )
