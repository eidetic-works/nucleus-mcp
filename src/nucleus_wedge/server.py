"""FastMCP server exposing two tools — ``remember`` and ``recall`` — over ``.brain/engrams/history.jsonl``.

Hard-capped at 2 tools through cycle 1 (ADR-0006 required to add a third).
"""
from __future__ import annotations

import sys

from fastmcp import FastMCP

from nucleus_wedge import __version__
from nucleus_wedge import bm25
from nucleus_wedge.seed import ensure_seeds
from nucleus_wedge.store import Store


def build_server() -> FastMCP:
    mcp = FastMCP(name=f"nucleus-wedge-{__version__}")
    store = Store()
    ensure_seeds(store)

    @mcp.tool()
    def remember(content: str, kind: str = "note", tags: list[str] | None = None) -> dict:
        """Append one memory to .brain/engrams/history.jsonl.

        Args:
            content: The text body to persist.
            kind: Optional taxonomy label (e.g. ``note``, ``decision``, ``pattern``).
            tags: Optional list of short tag strings; encoded into context field.

        Returns:
            ``{key, timestamp}`` of the appended record.
        """
        return store.append(value=content, kind=kind, tags=tags)

    @mcp.tool()
    def recall(query: str, limit: int = 5, kind: str | None = None, since: str | None = None) -> list[dict]:
        """Rank history rows by BM25 over content; return top-k.

        Args:
            query: Natural-language query string.
            limit: Max results (default 5).
            kind: Optional exact-prefix filter on context/kind.
            since: Optional ISO-8601 lower bound on timestamp (lex comparison).

        Returns:
            Ranked list of ``{content, kind, timestamp, key, score}``.
        """
        return bm25.search(store, query=query, limit=limit, kind=kind, since=since)

    return mcp


def main() -> None:
    try:
        server = build_server()
        server.run()
    except KeyboardInterrupt:
        print("nucleus-wedge: interrupted", file=sys.stderr)


if __name__ == "__main__":
    main()
