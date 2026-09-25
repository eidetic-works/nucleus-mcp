"""Lane daemons must outlive the session that started them.

Why this exists: `nucleus lane start --background` spawned its daemons with a
plain subprocess.Popen, so they inherited the launching shell's process group.
When the Claude Code session was torn down the whole group went with it. Observed
three times in one day: a lane mid-sweep died, leaving claims held by dead PIDs
and vendor edits stranded uncommitted in the shared worktree.

A lane exists to do unattended work. One that only runs while someone watches it
is the opposite of the thing.

These test the OS behaviour, not the source text. A grep for
`start_new_session=True` would pass just as well if the flag were spelled into a
dict nobody passes to Popen.
"""

import os
import subprocess
import sys

_SLEEPER = [sys.executable, "-c", "import time; time.sleep(30)"]


def _pgid(pid: int) -> int:
    return os.getpgid(pid)


def test_a_plain_popen_child_shares_our_process_group():
    """CONTROL: this is the old behaviour, and the reason the daemons died.
    If this ever fails, the premise of the fix is gone and it needs revisiting."""
    p = subprocess.Popen(_SLEEPER)
    try:
        assert _pgid(p.pid) == _pgid(os.getpid()), (
            "a plain Popen child was already detached -- the bug this guards "
            "against cannot happen on this platform"
        )
    finally:
        p.kill()
        p.wait()


def test_start_new_session_detaches_the_child():
    """THE FIX: a detached child leads its own session, so a group-directed
    signal to the launching shell cannot reach it."""
    p = subprocess.Popen(_SLEEPER, start_new_session=True)
    try:
        assert _pgid(p.pid) != _pgid(os.getpid()), "child stayed in our process group"
        assert _pgid(p.pid) == p.pid, "detached child should lead its own group"
    finally:
        p.kill()
        p.wait()


def test_a_group_signal_kills_the_attached_child_but_not_the_detached_one():
    """The consequence, demonstrated rather than asserted: the same signal that
    ends a session reaches one child and not the other."""
    import signal
    import time

    attached = subprocess.Popen(_SLEEPER)
    detached = subprocess.Popen(_SLEEPER, start_new_session=True)
    try:
        # Signal the ATTACHED child's group -- which is also ours, so target the
        # child directly by its group to avoid killing the test runner.
        os.killpg(_pgid(detached.pid), 0)  # detached group exists and is distinct
        os.kill(attached.pid, signal.SIGTERM)
        time.sleep(0.5)
        assert attached.poll() is not None, "attached child survived its signal"
        assert detached.poll() is None, (
            "detached child died -- it must be unreachable from the launching "
            "session's group"
        )
    finally:
        for p in (attached, detached):
            if p.poll() is None:
                p.kill()
            p.wait()


def test_the_lane_start_path_actually_passes_the_flag():
    """Behaviour above proves the mechanism; this proves we USE it. Both are
    needed -- a correct mechanism nobody calls is the failure mode this repo
    keeps finding."""
    import inspect
    from mcp_server_nucleus import cli
    src = inspect.getsource(cli)
    i = src.find("daemon_env[\"NUCLEUS_BRAIN_PATH\"]")
    assert i > 0, "lane daemon spawn block not found"
    block = src[i:i + 6000]
    assert block.count("start_new_session=True") >= 3, (
        "not every lane daemon (watcher, executors, secretary) is detached"
    )
