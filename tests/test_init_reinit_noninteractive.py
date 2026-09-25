"""Non-interactive ``init_brain`` re/init paths.

Every test chdir's into ``tmp_path`` and redirects ``Path.home`` to a tmp
dir so the repo's own ``.mcp.json`` (and the operator's real home config)
can never be touched. ``builtins.input`` is patched to raise so any
regression onto an interactive prompt becomes a loud failure instead of a
silent hang; the single interactive test overrides it with a stub.
"""
from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.cli import init_brain


def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """chdir into tmp_path, redirect Path.home to tmp_path, and forbid input()."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda self: tmp_path)
    monkeypatch.setattr(
        builtins,
        "input",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("input() was called on a no-prompt path")
        ),
    )
    return tmp_path


def test_fresh_default_init_creates_brain_and_mcp_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fresh init with the default template builds the full .brain tree and a project .mcp.json, no prompts."""
    _isolate(monkeypatch, tmp_path)

    ok = init_brain(".brain", "default", force=False)

    assert ok is True
    brain = tmp_path / ".brain"
    # Core default-template structure
    assert (brain / "ledger" / "state.json").is_file()
    assert (brain / "ledger" / "triggers.json").is_file()
    assert (brain / "ledger" / "events.jsonl").is_file()
    assert (brain / "ledger" / "tasks.json").is_file()
    assert (brain / "README.md").is_file()
    assert (brain / "agents" / "synthesizer.md").is_file()
    assert (brain / "memory" / "context.md").is_file()
    assert (brain / "memory" / "engrams.json").is_file()
    assert (brain / "config" / "nucleus.yaml").is_file()
    # Project-local .mcp.json written by _finish_init_with_value
    mcp = tmp_path / ".mcp.json"
    assert mcp.is_file()
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "mcpServers" in data and "nucleus" in data["mcpServers"]
    out = capsys.readouterr().out
    assert "initialized" in out.lower() or "control plane" in out.lower()


def test_fresh_solo_template_creates_solo_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Solo template produces the solo-mode ledger + meta/thread_registry.md, no prompts."""
    _isolate(monkeypatch, tmp_path)

    ok = init_brain(".brain", "solo", force=False)

    assert ok is True
    brain = tmp_path / ".brain"
    assert (brain / "ledger" / "state.json").is_file()
    assert (brain / "meta" / "thread_registry.md").is_file()
    assert (brain / "memory" / "context.md").is_file()
    assert (brain / "memory" / "engrams.json").is_file()
    assert (brain / "config" / "nucleus.yaml").is_file()
    # solo template does NOT create agents/synthesizer.md (default-only)
    assert not (brain / "agents" / "synthesizer.md").exists()
    # state.json carries the solo-mode state
    state = json.loads((brain / "ledger" / "state.json").read_text(encoding="utf-8"))
    assert isinstance(state, dict)
    out = capsys.readouterr().out
    assert "solo" in out.lower()


def test_reinit_with_force_overwrites_after_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """force=True re-inits an existing brain non-interactively: a backup is created, the brain is rebuilt, no prompt."""
    _isolate(monkeypatch, tmp_path)

    # First init: build a real brain.
    assert init_brain(".brain", "default", force=False) is True
    brain = tmp_path / ".brain"
    # Mutate a file so we can prove the backup captured the pre-reinit state.
    marker = brain / "memory" / "context.md"
    marker.write_text("PRE-REINIT MARKER\n", encoding="utf-8")

    # Reinit with force — must not call input().
    ok = init_brain(".brain", "default", force=True)
    assert ok is True

    # A backup directory was created next to .brain.
    backups = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".brain.backup."))
    assert backups, "expected at least one .brain.backup.<ts> directory after force reinit"

    # The fresh brain has the default context.md, not our marker.
    fresh_marker = brain / "memory" / "context.md"
    assert fresh_marker.is_file()
    assert "PRE-REINIT MARKER" not in fresh_marker.read_text(encoding="utf-8")

    # The most recent backup still carries the marker.
    latest_backup = tmp_path / backups[-1]
    assert "PRE-REINIT MARKER" in (latest_backup / "memory" / "context.md").read_text(encoding="utf-8")

    out = capsys.readouterr().out
    assert "backup" in out.lower()


def test_reinit_without_force_aborts_noninteractively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without force and a non-tty stdin, reinit on an existing brain aborts cleanly — no prompt, no mutation."""
    _isolate(monkeypatch, tmp_path)
    # Force stdin to report non-tty so the non-interactive branch is taken.
    import sys
    class _NonTtyStdin:
        def isatty(self) -> bool:
            return False
    monkeypatch.setattr(sys, "stdin", _NonTtyStdin())

    # Seed an existing brain with a recognizable file.
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    (brain / "ledger" / "state.json").write_text('{"v": "PRE"}', encoding="utf-8")
    pre_state = (brain / "ledger" / "state.json").read_text(encoding="utf-8")

    ok = init_brain(".brain", "default", force=False)

    assert ok is False
    # Existing brain untouched.
    assert (brain / "ledger" / "state.json").read_text(encoding="utf-8") == pre_state
    # No backup created.
    assert not any(p.name.startswith(".brain.backup.") for p in tmp_path.iterdir())
    out = capsys.readouterr().out
    assert "nothing was changed" in out.lower() or "--force" in out.lower()


def test_init_reinit_noninteractive_brain_surives_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Opposed pair to test_reinit_without_force_aborts_noninteractively.

    Non-tty stdin + no --force on an existing brain must abort with EVERY file
    byte-identical: no backup directory anywhere, sentinel content unchanged,
    total file count unchanged. Locks in that the abort path touches nothing.
    """
    _isolate(monkeypatch, tmp_path)
    # Force stdin to report non-tty so the non-interactive branch is taken.
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    # Seed an existing brain with a sentinel file whose content we will re-read.
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "sentinel.txt").write_text("SENTINEL-ORIGINAL", encoding="utf-8")

    pre_count = sum(1 for p in tmp_path.rglob("*") if p.is_file())

    ok = init_brain(".brain")

    assert ok is False
    # No backup directory created anywhere under tmp_path.
    assert list(tmp_path.glob("**/*.backup.*")) == []
    # Sentinel untouched.
    assert (brain / "sentinel.txt").is_file()
    assert (brain / "sentinel.txt").read_text(encoding="utf-8") == "SENTINEL-ORIGINAL"
    # Total file count unchanged.
    post_count = sum(1 for p in tmp_path.rglob("*") if p.is_file())
    assert post_count == pre_count
    out = capsys.readouterr().out
    assert "nothing was changed" in out.lower() or "--force" in out.lower()


def test_init_force_overwrites_and_backs_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """force=True on an ACTIVE (>10 files) brain: backs up the original, then re-inits.

    Patches isatty -> False and input -> raise so any regression onto an
    interactive prompt on the force path becomes a loud failure. The safety
    guarantee under test is that the backup preserves the pre-init content
    (here a sentinel file) even though .brain itself is rebuilt.
    """
    _isolate(monkeypatch, tmp_path)
    # Force stdin to report non-tty so the non-interactive branch is taken
    # even if force handling ever regresses onto an isatty() check.
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    # Seed an ACTIVE brain: >10 entries so the file_count > 10 protection
    # branch is exercised, with a sentinel whose content we re-read from the
    # backup after re-init.
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    (brain / "memory").mkdir()
    (brain / "agents").mkdir()
    (brain / "config").mkdir()
    (brain / "sentinel.txt").write_text("SENTINEL-ORIGINAL", encoding="utf-8")
    for i in range(12):
        (brain / "ledger" / f"entry_{i:02d}.json").write_text(
            json.dumps({"i": i}), encoding="utf-8"
        )
    # Sanity: the seeded brain crosses the >10 bright-line the function uses.
    assert len(list(brain.rglob("*"))) > 10

    ok = init_brain(".brain", force=True)

    # (a) re-init succeeded.
    assert ok is True

    # (b) a *.backup.* directory now exists in tmp_path.
    backups = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".brain.backup."))
    assert backups, "expected at least one .brain.backup.<ts> directory after force reinit"
    latest_backup = tmp_path / backups[-1]

    # (c) the backup preserved the sentinel with its original content — this
    #     is the safety guarantee: force overwrites .brain, but never loses it.
    assert (latest_backup / "sentinel.txt").is_file()
    assert (latest_backup / "sentinel.txt").read_text(encoding="utf-8") == "SENTINEL-ORIGINAL"

    # (d) .brain was re-initialised: the default-template structure is present.
    assert (brain / "ledger" / "state.json").is_file()
    assert (brain / "memory" / "context.md").is_file()
    assert (brain / "config" / "nucleus.yaml").is_file()

    out = capsys.readouterr().out
    assert "backup" in out.lower()


def test_init_interactive_abort_preserves_brain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Interactive path is unchanged: a non-confirming prompt answer aborts cleanly.

    Opposed pair to test_reinit_without_force_aborts_noninteractively. Here
    stdin IS a tty and the user types a non-confirming string ("no"), so the
    interactive branch runs input() and must abort on a non-'y' answer — no
    backup, no mutation, every file byte-identical. Proves the interactive
    path was not silently redirected onto the non-interactive one.
    """
    _isolate(monkeypatch, tmp_path)
    # Override _isolate's input-raises stub: the interactive path is allowed
    # to prompt, and here the user answers "no" (not 'y', so abort).
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", lambda *a, **k: "no")

    # Seed an existing brain with ≤10 files so the file_count > 10 branch is
    # NOT taken — the plain "Directory already exists" interactive path runs.
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    (brain / "ledger" / "state.json").write_text('{"v": "PRE"}', encoding="utf-8")
    (brain / "sentinel.txt").write_text("SENTINEL-ORIGINAL", encoding="utf-8")
    pre_count = sum(1 for p in tmp_path.rglob("*") if p.is_file())
    assert pre_count <= 10, "seeded brain must stay ≤10 files to hit the plain-exists branch"

    ok = init_brain(".brain")

    # (a) aborted.
    assert ok is False
    # (b) .brain still exists with all its files intact.
    assert brain.is_dir()
    assert (brain / "ledger" / "state.json").read_text(encoding="utf-8") == '{"v": "PRE"}'
    assert (brain / "sentinel.txt").is_file()
    assert (brain / "sentinel.txt").read_text(encoding="utf-8") == "SENTINEL-ORIGINAL"
    # (c) no *.backup.* directory created anywhere.
    assert list(tmp_path.glob("**/*.backup.*")) == []
    # (d) total file count unchanged — nothing was added or removed.
    post_count = sum(1 for p in tmp_path.rglob("*") if p.is_file())
    assert post_count == pre_count
    out = capsys.readouterr().out
    assert "abort" in out.lower()
