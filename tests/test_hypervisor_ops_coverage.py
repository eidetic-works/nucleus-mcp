"""Coverage tests for mcp_server_nucleus.runtime.hypervisor_ops."""
import os
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.runtime import hypervisor_ops as hops


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch, tmp_path):
    """Reset singletons and set brain path to tmp_path."""
    hops._locker_inst = None
    hops._injector_inst = None
    hops._watchdog_inst = None
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    yield
    hops._locker_inst = None
    hops._injector_inst = None
    hops._watchdog_inst = None


def test_get_locker_singleton():
    locker1 = hops.get_locker()
    locker2 = hops.get_locker()
    assert locker1 is locker2


def test_get_injector_singleton():
    inj1 = hops.get_injector()
    inj2 = hops.get_injector()
    assert inj1 is inj2


def test_get_watchdog_singleton():
    wd1 = hops.get_watchdog()
    wd2 = hops.get_watchdog()
    assert wd1 is wd2


def test_lock_resource_impl_success(monkeypatch):
    fake_locker = mock.MagicMock()
    fake_locker.lock.return_value = True
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    result = hops.lock_resource_impl("/tmp/test.txt")
    assert "LOCKED" in result


def test_lock_resource_impl_failure(monkeypatch):
    fake_locker = mock.MagicMock()
    fake_locker.lock.return_value = False
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    result = hops.lock_resource_impl("/tmp/test.txt")
    assert "FAILED" in result


def test_unlock_resource_impl_no_token():
    result = hops.unlock_resource_impl("/tmp/test.txt")
    assert "DENIED" in result
    assert "token" in result.lower()


def test_unlock_resource_impl_invalid_token(monkeypatch):
    fake_manager = mock.MagicMock()
    fake_manager.validate_token.return_value = (False, "invalid token")
    monkeypatch.setattr("mcp_server_nucleus.runtime.auth.ipc_provider.get_ipc_auth_manager", lambda: fake_manager)
    result = hops.unlock_resource_impl("/tmp/test.txt", token_id="bad")
    assert "DENIED" in result


def test_unlock_resource_impl_success(monkeypatch):
    fake_manager = mock.MagicMock()
    fake_manager.validate_token.return_value = (True, None)
    monkeypatch.setattr("mcp_server_nucleus.runtime.auth.ipc_provider.get_ipc_auth_manager", lambda: fake_manager)
    fake_locker = mock.MagicMock()
    fake_locker.unlock.return_value = True
    fake_locker._internal_secret = "secret"
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    result = hops.unlock_resource_impl("/tmp/test.txt", token_id="good")
    assert "UNLOCKED" in result


def test_unlock_resource_impl_unlock_fails(monkeypatch):
    fake_manager = mock.MagicMock()
    fake_manager.validate_token.return_value = (True, None)
    monkeypatch.setattr("mcp_server_nucleus.runtime.auth.ipc_provider.get_ipc_auth_manager", lambda: fake_manager)
    fake_locker = mock.MagicMock()
    fake_locker.unlock.return_value = False
    fake_locker._internal_secret = "secret"
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    result = hops.unlock_resource_impl("/tmp/test.txt", token_id="good")
    assert "FAILED" in result


def test_set_hypervisor_mode_red(monkeypatch):
    fake_injector = mock.MagicMock()
    monkeypatch.setattr(hops, "get_injector", lambda: fake_injector)
    result = hops.set_hypervisor_mode_impl("red")
    assert "RED" in result
    fake_injector.inject_identity.assert_called_with("RED TEAM", "#ff0000")


def test_set_hypervisor_mode_blue(monkeypatch):
    fake_injector = mock.MagicMock()
    monkeypatch.setattr(hops, "get_injector", lambda: fake_injector)
    result = hops.set_hypervisor_mode_impl("blue")
    assert "BLUE" in result
    fake_injector.inject_identity.assert_called_with("BLUE TEAM", "#007acc")


def test_set_hypervisor_mode_reset(monkeypatch):
    fake_injector = mock.MagicMock()
    monkeypatch.setattr(hops, "get_injector", lambda: fake_injector)
    result = hops.set_hypervisor_mode_impl("reset")
    assert "RESET" in result
    fake_injector.reset_identity.assert_called_once()


def test_set_hypervisor_mode_invalid(monkeypatch):
    fake_injector = mock.MagicMock()
    monkeypatch.setattr(hops, "get_injector", lambda: fake_injector)
    result = hops.set_hypervisor_mode_impl("purple")
    assert "Invalid" in result


def test_nucleus_list_directory_impl_outside_workspace(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    result = hops.nucleus_list_directory_impl("/etc")
    assert "BLOCKED" in result


def test_nucleus_list_directory_impl_not_found(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    result = hops.nucleus_list_directory_impl(str(tmp_path / "nonexistent"))
    assert "not found" in result.lower() or "ERROR" in result


def test_nucleus_list_directory_impl_success(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = tmp_path / "target_dir"
    target.mkdir()
    (target / "file1.txt").write_text("x")
    (target / "file2.txt").write_text("y")
    fake_locker = mock.MagicMock()
    fake_locker.is_locked.return_value = False
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    result = hops.nucleus_list_directory_impl(str(target))
    assert "file1.txt" in result
    assert "file2.txt" in result


def test_nucleus_list_directory_impl_with_locked(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = tmp_path / "target_dir"
    target.mkdir()
    (target / "locked.txt").write_text("x")
    fake_locker = mock.MagicMock()
    fake_locker.is_locked.return_value = True
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    result = hops.nucleus_list_directory_impl(str(target))
    assert "LOCKED" in result


def test_nucleus_delete_file_impl_outside_workspace(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    emit = mock.MagicMock()
    result = hops.nucleus_delete_file_impl("/etc/passwd", emit_event_fn=emit)
    assert "BLOCKED" in result
    emit.assert_called_once()


def test_nucleus_delete_file_impl_no_confirm(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = tmp_path / "file.txt"
    target.write_text("x")
    result = hops.nucleus_delete_file_impl(str(target))
    assert "HITL GATE" in result


def test_nucleus_delete_file_impl_locked(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = tmp_path / "file.txt"
    target.write_text("x")
    fake_locker = mock.MagicMock()
    fake_locker.is_locked.return_value = True
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    emit = mock.MagicMock()
    result = hops.nucleus_delete_file_impl(str(target), emit_event_fn=emit, confirm=True)
    assert "BLOCKED" in result
    assert "locked" in result.lower()
    emit.assert_called_once()


def test_nucleus_delete_file_impl_not_found(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    result = hops.nucleus_delete_file_impl(str(tmp_path / "nope.txt"), confirm=True)
    assert "not found" in result.lower() or "ERROR" in result


def test_nucleus_delete_file_impl_success(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = tmp_path / "file.txt"
    target.write_text("x")
    fake_locker = mock.MagicMock()
    fake_locker.is_locked.return_value = False
    monkeypatch.setattr(hops, "get_locker", lambda: fake_locker)
    emit = mock.MagicMock()
    result = hops.nucleus_delete_file_impl(str(target), emit_event_fn=emit, confirm=True)
    assert "SUCCESS" in result
    assert not target.exists()
    emit.assert_called_once()


def test_nucleus_delete_file_impl_exception(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    result = hops.nucleus_delete_file_impl("\x00bad\x00path", confirm=True)
    assert "ERROR" in result


def test_watch_resource_impl_outside_workspace(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    result = hops.watch_resource_impl("/etc")
    assert "BLOCKED" in result


def test_watch_resource_impl_success(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = tmp_path / "file.txt"
    target.write_text("x")
    fake_watchdog = mock.MagicMock()
    monkeypatch.setattr(hops, "get_watchdog", lambda: fake_watchdog)
    result = hops.watch_resource_impl(str(target))
    assert "WATCHING" in result
    fake_watchdog.protect.assert_called_once()


def test_hypervisor_status_impl(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    fake_watchdog = mock.MagicMock()
    fake_watchdog.observer.is_alive.return_value = True
    fake_watchdog.protected_paths = ["/tmp/p1", "/tmp/p2"]
    monkeypatch.setattr(hops, "get_watchdog", lambda: fake_watchdog)
    result = hops.hypervisor_status_impl()
    assert "HYPERVISOR" in result
    assert "/tmp/p1" in result
    assert "/tmp/p2" in result
    assert "Active" in result


def test_autostart_watchdog_ci(monkeypatch):
    """autostart_watchdog skips in CI environment."""
    monkeypatch.setenv("CI", "true")
    # Should return without calling get_watchdog
    with mock.patch.object(hops, "get_watchdog") as fake_gw:
        hops.autostart_watchdog()
        fake_gw.assert_not_called()


def test_autostart_watchdog_pytest(monkeypatch):
    """autostart_watchdog skips in pytest environment."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test")
    with mock.patch.object(hops, "get_watchdog") as fake_gw:
        hops.autostart_watchdog()
        fake_gw.assert_not_called()


def test_autostart_watchdog_skip_env(monkeypatch):
    """autostart_watchdog skips when NUCLEUS_SKIP_AUTOSTART=true."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("NUCLEUS_SKIP_AUTOSTART", "true")
    with mock.patch.object(hops, "get_watchdog") as fake_gw:
        hops.autostart_watchdog()
        fake_gw.assert_not_called()


def test_autostart_watchdog_exception(monkeypatch):
    """autostart_watchdog logs warning on exception."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("NUCLEUS_SKIP_AUTOSTART", raising=False)
    fake_wd = mock.MagicMock()
    fake_wd.start.side_effect = RuntimeError("fail")
    with mock.patch.object(hops, "get_watchdog", return_value=fake_wd):
        # Should not raise
        hops.autostart_watchdog()
