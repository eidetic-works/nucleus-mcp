"""Unified memory surface — MemoryFacade + flag-gated SoR store (Move 2).

Public API (batch 1, scaffold only — no existing caller is repointed here yet):

    from mcp_server_nucleus.memory import MemoryFacade
    mf = MemoryFacade()                 # honours NUCLEUS_MEMORY_SOR (default off)
    mf.capture(surface, payload, ...)   # -> {id, key, ts, persisted}
    mf.recall(query, ...)               # -> [ranked hits]
    mf.curate(id_or_key, action)        # -> {ok, ...}

See ``scratchpad/move2_manifest.md`` for the full design. Importing this package
must not trigger the heavy ``mcp_server_nucleus`` startup init (Move 1 contract).
"""
from .facade import MEMORY_SOR_FLAG, MemoryFacade, sor_flag_enabled
from .sor import CURATION_ACTIONS, SorStore

__all__ = [
    "MemoryFacade",
    "SorStore",
    "sor_flag_enabled",
    "MEMORY_SOR_FLAG",
    "CURATION_ACTIONS",
]
