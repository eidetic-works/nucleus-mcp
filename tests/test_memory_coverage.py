"""Coverage tests for runtime/memory.py."""
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import memory as memory_mod
from mcp_server_nucleus.runtime.memory import _read_memory, _search_memory, _write_memory, get_brain_path


def _setup_brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    (brain / "memory").mkdir(parents=True)
    (brain / "ledger").mkdir(parents=True)
    return brain


def test_get_brain_path_from_env(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    assert get_brain_path() == brain


def test_get_brain_path_fallback_dotbrain(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    (tmp_path / ".brain").mkdir()
    monkeypatch.chdir(tmp_path)
    assert get_brain_path() == tmp_path / ".brain"


def test_get_brain_path_fallback_parent(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    (tmp_path / ".brain").mkdir()
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert get_brain_path() == tmp_path / ".brain"


def test_get_brain_path_no_brain_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    with pytest.raises(ValueError):
        get_brain_path()


def test_write_memory_learnings(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    res = _write_memory("my engram", category="learnings")
    assert "Memory written" in res
    content = (brain / "memory" / "learnings.md").read_text()
    assert "my engram" in content


def test_write_memory_context(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    _write_memory("ctx", category="context")
    assert (brain / "memory" / "context.md").exists()


def test_write_memory_patterns(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    _write_memory("pat", category="patterns")
    assert (brain / "memory" / "patterns.md").exists()


def test_write_memory_decisions(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    _write_memory("dec", category="decisions")
    assert (brain / "ledger" / "decisions.md").exists()


def test_write_memory_memory_alias(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    _write_memory("x", category="memory")
    assert (brain / "memory" / "learnings.md").exists()


def test_write_memory_unknown_category_defaults_learnings(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    _write_memory("x", category="bogus")
    assert (brain / "memory" / "learnings.md").exists()


def test_write_memory_appends(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    _write_memory("first", category="learnings")
    _write_memory("second", category="learnings")
    content = (brain / "memory" / "learnings.md").read_text()
    assert "first" in content
    assert "second" in content


def test_read_memory_valid(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "context.md").write_text("hello context")
    res = _read_memory("context")
    assert res["category"] == "context"
    assert res["content"] == "hello context"


def test_read_memory_decisions(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "ledger" / "decisions.md").write_text("dec1")
    res = _read_memory("decisions")
    assert res["content"] == "dec1"


def test_read_memory_invalid_category(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    res = _read_memory("bogus")
    assert "error" in res


def test_read_memory_missing_file(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    res = _read_memory("context")
    assert "error" in res


def test_search_memory_with_ripgrep(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "learnings.md").write_text("hello world\nfoo bar\n")
    res = _search_memory("hello")
    assert res["query"] == "hello"
    assert res["count"] >= 1


def test_search_memory_fallback_no_ripgrep(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "learnings.md").write_text("hello world\nfoo bar\n")
    # force FileNotFoundError by making subprocess.run raise
    import subprocess as sp
    real_run = sp.run

    def fake_run(cmd, *a, **kw):
        raise FileNotFoundError("no rg")

    monkeypatch.setattr(sp, "run", fake_run)
    res = _search_memory("hello")
    assert res["count"] >= 1


def test_search_memory_no_results(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "learnings.md").write_text("nothing here")
    res = _search_memory("zzzznotfound")
    assert res["count"] == 0


def test_search_memory_includes_decisions(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "ledger" / "decisions.md").write_text("specialdecision\n")
    res = _search_memory("specialdecision")
    assert res["count"] >= 1


def test_search_memory_error_returns_error_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_mod, "get_brain_path", lambda: (_ for _ in ()).throw(ValueError("boom")))
    res = _search_memory("x")
    assert "error" in res


def test_read_memory_error_returns_error_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_mod, "get_brain_path", lambda: (_ for _ in ()).throw(ValueError("boom")))
    res = _read_memory("context")
    assert "error" in res


def test_write_memory_error_returns_error_str(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_mod, "get_brain_path", lambda: (_ for _ in ()).throw(ValueError("boom")))
    res = _write_memory("x", category="learnings")
    assert "Error" in res


# ── Move 2 batch 5: SoR read-model repoint (flag-ON, STRICT) ──────────────
# _search_memory default flag-ON unions the SoR (hybrid); mode="grep" is the
# RETAINED explicit ripgrep fallback. STRICT for both flag states — no `or True`.

def _seed_sor(brain: Path, text: str) -> None:
    from mcp_server_nucleus.memory.facade import MemoryFacade
    MemoryFacade(brain_path=brain, enabled=True).capture("claude_code", text, kind="note")


def test_search_memory_flag_on_hybrid_unions_sor(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "learnings.md").write_text("grep alpha line\n")
    monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
    _seed_sor(brain, "sorbeta reordered token unique")
    res = _search_memory("sorbeta")  # only in the SoR, not the grep corpus
    blob = "\n".join(res["results"])
    # STRICT: SoR-only doc surfaces only if the default routes through recall.
    assert "sorbeta reordered token unique" in blob, blob


def test_search_memory_grep_mode_excludes_sor(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "learnings.md").write_text("grep gamma line\n")
    monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
    _seed_sor(brain, "sordelta only in sor")
    res = _search_memory("sordelta", mode="grep")  # explicit RETAINED fallback
    # STRICT: grep mode must NOT union the SoR (escape hatch stays pure grep).
    assert res["count"] == 0
    # And grep still finds a grep-corpus term under mode="grep".
    res2 = _search_memory("gamma", mode="grep")
    assert res2["count"] >= 1


def test_search_memory_flag_off_is_grep_only(tmp_path, monkeypatch):
    brain = _setup_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "memory" / "learnings.md").write_text("grep epsilon line\n")
    monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
    _seed_sor(brain, "soromega only in sor")
    monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "")
    res = _search_memory("soromega")
    # STRICT: flag-OFF is byte-for-byte ripgrep — the SoR doc is invisible.
    assert res["count"] == 0
