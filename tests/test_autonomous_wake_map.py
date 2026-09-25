"""Tests for v0.3.0 integration — sessions/autonomous_wake_map.

Per cc-peer 2026-06-09T10:45Z + 11:28Z verdict batch + cc-tb 11:00Z
status relay decomposing PR #506 into library (this) + hook patch
(separate PR).

Coverage:
- AutonomousWakeConfig: required fields, defaults, immutability via __slots__
- AutonomousWakeConfig.__repr__ truncates session_id + org_uuid
- register/unregister/get/is_autonomous/list/clear lifecycle
- Registry key must match config.role
- Pseudonymity: register/unregister log emission truncates IDs
"""
from __future__ import annotations

import pytest

from mcp_server_nucleus.sessions import autonomous_wake_map as wm


@pytest.fixture(autouse=True)
def _clean_registry():
    """Wipe the module-level MAP between tests."""
    wm.clear_registry()
    yield
    wm.clear_registry()


# ── AutonomousWakeConfig ───────────────────────────────────────────────


def test_config_minimal_required_fields():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_abc", org_uuid="903554b9-org",
    )
    assert cfg.role == "cc_tb"
    assert cfg.session_id == "cse_abc"
    assert cfg.org_uuid == "903554b9-org"
    assert cfg.model is None
    assert cfg.max_tokens is None
    assert cfg.history_limit == 50  # default
    assert cfg.prearm is True  # default


def test_config_all_fields():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
        model="claude-opus-4-7", max_tokens=8192,
        history_limit=10, prearm=False,
    )
    assert cfg.model == "claude-opus-4-7"
    assert cfg.max_tokens == 8192
    assert cfg.history_limit == 10
    assert cfg.prearm is False


def test_config_raises_on_empty_role():
    with pytest.raises(ValueError):
        wm.AutonomousWakeConfig(role="", session_id="cse_x", org_uuid="o")


def test_config_raises_on_empty_session_id():
    with pytest.raises(ValueError):
        wm.AutonomousWakeConfig(role="cc_tb", session_id="", org_uuid="o")


def test_config_raises_on_empty_org_uuid():
    with pytest.raises(ValueError):
        wm.AutonomousWakeConfig(role="cc_tb", session_id="cse_x", org_uuid="")


def test_config_history_limit_int_coercion():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
        history_limit="25",  # str passed; should coerce
    )
    assert cfg.history_limit == 25
    assert isinstance(cfg.history_limit, int)


def test_config_slots_prevents_arbitrary_attrs():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
    )
    with pytest.raises(AttributeError):
        cfg.arbitrary_attr = "x"


# ── Repr pseudonymity ─────────────────────────────────────────────────


def test_repr_truncates_session_and_org_ids():
    long_cse = "cse_AAAAAAAAAAAAAAAAAAAAAAAAAAAA-secret-rest"
    long_org = "903554b9-AAAAAAAAAAAAAAAAAAAAAAAAA-secret-rest"
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id=long_cse, org_uuid=long_org,
    )
    r = repr(cfg)
    assert long_cse[:12] in r
    assert long_org[:12] in r
    assert long_cse not in r  # full ID not leaked
    assert long_org not in r


# ── register / get / is_autonomous ────────────────────────────────────


def test_register_and_get():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
    )
    wm.register_autonomous_role("cc_tb", cfg)
    assert wm.get_autonomous_config("cc_tb") is cfg
    assert wm.is_autonomous_role("cc_tb")


def test_get_returns_none_for_unregistered():
    assert wm.get_autonomous_config("ghost") is None
    assert wm.is_autonomous_role("ghost") is False


def test_register_overwrites_existing():
    cfg_old = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_old", org_uuid="o",
    )
    cfg_new = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_new", org_uuid="o",
    )
    wm.register_autonomous_role("cc_tb", cfg_old)
    wm.register_autonomous_role("cc_tb", cfg_new)
    assert wm.get_autonomous_config("cc_tb").session_id == "cse_new"


def test_register_rejects_role_key_mismatch():
    cfg = wm.AutonomousWakeConfig(
        role="cc_peer", session_id="cse_x", org_uuid="o",
    )
    with pytest.raises(ValueError):
        wm.register_autonomous_role("cc_tb", cfg)  # key vs config.role differ


def test_register_rejects_non_config_type():
    with pytest.raises(TypeError):
        wm.register_autonomous_role("cc_tb", {"role": "cc_tb"})  # raw dict


def test_register_rejects_empty_role():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
    )
    with pytest.raises(ValueError):
        wm.register_autonomous_role("", cfg)


# ── unregister ────────────────────────────────────────────────────────


def test_unregister_returns_true_on_removal():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
    )
    wm.register_autonomous_role("cc_tb", cfg)
    assert wm.unregister_autonomous_role("cc_tb") is True
    assert wm.is_autonomous_role("cc_tb") is False


def test_unregister_returns_false_on_missing():
    assert wm.unregister_autonomous_role("ghost") is False


# ── list / clear ──────────────────────────────────────────────────────


def test_list_autonomous_roles_empty_when_no_registrations():
    assert wm.list_autonomous_roles() == []


def test_list_autonomous_roles_returns_all_registered():
    wm.register_autonomous_role(
        "cc_tb", wm.AutonomousWakeConfig(
            role="cc_tb", session_id="cse_1", org_uuid="o",
        ),
    )
    wm.register_autonomous_role(
        "cc_peer", wm.AutonomousWakeConfig(
            role="cc_peer", session_id="cse_2", org_uuid="o",
        ),
    )
    roles = set(wm.list_autonomous_roles())
    assert roles == {"cc_tb", "cc_peer"}


def test_clear_registry_removes_all():
    wm.register_autonomous_role(
        "cc_tb", wm.AutonomousWakeConfig(
            role="cc_tb", session_id="cse_1", org_uuid="o",
        ),
    )
    wm.clear_registry()
    assert wm.list_autonomous_roles() == []
    assert wm.is_autonomous_role("cc_tb") is False


# ── Module-level MAP is the live registry ─────────────────────────────


def test_module_level_map_is_live_registry():
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id="cse_x", org_uuid="o",
    )
    wm.register_autonomous_role("cc_tb", cfg)
    # The exported NUCLEUS_AUTONOMOUS_WAKE_MAP must reflect the change
    assert "cc_tb" in wm.NUCLEUS_AUTONOMOUS_WAKE_MAP
    assert wm.NUCLEUS_AUTONOMOUS_WAKE_MAP["cc_tb"] is cfg


# ── Pseudonymity in logs ──────────────────────────────────────────────


def test_register_log_truncates_ids(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.autonomous_wake_map")
    long_cse = "cse_AAAAAAAA_BBBBBBBB_CCCCCCCC-secret"
    long_org = "903554b9_AAAAAAAA_BBBBBBBB-secret"
    cfg = wm.AutonomousWakeConfig(
        role="cc_tb", session_id=long_cse, org_uuid=long_org,
    )
    wm.register_autonomous_role("cc_tb", cfg)
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert long_cse[:12] in all_text
    assert long_org[:12] in all_text
    assert long_cse not in all_text
    assert long_org not in all_text


# ── Exports ───────────────────────────────────────────────────────────


def test_all_exported():
    expected = {
        "AutonomousWakeConfig",
        "NUCLEUS_AUTONOMOUS_WAKE_MAP",
        "register_autonomous_role",
        "unregister_autonomous_role",
        "get_autonomous_config",
        "is_autonomous_role",
        "list_autonomous_roles",
        "clear_registry",
    }
    assert set(wm.__all__) == expected
