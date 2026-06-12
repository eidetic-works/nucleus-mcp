"""FastMCP server exposing nucleus-wedge tools.

Original surface: ``remember`` + ``recall`` over ``.brain/engrams/history.jsonl``.

ADR-0033 v3 additions:
  - ``recall`` accepts new ``kind`` / ``tags`` / ``since`` structured filters
    while preserving full backward compat with ``recall(query='X')`` calls.
  - ``recall_activity(role, domain, since, limit)`` thin wrapper over the
    structured query path.
  - ``recall_activity_health(role)`` audit tool: fresh / stale / silent-fail.
"""
from __future__ import annotations

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
    ) -> list[dict]:
        """Recall history rows. Backward-compat dual surface (ADR-0033 v3 §A).

        - If only ``query`` is provided (legacy call), BM25 over history is used
          for ranking — preserves the pre-Phase-0.5 behavior.
        - If any structured filter (``kind`` / ``tags`` / ``since``) is provided,
          the SQLite projection is queried with composed AND clauses, and
          ``query`` becomes optional (empty allowed).

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

        Returns:
            Ranked list of result dicts.
        """
        has_structured = bool(kind or tags or since)
        if has_structured:
            from nucleus_wedge.recall_cmd import _do_recall_query
            from nucleus_wedge.memories import _parse_since
            since_norm = _parse_since(since) if since else None
            return _do_recall_query(
                query=query,
                limit=limit,
                kind=kind,
                tags=tags,
                since=since_norm,
                source_filter=None,
                brain_path_arg=None,
            )
        # Legacy BM25 path — ``query`` required.
        return bm25.search(store, query=query, limit=limit, kind=kind, since=since)

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
            status ∈ {``fresh`` (<24h), ``stale`` (24-168h), ``silent-fail`` (>168h or never)}.
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
