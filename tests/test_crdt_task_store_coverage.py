"""Coverage tests for mcp_server_nucleus.runtime.crdt_task_store.CRDTTaskStore."""
import json
import time
from unittest import mock

import pytest

from mcp_server_nucleus.runtime.crdt_task_store import CRDTTaskStore


def test_init_defaults():
    store = CRDTTaskStore()
    assert store.replica_id == "default"
    assert store._tasks == {}
    assert store._tombstones == set()


def test_init_custom_replica():
    store = CRDTTaskStore("replica_a")
    assert store.replica_id == "replica_a"


def test_add_task():
    store = CRDTTaskStore("r1")
    task = {"id": "t1", "title": "Test", "status": "pending", "tier": "T2"}
    result = store.add_task(task)
    assert result["id"] == "t1"
    assert result["title"] == "Test"
    assert "updated_at" in result
    assert "vector_clock" in result
    assert result["replica_id"] == "r1"
    assert "created_at" in result


def test_add_task_no_id_raises():
    store = CRDTTaskStore()
    with pytest.raises(ValueError, match="id"):
        store.add_task({"title": "no id"})


def test_add_task_removes_from_tombstones():
    store = CRDTTaskStore()
    store.add_task({"id": "t1"})
    store.delete_task("t1")
    assert "t1" in store._tombstones
    store.add_task({"id": "t1"})
    assert "t1" not in store._tombstones


def test_update_task():
    store = CRDTTaskStore("r1")
    store.add_task({"id": "t1", "title": "Original", "status": "pending"})
    result = store.update_task("t1", {"status": "done"})
    assert result["status"] == "done"
    assert result["title"] == "Original"
    assert "updated_at" in result


def test_update_task_not_found():
    store = CRDTTaskStore()
    with pytest.raises(KeyError, match="not found"):
        store.update_task("nonexistent", {})


def test_update_task_tombstoned():
    store = CRDTTaskStore()
    store.add_task({"id": "t1"})
    store.delete_task("t1")
    # Task is removed from _tasks and added to tombstones.
    # update_task checks _tasks first, so raises "not found"
    with pytest.raises(KeyError, match="not found"):
        store.update_task("t1", {})


def test_delete_task():
    store = CRDTTaskStore()
    store.add_task({"id": "t1"})
    assert store.delete_task("t1") is True
    assert "t1" in store._tombstones
    assert store.get_task("t1") is None


def test_delete_task_not_found():
    store = CRDTTaskStore()
    assert store.delete_task("nonexistent") is False


def test_get_task():
    store = CRDTTaskStore()
    store.add_task({"id": "t1", "title": "Test"})
    result = store.get_task("t1")
    assert result["title"] == "Test"


def test_get_task_not_found():
    store = CRDTTaskStore()
    assert store.get_task("nonexistent") is None


def test_get_all_tasks_sorted():
    store = CRDTTaskStore()
    store.add_task({"id": "t1", "title": "A"})
    time.sleep(0.01)
    store.add_task({"id": "t2", "title": "B"})
    tasks = store.get_all_tasks()
    assert len(tasks) == 2
    # Newest first
    assert tasks[0]["id"] == "t2"


def test_get_all_tasks_empty():
    store = CRDTTaskStore()
    assert store.get_all_tasks() == []


def test_get_tasks_by_tier():
    store = CRDTTaskStore()
    store.add_task({"id": "t1", "tier": "T2"})
    store.add_task({"id": "t2", "tier": "T3"})
    result = store.get_tasks_by_tier("T2")
    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_get_tasks_by_status():
    store = CRDTTaskStore()
    store.add_task({"id": "t1", "status": "pending"})
    store.add_task({"id": "t2", "status": "done"})
    result = store.get_tasks_by_status("pending")
    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_merge_new_task_from_remote():
    local = CRDTTaskStore("local")
    remote = CRDTTaskStore("remote")
    remote.add_task({"id": "t1", "title": "Remote Task", "tier": "T2"})
    local.merge(remote)
    assert local.get_task("t1") is not None
    assert local.get_task("t1")["title"] == "Remote Task"


def test_merge_lww_remote_newer():
    local = CRDTTaskStore("local")
    remote = CRDTTaskStore("remote")

    # Add to local first
    local.add_task({"id": "t1", "title": "Local Original", "status": "pending"})

    # Simulate remote having a newer timestamp
    remote.add_task({"id": "t1", "title": "Remote Updated", "status": "done"})
    # Force remote timestamp to be newer
    remote._timestamps["t1"] = local._timestamps["t1"] + 10000
    remote._tasks["t1"]["updated_at"] = remote._timestamps["t1"]

    local.merge(remote)
    task = local.get_task("t1")
    assert task["title"] == "Remote Updated"


def test_merge_lww_local_newer():
    local = CRDTTaskStore("local")
    remote = CRDTTaskStore("remote")

    # Add to remote first (older)
    remote.add_task({"id": "t1", "title": "Remote Old", "status": "pending"})
    # Make remote older
    remote._timestamps["t1"] = 1000
    remote._tasks["t1"]["updated_at"] = 1000

    # Add to local (newer)
    local.add_task({"id": "t1", "title": "Local New", "status": "done"})

    local.merge(remote)
    task = local.get_task("t1")
    assert task["title"] == "Local New"


def test_merge_tombstone_wins():
    local = CRDTTaskStore("local")
    remote = CRDTTaskStore("remote")

    local.add_task({"id": "t1"})
    local.delete_task("t1")

    remote.add_task({"id": "t1", "title": "Should be ignored"})
    local.merge(remote)
    assert local.get_task("t1") is None


def test_merge_remote_tombstones():
    local = CRDTTaskStore("local")
    remote = CRDTTaskStore("remote")

    local.add_task({"id": "t1"})
    remote.add_task({"id": "t1"})
    remote.delete_task("t1")

    local.merge(remote)
    assert local.get_task("t1") is None
    assert "t1" in local._tombstones


def test_merge_vector_clocks():
    local = CRDTTaskStore("local")
    remote = CRDTTaskStore("remote")
    local.add_task({"id": "t1"})
    remote.add_task({"id": "t2"})
    local.merge(remote)
    # Local clock should have both replicas
    assert "local" in local._clocks
    assert "remote" in local._clocks


def test_to_json():
    store = CRDTTaskStore("r1")
    store.add_task({"id": "t1", "title": "Test"})
    data = json.loads(store.to_json())
    assert data["replica_id"] == "r1"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["id"] == "t1"
    assert data["tombstones"] == []
    assert "vector_clocks" in data


def test_from_json():
    store = CRDTTaskStore("r1")
    store.add_task({"id": "t1", "title": "Test"})
    store.add_task({"id": "t2"})
    store.delete_task("t2")
    json_str = store.to_json()

    store2 = CRDTTaskStore("r2")
    store2.from_json(json_str)
    assert store2.replica_id == "r1"
    assert store2.get_task("t1") is not None
    assert "t2" in store2._tombstones


def test_get_stats():
    store = CRDTTaskStore("r1")
    store.add_task({"id": "t1"})
    store.add_task({"id": "t2"})
    store.delete_task("t2")
    stats = store.get_stats()
    assert stats["replica_id"] == "r1"
    assert stats["total_tasks"] == 1
    assert stats["tombstones"] == 1
    assert "vector_clock" in stats
    assert "memory_estimate_kb" in stats


def test_get_vector_clock():
    store = CRDTTaskStore("r1")
    store.add_task({"id": "t1"})
    vc = store._get_vector_clock()
    assert "r1" in vc
    assert vc["r1"] >= 1


def test_merge_vector_clocks_method():
    store = CRDTTaskStore("r1")
    store._clocks["r1"] = 5
    merged = store._merge_vector_clocks({"r2": 3, "r1": 2})
    assert merged["r1"] == 5  # max
    assert merged["r2"] == 3


def test_deepcopy_isolation():
    store = CRDTTaskStore()
    task = store.add_task({"id": "t1", "title": "Original"})
    task["title"] = "Modified"
    # Internal state should be unaffected
    assert store.get_task("t1")["title"] == "Original"
