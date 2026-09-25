"""Stage-1 pager — selective memory recall (relevance x recency x verified-trust).

Three small, self-contained tests:
  (a) ``page()`` ranks an exact-topic memory ABOVE loosely-related ones.
  (b) ``page()`` respects ``budget_chars`` (drops overflow).
  (c) With ``NUCLEUS_AGENT_OS_PAGER`` unset, ``boot.recall_and_inject`` output is
      byte-identical to the baseline (raw recall rows, no pager reselect) — the
      flag-OFF contract.
"""
import os

import pytest

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod
from mcp_server_nucleus.runtime.agent_os.pager import page


# ── (a) exact-topic ranks above loosely-related ──────────────────────────────


def test_page_ranks_exact_topic_above_loosely_related():
    candidates = [
        {"text": "Unrelated: the floor-3 coffee machine is broken.",
         "tags": "topic:office", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
        {"text": "The Nucleus gateway routes model calls through the OS.",
         "tags": "topic:gateway", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
        {"text": "Also unrelated: the office printer is out of toner.",
         "tags": "topic:office", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
    ]
    ranked = page("gateway", candidates, budget_chars=2000)
    assert ranked, "pager must return at least the best candidate"
    assert "gateway" in (ranked[0].get("text") or "").lower()
    assert "coffee" not in (ranked[0].get("text") or "").lower()
    assert "printer" not in (ranked[0].get("text") or "").lower()


# ── (b) budget_chars drops overflow ──────────────────────────────────────────


def test_page_respects_budget_chars_drops_overflow():
    candidates = [
        {"text": "The Nucleus gateway routes model calls through the OS.",
         "tags": "topic:gateway", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
        {"text": "Unrelated: the floor-3 coffee machine is broken.",
         "tags": "topic:office", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
        {"text": "Also unrelated: the office printer is out of toner.",
         "tags": "topic:office", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
    ]
    # Generous budget: all three fit (order is best-first, but all returned).
    full = page("gateway", candidates, budget_chars=4000)
    assert len(full) == 3
    # Tight budget: the best candidate still lands, the overflow is evicted.
    tight = page("gateway", candidates, budget_chars=60)
    assert 1 <= len(tight) < len(candidates)
    assert "gateway" in (tight[0].get("text") or "").lower()


# ── (c) flag-OFF byte-identical to baseline ──────────────────────────────────


@pytest.fixture()
def cell_env(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    # PAGER flag explicitly UNSET — the byte-identical-OFF contract.
    monkeypatch.delenv(boot_mod.PAGER_FLAG, raising=False)
    return str(brain)


def test_pager_flag_off_recall_and_inject_byte_identical_to_baseline(cell_env, monkeypatch):
    """With ``NUCLEUS_AGENT_OS_PAGER`` unset, ``recall_and_inject`` returns the
    raw ``_do_recall_query`` rows unchanged and builds the injected block the
    same way — the pager module is never imported. Guards the flag-OFF contract.
    """
    from nucleus_wedge.recall_cmd import _do_recall_query
    from nucleus_wedge.store import Store

    brain = cell_env
    Store(brain).append(
        value="The Nucleus gateway routes model calls through the OS.",
        kind="note", tags=["topic:gateway"], source_agent="prior-session",
    )

    # Sanity: the pager flag really is unset.
    assert os.environ.get(boot_mod.PAGER_FLAG) in (None, "")

    injected, rows = boot_mod.recall_and_inject("gateway", brain_path=brain)

    # Baseline: the exact same recall query, called directly (no pager).
    baseline_rows = _do_recall_query(
        query="gateway", limit=5, kind=None, tags=None,
        since=None, source_filter=None, brain_path_arg=brain,
    )
    # The injected block boot would build from the baseline rows.
    baseline_recalled = [r.get("text", "") for r in baseline_rows if r.get("text")]
    if baseline_recalled:
        baseline_injected = (
            "[NUCLEUS MEMORY — recalled before you think]\n"
            + "\n".join(f"- {t}" for t in baseline_recalled)
        )
    else:
        baseline_injected = "[NUCLEUS MEMORY — no prior memory matched this task]"

    assert rows == baseline_rows
    assert injected == baseline_injected
