"""Coverage tests for mcp_server_nucleus/core/egress_proxy.py — the egress
firewall allowlist, proxied HTTP fetch, and proxied pip install."""
import json
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.core import egress_proxy


# ── is_domain_allowed ───────────────────────────────────────────────

class TestIsDomainAllowed:
    def test_allowed_exact(self):
        assert egress_proxy.is_domain_allowed("https://pypi.org/x") is True

    def test_allowed_subdomain(self):
        assert egress_proxy.is_domain_allowed("https://docs.python.org/3/") is True

    def test_allowed_github_raw(self):
        assert egress_proxy.is_domain_allowed("https://raw.githubusercontent.com/a/b") is True

    def test_blocked_domain(self):
        assert egress_proxy.is_domain_allowed("https://evil.com/exfil") is False

    def test_empty_netloc(self):
        assert egress_proxy.is_domain_allowed("not-a-url") is False

    def test_subdomain_of_allowed(self):
        assert egress_proxy.is_domain_allowed("https://sub.pypi.org/x") is True

    def test_lookalike_domain(self):
        # "evilpypi.org" should NOT match "pypi.org"
        assert egress_proxy.is_domain_allowed("https://evilpypi.org/x") is False

    def test_exception_returns_false(self):
        with patch("urllib.parse.urlparse", side_effect=ValueError("bad")):
            assert egress_proxy.is_domain_allowed("https://x") is False


# ── nucleus_curl_impl ───────────────────────────────────────────────

class TestNucleusCurlImpl:
    def test_blocked_domain(self):
        r = json.loads(egress_proxy.nucleus_curl_impl("https://evil.com/x"))
        assert r["success"] is False
        assert "Egress Firewall Blocked" in r["error"]

    def test_success(self):
        fake_resp = MagicMock()
        fake_resp.getcode.return_value = 200
        fake_resp.read.return_value = b"hello world"
        fake_resp.__enter__ = MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_resp):
            r = json.loads(egress_proxy.nucleus_curl_impl("https://pypi.org/x"))
        assert r["success"] is True
        assert r["status_code"] == 200
        assert r["data"] == "hello world"

    def test_non_utf8_response(self):
        fake_resp = MagicMock()
        fake_resp.getcode.return_value = 200
        fake_resp.read.return_value = b"\xff\xfe\x00\x01"
        fake_resp.__enter__ = MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_resp):
            r = json.loads(egress_proxy.nucleus_curl_impl("https://pypi.org/x"))
        assert r["success"] is True
        assert "BASE64_ENCODED" in r["data"]

    def test_large_response_capped(self):
        fake_resp = MagicMock()
        fake_resp.getcode.return_value = 200
        fake_resp.read.return_value = b"x" * 200_000
        fake_resp.__enter__ = MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_resp):
            r = json.loads(egress_proxy.nucleus_curl_impl("https://pypi.org/x"))
        assert r["success"] is True
        assert len(r["data"]) == 100_000

    def test_request_exception(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            r = json.loads(egress_proxy.nucleus_curl_impl("https://pypi.org/x"))
        assert r["success"] is False
        assert "refused" in r["error"]

    def test_custom_method(self):
        fake_resp = MagicMock()
        fake_resp.getcode.return_value = 204
        fake_resp.read.return_value = b""
        fake_resp.__enter__ = MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_resp) as m:
            egress_proxy.nucleus_curl_impl("https://pypi.org/x", method="DELETE")
        req = m.call_args[0][0]
        assert req.get_method() == "DELETE"


# ── nucleus_pip_install_impl ────────────────────────────────────────

class TestNucleusPipInstallImpl:
    def test_invalid_package_name(self):
        r = json.loads(egress_proxy.nucleus_pip_install_impl("bad package; rm -rf /"))
        assert r["success"] is False
        assert "Invalid" in r["error"]

    def test_valid_package_success(self):
        result = MagicMock(returncode=0, stdout="Successfully installed foo")
        with patch("subprocess.run", return_value=result):
            r = json.loads(egress_proxy.nucleus_pip_install_impl("foo"))
        assert r["success"] is True
        assert "Successfully installed" in r["output"]

    def test_pip_install_failure(self):
        result = MagicMock(returncode=1, stdout="", stderr="ERROR: not found")
        with patch("subprocess.run", return_value=result):
            r = json.loads(egress_proxy.nucleus_pip_install_impl("nonexistent-pkg"))
        assert r["success"] is False
        assert "not found" in r["error"]

    def test_pip_install_exception(self):
        with patch("subprocess.run", side_effect=TimeoutError("timed out")):
            r = json.loads(egress_proxy.nucleus_pip_install_impl("foo"))
        assert r["success"] is False
        assert "timed out" in r["error"]

    def test_package_with_version_spec(self):
        result = MagicMock(returncode=0, stdout="ok")
        with patch("subprocess.run", return_value=result) as m:
            r = json.loads(egress_proxy.nucleus_pip_install_impl("foo>=1.0"))
        assert r["success"] is True
        cmd = m.call_args[0][0]
        assert "foo>=1.0" in cmd
