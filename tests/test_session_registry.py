"""Tests for T3.11 session-registry primitive."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.sessions import registry


@pytest.fixture
def registry_root(tmp_path, monkeypatch):
    root = tmp_path / "agent_registry"
    monkeypatch.setenv("NUCLEUS_AGENT_REGISTRY", str(root))
    # Mock _caller_lineage so register_session accepts any pid in tests.
    # The real validation checks the kernel process tree, which doesn't
    # include the fake PIDs (4242, 9999, etc.) used in tests.
    monkeypatch.setattr(
        registry, "_caller_lineage",
        lambda: {0, 1234, 4242, 5678, 9999, os.getpid(), os.getppid()},
    )
    return root


def test_agent_registry_root_honors_env(registry_root):
    assert registry.agent_registry_root() == registry_root


def test_agent_registry_root_falls_back_to_brain(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_AGENT_REGISTRY", raising=False)
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.setenv("NUCLEUS_BRAIN", str(tmp_path / ".brain"))
    assert registry.agent_registry_root() == tmp_path / ".brain" / "agent_registry"


def test_register_session_writes_envelope(registry_root):
    env = registry.register_session(
        session_id="sess-1",
        agent="claude_code",
        role="primary",
        provider="claude_anthropic",
        worktree_path="/tmp/worktree-a",
        pid=4242,
        heartbeat_interval_s=15,
    )
    target = registry_root / "sess-1.json"
    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload == env
    assert payload["session_id"] == "sess-1"
    assert payload["agent"] == "claude_code"
    assert payload["role"] == "primary"
    assert payload["provider"] == "claude_anthropic"
    assert payload["pid"] == 4242
    assert payload["heartbeat_interval_s"] == 15
    assert payload["primitive_version"] == registry.PRIMITIVE_VERSION
    assert payload["registered_at"] == payload["last_heartbeat"]


def test_register_session_rejects_empty_id(registry_root):
    with pytest.raises(ValueError):
        registry.register_session(
            session_id="", agent="x", role="primary", provider="p",
        )


def test_register_session_defaults_pid_to_os_getpid(registry_root):
    env = registry.register_session(
        session_id="sess-pid",
        agent="cowork",
        role="coordinator",
        provider="claude_anthropic",
    )
    # When pid=None, register_session uses os.getppid() (the parent process
    # is the registering agent in stdio MCP mode).
    assert env["pid"] == os.getppid()


def test_register_session_resolves_symlinked_worktree(tmp_path, registry_root):
    real = tmp_path / "real_tree"
    real.mkdir()
    link = tmp_path / "link_tree"
    link.symlink_to(real)
    env = registry.register_session(
        session_id="sess-sym",
        agent="claude_code",
        role="primary",
        provider="claude_anthropic",
        worktree_path=str(link),
    )
    assert env["worktree_path"] == str(real.resolve())


def test_heartbeat_touches_last_heartbeat(registry_root, monkeypatch):
    env = registry.register_session(
        session_id="sess-2", agent="claude_code", role="primary",
        provider="claude_anthropic",
    )
    original = env["last_heartbeat"]

    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    monkeypatch.setattr(
        registry, "_utcnow_iso",
        lambda: future.isoformat().replace("+00:00", "Z"),
    )
    updated = registry.heartbeat("sess-2")
    assert updated["last_heartbeat"] != original
    assert updated["registered_at"] == env["registered_at"]


def test_heartbeat_missing_raises(registry_root):
    with pytest.raises(FileNotFoundError):
        registry.heartbeat("nope")


def test_unregister_removes_envelope(registry_root):
    registry.register_session(
        session_id="sess-3", agent="cowork", role="coordinator",
        provider="claude_anthropic",
    )
    assert registry.unregister("sess-3") is True
    assert registry.unregister("sess-3") is False


def test_list_agents_filters_by_worktree_role_and_liveness(tmp_path, registry_root, monkeypatch):
    wt_a = tmp_path / "wt-a"
    wt_a.mkdir()
    wt_b = tmp_path / "wt-b"
    wt_b.mkdir()

    # Stale envelope (last_heartbeat far in the past).
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    monkeypatch.setattr(
        registry, "_utcnow_iso",
        lambda: old.isoformat().replace("+00:00", "Z"),
    )
    registry.register_session(
        session_id="stale", agent="claude_code", role="primary",
        provider="claude_anthropic", worktree_path=str(wt_a),
        heartbeat_interval_s=30,
    )
    # Fresh envelopes.
    monkeypatch.setattr(
        registry, "_utcnow_iso",
        lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    registry.register_session(
        session_id="alive-a", agent="claude_code", role="primary",
        provider="claude_anthropic", worktree_path=str(wt_a),
    )
    registry.register_session(
        session_id="alive-b", agent="cowork", role="coordinator",
        provider="claude_anthropic", worktree_path=str(wt_a),
    )
    registry.register_session(
        session_id="alive-c", agent="gemini_cli", role="primary",
        provider="google", worktree_path=str(wt_b),
    )

    ids = {a["session_id"] for a in registry.list_agents(alive_only=True)}
    assert ids == {"alive-a", "alive-b", "alive-c"}

    all_ids = {a["session_id"] for a in registry.list_agents(alive_only=False)}
    assert "stale" in all_ids

    wt_a_ids = {a["session_id"] for a in registry.list_agents(worktree_path=str(wt_a))}
    assert wt_a_ids == {"alive-a", "alive-b"}

    primary = {a["session_id"] for a in registry.list_agents(role="primary")}
    assert primary == {"alive-a", "alive-c"}


def test_detect_splits_flags_duplicate_role_on_same_worktree(tmp_path, registry_root):
    shared = tmp_path / "shared"
    shared.mkdir()
    registry.register_session(
        session_id="main-1", agent="claude_code", role="primary",
        provider="claude_anthropic", worktree_path=str(shared),
    )
    registry.register_session(
        session_id="main-2", agent="gemini_cli", role="primary",
        provider="google", worktree_path=str(shared),
    )
    registry.register_session(
        session_id="peer-1", agent="cowork", role="secondary",
        provider="claude_anthropic", worktree_path=str(shared),
    )

    splits = registry.detect_splits()
    assert len(splits) == 1
    split = splits[0]
    assert split["worktree_path"] == str(shared.resolve())
    assert split["role"] == "primary"
    assert split["count"] == 2
    assert set(split["sessions"]) == {"main-1", "main-2"}
    assert split["agents"] == ["claude_code", "gemini_cli"]


def test_detect_splits_scoped_to_worktree(tmp_path, registry_root):
    wt_a = tmp_path / "wt-a"
    wt_a.mkdir()
    wt_b = tmp_path / "wt-b"
    wt_b.mkdir()
    registry.register_session(
        session_id="a1", agent="claude_code", role="primary",
        provider="claude_anthropic", worktree_path=str(wt_a),
    )
    registry.register_session(
        session_id="a2", agent="gemini_cli", role="primary",
        provider="google", worktree_path=str(wt_a),
    )
    registry.register_session(
        session_id="b1", agent="claude_code", role="primary",
        provider="claude_anthropic", worktree_path=str(wt_b),
    )
    scoped = registry.detect_splits(worktree_path=str(wt_b))
    assert scoped == []


def test_atomic_write_leaves_no_tmp_on_success(registry_root):
    registry.register_session(
        session_id="sess-atomic", agent="claude_code", role="primary",
        provider="claude_anthropic",
    )
    leftovers = list(registry_root.glob(".reg-*"))
    assert leftovers == []


def test_envelope_path_sanitizes_session_id(registry_root):
    env = registry.register_session(
        session_id="weird/../slashes",
        agent="claude_code", role="primary", provider="claude_anthropic",
    )
    assert env["session_id"] == "weird/../slashes"
    files = {p.name for p in registry_root.iterdir() if p.suffix == ".json"}
    assert files
    for name in files:
        assert "/" not in name
        assert ".." not in name


def test_iter_envelopes_skips_junk(registry_root):
    registry.register_session(
        session_id="good", agent="claude_code", role="primary",
        provider="claude_anthropic",
    )
    # Corrupt file + stray non-json.
    (registry_root / "broken.json").write_text("{", encoding="utf-8")
    (registry_root / "README.md").write_text("notes", encoding="utf-8")

    ids = {a["session_id"] for a in registry.list_agents(alive_only=False)}
    assert ids == {"good"}


# ── find_session_in_ancestry tests ─────────────────────────────────────────


def test_walk_ppid_ancestry_returns_list(monkeypatch):
    """The walk function returns a non-empty list on POSIX where ps works."""
    # Use the current process; ancestry should include the test runner's parent.
    ancestors = registry._walk_ppid_ancestry(os.getpid(), max_depth=4)
    # Best-effort: on a system where ps works, we should at least get one
    # ancestor. On Windows or restricted CI, an empty list is acceptable.
    assert isinstance(ancestors, list)
    for pid in ancestors:
        assert isinstance(pid, int)
        assert pid > 1


def test_walk_ppid_ancestry_bounded_by_max_depth(monkeypatch):
    """max_depth caps the walk."""
    captured = []

    def fake_check_output(cmd, **kw):
        # cmd is ["ps", "-p", str(curr), "-o", "ppid="]
        curr = int(cmd[2])
        captured.append(curr)
        # Always return curr+1 as the parent — infinite chain.
        return f"{curr + 1}\n".encode()

    monkeypatch.setattr(
        "mcp_server_nucleus.sessions.registry.subprocess",
        type("M", (), {"check_output": staticmethod(fake_check_output),
                       "DEVNULL": -3})(),
        raising=False,
    )
    # Subprocess is imported inside the function; patch module-level subprocess
    # directly.
    import subprocess as _subprocess
    monkeypatch.setattr(_subprocess, "check_output", fake_check_output)

    ancestors = registry._walk_ppid_ancestry(1000, max_depth=5)
    assert len(ancestors) == 5


def test_walk_ppid_ancestry_handles_ps_failure(monkeypatch):
    """ps failure returns empty list, no exception."""
    def fail_check_output(*a, **kw):
        raise FileNotFoundError("ps not available")

    import subprocess as _subprocess
    monkeypatch.setattr(_subprocess, "check_output", fail_check_output)

    assert registry._walk_ppid_ancestry(1000, max_depth=8) == []


def test_walk_ppid_ancestry_stops_at_pid_1(monkeypatch):
    """Walk stops when it reaches init (pid 1)."""
    chain = {2000: 1500, 1500: 100, 100: 1}

    def fake_check_output(cmd, **kw):
        curr = int(cmd[2])
        ppid = chain.get(curr)
        if ppid is None:
            raise FileNotFoundError("end of chain")
        return f"{ppid}\n".encode()

    import subprocess as _subprocess
    monkeypatch.setattr(_subprocess, "check_output", fake_check_output)

    ancestors = registry._walk_ppid_ancestry(2000, max_depth=10)
    # 1500 and 100 should be in ancestors; 1 should not.
    assert ancestors == [1500, 100]


def test_walk_ppid_ancestry_breaks_self_parent_loop(monkeypatch):
    """A pid that lists itself as parent terminates the walk."""
    chain = {500: 500}  # self-loop

    def fake_check_output(cmd, **kw):
        curr = int(cmd[2])
        ppid = chain.get(curr)
        if ppid is None:
            raise FileNotFoundError("end of chain")
        return f"{ppid}\n".encode()

    import subprocess as _subprocess
    monkeypatch.setattr(_subprocess, "check_output", fake_check_output)

    # 500's parent is 500 itself; walk should NOT add 500 as its own ancestor.
    ancestors = registry._walk_ppid_ancestry(500, max_depth=10)
    assert ancestors == []


def test_find_session_in_ancestry_returns_none_when_no_sessions(registry_root, monkeypatch):
    """No registered sessions → None."""
    # Force ancestry to return some pids, but no sessions registered.
    monkeypatch.setattr(
        registry, "_walk_ppid_ancestry",
        lambda *a, **kw: [1234, 5678],
    )
    assert registry.find_session_in_ancestry() is None


def test_find_session_in_ancestry_returns_none_when_no_match(registry_root, monkeypatch):
    """Sessions registered but no ancestor matches → None."""
    registry.register_session(
        session_id="other", agent="claude_code", role="primary",
        provider="claude_anthropic", pid=9999,
    )
    monkeypatch.setattr(
        registry, "_walk_ppid_ancestry",
        lambda *a, **kw: [1234, 5678],
    )
    assert registry.find_session_in_ancestry() is None


def test_find_session_in_ancestry_returns_match(registry_root, monkeypatch):
    """An ancestor PID matches a registered session → return that envelope."""
    registry.register_session(
        session_id="ancestor-sess", agent="windsurf", role="primary",
        provider="anthropic_claude_code", pid=5678,
    )
    monkeypatch.setattr(
        registry, "_walk_ppid_ancestry",
        lambda *a, **kw: [1234, 5678, 9999],
    )
    match = registry.find_session_in_ancestry()
    assert match is not None
    assert match["session_id"] == "ancestor-sess"
    assert match["agent"] == "windsurf"


def test_find_session_in_ancestry_closest_ancestor_wins(registry_root, monkeypatch):
    """Multiple ancestors registered → closest one wins."""
    registry.register_session(
        session_id="far", agent="agent-far", role="primary",
        provider="p", pid=9999,
    )
    registry.register_session(
        session_id="close", agent="agent-close", role="primary",
        provider="p", pid=5678,
    )
    # Walk order: close first (5678), far second (9999).
    monkeypatch.setattr(
        registry, "_walk_ppid_ancestry",
        lambda *a, **kw: [5678, 9999],
    )
    match = registry.find_session_in_ancestry()
    assert match["session_id"] == "close"


def test_find_session_in_ancestry_alive_only_filter(registry_root, monkeypatch):
    """Stale sessions filtered out by default."""
    # Register a session and backdate its heartbeat past the liveness window.
    payload = registry.register_session(
        session_id="stale", agent="agent-x", role="primary",
        provider="p", pid=5678, heartbeat_interval_s=1,
    )
    # Manually rewrite the envelope with an old heartbeat.
    stale_iso = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat().replace(
        "+00:00", "Z"
    )
    payload["last_heartbeat"] = stale_iso
    registry._atomic_write(registry._envelope_path("stale"), payload)

    monkeypatch.setattr(
        registry, "_walk_ppid_ancestry",
        lambda *a, **kw: [5678],
    )
    # Default alive_only=True → stale session excluded.
    assert registry.find_session_in_ancestry() is None
    # alive_only=False → stale session included.
    match = registry.find_session_in_ancestry(alive_only=False)
    assert match is not None
    assert match["session_id"] == "stale"


def test_find_session_in_ancestry_empty_walk_returns_none(registry_root, monkeypatch):
    """If ancestry walk is empty (e.g. Windows), return None even with sessions."""
    registry.register_session(
        session_id="any", agent="x", role="primary",
        provider="p", pid=1234,
    )
    monkeypatch.setattr(registry, "_walk_ppid_ancestry", lambda *a, **kw: [])
    assert registry.find_session_in_ancestry() is None


# ── stone-1.5 (role-credential) — AUDIT_FINDINGS.md row #8 ────────────────
#
# Bar-2 (same-uid ceiling) possession check per ADJACENCY_THEOREM.md regime-2:
# raises forgery cost from "type a role string" to "possess that role's
# minted ~/.tb/relay_token_<role>". NOT fraud-proof — a same-uid adversary
# who can read another role's token file still forges for free.
#
# Every fixture below uses a SYNTHETIC token value in an isolated temp dir
# (NUCLEUS_ROLE_CREDENTIAL_DIR) — never the real ~/.tb.


_SYNTHETIC_MAIN_TOKEN = "synthetic-test-token-main-0f1e2d3c4b5a"
_SYNTHETIC_PEER_TOKEN = "synthetic-test-token-peer-9z8y7x6w5v4u"


@pytest.fixture
def credential_dir(tmp_path, monkeypatch):
    """Isolated per-role token directory — mints synthetic tokens for two roles."""
    d = tmp_path / "tb_tokens"
    d.mkdir()
    (d / "relay_token_claude_code_main").write_text(_SYNTHETIC_MAIN_TOKEN, encoding="utf-8")
    (d / "relay_token_claude_code_peer").write_text(_SYNTHETIC_PEER_TOKEN, encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL_DIR", str(d))
    return d


def test_role_credential_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("NUCLEUS_ROLE_CREDENTIAL", raising=False)
    assert registry._role_credential_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "True", "yes", "on", "ON"])
def test_role_credential_flag_truthy_values(monkeypatch, val):
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL", val)
    assert registry._role_credential_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", ""])
def test_role_credential_flag_falsy_values(monkeypatch, val):
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL", val)
    assert registry._role_credential_enabled() is False


def test_verify_role_credential_matches_minted_token(credential_dir):
    assert registry._verify_role_credential("claude_code_main", _SYNTHETIC_MAIN_TOKEN) is True


def test_verify_role_credential_rejects_wrong_token(credential_dir):
    """Presenting the PEER token for the MAIN role fails — cross-role reuse blocked."""
    assert registry._verify_role_credential("claude_code_main", _SYNTHETIC_PEER_TOKEN) is False


def test_verify_role_credential_rejects_missing_presented(credential_dir):
    assert registry._verify_role_credential("claude_code_main", None) is False
    assert registry._verify_role_credential("claude_code_main", "") is False


def test_verify_role_credential_rejects_no_token_minted_for_role(credential_dir):
    """A role with no minted token file can never be satisfied — safe default deny."""
    assert registry._verify_role_credential("claude_code_nonexistent", "anything") is False


def test_verify_role_credential_rejects_empty_token_file(credential_dir):
    (credential_dir / "relay_token_empty_role").write_text("", encoding="utf-8")
    assert registry._verify_role_credential("empty_role", "anything") is False


def test_register_session_flag_off_ignores_role_credential_legacy(registry_root, monkeypatch):
    """FLAG OFF: role is trusted as a free string regardless of role_credential
    (or its absence) — byte-identical to pre-stone-1.5 behavior."""
    monkeypatch.delenv("NUCLEUS_ROLE_CREDENTIAL", raising=False)
    env = registry.register_session(
        session_id="legacy-1", agent="claude_code", role="claude_code_main",
        provider="claude_anthropic",
    )
    assert env["role"] == "claude_code_main"
    assert "role_credential" not in env


def test_forge_role_without_token_accepted_when_flag_off_legacy(registry_root, credential_dir, monkeypatch):
    """FORGE TEST (flag OFF baseline): a lane calling register_session with an
    unauthenticated role string it does not possess a token for is ACCEPTED
    — this is the legacy hole the flag closes."""
    monkeypatch.delenv("NUCLEUS_ROLE_CREDENTIAL", raising=False)
    env = registry.register_session(
        session_id="forge-legacy", agent="claude_code", role="claude_code_main",
        provider="claude_anthropic", pid=os.getppid(),
        # no role_credential presented at all
    )
    assert env["role"] == "claude_code_main"


def test_forge_role_without_token_rejected_when_flag_on(registry_root, credential_dir, monkeypatch):
    """FORGE TEST (the fix): with NUCLEUS_ROLE_CREDENTIAL=1, the same call —
    register_session(role='claude_code_main') without possessing the main
    role token — is REJECTED."""
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL", "1")
    with pytest.raises(registry.RoleCredentialError):
        registry.register_session(
            session_id="forge-1", agent="claude_code", role="claude_code_main",
            provider="claude_anthropic", pid=os.getppid(),
            # no role_credential presented
        )
    # And no envelope was written for the rejected attempt.
    assert not (registry_root / "forge-1.json").exists()


def test_forge_role_with_wrong_role_credential_rejected_when_flag_on(registry_root, credential_dir, monkeypatch):
    """Presenting a DIFFERENT role's valid token (cross-role credential reuse)
    is still a forgery and must be rejected."""
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL", "1")
    with pytest.raises(registry.RoleCredentialError):
        registry.register_session(
            session_id="forge-2", agent="claude_code", role="claude_code_main",
            provider="claude_anthropic",
            role_credential=_SYNTHETIC_PEER_TOKEN,
        )


def test_register_session_flag_on_accepts_valid_role_credential(registry_root, credential_dir, monkeypatch):
    """A valid token for the CLAIMED role passes — the honest path stays open."""
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL", "1")
    env = registry.register_session(
        session_id="honest-1", agent="claude_code", role="claude_code_main",
        provider="claude_anthropic",
        role_credential=_SYNTHETIC_MAIN_TOKEN,
    )
    assert env["role"] == "claude_code_main"
    assert env["session_id"] == "honest-1"


def test_register_session_envelope_never_persists_role_credential(registry_root, credential_dir, monkeypatch):
    """The stored envelope must never carry the raw credential value on disk,
    flag on or off — the token is a presented secret, not session state."""
    monkeypatch.setenv("NUCLEUS_ROLE_CREDENTIAL", "1")
    registry.register_session(
        session_id="no-leak-1", agent="claude_code", role="claude_code_peer",
        provider="claude_anthropic",
        role_credential=_SYNTHETIC_PEER_TOKEN,
    )
    on_disk = json.loads((registry_root / "no-leak-1.json").read_text(encoding="utf-8"))
    assert "role_credential" not in on_disk
    serialized = json.dumps(on_disk)
    assert _SYNTHETIC_PEER_TOKEN not in serialized
