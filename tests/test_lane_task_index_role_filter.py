"""The watcher's task index must not hide tasks that are open to any agent.

Why this exists: 13 sweep tasks sat PENDING in the store while `nucleus lane
status` reported them NOT_SEEDED -- a status meaning "this task was never
created" applied to tasks that existed and were queued. _task_index() kept only
tasks whose required_role equalled the lane's role, but _add_task documents an
empty required_role as "any agent can pull". The filter dropped precisely the
tasks open to everyone.

The docstring on _task_index already records an earlier version of this same
bug (an ID-prefix filter that never matched). Same shape, different column, and
both surfaced as NOT_SEEDED -- a report that says the opposite of what is true.
"""

from unittest.mock import MagicMock, patch

from mcp_server_nucleus.runtime.lane.control_watcher import ControlWatcher


def _watcher(role="lane-g1"):
    w = ControlWatcher.__new__(ControlWatcher)
    w.config = MagicMock()
    w.config.role = role
    w.config.repo_root = MagicMock()
    return w


def _index(tasks, role="lane-g1"):
    with patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=tasks):
        return _watcher(role)._task_index()


def test_a_task_open_to_any_agent_is_visible():
    """THE BUG: empty required_role means any agent, not 'belongs to nobody'."""
    idx = _index([{"id": "sweep_x", "status": "PENDING", "required_role": ""}])
    assert "sweep_x" in idx, "a task open to any agent was hidden from the index"


def test_a_missing_required_role_key_is_visible():
    """Same contract when the key is absent rather than empty."""
    assert "sweep_y" in _index([{"id": "sweep_y", "status": "PENDING"}])


def test_a_whitespace_role_counts_as_open():
    """OPPOSED-adjacent: ' ' is not a role. Treating it as one reintroduces the
    bug for anything that round-trips through a text field."""
    assert "sweep_z" in _index([{"id": "sweep_z", "status": "PENDING",
                                 "required_role": "   "}])


def test_a_task_scoped_to_ANOTHER_role_is_still_excluded():
    """OPPOSED, load-bearing: the filter must still filter. If this passes as
    visible, the fix has simply removed role scoping and one lane will report
    and claim another lane's work."""
    idx = _index([{"id": "peer_task", "status": "PENDING",
                   "required_role": "lane-peer"}])
    assert "peer_task" not in idx, "role scoping was removed, not fixed"


def test_this_lanes_own_role_still_matches():
    assert "mine" in _index([{"id": "mine", "status": "DONE",
                              "required_role": "lane-g1"}])
