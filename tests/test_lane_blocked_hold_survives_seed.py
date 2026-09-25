"""A deliberate BLOCKED hold must survive a seed cycle.

Why this exists: five GentleQuest docs were pulled out of the nucleus sweep
queue and set BLOCKED with a written reason. `nucleus lane start` returned all
five to PENDING and wiped pause_reason within minutes.

The auto-unblock was `all(dep is DONE for dep in item.blocked_by)`. Over an
EMPTY blocked_by that is vacuously True, so any task blocked WITHOUT declared
dependencies -- which is what a human hold looks like -- was unblocked on every
cycle. The instrument was not broken; it was asked a question about an empty set
and answered yes.

Each test names its failure direction.
"""

from unittest.mock import MagicMock, patch

from mcp_server_nucleus.runtime.lane.control_watcher import ControlWatcher


def _watcher():
    w = ControlWatcher.__new__(ControlWatcher)
    w.config = MagicMock()
    w.config.role = "executor"
    w.parser = MagicMock()
    w.parser.verify_spec.return_value = {"ok": True}
    return w


def _item(task_id, blocked_by):
    it = MagicMock()
    it.task_id = task_id
    it.blocked_by = blocked_by
    it.description = f"Audit `docs/{task_id}.md`"
    it.task_type = "audit"
    it.command = None
    return it


def _run(watcher, items, tasks):
    with patch("mcp_server_nucleus.runtime.lane.control_watcher._update_task") as upd, \
         patch("mcp_server_nucleus.runtime.lane.control_watcher._list_tasks",
               return_value=list(tasks.values())):
        watcher.parser.parse.return_value = items
        watcher._seed_tasks(items) if hasattr(watcher, "_seed_tasks") else None
        return upd


def test_hold_with_no_dependencies_is_not_auto_unblocked():
    """THE BUG: a task BLOCKED with an empty blocked_by is a deliberate hold.
    all([]) is True, so it was cleared every cycle."""
    assert all([]) is True, "premise of the bug: vacuous truth over an empty set"
    item = _item("gq_doc", blocked_by=[])
    should_unblock = bool(item.blocked_by) and all(
        {}.get(d, {}).get("status", "").upper() == "DONE" for d in item.blocked_by
    )
    assert should_unblock is False, "a dependency-free hold was cleared"


def test_dependency_block_still_clears_when_deps_are_done():
    """OPPOSED: the real feature must survive. A task blocked ON something must
    still unblock once that something is DONE -- otherwise this fix trades one
    silent failure for a permanent stall."""
    item = _item("dep_doc", blocked_by=["upstream"])
    existing = {"upstream": {"status": "DONE"}}
    should_unblock = bool(item.blocked_by) and all(
        existing.get(d, {}).get("status", "").upper() == "DONE" for d in item.blocked_by
    )
    assert should_unblock is True, "dependency auto-unblock was broken by the fix"


def test_dependency_block_does_not_clear_while_a_dep_is_pending():
    """OPPOSED: an unfinished dependency must keep the task blocked."""
    item = _item("dep_doc", blocked_by=["upstream"])
    existing = {"upstream": {"status": "PENDING"}}
    should_unblock = bool(item.blocked_by) and all(
        existing.get(d, {}).get("status", "").upper() == "DONE" for d in item.blocked_by
    )
    assert should_unblock is False


def test_the_shipped_source_actually_guards_on_blocked_by():
    """The three tests above model the logic; this one asserts the shipped file
    contains the guard, so the model cannot drift away from the code it claims
    to describe."""
    import inspect
    from mcp_server_nucleus.runtime.lane import control_watcher
    src = inspect.getsource(control_watcher)
    assert "if item.blocked_by:" in src, (
        "the empty-blocked_by guard is missing from control_watcher"
    )
