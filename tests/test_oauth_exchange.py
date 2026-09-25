"""Tests for v0.3.0 Layer 0 — mcp_server_nucleus.oauth.exchange.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 0 +
op-assistant 2026-06-09T09:15Z architectural amendment (build INTO
nucleus, not standalone scripts/). Static-shape + behavior coverage;
no live api.anthropic.com calls (stubbed via patch of curl_cffi.requests.post).

Coverage:
- Cache cold/warm/expired/corrupt/empty
- Refresh-token grant + authorization_code grant + chain (refresh fail → cookie path)
- File mode 0o600 + JSON roundtrip
- Pseudonymity: tokens never logged at any level (caplog scan)
- Atomic-write via tmp + rename
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.oauth import exchange as oauth


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Redirect ~/.tb to a tmp dir so tests don't pollute operator's home."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(oauth, "_TOKEN_DIR", tmp_path / ".tb")
    return tmp_path


def _ok_response(access="STUB-OAT-NEW-token-AAA",
                 refresh="STUB-ORT-NEW-refresh-BBB",
                 expires_in=2592000,
                 org="903554b9-org",
                 acct="bad904b4-acct"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "token_type": "Bearer",
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": expires_in,
        "scope": "user:file_upload user:inference user:profile user:sessions:claude_code",
        "token_uuid": "tok-uuid",
        "organization": {"uuid": org},
        "account": {"uuid": acct},
    }
    return resp


def _bad_response(status=401):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"error": "invalid_grant"}
    return resp


def _write_cached(home: Path, role: str, *, access, refresh, expires_at):
    tb = home / ".tb"
    tb.mkdir(exist_ok=True)
    path = tb / f"oauth_{role}.json"
    path.write_text(json.dumps({
        "access_token": access,
        "refresh_token": refresh,
        "expires_at": expires_at,
        "scope": "x",
        "organization_uuid": "o",
        "account_uuid": "a",
        "minted_at": int(time.time()),
    }))
    path.chmod(0o600)
    return path


# ── Cache hit (no HTTP call) ─────────────────────────────────────────────


def test_cached_token_within_margin_returns_without_http(_isolate_home):
    """Spec test 1: cached token exists + not expired → return cached without HTTP."""
    _write_cached(_isolate_home, "bespoq_cowork",
                  access="STUB-OAT-CACHED-good",
                  refresh="STUB-ORT-CACHED-refresh",
                  expires_at=int(time.time()) + 600)  # 10 min ahead
    with patch.object(oauth, "_post_oauth") as mock_post:
        result = oauth.get_access_token("bespoq_cowork")
    assert result == "STUB-OAT-CACHED-good"
    mock_post.assert_not_called()


def test_force_refresh_bypasses_cache(_isolate_home):
    """force_refresh=True ignores valid cache and re-exchanges."""
    _write_cached(_isolate_home, "role_x",
                  access="OLD-cached",
                  refresh="OLD-refresh",
                  expires_at=int(time.time()) + 600)
    with patch.object(oauth, "_post_oauth",
                      return_value={"access_token": "NEW-forced",
                                    "refresh_token": "NEW-refresh",
                                    "expires_in": 2592000,
                                    "organization": {"uuid": "o"},
                                    "account": {"uuid": "a"}}):
        result = oauth.get_access_token("role_x", force_refresh=True)
    assert result == "NEW-forced"


# ── Refresh-token grant path ────────────────────────────────────────────


def test_expired_cache_with_refresh_uses_refresh_grant(_isolate_home):
    """Spec test 3: cached expired + refresh_token present → refresh grant."""
    _write_cached(_isolate_home, "role_y",
                  access="sk-EXPIRED",
                  refresh="STUB-ORT-still-valid",
                  expires_at=int(time.time()) - 100)  # expired
    captured = {}
    def _capture(**kwargs):
        captured.update(kwargs)
        return {
            "access_token": "STUB-OAT-FRESH",
            "refresh_token": "STUB-ORT-rotated",
            "expires_in": 2592000,
            "organization": {"uuid": "o"},
            "account": {"uuid": "a"},
        }
    with patch.object(oauth, "_post_oauth", side_effect=_capture):
        result = oauth.get_access_token("role_y")
    assert result == "STUB-OAT-FRESH"
    assert captured["grant_type"] == "refresh_token"
    assert captured["bearer"] == "STUB-ORT-still-valid"


def test_within_refresh_margin_triggers_refresh(_isolate_home):
    """Token expiring in <5 min triggers proactive refresh."""
    _write_cached(_isolate_home, "role_margin",
                  access="sk-CACHED",
                  refresh="STUB-ORT-refresh-1",
                  expires_at=int(time.time()) + 100)  # < 300s margin
    with patch.object(oauth, "_post_oauth",
                      return_value={"access_token": "STUB-OAT-REFRESHED",
                                    "refresh_token": "rot",
                                    "expires_in": 2592000,
                                    "organization": {"uuid": "o"},
                                    "account": {"uuid": "a"}}) as mock_post:
        result = oauth.get_access_token("role_margin")
    assert result == "STUB-OAT-REFRESHED"
    mock_post.assert_called_once()


# ── Cookie / authorization_code grant path ──────────────────────────────


def test_no_cache_with_session_key_uses_authorization_code_grant(_isolate_home):
    """Spec test 4: no cached token + cookie → authorization_code grant."""
    captured = {}
    def _capture(**kwargs):
        captured.update(kwargs)
        return {
            "access_token": "STUB-OAT-FIRST-mint",
            "refresh_token": "STUB-ORT-first",
            "expires_in": 2592000,
            "organization": {"uuid": "o"},
            "account": {"uuid": "a"},
        }
    with patch.object(oauth, "_post_oauth", side_effect=_capture):
        result = oauth.get_access_token("fresh_role",
                                        session_key="STUB-SID-cookie-value")
    assert result == "STUB-OAT-FIRST-mint"
    assert captured["grant_type"] == "authorization_code"
    assert captured["bearer"] == "STUB-SID-cookie-value"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN BROKEN, live-confirmed 2026-08-21 (see "
        "AGENT_OS_OAUTH_LIVE_VERIFICATION.md). Not fixed here -- guessing at "
        "Anthropic's undocumented real code/state/code_verifier semantics by "
        "trial-and-error against a live account is explicitly declined "
        "pending operator approval. xfail(strict=True) so this is loudly "
        "visible, cannot silently regress further, and flips to an "
        "unexpected-pass failure the moment someone actually fixes it."
    ),
)
def test_authorization_code_grant_sends_a_real_code_KNOWN_BROKEN(_isolate_home):
    """RED test, intentional (2026-08-21/22) -- documents a real, live-confirmed
    bug rather than silently letting it regress further or get forgotten.
    See mcp-server-nucleus/docs/AGENT_OS_OAUTH_LIVE_VERIFICATION.md for the
    full live investigation: the authorization_code grant body's ``code``
    field is ``str(uuid.uuid4())`` -- a fresh random value on every call,
    bearing zero relationship to ``session_key``/``bearer`` or anything else
    about the actual auth flow. Confirmed against the real Anthropic OAuth
    server: it rejects this with
    ``invalid_grant: Invalid 'code' in request.`` every time.

    This test stays mock-only (matches this file's own no-live-calls
    contract) and proves the mechanistic root cause the live 400 traces
    back to: call get_access_token() twice with the SAME session_key and
    show the two ``code`` values sent are unrelated random noise, not
    something a real authorization_code exchange would ever produce.

    NOT fixed here -- per explicit brief scope, guessing at Anthropic's
    undocumented real code/state/code_verifier semantics by trial-and-error
    against a live account is declined; needs either a captured real
    authorization_code from an actual re-mint flow or a documented spec,
    and explicit operator approval before any live-account attempt. See the
    root-cause note in AGENT_OS_OAUTH_LIVE_VERIFICATION.md for exactly what
    a correct fix would need.
    """
    captured_codes = []

    def _capture(**kwargs):
        captured_codes.append(kwargs["extra_body"]["code"])
        return {
            "access_token": f"STUB-OAT-{len(captured_codes)}",
            "refresh_token": "STUB-ORT",
            "expires_in": 2592000,
            "organization": {"uuid": "o"},
            "account": {"uuid": "a"},
        }

    same_session_key = "STUB-SID-identical-cookie-both-calls"
    with patch.object(oauth, "_post_oauth", side_effect=_capture):
        oauth.get_access_token("role_a", session_key=same_session_key)
        _write_cached(_isolate_home, "role_a", access="EXPIRED", refresh="",
                      expires_at=int(time.time()) - 100)
        oauth.get_access_token("role_a", session_key=same_session_key)

    assert len(captured_codes) == 2
    # KNOWN BROKEN: a real implementation's code should be reproducible from
    # (or otherwise meaningfully tied to) the same session_key -- it should
    # NOT be two unrelated random values. This is exactly what the live
    # server's "Invalid 'code' in request" rejection traces back to.
    assert captured_codes[0] == captured_codes[1], (
        "the two authorization codes sent for the SAME session_key were "
        f"different random values ({captured_codes!r}) -- this is the "
        "confirmed root cause of the live invalid_grant rejection; a real "
        "fix requires deriving `code` from the actual OAuth flow, not "
        "str(uuid.uuid4()). See AGENT_OS_OAUTH_LIVE_VERIFICATION.md."
    )


def test_refresh_fail_falls_back_to_auth_code_when_session_key_present(_isolate_home):
    """Refresh raises → if session_key provided, fall through to cookie grant."""
    _write_cached(_isolate_home, "role_z",
                  access="EXPIRED",
                  refresh="STALE-refresh",
                  expires_at=int(time.time()) - 100)
    calls = []
    def _stub(**kwargs):
        calls.append(kwargs["grant_type"])
        if kwargs["grant_type"] == "refresh_token":
            raise oauth.OAuthExchangeError("refresh stale")
        return {
            "access_token": "STUB-OAT-COOKIE-fallback",
            "refresh_token": "new",
            "expires_in": 2592000,
            "organization": {"uuid": "o"},
            "account": {"uuid": "a"},
        }
    with patch.object(oauth, "_post_oauth", side_effect=_stub):
        result = oauth.get_access_token("role_z", session_key="STUB-SID-fresh-cookie")
    assert result == "STUB-OAT-COOKIE-fallback"
    assert calls == ["refresh_token", "authorization_code"]


def test_no_cache_no_session_key_raises_actionable_error(_isolate_home):
    """Spec test 5: no path forward → OAuthExchangeError with role name."""
    with pytest.raises(oauth.OAuthExchangeError) as exc:
        oauth.get_access_token("missing_role")
    assert "missing_role" in str(exc.value)


# ── Refresh raise WITHOUT session_key → raises (no fallback) ────────────


def test_refresh_fail_without_session_key_raises(_isolate_home):
    _write_cached(_isolate_home, "role_x",
                  access="EXPIRED",
                  refresh="STALE",
                  expires_at=int(time.time()) - 100)
    with patch.object(oauth, "_post_oauth",
                      side_effect=oauth.OAuthExchangeError("invalid_grant")):
        with pytest.raises(oauth.OAuthExchangeError):
            oauth.get_access_token("role_x")  # no session_key


# ── File mode + atomicity ───────────────────────────────────────────────


def test_persisted_file_mode_is_0o600(_isolate_home):
    """Spec test 6: persisted JSON file mode 0o600 (operator-identity protection)."""
    with patch.object(oauth, "_post_oauth",
                      return_value={"access_token": "a", "refresh_token": "r",
                                    "expires_in": 2592000,
                                    "organization": {"uuid": "o"},
                                    "account": {"uuid": "a"}}):
        oauth.get_access_token("role_perm", session_key="sk-x")
    path = _isolate_home / ".tb" / "oauth_role_perm.json"
    assert path.exists()
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600, f"got mode {oct(mode)}; must be 0o600"


def test_atomic_write_via_tmp_and_rename(_isolate_home, monkeypatch):
    """Tmp file is rename()d into place; partial state never observable."""
    seen_tmp = []
    orig_replace = Path.replace

    def _trace_replace(self, target):
        if str(self).endswith(".tmp"):
            seen_tmp.append(str(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _trace_replace)
    with patch.object(oauth, "_post_oauth",
                      return_value={"access_token": "a", "refresh_token": "r",
                                    "expires_in": 2592000,
                                    "organization": {"uuid": "o"},
                                    "account": {"uuid": "a"}}):
        oauth.get_access_token("role_atomic", session_key="sk-x")
    assert any(".tmp" in t for t in seen_tmp), \
        "no atomic-via-tmp rename observed"


# ── JSON roundtrip / persistence survives Python restart ────────────────


def test_persisted_state_survives_module_reload(_isolate_home):
    """Spec test 8: file roundtrip — write, then re-read on fresh load."""
    with patch.object(oauth, "_post_oauth",
                      return_value={"access_token": "STUB-OAT-PERSISTED",
                                    "refresh_token": "STUB-ORT-stored",
                                    "expires_in": 2592000,
                                    "scope": "user:inference",
                                    "organization": {"uuid": "org-id"},
                                    "account": {"uuid": "acct-id"}}):
        oauth.get_access_token("role_persist", session_key="sk-x")

    # Subsequent call (different "session") MUST find cached, no HTTP
    with patch.object(oauth, "_post_oauth") as mock_post:
        result = oauth.get_access_token("role_persist")
    assert result == "STUB-OAT-PERSISTED"
    mock_post.assert_not_called()

    # Inspect via public read
    tok = oauth.get_token_for_role("role_persist")
    assert tok is not None
    assert tok.access_token == "STUB-OAT-PERSISTED"
    assert tok.refresh_token == "STUB-ORT-stored"
    assert tok.organization_uuid == "org-id"
    assert tok.scope == "user:inference"


# ── Cache corruption / empty ────────────────────────────────────────────


def test_corrupt_cache_file_treated_as_no_cache(_isolate_home):
    tb = _isolate_home / ".tb"
    tb.mkdir(exist_ok=True)
    (tb / "oauth_corrupt.json").write_text("not-json{{{")
    # No session_key + no valid cache → raise
    with pytest.raises(oauth.OAuthExchangeError):
        oauth.get_access_token("corrupt")


def test_tiny_cache_file_treated_as_no_cache(_isolate_home):
    """File smaller than _MIN_CACHE_BYTES treated as no-cache."""
    tb = _isolate_home / ".tb"
    tb.mkdir(exist_ok=True)
    (tb / "oauth_tiny.json").write_text("{}")
    with pytest.raises(oauth.OAuthExchangeError):
        oauth.get_access_token("tiny")


# ── Pseudonymity — tokens never logged ──────────────────────────────────


def test_access_token_never_appears_in_log_records(_isolate_home, caplog):
    """Spec test 7 + pseudonymity discipline carryover from v0.2.x."""
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.oauth")
    SECRET_ACCESS = "STUB-OAT-VERY-SECRET-ACCESS-TOKEN-xyz"
    SECRET_REFRESH = "STUB-ORT-VERY-SECRET-REFRESH-zzz"
    SECRET_SESSION = "STUB-SID-VERY-SECRET-SESSION-www"
    with patch.object(oauth, "_post_oauth",
                      return_value={"access_token": SECRET_ACCESS,
                                    "refresh_token": SECRET_REFRESH,
                                    "expires_in": 2592000,
                                    "organization": {"uuid": "o"},
                                    "account": {"uuid": "a"}}):
        oauth.get_access_token("logged_role", session_key=SECRET_SESSION)
    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_ACCESS not in all_log_text
    assert SECRET_REFRESH not in all_log_text
    assert SECRET_SESSION not in all_log_text


def test_log_warn_on_oauth_reject_does_not_leak_bearer(_isolate_home, caplog):
    """Even on rejection logs, the bearer value MUST NOT leak."""
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.oauth")
    SECRET_SESSION = "STUB-SID-LEAK-CHECK-xyz"
    with patch.object(oauth, "_post_oauth",
                      side_effect=oauth.OAuthExchangeError("rejected status=401")):
        # First exhausts refresh fallback (no cache) then tries cookie grant
        with pytest.raises(oauth.OAuthExchangeError):
            oauth.get_access_token("rejected_role", session_key=SECRET_SESSION)
    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_SESSION not in all_log_text


# ── Module-level constants from mitm capture ────────────────────────────


def test_client_id_matches_mitm_capture():
    """Per spec line 21: 9d1c250a-e61b-44d9-88ed-5944d1962f5e."""
    assert oauth._CLIENT_ID == "9d1c250a-e61b-44d9-88ed-5944d1962f5e"


def test_oauth_url_is_api_anthropic_not_claude_ai():
    """Critical mitm finding: real OAuth lives at api.anthropic.com,
    NOT claude.ai. Guard against regression."""
    assert oauth._OAUTH_URL == "https://api.anthropic.com/v1/oauth/token"
    assert "claude.ai" not in oauth._OAUTH_URL


def test_refresh_margin_is_300s():
    """5-minute margin = spec line 77."""
    assert oauth._REFRESH_MARGIN_S == 300


def test_curl_cffi_impersonate_set_per_spec_line_172():
    """Chrome impersonation defensive default per spec."""
    assert oauth._IMPERSONATE.startswith("chrome")


def test_all_exported():
    expected = {
        "OAuthToken",
        "OAuthExchangeError",
        "get_access_token",
        "get_token_for_role",
    }
    assert set(oauth.__all__) == expected
