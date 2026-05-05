"""T3.11 wedge-identity hardening — VS Code fork disambiguation + targeted relay routing.

The bug (per Antigravity directive 2026-04-26):
  VSCODE_PID is shared across every VS Code fork (Antigravity, Windsurf, Cursor,
  vanilla VS Code). The detection fallback used to blanket-claim "antigravity"
  for any process with VSCODE_PID set — so Windsurf processes were misidentified
  as Antigravity and routed into the wrong relay bucket.

The hardening:
  1. Add ANTIGRAVITY_SESSION env-var check (symmetric with WINDSURF_SESSION /
     CURSOR_SESSION) to distinguish forks that opt-in.
  2. Add _disambiguate_vscode_fork() — walks process ancestors and checks each
     ancestor's executable path for a known app-bundle marker. Used as a fallback
     when VSCODE_PID is set but no fork-specific env var is.
  3. If ancestry disambiguation also fails, return generic "vscode" instead of
     blanket-claiming "antigravity". The registry's ancestry lookup (T3.11 primary)
     remains the authoritative path; this hardens only the heuristic fallback.

Targeted-relay verification (step 3 of directive):
  Confirm that messages with to_session_id surface only to the matching session,
  while broadcasts (no to_session_id) surface to every session — i.e., targeted
  relays bypass the global watcher's session-agnostic consolidation.
"""
from __future__ import annotations

import json
import pathlib
import sys
from unittest.mock import patch

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server_nucleus.runtime import relay_ops  # noqa: E402


# ── Block all primary-priority paths so the heuristic fallback is the one under test ──

@pytest.fixture(autouse=True)
def _bypass_primary_paths(monkeypatch):
    # NUCLEUS_SESSION_TYPE override would short-circuit the raw detector; clear it.
    # T3.11 Priority-2 registry-aware ancestry detection (PR #170) is also a
    # primary path; mock it to return None unless a test opts in.
    monkeypatch.delenv("NUCLEUS_SESSION_TYPE", raising=False)
    monkeypatch.delenv("WINDSURF_SESSION", raising=False)
    monkeypatch.delenv("CURSOR_SESSION", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_SESSION", raising=False)
    monkeypatch.delenv("CLAUDE_DESKTOP", raising=False)
    monkeypatch.delenv("CLAUDE_CODE", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION", raising=False)
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)
    # Default: registry-aware ancestry returns nothing so heuristic paths run.
    from mcp_server_nucleus.sessions import registry as _reg
    monkeypatch.setattr(_reg, "find_session_in_ancestry", lambda *a, **kw: None)


# ── Env-var detection: ANTIGRAVITY_SESSION wins over VSCODE_PID ──

def test_antigravity_session_env_wins(monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_SESSION", "1")
    monkeypatch.setenv("VSCODE_PID", "12345")
    assert relay_ops.detect_session_type() == "antigravity"


def test_windsurf_session_env_wins_over_vscode_pid(monkeypatch):
    monkeypatch.setenv("WINDSURF_SESSION", "abc")
    monkeypatch.setenv("VSCODE_PID", "12345")
    assert relay_ops.detect_session_type() == "windsurf"


def test_cursor_session_env_wins_over_vscode_pid(monkeypatch):
    monkeypatch.setenv("CURSOR_SESSION", "abc")
    monkeypatch.setenv("VSCODE_PID", "12345")
    assert relay_ops.detect_session_type() == "cursor"


# ── VSCODE_PID alone no longer blanket-claims antigravity ──

def test_vscode_pid_without_fork_env_does_not_claim_antigravity(monkeypatch):
    """The bug: pre-fix, VSCODE_PID alone returned 'antigravity'. Post-fix,
    falls through to ancestor disambiguation; if no ancestor matches, returns
    generic 'vscode'."""
    monkeypatch.setenv("VSCODE_PID", "12345")
    # Force ancestry disambiguation to find nothing → should return "vscode".
    with patch.object(relay_ops, "_disambiguate_vscode_fork", return_value=None):
        assert relay_ops.detect_session_type() == "vscode"


def test_vscode_pid_with_antigravity_ancestor_returns_antigravity(monkeypatch):
    monkeypatch.setenv("VSCODE_PID", "12345")
    with patch.object(relay_ops, "_disambiguate_vscode_fork", return_value="antigravity"):
        assert relay_ops.detect_session_type() == "antigravity"


def test_vscode_pid_with_windsurf_ancestor_returns_windsurf(monkeypatch):
    monkeypatch.setenv("VSCODE_PID", "12345")
    with patch.object(relay_ops, "_disambiguate_vscode_fork", return_value="windsurf"):
        assert relay_ops.detect_session_type() == "windsurf"


def test_vscode_pid_with_cursor_ancestor_returns_cursor(monkeypatch):
    monkeypatch.setenv("VSCODE_PID", "12345")
    with patch.object(relay_ops, "_disambiguate_vscode_fork", return_value="cursor"):
        assert relay_ops.detect_session_type() == "cursor"


# ── _disambiguate_vscode_fork ancestor-walk semantics ──

def test_disambiguate_matches_app_bundle_in_ancestor(monkeypatch):
    """Mock ps-output of one ancestor as Antigravity.app — should match."""
    calls = {"n": 0}

    def fake_check_output(args, **kwargs):
        # Args alternate: comm= for current, ppid= for parent
        calls["n"] += 1
        if "-o" in args and "comm=" in args:
            return b"/Applications/Antigravity.app/Contents/MacOS/Antigravity\n"
        if "-o" in args and "ppid=" in args:
            return b"1\n"  # walk terminates next iteration
        return b""

    with patch("subprocess.check_output", side_effect=fake_check_output):
        assert relay_ops._disambiguate_vscode_fork() == "antigravity"


def test_disambiguate_returns_none_for_unknown_ancestor():
    def fake_check_output(args, **kwargs):
        if "-o" in args and "comm=" in args:
            return b"/usr/local/bin/something_random\n"
        if "-o" in args and "ppid=" in args:
            return b"1\n"
        return b""

    with patch("subprocess.check_output", side_effect=fake_check_output):
        assert relay_ops._disambiguate_vscode_fork() is None


def test_disambiguate_handles_ps_failure_gracefully():
    def boom(args, **kwargs):
        raise OSError("ps not available")

    with patch("subprocess.check_output", side_effect=boom):
        assert relay_ops._disambiguate_vscode_fork() is None


# ── Targeted relay routing (step 3 of directive) ──

def _write_relay(inbox: pathlib.Path, *, mid: str, to_session_id: str | None):
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{mid}.json").write_text(json.dumps({
        "id": mid,
        "from": "antigravity",
        "to": "claude_code_peer",
        "to_session_id": to_session_id,
        "subject": f"test {mid}",
        "body": "x",
        "priority": "normal",
        "read": False,
    }))


def test_targeted_relay_only_surfaces_to_matching_session(tmp_path):
    """Step 3 verification: a relay with to_session_id=X surfaces only to the
    session that identifies as X; other sessions skip it. Broadcast (None)
    surfaces to every session."""
    from mcp_server_nucleus.mirror import hook as mirror_hook

    inbox = tmp_path / "claude_code_peer"
    _write_relay(inbox, mid="targeted_to_alpha", to_session_id="alpha")
    _write_relay(inbox, mid="broadcast",          to_session_id=None)
    _write_relay(inbox, mid="targeted_to_beta",   to_session_id="beta")

    # Session "alpha" should see its targeted message + the broadcast, NOT beta's
    alpha_lines = mirror_hook._collect_unread_relays(session_id="alpha", inbox=inbox)
    alpha_text = " ".join(alpha_lines)
    assert "targeted_to_alpha" in alpha_text
    assert "broadcast" in alpha_text
    assert "targeted_to_beta" not in alpha_text

    # Session "beta" should see beta's targeted + broadcast, not alpha's
    beta_lines = mirror_hook._collect_unread_relays(session_id="beta", inbox=inbox)
    beta_text = " ".join(beta_lines)
    assert "targeted_to_beta" in beta_text
    assert "broadcast" in beta_text
    assert "targeted_to_alpha" not in beta_text

    # A third session "gamma" sees only the broadcast
    gamma_lines = mirror_hook._collect_unread_relays(session_id="gamma", inbox=inbox)
    gamma_text = " ".join(gamma_lines)
    assert "broadcast" in gamma_text
    assert "targeted_to_alpha" not in gamma_text
    assert "targeted_to_beta" not in gamma_text


# ── Priority-2 registry-aware ancestry detection (PR #170 + this PR) ──


def test_priority2_registry_match_returns_agent(monkeypatch):
    """When find_session_in_ancestry() returns a known-session-type agent,
    detect_session_type returns it — wins over heuristic fallbacks below."""
    from mcp_server_nucleus.sessions import registry as _reg
    monkeypatch.setattr(
        _reg, "find_session_in_ancestry",
        lambda *a, **kw: {"agent": "windsurf", "session_id": "ancestor-sess",
                          "pid": 5678},
    )
    monkeypatch.setenv("VSCODE_PID", "12345")
    with patch.object(relay_ops, "_disambiguate_vscode_fork", return_value="cursor"):
        # If Priority-2 wins, we get "windsurf" not "cursor".
        assert relay_ops.detect_session_type() == "windsurf"


def test_priority2_unknown_agent_falls_through(monkeypatch):
    """If find_session_in_ancestry returns an envelope with an agent that's
    NOT in KNOWN_SESSION_TYPES, fall through to subsequent priorities."""
    from mcp_server_nucleus.sessions import registry as _reg
    monkeypatch.setattr(
        _reg, "find_session_in_ancestry",
        lambda *a, **kw: {"agent": "some_unregistered_provider",
                          "session_id": "x", "pid": 9999},
    )
    monkeypatch.setenv("WINDSURF_SESSION", "abc")
    # Priority-2 returns unknown-type → fall through → env-var catches WINDSURF_SESSION.
    assert relay_ops.detect_session_type() == "windsurf"


def test_priority2_registry_failure_swallowed(monkeypatch):
    """If find_session_in_ancestry raises, the exception is swallowed and
    detection falls through to the next priority."""
    from mcp_server_nucleus.sessions import registry as _reg

    def raise_boom(*a, **kw):
        raise RuntimeError("registry blew up")

    monkeypatch.setattr(_reg, "find_session_in_ancestry", raise_boom)
    monkeypatch.setenv("WINDSURF_SESSION", "abc")
    assert relay_ops.detect_session_type() == "windsurf"


def test_priority2_no_match_returns_none_falls_through(monkeypatch):
    """When find_session_in_ancestry returns None (no matching ancestor),
    detection falls through to subsequent priorities."""
    from mcp_server_nucleus.sessions import registry as _reg
    monkeypatch.setattr(_reg, "find_session_in_ancestry",
                         lambda *a, **kw: None)
    monkeypatch.setenv("CURSOR_SESSION", "abc")
    assert relay_ops.detect_session_type() == "cursor"
