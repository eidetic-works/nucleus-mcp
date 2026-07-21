"""Claude OAuth-bearer LLM provider — Max-plan-covered /v1/messages.

Drop-in replacement for AnthropicLLM that routes /v1/messages calls
through an OAuth bearer (e.g., Claude Code / Claude.app session) instead
of an API key. Lets Max-plan quota cover any nucleus path that previously
required NUCLEUS_ANTHROPIC_API_KEY.

The factory swap `NUCLEUS_LLM_PROVIDER=claude_oauth` is binary-compatible
with existing `get_llm_client(provider="anthropic")` consumers because the
returned object exposes the same `generate_content(prompt) -> response`
shape with `.text`, `.model`, `.usage` attrs.

Auth model:
- Constructor takes ``role`` (which OAuth bearer to use). Resolved via
  mcp_server_nucleus.oauth.exchange.get_access_token(role).
- On HTTP 401 from /v1/messages, force-refresh the bearer once and retry.
- Default role from NUCLEUS_OAUTH_ROLE env, fallback "bespoq_cowork"
  (the only role with a cached refresh_token as of v0.3.x — operator can
  mint additional bearers via existing oauth.exchange paths).

Pseudonymity discipline (carryover from sessions.autonomous_wake):
- Bearer never logged at any level
- Prompt body never logged (only counts + status + stop_reason)
- curl_cffi chrome120 impersonation for TLS-fingerprint parity

v1 scope (this module): generate_content + stream_content (yield-once
fallback). stream_with_tools + generate_vision raise NotImplementedError
explicitly so sovereign-workflow callers fall back to a richer provider
rather than silently degrading. v2 can add SSE streaming + tools payload
once empirically warranted.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from curl_cffi import requests as _curl_requests
except ImportError:  # pragma: no cover - tests stub via patch
    _curl_requests = None  # type: ignore[assignment]


logger = logging.getLogger("nucleus.oauth_llm")

_API_ANTHROPIC = "https://api.anthropic.com"
_MESSAGES_URL = f"{_API_ANTHROPIC}/v1/messages?beta=true"
_ANTHROPIC_VERSION = "2023-06-01"
_IMPERSONATE = "chrome120"
_HTTP_TIMEOUT_S = 120.0

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_ROLE = "bespoq_cowork"


class ClaudeOAuthError(RuntimeError):
    """Terminal failure during OAuth-bearer LLM call."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ClaudeOAuthResponse:
    """Response shape matching AnthropicResponse (text + model + usage)."""

    text: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


class ClaudeOAuthLLM:
    """LLM client that routes /v1/messages via OAuth bearer (Max plan).

    Drop-in shape-compatible with AnthropicLLM.generate_content().
    """

    DEFAULT_MODEL = _DEFAULT_MODEL
    DEFAULT_MAX_TOKENS = _DEFAULT_MAX_TOKENS

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        role: Optional[str] = None,
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
                "ClaudeOAuthLLM requires curl_cffi. "
                "Install with: pip install curl_cffi"
            )

        self.role = role or os.environ.get("NUCLEUS_OAUTH_ROLE") or _DEFAULT_ROLE
        self.model_name = (
            model_name
            or os.environ.get("NUCLEUS_OAUTH_MODEL")
            or self.DEFAULT_MODEL
        )
        self.system_instruction = system_instruction
        self.engine = "CLAUDE_OAUTH"
        self._provider_id = "claude_oauth"
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
        self._bearer = self._fetch_bearer(force_refresh=False)

        logger.info(
            "oauth_llm: ready role=%s model=%s engine=%s",
            self.role, self.model_name, self.engine,
        )

    # ── Bearer resolution ────────────────────────────────────

    def _fetch_bearer(self, *, force_refresh: bool) -> str:
        """Resolve OAuth bearer for this provider's role.

        Lazy-imports oauth.exchange so the module is importable even when
        OAuth isn't configured (test envs).
        """
        try:
            from mcp_server_nucleus.oauth import exchange as _oauth_exchange
        except ImportError as exc:
            raise ClaudeOAuthError(
                f"oauth.exchange module unavailable: {type(exc).__name__}"
            ) from exc
        try:
            return _oauth_exchange.get_access_token(
                self.role, force_refresh=force_refresh,
            )
        except Exception as exc:
            raise ClaudeOAuthError(
                f"oauth token resolve failed role={self.role} "
                f"class={type(exc).__name__}"
            ) from exc

    # ── Core interface (matches AnthropicLLM) ────────────────

    def generate_content(self, prompt: str, **kwargs: Any) -> ClaudeOAuthResponse:
        """Generate text via /v1/messages?beta=true with OAuth bearer.

        On HTTP 401, force-refresh the bearer once and retry. All other
        non-2xx responses propagate as ClaudeOAuthError.
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
        self.last_stop_reason = parsed.get("stop_reason")
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
            "ClaudeOAuthLLM v1 does not support stream_with_tools. "
            "Use provider='anthropic' or 'groq' for tool-use workflows, "
            "or override NUCLEUS_LLM_PROVIDER for this specific call site."
        )

    def generate_vision(self, *args: Any, **kwargs: Any):
        """Multimodal vision. Unsupported in v1.

        /v1/messages?beta=true supports image content blocks, but wiring
        base64 image upload + content-block composition has been deferred
        to v2 pending an actual consumer.
        """
        raise NotImplementedError(
            "ClaudeOAuthLLM v1 does not support generate_vision. "
            "Use provider='anthropic' or 'gemini' for vision workflows."
        )

    # ── Internals ────────────────────────────────────────────

    def _compose_payload(
        self, prompt: str, *, max_tokens: int,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.system_instruction:
            payload["system"] = self.system_instruction
        return payload

    def _post_with_refresh(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/messages; on 401 force-refresh bearer + retry once.

        Mirrors the autonomous_wake.WakeAuthError retry pattern (PR #534)
        but lives here so the provider is self-contained and doesn't
        couple to the wake-orchestration layer.
        """
        try:
            return self._post(payload, bearer=self._bearer)
        except ClaudeOAuthError as exc:
            if exc.status_code != 401:
                raise
            logger.info(
                "oauth_llm: 401 — refreshing bearer role=%s", self.role,
            )
            fresh = self._fetch_bearer(force_refresh=True)
            if fresh == self._bearer:
                # Refresh returned the same token — bearer is fundamentally
                # invalid; propagate the original 401 rather than loop.
                raise
            self._bearer = fresh
            return self._post(payload, bearer=fresh)

    def _post(
        self, payload: Dict[str, Any], *, bearer: str,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {bearer}",
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            resp = _curl_requests.post(
                _MESSAGES_URL, headers=headers, json=payload,
                impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
            )
        except Exception as exc:
            logger.warning(
                "oauth_llm: transport class=%s role=%s",
                type(exc).__name__, self.role,
            )
            raise ClaudeOAuthError(
                f"transport error: {type(exc).__name__}"
            ) from exc

        if not (200 <= resp.status_code < 300):
            logger.warning(
                "oauth_llm: rejected status=%d role=%s model=%s",
                resp.status_code, self.role, self.model_name,
            )
            raise ClaudeOAuthError(
                f"inference rejected status={resp.status_code}",
                status_code=resp.status_code,
            )

        try:
            parsed = resp.json()
        except Exception as exc:
            raise ClaudeOAuthError(
                f"non-json response class={type(exc).__name__}"
            ) from exc

        logger.info(
            "oauth_llm: ok role=%s model=%s stop=%s blocks=%d",
            self.role, self.model_name,
            parsed.get("stop_reason", "?"),
            len(parsed.get("content") or []),
        )
        return parsed

    def _parse_response(
        self, parsed: Dict[str, Any],
    ) -> ClaudeOAuthResponse:
        """Extract text from /v1/messages content blocks → flat string.

        Anthropic returns content as a list of blocks. For non-tool-use
        responses they're all type='text'. We concatenate text blocks
        with newlines (matches AnthropicLLM behavior).
        """
        blocks = parsed.get("content") or []
        text_parts: List[str] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                t = block.get("text")
                if t:
                    text_parts.append(str(t))
        usage_raw = parsed.get("usage") or {}
        usage = {
            "input_tokens": int(usage_raw.get("input_tokens", 0) or 0),
            "output_tokens": int(usage_raw.get("output_tokens", 0) or 0),
        }
        return ClaudeOAuthResponse(
            text="\n".join(text_parts),
            model=parsed.get("model", self.model_name) or self.model_name,
            usage=usage,
        )

    def _record_token_usage(
        self,
        prompt: str,
        response: ClaudeOAuthResponse,
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
                "oauth_llm: token usage record skipped class=%s",
                type(exc).__name__,
            )

    @property
    def active_engine(self) -> str:
        return self.engine


__all__ = ["ClaudeOAuthLLM", "ClaudeOAuthResponse", "ClaudeOAuthError"]
