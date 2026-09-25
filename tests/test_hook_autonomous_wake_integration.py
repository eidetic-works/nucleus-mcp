"""Integration tests for v0.3.0 Piece B — hook.py autonomous wake patch.

Per cc-peer 2026-06-09T12:15Z Piece B locked contract: 6 high-value
integration tests covering concerns 1-5 + Q5 augmentation (subject
also scrubbed).

Coverage:
1. test_unregistered_role_no_autonomous_wake_fires (concern 1)
2. test_running_session_skips_autonomous_wake (concern 2)
3. test_not_running_session_fires_autonomous_wake (concern 2)
4. test_concurrent_arrivals_coalesce_within_grace_window (concern 3)
5. test_FallbackChainError_writes_sentinel_to_op_assistant (concern 4)
6. test_relay_body_scrubbed_before_inference (concern 5)
7. test_relay_subject_scrubbed_before_inference (concern 5 Q5 augmentation)

Plus safety nets:
- test_hook_disabled_env_var_skips_all
- test_inner_exception_does_not_break_hook (PR #480 precedent)
- test_current_role_excluded_from_autonomous_wake
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.mirror import hook
from mcp_server_nucleus.sessions import (
    autonomous_wake_map as wm,
    coalesce_queue as cq,
)
from mcp_server_nucleus.sessions.fallback import FallbackChainError


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch, tmp_path):
    """Wipe MAP + coalesce queue; isolate HOME + brain to tmp."""
    wm.clear_registry()
    cq.clear_pending()
    monkeypatch.delenv("NUCLEUS_AUTONOMOUS_WAKE_DISABLED", raising=False)
    # Force grace window to ~0 so drain_ready_roles returns immediately
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "0.1")  # v0.3.1: bumped above disk I/O latency
    # Redirect HOME for any ~/.tb/ paths in modules-under-test
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    yield
    wm.clear_registry()
    cq.clear_pending()


def _write_relay(inbox: Path, *, subject: str, body, frm: str = "main",
                  ident: str = "r1") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    p = inbox / f"20260609T120000Z_{frm}_{ident}.json"
    p.write_text(json.dumps({
        "id": ident,
        "from": frm,
        "subject": subject,
        "body": body,
    }))
    return p


def _register(role="cc_tb", session_id="cse_test", org_uuid="org-test"):
    cfg = wm.AutonomousWakeConfig(
        role=role, session_id=session_id, org_uuid=org_uuid,
    )
    wm.register_autonomous_role(role, cfg)
    return cfg


def _make_brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir()
    return brain


def _stub_loader(monkeypatch):
    """Loader is invoked by _process_autonomous_wake on every call;
    stub it out so the registered MAP state survives the call (loader
    would clear + re-load from absent config file → empty MAP)."""
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.autonomous_wake_loader.load_autonomous_wake_map",
        lambda *a, **kw: 0,
    )


def _stub_bearer(monkeypatch, value: str = "STUB-OAT"):
    monkeypatch.setattr(hook, "_fetch_bearer_for_role", lambda role: value)


def _stub_discovery(monkeypatch, context=None):
    ctx = context if context is not None else {"system_prompt": "you are autonomous"}
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.discovery_context.build_discovery_context",
        lambda role, *, bearer, org_uuid: ctx,
    )


# ── Test 1: opt-in default — unregistered role no fire ──────────────────


def test_unregistered_role_no_autonomous_wake_fires(monkeypatch, tmp_path):
    """concern 1: empty MAP → list_autonomous_roles() is [] → no fire."""
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    hook._process_autonomous_wake("main", brain)

    fire.assert_not_called()


# ── Test 2: running session — skip ──────────────────────────────────────


def test_running_session_skips_autonomous_wake(monkeypatch, tmp_path):
    """concern 2: is_session_running True → skip role even if registered."""
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: True,  # ALL roles "running"
    )
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    _write_relay(brain / "relay" / "cc_tb", subject="s", body="b")
    hook._process_autonomous_wake("main", brain)

    fire.assert_not_called()


# ── Test 3: not running — fires ─────────────────────────────────────────


def test_not_running_session_fires_autonomous_wake(monkeypatch, tmp_path):
    """concern 2: is_session_running False → role fires post_relay_to_role."""
    import time as _t
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
        lambda role: "cc_tb",
    )
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    _write_relay(brain / "relay" / "cc_tb", subject="hello", body="content")
    hook._process_autonomous_wake("main", brain)
    _t.sleep(0.2)  # disk I/O latency safe (post v0.3.1)  # ensure grace window expires
    # Second invocation should drain
    hook._process_autonomous_wake("main", brain)

    fire.assert_called()
    kwargs = fire.call_args.kwargs
    assert kwargs["role"] == "cc_tb"
    assert kwargs["bearer"] == "STUB-OAT"


# ── Test 4: concurrent arrivals coalesce ────────────────────────────────


def test_concurrent_arrivals_coalesce_within_grace_window(monkeypatch, tmp_path):
    """concern 3: 3 relays → 1 fire with combined wake_instruction."""
    import time as _t
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
        lambda role: "cc_tb",
    )
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    inbox = brain / "relay" / "cc_tb"
    _write_relay(inbox, subject="subj1", body="body1", ident="r1")
    _write_relay(inbox, subject="subj2", body="body2", ident="r2")
    _write_relay(inbox, subject="subj3", body="body3", ident="r3")

    hook._process_autonomous_wake("main", brain)
    _t.sleep(0.2)  # disk I/O latency safe (post v0.3.1)
    hook._process_autonomous_wake("main", brain)

    assert fire.call_count == 1
    kwargs = fire.call_args.kwargs
    # Combined subject contains all 3
    assert "subj1" in kwargs["relay_subject"]
    assert "subj2" in kwargs["relay_subject"]
    assert "subj3" in kwargs["relay_subject"]
    # Combined body contains all 3 with numbered prefix
    assert "(1) body1" in kwargs["relay_body"]
    assert "(2) body2" in kwargs["relay_body"]
    assert "(3) body3" in kwargs["relay_body"]


# ── Test 5: FallbackChainError → sentinel ──────────────────────────────


def test_FallbackChainError_writes_sentinel_to_op_assistant(monkeypatch, tmp_path):
    """concern 4: post_relay_to_role raises → sentinel written."""
    import time as _t
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
        lambda role: "cc_tb",
    )
    # Fire raises FallbackChainError
    def _raises(**kwargs):
        raise FallbackChainError("Layer 5 inference failed for role=cc_tb: timeout")
    monkeypatch.setattr(hook, "_fire_post_relay", _raises)

    brain = _make_brain(tmp_path)
    _write_relay(brain / "relay" / "cc_tb", subject="wake me", body="please")

    hook._process_autonomous_wake("main", brain)
    _t.sleep(0.2)  # disk I/O latency safe (post v0.3.1)
    hook._process_autonomous_wake("main", brain)

    # Sentinel landed in op-assistant inbox
    op_inbox = brain / "relay" / "claude_code_operator_assistant"
    sentinels = list(op_inbox.glob("*_cc_tb_autonomous_wake_FAILED_role_cc_tb_err_*.json"))
    assert len(sentinels) == 1
    body = json.loads(sentinels[0].read_text())["body"]
    assert body["kind"] == "autonomous_wake_failure_sentinel"
    assert body["error_class_name"] == "FallbackChainError"
    assert body["role"] == "cc_tb"


# ── Test 6: relay body scrubbed before inference ───────────────────────


def test_relay_body_scrubbed_before_inference(monkeypatch, tmp_path):
    """concern 5: body identity strings → scrubbed in relay_body passed to fire."""
    import time as _t
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
        lambda role: "cc_tb",
    )
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    _write_relay(
        brain / "relay" / "cc_tb",
        subject="ok",
        body="please look at /Users/some_engineer/secret/path.py and Bearer SECRET_TOKEN_abcdef123456 too",
    )
    hook._process_autonomous_wake("main", brain)
    _t.sleep(0.2)  # disk I/O latency safe (post v0.3.1)
    hook._process_autonomous_wake("main", brain)

    fire.assert_called()
    relay_body = fire.call_args.kwargs["relay_body"]
    # Generic path + bearer patterns from pseudonymity_guard ARE applied
    assert "/Users/some_engineer/" not in relay_body
    assert "/Users/OPERATOR/" in relay_body
    assert "SECRET_TOKEN_abcdef123456" not in relay_body
    assert "Bearer SCRUBBED" in relay_body


# ── Test 7: relay subject scrubbed (Q5 augmentation) ────────────────────


def test_relay_subject_scrubbed_before_inference(monkeypatch, tmp_path):
    """Q5 augmentation per cc-peer: subject also threads into wake_instruction."""
    import time as _t
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
        lambda role: "cc_tb",
    )
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    _write_relay(
        brain / "relay" / "cc_tb",
        subject="check /Users/someone_else/file.py",
        body="ok",
    )
    hook._process_autonomous_wake("main", brain)
    _t.sleep(0.2)  # disk I/O latency safe (post v0.3.1)
    hook._process_autonomous_wake("main", brain)

    fire.assert_called()
    subject = fire.call_args.kwargs["relay_subject"]
    assert "/Users/someone_else/" not in subject
    assert "/Users/OPERATOR/" in subject


# ── Safety: env kill-switch ────────────────────────────────────────────


def test_hook_disabled_env_var_skips_all(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_AUTONOMOUS_WAKE_DISABLED", "1")
    _register("cc_tb")
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    _write_relay(brain / "relay" / "cc_tb", subject="s", body="b")
    hook._process_autonomous_wake("main", brain)
    fire.assert_not_called()


# ── Safety: inner exception must not bubble up ────────────────────────


def test_inner_exception_does_not_break_hook(monkeypatch, tmp_path):
    """PR #480 precedent: hook break = all sessions break. Outer try/except
    must absorb ALL inner failures."""
    _register("cc_tb")
    # Make load_autonomous_wake_map raise — even though our stubs should
    # bypass it, an unforeseen module-level crash must not propagate.
    def _raise(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.autonomous_wake_loader.load_autonomous_wake_map",
        _raise,
    )
    brain = _make_brain(tmp_path)
    # Must NOT raise
    hook._process_autonomous_wake("main", brain)


# ── Test: current role excluded ───────────────────────────────────────


def test_current_role_excluded_from_autonomous_wake(monkeypatch, tmp_path):
    """If the current hook role is itself registered, skip it (own session
    is the one firing the hook — Monitor / chat surface handles it)."""
    import time as _t
    _stub_loader(monkeypatch)
    _stub_bearer(monkeypatch)
    _stub_discovery(monkeypatch)
    _register("cc_tb")  # current role
    _register("cc_peer")  # different role
    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.session_presence.is_session_running",
        lambda role: False,
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
        lambda role: role,  # identity passthrough for test
    )
    fire = MagicMock()
    monkeypatch.setattr(hook, "_fire_post_relay", fire)

    brain = _make_brain(tmp_path)
    _write_relay(brain / "relay" / "cc_tb", subject="own", body="own")
    _write_relay(brain / "relay" / "cc_peer", subject="other", body="other")

    hook._process_autonomous_wake("cc_tb", brain)  # cc_tb is current role
    _t.sleep(0.2)  # disk I/O latency safe (post v0.3.1)
    hook._process_autonomous_wake("cc_tb", brain)

    # Only cc_peer fired; cc_tb (current role) skipped
    assert fire.call_count == 1
    assert fire.call_args.kwargs["role"] == "cc_peer"
