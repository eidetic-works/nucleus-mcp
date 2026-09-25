"""nucleus_root must not assume anything about the machine it runs on."""

import pytest

from mcp_server_nucleus import paths


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("NUCLEUS_ROOT", raising=False)
    monkeypatch.delenv("NUCLEUS_BRAIN", raising=False)


def test_env_var_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_ROOT", str(tmp_path / "explicit"))
    assert paths.nucleus_root() == tmp_path / "explicit"


def test_discovers_root_from_a_subdirectory(monkeypatch, tmp_path):
    (tmp_path / ".brain").mkdir()
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    assert paths.nucleus_root() == tmp_path.resolve()


def test_without_a_brain_falls_back_to_cwd_not_a_hard_coded_home(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    root = paths.nucleus_root()
    assert root == tmp_path.resolve()
    assert "ai-mvp-backend" not in str(root)


def test_strict_mode_explains_how_to_fix_it(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(paths.NucleusPathError) as exc:
        paths.nucleus_root(strict=True)
    msg = str(exc.value)
    assert "NUCLEUS_ROOT" in msg and "nucleus init" in msg


def test_brain_path_follows_the_discovered_root(monkeypatch, tmp_path):
    (tmp_path / ".brain").mkdir()
    monkeypatch.chdir(tmp_path)
    assert paths.brain_path() == tmp_path.resolve() / ".brain"
