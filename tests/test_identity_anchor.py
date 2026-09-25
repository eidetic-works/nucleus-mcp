"""Tests for NUCLEUS_IDENTITY_ANCHOR — kernel-anchored session-envelope ownership.

Three buckets:
  (a) FLAG-OFF == BASELINE  — every new code path short-circuits; payload shape,
      ancestry match, and unregister are byte-for-byte today's behavior.
  (b) FLAG-ON LEGITIMATE     — the real registrant stamps pid+create_time
      server-side and can heartbeat / unregister / be found in ancestry.
  (c) FLAG-ON FORGERY FAILS  — a lane cannot mint an envelope for a foreign
      process, cannot delete/keep-alive a victim's envelope, and a
      recycled-PID / stale-create_time envelope is skipped at read.

The flag is default-OFF (autouse fixture deletes it); flag-ON tests set it
explicitly. ps-dependent assertions are skipped where ps/create_time is
unreadable (Windows / restricted CI) — there the flag is inert (fail-open),
so there is nothing to prove.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

from mcp_server_nucleus.sessions import registry

# ps-availability probe: anchoring only engages where `ps -o lstart=` works and
# the caller has a real kernel lineage. Where it doesn't, the flag degrades to
# today's pid-only path (fail-open), so the forgery guards have nothing to assert.
_PS_WORKS = (
    len(registry._caller_lineage()) > 1
    and registry._pid_create_time(os.getpid()) is not None
)
requires_ps = pytest.mark.skipif(
    not _PS_WORKS, reason="ps/create_time unavailable — anchoring is fail-open (inert)"
)

_BASELINE_KEYS = {
    "session_id", "agent", "role", "worktree_path", "pid",
    "registered_at", "last_heartbeat", "heartbeat_interval_s",
    "provider", "primitive_version",
}


@pytest.fixture(autouse=True)
def registry_root(tmp_path, monkeypatch):
    """Isolate the registry to a tmp dir and force the flag OFF by default."""
    monkeypatch.delenv("NUCLEUS_IDENTITY_ANCHOR", raising=False)
    root = tmp_path / "agent_registry"
    monkeypatch.setenv("NUCLEUS_AGENT_REGISTRY", str(root))
    return root


@pytest.fixture
def victim_pid():
    """A live process that is NOT in the test's kernel lineage (a child, not an ancestor)."""
    proc = subprocess.Popen(["sleep", "30"])
    try:
        yield proc.pid
    finally:
        proc.kill()
        proc.wait()


# ── (a) FLAG-OFF == BASELINE ────────────────────────────────────────────────


def test_flag_off_payload_shape_unchanged(registry_root):
    """Flag unset → exact 10-key payload of today, no create_time, pid=os.getpid()."""
    env = registry.register_session(
        session_id="off-shape", agent="claude_code", role="claude_code_main",
        provider="claude_anthropic",
    )
    assert set(env.keys()) == _BASELINE_KEYS
    assert "create_time" not in env
    assert env["pid"] == os.getpid()


def test_flag_off_ancestry_match_unchanged(registry_root, monkeypatch):
    """Flag unset → synthetic non-live pid still matches (no create_time gate)."""
    monkeypatch.setattr(registry, "_walk_ppid_ancestry", lambda *a, **kw: [4242])
    registry.register_session(
        session_id="off-anc", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=4242,
    )
    match = registry.find_session_in_ancestry()
    assert match is not None
    assert match["session_id"] == "off-anc"


def test_flag_off_unregister_needs_no_ownership(registry_root):
    """Flag unset → a foreign-pid envelope is freely deletable (returns True)."""
    registry.register_session(
        session_id="off-unreg", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=4242,
    )
    assert registry.unregister("off-unreg") is True


# ── (b) FLAG-ON LEGITIMATE REGISTRATION WORKS ───────────────────────────────


@requires_ps
def test_anchor_register_stamps_server_side(registry_root, monkeypatch):
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    env = registry.register_session(
        session_id="on-stamp", agent="claude_code", role="claude_code_main",
        provider="claude_anthropic", pid=None,
    )
    assert env["pid"] == os.getppid()
    assert env["create_time"] == registry._pid_create_time(os.getppid())
    assert env["create_time"]  # non-empty on macOS/Linux


@requires_ps
def test_anchor_register_accepts_own_lineage(registry_root, monkeypatch):
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    env = registry.register_session(
        session_id="on-self", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=os.getpid(),
    )
    assert env["pid"] == os.getpid()
    assert env["create_time"] == registry._pid_create_time(os.getpid())


@requires_ps
def test_anchor_owner_heartbeat_and_unregister_ok(registry_root, monkeypatch):
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    registry.register_session(
        session_id="on-owner", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=None,
    )
    hb = registry.heartbeat("on-owner")
    assert hb["session_id"] == "on-owner"
    assert registry.unregister("on-owner") is True


@requires_ps
def test_anchor_ancestry_match_validates_create_time(registry_root, monkeypatch):
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    registry.register_session(
        session_id="on-anc", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=None,
    )
    ppid = os.getppid()
    monkeypatch.setattr(registry, "_walk_ppid_ancestry", lambda *a, **kw: [ppid])
    match = registry.find_session_in_ancestry()
    assert match is not None
    assert match["session_id"] == "on-anc"


def test_anchor_fail_open_no_ps(registry_root, monkeypatch):
    """Flag ON but ps unavailable → register/heartbeat/unregister behave as flag-OFF."""
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    monkeypatch.setattr(registry, "_pid_create_time", lambda pid: None)
    monkeypatch.setattr(registry, "_walk_ppid_ancestry", lambda *a, **kw: [])
    env = registry.register_session(
        session_id="on-failopen", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=None,
    )
    # No create_time key — same shape as flag-OFF (fail-open to pid-only envelope).
    assert "create_time" not in env
    assert env["pid"] == os.getppid()
    # Grandfathered / lineage-empty → ownership guard is inert.
    hb = registry.heartbeat("on-failopen")
    assert hb["session_id"] == "on-failopen"
    assert registry.unregister("on-failopen") is True


# ── (c) FLAG-ON FORGERY FAILS ───────────────────────────────────────────────


@requires_ps
def test_anchor_rejects_foreign_pid_at_register(registry_root, monkeypatch, victim_pid):
    """A lane cannot mint an envelope claiming a process outside its lineage."""
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    with pytest.raises(ValueError, match="not in the registering process lineage"):
        registry.register_session(
            session_id="imp", agent="claude_code", role="claude_code_main",
            provider="claude_anthropic", pid=victim_pid,
        )


@requires_ps
def test_anchor_blocks_unregister_and_heartbeat_of_victim(registry_root, monkeypatch, victim_pid):
    """A session genuinely owned by a DIFFERENT live process cannot be
    heartbeat-kept-alive or deleted by a non-owning caller."""
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    now = registry._utcnow_iso()
    payload = {
        "session_id": "victim-sess", "agent": "claude_code", "role": "primary",
        "worktree_path": None, "pid": victim_pid,
        "registered_at": now, "last_heartbeat": now,
        "heartbeat_interval_s": 30, "provider": "claude_anthropic",
        "primitive_version": registry.PRIMITIVE_VERSION,
        "create_time": registry._pid_create_time(victim_pid),
    }
    assert payload["create_time"]  # victim is live — real create_time
    registry._atomic_write(registry._envelope_path("victim-sess"), payload)

    with pytest.raises(PermissionError):
        registry.heartbeat("victim-sess")
    with pytest.raises(PermissionError):
        registry.unregister("victim-sess")


@requires_ps
def test_anchor_recycled_pid_rejected_at_match(registry_root, monkeypatch, victim_pid):
    """A stale/forged create_time (PID recycling) is skipped at read and
    reported dead even with a fresh heartbeat."""
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    fresh = registry._utcnow_iso()
    payload = {
        "session_id": "recycled", "agent": "claude_code", "role": "primary",
        "worktree_path": None, "pid": victim_pid,
        "registered_at": fresh, "last_heartbeat": fresh,
        "heartbeat_interval_s": 30, "provider": "claude_anthropic",
        "primitive_version": registry.PRIMITIVE_VERSION,
        "create_time": "Mon Jan  1 00:00:00 2001",  # stale / forged
    }
    registry._atomic_write(registry._envelope_path("recycled"), payload)
    monkeypatch.setattr(registry, "_walk_ppid_ancestry", lambda *a, **kw: [victim_pid])

    # alive-filtered read: stale create_time → not alive → not indexed → None.
    assert registry.find_session_in_ancestry() is None
    # forensic read (alive_only=False): envelope survives liveness but the
    # closest-ancestor loop skips it on create_time mismatch (E7) → None.
    assert registry.find_session_in_ancestry(alive_only=False) is None
    # _is_alive returns False despite the fresh heartbeat (E6).
    assert registry._is_alive(payload) is False


# ── (c) FORGE-CONFIRMED ROUND-1 HOLES — regression guards ────────────────────


@requires_ps
def test_anchor_rejects_reregister_over_anchored_victim(registry_root, monkeypatch, victim_pid):
    """HOLE 1 regression: a non-owning caller CANNOT overwrite (re-register) an
    ANCHORED victim's envelope. The write leg is now guarded exactly like the
    delete/heartbeat legs → PermissionError, and the victim envelope is untouched.
    """
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    now = registry._utcnow_iso()
    victim = {
        "session_id": "victim-reg", "agent": "claude_code", "role": "primary",
        "worktree_path": None, "pid": victim_pid,
        "registered_at": now, "last_heartbeat": now,
        "heartbeat_interval_s": 30, "provider": "claude_anthropic",
        "primitive_version": registry.PRIMITIVE_VERSION,
        "create_time": registry._pid_create_time(victim_pid),  # anchored, real
    }
    assert victim["create_time"]  # victim is live — real create_time
    registry._atomic_write(registry._envelope_path("victim-reg"), victim)

    with pytest.raises(PermissionError):
        registry.register_session(
            session_id="victim-reg", agent="attacker", role="primary",
            provider="claude_anthropic", pid=None,
        )

    # The envelope was NOT seized: agent/pid/create_time are the victim's.
    after = json.loads(registry._envelope_path("victim-reg").read_text(encoding="utf-8"))
    assert after["agent"] == "claude_code"
    assert after["pid"] == victim_pid
    assert after["create_time"] == victim["create_time"]


@requires_ps
def test_anchor_path_shim_ps_cannot_disable_anchor(registry_root, monkeypatch, tmp_path, victim_pid):
    """HOLE 2 regression: a ``$PATH``-shimmed failing ``ps`` cannot disable the
    anchor for an ANCHORED envelope.

    (2a) ownership resolves via absolute ``/bin/ps``, so a non-owner's
         heartbeat/unregister of the anchored victim is DENIED despite the shim.
    (2b) when the oracle is genuinely unreadable (lineage collapsed / no live
         create_time) an anchored envelope fails CLOSED (deny).
    A grandfathered (no-create_time) envelope still degrades gracefully (fail-open).
    """
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")

    # A fake `ps` that always fails (exit 1), shimmed to the FRONT of $PATH.
    shim = tmp_path / "psshim"
    shim.mkdir()
    fake_ps = shim / "ps"
    fake_ps.write_text("#!/bin/sh\nexit 1\n")
    fake_ps.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim}{os.pathsep}{os.environ.get('PATH', '')}")

    # Sanity: a bare PATH-resolved `ps` is now the failing shim…
    assert subprocess.call(["ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0
    # …yet the anchored oracle still reads a real create_time via absolute /bin/ps.
    real_ct = registry._pid_create_time(victim_pid)
    assert real_ct  # absolute-path ps bypassed the shim

    # ── (2a) ANCHORED victim: shim must NOT let a non-owner seize it. ──
    now = registry._utcnow_iso()
    anchored = {
        "session_id": "shim-victim", "agent": "claude_code", "role": "primary",
        "worktree_path": None, "pid": victim_pid,
        "registered_at": now, "last_heartbeat": now,
        "heartbeat_interval_s": 30, "provider": "claude_anthropic",
        "primitive_version": registry.PRIMITIVE_VERSION,
        "create_time": real_ct,
    }
    registry._atomic_write(registry._envelope_path("shim-victim"), anchored)
    with pytest.raises(PermissionError):
        registry.heartbeat("shim-victim")
    with pytest.raises(PermissionError):
        registry.unregister("shim-victim")

    # ── (2b) oracle genuinely unreadable → anchored must fail CLOSED. ──
    monkeypatch.setattr(registry, "_caller_lineage", lambda: {os.getpid()})
    monkeypatch.setattr(registry, "_pid_create_time", lambda pid: None)
    assert registry._caller_owns_envelope(anchored) is False  # deny, NOT fail-open

    # ── grandfathered (no create_time) still degrades gracefully. ──
    grand = {
        "session_id": "shim-grandfathered", "agent": "claude_code", "role": "primary",
        "worktree_path": None, "pid": victim_pid,
        "registered_at": now, "last_heartbeat": now,
        "heartbeat_interval_s": 30, "provider": "claude_anthropic",
        "primitive_version": registry.PRIMITIVE_VERSION,
        # NO create_time → pre-anchor / grandfathered → fail-open preserved
    }
    registry._atomic_write(registry._envelope_path("shim-grandfathered"), grand)
    assert registry._caller_owns_envelope(grand) is True
    hb = registry.heartbeat("shim-grandfathered")
    assert hb["session_id"] == "shim-grandfathered"
    assert registry.unregister("shim-grandfathered") is True
