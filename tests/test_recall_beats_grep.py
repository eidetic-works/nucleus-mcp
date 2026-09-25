"""Move 2 batch 4 acceptance test — "recall beats grepping your history."

The MOVE-2 product gate (``scratchpad/move2_manifest.md`` Part C, Batch 4): a
corpus where the unified SoR / FTS5 recall returns a target document that the
ripgrep memory path (``runtime/memory.py::_search_memory``, lineage A5) *misses*.

Why recall wins, structurally:
  - ``_search_memory`` runs ``rg -i -- "<query>"`` — a literal contiguous regex,
    so a multi-word query only matches lines where those words appear adjacent in
    that exact order.
  - FTS5 (``engrams_fts MATCH``) tokenizes and combines terms with an implicit
    AND — so it matches a document that contains all the query terms even when
    they are re-ordered or separated. (Verified empirically: ``MATCH 'rollback
    deployment procedure'`` returns a doc that reads "deployment rollback
    procedure"; ``rg`` does not.)

The corpus therefore has a TARGET doc whose terms are present-but-reordered
(FTS5 finds it, ripgrep misses it) and a DECOY doc with the contiguous phrase
(both find it) — so recall's result set strictly contains the doc grep missed.

Second test pins the historical-completeness safeguard (UNION-READ): with the
flag on, ``_do_recall_query`` returns BOTH a pre-shim record (legacy
``memories.db`` only) and a post-shim record (SoR only) — nothing is missed, so
flag-ON is never worse than flag-OFF.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server_nucleus.memory.facade import MEMORY_SOR_FLAG, MemoryFacade
from mcp_server_nucleus.runtime.memory import _search_memory
from nucleus_wedge.recall_cmd import _do_recall_query
from nucleus_wedge.store import Store

QUERY = "rollback deployment procedure"

# Terms present but RE-ORDERED vs QUERY ("deployment rollback procedure"): FTS5
# matches (implicit AND over tokens); ripgrep's literal contiguous regex misses.
TARGET = (
    "The deployment rollback procedure must run within the first hour "
    "of a bad release"
)
# Contiguous phrase "rollback deployment procedure": BOTH grep and FTS5 match it.
DECOY = "Standard rollback deployment procedure documented for reference"
NOISE = [
    "Morning coffee routines and standup notes for the team",
    "Firestore KNN vector index rebuild timing benchmark",
]

CORPUS = [TARGET, DECOY, *NOISE]


@pytest.fixture
def brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp ``.brain`` holding the SAME corpus in both stores:

    - ripgrep corpus: ``<brain>/memory/learnings.md`` (one doc per line), plus
      ``get_brain_path`` pointed here via ``NUCLEUS_BRAIN_PATH``.
    - SoR corpus: each doc ``capture()``-d into ``<brain>/engrams.db``.
    """
    b = tmp_path / ".brain"
    (b / "memory").mkdir(parents=True)
    (b / "memory" / "learnings.md").write_text(
        "\n".join(CORPUS) + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")

    facade = MemoryFacade(brain_path=b, enabled=True)
    for doc in CORPUS:
        facade.capture(surface="claude_code", payload=doc, kind="note")
    return b


def test_recall_returns_the_target_ripgrep_misses(brain: Path) -> None:
    """The product gate: SoR/FTS5 recall returns the TARGET that ripgrep misses."""
    # --- grep path (lineage A5) ------------------------------------------------
    # Move 2 batch 5 repointed the flag-ON default of ``_search_memory`` to the
    # unified SoR hybrid; the ripgrep scan is RETAINED as the explicit
    # ``mode="grep"`` escape hatch, which is exactly the grep baseline this gate
    # needs. (Non-weakening: the assertions below are unchanged.)
    grep = _search_memory(QUERY, mode="grep")
    assert "error" not in grep, grep
    grep_blob = "\n".join(grep["results"])

    # ripgrep matches only the contiguous DECOY; it MISSES the reordered TARGET.
    assert DECOY in grep_blob, "sanity: ripgrep should match the contiguous decoy"
    assert TARGET not in grep_blob, (
        "ripgrep must MISS the reordered target — that is the gap recall closes"
    )

    # --- recall path (unified SoR / FTS5) -------------------------------------
    hits = MemoryFacade(brain_path=brain, enabled=True).recall(QUERY, limit=5)
    recall_texts = [h["text"] for h in hits]

    # recall FINDS the target grep missed, plus the decoy; noise is excluded.
    assert any(TARGET in t for t in recall_texts), (
        f"recall must surface the target grep missed; got {recall_texts!r}"
    )
    assert any(DECOY in t for t in recall_texts)
    for noise in NOISE:
        assert not any(noise in t for t in recall_texts), (
            "FTS5 implicit-AND must exclude docs missing a query term"
        )

    # The decisive product claim: recall's result set strictly contains a
    # relevant doc that grep did not return within its own results.
    assert any(TARGET in t for t in recall_texts) and TARGET not in grep_blob


def test_recall_ranks_relevant_above_noise(brain: Path) -> None:
    """bm25/FTS5 ranking preserved on a multi-doc corpus: the two term-matching
    docs rank strictly above the noise (which does not match at all)."""
    hits = MemoryFacade(brain_path=brain, enabled=True).recall(QUERY, limit=10)
    texts = [h["text"] for h in hits]
    # Only the two relevant docs come back; ordering is BM25 over the tokens.
    assert len(hits) == 2
    assert {TARGET, DECOY} == set(texts)
    # Scores are populated and monotonically non-increasing (best-first).
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_union_read_misses_nothing_pre_or_post_shim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Historical-completeness safeguard: flag-ON ``_do_recall_query`` returns
    BOTH a pre-shim record (legacy ``memories.db`` only) AND a post-shim record
    (SoR only). The union means flag-ON never drops what flag-OFF would find.
    """
    b = tmp_path / ".brain"
    b.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)

    pre = "pre shim widget alpha decision"
    post = "post shim widget beta decision"

    # PRE-SHIM: write to the legacy store ONLY (flag OFF → no SoR mirror), so it
    # lives in history.jsonl → memories.db but never in the SoR.
    monkeypatch.delenv(MEMORY_SOR_FLAG, raising=False)
    Store(brain_path=b).append(pre, kind="note")
    assert not (b / "engrams.db").exists(), "pre-shim write must not touch the SoR"

    # POST-SHIM: capture() straight into the SoR ONLY (never history.jsonl), so
    # the legacy memories.db projection cannot see it.
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    MemoryFacade(brain_path=b, enabled=True).capture(
        surface="claude_code", payload=post, kind="note"
    )

    # Flag-ON union recall for the common term → must return BOTH records.
    rows = _do_recall_query(
        query="widget",
        limit=10,
        kind=None,
        tags=None,
        since=None,
        source_filter=None,
        brain_path_arg=str(b),
    )
    texts = [r["text"] for r in rows]
    assert any(pre in t for t in texts), f"pre-shim (legacy-only) missed: {texts!r}"
    assert any(post in t for t in texts), f"post-shim (SoR-only) missed: {texts!r}"
