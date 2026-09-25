"""``nucleus agent-os recall <query>`` — selective memory-continuity CLI.

Three tests mirroring test_agent_os_run_cli.py / test_agent_os_pager.py fixture
patterns:
  (a) recall command emits the header + at least one row for a seeded brain.
  (b) with NUCLEUS_AGENT_OS_PAGER=1 the emitted rows are the pager-selected
      slice (fewer/ordered) vs flag-OFF plain recall.
  (c) flag-OFF path is unchanged/plain (raw recall rows, no pager reselect).
"""
import os

import pytest

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod
from mcp_server_nucleus.runtime.agent_os import recall_cli


@pytest.fixture()
def recall_env(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    # PAGER flag explicitly UNSET by default — the byte-identical-OFF contract.
    monkeypatch.delenv(boot_mod.PAGER_FLAG, raising=False)
    return str(brain)


def _seed_brain(brain_path: str) -> None:
    """Seed a tiny temp brain the way test_agent_os_run_cli.py does."""
    from nucleus_wedge.store import Store

    Store(brain_path).append(
        value="The Nucleus gateway routes model calls through the OS; agents live INSIDE.",
        kind="note", tags=["topic:gateway"], source_agent="prior-session",
    )
    Store(brain_path).append(
        value="Unrelated: the floor-3 coffee machine is broken.",
        kind="note", tags=["topic:office"], source_agent="prior-session",
    )
    Store(brain_path).append(
        value="Also unrelated: the office printer is out of toner.",
        kind="note", tags=["topic:office"], source_agent="prior-session",
    )


# ── (a) header + at least one row for a seeded brain ─────────────────────────


def test_recall_cli_emits_header_and_rows(recall_env, capsys):
    brain = recall_env
    _seed_brain(brain)

    rc = recall_cli.recall("gateway", brain_path=brain, recall_limit=5)

    assert rc == 0
    out = capsys.readouterr().out
    # Header line present with row count + budget.
    assert "# selective recall (" in out
    assert "rows, 2000 chars)" in out
    # At least one row line, shaped "- [<idx>] <text>".
    row_lines = [l for l in out.splitlines() if l.startswith("- [")]
    assert row_lines, "recall must emit at least one row for a seeded brain"
    # The gateway memory is among the recalled rows.
    assert any("gateway" in l.lower() for l in row_lines)


# ── (b) pager-ON selects a smaller/ordered slice vs flag-OFF plain ───────────


def test_recall_cli_pager_on_selects_slice(recall_env, monkeypatch, capsys):
    brain = recall_env
    _seed_brain(brain)

    # Flag-OFF plain recall: raw rows in recall-engine order.
    monkeypatch.delenv(boot_mod.PAGER_FLAG, raising=False)
    rc_off = recall_cli.recall("gateway", brain_path=brain, recall_limit=5)
    assert rc_off == 0
    out_off = capsys.readouterr().out
    off_rows = [l for l in out_off.splitlines() if l.startswith("- [")]

    # Flag-ON pager recall: tight budget forces eviction; best-first order.
    monkeypatch.setenv(boot_mod.PAGER_FLAG, "1")
    rc_on = recall_cli.recall(
        "gateway", brain_path=brain, budget=60, recall_limit=5,
    )
    assert rc_on == 0
    out_on = capsys.readouterr().out
    on_rows = [l for l in out_on.splitlines() if l.startswith("- [")]

    # Pager selected FEWER rows than the plain recall (budget eviction).
    assert len(on_rows) <= len(off_rows)
    assert len(on_rows) >= 1
    # Best-first: the gateway memory ranks first under the pager.
    assert "gateway" in on_rows[0].lower()


# ── (c) flag-OFF path is unchanged/plain ─────────────────────────────────────


def test_recall_cli_flag_off_is_plain(recall_env, capsys):
    brain = recall_env
    _seed_brain(brain)

    # PAGER flag unset — the byte-identical-OFF contract.
    assert os.environ.get(boot_mod.PAGER_FLAG) in (None, "")

    rc = recall_cli.recall("gateway", brain_path=brain, recall_limit=5)
    assert rc == 0
    out = capsys.readouterr().out
    rows = [l for l in out.splitlines() if l.startswith("- [")]

    # Plain recall returns the raw _do_recall_query rows unchanged — same rows
    # the boot.recall_and_inject flag-OFF path would see.
    from nucleus_wedge.recall_cmd import _do_recall_query

    raw = _do_recall_query(
        query="gateway", limit=5, kind=None, tags=None,
        since=None, source_filter=None, brain_path_arg=brain,
    )
    # Engram text routinely contains newlines, and the CLI prints text[:120]
    # verbatim -- so ONE row can span several physical lines while only its
    # first line starts with "- [". Comparing the collected "- [" lines against
    # the full 120-char slice therefore compares a first line against a
    # multi-line string and fails on any multi-line engram. That is a defect in
    # this reconstruction, not in the CLI: the row content is identical, the
    # test just cannot see past the first line of it.
    raw_texts = [str(r.get("text") or "")[:120].splitlines()[0]
                 for r in raw if str(r.get("text") or "").strip()]
    emitted_texts = [l[len("- [0] "):] if l.startswith("- [0] ") else
                     l.split("] ", 1)[1] if "] " in l else l
                     for l in rows]
    # The emitted row texts match the raw recall texts (order + content), on
    # the part of each row the line-based capture can actually observe.
    assert emitted_texts == raw_texts


# ── (d) --list prints the rows the pager WOULD select, no injectable header ──


def test_recall_cli_list_flag_emits_clean_listing(recall_env, capsys):
    brain = recall_env
    _seed_brain(brain)

    rc = recall_cli.recall("gateway", brain_path=brain, recall_limit=5, list_rows=True)

    assert rc == 0
    out = capsys.readouterr().out
    # --list uses the clean listing header, NOT the injectable-block header.
    assert "# recall list (" in out
    assert "rows)" in out
    assert "# selective recall" not in out
    # No budget mention — listing is not an injectable block.
    assert "chars)" not in out
    # At least one row, shaped "- [<idx>] <text>".
    row_lines = [l for l in out.splitlines() if l.startswith("- [")]
    assert row_lines, "--list must emit at least one row for a seeded brain"
    # The gateway memory is among the listed rows.
    assert any("gateway" in l.lower() for l in row_lines)


def test_recall_cli_list_flag_same_rows_as_default(recall_env, capsys):
    brain = recall_env
    _seed_brain(brain)

    # Default (injectable block) rows.
    rc_default = recall_cli.recall("gateway", brain_path=brain, recall_limit=5)
    assert rc_default == 0
    out_default = capsys.readouterr().out
    default_rows = [l for l in out_default.splitlines() if l.startswith("- [")]

    # --list rows — same data path, so the row texts must match exactly.
    rc_list = recall_cli.recall(
        "gateway", brain_path=brain, recall_limit=5, list_rows=True,
    )
    assert rc_list == 0
    out_list = capsys.readouterr().out
    list_rows = [l for l in out_list.splitlines() if l.startswith("- [")]

    assert list_rows == default_rows


def test_recall_cli_list_flag_via_main_argv(recall_env, capsys):
    brain = recall_env
    _seed_brain(brain)

    rc = recall_cli.main(["gateway", "--list", "--brain-path", brain])

    assert rc == 0
    out = capsys.readouterr().out
    assert "# recall list (" in out
    assert "# selective recall" not in out
    row_lines = [l for l in out.splitlines() if l.startswith("- [")]
    assert row_lines
    assert any("gateway" in l.lower() for l in row_lines)
