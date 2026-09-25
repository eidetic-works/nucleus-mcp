"""Unit tests for oauth_shim_http Gemini fallback path.

All HTTP is mocked — no real API calls. Tests cover:
    - Anthropic→Gemini request translation (basic / system / multi-turn)
    - Gemini→Anthropic response translation (STOP / MAX_TOKENS)
    - Key-pool: load from file, round-robin, 429 cooldown skip
    - Fallback disable env var
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import oauth_shim_http as shim


# If curl_cffi isn't installed in the test env, swap in a stub module so
# patch.object(shim._curl_requests, "post", ...) has a real attribute to bind.
if shim._curl_requests is None:
    import types
    _stub = types.SimpleNamespace(post=MagicMock())
    shim._curl_requests = _stub  # type: ignore[assignment]


# --- Translation: Anthropic -> Gemini ---------------------------------------

def test_translation_anthropic_to_gemini_basic():
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 256,
        "messages": [{"role": "user", "content": "hello"}],
    }
    out = shim._gemini_translate_request(payload)
    assert out["generationConfig"] == {"maxOutputTokens": 256}
    assert out["contents"] == [{"role": "user", "parts": [{"text": "hello"}]}]
    assert "systemInstruction" not in out


def test_translation_anthropic_to_gemini_with_system():
    payload = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 100,
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "hi"}],
    }
    out = shim._gemini_translate_request(payload)
    assert out["systemInstruction"] == {"parts": [{"text": "You are helpful."}]}
    assert out["contents"][0]["role"] == "user"


def test_translation_anthropic_to_gemini_multi_turn():
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 200,
        "messages": [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
        ],
    }
    out = shim._gemini_translate_request(payload)
    roles = [m["role"] for m in out["contents"]]
    texts = [m["parts"][0]["text"] for m in out["contents"]]
    assert roles == ["user", "model", "user"]
    assert texts == ["q1", "a1", "q2"]


def test_translation_anthropic_to_gemini_text_blocks_concat():
    payload = {
        "model": "claude-x",
        "max_tokens": 50,
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": "part1 "},
                {"type": "image", "source": {"data": "x"}},  # ignored
                {"type": "text", "text": "part2"},
            ]},
        ],
    }
    out = shim._gemini_translate_request(payload)
    assert out["contents"][0]["parts"][0]["text"] == "part1 part2"


# --- Translation: Gemini -> Anthropic ---------------------------------------

def test_translation_gemini_to_anthropic_basic():
    gemini_body = {
        "candidates": [{
            "content": {"parts": [{"text": "hello back"}], "role": "model"},
            "finishReason": "STOP",
        }],
        "usageMetadata": {
            "promptTokenCount": 5,
            "candidatesTokenCount": 7,
            "totalTokenCount": 12,
        },
        "modelVersion": "gemini-2.0-flash-001",
    }
    out = shim._gemini_translate_response(gemini_body, "claude-3-5-sonnet-20241022")
    assert out["type"] == "message"
    assert out["role"] == "assistant"
    # Critical: must NOT leak the gemini model name
    assert out["model"] == "claude-3-5-sonnet-20241022"
    assert out["content"] == [{"type": "text", "text": "hello back"}]
    assert out["stop_reason"] == "end_turn"
    assert out["stop_sequence"] is None
    assert out["usage"] == {"input_tokens": 5, "output_tokens": 7}
    assert out["id"].startswith("msg_shim_")


def test_translation_gemini_to_anthropic_max_tokens():
    gemini_body = {
        "candidates": [{
            "content": {"parts": [{"text": "truncated"}], "role": "model"},
            "finishReason": "MAX_TOKENS",
        }],
        "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 100},
    }
    out = shim._gemini_translate_response(gemini_body, "claude-x")
    assert out["stop_reason"] == "max_tokens"
    assert out["usage"]["output_tokens"] == 100


def test_translation_gemini_to_anthropic_safety_finish():
    gemini_body = {
        "candidates": [{
            "content": {"parts": [{"text": ""}], "role": "model"},
            "finishReason": "SAFETY",
        }],
        "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 0},
    }
    out = shim._gemini_translate_response(gemini_body, "claude-x")
    assert out["stop_reason"] == "stop_sequence"


# --- Key pool: load / rotation / cooldown -----------------------------------

def test_pool_load_from_file():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("  AIza_KEY_A , AIza_KEY_B,AIza_KEY_C  ,   ,AIza_KEY_D\n")
        path = f.name
    try:
        pool = shim._gemini_load_pool(path)
        assert pool.size == 4
        # Round-robin to verify load order + stripping
        keys_seen = [pool.next_key()[1] for _ in range(4)]
        assert keys_seen == ["AIza_KEY_A", "AIza_KEY_B", "AIza_KEY_C", "AIza_KEY_D"]
    finally:
        os.unlink(path)


def test_pool_load_missing_file_returns_empty():
    pool = shim._gemini_load_pool("/nonexistent/path/keys.txt")
    assert pool.size == 0
    assert pool.next_key() is None


def test_pool_rotation_round_robin():
    pool = shim._GeminiKeyPool(["k1", "k2", "k3", "k4", "k5"])
    seen = [pool.next_key()[1] for _ in range(5)]
    assert seen == ["k1", "k2", "k3", "k4", "k5"]
    # Wraps around
    assert pool.next_key()[1] == "k1"


def test_pool_skip_cooldown_key():
    pool = shim._GeminiKeyPool(["k1", "k2", "k3"])
    # Pick k1, then mark it cooled
    idx, key = pool.next_key(now=1000.0)
    assert key == "k1" and idx == 0
    pool.mark_cooldown(0, now=1000.0)
    # Within cooldown window, k1 must be skipped
    next_picks = [pool.next_key(now=1010.0)[1] for _ in range(4)]
    assert "k1" not in next_picks
    assert set(next_picks) == {"k2", "k3"}
    # After cooldown window, k1 returns
    later = pool.next_key(now=1000.0 + shim._GEMINI_COOLDOWN_S + 1.0)
    assert later is not None
    # Eventually k1 will be re-selected; do up to size rotations
    found_k1 = False
    keys_post = [later[1]]
    for _ in range(5):
        keys_post.append(pool.next_key(now=1100.0)[1])
    assert "k1" in keys_post


def test_pool_all_cooled_returns_none():
    pool = shim._GeminiKeyPool(["k1", "k2"])
    pool.mark_cooldown(0, now=1000.0)
    pool.mark_cooldown(1, now=1000.0)
    assert pool.next_key(now=1010.0) is None


# --- Fallback disable env var -----------------------------------------------

def test_fallback_disabled_env_var(monkeypatch):
    monkeypatch.setenv("NUCLEUS_GEMINI_FALLBACK_DISABLED", "1")
    assert shim._gemini_fallback_disabled() is True


def test_fallback_enabled_by_default(monkeypatch):
    monkeypatch.delenv("NUCLEUS_GEMINI_FALLBACK_DISABLED", raising=False)
    assert shim._gemini_fallback_disabled() is False


def test_fallback_model_default(monkeypatch):
    monkeypatch.delenv("NUCLEUS_GEMINI_FALLBACK_MODEL", raising=False)
    assert shim._gemini_fallback_model() == "gemini-2.0-flash"


def test_fallback_model_env_override(monkeypatch):
    monkeypatch.setenv("NUCLEUS_GEMINI_FALLBACK_MODEL", "gemini-1.5-pro")
    assert shim._gemini_fallback_model() == "gemini-1.5-pro"


# --- _gemini_try_fallback end-to-end with mocked curl_cffi.post -------------

def _make_mock_resp(status: int, json_body):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_body
    m.text = "" if isinstance(json_body, dict) else str(json_body)
    return m


def test_gemini_try_fallback_success_first_key():
    pool = shim._GeminiKeyPool(["k1", "k2", "k3"])
    anthropic_payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "ping"}],
    }
    gemini_body = {
        "candidates": [{
            "content": {"parts": [{"text": "pong"}], "role": "model"},
            "finishReason": "STOP",
        }],
        "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
    }
    with patch.object(shim, "_gemini_pool", pool), \
         patch.object(shim._curl_requests, "post",
                      return_value=_make_mock_resp(200, gemini_body)) as p:
        result = shim._gemini_try_fallback(anthropic_payload)
    assert result is not None
    status, body = result
    assert status == 200
    assert body["model"] == "claude-3-5-sonnet-20241022"
    assert body["content"][0]["text"] == "pong"
    assert p.call_count == 1


def test_gemini_try_fallback_rotates_past_429():
    pool = shim._GeminiKeyPool(["k1", "k2"])
    anthropic_payload = {
        "model": "claude-x",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "hi"}],
    }
    ok_body = {
        "candidates": [{
            "content": {"parts": [{"text": "ok"}], "role": "model"},
            "finishReason": "STOP",
        }],
        "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
    }
    responses = [
        _make_mock_resp(429, {"error": "quota"}),
        _make_mock_resp(200, ok_body),
    ]
    with patch.object(shim, "_gemini_pool", pool), \
         patch.object(shim._curl_requests, "post", side_effect=responses):
        result = shim._gemini_try_fallback(anthropic_payload)
    assert result is not None
    assert result[0] == 200
    # 429'd key (k1, idx=0) is now in cooldown
    assert 0 in pool._cooldown_until


def test_gemini_try_fallback_pool_empty():
    with patch.object(shim, "_gemini_pool", shim._GeminiKeyPool([])):
        result = shim._gemini_try_fallback({"model": "x", "messages": []})
    assert result is None


def test_gemini_try_fallback_all_keys_fail():
    pool = shim._GeminiKeyPool(["k1", "k2"])
    with patch.object(shim, "_gemini_pool", pool), \
         patch.object(shim._curl_requests, "post",
                      side_effect=RuntimeError("boom")):
        result = shim._gemini_try_fallback(
            {"model": "x", "max_tokens": 10,
             "messages": [{"role": "user", "content": "p"}]}
        )
    assert result is None


# --- Failure classifier -----------------------------------------------------

@pytest.mark.parametrize("status,expected", [
    (200, False),
    (400, False),  # real client error — NEVER fallback
    (401, True),   # post-refresh 401 → fallback
    (403, False),  # real client error
    (404, False),  # real client error (bad model)
    (429, True),
    (500, True),
    (502, True),
    (503, True),
    (599, True),
])
def test_should_fallback_classifier(status, expected):
    assert shim._should_fallback(status, {}) is expected
