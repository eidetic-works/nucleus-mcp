"""v0.3.0 Layer 0 — OAuth token exchange for Anthropic api session bearer.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 0
(filed by op-assistant 2026-06-09T03:00Z after mitm-capture spike
proved v0.2.x cookie-replay path was hitting a stub-200 no-op endpoint)
+ op-assistant 2026-06-09T09:15Z architectural amendment (build INTO
nucleus, not standalone scripts/).

This helper exchanges a Claude.app sessionKey cookie value for a
30-day `sk-ant-oat01-...` access_token via the OAuth exchange that
Claude.app itself uses internally. Result is persisted to
`~/.tb/oauth_<role>.json` mode 600 so subsequent layers can read
the cached bearer.

Foundation layer: every higher v0.3.0 layer (1 session pre-arm at
sessions.wake, 2 org-discovery at org.discovery, 4 fallback chain,
5 full inference at sessions.autonomous_wake) needs an OAuth bearer
to call api.anthropic.com.

Original PR #501 shipped this module at scripts/oauth_exchange.py. PR
#501-amend relocates it to nucleus path; the scripts/oauth_exchange.py
file remains as a one-line re-export shim for backward compat with any
extant callers.

Pseudonymity (carryover from v0.2.x):
- access_token + refresh_token + sessionKey VALUES never logged
- ~/.tb/oauth_<role>.json mode 600 (matches per-role bearer convention
  from PR #495 v0.2.1 Layer A)
- curl_cffi Chrome impersonation per spec line 172 (defensive against
  future CF re-engagement)
"""
from __future__ import annotations

import json
import logging
import time
import uuid as _uuid
from pathlib import Path
from typing import Optional

try:
    from curl_cffi import requests as _curl_requests
except ImportError:  # pragma: no cover - tests stub via patch
    _curl_requests = None  # type: ignore[assignment]


logger = logging.getLogger("nucleus.oauth")

_OAUTH_URL = "https://api.anthropic.com/v1/oauth/token"
_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # Claude.app's actual client_id per 2026-06-09 mitm capture
_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
_EXPIRES_IN_S = 2592000  # 30 days (Anthropic ceiling per capture)
_REFRESH_MARGIN_S = 300  # refresh when within 5 min of expiry
_TOKEN_DIR = Path.home() / ".tb"
_IMPERSONATE = "chrome120"  # curl_cffi profile

# Minimum reasonable file size — corrupted/truncated cached JSON beneath
# this is treated as no-cache and forces a fresh exchange.
_MIN_CACHE_BYTES = 32


# ── Data shapes ─────────────────────────────────────────────────────────


class OAuthToken:
    """Persisted OAuth state for one role/account."""

    __slots__ = (
        "access_token", "refresh_token", "expires_at", "scope",
        "organization_uuid", "account_uuid", "minted_at",
    )

    def __init__(
        self,
        *,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        scope: str = "",
        organization_uuid: str = "",
        account_uuid: str = "",
        minted_at: int = 0,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = int(expires_at)
        self.scope = scope
        self.organization_uuid = organization_uuid
        self.account_uuid = account_uuid
        self.minted_at = int(minted_at)

    def is_valid(self, margin_s: int = _REFRESH_MARGIN_S) -> bool:
        """True when access_token has at least `margin_s` seconds before expiry."""
        return int(time.time()) < (self.expires_at - margin_s)

    def to_json(self) -> str:
        return json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "organization_uuid": self.organization_uuid,
            "account_uuid": self.account_uuid,
            "minted_at": self.minted_at,
        }, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "OAuthToken":
        d = json.loads(raw)
        return cls(
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            expires_at=int(d["expires_at"]),
            scope=d.get("scope", ""),
            organization_uuid=d.get("organization_uuid", ""),
            account_uuid=d.get("account_uuid", ""),
            minted_at=int(d.get("minted_at", 0)),
        )


class OAuthExchangeError(RuntimeError):
    """Raised when OAuth exchange fails terminally (401 / invalid_grant).

    Caller decides recovery path (re-extract cookies from Cookies SQLite,
    surface to operator, etc).
    """


# ── Cache file I/O ──────────────────────────────────────────────────────


def _cache_path(role: str) -> Path:
    return _TOKEN_DIR / f"oauth_{role}.json"


def _load_cached(role: str) -> Optional[OAuthToken]:
    """Read ~/.tb/oauth_<role>.json. Returns None on absent/empty/corrupt."""
    path = _cache_path(role)
    try:
        stat = path.stat()
    except OSError:
        return None
    if stat.st_size < _MIN_CACHE_BYTES:
        return None
    try:
        raw = path.read_text()
        return OAuthToken.from_json(raw)
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None


def _save_cached(role: str, token: OAuthToken) -> None:
    """Persist token JSON to ~/.tb/oauth_<role>.json mode 600.

    Creates the .tb dir if missing. Atomic write via tmp + rename so
    concurrent reads never see a partial file.
    """
    _TOKEN_DIR.mkdir(mode=0o700, exist_ok=True)
    target = _cache_path(role)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(token.to_json())
    tmp.chmod(0o600)
    tmp.replace(target)


# ── HTTP exchange ───────────────────────────────────────────────────────


def _post_oauth(
    *,
    grant_type: str,
    bearer: str,
    extra_body: dict,
) -> dict:
    """POST to /v1/oauth/token. Bearer is sessionKey (authorization_code)
    or access_token (refresh_token). Returns parsed JSON or raises
    OAuthExchangeError on non-2xx.

    Token VALUE never logged (only status_code + brief error class).
    """
    if _curl_requests is None:
        raise OAuthExchangeError(
            "curl_cffi not installed; pip install curl_cffi"
        )
    body = {
        "grant_type": grant_type,
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "expires_in": _EXPIRES_IN_S,
        **extra_body,
    }
    headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        resp = _curl_requests.post(
            _OAUTH_URL,
            headers=headers,
            json=body,
            impersonate=_IMPERSONATE,
            timeout=30,
        )
    except Exception as exc:
        logger.warning("oauth: transport error class=%s", type(exc).__name__)
        raise OAuthExchangeError(f"transport error: {type(exc).__name__}") from exc

    if resp.status_code < 200 or resp.status_code >= 300:
        logger.warning(
            "oauth: grant=%s rejected status=%d",
            grant_type, resp.status_code,
        )
        try:
            _err_body = resp.text[:200]
        except Exception:
            _err_body = "<unreadable body>"
        raise OAuthExchangeError(
            f"oauth grant_type={grant_type} rejected with status={resp.status_code}: {_err_body}"
        )
    return resp.json()


def _parsed_to_token(parsed: dict, minted_at: Optional[int] = None) -> OAuthToken:
    """Build OAuthToken from /v1/oauth/token response body."""
    minted = int(minted_at if minted_at is not None else time.time())
    expires_in = int(parsed.get("expires_in", _EXPIRES_IN_S))
    return OAuthToken(
        access_token=parsed["access_token"],
        refresh_token=parsed.get("refresh_token", ""),
        expires_at=minted + expires_in,
        scope=parsed.get("scope", ""),
        organization_uuid=(parsed.get("organization") or {}).get("uuid", ""),
        account_uuid=(parsed.get("account") or {}).get("uuid", ""),
        minted_at=minted,
    )


# ── Public API ──────────────────────────────────────────────────────────


def get_access_token(
    role: str,
    *,
    session_key: Optional[str] = None,
    force_refresh: bool = False,
) -> str:
    """Resolve a valid access_token for ``role``.

    Priority order:
      1. Cached + not expired (>5 min margin) and not force_refresh → return cached
      2. Cached refresh_token → POST /v1/oauth/token grant_type=refresh_token
      3. session_key provided → POST grant_type=authorization_code

    Raises OAuthExchangeError if no valid path produces a fresh token.

    Returns: access_token string. Caller threads it as
    Authorization: Bearer <token> into subsequent layer-1+ calls.
    """
    cached = _load_cached(role)
    if cached and not force_refresh and cached.is_valid():
        return cached.access_token

    # Try refresh_token grant first if available — cheaper + doesn't need cookies
    if cached and cached.refresh_token:
        try:
            parsed = _post_oauth(
                grant_type="refresh_token",
                bearer=cached.refresh_token,
                extra_body={"refresh_token": cached.refresh_token},
            )
            token = _parsed_to_token(parsed)
            _save_cached(role, token)
            return token.access_token
        except OAuthExchangeError:
            # Refresh failed; fall through to cookie exchange if session_key present
            logger.warning("oauth: refresh_token grant failed for role=%s", role)

    # Cookie path — need fresh sessionKey from Cookies SQLite
    if not session_key:
        raise OAuthExchangeError(
            f"no valid cached token for role={role!r} and no session_key provided"
        )

    parsed = _post_oauth(
        grant_type="authorization_code",
        bearer=session_key,
        extra_body={
            "code": str(_uuid.uuid4()),
            "state": str(_uuid.uuid4()),
            "code_verifier": str(_uuid.uuid4()),
        },
    )
    token = _parsed_to_token(parsed)
    _save_cached(role, token)
    return token.access_token


def get_token_for_role(role: str) -> Optional[OAuthToken]:
    """Return the full cached OAuthToken object (or None) without refresh.

    Useful for Layer 2+ that may need expires_at / organization_uuid for
    subsequent endpoint construction.
    """
    return _load_cached(role)


__all__ = [
    "OAuthToken",
    "OAuthExchangeError",
    "get_access_token",
    "get_token_for_role",
]
