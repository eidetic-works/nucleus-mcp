"""MemoryFacade tests — Move 2 batch 1 (flag-gated scaffold).

Proves: (a) flag-OFF is a true no-op (callable, persists nothing, creates no db);
(b) flag-ON (env or param) round-trips capture->recall->curate through the SoR;
(c) the env-flag parser; (d) importing the package does not disturb the Move 1
lazy-init contract (`_INITIALIZED` stays False after a bare package import).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.memory import MEMORY_SOR_FLAG, MemoryFacade, sor_flag_enabled


@pytest.fixture(autouse=True)
def _flag_unset(monkeypatch: pytest.MonkeyPatch):
    """Every test starts with NUCLEUS_MEMORY_SOR unset (default OFF)."""
    monkeypatch.delenv(MEMORY_SOR_FLAG, raising=False)


# ── (a) flag-OFF no-op ────────────────────────────────────────────────────
def test_flag_off_is_a_noop(tmp_path: Path) -> None:
    db = tmp_path / "engrams.db"
    mf = MemoryFacade(db_path=db)  # env unset → disabled
    assert mf.enabled is False

    cap = mf.capture("claude_code", "should not persist")
    assert cap == {"id": None, "key": None, "ts": None, "persisted": False}
    assert mf.recall("should not persist") == []
    cur = mf.curate(1, "archive")
    assert cur["ok"] is False and MEMORY_SOR_FLAG in cur["reason"]

    # The decisive no-op evidence: no SoR file was ever created.
    assert not db.exists(), "flag-OFF must not create the SoR db"


def test_flag_off_via_env_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "0")
    mf = MemoryFacade(db_path=tmp_path / "engrams.db")
    assert mf.enabled is False
    assert mf.capture("s", "p")["persisted"] is False


# ── (b) flag-ON round-trip ────────────────────────────────────────────────
def test_flag_on_via_env_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    db = tmp_path / "engrams.db"
    mf = MemoryFacade(db_path=db)
    assert mf.enabled is True

    cap = mf.capture("claude_code", "suspense boundary react note", kind="note")
    assert cap["persisted"] is True
    assert isinstance(cap["id"], int) and cap["key"]
    assert db.exists()

    hits = mf.recall("suspense boundary")
    assert len(hits) == 1
    assert hits[0]["id"] == cap["id"]
    assert "suspense boundary" in hits[0]["text"]


def test_flag_on_via_param_overrides_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MEMORY_SOR_FLAG, raising=False)  # env OFF
    mf = MemoryFacade(db_path=tmp_path / "engrams.db", enabled=True)  # param ON wins
    assert mf.enabled is True
    assert mf.capture("s", "payload text")["persisted"] is True
    assert len(mf.recall("payload")) == 1


def test_full_capture_recall_curate_cycle(tmp_path: Path) -> None:
    mf = MemoryFacade(db_path=tmp_path / "engrams.db", enabled=True)
    a = mf.capture("claude_code", "keep this canonical answer")
    b = mf.capture("claude_code", "noisy duplicate answer to archive")

    # curate: archive one, canonical the other
    assert mf.curate(b["id"], "archive")["ok"] is True
    assert mf.curate(a["id"], "canonical")["ok"] is True

    hits = mf.recall("answer")
    ids = [h["id"] for h in hits]
    assert b["id"] not in ids, "archived engram excluded from default recall"
    assert ids[0] == a["id"], "canonical engram ranks first"
    assert hits[0]["curation"] == "canonical"


def test_recall_literal_token_via_facade(tmp_path: Path) -> None:
    mf = MemoryFacade(db_path=tmp_path / "engrams.db", enabled=True)
    mf.capture("claude_code", "run the tb.py harness in feat/foo-bar")
    hits = mf.recall("tb.py")  # would be an FTS5 syntax error without the retry
    assert len(hits) == 1


# ── (c) env-flag parser ───────────────────────────────────────────────────
@pytest.mark.parametrize(
    "val,expected",
    [("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True),
     ("0", False), ("false", False), ("", False), ("no", False), ("off", False)],
)
def test_sor_flag_enabled_parsing(monkeypatch: pytest.MonkeyPatch, val: str, expected: bool) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, val)
    assert sor_flag_enabled() is expected


def test_sor_flag_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MEMORY_SOR_FLAG, raising=False)
    assert sor_flag_enabled() is False


# ── (d) Move 1 lazy-init contract preserved ───────────────────────────────
def test_import_does_not_trigger_heavy_init() -> None:
    """A bare `import mcp_server_nucleus` + importing the new memory package must
    NOT flip `_INITIALIZED` (Move 1 de-eager contract). Run in a clean subprocess
    so suite ordering can't have pre-initialised the package."""
    src = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import mcp_server_nucleus as m\n"
        "import mcp_server_nucleus.memory as mem\n"
        "assert m._INITIALIZED is False, ('_INITIALIZED', m._INITIALIZED)\n"
        "assert hasattr(mem, 'MemoryFacade')\n"
        "assert hasattr(mem, 'SorStore')\n"
        "print('IMPORT_OK')\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop(MEMORY_SOR_FLAG, None)
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=25
    )
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"
    assert "IMPORT_OK" in r.stdout
