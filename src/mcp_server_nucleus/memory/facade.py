"""MemoryFacade — the one unified capture/recall/curate surface (Move 2 batch 1).

Target design (``scratchpad/move2_manifest.md`` Part B): every memory caller —
``nucleus_wedge`` remember/recall, ``nucleus_engrams`` write/query/search, the
``capabilities.brain_store/search_memory`` ops, and the eidetic daemon's fsnotify
captures — eventually delegates to this facade's three verbs:

    capture(surface, payload, *, kind, tags, meta, ts, key) -> {id, key, ts}
    recall(query, *, kind, tags, since, surface, limit, mode)  -> [ranked hits]
    curate(target, action)                                     -> {ok}

BATCH 1 IS SCAFFOLD ONLY. This module adds the importable API and (when enabled)
wires it to the SoR store — but **no existing caller is repointed here yet**, so
adding it changes zero production behavior.

Flag gating (``NUCLEUS_MEMORY_SOR``, default OFF):
  - OFF (default): the facade is a callable no-op scaffold. ``capture`` persists
    nothing and returns ``{"id": None, "key": key, "ts": ts, "persisted": False}``;
    ``recall`` returns ``[]``; ``curate`` returns ``{"ok": False, ...}``. No SoR
    file is created and no existing store is touched — a true no-op.
  - ON (``NUCLEUS_MEMORY_SOR=1``): the facade lazily constructs a ``SorStore`` at
    ``.brain/engrams.db`` and delegates the three verbs to it. The SoR is created
    but not yet authoritative (later batches route real traffic to it).

The facade never imports the heavy ``mcp_server_nucleus`` startup path and never
calls ``_ensure_initialized`` — importing it must not disturb the Move 1
lazy-init contract (a bare ``import mcp_server_nucleus`` stays residue-free).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from .sor import SorStore

# Env values (case-insensitive) that turn the SoR path on.
_TRUTHY = frozenset({"1", "true", "yes", "on"})

MEMORY_SOR_FLAG = "NUCLEUS_MEMORY_SOR"


def sor_flag_enabled() -> bool:
    """True iff ``NUCLEUS_MEMORY_SOR`` is set to a truthy value (default False)."""
    return os.environ.get(MEMORY_SOR_FLAG, "").strip().lower() in _TRUTHY


def _resolve_enabled(enabled: Optional[bool]) -> bool:
    if enabled is not None:
        return bool(enabled)
    return sor_flag_enabled()


class MemoryFacade:
    """Unified capture/recall/curate surface over the SoR (flag-gated)."""

    def __init__(
        self,
        brain_path: Union[None, str, Path] = None,
        *,
        enabled: Optional[bool] = None,
        db_path: Union[None, str, Path] = None,
    ):
        """
        Args:
            brain_path: explicit ``.brain`` dir; default resolves via the wedge
                Store path rules (only consulted when enabled + no ``db_path``).
            enabled: force the SoR path on/off, overriding ``NUCLEUS_MEMORY_SOR``.
                ``None`` (default) reads the env flag.
            db_path: explicit SoR db file, bypassing brain-path resolution
                (used by tests / isolated round-trips).
        """
        self._brain_path = brain_path
        self._explicit_db_path = db_path
        self._enabled = _resolve_enabled(enabled)
        self._sor: Optional[SorStore] = None  # lazy — never built when disabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _resolve_db_path(self) -> Path:
        if self._explicit_db_path is not None:
            return Path(self._explicit_db_path)
        # Import lazily so the facade stays decoupled from nucleus_wedge and
        # ultra-light to import (Store is only needed to resolve the default path).
        from nucleus_wedge.store import Store

        return Store.brain_path(self._brain_path) / "engrams.db"

    def _store(self) -> Optional[SorStore]:
        if not self._enabled:
            return None
        if self._sor is None:
            self._sor = SorStore(self._resolve_db_path())
        return self._sor

    # -- the three verbs ----------------------------------------------------
    def capture(
        self,
        surface: str,
        payload: str,
        *,
        kind: str = "note",
        tags: Union[None, str, Iterable[str]] = None,
        meta: Union[None, str, dict] = None,
        ts: Optional[str] = None,
        key: Optional[str] = None,
        vector_sink: Any = None,
    ) -> dict:
        """Capture one engram. Flag-OFF: no-op scaffold (persists nothing).

        ``vector_sink`` (Move 2 batch 5): an optional best-effort index sink —
        after the authoritative SoR insert, the facade calls
        ``vector_sink.index(id, text, metadata=meta)`` so a derived vector index
        (e.g. ``runtime.vector_store.VectorStore``) can be kept warm for the
        optional recall re-rank. Purely additive: a sink failure never breaks the
        capture (the SoR already holds the durable record), and ``None`` (default)
        leaves capture untouched.
        """
        store = self._store()
        if store is None:
            return {"id": None, "key": key, "ts": ts, "persisted": False}
        result = store.insert(
            surface, payload, kind=kind, tags=tags, meta=meta, ts=ts, key=key
        )
        result["persisted"] = True
        if vector_sink is not None:
            try:
                vector_sink.index(result["id"], payload, metadata=meta)
            except Exception:  # noqa: BLE001 — index sink is best-effort/additive
                pass
        return result

    def recall(
        self,
        query: str = "",
        *,
        kind: Optional[str] = None,
        tags: Optional[str] = None,
        since: Union[None, str] = None,
        surface: Optional[str] = None,
        limit: int = 10,
        mode: str = "hybrid",
        include_archived: bool = False,
    ) -> list:
        """Ranked recall. Flag-OFF: no-op scaffold (returns ``[]``).

        ``mode`` is accepted for API stability ("hybrid" = FTS5 lexical, with a
        vector re-rank stage added in a later batch); batch 1 always uses the
        SoR's FTS5 path.
        """
        store = self._store()
        if store is None:
            return []
        return store.search(
            query,
            kind=kind,
            tags=tags,
            since=since,
            surface=surface,
            limit=limit,
            include_archived=include_archived,
        )

    def curate(self, target: Union[int, str], action: str) -> dict:
        """Non-destructive curation overlay. Flag-OFF: no-op scaffold."""
        store = self._store()
        if store is None:
            return {"ok": False, "persisted": False, "reason": f"{MEMORY_SOR_FLAG} disabled"}
        return store.curate(target, action)
