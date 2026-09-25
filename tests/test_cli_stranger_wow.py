"""STRANGER-WOW (ADR-0043 W2): CLI-level tests for the value-demonstrating
`nucleus init` close-out and the `nucleus relay send|inbox` verbs.

Covers:
  1. argparse reachability of `relay send` / `relay inbox`.
  2. `nucleus init` happy-path in an isolated HOME/cwd — writes project
     .mcp.json ({"command": "nucleus-mcp"}) and recalls its seed engram on screen.
  3. `relay send` -> `relay inbox` roundtrip over the FS mailbox in a tmp brain,
     with zero tokens / env, plus --unread/--ack semantics.
"""
import argparse
import json
from pathlib import Path

import pytest

from mcp_server_nucleus import cli


# ── 1. argparse reachability ──────────────────────────────────────────────

@pytest.mark.parametrize("argv", [
    ["nucleus", "relay", "send", "--help"],
    ["nucleus", "relay", "inbox", "--help"],
])
def test_relay_subcommands_reachable(monkeypatch, argv):
    """`relay send` / `relay inbox` parse and reach their help (SystemExit 0)."""
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0


# ── 2. init happy-path: honest .mcp.json + on-screen recall ───────────────

def test_init_writes_mcp_json_and_recalls(monkeypatch, tmp_path, capsys):
    home = tmp_path / "home"
    proj = tmp_path / "proj"
    home.mkdir()
    proj.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.chdir(proj)
    monkeypatch.setattr("sys.argv", ["nucleus", "init", "--no-wizard"])

    cli.main()
    out = capsys.readouterr().out

    # (a) project-local .mcp.json written with a LAUNCHABLE server command.
    # The regression guarded here is a BARE command string like "nucleus-mcp":
    # an MCP client that starts without the install venv on PATH cannot resolve
    # it (verified: exit 2, command not found), so the server never boots. The
    # command must therefore be absolute, and carry the brain path in env.
    mcp = proj / ".mcp.json"
    assert mcp.exists(), "init must write a project-local .mcp.json"
    cfg = json.loads(mcp.read_text())
    entry = cfg["mcpServers"]["nucleus"]
    assert Path(entry["command"]).is_absolute(), (
        f"init must write an absolute command, got {entry['command']!r}"
    )
    assert Path(entry["command"]).name == "nucleus-mcp"
    assert entry["env"]["NUCLEUS_BRAIN_PATH"] == str((proj / ".brain").absolute())
    assert f'wrote {mcp.name}' in out or "wrote .mcp.json" in out

    # (b) memory self-test recalled the seed engram on screen (proof, not claim)
    assert "memory self-test" in out
    assert "recall" in out and "hit" in out
    assert "Nucleus initialized" in out

    # (c) two-agent relay demo is printed as copy-paste lines
    assert "relay send peer" in out
    assert "relay inbox" in out

    # No client-config files were patched into HOME (only telemetry/install flags)
    home_writes = {p.name for p in home.rglob("*") if p.is_file()}
    assert "claude_desktop_config.json" not in home_writes
    assert ".mcp.json" not in home_writes


# ── 3. relay send -> inbox roundtrip over the FS mailbox ──────────────────

def _ns(**kw):
    return argparse.Namespace(**kw)


def test_relay_send_inbox_roundtrip(monkeypatch, tmp_path, capsys):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)  # guarantee FS path
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)

    # agent A: send to peer (sender defaults to "main")
    rc = cli.handle_relay_command(_ns(
        relay_action="send", to="peer",
        subject="handoff", body="deploy key in vault slot 4", sender=None,
    ))
    assert rc == 0
    send_out = capsys.readouterr().out
    assert "sent to peer" in send_out

    # message landed in the FS mailbox with an unchanged envelope + real clock ts
    files = list((brain / "relay" / "peer").glob("*.json"))
    assert len(files) == 1
    env = json.loads(files[0].read_text())
    assert env["to"] == "peer"
    assert env["body"] == "deploy key in vault slot 4"
    assert env["subject"] == "handoff"
    assert env.get("created_at"), "envelope must carry a created_at timestamp"

    # agent B: bare inbox (role defaults to "peer") surfaces the message
    rc = cli.handle_relay_command(_ns(
        relay_action="inbox", role=None, unread=False, ack=False, limit=20,
    ))
    assert rc == 0
    inbox_out = capsys.readouterr().out
    assert "deploy key in vault slot 4" in inbox_out
    assert "handoff" in inbox_out

    # --unread + --ack marks it read; a following --unread read is empty
    rc = cli.handle_relay_command(_ns(
        relay_action="inbox", role="peer", unread=True, ack=True, limit=20,
    ))
    assert rc == 0
    assert "acked 1" in capsys.readouterr().out

    rc = cli.handle_relay_command(_ns(
        relay_action="inbox", role="peer", unread=True, ack=False, limit=20,
    ))
    assert rc == 0
    assert "no unread messages" in capsys.readouterr().out


def test_relay_send_requires_body(monkeypatch):
    """`relay send` without --body is an argparse error (exit 2)."""
    monkeypatch.setattr("sys.argv", ["nucleus", "relay", "send", "peer"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


# ── setup exit codes: opposed pair (--create vs no --create) ──────────────

def test_setup_exit_codes_opposed_pair(tmp_path, monkeypatch):
    """``nucleus setup`` without ``--create`` exits 1 and writes no file when
    zero IDE configs are discoverable; with ``--create`` it writes
    ``~/.claude.json`` (in the isolated home) carrying an absolute command
    path and exits cleanly."""
    # Isolation preamble: empty home → zero IDE configs discoverable.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()

    # (a) Without --create: exits 1, writes no .claude.json.
    monkeypatch.setattr("sys.argv", ["nucleus", "setup"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    assert not (tmp_path / "home" / ".claude.json").exists()

    # (b) With --create: writes .claude.json with absolute command, exits clean.
    monkeypatch.setattr("sys.argv", ["nucleus", "setup", "--create"])
    try:
        cli.main()
    except SystemExit as exc2:
        assert exc2.code in (0, None), (
            f"setup --create exited with unexpected code {exc2.code}"
        )
    claude_json = tmp_path / "home" / ".claude.json"
    assert claude_json.exists(), "--create must write ~/.claude.json"
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    assert Path(data["mcpServers"]["nucleus"]["command"]).is_absolute()


# ── 4. dry-run immunity: never writes, never fails the gate ───────────────

def test_dry_run_immunity(tmp_path, monkeypatch):
    """``nucleus setup --dry-run`` must never write a file and never fail the
    gate. Dry-run falls through ``main()`` without ``sys.exit``, so a clean
    return (no SystemExit) is also acceptable — the only unacceptable
    outcomes are a non-zero/non-clean exit or any file written under the
    isolated home."""
    # Isolation preamble: empty home → zero IDE configs discoverable.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()

    monkeypatch.setattr("sys.argv", ["nucleus", "setup", "--dry-run"])
    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code in (0, None), (
            f"setup --dry-run exited with unexpected code {exc.code}"
        )
    # No SystemExit is also success — dry-run falls through main() cleanly.

    # Dry-run must never write anything under the isolated home.
    assert list((tmp_path / "home").iterdir()) == []
