"""Per ADR-0033 v3 §B / §A + role_taxonomy_refactor_agy_v3.md: every canonical
mapping in the role-normalization table is exercised; unknown roles log a
warning and return 'unknown'.

Updated for Phase 1 role taxonomy refactor:
- Legacy roles (main, peer, tb) are now aliases, not canonical.
- Canonical roles are: coordinator, worker, reviewer, gq, operator_assistant,
  agy, devin, codex, unknown.
- main → coordinator, peer → worker, tb → reviewer.
"""
from __future__ import annotations

import logging

import pytest


@pytest.mark.parametrize(
    "alias,expected",
    [
        # Functional roles (canonical)
        ("coordinator", "coordinator"),
        ("worker", "worker"),
        ("reviewer", "reviewer"),
        # Legacy aliases → functional canonical
        ("main", "coordinator"),
        ("cc_main", "coordinator"),
        ("claude_code_main", "coordinator"),
        ("cc-main", "coordinator"),
        ("CC-MAIN", "coordinator"),
        ("primary", "coordinator"),
        ("peer", "worker"),
        ("cc_peer", "worker"),
        ("cc-peer", "worker"),
        ("secondary", "worker"),
        ("tb", "reviewer"),
        ("cc_tb", "reviewer"),
        ("cc-tb", "reviewer"),
        # Vendor-specific roles (canonical)
        ("gq", "gq"),
        ("cc_gq", "gq"),
        ("cc-gq", "gq"),
        ("operator_assistant", "operator_assistant"),
        ("op_assistant", "operator_assistant"),
        ("op-assistant", "operator_assistant"),
        ("agy", "agy"),
        ("antigravity", "agy"),
        ("agy-cli", "agy"),
        ("devin", "devin"),
        ("codex", "codex"),
    ],
)
def test_canonical_mappings(alias: str, expected: str) -> None:
    from nucleus_wedge.role_normalize import _normalize_role
    assert _normalize_role(alias) == expected


@pytest.mark.parametrize(
    "drift",
    ["random-thing", "", None, "   "],
)
def test_unknown_logs_warning(drift, caplog) -> None:
    from nucleus_wedge.role_normalize import _normalize_role

    with caplog.at_level(logging.WARNING, logger="nucleus_wedge.role_normalize"):
        result = _normalize_role(drift)
    assert result == "unknown"
    assert any("role normalize" in r.message for r in caplog.records)


def test_canonical_roles_list_contains_all() -> None:
    from nucleus_wedge.role_normalize import canonical_roles

    roles = set(canonical_roles())
    assert {
        "coordinator", "worker", "reviewer",
        "gq", "operator_assistant", "agy",
        "devin", "codex", "unknown",
    } <= roles


def test_role_canonical_at_store_save(tmp_path, monkeypatch) -> None:
    """End-to-end: Store.append's tags writer normalizes role:<x> tags."""
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    from nucleus_wedge.store import Store

    store = Store(brain)
    store.append(value="hello", kind="activity", tags=["role:cc_main", "domain:test"])
    rows = list(store.rows())
    assert len(rows) == 1
    ctx = rows[0]["snapshot"]["context"]
    # cc_main is now an alias for coordinator (not main)
    assert "role:coordinator" in ctx
    assert "role:cc_main" not in ctx
    assert "role:main" not in ctx
    assert "domain:test" in ctx
