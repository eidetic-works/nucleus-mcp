"""FastMCP server exposing nucleus-wedge tools.

Original surface: ``remember`` + ``recall`` over ``.brain/engrams/history.jsonl``.

ADR-0033 v3 additions:
  - ``recall`` accepts new ``kind`` / ``tags`` / ``since`` structured filters
    while preserving full backward compat with ``recall(query='X')`` calls.
  - ``recall_activity(role, domain, since, limit)`` thin wrapper over the
    structured query path.
  - ``recall_activity_health(role)`` audit tool: fresh / stale / silent-fail
    / never-ran / unparseable.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from fastmcp import FastMCP

from nucleus_wedge import __version__
from nucleus_wedge import bm25
from nucleus_wedge.seed import ensure_seeds
from nucleus_wedge.store import Store


def build_server() -> FastMCP:
    mcp = FastMCP(name=f"nucleus-wedge-{__version__}")
    try:
        from mcp_server_nucleus.runtime.tool_instrumentation import install_instrumentation
        install_instrumentation(mcp)
    except ImportError:
        # nucleus_wedge runs as a stand-alone package in some deployments;
        # instrumentation is best-effort and never blocks server startup.
        pass
    store = Store()
    ensure_seeds(store)

    @mcp.tool()
    def remember(content: str, kind: str = "note", tags: list[str] | None = None) -> dict:
        """Append one memory to .brain/engrams/history.jsonl.

        Args:
            content: The text body to persist.
            kind: Optional taxonomy label (e.g. ``note``, ``decision``, ``pattern``,
                  ``activity``).
            tags: Optional list of short tag strings; encoded into context field.
                  Any ``role:<x>`` tag is canonicalized at write-time per
                  ADR-0033 v3 §B (`_normalize_role`).

        Returns:
            ``{key, timestamp}`` of the appended record.
        """
        return store.append(value=content, kind=kind, tags=tags)

    @mcp.tool()
    def recall(
        query: str = "",
        limit: int = 5,
        kind: Optional[str] = None,
        tags: Optional[list[str]] = None,
        since: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> list[dict]:
        """Recall memories, ranked by BM25, optionally narrowed by filters.

        All calls read ONE corpus: the ``memories.db`` projection over
        ``history.jsonl`` (deduped by content hash, machine chatter excluded
        from the index but never from the store). Structured filters
        (``kind`` / ``tags`` / ``since``) narrow that same corpus rather than
        selecting a different one, so passing a filter can only ever reduce the
        result set — it cannot change which memories were searchable.

        Until fw-1786153512 this was two corpora behind one name: filtered calls
        hit the projection, unfiltered calls scanned raw history. Set
        ``NUCLEUS_WEDGE_LEGACY_RECALL=1`` to restore the old raw-history scan.

        Args:
            query: Natural-language query string (optional when structured filters
                   are present).
            limit: Max results (default 5).
            kind: Optional exact-match filter on engram ``kind`` column
                  (e.g. ``activity``).
            tags: Optional list of tag substrings to match (e.g.
                  ``['role:main', 'domain:tb-endpoint']``).
            since: Optional ISO-8601 lower bound on timestamp, or relative window
                   ``Nd``/``Nh``/``Nm``.
            repo: Optional origin-repo filter, e.g. ``"ai-mvp-backend"``. Rows
                  whose origin was never recorded (everything written before
                  origin tracking) are INCLUDED — unknown origin means unknown,
                  not "other repo", and excluding it would hide the historical
                  corpus behind a filter that looks precise.

        Returns:
            Ranked list of result dicts.
        """
        # ONE corpus, one ranking, whether or not a filter was passed
        # (fw-1786153512 defect 2). These were two different corpora behind one
        # tool name: the filtered branch queried the memories.db projection
        # (5,351 rows — deduped, chatter excluded) while the unfiltered branch
        # scanned raw history.jsonl (19,805 rows). Same question, different
        # answer, decided by whether you happened to pass `since`.
        #
        # It mattered most in the direction nobody would guess: the UNFILTERED
        # call is the common one, and the one nucleus_first_pretool.sh forces
        # agents into, so all of that traffic was hitting the noisy corpus while
        # only filtered calls got the curated one. Unifying on the projection
        # hands dedup and chatter-exclusion to the default path.
        #
        # NUCLEUS_WEDGE_LEGACY_RECALL=1 restores the raw-history scan, so this
        # is reversible without a revert if the projection ever misbehaves.
        from nucleus_wedge.recall_cmd import _do_recall_query
        from nucleus_wedge.memories import _parse_since

        if os.environ.get("NUCLEUS_WEDGE_LEGACY_RECALL", "").strip() in {"1", "true", "yes"}:
            return bm25.search(store, query=query, limit=limit, kind=kind, since=since)

        since_norm = _parse_since(since) if since else None
        return _do_recall_query(
            query=query,
            limit=limit,
            kind=kind,
            tags=tags,
            since=since_norm,
            source_filter=None,
            brain_path_arg=None,
            repo=repo,
        )

    @mcp.tool()
    def recall_activity(
        role: str,
        domain: Optional[str] = None,
        since: str = "30d",
        limit: int = 10,
    ) -> dict:
        """Per-agent activity recall (ADR-0033 v3 §C).

        Thin wrapper over the structured recall path. Normalizes the role,
        composes ``tags=['role:<canonical>', 'domain:<d>']``, calls with
        ``kind='activity'``.

        Args:
            role: Agent role string (any alias accepted; canonicalized internally).
            domain: Optional ``domain:<freeform>`` filter (per ADR-0033 v3 §B,
                    free-form on purpose pre-registry).
            since: Window (default ``30d``; accepts ``Nd``/``Nh``/``Nm`` or ISO).
            limit: Max results (default 10).

        Returns:
            ``{role, domain, since, results: [...]}``
        """
        from nucleus_wedge.memories import recall_activity as _recall_activity
        return _recall_activity(role=role, domain=domain, since=since, limit=limit)

    @mcp.tool()
    def recall_activity_health(role: Optional[str] = None) -> dict:
        """Per-role digest-freshness audit (ADR-0033 v3 §D).

        Args:
            role: Optional single-role check; defaults to all canonical roles.

        Returns:
            ``{roles: [{role, last_digest_at, age_hours, status}]}``
            status ∈ {``fresh`` (<24h), ``stale`` (24-168h), ``silent-fail``
            (wrote, then quiet >168h), ``never-ran`` (no digest ever — not a
            fault), ``unparseable`` (timestamp unreadable — a writer bug)}.
        """
        from nucleus_wedge.memories import recall_activity_health as _health
        return _health(role=role)

    return mcp


def main() -> None:
    try:
        server = build_server()
        server.run()
    except KeyboardInterrupt:
        print("nucleus-wedge: interrupted", file=sys.stderr)


if __name__ == "__main__":
    main()
