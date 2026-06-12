"""v0.3.0 Layer 2 — Org-discovery read-only endpoint wrappers.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 2
(spec lines 97-120) + op-assistant 2026-06-09T09:15Z architectural
amendment (build INTO nucleus, not standalone scripts/). Operator
GREENLIT v0.3.0 at 2026-06-09T08:55Z.

13 read-only endpoints wrapped as clean Python functions; each takes
an OAuth bearer (from Layer 0 oauth_exchange) and returns parsed JSON.

Why this lives inside nucleus per operator 09:10Z directive:
- OAuth + session + discovery surfaces all need to fire inside the
  nucleus MCP subprocess so relay_inbox_hook → autonomous_wake →
  inference replay (Layer 5) can compose them without crossing
  process boundaries.
- nucleus tool surface can expose actions like nucleus_org(action=
  'list_chat_conversations'|'mcp_bootstrap'|...) so other fleet
  surfaces (cc-main, cc-peer, Cowork) consume via MCP.

Architectural context: op-assistant 2026-06-09T03:50Z Layer 3 NULL
VERDICT confirmed no undocumented /run primitive. Layer 5 (full
POST /v1/messages?beta=true inference replay) is now MANDATORY.
Layer 5 needs Layer 2's discovery surface to populate inference
payload context: system_prompt + tools + MCP servers + history.

Layer 2 also independently valuable (per spec § Forward-looking
compounding line 161-165):
- MCP-server-side fleet awareness via chat_conversations_v2
  (replaces local-JSON polling)
- External memory READS (writes deferred to v0.3.x extension)
- GitHub branch-status as passive wake heuristic

Pseudonymity carryover:
- OAuth bearer + org/account UUIDs never logged at any level
- Read-only: no destructive ops anywhere in this module
- All HTTP via curl_cffi Chrome impersonation (chrome120 consistent
  with Layer 0)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

try:
    from curl_cffi import requests as _curl_requests
except ImportError:  # pragma: no cover - tests stub via patch
    _curl_requests = None  # type: ignore[assignment]


logger = logging.getLogger("nucleus.org_discovery")

_CLAUDE_AI = "https://claude.ai"
_API_ANTHROPIC = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"
_IMPERSONATE = "chrome120"
_HTTP_TIMEOUT_S = 15.0


class DiscoveryError(RuntimeError):
    """Raised when a read-only discovery call fails terminally."""


# ── Shared GET helper ───────────────────────────────────────────────────


def _get_json(
    url: str,
    *,
    bearer: str,
    accept: str = "application/json",
) -> Any:
    """Issue a bearer-authed GET. Return parsed JSON or raise DiscoveryError.

    Bearer VALUE never logged; only status_code + path on failure.
    """
    if not bearer:
        raise DiscoveryError("bearer required")
    if _curl_requests is None:
        raise DiscoveryError("curl_cffi not installed")
    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Accept": accept,
    }
    try:
        resp = _curl_requests.get(
            url, headers=headers,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning("org_discovery: transport class=%s", type(exc).__name__)
        raise DiscoveryError(f"transport error: {type(exc).__name__}") from exc
    if not (200 <= resp.status_code < 300):
        logger.warning(
            "org_discovery: GET rejected status=%d path=%s",
            resp.status_code, _path_for_log(url),
        )
        raise DiscoveryError(f"GET rejected status={resp.status_code}")
    return resp.json()


def _post_json(
    url: str,
    body: Dict[str, Any],
    *,
    bearer: str,
) -> Any:
    """Issue a bearer-authed POST (used only for read-style POSTs like
    batch-branch-status). Caller must guarantee read-only semantics."""
    if not bearer:
        raise DiscoveryError("bearer required")
    if _curl_requests is None:
        raise DiscoveryError("curl_cffi not installed")
    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = _curl_requests.post(
            url, headers=headers, json=body,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning("org_discovery: transport class=%s", type(exc).__name__)
        raise DiscoveryError(f"transport error: {type(exc).__name__}") from exc
    if not (200 <= resp.status_code < 300):
        logger.warning(
            "org_discovery: POST rejected status=%d path=%s",
            resp.status_code, _path_for_log(url),
        )
        raise DiscoveryError(f"POST rejected status={resp.status_code}")
    return resp.json()


def _path_for_log(url: str) -> str:
    """Strip query + cap for log emission."""
    bare = url.split("?", 1)[0]
    return bare[:120]


# ── 13 read-only endpoint wrappers per spec § Layer 2 ───────────────────


def get_chat_conversations(
    org: str,
    *,
    bearer: str,
    limit: int = 30,
    starred: bool = False,
) -> Any:
    """GET /api/organizations/<org>/chat_conversations_v2?limit=N&starred=..."""
    qs = urlencode({"limit": int(limit), "starred": "true" if starred else "false"})
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/chat_conversations_v2?{qs}"
    return _get_json(url, bearer=bearer)


def get_cowork_settings(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/cowork_settings"""
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/cowork_settings"
    return _get_json(url, bearer=bearer)


def get_mcp_bootstrap(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/mcp/v2/bootstrap — MCP server inventory."""
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/mcp/v2/bootstrap"
    return _get_json(url, bearer=bearer)


def get_memory(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/memory — memory state.

    Read-only here. Spec line 49 notes /memory is RW; writes deferred
    to a separate v0.3.x extension PR per spec § Forward-looking
    compounding (line 163).
    """
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/memory"
    return _get_json(url, bearer=bearer)


def get_memory_settings(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/memory/settings"""
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/memory/settings"
    return _get_json(url, bearer=bearer)


def get_projects(
    org: str,
    *,
    bearer: str,
    include_harmony: bool = True,
    limit: int = 200,
) -> Any:
    """GET /api/organizations/<org>/projects?include_harmony_projects=&limit="""
    qs = urlencode({
        "include_harmony_projects": "true" if include_harmony else "false",
        "limit": int(limit),
    })
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/projects?{qs}"
    return _get_json(url, bearer=bearer)


def get_plugins_enabled_state(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/plugins/enabled-state"""
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/plugins/enabled-state"
    return _get_json(url, bearer=bearer)


def list_plugins(
    org: str,
    *,
    bearer: str,
    installation_preference: str = "auto_install",
    limit: int = 100,
) -> Any:
    """GET /api/organizations/<org>/plugins/list-plugins?..."""
    qs = urlencode({
        "installation_preference": installation_preference,
        "limit": int(limit),
    })
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/plugins/list-plugins?{qs}"
    return _get_json(url, bearer=bearer)


def get_notification_preferences(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/notification/preferences"""
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/notification/preferences"
    return _get_json(url, bearer=bearer)


def get_overage_spend_limit(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/overage_spend_limit"""
    url = f"{_CLAUDE_AI}/api/organizations/{quote(org)}/overage_spend_limit"
    return _get_json(url, bearer=bearer)


def get_dxt_extension_versions(
    org: str,
    extension_id: str,
    *,
    bearer: str,
) -> Any:
    """GET /api/organizations/<org>/dxt/extensions/<id>/versions"""
    if not extension_id:
        raise DiscoveryError("extension_id required")
    url = (
        f"{_CLAUDE_AI}/api/organizations/{quote(org)}"
        f"/dxt/extensions/{quote(extension_id)}/versions"
    )
    return _get_json(url, bearer=bearer)


def get_model_config(org: str, model_id: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/model_configs/<model>"""
    if not model_id:
        raise DiscoveryError("model_id required")
    url = (
        f"{_CLAUDE_AI}/api/organizations/{quote(org)}"
        f"/model_configs/{quote(model_id)}"
    )
    return _get_json(url, bearer=bearer)


def list_account_marketplaces(org: str, *, bearer: str) -> Any:
    """GET /api/organizations/<org>/marketplaces/list-account-marketplaces"""
    url = (
        f"{_CLAUDE_AI}/api/organizations/{quote(org)}"
        f"/marketplaces/list-account-marketplaces"
    )
    return _get_json(url, bearer=bearer)


def get_github_branch_status(repos: List[str], *, bearer: str) -> Any:
    """POST /v1/code/github/batch-branch-status?caller=ccd-sidebar.

    Read-style POST (idempotent — only returns branch state). Body is
    the list of repos to check. Caller can use this passively to detect
    'CI failed' or 'PR comment landed' as a wake heuristic per spec
    line 164 forward-looking compounding.
    """
    if not repos:
        raise DiscoveryError("repos list required")
    url = f"{_API_ANTHROPIC}/v1/code/github/batch-branch-status?caller=ccd-sidebar"
    return _post_json(url, {"repos": list(repos)}, bearer=bearer)


__all__ = [
    "DiscoveryError",
    "get_chat_conversations",
    "get_cowork_settings",
    "get_mcp_bootstrap",
    "get_memory",
    "get_memory_settings",
    "get_projects",
    "get_plugins_enabled_state",
    "list_plugins",
    "get_notification_preferences",
    "get_overage_spend_limit",
    "get_dxt_extension_versions",
    "get_model_config",
    "list_account_marketplaces",
    "get_github_branch_status",
]
