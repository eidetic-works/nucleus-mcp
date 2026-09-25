"""Sibling-repo script resolution: found, not found, and configured two ways."""

import os
import pytest

from mcp_server_nucleus.runtime import sibling_repos


def test_finds_script_in_this_repo_first(tmp_path, monkeypatch):
    sibling = tmp_path / "sibling"
    (sibling / "scripts").mkdir(parents=True)
    (sibling / "scripts" / "x.py").write_text("# sibling copy\n")
    monkeypatch.setenv("NUCLEUS_SIBLING_REPOS", str(sibling))
    own = sibling_repos.PROJECT_ROOT / "scripts" / "map_gen.py"
    if own.exists():
        assert sibling_repos.find_script("scripts/map_gen.py") == own


def test_finds_script_in_a_sibling(tmp_path, monkeypatch):
    sibling = tmp_path / "tb"
    (sibling / "scripts").mkdir(parents=True)
    target = sibling / "scripts" / "moved_away.py"
    target.write_text("# moved in the split\n")
    monkeypatch.setenv("NUCLEUS_SIBLING_REPOS", str(sibling))
    assert sibling_repos.find_script("scripts/moved_away.py") == target
    assert sibling_repos.require_script("scripts/moved_away.py") == target


def test_missing_script_raises_and_names_where_it_looked(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_SIBLING_REPOS", str(tmp_path))
    with pytest.raises(FileNotFoundError) as exc:
        sibling_repos.require_script("scripts/not_anywhere.py")
    msg = str(exc.value)
    assert "not_anywhere.py" in msg
    assert str(tmp_path) in msg          # says where it looked
    assert "NUCLEUS_SIBLING_REPOS" in msg  # says how to fix it


def test_find_returns_none_rather_than_raising(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_SIBLING_REPOS", str(tmp_path))
    assert sibling_repos.find_script("scripts/not_anywhere.py") is None


def test_env_override_uses_pathsep(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    (b / "scripts").mkdir(parents=True)
    (b / "scripts" / "second.py").write_text("x\n")
    monkeypatch.setenv("NUCLEUS_SIBLING_REPOS", os.pathsep.join([str(a), str(b)]))
    assert sibling_repos.find_script("scripts/second.py") == b / "scripts" / "second.py"


def test_no_configuration_means_this_repo_only(tmp_path, monkeypatch):
    """Nothing about the host machine is assumed: unconfigured, only this repo is searched."""
    monkeypatch.delenv("NUCLEUS_SIBLING_REPOS", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))       # no siblings file inside
    monkeypatch.delenv("NUCLEUS_CONFIG_HOME", raising=False)
    import importlib
    importlib.reload(sibling_repos)
    assert sibling_repos.search_roots() == [sibling_repos.PROJECT_ROOT]
    assert sibling_repos.find_script("scripts/not_anywhere.py") is None


def test_config_file_is_read_when_env_is_unset(tmp_path, monkeypatch):
    sibling = tmp_path / "companion"
    (sibling / "scripts").mkdir(parents=True)
    (sibling / "scripts" / "from_config.py").write_text("x\n")
    cfg = tmp_path / "cfg" / "nucleus"
    cfg.mkdir(parents=True)
    (cfg / "siblings").write_text(f"# comment line\n{sibling}\n")
    monkeypatch.delenv("NUCLEUS_SIBLING_REPOS", raising=False)
    monkeypatch.setenv("NUCLEUS_CONFIG_HOME", str(cfg))
    import importlib
    importlib.reload(sibling_repos)
    assert sibling_repos.find_script("scripts/from_config.py") == sibling / "scripts" / "from_config.py"
