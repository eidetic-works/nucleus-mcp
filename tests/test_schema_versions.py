"""Unit tests for runtime.schema_versions."""

from __future__ import annotations

import pytest

from mcp_server_nucleus.runtime import schema_versions as sv


def test_constants_are_ints():
    assert isinstance(sv.STATE_SCHEMA_VERSION, int)
    assert isinstance(sv.ENGRAM_SCHEMA_VERSION, int)
    assert isinstance(sv.TASK_SCHEMA_VERSION, int)
    assert isinstance(sv.MANIFEST_SCHEMA_VERSION, int)


def test_current_version_known_kinds():
    assert sv.current_version("state") == sv.STATE_SCHEMA_VERSION
    assert sv.current_version("engram") == sv.ENGRAM_SCHEMA_VERSION
    assert sv.current_version("task") == sv.TASK_SCHEMA_VERSION
    assert sv.current_version("manifest") == sv.MANIFEST_SCHEMA_VERSION


def test_current_version_unknown_kind_raises():
    with pytest.raises(ValueError):
        sv.current_version("zebra")


def test_upgrade_engram_v1_to_v2():
    record = {"id": "abc", "text": "hello"}
    out = sv.upgrade("engram", record)
    assert out["schema_version"] == 2
    assert out["project"] == "_unscoped"
    assert out["brain_id"] == "unknown"
    assert out["id"] == "abc"


def test_upgrade_preserves_existing_project():
    record = {"id": "abc", "project": "explicit-project"}
    out = sv.upgrade("engram", record)
    assert out["project"] == "explicit-project"


def test_upgrade_idempotent_on_current():
    record = {"id": "abc", "schema_version": 2, "project": "x", "brain_id": "y"}
    out = sv.upgrade("engram", record)
    assert out["schema_version"] == 2
    assert out["project"] == "x"


def test_upgrade_state_fills_stale_after_defaults():
    record = {
        "priorities": [{"name": "p1"}, {"name": "p2", "stale_after": "7d"}],
        "tasks": [{"name": "t1"}],
    }
    out = sv.upgrade("state", record)
    assert out["priorities"][0]["stale_after"] == "14d"
    assert out["priorities"][1]["stale_after"] == "7d"  # preserved
    assert out["tasks"][0]["stale_after"] == "30d"
    assert out["schema_version"] == 2


def test_upgrade_task_defaults():
    record = {"name": "my-task"}
    out = sv.upgrade("task", record)
    assert out["stale_after"] == "30d"
    assert out["schema_version"] == 2


def test_upgrade_manifest_defaults():
    record = {"brain_id": "nucleus-primary"}
    out = sv.upgrade("manifest", record)
    assert out["tracks_projects"] == []
    assert out["primary_brain"] is False
    assert out["schema_version"] == 2


def test_upgrade_non_dict_raises():
    with pytest.raises(TypeError):
        sv.upgrade("state", ["not", "a", "dict"])


def test_upgrade_unknown_kind_raises():
    with pytest.raises(ValueError):
        sv.upgrade("unicorn", {"a": 1})


def test_upgrade_does_not_mutate_input():
    record = {"id": "abc"}
    sv.upgrade("engram", record)
    assert "schema_version" not in record
    assert "project" not in record
