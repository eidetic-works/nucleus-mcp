"""Role-string normalization per ADR-0033 v3 §B + role_taxonomy_refactor_agy_v3.md.

Maps empirically-observed drift in `from_role` values (past-7d relays) to a
canonical set used for `role:<x>` activity engram tags. Without this helper,
doublet drift (`cc_gq` vs `gq`, `antigravity` vs `agy`) would split a single
agent's activity engrams across two `role:<x>` tags — recall would silently
return half the truth (cc-peer v2 finding #6, correctness-blocking).

Canonical roles (per role_taxonomy_refactor_agy_v3.md §1):
    Functional: coordinator, worker, reviewer
    Vendor-specific: gq, operator_assistant, agy, devin, codex
    Fallback: unknown

Legacy role names (main, peer, tb) are accepted as aliases and mapped to
the new functional vocabulary:
    main → coordinator (plan-bound coordinator)
    peer → worker (free-roaming integrator)
    tb → reviewer (third-brother verify role)

Apply at every write of `role:<x>` tag (called from `Store.append` via
`memories.py`).
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical → known aliases. Lookup happens via the inverted alias→canonical map
# so we can normalize observed drift in a single LOC at write-time.
_CANONICAL_ALIASES: dict[str, list[str]] = {
    # Functional roles (role_taxonomy_refactor_agy_v3.md §1)
    "coordinator": ["coordinator", "main", "cc_main", "claude_code_main", "cc-main", "primary"],
    "worker": ["worker", "peer", "cc_peer", "cc-peer", "secondary"],
    "reviewer": ["reviewer", "tb", "cc_tb", "cc-tb"],
    # Vendor-specific roles (not function roles, kept as-is)
    "gq": ["gq", "cc_gq", "cc-gq", "gentlequest"],
    "operator_assistant": ["operator_assistant", "op_assistant", "op-assistant"],
    "agy": ["agy", "antigravity", "agy-cli"],
    "devin": ["devin"],
    "codex": ["codex"],
}

# Inverted lookup table: alias → canonical
_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias.lower(): canonical
    for canonical, aliases in _CANONICAL_ALIASES.items()
    for alias in aliases
}


def _normalize_role(s: Optional[str]) -> str:
    """Map any observed role string to its canonical form.

    - Known canonical or alias → canonical (e.g., `cc_main` → `coordinator`)
    - Empty / None / unrecognized → `unknown` with a logger.warning so drift
      is visible (do not silent-bucket).

    Args:
        s: Role string from NUCLEUS_SESSION_ROLE env, CC_SESSION_ROLE env,
           relay envelope, etc.

    Returns:
        Canonical role string from the set defined in `_CANONICAL_ALIASES`,
        or `unknown` for unrecognized inputs.
    """
    if not s:
        logger.warning("role normalize: empty/None role -> 'unknown'")
        return "unknown"
    key = s.strip().lower()
    if not key:
        logger.warning("role normalize: whitespace-only role -> 'unknown'")
        return "unknown"
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]
    logger.warning("role normalize: unrecognized role %r -> 'unknown'", s)
    return "unknown"


def canonical_roles() -> list[str]:
    """Return the list of canonical roles (for audit / health reporting)."""
    return list(_CANONICAL_ALIASES.keys()) + ["unknown"]
