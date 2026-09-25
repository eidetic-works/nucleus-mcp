"""Tests for scripts/primitives_bijection_gate.py (treatment sweep #003b vaccine).

Covers the three regression classes a decorator-grep gate leaks (peer verdict
2026-06-11T04:03Z):
  1) documented-but-not-registered (dead row)
  2) registered-but-not-documented (new tool without inventory update)
  3) Server-C dispatch-table tools (no @mcp.tool decorator)

Plus the doc-parser regex, end-to-end main() exit codes, and the env-gated
Server C scan.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_gate():
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / "scripts" / "primitives_bijection_gate.py"
    spec = importlib.util.spec_from_file_location("primitives_bijection_gate", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bg = _load_gate()


def test_primitives_doc_regex_extracts_table_rows(tmp_path):
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("""
# Inventory

## Server A

| # | Tool | Reg site | Caller | Class |
|---|------|----------|--------|-------|
| 1 | `nucleus_governance` | tools/governance.py:330 | ... | HOOK-NUDGED |
| 2 | `nucleus_engrams` | tools/engrams.py:376 | ... | HOOK-NUDGED |

## Notes

- `nucleus_NOT_a_row` should NOT match (not a table row).

## Server B

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 21 | `remember` | nucleus_wedge/server.py:30 | ... | HOOK-NUDGED |
""")
    out = bg.primitives_from_doc(doc)
    assert out == {"nucleus_governance", "nucleus_engrams", "remember"}


def test_primitives_doc_missing_file_returns_empty(tmp_path):
    assert bg.primitives_from_doc(tmp_path / "nope.md") == set()


def test_diff_bijection_shared_only_is_OK_state():
    diff = bg.diff_bijection(
        doc_primitives={"a", "b"},
        a={"a", "b"},
        b=set(),
        c=set(),
    )
    assert diff["documented_but_not_registered"] == []
    assert diff["registered_but_not_documented"] == []
    assert diff["shared"] == ["a", "b"]


def test_diff_bijection_detects_documented_but_not_registered():
    """Regression class 1: a row exists in PRIMITIVES.md but the tool never loaded
    (dead-in-registry like tools/archive.py was — decorator present, module not
    imported, would silently pass a decorator-grep gate)."""
    diff = bg.diff_bijection(
        doc_primitives={"alive", "dead"},
        a={"alive"},
        b=set(),
        c=set(),
    )
    assert diff["documented_but_not_registered"] == ["dead"]
    assert diff["registered_but_not_documented"] == []


def test_diff_bijection_detects_registered_but_not_documented():
    """Regression class 2: a new tool got added to source but no PRIMITIVES.md
    row was added — the inventory drifted."""
    diff = bg.diff_bijection(
        doc_primitives={"alive"},
        a={"alive", "new_undocumented"},
        b=set(),
        c=set(),
    )
    assert diff["documented_but_not_registered"] == []
    assert diff["registered_but_not_documented"] == ["new_undocumented"]


def test_diff_bijection_picks_up_server_c_dispatch_table():
    """Regression class 3: Server C uses @server.list_tools / @server.call_tool
    dispatch table — zero @mcp.tool occurrences in source. A decorator-grep
    gate misses Server C entirely; the bijection gate sees these via the
    runtime-manifest path."""
    diff = bg.diff_bijection(
        doc_primitives={"search_engrams", "nucleus_curate"},
        a=set(),
        b=set(),
        c={"search_engrams", "nucleus_curate"},
    )
    assert diff["shared"] == sorted({"search_engrams", "nucleus_curate"})
    assert diff["documented_but_not_registered"] == []
    assert diff["registered_but_not_documented"] == []


def test_diff_bijection_detects_server_c_new_undocumented():
    """If a Server C tool gets added via dispatch table without a row, the
    bijection gate must catch it (decorator-grep cannot)."""
    diff = bg.diff_bijection(
        doc_primitives={"search_engrams"},
        a=set(),
        b=set(),
        c={"search_engrams", "new_dispatch_tool"},
    )
    assert diff["registered_but_not_documented"] == ["new_dispatch_tool"]


def test_main_returns_zero_on_clean_bijection(tmp_path, monkeypatch):
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("| 1 | `nucleus_tasks` | tools/tasks.py:80 | ... | ALLOW-LISTED |\n")
    monkeypatch.setattr(bg, "server_a_tools", lambda: {"nucleus_tasks"})
    monkeypatch.setattr(bg, "server_b_tools", lambda: set())
    monkeypatch.setattr(bg, "server_c_tools", lambda: set())

    rc = bg.main(["--doc", str(doc)])
    assert rc == 0


def test_main_returns_one_on_drift(tmp_path, monkeypatch):
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("| 1 | `nucleus_tasks` | tools/tasks.py:80 | ... | ALLOW-LISTED |\n")
    monkeypatch.setattr(bg, "server_a_tools", lambda: {"nucleus_tasks", "extra_new"})
    monkeypatch.setattr(bg, "server_b_tools", lambda: set())
    monkeypatch.setattr(bg, "server_c_tools", lambda: set())

    rc = bg.main(["--doc", str(doc)])
    assert rc == 1


def test_main_allow_drift_returns_zero_with_drift(tmp_path, monkeypatch):
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("| 1 | `nucleus_tasks` | tools/tasks.py:80 | ... | ALLOW-LISTED |\n")
    monkeypatch.setattr(bg, "server_a_tools", lambda: {"nucleus_tasks", "extra_new"})
    monkeypatch.setattr(bg, "server_b_tools", lambda: set())
    monkeypatch.setattr(bg, "server_c_tools", lambda: set())

    rc = bg.main(["--doc", str(doc), "--allow-drift"])
    assert rc == 0


def test_main_returns_two_when_doc_has_no_primitives(tmp_path):
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("# Empty doc, no table rows\n")
    rc = bg.main(["--doc", str(doc)])
    assert rc == 2


def test_main_returns_two_when_doc_missing(tmp_path):
    rc = bg.main(["--doc", str(tmp_path / "nope.md")])
    assert rc == 2


def test_server_c_skipped_when_env_var_unset_returns_empty_set(monkeypatch):
    """Scan disabled is set() (opt-out signal), NOT None (failure signal).
    This distinction lets main() exit 0 via the excluded-section path
    instead of exit 2 (cc-main crack #4)."""
    monkeypatch.delenv("NUCLEUS_BIJECTION_SCAN_SERVER_C", raising=False)
    assert bg.server_c_tools() == set()


def test_enumerator_prefers_get_tools_over_list_tools():
    """cc-main crack #3: fastmcp 2.14.3 standalone API is get_tools(); the
    official mcp SDK uses list_tools(). Prefer the standalone form, fall
    back to the official one."""
    class _Mcp:
        async def get_tools(self):
            return {"alpha": object(), "beta": object()}
        async def list_tools(self):
            # If get_tools is preferred, this MUST NOT be called.
            raise AssertionError("list_tools should not be called when get_tools is available")
    assert bg._enumerate_fastmcp_tools(_Mcp()) == {"alpha", "beta"}


def test_enumerator_falls_back_to_list_tools():
    """When get_tools is absent but list_tools is present (official mcp SDK)."""
    class _Tool:
        def __init__(self, name):
            self.name = name
    class _Mcp:
        async def list_tools(self):
            return [_Tool("alpha"), _Tool("beta")]
    assert bg._enumerate_fastmcp_tools(_Mcp()) == {"alpha", "beta"}


def test_enumerator_returns_none_when_neither_api_present():
    """cc-main crack #4: neither attribute = scan-impossible. Returns None
    so main() can exit 2 (scan failed) instead of 1 (drift) or 0 (false green)."""
    class _Mcp:
        pass
    assert bg._enumerate_fastmcp_tools(_Mcp()) is None


def test_enumerator_returns_none_on_runtime_error():
    """Async-loop-already-running etc. = scan-failed, not empty."""
    class _Mcp:
        async def get_tools(self):
            raise RuntimeError("already in event loop")
    assert bg._enumerate_fastmcp_tools(_Mcp()) is None


def test_server_c_returns_none_when_enabled_but_empty(monkeypatch, tmp_path):
    """Peer residual nit (2026-06-11T10:31Z): SCAN_SERVER_C=1 + bridge
    importable + handler raises + parser fallback returns set() should
    NOT conflate with scan-disabled. Empty result with scan enabled is
    treated as scan-failed (None) so main() exits 2."""
    monkeypatch.setenv("NUCLEUS_BIJECTION_SCAN_SERVER_C", "1")
    monkeypatch.setenv("NUCLEUS_EIDETIC_BRIDGE_PATH", str(tmp_path))

    # Plant a stub eidetic_mcp.server module on sys.path that has no
    # list_tools_handler and an empty __file__ (so dispatch-table grep
    # returns empty).
    bridge_pkg = tmp_path / "eidetic_mcp"
    bridge_pkg.mkdir()
    (bridge_pkg / "__init__.py").write_text("")
    (bridge_pkg / "server.py").write_text("# empty source; no Tool(name=...)\n")

    import sys as _sys
    # Drop any previous cache; force fresh import.
    for k in list(_sys.modules):
        if k.startswith("eidetic_mcp"):
            del _sys.modules[k]

    result = bg.server_c_tools()
    assert result is None, f"empty-with-knob-set should be None (scan failed), got {result!r}"


def test_main_returns_two_when_server_enumeration_fails(tmp_path, monkeypatch):
    """cc-main crack #4: any server enumerator returning None must escalate
    to exit 2; the previous behavior treated it as drift (exit 1) or false
    green (exit 0 via excluded-section)."""
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("| 1 | `nucleus_tasks` | tasks.py:80 | ... | ALLOW-LISTED |\n")
    monkeypatch.setattr(bg, "server_a_tools", lambda: None)  # scan failed
    monkeypatch.setattr(bg, "server_b_tools", lambda: set())
    monkeypatch.setattr(bg, "server_c_tools", lambda: set())

    rc = bg.main(["--doc", str(doc)])
    assert rc == 2  # NOT 1 (drift) — scan failed must be distinct signal


def test_primitives_per_server_parses_sections(tmp_path):
    """The per-server breakdown lets the gate exclude Server-C-only rows when
    Server C scan is disabled — otherwise CI runners without eidetic-daemon
    mounted would always see Server C tools as drift."""
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("""
# Inventory

## Server A — mcp-server-nucleus

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 1 | `nucleus_governance` | gov.py:330 | ... | HOOK-NUDGED |
| 2 | `nucleus_tasks` | tasks.py:80 | ... | ALLOW-LISTED |

## Server B — nucleus_wedge

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 21 | `remember` | wedge.py:30 | ... | HOOK-NUDGED |

## Server C — eidetic daemon bridge

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 30 | `search_engrams` | server.py:422 | ... | HOOK-NUDGED |
| 35 | `count_engrams` | server.py:571 | ... | DEAD-IN-CODE |
""")
    per_server = bg.primitives_per_server(doc)
    assert per_server["A"] == {"nucleus_governance", "nucleus_tasks"}
    assert per_server["B"] == {"remember"}
    assert per_server["C"] == {"search_engrams", "count_engrams"}


def test_main_excludes_server_c_rows_when_scan_disabled(tmp_path, monkeypatch):
    """End-to-end: Server C scan disabled + doc has Server C section -> those
    rows are EXCLUDED from the bijection check (else CI flakes)."""
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("""
## Server A

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 1 | `nucleus_tasks` | tasks.py:80 | ... | ALLOW-LISTED |

## Server C

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 30 | `search_engrams` | server.py:422 | ... | HOOK-NUDGED |
""")
    monkeypatch.setattr(bg, "server_a_tools", lambda: {"nucleus_tasks"})
    monkeypatch.setattr(bg, "server_b_tools", lambda: set())
    monkeypatch.setattr(bg, "server_c_tools", lambda: set())  # disabled

    rc = bg.main(["--doc", str(doc)])
    assert rc == 0  # Server C rows excluded, A's nucleus_tasks bijects


def test_main_includes_server_c_rows_when_scan_enabled(tmp_path, monkeypatch):
    """Mirror: Server C scan ENABLED -> Server C rows MUST biject with registered."""
    doc = tmp_path / "PRIMITIVES.md"
    doc.write_text("""
## Server A

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 1 | `nucleus_tasks` | tasks.py:80 | ... | ALLOW-LISTED |

## Server C

| # | Tool | Reg | Caller | Class |
|---|------|-----|--------|-------|
| 30 | `search_engrams` | server.py:422 | ... | HOOK-NUDGED |
""")
    monkeypatch.setattr(bg, "server_a_tools", lambda: {"nucleus_tasks"})
    monkeypatch.setattr(bg, "server_b_tools", lambda: set())
    monkeypatch.setattr(bg, "server_c_tools", lambda: {"search_engrams"})  # enabled

    rc = bg.main(["--doc", str(doc)])
    assert rc == 0
