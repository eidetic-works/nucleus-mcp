"""Tests for v0.3.0 — sessions.session_presence.

Per cc-peer 2026-06-09T11:55Z SIGNOFF Q2 CONCUR:
- register_session_pid / unregister_session_pid lifecycle
- is_session_running: PID file present + alive → True
- Stale PID (file exists, process dead) → False
- PID file mode 0o600
- Empty role rejected
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_server_nucleus.sessions import session_presence as sp


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(sp, "_PID_DIR", tmp_path / ".tb")
    # Wipe registered roles set so atexit cleanup doesn't touch tests
    sp._registered_roles.clear()
    yield
    sp._registered_roles.clear()


# ── register / unregister ──────────────────────────────────────────────


def test_register_writes_pid_file(tmp_path):
    path = sp.register_session_pid("cc_tb", pid=12345)
    assert path.exists()
    assert path.read_text().strip() == "12345"
    assert path == tmp_path / ".tb" / "session.cc_tb.pid"


def test_register_writes_pid_file_mode_0o600(tmp_path):
    path = sp.register_session_pid("cc_tb", pid=12345)
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600


def test_register_default_pid_is_os_getpid(tmp_path):
    path = sp.register_session_pid("cc_tb")
    assert path.read_text().strip() == str(os.getpid())


def test_register_empty_role_raises():
    with pytest.raises(ValueError):
        sp.register_session_pid("", pid=12345)


def test_unregister_removes_file(tmp_path):
    sp.register_session_pid("cc_tb", pid=12345)
    path = tmp_path / ".tb" / "session.cc_tb.pid"
    assert path.exists()
    assert sp.unregister_session_pid("cc_tb") is True
    assert not path.exists()


def test_unregister_missing_file_returns_false():
    assert sp.unregister_session_pid("ghost") is False


def test_unregister_empty_role_raises():
    with pytest.raises(ValueError):
        sp.unregister_session_pid("")


# ── is_session_running ─────────────────────────────────────────────────


def test_session_not_running_when_no_pid_file():
    assert sp.is_session_running("ghost") is False


def test_session_running_when_pid_alive():
    sp.register_session_pid("cc_tb", pid=os.getpid())  # self
    assert sp.is_session_running("cc_tb") is True


def test_session_not_running_with_stale_pid(tmp_path):
    """PID file exists but PID has no process → False."""
    sp.register_session_pid("cc_tb", pid=999_999_999)  # implausibly large
    # kill(0) on non-existent pid raises ProcessLookupError (ESRCH)
    assert sp.is_session_running("cc_tb") is False


def test_session_not_running_when_pid_unreadable(tmp_path):
    """PID file has garbage → False."""
    pid_dir = tmp_path / ".tb"
    pid_dir.mkdir(exist_ok=True)
    (pid_dir / "session.cc_tb.pid").write_text("not-a-number")
    assert sp.is_session_running("cc_tb") is False


def test_session_not_running_with_zero_or_negative_pid(tmp_path):
    pid_dir = tmp_path / ".tb"
    pid_dir.mkdir(exist_ok=True)
    (pid_dir / "session.cc_tb.pid").write_text("0")
    assert sp.is_session_running("cc_tb") is False
    (pid_dir / "session.cc_tb.pid").write_text("-1")
    assert sp.is_session_running("cc_tb") is False


def test_session_running_empty_role_returns_false():
    assert sp.is_session_running("") is False


# ── Atomic write ──────────────────────────────────────────────────────


def test_register_writes_atomically_via_tmp_rename(tmp_path, monkeypatch):
    seen_tmp = []
    orig_replace = Path.replace

    def _trace(self, target):
        if str(self).endswith(".tmp"):
            seen_tmp.append(str(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _trace)
    sp.register_session_pid("cc_tb", pid=12345)
    assert any(".tmp" in s for s in seen_tmp)


# ── Module exports ─────────────────────────────────────────────────────


def test_all_exported():
    expected = {
        "register_session_pid",
        "unregister_session_pid",
        "is_session_running",
    }
    assert set(sp.__all__) == expected
