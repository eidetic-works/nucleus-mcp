"""A12 (gates-governance) — registry-anchored governance validation.

AUDIT_FINDINGS.md row #9 / HANDOFF_BACKLOG.md §A row A12: `validate_strategic_plan`
was a bare regex match of `[BB##]` tags over the submitter's own text (a
`[BB99]` reference passed even with no registered insight behind it), and
`audit_report`'s "sovereignty verified" checklist item was a hardcoded pass.

Flag `NUCLEUS_GOVERNANCE_ANCHOR` (default OFF) gates the fix:
  - OFF: legacy regex-only behavior, byte-identical to pre-change output.
  - ON:  `[BB##]` tags must map to a real entry in the committed Big Bang
         registry artifact (docs/reports/nucleus_bigbang_30d.md — the exact
         file the protocol's own error message already names); the
         "sovereignty verified" checklist item reflects real event-log state
         instead of a hardcoded pass.

DEVIATION (see final report to caller): no real BB registry (file/DB/module)
exists anywhere in this repo today — grep-verified. Rather than inventing one,
the anchor check opens the committed artifact the protocol error message
already points at. Until that file is created and populated, every [BB##]
reference is "unregistered" when the flag is ON — this is the honest,
non-fabricated behavior, not a bug in this test suite.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ──────────────────────────────────────────────────────────────
# validate_strategic_plan — helpers
# ──────────────────────────────────────────────────────────────


def _build_router():
    """Register the governance facade against a stub MCP and return its tool callable."""
    captured: dict = {}

    class _StubMCP:
        def tool(self, *a, **kw):
            def _decorator(fn):
                captured["tool"] = fn
                return fn
            return _decorator

    from mcp_server_nucleus.tools import governance as gov_mod
    gov_mod.register(_StubMCP(), helpers=None)
    return captured["tool"]


@pytest.fixture
def gov_brain(tmp_path, monkeypatch):
    """Per-test brain dir; isolates events.jsonl writes and NUCLEUS_PROJECT_ROOT."""
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True)
    (brain / "engrams").mkdir(parents=True)
    (brain / "sessions").mkdir(parents=True)
    (brain / "meta").mkdir(parents=True)
    (brain / "ledger" / "events.jsonl").write_text("")
    (brain / "ledger" / "interaction_log.jsonl").write_text("")
    (brain / "engrams" / "ledger.jsonl").write_text("")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    # Point the registry-root resolution at an empty scratch dir by default —
    # no docs/reports/nucleus_bigbang_30d.md present unless a test writes one.
    monkeypatch.setenv("NUCLEUS_PROJECT_ROOT", str(tmp_path))
    return brain


def _read_events(brain: Path) -> list[dict]:
    path = brain / "ledger" / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ──────────────────────────────────────────────────────────────
# FORGE TEST — [BB99] with no registry entry
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forge_bb99_no_registry_passes_when_flag_off(gov_brain, monkeypatch):
    """Legacy behavior preserved: flag OFF, regex match alone is enough."""
    monkeypatch.delenv("NUCLEUS_GOVERNANCE_ANCHOR", raising=False)
    tool = _build_router()
    raw = await tool("validate_strategic_plan", {"plan_text": "plan cites [BB99]", "mode": "strategic"})
    result = json.loads(raw)
    assert result["valid"] is True, result
    assert "anchor_verified" not in result, result


@pytest.mark.asyncio
async def test_forge_bb99_no_registry_fails_when_flag_on(gov_brain, monkeypatch):
    """THE FORGE TEST: [BB99] with no registry entry anywhere fails validation
    when the anchor flag is ON — no docs/reports/nucleus_bigbang_30d.md exists
    in the scratch NUCLEUS_PROJECT_ROOT at all, so nothing can be registered."""
    monkeypatch.setenv("NUCLEUS_GOVERNANCE_ANCHOR", "1")
    tool = _build_router()
    raw = await tool("validate_strategic_plan", {"plan_text": "plan cites [BB99]", "mode": "strategic"})
    result = json.loads(raw)
    assert result["valid"] is False, result
    assert "BB99" in str(result.get("unregistered_refs")), result

    types = [e.get("type") for e in _read_events(gov_brain)]
    assert "governance_strategic_plan_rejected" in types, types


# ──────────────────────────────────────────────────────────────
# Registry-hit path — flag ON, tag IS registered
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_registered_bb_ref_passes_when_flag_on(gov_brain, monkeypatch, tmp_path):
    """A [BB01] tag that DOES map to a committed registry entry passes anchor
    verification, and the response is stamped anchor_verified=True."""
    registry = tmp_path / "docs" / "reports" / "nucleus_bigbang_30d.md"
    registry.parent.mkdir(parents=True)
    registry.write_text("## BB01 — the insight\nSome committed content.\n")

    monkeypatch.setenv("NUCLEUS_GOVERNANCE_ANCHOR", "1")
    tool = _build_router()
    raw = await tool("validate_strategic_plan", {"plan_text": "plan cites [BB01]", "mode": "strategic"})
    result = json.loads(raw)
    assert result["valid"] is True, result
    assert result["anchor_verified"] is True, result


@pytest.mark.asyncio
async def test_mixed_registered_and_unregistered_refs_fails_when_flag_on(gov_brain, monkeypatch, tmp_path):
    """[BB01] is registered but [BB02] is not — the whole plan still fails,
    and only the unregistered tag is reported."""
    registry = tmp_path / "docs" / "reports" / "nucleus_bigbang_30d.md"
    registry.parent.mkdir(parents=True)
    registry.write_text("## BB01 — the insight\n")

    monkeypatch.setenv("NUCLEUS_GOVERNANCE_ANCHOR", "1")
    tool = _build_router()
    raw = await tool(
        "validate_strategic_plan",
        {"plan_text": "plan cites [BB01] and [BB02]", "mode": "strategic"},
    )
    result = json.loads(raw)
    assert result["valid"] is False, result
    assert result["unregistered_refs"] == ["[BB02]"], result


@pytest.mark.asyncio
async def test_tactical_mode_unaffected_by_flag(gov_brain, monkeypatch):
    """TACTICAL mode never required BB refs and the anchor check is a
    strategic-mode-only gate; flag ON must not change tactical behavior."""
    monkeypatch.setenv("NUCLEUS_GOVERNANCE_ANCHOR", "1")
    tool = _build_router()
    raw = await tool("validate_strategic_plan", {"plan_text": "no refs at all", "mode": "tactical"})
    result = json.loads(raw)
    assert result["valid"] is True, result


# ──────────────────────────────────────────────────────────────
# audit_report — "sovereignty verified" no longer hardcoded
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def brain_dir(tmp_path):
    brain = tmp_path / ".brain2"
    (brain / "ledger").mkdir(parents=True)
    (brain / "engrams").mkdir(parents=True)
    (brain / "governance").mkdir(parents=True)
    return brain


def _write_events(brain: Path, events: list[dict]) -> None:
    events_file = brain / "ledger" / "events.jsonl"
    with open(events_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _sovereignty_check(report: dict) -> dict:
    checks = report["sections"]["compliance_checklist"]["checks"]
    matches = [c for c in checks if c["item"] == "All data local (sovereignty verified)"]
    assert len(matches) == 1, checks
    return matches[0]


def test_audit_report_sovereignty_hardcoded_pass_when_flag_off(brain_dir, monkeypatch):
    """Legacy behavior preserved: flag OFF always reports pass, even with an
    egress event on record — this is the pre-existing (gap) behavior."""
    monkeypatch.delenv("NUCLEUS_GOVERNANCE_ANCHOR", raising=False)
    _write_events(brain_dir, [
        {"event_type": "governance_egress_curl", "timestamp": "2026-07-12T00:00:00Z",
         "emitter": "nucleus_governance", "description": "curl GET https://pypi.org"},
    ])
    from mcp_server_nucleus.runtime.audit_report import generate_audit_report
    report = generate_audit_report(brain_dir)
    check = _sovereignty_check(report)
    assert check["status"] == "pass", check


def test_audit_report_sovereignty_fails_on_real_egress_when_flag_on(brain_dir, monkeypatch):
    """Anchored check: a real egress event in the event log flips the
    checklist item to fail instead of the old hardcoded pass."""
    monkeypatch.setenv("NUCLEUS_GOVERNANCE_ANCHOR", "1")
    _write_events(brain_dir, [
        {"event_type": "governance_egress_curl", "timestamp": "2026-07-12T00:00:00Z",
         "emitter": "nucleus_governance", "description": "curl GET https://pypi.org"},
    ])
    from mcp_server_nucleus.runtime.audit_report import generate_audit_report
    report = generate_audit_report(brain_dir)
    check = _sovereignty_check(report)
    assert check["status"] == "fail", check


def test_audit_report_sovereignty_passes_with_no_egress_when_flag_on(brain_dir, monkeypatch):
    """Anchored check with a clean event log (no egress) still passes —
    this is a real verification, not a permanent fail."""
    monkeypatch.setenv("NUCLEUS_GOVERNANCE_ANCHOR", "1")
    _write_events(brain_dir, [
        {"event_type": "TaskClaimed", "timestamp": "2026-07-12T00:00:00Z",
         "emitter": "agent-1", "description": "Claimed task T001"},
    ])
    from mcp_server_nucleus.runtime.audit_report import generate_audit_report
    report = generate_audit_report(brain_dir)
    check = _sovereignty_check(report)
    assert check["status"] == "pass", check
