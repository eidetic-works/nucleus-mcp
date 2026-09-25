"""Unit tests for the NUCLEUS_CHAT_BACKEND switch (`_chat_shim_config`).

Covers the guardrails the helper enforces (see DECISIONS.md ADR-0040):
  - (3) one-move kill-switch: default (anthropic_direct) bypasses.
  - (2) interactive only: a batch run never routes through the switch.
  - endpoint is env-only: =shim with no NUCLEUS_CHAT_SHIM_URL is a safe no-op
    (no host is baked into the shipped source).
"""
from __future__ import annotations

import os
from unittest.mock import patch

from mcp_server_nucleus.cli import _chat_shim_config, _CHAT_SHIM_ROLE

_URL = "https://example-shim.invalid"


def _env(**overrides):
    """Clean env with the two relevant keys removed, then overrides applied."""
    base = {k: v for k, v in os.environ.items()
            if k not in ("NUCLEUS_CHAT_BACKEND", "NUCLEUS_CHAT_SHIM_URL")}
    base.update(overrides)
    return base


def test_default_is_anthropic_direct():
    with patch.dict(os.environ, _env(), clear=True):
        assert _chat_shim_config(batch=False) is None


def test_anthropic_direct_explicit_bypasses():
    with patch.dict(os.environ, _env(NUCLEUS_CHAT_BACKEND="anthropic_direct"), clear=True):
        assert _chat_shim_config(batch=False) is None


def test_shim_interactive_routes():
    with patch.dict(
        os.environ,
        _env(NUCLEUS_CHAT_BACKEND="shim", NUCLEUS_CHAT_SHIM_URL=_URL),
        clear=True,
    ):
        cfg = _chat_shim_config(batch=False)
    assert cfg is not None
    assert cfg["provider"] == "anthropic"
    assert cfg["base_url"] == _URL
    assert cfg["role"] == _CHAT_SHIM_ROLE
    # UA override is scoped to the shim path so the endpoint never sees the SDK's
    # default User-Agent (which the proxy front-end rejects); the anthropic_direct
    # path is untouched and keeps the native SDK UA.
    assert cfg["user_agent"].startswith("nucleus-mcp/")


def test_shim_batch_is_ignored():
    """Guardrail 2: batch/non-interactive never routes through the switch."""
    with patch.dict(
        os.environ,
        _env(NUCLEUS_CHAT_BACKEND="shim", NUCLEUS_CHAT_SHIM_URL=_URL),
        clear=True,
    ):
        assert _chat_shim_config(batch=True) is None


def test_shim_without_url_is_safe_noop():
    with patch.dict(os.environ, _env(NUCLEUS_CHAT_BACKEND="shim"), clear=True):
        assert _chat_shim_config(batch=False) is None


def test_backend_value_is_case_and_space_insensitive():
    with patch.dict(
        os.environ,
        _env(NUCLEUS_CHAT_BACKEND="  SHIM  ", NUCLEUS_CHAT_SHIM_URL=_URL),
        clear=True,
    ):
        assert _chat_shim_config(batch=False) is not None
