"""Antigravity OAuth-bearer LLM provider — Google Cloud Code Assist.

Drop-in replacement for AnthropicLLM / ClaudeOAuthLLM that routes
generateContent calls through a Google OAuth bearer (Antigravity /
Cloud Code Assist session) instead of an API key. Lets the Antigravity
Gemini quota cover any nucleus path that previously required
GEMINI_API_KEY.

The factory swap `NUCLEUS_LLM_PROVIDER=antigravity` is binary-compatible
with existing `get_llm_client(provider="gemini")` consumers because the
returned object exposes the same `generate_content(prompt) -> response`
shape with `.text`, `.model`, `.usage` attrs.

Auth model:
- Tokens stored at ``~/.tb/oauth_antigravity.json`` (mode 600) with the
  shape ``{access_token, refresh_token, expires_at, email, project_id}``.
- Access tokens are auto-refreshed via the Google OAuth token endpoint
  ``https://oauth2.googleapis.com/token`` when missing or expired.
- On HTTP 401 from the generateContent endpoint, force-refresh the
  bearer once and retry.

Pseudonymity discipline (carryover from claude_oauth_llm):
- Bearer never logged at any level
- Prompt body never logged (only counts + status + finish_reason)
- curl_cffi chrome120 impersonation for TLS-fingerprint parity

v1 scope (this module): generate_content + stream_content (yield-once
fallback). stream_with_tools + generate_vision raise NotImplementedError
explicitly so sovereign-workflow callers fall back to a richer provider
rather than silently degrading. v2 can add SSE streaming + tools payload
once empirically warranted.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from curl_cffi import requests as _curl_requests
except ImportError:  # pragma: no cover - tests stub via patch
    _curl_requests = None  # type: ignore[assignment]


logger = logging.getLogger("nucleus.antigravity_llm")

# ── Endpoint / client constants ─────────────────────────────────────────
# Client ID / secret mirror the opencode-antigravity-auth constants
# (public OAuth client used by the Antigravity IDE plugin).
_CLIENT_ID = (
    "1071006060591-"
    "tmhssin2h4g403ep.apps.googleusercontent.com"
)
_CLIENT_SECRET = "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"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API_ENDPOINT = "https://cloudcode-pa.googleapis.com"

_IMPERSONATE = "chrome120"
_HTTP_TIMEOUT_S = 120.0

_DEFAULT_MODEL = "gemini-2.5-flash"
_DEFAULT_MAX_TOKENS = 4096
_TOKEN_EXPIRY_SKEW_S = 60  # refresh 60s before actual expiry

# Token cache location (matches ~/.tb/oauth_<role>.json convention).
_TOKEN_DIR = Path(os.path.expanduser("~/.tb"))
_TOKEN_FILE = _TOKEN_DIR / "oauth_antigravity.json"


class AntigravityOAuthError(RuntimeError):
    """Terminal failure during Antigravity OAuth-bearer LLM call."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class AntigravityOAuthResponse:
    """Response shape matching AnthropicResponse (text + model + usage)."""

    text: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


class AntigravityOAuthLLM:
    """LLM client that routes generateContent via Google OAuth bearer.

    Drop-in shape-compatible with AnthropicLLM.generate_content().
    """

    DEFAULT_MODEL = _DEFAULT_MODEL
    DEFAULT_MAX_TOKENS = _DEFAULT_MAX_TOKENS

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        # Accept (and ignore) provider-specific kwargs so factory callers
        # don't break when swapping providers.
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tier: Any = None,
        job_type: Optional[str] = None,
        budget_mode: str = "balanced",
        **_ignored: Any,
    ) -> None:
        if _curl_requests is None:
            raise ImportError(
                "AntigravityOAuthLLM requires curl_cffi. "
                "Install with: pip install curl_cffi"
            )

        self.model_name = (
            model_name
            or os.environ.get("NUCLEUS_ANTIGRAVITY_MODEL")
            or self.DEFAULT_MODEL
        )
        self.system_instruction = system_instruction
        self.engine = "ANTIGRAVITY_OAUTH"
        self._provider_id = "antigravity"
        self.tier = tier
        self.budget_mode = budget_mode

        # State surface mirrored from AnthropicLLM.stream_with_tools so
        # consumers that read these attrs after a call (sovereign judges)
        # don't AttributeError. We don't populate them; stream_with_tools
        # is unsupported in v1.
        self.last_tool_calls: List[Dict[str, Any]] = []
        self.last_stop_reason: Optional[str] = None

        # Eager bearer fetch surfaces auth failure at construction rather
        # than at first call. Lets the factory caller fall back to a
        # different provider immediately if no bearer is available.
        self._token = self._load_token()
        self._bearer = self._resolve_access_token(force_refresh=False)

        logger.info(
            "antigravity_llm: ready model=%s engine=%s",
            self.model_name, self.engine,
        )

    # ── Token cache I/O ──────────────────────────────────────

    @staticmethod
    def _load_token() -> Dict[str, Any]:
        """Read ~/.tb/oauth_antigravity.json. Returns {} on absent/corrupt."""
        try:
            raw = _TOKEN_FILE.read_text()
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("access_token"):
                return data
        except (OSError, json.JSONDecodeError, ValueError):
            pass
        return {}

    @staticmethod
    def _save_token(token: Dict[str, Any]) -> None:
        """Persist token JSON to ~/.tb/oauth_antigravity.json mode 600.

        Creates the .tb dir if missing. Atomic write via tmp + rename so
        concurrent reads never see a partial file.
        """
        _TOKEN_DIR.mkdir(mode=0o700, exist_ok=True)
        tmp = _TOKEN_FILE.with_suffix(_TOKEN_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps(token, indent=2))
        tmp.chmod(0o600)
        tmp.replace(_TOKEN_FILE)

    # ── Bearer resolution ────────────────────────────────────

    def _resolve_access_token(self, *, force_refresh: bool) -> str:
        """Return a valid access_token, refreshing via Google OAuth if needed.

        - If ``force_refresh`` is True, always refresh using the cached
          refresh_token.
        - Otherwise, refresh only when the cached access_token is missing
          or within ``_TOKEN_EXPIRY_SKEW_S`` of expiry.
        """
        token = self._token

        needs_refresh = (
            force_refresh
            or not token.get("access_token")
            or not token.get("refresh_token")
            or int(token.get("expires_at", 0)) - _TOKEN_EXPIRY_SKEW_S <= int(time.time())
        )

        if not needs_refresh:
            return token["access_token"]

        refresh_token = token.get("refresh_token")
        if not refresh_token:
            raise AntigravityOAuthError(
                "no refresh_token cached at "
                f"{_TOKEN_FILE} — complete the Antigravity OAuth flow first"
            )

        fresh = self._refresh_access_token(refresh_token)
        # Preserve email / project_id across refresh.
        fresh.setdefault("email", token.get("email", ""))
        fresh.setdefault("project_id", token.get("project_id", ""))
        self._token = fresh
        self._save_token(fresh)
        return fresh["access_token"]

    def _refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """POST to https://oauth2.googleapis.com/token to refresh.

        Token VALUE never logged (only status_code + brief error class).
        """
        body = {
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        try:
            resp = _curl_requests.post(
                _TOKEN_URL,
                headers=headers,
                data=body,
                impersonate=_IMPERSONATE,
                timeout=30,
            )
        except Exception as exc:
            logger.warning(
                "antigravity_llm: token refresh transport error class=%s",
                type(exc).__name__,
            )
            raise AntigravityOAuthError(
                f"token refresh transport error: {type(exc).__name__}"
            ) from exc

        if not (200 <= resp.status_code < 300):
            logger.warning(
                "antigravity_llm: token refresh rejected status=%d",
                resp.status_code,
            )
            raise AntigravityOAuthError(
                f"token refresh rejected status={resp.status_code}",
                status_code=resp.status_code,
            )

        try:
            payload = resp.json()
        except Exception as exc:
            raise AntigravityOAuthError(
                f"token refresh non-json class={type(exc).__name__}"
            ) from exc

        access_token = payload.get("access_token")
        if not access_token:
            raise AntigravityOAuthError(
                "token refresh response missing access_token"
            )
        expires_in = int(payload.get("expires_in", 3600) or 3600)
        return {
            "access_token": access_token,
            "refresh_token": payload.get("refresh_token", refresh_token),
            "expires_at": int(time.time()) + expires_in,
        }

    # ── Core interface (matches AnthropicLLM) ────────────────

    def generate_content(
        self, prompt: str, **kwargs: Any,
    ) -> AntigravityOAuthResponse:
        """Generate text via generateContent with OAuth bearer.

        On HTTP 401, force-refresh the bearer once and retry. All other
        non-2xx responses propagate as AntigravityOAuthError.
        """
        session_id = os.environ.get("NUCLEUS_SESSION_ID", "default")
        agent_id = kwargs.pop("_agent_id", "default")

        # Token budget pre-check (parity with AnthropicLLM).
        try:
            from .token_budget import get_budget_manager
            if not get_budget_manager().can_execute(
                session_id=session_id, agent_id=agent_id,
            ):
                raise RuntimeError(
                    f"Token budget exceeded for session={session_id}, agent={agent_id}."
                )
        except ImportError:
            pass

        max_tokens = int(kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS))
        payload = self._compose_payload(prompt, max_tokens=max_tokens)

        parsed = self._post_with_refresh(payload)
        response = self._parse_response(parsed)
        self._record_token_usage(prompt, response, session_id, agent_id)
        self.last_stop_reason = self._extract_finish_reason(parsed)
        return response

    # Alias for legacy callers (matches DualEngineLLM/AnthropicLLM).
    generate = generate_content

    def stream_content(self, prompt: Any, **kwargs: Any):
        """Yield-once fallback. Real SSE streaming deferred to v2.

        Consumer shape preserved: yields string chunks. v1 yields the
        whole response as a single chunk after the synchronous POST
        completes. If ``prompt`` is a messages-list, collapse to the
        most-recent user-turn content.
        """
        if isinstance(prompt, list):
            prompt_text = ""
            for entry in reversed(prompt):
                if isinstance(entry, dict) and entry.get("role") == "user":
                    prompt_text = str(entry.get("content", ""))
                    break
        else:
            prompt_text = str(prompt)
        response = self.generate_content(prompt_text, **kwargs)
        if response.text:
            yield response.text

    def stream_with_tools(self, messages: List[Dict[str, Any]], **kwargs: Any):
        """Native-tool streaming. Unsupported in v1.

        Sovereign workflows that need tool-use should keep using the
        AnthropicLLM/Groq path until v2 lands curl_cffi-side SSE + tools
        payload wiring. Raising here lets callers detect missing capability
        and pick a different provider.
        """
        raise NotImplementedError(
            "AntigravityOAuthLLM v1 does not support stream_with_tools. "
            "Use provider='anthropic' or 'groq' for tool-use workflows, "
            "or override NUCLEUS_LLM_PROVIDER for this specific call site."
        )

    def generate_vision(self, *args: Any, **kwargs: Any):
        """Multimodal vision. Unsupported in v1.

        generateContent supports inline_data parts, but wiring base64
        image upload + part composition has been deferred to v2 pending
        an actual consumer.
        """
        raise NotImplementedError(
            "AntigravityOAuthLLM v1 does not support generate_vision. "
            "Use provider='gemini' or 'anthropic' for vision workflows."
        )

    # ── Internals ────────────────────────────────────────────

    def _compose_payload(
        self, prompt: str, *, max_tokens: int,
    ) -> Dict[str, Any]:
        """Compose a v1internal:generateContent request body.

        The Antigravity Cloud Code Assist API wraps the standard Gemini
        generateContent body inside a ``request`` field, with ``model`` at
        the top level. The response is similarly wrapped in a ``response``
        field. Discovered empirically 2026-07-13.
        """
        contents: List[Dict[str, Any]] = [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
        inner: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
            },
        }
        if self.system_instruction:
            inner["systemInstruction"] = {
                "parts": [{"text": self.system_instruction}],
            }
        return {
            "model": self.model_name,
            "request": inner,
        }

    def _post_with_refresh(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST generateContent; on 401 force-refresh bearer + retry once.

        Mirrors the autonomous_wake.WakeAuthError retry pattern (PR #534)
        but lives here so the provider is self-contained and doesn't
        couple to the wake-orchestration layer.
        """
        try:
            return self._post(payload, bearer=self._bearer)
        except AntigravityOAuthError as exc:
            if exc.status_code != 401:
                raise
            logger.info(
                "antigravity_llm: 401 — refreshing bearer",
            )
            fresh = self._resolve_access_token(force_refresh=True)
            if fresh == self._bearer:
                # Refresh returned the same token — bearer is fundamentally
                # invalid; propagate the original 401 rather than loop.
                raise
            self._bearer = fresh
            return self._post(payload, bearer=fresh)

    def _post(
        self, payload: Dict[str, Any], *, bearer: str,
    ) -> Dict[str, Any]:
        url = f"{_API_ENDPOINT}/v1internal:generateContent"
        headers = {
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity/1.18.3 darwin/arm64",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
            "Client-Metadata": json.dumps(
                {
                    "ideType": "ANTIGRAVITY",
                    "platform": "MACOS",
                    "pluginType": "GEMINI",
                },
                separators=(",", ":"),
            ),
        }
        try:
            resp = _curl_requests.post(
                url, headers=headers, json=payload,
                impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
            )
        except Exception as exc:
            logger.warning(
                "antigravity_llm: transport class=%s",
                type(exc).__name__,
            )
            raise AntigravityOAuthError(
                f"transport error: {type(exc).__name__}"
            ) from exc

        if not (200 <= resp.status_code < 300):
            logger.warning(
                "antigravity_llm: rejected status=%d model=%s",
                resp.status_code, self.model_name,
            )
            raise AntigravityOAuthError(
                f"inference rejected status={resp.status_code}",
                status_code=resp.status_code,
            )

        try:
            parsed = resp.json()
        except Exception as exc:
            raise AntigravityOAuthError(
                f"non-json response class={type(exc).__name__}"
            ) from exc

        # The v1internal API wraps the Gemini response in a "response" field.
        # Unwrap it so downstream parsing sees the standard Gemini shape.
        if isinstance(parsed.get("response"), dict):
            parsed = parsed["response"]

        logger.info(
            "antigravity_llm: ok model=%s finish=%s candidates=%d",
            self.model_name,
            self._extract_finish_reason(parsed),
            len(parsed.get("candidates") or []),
        )
        return parsed

    @staticmethod
    def _extract_finish_reason(parsed: Dict[str, Any]) -> str:
        candidates = parsed.get("candidates") or []
        if candidates and isinstance(candidates[0], dict):
            return str(candidates[0].get("finishReason") or "")
        return ""

    def _parse_response(
        self, parsed: Dict[str, Any],
    ) -> AntigravityOAuthResponse:
        """Extract text from generateContent candidates → flat string.

        Gemini returns content as candidates[].content.parts[].text.
        We concatenate text parts across candidates with newlines
        (matches GeminiLLM behavior).
        """
        text_parts: List[str] = []
        for candidate in parsed.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                if isinstance(part, dict) and part.get("text"):
                    text_parts.append(str(part["text"]))

        usage_meta = parsed.get("usageMetadata") or {}
        usage = {
            "input_tokens": int(usage_meta.get("promptTokenCount", 0) or 0),
            "output_tokens": int(usage_meta.get("candidatesTokenCount", 0) or 0),
        }
        return AntigravityOAuthResponse(
            text="\n".join(text_parts),
            model=parsed.get("modelVersion", self.model_name) or self.model_name,
            usage=usage,
        )

    def _record_token_usage(
        self,
        prompt: str,
        response: AntigravityOAuthResponse,
        session_id: str,
        agent_id: str,
    ) -> None:
        """Forward usage to BudgetManager. Silent on any failure."""
        try:
            from .token_budget import get_budget_manager, estimate_tokens
            input_tokens = (
                response.usage.get("input_tokens")
                or estimate_tokens(str(prompt))
            )
            output_tokens = (
                response.usage.get("output_tokens")
                or estimate_tokens(response.text)
            )
            get_budget_manager().record_usage(
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                session_id=session_id,
                agent_id=agent_id,
            )
        except Exception as exc:
            logger.debug(
                "antigravity_llm: token usage record skipped class=%s",
                type(exc).__name__,
            )

    @property
    def active_engine(self) -> str:
        return self.engine


__all__ = [
    "AntigravityOAuthLLM",
    "AntigravityOAuthResponse",
    "AntigravityOAuthError",
]
