"""
Centralized secret retrieval with GCP Secret Manager support.

Usage:
    from mcp_server_nucleus.runtime.secrets import get_telegram_token, get_telegram_chat_id

Production (GCP): Reads from Secret Manager with in-process caching.
Local dev: Falls back to environment variables.

The google-cloud-secret-manager package is a lazy/optional dependency —
the system works without it installed.
"""

import os
import threading
import warnings
from typing import Optional


_cache: dict = {}
_cache_lock = threading.Lock()


def _get_sm_client():
    """Lazy-load and return a GCP Secret Manager client.

    Raises ImportError if google-cloud-secret-manager is not installed.
    Extracted as a separate function to allow easy mocking in tests.
    """
    from google.cloud import secretmanager
    return secretmanager.SecretManagerServiceClient()


def get_secret(
    name: str,
    project_id: Optional[str] = None,
    version: str = "latest",
    use_cache: bool = True,
) -> str:
    """Fetch a secret value with GCP Secret Manager fallback to env var.

    Resolution order:
        1. In-process cache (if use_cache=True)
        2. Environment variable with the same name
        3. GCP Secret Manager (lazy import, optional dependency)

    Args:
        name: Secret name (also used as env var name).
        project_id: GCP project ID. Defaults to GCP_PROJECT_ID or
                     GOOGLE_CLOUD_PROJECT env var.
        version: Secret version (default "latest").
        use_cache: Whether to cache the resolved value in-process.

    Returns:
        The secret value, or empty string if unavailable.
    """
    cache_key = f"{name}:{version}"

    if use_cache:
        with _cache_lock:
            if cache_key in _cache:
                return _cache[cache_key]

    # Fast path: environment variable
    env_val = os.environ.get(name, "")
    if env_val:
        if use_cache:
            with _cache_lock:
                _cache[cache_key] = env_val
        return env_val

    # Slow path: GCP Secret Manager (optional)
    project = project_id or os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        return ""

    try:
        client = _get_sm_client()
    except ImportError:
        warnings.warn(
            f"google-cloud-secret-manager not installed. "
            f"Cannot fetch '{name}' from Secret Manager. "
            f"Set the {name} environment variable instead.",
            stacklevel=2,
        )
        return ""

    try:
        resource = f"projects/{project}/secrets/{name}/versions/{version}"
        response = client.access_secret_version(request={"name": resource})
        value = response.payload.data.decode("UTF-8")

        if use_cache:
            with _cache_lock:
                _cache[cache_key] = value
        return value
    except Exception as e:
        warnings.warn(
            f"Failed to fetch '{name}' from GCP Secret Manager: {e}. "
            f"Falling back to empty string.",
            stacklevel=2,
        )
        return ""


def get_telegram_token() -> str:
    """Get the Telegram bot token from Secret Manager or env var."""
    return get_secret("TELEGRAM_BOT_TOKEN")


def get_telegram_chat_id() -> str:
    """Get the Telegram chat ID from Secret Manager or env var."""
    return get_secret("TELEGRAM_CHAT_ID")


def clear_cache() -> None:
    """Clear the in-process secret cache. Useful for testing."""
    with _cache_lock:
        _cache.clear()
