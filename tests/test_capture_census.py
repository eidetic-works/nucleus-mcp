"""Tests for the capture_census instrument (PRINCIPAL G1 workstream #0).

Verifies the census correctly classifies vendor surfaces from relay buckets,
attributes engrams via relay projection keys + direct vendor source_agents,
and reports the missing-capture verdict. Sandboxed per
feedback_dogfood_sandbox_leak.md — every test builds a tmp .brain tree.
"""
from __future__ import annotations

import json
from pathlib import Path

from mcp_server_nucleus.runtime import capture_census as cc


def _make_relay(relay_id: str, bucket: str, from_agent: str = "cc_main",
                to_agent: str = "antigravity", from_provider: str | None = None) -> dict:
    msg = {
        "id": relay_id,
        "from": from_agent,
        "to": to_agent,
        "from_role": "worker",
        "subject": "test",
        "body": "test body",
        "priority": "normal",
        "read": False,
    }
    if from_provider:
        msg["from_provider"] = from_provider
    return msg


def _build_brain(tmp_path: Path, relay_buckets: dict[str, list[dict]],
                 engram_lines: list[dict] | None = None) -> Path:
    """Build a minimal .brain tree with relay buckets + engram history.jsonl."""
    brain = tmp_path / ".brain"
    relay_root = brain / "relay"
    relay_root.mkdir(parents=True)
    for bucket, msgs in relay_buckets.items():
        bdir = relay_root / bucket
        bdir.mkdir()
        for i, msg in enumerate(msgs):
            (bdir / f"msg_{i}.json").write_text(json.dumps(msg))
    engram_dir = brain / "engrams"
    engram_dir.mkdir()
    lines = engram_lines or []
    with open(engram_dir / "history.jsonl", "w") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")
    return brain


def test_classify_vendor_surface_by_bucket():
    """Antigravity/glm/devin buckets classify to their vendor surfaces."""
    assert cc._classify_vendor_surface("antigravity", {}) == "antigravity"
    assert cc._classify_vendor_surface("glm_main_agent", {}) == "glm"
    assert cc._classify_vendor_surface("devin", {}) == "devin"
    assert cc._classify_vendor_surface("claude_code_main", {}) == "anthropic_claude_code"


def test_classify_vendor_surface_test_fixture():
    """acme_corp buckets classify as test_fixture, not a fleet surface."""
    assert cc._classify_vendor_surface("acme_corp", {}) == "test_fixture"
    assert cc._classify_vendor_surface("acme_corp_fail", {}) == "test_fixture"


def test_classify_vendor_surface_by_from_provider():
    """from_provider overrides bucket when present (vendor-stamped)."""
    msg = {"from_provider": "zhipu_glm"}
    assert cc._classify_vendor_surface("unknown_bucket", msg) == "glm"
    msg = {"from_provider": "cognition_devin"}
    assert cc._classify_vendor_surface("unknown_bucket", msg) == "devin"


def test_census_relay_counts_by_vendor_surface(tmp_path):
    """Relay envelopes are counted per vendor surface."""
    brain = _build_brain(tmp_path, {
        "antigravity": [_make_relay("r1", "antigravity", to_agent="antigravity")],
        "glm_main_agent": [_make_relay("r2", "glm_main_agent", to_agent="glm_main_agent")],
        "claude_code_main": [_make_relay("r3", "claude_code_main")],
        "acme_corp": [_make_relay("r4", "acme_corp")],
    })
    report = cc.run_census(brain)
    by_surf = report["relay"]["by_vendor_surface"]
    assert by_surf.get("antigravity") == 1
    assert by_surf.get("glm") == 1
    assert by_surf.get("anthropic_claude_code") == 1
    assert by_surf.get("test_fixture") == 1
    assert report["relay"]["total_envelopes"] == 4


def test_census_engram_projection_attribution(tmp_path):
    """Relay projection engrams are attributed to the envelope's vendor surface."""
    relay = _make_relay("relay_abc", "antigravity", from_agent="cc_main",
                        to_agent="antigravity")
    brain = _build_brain(tmp_path, {
        "antigravity": [relay],
    }, engram_lines=[
        {"key": "relay_projection_relay_abc", "op_type": "ADD",
         "snapshot": {"key": "relay_projection_relay_abc", "source_agent": "relay_surface_projection"}},
        {"key": "auto_1", "op_type": "ADD",
         "snapshot": {"key": "auto_1", "source_agent": "auto_hook"}},
    ])
    report = cc.run_census(brain)
    e = report["engram"]
    assert e["relay_projection_engrams"] == 1
    assert e["engrams_by_vendor_surface"].get("antigravity") == 1
    assert "auto_hook" in e["engrams_by_source_agent"]


def test_census_direct_vendor_source_agent(tmp_path):
    """Direct vendor source_agent stamps (devin, agy) attribute to vendor surface."""
    brain = _build_brain(tmp_path, {
        "devin": [_make_relay("r1", "devin", to_agent="devin")],
    }, engram_lines=[
        {"key": "eng_1", "op_type": "ADD",
         "snapshot": {"key": "eng_1", "source_agent": "devin"}},
        {"key": "eng_2", "op_type": "ADD",
         "snapshot": {"key": "eng_2", "source_agent": "agy"}},
    ])
    report = cc.run_census(brain)
    e = report["engram"]
    assert e["direct_vendor_engrams"] == 2
    assert e["engrams_by_vendor_surface"].get("devin") == 1
    assert e["engrams_by_vendor_surface"].get("antigravity") == 1


def test_census_verdict_missing_capture(tmp_path):
    """A fleet surface with relay traffic but no engram projection is flagged missing."""
    brain = _build_brain(tmp_path, {
        "antigravity": [_make_relay("r1", "antigravity", to_agent="antigravity")],
    }, engram_lines=[])
    report = cc.run_census(brain)
    v = report["verdict"]
    assert "antigravity" in v["surfaces_with_relay_traffic"]
    assert "antigravity" in v["surfaces_relay_only_no_engram_projection"]
    assert "antigravity" in v["missing_capture_for_known_fleet"]
    assert "antigravity" not in v["surfaces_fully_captured"]


def test_census_verdict_fully_captured(tmp_path):
    """A surface with both relay traffic AND engram projection is fully captured."""
    relay = _make_relay("relay_xyz", "antigravity", to_agent="antigravity")
    brain = _build_brain(tmp_path, {
        "antigravity": [relay],
    }, engram_lines=[
        {"key": "relay_projection_relay_xyz", "op_type": "ADD",
         "snapshot": {"key": "relay_projection_relay_xyz", "source_agent": "relay_surface_projection"}},
    ])
    report = cc.run_census(brain)
    v = report["verdict"]
    assert "antigravity" in v["surfaces_fully_captured"]
    assert "antigravity" not in v["missing_capture_for_known_fleet"]


def test_census_cross_vendor_edges(tmp_path):
    """Cross-vendor edges (from_surface -> to_surface) are detected."""
    brain = _build_brain(tmp_path, {
        "antigravity": [_make_relay("r1", "antigravity", from_agent="cc_main",
                                    to_agent="antigravity")],
    })
    report = cc.run_census(brain)
    edges = report["relay"]["cross_vendor_edges"]
    assert any("anthropic_claude_code->antigravity" in e for e in edges)


def test_census_idempotent_rerun(tmp_path):
    """Re-running the census produces identical verdicts (pure measurement)."""
    brain = _build_brain(tmp_path, {
        "antigravity": [_make_relay("r1", "antigravity", to_agent="antigravity")],
        "glm_main_agent": [_make_relay("r2", "glm_main_agent", to_agent="glm_main_agent")],
    }, engram_lines=[
        {"key": "relay_projection_r1", "op_type": "ADD",
         "snapshot": {"key": "relay_projection_r1", "source_agent": "relay_surface_projection"}},
    ])
    r1 = cc.run_census(brain)
    r2 = cc.run_census(brain)
    assert r1["verdict"] == r2["verdict"]
    assert r1["relay"]["by_vendor_surface"] == r2["relay"]["by_vendor_surface"]
