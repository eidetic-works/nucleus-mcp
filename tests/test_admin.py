"""Tests for mcp_server_nucleus.admin — portability contract.

The admin modules drive host-side state (MCP host config, ledger file), so
tests cover the primitive-gate invariants:

- Clean import with no NUCLEUS_* env set.
- Env-override precedence for each path helper.
- Fallback semantics when env is unset.
- Atomic write (tmp-then-rename) for the triggers writer — no truncated
  reader visibility.
- ``switch_brain`` exit codes for the three observable failure modes
  (unknown mode, missing host config, malformed config).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ENV_KEYS = (
    "NUCLEUS_ROOT",
    "NUCLEUS_BRAIN",
    "NUCLEUS_BRAIN_PATH",
    "NUCLEUS_ANTIGRAVITY_CONFIG",
    "NUCLEUS_TEST_BRAIN",
    "NUCLEUS_TRIGGERS_PATH",
)


@pytest.fixture
def clean_env(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


# ---------------------------------------------------------------------------
# admin package import surface
# ---------------------------------------------------------------------------


def test_admin_modules_import_clean(clean_env):
    from mcp_server_nucleus.admin import switch_brain, triggers

    assert callable(switch_brain.main)
    assert callable(switch_brain.switch_brain)
    assert callable(triggers.main)
    assert callable(triggers.write_triggers)
    assert callable(triggers.default_triggers_v22)


# ---------------------------------------------------------------------------
# switch_brain env-driven paths
# ---------------------------------------------------------------------------


def test_switch_brain_host_config_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.admin import switch_brain

    clean_env.setenv("NUCLEUS_ANTIGRAVITY_CONFIG", str(tmp_path / "mcp.json"))
    assert switch_brain._host_config_path() == tmp_path / "mcp.json"


def test_switch_brain_host_config_fallback(clean_env):
    from mcp_server_nucleus.admin import switch_brain

    assert (
        switch_brain._host_config_path()
        == Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
    )


def test_switch_brain_warm_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.admin import switch_brain

    clean_env.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "warm" / ".brain"))
    assert switch_brain._warm_brain() == str(tmp_path / "warm" / ".brain")


def test_switch_brain_warm_fallback_is_dot_brain(clean_env):
    from mcp_server_nucleus.admin import switch_brain

    assert switch_brain._warm_brain() == ".brain"


def test_switch_brain_cold_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.admin import switch_brain

    clean_env.setenv("NUCLEUS_TEST_BRAIN", str(tmp_path / "cold" / ".brain"))
    assert switch_brain._cold_brain() == str(tmp_path / "cold" / ".brain")


def test_switch_brain_cold_fallback_is_sibling_of_nucleus_root(clean_env, tmp_path):
    from mcp_server_nucleus.admin import switch_brain

    clean_env.setenv("NUCLEUS_ROOT", str(tmp_path / "repo"))
    assert (
        switch_brain._cold_brain()
        == str(tmp_path / "dogfood-brain" / ".brain")
    )


def test_switch_brain_brains_dict_aliases(clean_env, tmp_path):
    from mcp_server_nucleus.admin import switch_brain

    clean_env.setenv("NUCLEUS_BRAIN_PATH", "/warm/.brain")
    clean_env.setenv("NUCLEUS_TEST_BRAIN", "/cold/.brain")
    brains = switch_brain._brains()
    assert brains["warm"] == brains["prod"] == "/warm/.brain"
    assert brains["cold"] == brains["dogfood"] == "/cold/.brain"


# ---------------------------------------------------------------------------
# switch_brain exit codes — the observable primitive-gate surface
# ---------------------------------------------------------------------------


def test_switch_brain_unknown_mode_returns_1(clean_env):
    from mcp_server_nucleus.admin import switch_brain

    assert switch_brain.switch_brain("hot") == 1


def test_switch_brain_missing_host_config_returns_1(clean_env, tmp_path, monkeypatch):
    from mcp_server_nucleus.admin import switch_brain

    clean_env.setenv("NUCLEUS_ANTIGRAVITY_CONFIG", str(tmp_path / "nope.json"))
    monkeypatch.setattr(switch_brain, "_kill_servers", lambda: None)
    assert switch_brain.switch_brain("warm") == 1


def test_switch_brain_malformed_host_config_returns_1(
    clean_env, tmp_path, monkeypatch
):
    from mcp_server_nucleus.admin import switch_brain

    host = tmp_path / "mcp.json"
    host.write_text(json.dumps({"mcpServers": {"other": {}}}))
    clean_env.setenv("NUCLEUS_ANTIGRAVITY_CONFIG", str(host))
    monkeypatch.setattr(switch_brain, "_kill_servers", lambda: None)
    assert switch_brain.switch_brain("warm") == 1


def test_switch_brain_warm_updates_host_config(clean_env, tmp_path, monkeypatch):
    from mcp_server_nucleus.admin import switch_brain

    host = tmp_path / "mcp.json"
    host.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "nucleus": {
                        "env": {"NUCLEUS_BRAIN_PATH": "/stale/.brain"},
                    }
                }
            }
        )
    )
    clean_env.setenv("NUCLEUS_ANTIGRAVITY_CONFIG", str(host))
    clean_env.setenv("NUCLEUS_BRAIN_PATH", "/new/.brain")
    monkeypatch.setattr(switch_brain, "_kill_servers", lambda: None)

    assert switch_brain.switch_brain("warm") == 0

    rewritten = json.loads(host.read_text())
    assert (
        rewritten["mcpServers"]["nucleus"]["env"]["NUCLEUS_BRAIN_PATH"]
        == "/new/.brain"
    )


def test_switch_brain_cold_wipes_existing_target(clean_env, tmp_path, monkeypatch):
    from mcp_server_nucleus.admin import switch_brain

    host = tmp_path / "mcp.json"
    host.write_text(
        json.dumps(
            {"mcpServers": {"nucleus": {"env": {"NUCLEUS_BRAIN_PATH": "x"}}}}
        )
    )
    cold = tmp_path / "cold" / ".brain"
    cold.mkdir(parents=True)
    (cold / "stale.txt").write_text("leftover")

    clean_env.setenv("NUCLEUS_ANTIGRAVITY_CONFIG", str(host))
    clean_env.setenv("NUCLEUS_TEST_BRAIN", str(cold))
    monkeypatch.setattr(switch_brain, "_kill_servers", lambda: None)

    assert switch_brain.switch_brain("cold") == 0
    assert not cold.exists()


def test_switch_brain_main_requires_single_arg(clean_env):
    from mcp_server_nucleus.admin import switch_brain

    assert switch_brain.main([]) == 1
    assert switch_brain.main(["warm", "cold"]) == 1


# ---------------------------------------------------------------------------
# triggers path + writer
# ---------------------------------------------------------------------------


def test_triggers_path_env_wins(clean_env, tmp_path):
    from mcp_server_nucleus.admin import triggers

    clean_env.setenv("NUCLEUS_TRIGGERS_PATH", str(tmp_path / "t.json"))
    assert triggers.triggers_path() == tmp_path / "t.json"


def test_triggers_path_fallback_under_brain(clean_env, tmp_path):
    from mcp_server_nucleus.admin import triggers

    clean_env.setenv("NUCLEUS_BRAIN", str(tmp_path / ".brain"))
    assert (
        triggers.triggers_path()
        == tmp_path / ".brain" / "ledger" / "triggers.json"
    )


def test_default_triggers_v22_shape(clean_env):
    from mcp_server_nucleus.admin import triggers

    bundle = triggers.default_triggers_v22()
    assert bundle["version"] == "2.2"
    ids = [t["id"] for t in bundle["triggers"]]
    assert "task-state-changed" in ids
    assert "trigger-synthesis" in ids
    assert "trigger-task-assigned" in ids
    assert len(ids) == len(set(ids)), "trigger ids must be unique"


def test_default_triggers_v22_returns_fresh_dict(clean_env):
    from mcp_server_nucleus.admin import triggers

    a = triggers.default_triggers_v22()
    b = triggers.default_triggers_v22()
    a["triggers"].clear()
    assert len(b["triggers"]) > 0, "mutating one copy must not affect the next"


def test_write_triggers_writes_default_bundle(clean_env, tmp_path):
    from mcp_server_nucleus.admin import triggers

    dest = tmp_path / "sub" / "triggers.json"
    clean_env.setenv("NUCLEUS_TRIGGERS_PATH", str(dest))

    written = triggers.write_triggers()
    assert written == dest
    assert dest.exists()

    loaded = json.loads(dest.read_text())
    assert loaded == triggers.default_triggers_v22()


def test_write_triggers_accepts_override_content(clean_env, tmp_path):
    from mcp_server_nucleus.admin import triggers

    dest = tmp_path / "triggers.json"
    override = {"version": "test", "triggers": []}

    triggers.write_triggers(path=dest, content=override)
    assert json.loads(dest.read_text()) == override


def test_write_triggers_is_atomic_no_tmp_leak(clean_env, tmp_path):
    from mcp_server_nucleus.admin import triggers

    dest = tmp_path / "triggers.json"
    triggers.write_triggers(path=dest)

    assert dest.exists()
    assert not (tmp_path / "triggers.json.tmp").exists()


def test_triggers_main_returns_0_on_success(clean_env, tmp_path):
    from mcp_server_nucleus.admin import triggers

    dest = tmp_path / "out.json"
    clean_env.setenv("NUCLEUS_TRIGGERS_PATH", str(dest))
    assert triggers.main() == 0
    assert dest.exists()
