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
from nucleus_wedge.store import MemoryConflict, Store, mark_long_lived


def build_server() -> FastMCP:
    # This process serves many sessions and its environment froze at startup,
    # so it must not attribute writes from that environment. Measured
    # 2026-09-20: the running server held a session id 8.6h stale.
    mark_long_lived()
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
    def memory_store_status() -> dict:
        """Whether an engram store is present here, and how full it is.

        Answers the question a zero-result ``recall`` cannot: is this brain
        empty, or is it the wrong brain? Those look identical from the outside
        and the difference is usually a wrong working directory.

        Returns ``{state, rows, path, detail}`` where ``state`` is one of:
          ``ABSENT``    — no engram store at this path. Nothing has ever been
                          written here; a recall will return nothing and that
                          nothing means nothing.
          ``EMPTY``     — a real store exists but holds no records.
          ``POPULATED`` — a store with records in it.
        """
        path = str(store.history_file)
        if not store.exists:
            return {
                "state": "ABSENT",
                "rows": 0,
                "path": path,
                "detail": (
                    "No engram store at this path — absent, not empty. A recall "
                    "here returns nothing because there is nothing to search, "
                    "not because nothing has been learned. Check the working "
                    "directory or set NUCLEUS_BRAIN_PATH."
                ),
            }
        rows = sum(1 for _ in store.rows())
        if rows == 0:
            return {
                "state": "EMPTY",
                "rows": 0,
                "path": path,
                "detail": "Engram store exists but holds no records yet.",
            }
        return {
            "state": "POPULATED",
            "rows": rows,
            "path": path,
            "detail": f"Engram store holds {rows} records.",
        }

    @mcp.tool()
    def memory_head_hash(key: str) -> dict:
        """Hash of the current head of memory ``key`` — the read half of a
        guarded update.

        Take this before editing a memory, then hand it back to ``remember`` as
        ``expected_hash``. If another agent wrote to the same key in between,
        the write is refused instead of silently overwriting their work.

        Returns:
            ``{key, head_hash}``. ``head_hash`` is ``"absent"`` when no live
            record exists — pass that value back to assert you are creating it.
        """
        return {"key": key, "head_hash": store.head_hash(key)}

    @mcp.tool()
    def remember(
        content: str,
        kind: str = "note",
        tags: list[str] | None = None,
        key: str | None = None,
        expected_hash: str | None = None,
        session: str | None = None,
    ) -> dict:
        """Append one memory to .brain/engrams/history.jsonl.

        Args:
            content: The text body to persist.
            kind: Optional taxonomy label (e.g. ``note``, ``decision``, ``pattern``,
                  ``activity``).
            tags: Optional list of short tag strings; encoded into context field.
                  Any ``role:<x>`` tag is canonicalized at write-time per
                  ADR-0033 v3 §B (`_normalize_role`).
            key: Optional explicit key. Reusing an existing key updates that
                 memory; omitting it mints a fresh one as before.
            session: The caller's session id, recorded so a later reading can
                  count how many DISTINCT sessions a pattern appeared in.
                  Supply it per call. This server process may outlive the
                  session that spawned it -- measured at 3 days -- so its own
                  environment cannot be trusted to say which session is
                  writing, and an id taken from there is recorded but not
                  counted.
            expected_hash: Optional compare-and-swap token from
                 ``memory_head_hash``. When supplied, the write is refused with
                 ``conflict: true`` if the head moved since you read it. Requires
                 ``key``. Omit it and the write behaves exactly as it always has.

        Returns:
            ``{key, timestamp, head_hash}`` on success — ``head_hash`` is the new
            head, so a read-modify-write loop needs no second call. On a refused
            write: ``{conflict: True, key, expected, actual, error}``.
        """
        try:
            out = store.append(
                value=content, kind=kind, tags=tags, key=key,
                expected_hash=expected_hash, session=session,
            )
        except MemoryConflict as exc:
            # Returned, not raised: an MCP tool that throws gives the calling
            # agent a stack trace to guess at. This gives it the two hashes and
            # the retry instruction in a shape it can branch on.
            return {
                "conflict": True,
                "key": exc.key,
                "expected": exc.expected,
                "actual": exc.actual,
                "error": str(exc),
            }
        out["head_hash"] = store.head_hash(out["key"])
        return out

    @mcp.tool()
    def memory_proposals_list() -> dict:
        """Pending proposed memory changes — the queue a decision gates.

        The dreaming batch pass proposes memory changes with evidence attached;
        nothing reaches memory until a proposal is accepted. This is the list
        of what is waiting for that decision.

        Returns ``{pending: [...], count}`` where each entry carries
        ``proposal_id``, ``proposed_memory``, ``evidence_summary``, and
        ``evidence_complete`` — the flag ``memory_proposal_accept`` checks. An
        entry with ``evidence_complete: false`` cannot be accepted; weak
        evidence is a reason to reject, not to approve.
        """
        try:
            from mcp_server_nucleus.flywheel import proposals
        except ImportError:
            # nucleus_wedge is packaged to be importable standalone; the
            # proposal gate lives in mcp_server_nucleus.
            return {
                "available": False,
                "pending": [],
                "count": 0,
                "error": "mcp_server_nucleus is not available in this build",
            }
        rows = proposals.pending(store._brain_path)
        return {
            "pending": [
                {
                    "proposal_id": r.get("proposal_id"),
                    "proposed_memory": r.get("proposed_memory"),
                    "evidence_summary": (r.get("evidence") or {}).get("summary", ""),
                    "evidence_complete": bool(
                        (r.get("evidence") or {}).get("complete", False)
                    ),
                    "pattern": r.get("pattern", ""),
                    "proposed_at": r.get("at"),
                }
                for r in rows
            ],
            "count": len(rows),
        }

    @mcp.tool()
    def memory_proposal_accept(proposal_id: str) -> dict:
        """Accept a pending proposal — the ONLY path a proposal has to memory.

        The gate's central refusal lives here: a proposal whose evidence is
        INSUFFICIENT (a capped scan, a count over a set nobody could fully see)
        cannot be accepted. Approving it is how a partial reading becomes an
        organisational fact every later agent reads.

        Args:
            proposal_id: The ``proposal_id`` from ``memory_proposals_list``.

        Returns:
            The decided row fields on success. On any refusal — insufficient
            evidence, already decided, unknown id — ``{refused: True,
            proposal_id, reason}`` so the caller can branch on it instead of
            parsing a stack trace.
        """
        try:
            from mcp_server_nucleus.flywheel import proposals
        except ImportError:
            return {
                "available": False,
                "error": "mcp_server_nucleus is not available in this build",
            }
        try:
            row = proposals.accept(store._brain_path, proposal_id)
        except ValueError as exc:
            # Returned, not raised — same shape as ``remember``'s conflict: the
            # calling agent gets a refusal it can act on, not a traceback.
            return {"refused": True, "proposal_id": proposal_id, "reason": str(exc)}
        return {
            "refused": False,
            "accepted": True,
            "proposal_id": row["proposal_id"],
            "status": row["status"],
            "decided_at": row["decided_at"],
            "decided_by": row["decided_by"],
        }

    @mcp.tool()
    def memory_proposal_reject(proposal_id: str, reason: str) -> dict:
        """Reject a pending proposal. Recorded, never deleted.

        A rejection needs a reason: an unexplained rejection tells the next
        batch pass nothing, so it proposes the same thing again. The record of
        what was rejected — and why — is itself evidence.

        Args:
            proposal_id: The ``proposal_id`` from ``memory_proposals_list``.
            reason: Why the proposal is declined. Required — an empty reason
                    is refused.

        Returns:
            The decided row fields on success, or ``{refused: True,
            proposal_id, reason}`` when the rejection itself is refused
            (empty reason, already decided, unknown id).
        """
        try:
            from mcp_server_nucleus.flywheel import proposals
        except ImportError:
            return {
                "available": False,
                "error": "mcp_server_nucleus is not available in this build",
            }
        try:
            row = proposals.reject(store._brain_path, proposal_id, reason=reason)
        except ValueError as exc:
            return {"refused": True, "proposal_id": proposal_id, "reason": str(exc)}
        return {
            "refused": False,
            "accepted": False,
            "proposal_id": row["proposal_id"],
            "status": row["status"],
            "decided_at": row["decided_at"],
            "decided_by": row["decided_by"],
            "reason": row["reason"],
        }

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
