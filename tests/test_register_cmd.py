"""Tests for ``nucleus_wedge.register_cmd.do_register`` (spec §3b steps 1-6).

Bind acceptance criteria #8 (idempotence — register) and #9 (preservation —
non-nucleus MCP entries unchanged via sha256). All tests use ``tmp_path``
and monkeypatch ``shutil.which`` / ``Store.brain_path`` so we never touch
``~/.claude.json`` or rely on a real install.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from nucleus_wedge import register_cmd
from nucleus_wedge.register_cmd import WEDGE_KEY, do_register


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setattr(
        "nucleus_wedge.register_cmd.Store.brain_path",
        lambda flag=None: brain,
    )
    return brain


@pytest.fixture
def fake_binary(monkeypatch: pytest.MonkeyPatch) -> str:
    binary = "/opt/venv/bin/nucleus-wedge"
    monkeypatch.setattr(register_cmd, "_resolve_binary", lambda: binary)
    return binary


def _sha256_siblings(config: dict) -> str:
    siblings = {k: v for k, v in config.get("mcpServers", {}).items() if k != WEDGE_KEY}
    payload = json.dumps(siblings, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _seed_config(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_register_fresh_inserts_entry(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "claude.json"
    _seed_config(config, {"mcpServers": {"other": {"command": "/usr/bin/other"}}})

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 0
    written = json.loads(config.read_text(encoding="utf-8"))
    assert written["mcpServers"][WEDGE_KEY]["command"] == fake_binary
    assert written["mcpServers"][WEDGE_KEY]["env"]["NUCLEUS_BRAIN_PATH"] == str(fake_brain)
    assert written["mcpServers"]["other"] == {"command": "/usr/bin/other"}
    out = capsys.readouterr().out
    assert "backup:" in out
    assert "entry: nucleus_wedge" in out
    backups = list(tmp_path.glob("claude.json.bak.*"))
    assert len(backups) == 1


def test_register_idempotent(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Criterion #8: second run skips, config bytes unchanged."""
    config = tmp_path / "claude.json"
    _seed_config(config, {"mcpServers": {}})

    do_register(config_path_arg=str(config), dry_run=False)
    capsys.readouterr()
    bytes_after_first = config.read_bytes()
    backups_after_first = sorted(tmp_path.glob("claude.json.bak.*"))

    rc2 = do_register(config_path_arg=str(config), dry_run=False)
    bytes_after_second = config.read_bytes()
    backups_after_second = sorted(tmp_path.glob("claude.json.bak.*"))

    assert rc2 == 0
    assert bytes_after_first == bytes_after_second
    assert backups_after_first == backups_after_second  # no new backup on no-op
    assert "skipping (idempotent no-op)" in capsys.readouterr().out


def test_register_preserves_sibling_entries_sha256(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
) -> None:
    """Criterion #9: sha256 of mcpServers excluding nucleus_wedge unchanged."""
    config = tmp_path / "claude.json"
    siblings = {
        "alpha": {"command": "/bin/alpha", "env": {"X": "1"}},
        "beta": {"command": "/bin/beta", "args": ["--port", "9000"]},
    }
    _seed_config(config, {"mcpServers": dict(siblings)})
    pre_digest = _sha256_siblings(json.loads(config.read_text(encoding="utf-8")))

    do_register(config_path_arg=str(config), dry_run=False)

    post_digest = _sha256_siblings(json.loads(config.read_text(encoding="utf-8")))
    assert pre_digest == post_digest


def test_register_dry_run_no_write(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "claude.json"
    _seed_config(config, {"mcpServers": {}})
    pre_bytes = config.read_bytes()

    rc = do_register(config_path_arg=str(config), dry_run=True)

    assert rc == 0
    assert config.read_bytes() == pre_bytes
    assert list(tmp_path.glob("claude.json.bak.*")) == []
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert WEDGE_KEY in out


def test_register_aborts_on_corrupt_json(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "claude.json"
    config.write_text("{ broken json", encoding="utf-8")
    pre_bytes = config.read_bytes()

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 1
    assert config.read_bytes() == pre_bytes
    err = capsys.readouterr().err
    assert "not valid JSON" in err
    assert "Refusing to rewrite" in err


def test_register_aborts_on_missing_config(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "does_not_exist.json"

    rc = do_register(config_path_arg=str(missing), dry_run=False)

    assert rc == 1
    assert "config not found" in capsys.readouterr().err


def test_register_aborts_when_binary_missing(
    tmp_path: Path,
    fake_brain: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(register_cmd, "_resolve_binary", lambda: None)
    config = tmp_path / "claude.json"
    _seed_config(config, {"mcpServers": {}})

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 1
    assert "cannot locate `nucleus-wedge` binary" in capsys.readouterr().err


def test_register_updates_existing_stale_entry(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
) -> None:
    """If existing entry has a stale binary path, register updates it (not idempotent)."""
    config = tmp_path / "claude.json"
    _seed_config(
        config,
        {
            "mcpServers": {
                WEDGE_KEY: {
                    "command": "/old/binary/path",
                    "args": [],
                    "env": {"NUCLEUS_BRAIN_PATH": "/old/brain"},
                }
            }
        },
    )

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 0
    written = json.loads(config.read_text(encoding="utf-8"))
    assert written["mcpServers"][WEDGE_KEY]["command"] == fake_binary
    assert written["mcpServers"][WEDGE_KEY]["env"]["NUCLEUS_BRAIN_PATH"] == str(fake_brain)


def test_register_creates_mcp_servers_when_absent(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
) -> None:
    config = tmp_path / "claude.json"
    _seed_config(config, {"theme": "dark"})

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 0
    written = json.loads(config.read_text(encoding="utf-8"))
    assert WEDGE_KEY in written["mcpServers"]
    assert written["theme"] == "dark"


@pytest.mark.parametrize("bad_value", [None, [], "wrong", 42])
def test_register_aborts_on_non_dict_mcp_servers(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    bad_value: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Non-dict mcpServers must abort pre-write — no TypeError leak, no backup."""
    config = tmp_path / "claude.json"
    _seed_config(config, {"mcpServers": bad_value, "theme": "dark"})
    pre_bytes = config.read_bytes()

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 1
    assert config.read_bytes() == pre_bytes
    assert list(tmp_path.glob("claude.json.bak.*")) == []
    err = capsys.readouterr().err
    assert "mcpServers" in err
    assert "expected object/dict" in err


def test_register_restore_uses_atomic_write(
    tmp_path: Path,
    fake_brain: Path,
    fake_binary: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Post-write validation failure must restore via _atomic_write — symmetric with patch write.

    Asymmetric writes (atomic patch + plain restore) leak partial state to concurrent
    readers during the restore window. Both writes must use the same atomic primitive.
    """
    config = tmp_path / "claude.json"
    _seed_config(config, {"mcpServers": {"other": {"command": "/usr/bin/other"}}})
    original_bytes = config.read_bytes()

    real_atomic = register_cmd._atomic_write
    calls: list[tuple[Path, str]] = []

    def fake_atomic(path: Path, payload: str) -> None:
        calls.append((path, payload))
        if len(calls) == 1:
            real_atomic(path, "{ corrupted")
        else:
            real_atomic(path, payload)

    monkeypatch.setattr(register_cmd, "_atomic_write", fake_atomic)

    rc = do_register(config_path_arg=str(config), dry_run=False)

    assert rc == 1
    assert len(calls) == 2
    assert calls[1][1] == original_bytes.decode("utf-8")
    assert config.read_bytes() == original_bytes
    assert list(tmp_path.glob("*.tmp")) == []
    assert "post-write validation failed" in capsys.readouterr().err
