"""
Tests for the centralized secrets module (secrets.py).

Covers:
- Environment variable resolution
- In-process caching
- GCP Secret Manager integration (mocked)
- Graceful fallback when GCP SDK not installed
- get_telegram_token / get_telegram_chat_id helpers
- Thread safety
"""

import os
import threading
import warnings
from unittest import mock

import pytest

from mcp_server_nucleus.runtime.secrets import (
    get_secret,
    get_telegram_token,
    get_telegram_chat_id,
    clear_cache,
    _cache,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear the secret cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


# ============================================================
# Environment variable resolution
# ============================================================

class TestEnvVarResolution:
    """Secrets should resolve from environment variables first."""

    def test_returns_env_var_value(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "env-value-123")
        assert get_secret("MY_SECRET") == "env-value-123"

    def test_returns_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        assert get_secret("MY_SECRET") == ""

    def test_empty_env_var_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "")
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        assert get_secret("MY_SECRET") == ""

    def test_env_var_takes_priority_over_gcp(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "from-env")
        monkeypatch.setenv("GCP_PROJECT_ID", "my-project")
        # Even with GCP configured, env var wins
        assert get_secret("MY_SECRET") == "from-env"


# ============================================================
# Caching behavior
# ============================================================

class TestCaching:
    """In-process cache should avoid redundant lookups."""

    def test_cached_value_returned(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "cached-val")
        assert get_secret("MY_SECRET") == "cached-val"
        # Change env var — cached value should still be returned
        monkeypatch.setenv("MY_SECRET", "new-val")
        assert get_secret("MY_SECRET") == "cached-val"

    def test_cache_bypass(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "v1")
        assert get_secret("MY_SECRET", use_cache=True) == "v1"
        monkeypatch.setenv("MY_SECRET", "v2")
        assert get_secret("MY_SECRET", use_cache=False) == "v2"

    def test_clear_cache(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "v1")
        get_secret("MY_SECRET")
        monkeypatch.setenv("MY_SECRET", "v2")
        clear_cache()
        assert get_secret("MY_SECRET") == "v2"

    def test_different_versions_cached_separately(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "env-val")
        get_secret("MY_SECRET", version="1")
        get_secret("MY_SECRET", version="2")
        assert "MY_SECRET:1" in _cache
        assert "MY_SECRET:2" in _cache


# ============================================================
# GCP Secret Manager (mocked)
# ============================================================

def _make_mock_client(payload_bytes=b"gcp-secret-value", side_effect=None):
    """Helper: create a mock SecretManagerServiceClient."""
    mock_response = mock.MagicMock()
    mock_response.payload.data = payload_bytes
    mock_client = mock.MagicMock()
    if side_effect:
        mock_client.access_secret_version.side_effect = side_effect
    else:
        mock_client.access_secret_version.return_value = mock_response
    return mock_client


SM_CLIENT_PATH = "mcp_server_nucleus.runtime.secrets._get_sm_client"


class TestGCPSecretManager:
    """Test GCP Secret Manager integration with mocked _get_sm_client."""

    def test_fetches_from_gcp_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

        mock_client = _make_mock_client(b"gcp-secret-value")

        with mock.patch(SM_CLIENT_PATH, return_value=mock_client):
            result = get_secret("TELEGRAM_BOT_TOKEN", use_cache=False)

        assert result == "gcp-secret-value"
        mock_client.access_secret_version.assert_called_once_with(
            request={"name": "projects/test-project/secrets/TELEGRAM_BOT_TOKEN/versions/latest"}
        )

    def test_custom_version(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        monkeypatch.setenv("GCP_PROJECT_ID", "proj-1")

        mock_client = _make_mock_client(b"v3-value")

        with mock.patch(SM_CLIENT_PATH, return_value=mock_client):
            result = get_secret("MY_SECRET", version="3", use_cache=False)

        assert result == "v3-value"
        mock_client.access_secret_version.assert_called_once_with(
            request={"name": "projects/proj-1/secrets/MY_SECRET/versions/3"}
        )

    def test_custom_project_id(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

        mock_client = _make_mock_client(b"val")

        with mock.patch(SM_CLIENT_PATH, return_value=mock_client):
            result = get_secret("MY_SECRET", project_id="explicit-proj", use_cache=False)

        assert result == "val"
        mock_client.access_secret_version.assert_called_once_with(
            request={"name": "projects/explicit-proj/secrets/MY_SECRET/versions/latest"}
        )

    def test_gcp_error_returns_empty(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        monkeypatch.setenv("GCP_PROJECT_ID", "proj")

        mock_client = _make_mock_client(side_effect=Exception("GCP error"))

        with mock.patch(SM_CLIENT_PATH, return_value=mock_client):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = get_secret("MY_SECRET", use_cache=False)

        assert result == ""
        assert any("GCP error" in str(warning.message) for warning in w)

    def test_google_cloud_project_env_var(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "alt-project")

        mock_client = _make_mock_client(b"alt-val")

        with mock.patch(SM_CLIENT_PATH, return_value=mock_client):
            result = get_secret("MY_SECRET", use_cache=False)

        assert result == "alt-val"


# ============================================================
# Missing GCP SDK
# ============================================================

class TestMissingGCPSDK:
    """Graceful fallback when google-cloud-secret-manager is not installed."""

    def test_warns_when_sdk_missing(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        monkeypatch.setenv("GCP_PROJECT_ID", "proj")

        with mock.patch(SM_CLIENT_PATH, side_effect=ImportError("No module")):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = get_secret("MY_SECRET", use_cache=False)

        assert result == ""
        assert any("not installed" in str(warning.message) for warning in w)


# ============================================================
# Convenience helpers
# ============================================================

class TestConvenienceHelpers:
    """Test get_telegram_token and get_telegram_chat_id."""

    def test_get_telegram_token(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok-12345")
        assert get_telegram_token() == "tok-12345"

    def test_get_telegram_chat_id(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "99999")
        assert get_telegram_chat_id() == "99999"

    def test_telegram_token_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        assert get_telegram_token() == ""

    def test_telegram_chat_id_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        assert get_telegram_chat_id() == ""


# ============================================================
# Thread safety
# ============================================================

class TestThreadSafety:
    """Cache operations should be thread-safe."""

    def test_concurrent_access(self, monkeypatch):
        monkeypatch.setenv("THREAD_SECRET", "safe-val")
        results = []
        errors = []

        def worker():
            try:
                for _ in range(50):
                    val = get_secret("THREAD_SECRET")
                    results.append(val)
                    clear_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert all(v == "safe-val" for v in results)
