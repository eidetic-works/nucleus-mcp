"""Tests for v0.2.1 Layer A — per-role bearer resolution.

Per .brain/specs/v021_per_role_bearer_and_registry_binding.md § Layer A.
Covers 8 spec test cases + tools/relay.py _resolve_bearer helper +
runtime/relay_transport.py bearer-kwarg threading.

Substrate baseline: PR #494 (b607f852) nucleus_relay facade + PR #493
(e4e5e817) 2xx widening.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ─────────────────────────────────────────────────────────────


class _FakeMCP:
    """Stand-in for FastMCP. Captures registered tool function."""
    def __init__(self):
        self._registered = []

    def tool(self, **kwargs):
        def decorator(fn):
            self._registered.append(fn)
            return fn
        return decorator


@pytest.fixture
def relay_tool():
    """Register tools/relay.py against a FakeMCP and return the facade fn."""
    from mcp_server_nucleus.tools import relay as relay_mod
    mcp = _FakeMCP()
    pairs = relay_mod.register(mcp, helpers=None)
    assert len(pairs) == 1
    name, fn = pairs[0]
    assert name == "nucleus_relay"
    return fn


@pytest.fixture
def relay_module():
    """Return the relay module (for _resolve_bearer + RelayConfigError)."""
    from mcp_server_nucleus.tools import relay as relay_mod
    return relay_mod


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Reset env vars + HOME isolation each test."""
    for k in ("NUCLEUS_RELAY_URL", "NUCLEUS_RELAY_BEARER", "CC_SESSION_ROLE"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Isolate Path.home() to a tmp dir so per-role file tests don't pollute real ~."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Also patch Path.home() since some implementations cache
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _write_role_token(home: Path, role: str, contents: str):
    """Helper: write ~/.tb/relay_token_<role> with given contents."""
    tb_dir = home / ".tb"
    tb_dir.mkdir(exist_ok=True)
    path = tb_dir / f"relay_token_{role}"
    path.write_text(contents)
    path.chmod(0o600)
    return path


def _get_resolver(relay_module):
    """Extract the inner _resolve_bearer closure by registering the module
    against a FakeMCP. _resolve_bearer is a closure inside register(),
    not a module-level fn, so we exercise it via the facade for layer-A
    tests + via a thin extractor for unit-level coverage."""
    mcp = _FakeMCP()
    relay_module.register(mcp, helpers=None)
    # _resolve_bearer is closed-over inside register(); exercise via facade
    # for end-to-end + craft a dedicated helper-exposing variant by re-
    # registering. For unit tests we go through the facade with mocks on
    # relay_transport so the bearer resolution path is exercised.
    return mcp


# ── Spec test cases 1–8 (Layer A) ───────────────────────────────────────


async def test_case1_role_file_exists_env_empty_file_wins(relay_tool, fake_home, monkeypatch):
    """Spec § 'Test cases' #1: Role file exists; env empty → file."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    _write_role_token(fake_home, "tb", "per-role-bearer-tb")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    # bearer kwarg passed through MUST be the per-role file value
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "per-role-bearer-tb"


async def test_case2_role_file_missing_env_set_env_wins(relay_tool, fake_home, monkeypatch):
    """Spec § 'Test cases' #2: Role file missing; env set → env (v0.2.0 fallback)."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-fallback-bearer")
    # No per-role file written
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "env-fallback-bearer"


async def test_case3_both_file_and_env_file_wins(relay_tool, fake_home, monkeypatch):
    """Spec § 'Test cases' #3: Both file and env → file wins."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-bearer-should-NOT-win")
    _write_role_token(fake_home, "tb", "file-bearer-should-win")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "file-bearer-should-win"


async def test_case4_neither_set_surfaces_relay_config_error_in_dispatch_envelope(relay_tool, fake_home, monkeypatch, relay_module):
    """Spec § 'Test cases' #4: Neither set → RelayConfigError with path + role in message.

    NOTE: dispatch wraps all handler exceptions into a JSON error envelope
    rather than propagating; the spec's RelayConfigError class is verified
    via test_relay_config_error_is_subclass_of_runtime_error (separate test).
    Here we verify the envelope DOES surface the actionable RelayConfigError
    message text (path + role + env var) so callers can fix configuration.
    """
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    # No per-role file, no env bearer
    result = await relay_tool("inbox", {})
    parsed = json.loads(result)
    # Dispatch envelope has 'error' field with the exception message
    err = parsed.get("error", "")
    assert "tb" in err  # role mentioned
    assert "relay_token_tb" in err  # per-role file path mentioned
    assert "NUCLEUS_RELAY_BEARER" in err  # env fallback mentioned


async def test_case5_explicit_role_param_uses_that_roles_file(relay_tool, fake_home, monkeypatch):
    """Spec § 'Test cases' #5: Explicit role param + per-role file → that role's file."""
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    _write_role_token(fake_home, "bespoq_cowork", "bespoq-bearer-value")
    _write_role_token(fake_home, "main", "main-bearer-value")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {"role": "bespoq_cowork"})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "bespoq-bearer-value"


async def test_case6_role_from_cc_session_role_env_uses_named_role_file(relay_tool, fake_home, monkeypatch):
    """Spec § 'Test cases' #6: role from CC_SESSION_ROLE env → env-named-role's file."""
    monkeypatch.setenv("CC_SESSION_ROLE", "peer")
    _write_role_token(fake_home, "peer", "peer-bearer-value")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "peer-bearer-value"


async def test_case7_role_param_mid_call_differs_from_env_per_call_wins(relay_tool, fake_home, monkeypatch):
    """Spec § 'Test cases' #7: role param mid-call differs from env → per-call role wins."""
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    _write_role_token(fake_home, "tb", "tb-bearer")
    _write_role_token(fake_home, "main", "main-bearer")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        # First call: env-default (main)
        await relay_tool("inbox", {})
        # Second call: explicit role=tb
        await relay_tool("inbox", {"role": "tb"})
    # First call used main, second used tb
    first_kwargs = mock_read.call_args_list[0].kwargs
    second_kwargs = mock_read.call_args_list[1].kwargs
    assert first_kwargs.get("bearer") == "main-bearer"
    assert second_kwargs.get("bearer") == "tb-bearer"


async def test_case8_concurrent_calls_different_roles_no_shared_state(relay_tool, fake_home):
    """Spec § 'Test cases' #8: Concurrent calls with different roles → independent.

    Mirrors Chat-tab + Cowork-tab race condition where shared MCP subprocess
    handles overlapping in-flight calls. _resolve_bearer must read fresh
    each call (no module-level cache holding stale bearer).
    """
    _write_role_token(fake_home, "chat_tab", "chat-bearer")
    _write_role_token(fake_home, "cowork_tab", "cowork-bearer")

    captured_bearers = []
    captured_lock = threading.Lock()

    def _capturing_mock_read(role, **kwargs):
        with captured_lock:
            captured_bearers.append((role, kwargs.get("bearer")))
        return []

    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        side_effect=_capturing_mock_read,
    ):
        # Fire 10 calls alternating roles; threads to maximize race surface
        threads = []
        for i in range(10):
            role = "chat_tab" if i % 2 == 0 else "cowork_tab"
            t = threading.Thread(target=lambda r=role: asyncio.run(relay_tool("inbox", {"role": r})))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    # Every chat_tab call MUST have used chat-bearer; every cowork_tab call
    # MUST have used cowork-bearer. Cross-talk would surface as (chat_tab,
    # cowork-bearer) or vice-versa.
    for role, bearer in captured_bearers:
        if role == "chat_tab":
            assert bearer == "chat-bearer", f"chat_tab got wrong bearer: {bearer!r}"
        elif role == "cowork_tab":
            assert bearer == "cowork-bearer", f"cowork_tab got wrong bearer: {bearer!r}"
    assert len(captured_bearers) == 10


# ── Additional coverage: empty-file fallback + RelayConfigError shape ───


async def test_empty_file_treated_as_missing_falls_through_to_env(relay_tool, fake_home, monkeypatch):
    """Spec § 'Failure modes' line 78: empty file → fall through to env."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-fallback")
    _write_role_token(fake_home, "tb", "")  # empty file
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "env-fallback"


async def test_whitespace_only_file_treated_as_missing(relay_tool, fake_home, monkeypatch):
    """Whitespace-only file content (after .strip()) → fall through to env."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-fallback")
    _write_role_token(fake_home, "tb", "\n  \t\n")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "env-fallback"


async def test_role_token_trims_surrounding_whitespace(relay_tool, fake_home, monkeypatch):
    """File contents are stripped (handles trailing newline from echo > file)."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    _write_role_token(fake_home, "tb", "  bearer-with-padding  \n")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    _, kwargs = mock_read.call_args
    assert kwargs.get("bearer") == "bearer-with-padding"


def test_relay_config_error_is_subclass_of_runtime_error(relay_module):
    """RelayConfigError is a RuntimeError subclass so existing handlers work."""
    assert issubclass(relay_module.RelayConfigError, RuntimeError)


# ── post + ack action paths exercise bearer kwarg ───────────────────────


async def test_post_passes_bearer_through_to_post_relay(relay_tool, fake_home, monkeypatch):
    """post action resolves bearer + threads to relay_transport.post_relay."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    _write_role_token(fake_home, "tb", "tb-bearer-for-post")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "m1"},
    ) as mock_post:
        await relay_tool("post", {"to": "main", "subject": "x"})
    _, kwargs = mock_post.call_args
    assert kwargs.get("bearer") == "tb-bearer-for-post"


async def test_ack_passes_bearer_through_to_mark_seen(relay_tool, fake_home, monkeypatch):
    """ack action resolves bearer + threads to relay_transport.mark_seen."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    _write_role_token(fake_home, "tb", "tb-bearer-for-ack")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.mark_seen",
        return_value={"acked": 1, "failed": 0},
    ) as mock_ack:
        await relay_tool("ack", {"message_ids": ["id-1"]})
    _, kwargs = mock_ack.call_args
    assert kwargs.get("bearer") == "tb-bearer-for-ack"


async def test_post_explicit_role_param_uses_that_roles_bearer(relay_tool, fake_home, monkeypatch):
    """post supports role kwarg to identity-switch sender per-call."""
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    _write_role_token(fake_home, "bespoq_cowork", "bespoq-bearer")
    _write_role_token(fake_home, "main", "main-bearer")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "m1"},
    ) as mock_post:
        await relay_tool("post", {"to": "operator_assistant", "subject": "x", "role": "bespoq_cowork"})
    _, kwargs = mock_post.call_args
    assert kwargs.get("bearer") == "bespoq-bearer"


# ── status action stays diagnostic-only (no bearer resolution attempted) ──


async def test_status_does_not_resolve_bearer_no_raise_when_no_token(relay_tool, fake_home, monkeypatch):
    """status MUST NOT call _resolve_bearer; works even with no bearer anywhere.

    Per spec line 209 'Acceptance' + PR #494 anti-leak Crack 1 discipline:
    status is intentionally diagnostic-only and reports presence as boolean.
    """
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    # No per-role file + no env bearer
    result = await relay_tool("status", {})
    parsed = json.loads(result)
    # Should succeed without raising; bearer_set=False reflects env state
    assert parsed["bearer_set"] is False
    assert parsed["canonical_role"] == "tb"


async def test_status_bearer_set_does_not_leak_per_role_file_contents(relay_tool, fake_home, monkeypatch):
    """status must not echo per-role file bearer value."""
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    _write_role_token(fake_home, "tb", "sk-very-secret-per-role-bearer-xyz")
    result = await relay_tool("status", {})
    assert "sk-very-secret-per-role-bearer-xyz" not in result


# ── runtime/relay_transport.py bearer kwarg threading ────────────────────


def test_relay_transport_post_relay_accepts_bearer_kwarg():
    """post_relay signature accepts bearer= kwarg (v0.2.1 contract)."""
    from mcp_server_nucleus.runtime import relay_transport
    import inspect
    sig = inspect.signature(relay_transport.post_relay)
    assert "bearer" in sig.parameters


def test_relay_transport_read_inbox_accepts_bearer_kwarg():
    """read_inbox signature accepts bearer= kwarg."""
    from mcp_server_nucleus.runtime import relay_transport
    import inspect
    sig = inspect.signature(relay_transport.read_inbox)
    assert "bearer" in sig.parameters


def test_relay_transport_mark_seen_accepts_bearer_kwarg():
    """mark_seen signature accepts bearer= kwarg."""
    from mcp_server_nucleus.runtime import relay_transport
    import inspect
    sig = inspect.signature(relay_transport.mark_seen)
    assert "bearer" in sig.parameters


def test_relay_transport_resolve_bearer_explicit_wins(monkeypatch):
    """_resolve_bearer: non-None explicit kwarg wins over env."""
    from mcp_server_nucleus.runtime import relay_transport
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-bearer")
    assert relay_transport._bearer_or_raise("explicit-bearer") == "explicit-bearer"


def test_relay_transport_resolve_bearer_none_falls_to_env(monkeypatch):
    """_resolve_bearer: None falls through to NUCLEUS_RELAY_BEARER env."""
    from mcp_server_nucleus.runtime import relay_transport
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-bearer-only")
    assert relay_transport._bearer_or_raise(None) == "env-bearer-only"


def test_relay_transport_resolve_bearer_empty_string_falls_to_env(monkeypatch):
    """_resolve_bearer: empty string treated as None (defensive)."""
    from mcp_server_nucleus.runtime import relay_transport
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "env-bearer-fallback")
    assert relay_transport._bearer_or_raise("") == "env-bearer-fallback"


def test_relay_transport_resolve_bearer_neither_raises_runtime_error(monkeypatch):
    """_resolve_bearer: None + no env → RuntimeError (existing fail-loud shape)."""
    from mcp_server_nucleus.runtime import relay_transport
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://r.example.com")
    with pytest.raises(RuntimeError):
        relay_transport._bearer_or_raise(None)
