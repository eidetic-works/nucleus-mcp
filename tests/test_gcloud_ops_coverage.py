"""Comprehensive tests for gcloud_ops module."""
import json
import subprocess
import os
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import gcloud_ops
from mcp_server_nucleus.runtime.gcloud_ops import (
    find_gcloud,
    GCloudResult,
    GCloudOps,
    get_gcloud_ops,
    _gcloud_ops,
)


# ── find_gcloud ──────────────────────────────────────────────────

class TestFindGcloud:
    def test_found_in_path(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        result = find_gcloud()
        assert result == "/usr/local/bin/gcloud"

    def test_not_found_anywhere(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        monkeypatch.setattr("os.path.exists", lambda p: False)
        result = find_gcloud()
        assert result is None

    def test_found_in_common_path(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        def mock_exists(p):
            return p == "/opt/homebrew/bin/gcloud"
        monkeypatch.setattr("os.path.exists", mock_exists)
        result = find_gcloud()
        assert result == "/opt/homebrew/bin/gcloud"

    def test_found_in_home_sdk(self, monkeypatch, tmp_path):
        monkeypatch.setattr("shutil.which", lambda name: None)
        sdk_path = str(tmp_path / "google-cloud-sdk" / "bin" / "gcloud")
        def mock_exists(p):
            return p == sdk_path
        monkeypatch.setattr("os.path.exists", mock_exists)
        monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) + p[1:] if p.startswith("~") else p)
        result = find_gcloud()
        assert result == sdk_path


# ── GCloudResult ─────────────────────────────────────────────────

class TestGCloudResult:
    def test_defaults(self):
        r = GCloudResult(success=True)
        assert r.success is True
        assert r.data is None
        assert r.error is None
        assert r.command == ""

    def test_to_dict(self):
        r = GCloudResult(success=True, data={"key": "val"}, error=None, command="gcloud test")
        d = r.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "val"}
        assert d["error"] is None
        assert d["command"] == "gcloud test"

    def test_error_result(self):
        r = GCloudResult(success=False, error="failed", command="gcloud test")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "failed"


# ── GCloudOps ────────────────────────────────────────────────────

class TestGCloudOps:
    def test_init_no_gcloud(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        monkeypatch.setattr("os.path.exists", lambda p: False)
        ops = GCloudOps()
        assert ops.is_available is False
        assert ops.gcloud_path is None

    def test_init_with_gcloud(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        ops = GCloudOps()
        assert ops.is_available is True
        assert ops.gcloud_path == "/usr/local/bin/gcloud"

    def test_init_with_project_env(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        monkeypatch.setenv("GCLOUD_PROJECT", "my-project")
        ops = GCloudOps()
        assert ops.project == "my-project"

    def test_init_with_project_arg(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        ops = GCloudOps(project="custom-project")
        assert ops.project == "custom-project"

    def test_init_default_region(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        ops = GCloudOps()
        assert ops.region == "us-central1"

    def test_init_custom_region(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        ops = GCloudOps(region="europe-west1")
        assert ops.region == "europe-west1"

    # ── _run ───────────────────────────────────────────────────

    def test_run_not_available(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        monkeypatch.setattr("os.path.exists", lambda p: False)
        ops = GCloudOps()
        result = ops._run(["config", "get-value", "project"])
        assert result.success is False
        assert "not found" in result.error

    def test_run_success_json(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([{"name": "svc1"}])
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is True
        assert result.data == [{"name": "svc1"}]

    def test_run_success_text(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "my-project\n"
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops._run(["config", "get-value", "project"], format_json=False)
        assert result.success is True
        assert result.data == "my-project"

    def test_run_failure(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: not authorized"
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is False
        assert "not authorized" in result.error

    def test_run_failure_no_stderr(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is False
        assert "exit code 1" in result.error

    def test_run_timeout(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        monkeypatch.setattr("subprocess.run", MagicMock(side_effect=subprocess.TimeoutExpired(cmd="gcloud", timeout=30)))
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is False
        assert "timed out" in result.error

    def test_run_exception(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        monkeypatch.setattr("subprocess.run", MagicMock(side_effect=Exception("unexpected")))
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is False
        assert "unexpected" in result.error

    def test_run_invalid_json_returns_text(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json{{"
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is True
        assert result.data == "not json{{"

    def test_run_empty_stdout(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops._run(["run", "services", "list"])
        assert result.success is True
        assert result.data == ""

    # ── get_current_project ────────────────────────────────────

    def test_get_current_project(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "my-project\n"
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops.get_current_project()
        assert result.success is True
        assert result.data == "my-project"

    # ── get_account ────────────────────────────────────────────

    def test_get_account(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "user@example.com\n"
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops.get_account()
        assert result.success is True
        assert result.data == "user@example.com"

    # ── list_cloud_run_services ────────────────────────────────

    def test_list_cloud_run_services(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([{"name": "svc1"}])
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps(project="my-project")
        result = ops.list_cloud_run_services()
        assert result.success is True

    def test_list_cloud_run_services_with_project_arg(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([])
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        result = ops.list_cloud_run_services(project="other-project")
        assert result.success is True

    # ── get_cloud_run_service ──────────────────────────────────

    def test_get_cloud_run_service(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"name": "svc1"})
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps(project="my-project")
        result = ops.get_cloud_run_service("svc1")
        assert result.success is True

    # ── get_cloud_run_revisions ────────────────────────────────

    def test_get_cloud_run_revisions(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([{"name": "rev1"}])
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps(project="my-project")
        result = ops.get_cloud_run_revisions("svc1")
        assert result.success is True

    # ── check_auth_status ──────────────────────────────────────

    def test_check_auth_status_available(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "my-project\n"
        mock_result.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_result)
        ops = GCloudOps()
        status = ops.check_auth_status()
        assert status["gcloud_available"] is True
        assert status["project"] == "my-project"

    def test_check_auth_status_not_available(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        monkeypatch.setattr("os.path.exists", lambda p: False)
        ops = GCloudOps()
        status = ops.check_auth_status()
        assert status["gcloud_available"] is False
        assert status["project"] is None
        assert status["account"] is None


# ── get_gcloud_ops ───────────────────────────────────────────────

class TestGetGcloudOps:
    def test_singleton(self, monkeypatch):
        # Reset singleton
        gcloud_ops._gcloud_ops = None
        monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/gcloud")
        ops1 = get_gcloud_ops()
        ops2 = get_gcloud_ops()
        assert ops1 is ops2
        # Cleanup
        gcloud_ops._gcloud_ops = None
