"""Tests for v0.3.0 Layer 2 — mcp_server_nucleus.org.discovery.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 2
(spec lines 97-120) + op-assistant 2026-06-09T09:15Z amendment
(build INTO nucleus, not standalone scripts/). 13 read-only endpoint
wrappers — each must use Bearer auth, hit the correct URL, and pass
query/path params correctly.

Coverage:
- Each of 13 endpoint wrappers: URL + auth + params
- Shared GET helper: bearer required, raises on non-2xx
- Shared POST helper: same shape for batch-branch-status
- Pseudonymity: bearer never logged at any level
- urlencode + quote for path/query safety
- Read-only audit: no destructive HTTP verbs in production code
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.org import discovery as od


@pytest.fixture(autouse=True)
def _stub_curl():
    """Inject MagicMock for curl_cffi so tests work without real dep."""
    real = od._curl_requests
    od._curl_requests = MagicMock()
    yield
    od._curl_requests = real


def _ok_resp(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


def _capture_get(payload=None):
    mock = MagicMock(return_value=_ok_resp(payload or {"ok": True}))
    od._curl_requests.get = mock
    return mock


def _capture_post(payload=None):
    mock = MagicMock(return_value=_ok_resp(payload or {"ok": True}))
    od._curl_requests.post = mock
    return mock


def _called_url(mock):
    args = mock.call_args
    if args.args:
        return args.args[0]
    return args.kwargs.get("url")


def _called_headers(mock):
    return mock.call_args.kwargs["headers"]


# ── Shared GET helper ────────────────────────────────────────────────────


def test_get_json_requires_bearer():
    with pytest.raises(od.DiscoveryError):
        od._get_json("https://x", bearer="")


def test_get_json_raises_on_non_2xx():
    od._curl_requests.get = MagicMock(return_value=_ok_resp({}, status=403))
    with pytest.raises(od.DiscoveryError):
        od._get_json("https://x/y", bearer="b")


def test_get_json_includes_bearer_anthropic_version_accept():
    mock = _capture_get()
    od._get_json("https://claude.ai/api/x", bearer="STUB-OAT-bearer")
    headers = _called_headers(mock)
    assert headers["Authorization"] == "Bearer STUB-OAT-bearer"
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["Accept"] == "application/json"


# ── 13 endpoint wrappers — URL shape verification ───────────────────────


def test_get_chat_conversations_url_shape():
    mock = _capture_get()
    od.get_chat_conversations("903554b9-org", bearer="b", limit=42, starred=True)
    url = _called_url(mock)
    assert "claude.ai/api/organizations/903554b9-org/chat_conversations_v2" in url
    assert "limit=42" in url
    assert "starred=true" in url


def test_get_chat_conversations_starred_false_default():
    mock = _capture_get()
    od.get_chat_conversations("org-x", bearer="b")
    url = _called_url(mock)
    assert "starred=false" in url
    assert "limit=30" in url


def test_get_cowork_settings_url_shape():
    mock = _capture_get()
    od.get_cowork_settings("org-x", bearer="b")
    assert _called_url(mock) == "https://claude.ai/api/organizations/org-x/cowork_settings"


def test_get_mcp_bootstrap_url_shape():
    mock = _capture_get()
    od.get_mcp_bootstrap("org-x", bearer="b")
    assert _called_url(mock) == "https://claude.ai/api/organizations/org-x/mcp/v2/bootstrap"


def test_get_memory_url_shape_read_only():
    od._curl_requests.post = MagicMock()
    mock = _capture_get()
    od.get_memory("org-x", bearer="b")
    url = _called_url(mock)
    assert url == "https://claude.ai/api/organizations/org-x/memory"
    assert od._curl_requests.get.called
    assert not od._curl_requests.post.called


def test_get_memory_settings_url_shape():
    od._curl_requests.post = MagicMock()
    mock = _capture_get()
    od.get_memory_settings("org-x", bearer="b")
    assert _called_url(mock) == "https://claude.ai/api/organizations/org-x/memory/settings"


def test_get_projects_url_shape_with_query():
    mock = _capture_get()
    od.get_projects("org-x", bearer="b", include_harmony=True, limit=200)
    url = _called_url(mock)
    assert "claude.ai/api/organizations/org-x/projects" in url
    assert "include_harmony_projects=true" in url
    assert "limit=200" in url


def test_get_projects_include_harmony_false():
    mock = _capture_get()
    od.get_projects("org-x", bearer="b", include_harmony=False)
    url = _called_url(mock)
    assert "include_harmony_projects=false" in url


def test_get_plugins_enabled_state_url_shape():
    mock = _capture_get()
    od.get_plugins_enabled_state("org-x", bearer="b")
    assert _called_url(mock) == "https://claude.ai/api/organizations/org-x/plugins/enabled-state"


def test_list_plugins_url_shape():
    mock = _capture_get()
    od.list_plugins("org-x", bearer="b", installation_preference="manual", limit=50)
    url = _called_url(mock)
    assert "claude.ai/api/organizations/org-x/plugins/list-plugins" in url
    assert "installation_preference=manual" in url
    assert "limit=50" in url


def test_get_notification_preferences_url_shape():
    mock = _capture_get()
    od.get_notification_preferences("org-x", bearer="b")
    assert _called_url(mock) == "https://claude.ai/api/organizations/org-x/notification/preferences"


def test_get_overage_spend_limit_url_shape():
    mock = _capture_get()
    od.get_overage_spend_limit("org-x", bearer="b")
    assert _called_url(mock) == "https://claude.ai/api/organizations/org-x/overage_spend_limit"


def test_get_dxt_extension_versions_url_shape():
    mock = _capture_get()
    od.get_dxt_extension_versions("org-x", "ext-abc123", bearer="b")
    url = _called_url(mock)
    assert url == "https://claude.ai/api/organizations/org-x/dxt/extensions/ext-abc123/versions"


def test_get_dxt_extension_versions_requires_extension_id():
    with pytest.raises(od.DiscoveryError):
        od.get_dxt_extension_versions("org-x", "", bearer="b")


def test_get_model_config_url_shape():
    mock = _capture_get()
    od.get_model_config("org-x", "claude-opus-4-7", bearer="b")
    url = _called_url(mock)
    assert url == "https://claude.ai/api/organizations/org-x/model_configs/claude-opus-4-7"


def test_get_model_config_requires_model_id():
    with pytest.raises(od.DiscoveryError):
        od.get_model_config("org-x", "", bearer="b")


def test_list_account_marketplaces_url_shape():
    mock = _capture_get()
    od.list_account_marketplaces("org-x", bearer="b")
    url = _called_url(mock)
    assert url == "https://claude.ai/api/organizations/org-x/marketplaces/list-account-marketplaces"


# ── batch-branch-status (POST shape, idempotent read-style) ─────────────


def test_get_github_branch_status_uses_post_to_api_anthropic():
    mock = _capture_post()
    od.get_github_branch_status(["repo-a", "repo-b"], bearer="STUB-OAT")
    url = _called_url(mock)
    assert "api.anthropic.com/v1/code/github/batch-branch-status" in url
    assert "caller=ccd-sidebar" in url
    body = mock.call_args.kwargs["json"]
    assert body == {"repos": ["repo-a", "repo-b"]}
    headers = _called_headers(mock)
    assert headers["Authorization"] == "Bearer STUB-OAT"


def test_get_github_branch_status_requires_repos():
    with pytest.raises(od.DiscoveryError):
        od.get_github_branch_status([], bearer="b")


# ── URL safety: path quoting via urllib.quote ───────────────────────────


def test_org_with_special_chars_url_quoted():
    """urllib.quote escapes spaces + special chars (default safe='/')."""
    mock = _capture_get()
    od.get_cowork_settings("org with space", bearer="b")
    url = _called_url(mock)
    assert "org%20with%20space" in url


# ── Pseudonymity ────────────────────────────────────────────────────────


def test_bearer_never_logged_on_success(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.org_discovery")
    SECRET_BEARER = "STUB-OAT-DEEPLY-SECRET-do-not-leak-xyz"
    _capture_get()
    od.get_mcp_bootstrap("org-x", bearer=SECRET_BEARER)
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_bearer_never_logged_on_fail(caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.org_discovery")
    SECRET_BEARER = "STUB-OAT-FAIL-LEAK-CHECK-xyz"
    od._curl_requests.get = MagicMock(return_value=_ok_resp({}, status=403))
    with pytest.raises(od.DiscoveryError):
        od.get_mcp_bootstrap("org-x", bearer=SECRET_BEARER)
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_post_bearer_never_logged_on_transport_err(caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.org_discovery")
    SECRET_BEARER = "STUB-OAT-POST-FAIL-leak-check"
    od._curl_requests.post = MagicMock(side_effect=Exception("dns fail"))
    with pytest.raises(od.DiscoveryError):
        od.get_github_branch_status(["r"], bearer=SECRET_BEARER)
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


# ── Module constants ────────────────────────────────────────────────────


def test_claude_ai_host_constant():
    assert od._CLAUDE_AI == "https://claude.ai"


def test_api_anthropic_host_constant():
    assert od._API_ANTHROPIC == "https://api.anthropic.com"


def test_all_13_endpoints_exported():
    expected = {
        "DiscoveryError",
        "get_chat_conversations", "get_cowork_settings", "get_mcp_bootstrap",
        "get_memory", "get_memory_settings", "get_projects",
        "get_plugins_enabled_state", "list_plugins",
        "get_notification_preferences", "get_overage_spend_limit",
        "get_dxt_extension_versions", "get_model_config",
        "list_account_marketplaces", "get_github_branch_status",
    }
    assert set(od.__all__) == expected


# ── Read-only audit ─────────────────────────────────────────────────────


def test_no_destructive_http_verbs_used():
    """Audit module source: no PUT/DELETE/PATCH anywhere in production
    code. Only GET + idempotent read-style POST for batch-branch-status."""
    import inspect
    src = inspect.getsource(od)
    code_lines = []
    in_string = False
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_string = not in_string
            continue
        if not in_string and not stripped.startswith("#"):
            code_lines.append(line)
    code = "\n".join(code_lines)
    assert "_curl_requests.put" not in code
    assert "_curl_requests.delete" not in code
    assert "_curl_requests.patch" not in code
