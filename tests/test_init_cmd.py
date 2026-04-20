"""Tests for ``nucleus_wedge.init_cmd.do_init`` (spec §3a steps 1-7).

Bind acceptance criteria #6 (substrate-resolution safety) and #7 (idempotence).
Tests use ``tmp_path`` exclusively — never touch the real ``.brain/``.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from nucleus_wedge.init_cmd import AGENTS_STUB, GITIGNORE_LINES, SUBDIRS, do_init
from nucleus_wedge.seed import SEED_KEYS


def _seeded_engrams(brain: Path, src: Path) -> None:
    """Copy a real engrams.json snapshot into a tmp brain so seed resolution exercises real data."""
    dst = brain / "memory"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst / "engrams.json")


@pytest.fixture
def engrams_src() -> Path:
    """Resolve a real engrams.json from NUCLEUS_TEST_ENGRAMS_PATH; skip if unset/missing.

    Set NUCLEUS_TEST_ENGRAMS_PATH to the absolute path of an engrams.json
    snapshot (e.g. ``$HOME/.brain/memory/engrams.json`` on a developer machine)
    to enable these tests. CI / fresh installs without that env var skip cleanly.
    """
    import os
    env_path = os.environ.get("NUCLEUS_TEST_ENGRAMS_PATH")
    if not env_path:
        pytest.skip("NUCLEUS_TEST_ENGRAMS_PATH not set — skipping seed-resolution tests")
    src = Path(env_path)
    if not src.exists():
        pytest.skip(f"NUCLEUS_TEST_ENGRAMS_PATH points to missing file: {src}")
    return src


def test_init_fresh_creates_full_tree(tmp_path: Path, engrams_src: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)

    rc = do_init(brain_path_arg=str(brain), seeds_mode="default", force=False)

    assert rc == 0
    for sub in SUBDIRS:
        assert (brain / sub).is_dir()
    assert (brain / "engrams" / "history.jsonl").exists()
    gitignore_text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    for line in GITIGNORE_LINES:
        assert line in gitignore_text
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == AGENTS_STUB
    out = capsys.readouterr().out
    assert "engrams: created" in out
    assert "seeds: 3 added" in out
    assert "next_step: nucleus mcp register --client claude-code" in out


def test_init_idempotent_seeds(tmp_path: Path, engrams_src: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Criterion #7: second run reports skipped, no duplicate rows."""
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)

    do_init(brain_path_arg=str(brain), seeds_mode="default", force=False)
    capsys.readouterr()
    history = brain / "engrams" / "history.jsonl"
    first_count = sum(1 for _ in history.open(encoding="utf-8"))

    rc2 = do_init(brain_path_arg=str(brain), seeds_mode="default", force=False)
    second_count = sum(1 for _ in history.open(encoding="utf-8"))

    assert rc2 == 0
    assert second_count == first_count
    out = capsys.readouterr().out
    assert "seeds: 3 skipped (already present)" in out
    assert "engrams: existing" in out


def test_init_seeds_none_skips_step_4(tmp_path: Path, engrams_src: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)

    rc = do_init(brain_path_arg=str(brain), seeds_mode="none", force=False)

    assert rc == 0
    history_lines = (brain / "engrams" / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert history_lines == []
    assert "seeds: 0 (--seeds none)" in capsys.readouterr().out


def test_init_force_overwrites_only_agents(tmp_path: Path, engrams_src: Path) -> None:
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)
    pre_existing = "# my own AGENTS.md\n"
    (tmp_path / "AGENTS.md").write_text(pre_existing, encoding="utf-8")

    do_init(brain_path_arg=str(brain), seeds_mode="default", force=False)
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == pre_existing

    do_init(brain_path_arg=str(brain), seeds_mode="default", force=True)
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == AGENTS_STUB


def test_init_aborts_with_no_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Criterion #6: from a dir with no .git/.brain/env/flag, abort non-zero, no writes."""
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    pre_listing = sorted(p.name for p in tmp_path.iterdir())

    rc = do_init(brain_path_arg=None, seeds_mode="default", force=False)

    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot resolve brain path" in err
    assert "--brain-path" in err
    assert "NUCLEUS_BRAIN_PATH" in err
    assert sorted(p.name for p in tmp_path.iterdir()) == pre_listing


def test_init_gitignore_dedup(tmp_path: Path, engrams_src: Path) -> None:
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n.brain/relay/\n", encoding="utf-8")
    pre_size_node = "node_modules/"

    do_init(brain_path_arg=str(brain), seeds_mode="none", force=False)

    text = gitignore.read_text(encoding="utf-8")
    assert text.count(pre_size_node) == 1
    assert text.count(".brain/relay/") == 1
    for line in GITIGNORE_LINES:
        assert line in text


def test_init_resolves_via_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engrams_src: Path
) -> None:
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.chdir(tmp_path)

    rc = do_init(brain_path_arg=None, seeds_mode="default", force=False)

    assert rc == 0
    assert (brain / "engrams" / "history.jsonl").exists()


def test_init_resolves_via_cwd_dot_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engrams_src: Path
) -> None:
    """Greenfield path: cwd has .git, no .brain → init creates .brain/ in cwd."""
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    _seeded_engrams(tmp_path / ".brain", engrams_src)

    rc = do_init(brain_path_arg=None, seeds_mode="default", force=False)

    assert rc == 0
    assert (tmp_path / ".brain" / "engrams" / "history.jsonl").exists()


def test_init_summary_records_3_keys_via_seed_module(
    tmp_path: Path, engrams_src: Path
) -> None:
    """Cross-check: history.jsonl contains exactly the three SEED_KEYS after fresh init."""
    brain = tmp_path / ".brain"
    _seeded_engrams(brain, engrams_src)

    do_init(brain_path_arg=str(brain), seeds_mode="default", force=False)

    keys = []
    with (brain / "engrams" / "history.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            keys.append(json.loads(line)["key"])
    assert sorted(keys) == sorted(SEED_KEYS)
