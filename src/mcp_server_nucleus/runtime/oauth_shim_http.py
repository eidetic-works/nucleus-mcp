"""HTTP shim — Anthropic Messages API backed by Claude Max OAuth, with Gemini fallback.

Fallback chain per POST /v1/messages:
    1. Anthropic upstream via Max-plan OAuth bearer (auto-refresh on 401).
    2. On 401-after-refresh / 429 / 5xx / transport error → translate request
       to Gemini shape, call generativelanguage.googleapis.com using a key
       from the round-robin pool, translate response back to Anthropic shape.
    3. If Gemini also fails (pool empty/cooled/erroring), return the ORIGINAL
       Anthropic error so the caller sees normal upstream behavior.

Caller wire (unchanged from v1): native Anthropic Messages JSON in, native
Anthropic response out. Extra response header `x-shim-backend: anthropic|gemini`
exposes routing. 400/403/404 are NEVER fallback-worthy (real client errors).

Env contract:
    NUCLEUS_OAUTH_SHIM_SECRET            shared secret (REQUIRED)
    NUCLEUS_OAUTH_ROLE                   default "bespoq_cowork"
    NUCLEUS_GEMINI_KEYS_FILE             comma-separated AIza... keys file
                                         (default /etc/nucleus-oauth/gemini_keys.txt)
    NUCLEUS_GEMINI_FALLBACK_MODEL        default "gemini-2.0-flash"
    NUCLEUS_GEMINI_FALLBACK_DISABLED     "1" disables fallback (v1 behavior)

Hard rules: never log bearer / shared secret / any Gemini key (length+index only);
never log prompt or response body (counts + status only).

Fresh-deploy operators: see ``infra/oauth-shim/README.md`` for host setup
(uid 10001 chown, bearer + Gemini pool placement, compose env contract).
"""
from __future__ import annotations

import argparse
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    from curl_cffi import requests as _curl_requests
except ImportError as _imp_err:
    _curl_requests = None  # type: ignore[assignment]
    _IMPORT_ERR = _imp_err
else:
    _IMPORT_ERR = None

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
import hmac


logger = logging.getLogger("nucleus.oauth_shim")

_API_ANTHROPIC = "https://api.anthropic.com"
_MESSAGES_URL = f"{_API_ANTHROPIC}/v1/messages?beta=true"
_ANTHROPIC_VERSION = "2023-06-01"
_IMPERSONATE = "chrome120"
_HTTP_TIMEOUT_S = 600.0
_DEFAULT_ROLE = "bespoq_cowork"

# --- Gemini fallback constants -----------------------------------------------
_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"
_GEMINI_DEFAULT_KEYS_FILE = "/etc/nucleus-oauth/gemini_keys.txt"
_GEMINI_COOLDOWN_S = 60.0
_GEMINI_FINISH_MAP = {
    "STOP": "end_turn",
    "MAX_TOKENS": "max_tokens",
    "SAFETY": "stop_sequence",
}


def _shared_secret() -> str:
    secret = os.environ.get("NUCLEUS_OAUTH_SHIM_SECRET", "")
    if not secret:
        raise RuntimeError(
            "NUCLEUS_OAUTH_SHIM_SECRET env var is required — shim refuses to "
            "start with an empty shared secret (would accept any caller)."
        )
    return secret


def _resolve_bearer(role: str, *, force_refresh: bool) -> str:
    from mcp_server_nucleus.oauth import exchange as _oauth_exchange
    return _oauth_exchange.get_access_token(role, force_refresh=force_refresh)


def _post_upstream(payload: Dict[str, Any], bearer: str) -> "tuple[int, Dict[str, Any] | str]":
    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = _curl_requests.post(
        _MESSAGES_URL, headers=headers, json=payload,
        impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
    )
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


# --- Gemini key pool ---------------------------------------------------------

class _GeminiKeyPool:
    """Round-robin Gemini key pool with per-key 429 cooldown."""

    def __init__(self, keys: List[str]) -> None:
        self._keys = [k.strip() for k in keys if k.strip()]
        self._cooldown_until: Dict[int, float] = {}
        self._idx = 0
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        return len(self._keys)

    def next_key(self, now: Optional[float] = None) -> Optional[Tuple[int, str]]:
        """Return (index, key) of next available key, or None if all in cooldown."""
        if not self._keys:
            return None
        now = now if now is not None else time.time()
        with self._lock:
            n = len(self._keys)
            for _ in range(n):
                i = self._idx % n
                self._idx = (self._idx + 1) % n
                until = self._cooldown_until.get(i, 0.0)
                if until <= now:
                    return i, self._keys[i]
            return None

    def mark_cooldown(self, idx: int, now: Optional[float] = None) -> None:
        now = now if now is not None else time.time()
        with self._lock:
            self._cooldown_until[idx] = now + _GEMINI_COOLDOWN_S


def _gemini_load_pool(path: Optional[str] = None) -> _GeminiKeyPool:
    """Load comma-separated keys from file. Returns empty pool on read failure."""
    target = path or os.environ.get("NUCLEUS_GEMINI_KEYS_FILE") or _GEMINI_DEFAULT_KEYS_FILE
    try:
        with open(target, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as exc:
        logger.warning(
            "gemini_pool: load failed path=%s class=%s",
            target, type(exc).__name__,
        )
        return _GeminiKeyPool([])
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    logger.info("gemini_pool: loaded %d keys from %s", len(keys), target)
    return _GeminiKeyPool(keys)


# Module-level singleton; lazily initialised by build_app(). Tests may
# patch _gemini_pool directly.
_gemini_pool: Optional[_GeminiKeyPool] = None


def _gemini_fallback_disabled() -> bool:
    return os.environ.get("NUCLEUS_GEMINI_FALLBACK_DISABLED", "") == "1"


def _gemini_fallback_model() -> str:
    return os.environ.get("NUCLEUS_GEMINI_FALLBACK_MODEL") or _GEMINI_DEFAULT_MODEL


def _gemini_translate_request(anthropic_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Translate Anthropic Messages request → Gemini generateContent request."""
    out: Dict[str, Any] = {"contents": []}

    max_tokens = anthropic_payload.get("max_tokens")
    if isinstance(max_tokens, int):
        out["generationConfig"] = {"maxOutputTokens": max_tokens}

    system = anthropic_payload.get("system")
    if isinstance(system, str) and system:
        out["systemInstruction"] = {"parts": [{"text": system}]}

    for msg in anthropic_payload.get("messages", []) or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        gemini_role = "model" if role == "assistant" else "user"
        content = msg.get("content")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    t = block.get("text")
                    if isinstance(t, str):
                        parts.append(t)
            text = "".join(parts)
        if not text:
            continue
        out["contents"].append({"role": gemini_role, "parts": [{"text": text}]})

    return out


def _gemini_translate_response(
    gemini_body: Dict[str, Any], original_model: str,
) -> Dict[str, Any]:
    """Translate Gemini generateContent response → Anthropic Messages response."""
    candidates = gemini_body.get("candidates") or []
    text_parts: List[str] = []
    finish_reason = "STOP"
    if candidates:
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        content = first.get("content") or {}
        for part in content.get("parts") or []:
            if isinstance(part, dict):
                t = part.get("text")
                if isinstance(t, str):
                    text_parts.append(t)
        fr = first.get("finishReason")
        if isinstance(fr, str):
            finish_reason = fr

    usage = gemini_body.get("usageMetadata") or {}
    input_tokens = usage.get("promptTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0)

    msg_id = "msg_shim_" + uuid.uuid4().hex[:22]
    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": original_model,
        "content": [{"type": "text", "text": "".join(text_parts)}],
        "stop_reason": _GEMINI_FINISH_MAP.get(finish_reason, "end_turn"),
        "stop_sequence": None,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


def _gemini_call_once(
    gemini_payload: Dict[str, Any], key: str, model: str,
) -> Tuple[int, Dict[str, Any] | str]:
    url = f"{_GEMINI_API_BASE}/{model}:generateContent?key={key}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    resp = _curl_requests.post(
        url, headers=headers, json=gemini_payload,
        impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
    )
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


def _gemini_try_fallback(
    anthropic_payload: Dict[str, Any],
) -> Optional[Tuple[int, Dict[str, Any]]]:
    """Attempt Gemini fallback. Returns (status, anthropic-shape body) on success,
    None if pool exhausted / transport-failed for every available key."""
    pool = _gemini_pool
    if pool is None or pool.size == 0:
        logger.warning("gemini_fallback: pool empty/uninitialised")
        return None
    original_model = anthropic_payload.get("model", "unknown")
    gemini_payload = _gemini_translate_request(anthropic_payload)
    gemini_model = _gemini_fallback_model()

    attempts = 0
    while attempts < pool.size:
        attempts += 1
        picked = pool.next_key()
        if picked is None:
            logger.warning("gemini_fallback: all %d keys in cooldown", pool.size)
            return None
        idx, key = picked
        logger.info(
            "gemini_fallback: attempt %d using pool key %d/%d (len=%d)",
            attempts, idx + 1, pool.size, len(key),
        )
        try:
            status, body = _gemini_call_once(gemini_payload, key, gemini_model)
        except Exception as exc:
            logger.warning(
                "gemini_fallback: transport class=%s key_idx=%d",
                type(exc).__name__, idx,
            )
            continue
        if status == 429:
            pool.mark_cooldown(idx)
            logger.warning("gemini_fallback: 429 key_idx=%d cooldown set", idx)
            continue
        if 200 <= status < 300 and isinstance(body, dict):
            translated = _gemini_translate_response(body, original_model)
            return status, translated
        # 4xx (other) / 5xx — try next key
        logger.warning("gemini_fallback: status=%d key_idx=%d", status, idx)
    return None


# --- Failure classifier ------------------------------------------------------

def _should_fallback(status: int, _body: Dict[str, Any] | str) -> bool:
    """True iff Anthropic outcome warrants Gemini fallback.

    400/403/404 are NOT fallback-worthy — they're real client errors that should
    surface verbatim. 401 reaching this point already survived a bearer refresh.
    """
    if status == 429 or status >= 500:
        return True
    if status == 401:
        return True
    return False


# --- HTTP handlers -----------------------------------------------------------

async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "shim": "oauth", "version": "v2"})


def _err_response(status: int, body: Dict[str, Any] | str, backend: str) -> Response:
    headers = {"x-shim-backend": backend}
    if isinstance(body, dict):
        return JSONResponse(body, status_code=status, headers=headers)
    return PlainTextResponse(str(body), status_code=status, headers=headers)


async def messages(request: Request) -> Response:
    expected_secret = _shared_secret()
    presented = request.headers.get("x-api-key", "")
    if not hmac.compare_digest(presented, expected_secret):
        logger.warning(
            "oauth_shim: auth reject ua=%s ip=%s presented_len=%d",
            request.headers.get("user-agent", "?")[:40],
            request.client.host if request.client else "?",
            len(presented),
        )
        return JSONResponse(
            {"type": "error", "error": {"type": "authentication_error",
             "message": "invalid x-api-key"}}, status_code=401,
        )

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"type": "error", "error": {"type": "invalid_request_error",
             "message": "body is not valid JSON"}}, status_code=400,
        )

    role = os.environ.get("NUCLEUS_OAUTH_ROLE") or _DEFAULT_ROLE
    try:
        bearer = _resolve_bearer(role, force_refresh=False)
    except Exception as exc:
        logger.warning(
            "oauth_shim: bearer resolve failed role=%s class=%s",
            role, type(exc).__name__,
        )
        return JSONResponse(
            {"type": "error", "error": {"type": "api_error",
             "message": f"bearer resolve failed: {type(exc).__name__}"}},
            status_code=502,
        )

    transport_failed = False
    try:
        status, body = _post_upstream(payload, bearer)
    except Exception as exc:
        logger.warning("oauth_shim: transport class=%s", type(exc).__name__)
        transport_failed = True
        status, body = 502, {
            "type": "error",
            "error": {"type": "api_error",
                      "message": f"transport error: {type(exc).__name__}"},
        }

    if not transport_failed and status == 401:
        logger.info("oauth_shim: 401 from upstream — refreshing bearer role=%s", role)
        try:
            fresh = _resolve_bearer(role, force_refresh=True)
            if fresh != bearer:
                status, body = _post_upstream(payload, fresh)
        except Exception as exc:
            logger.warning(
                "oauth_shim: bearer refresh failed class=%s", type(exc).__name__,
            )
            # leave status/body as-is; fallback decision happens below

    # Decide on Gemini fallback (transport failure OR fallback-worthy status)
    needs_fallback = transport_failed or _should_fallback(status, body)
    if needs_fallback and not _gemini_fallback_disabled():
        logger.info(
            "oauth_shim: fallback->gemini anthropic_status=%d model=%s",
            status, payload.get("model", "?"),
        )
        fb = _gemini_try_fallback(payload)
        if fb is not None:
            fb_status, fb_body = fb
            logger.info("oauth_shim: gemini ok status=%d", fb_status)
            return JSONResponse(
                fb_body, status_code=fb_status,
                headers={"x-shim-backend": "gemini"},
            )
        logger.warning(
            "oauth_shim: gemini fallback exhausted — returning original anthropic error",
        )

    logger.info(
        "oauth_shim: ok status=%d role=%s model=%s backend=anthropic",
        status, role, payload.get("model", "?"),
    )
    return _err_response(status, body, backend="anthropic")


def build_app() -> Starlette:
    if _curl_requests is None:
        raise ImportError(
            f"oauth_shim_http requires curl_cffi (install: pip install curl_cffi). "
            f"Original error: {_IMPORT_ERR}"
        )
    _shared_secret()  # fail fast if missing
    global _gemini_pool
    if _gemini_pool is None:
        _gemini_pool = _gemini_load_pool()
    return Starlette(debug=False, routes=[
        Route("/health", health, methods=["GET"]),
        Route("/v1/messages", messages, methods=["POST"]),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Nucleus OAuth shim — Max-plan API arbitrage.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8890)
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = build_app()
    import uvicorn  # local import so the module is importable without uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
