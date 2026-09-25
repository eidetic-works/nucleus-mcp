"""Coverage tests for runtime/team.py."""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.team import TeamConfig, TeamManager, TeamPolicy


def _brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir()
    return brain


def test_team_policy_defaults():
    p = TeamPolicy()
    assert p.require_signed is True
    assert p.min_trust_level == "verified"


def test_team_config_defaults():
    c = TeamConfig(team_id="t1", name="Team")
    assert c.registry_url is None
    assert c.trusted_keys == []
    assert c.policy.require_signed is True


def test_team_config_custom():
    c = TeamConfig(
        team_id="t1",
        name="Team",
        registry_url="https://r",
        trusted_keys=["k1"],
        policy=TeamPolicy(require_signed=False, min_trust_level="community"),
    )
    assert c.registry_url == "https://r"
    assert c.trusted_keys == ["k1"]
    assert c.policy.require_signed is False


def test_get_config_no_file(tmp_path):
    brain = _brain(tmp_path)
    tm = TeamManager(brain)
    assert tm.get_config() is None


def test_get_config_valid(tmp_path):
    brain = _brain(tmp_path)
    cfg = brain / "config"
    cfg.mkdir()
    (cfg / "team.json").write_text(json.dumps({
        "team_id": "t1",
        "name": "Team",
        "trusted_keys": ["k1", "k2"],
        "registry_url": "https://r",
    }))
    tm = TeamManager(brain)
    c = tm.get_config()
    assert c.team_id == "t1"
    assert c.trusted_keys == ["k1", "k2"]


def test_get_config_corrupt(tmp_path):
    brain = _brain(tmp_path)
    cfg = brain / "config"
    cfg.mkdir()
    (cfg / "team.json").write_text("not json")
    tm = TeamManager(brain)
    assert tm.get_config() is None


def test_get_trusted_roots_no_config(tmp_path):
    brain = _brain(tmp_path)
    tm = TeamManager(brain)
    assert tm.get_trusted_roots() == []


def test_get_trusted_roots_with_config(tmp_path):
    brain = _brain(tmp_path)
    cfg = brain / "config"
    cfg.mkdir()
    (cfg / "team.json").write_text(json.dumps({
        "team_id": "t1", "name": "T", "trusted_keys": ["k1"],
    }))
    tm = TeamManager(brain)
    assert tm.get_trusted_roots() == ["k1"]


def test_get_registry_url_no_config(tmp_path):
    brain = _brain(tmp_path)
    tm = TeamManager(brain)
    assert tm.get_registry_url() is None


def test_get_registry_url_with_config(tmp_path):
    brain = _brain(tmp_path)
    cfg = brain / "config"
    cfg.mkdir()
    (cfg / "team.json").write_text(json.dumps({
        "team_id": "t1", "name": "T", "registry_url": "https://reg",
    }))
    tm = TeamManager(brain)
    assert tm.get_registry_url() == "https://reg"
