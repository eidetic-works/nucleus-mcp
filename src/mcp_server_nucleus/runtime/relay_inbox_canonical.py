"""Canonical relay inbox-dir map per feedback_relay_inbox_dir_canonical_v1.md.

Closes 3-week-old gap behind `feedback_relay_arrival_invisible_midsession` HARD RULE:
    cc-tb (and similar bare-name canonical agents) was subscribing to the wrong
    inbox dir because _resolve_inbox_dir only handled 'main'/'peer' remapping.

Per cc-peer's 9th scout finding (2026-06-04 ~16:35Z amendment):
    - cc-tb canonical inbox is `cc_tb/` (bare name), NOT `claude_code_tb/` (legacy)
    - agy canonical inbox is `antigravity/` (bare name)
    - main/peer/op-assistant canonical = `claude_code_<role>` (full)

This module is the SINGLE SOURCE OF TRUTH for role→inbox mapping.
"""
from __future__ import annotations


# Canonical role → inbox-dir mapping (per feedback_relay_inbox_dir_canonical_v1.md)
# Updated 2026-06-04 ~16:35Z to mark cc_tb/ as canonical bare-name for cc-tb role.
#
# Intentional omissions (verified 2026-06-05 per cc-peer hole-poke verdict F2):
#   - cc_voice: single stale relay 2026-05-31; NOT a real fleet agent.
#     Adding entry would imply legitimacy that doesn't exist.
#   - claude_code/coordinator/drafts/reviewer/sonnet_*: scratch / sub-agent /
#     legacy variants; not real fleet members.
#   - test_script: test scaffold dir; not a fleet agent.
# Future cleanup PR can audit + consolidate these if any become real surfaces.
CANONICAL_ROLE_TO_INBOX_DIR: dict[str, str] = {
    # ── Functional role aliases (role_taxonomy_refactor_agy_v3.md Phase 1) ──
    # These map the generic vocabulary to existing bucket dirs.
    # The role+provider composite key is handled by resolve_canonical_inbox_name()
    # which checks for "<role>+<provider>" before falling back to bare role.
    "coordinator": "claude_code_main",
    "worker": "claude_code_peer",  # default; provider-specific override below
    "reviewer": "cc_tb",  # maps to existing cc_tb bare-name dir

    # ── main + peer (legacy, kept for backward compat) ──
    "main": "claude_code_main",
    "peer": "claude_code_peer",
    "claude_code_main": "claude_code_main",
    "claude_code_peer": "claude_code_peer",

    # cc-tb canonical = `cc_tb/` bare-name (2026-06-04 ~16:35Z amendment empirical).
    # Legacy `claude_code_tb/` deprecated (stale since 2026-05-31).
    "tb": "cc_tb",
    "cc_tb": "cc_tb",
    "claude_code_tb": "cc_tb",  # alias legacy → canonical for write-compat

    # op-assistant canonical full-name
    "operator_assistant": "claude_code_operator_assistant",
    "op_assistant": "claude_code_operator_assistant",
    # Short alias for phone/Dispatch ergonomics (Task #62 follow-on F2)
    "ops": "claude_code_operator_assistant",
    "claude_code_operator_assistant": "claude_code_operator_assistant",

    # agy canonical bare-name (historical antigravity convention)
    "antigravity": "antigravity",
    "agy": "antigravity",

    # devin canonical bare-name (cross-vendor GLM surface; NUCLEUS_CROSS_VENDOR).
    # Kept bare-name to mirror the `antigravity` convention rather than the
    # `claude_code_<role>` prefix, since it is a non-Claude vendor surface.
    "devin": "devin",
    "glm": "devin",

    # Antigravity IDE per-purpose sessions (operator roster expansion 2026-06-06).
    # Pattern: bare-name antigravity_<purpose>; mirrors the bare-name convention
    # used by `antigravity` itself rather than the `claude_code_<role>` prefix.
    "antigravity_gq": "antigravity_gq",
    "agy_gq": "antigravity_gq",
    "antigravity_voice": "antigravity_voice",
    "agy_voice": "antigravity_voice",

    # cc_gq canonical full-name (33 files at claude_code_cc_gq; merge candidate)
    "cc_gq": "claude_code_cc_gq",
    "claude_code_cc_gq": "claude_code_cc_gq",
    "gq": "claude_code_gq",
    "claude_code_gq": "claude_code_gq",

    # ultraplan + windsurf + main-debug + test_hold
    "ultraplan": "claude_code_ultraplan",
    "claude_code_ultraplan": "claude_code_ultraplan",
    "windsurf": "claude_code_windsurf",
    "claude_code_windsurf": "claude_code_windsurf",
    "main_debug": "claude_code_main-debug",
    # Lookup keys must be resolver-normalized ('-' -> '_'); a hyphenated key
    # is unreachable. Value keeps the on-disk hyphenated dir name.
    "claude_code_main_debug": "claude_code_main-debug",
    "test_hold": "claude_code_test_hold",
    "claude_code_test_hold": "claude_code_test_hold",

    # board = shared multi-agent broadcast
    "board": "board",

    # ── Provider-specific composite keys (role+provider → bucket) ──
    # Per role_taxonomy_refactor_agy_v3.md Phase 1: vendor-aware alias layer.
    # These override the bare role mapping when a provider is known.
    "coordinator+anthropic": "claude_code_main",
    "worker+anthropic": "claude_code_peer",
    "worker+gemini": "antigravity",
    "worker+glm": "devin",
    "reviewer+anthropic": "cc_tb",
}


# Deprecated dir → canonical replacement (write-side coercion for cleanup)
#
# Per cc-peer hole-poke verdict 2026-06-05 F2 (SHOULD-FIX):
#   This map is currently PASSIVE METADATA — NOT consumed by _resolve_inbox_dir.
#   Wiring to read-side coercion deferred per v0.1 compat-preserving:
#     - writers can still target legacy dirs (no breaking change to existing callers)
#     - subscribers using canonical map miss legacy-targeted relays silently
#   Future cleanup PR can wire this into _resolve_inbox_dir to auto-redirect
#   deprecated-dir reads to canonical (e.g., subscribing role='op_assistant'
#   would resolve to 'claude_code_operator_assistant' inbox automatically).
DEPRECATED_DIR_TO_CANONICAL: dict[str, str] = {
    "op_assistant": "claude_code_operator_assistant",
    "operator_assistant": "claude_code_operator_assistant",
    "main": "claude_code_main",
    "windsurf": "claude_code_windsurf",
    "cowork": "claude_code_main",  # historical; route to main
    "claude_code_tb": "cc_tb",  # legacy → canonical bare-name
}


def resolve_canonical_inbox_name(role: str, provider: str | None = None) -> str:
    """Map an agent role to its canonical inbox dir NAME (not full path).

    Returns the dir NAME (e.g., 'cc_tb', 'claude_code_main') for downstream
    Path construction. Unknown roles pass through unchanged.

    Per role_taxonomy_refactor_agy_v3.md Phase 1: if a provider is supplied,
    checks the composite key "<role>+<provider>" first (vendor-aware alias
    layer), then falls back to the bare role mapping.

    Examples:
        resolve_canonical_inbox_name('tb')                -> 'cc_tb'
        resolve_canonical_inbox_name('cc_tb')             -> 'cc_tb'
        resolve_canonical_inbox_name('claude_code_tb')    -> 'cc_tb' (legacy alias)
        resolve_canonical_inbox_name('main')              -> 'claude_code_main'
        resolve_canonical_inbox_name('antigravity')       -> 'antigravity'
        resolve_canonical_inbox_name('worker', 'gemini')  -> 'antigravity'
        resolve_canonical_inbox_name('worker', 'glm')     -> 'devin'
        resolve_canonical_inbox_name('worker', 'anthropic') -> 'claude_code_peer'
        resolve_canonical_inbox_name('coordinator', 'anthropic') -> 'claude_code_main'
        resolve_canonical_inbox_name('unknown_role')      -> 'unknown_role'
    """
    if not role:
        return ""
    key = role.strip().lower().replace("-", "_")
    # Phase 1: check provider-specific composite key first
    if provider:
        composite = f"{key}+{provider.strip().lower()}"
        if composite in CANONICAL_ROLE_TO_INBOX_DIR:
            return CANONICAL_ROLE_TO_INBOX_DIR[composite]
    return CANONICAL_ROLE_TO_INBOX_DIR.get(key, key)


def is_deprecated_inbox(dir_name: str) -> bool:
    """Return True if the dir name is a known deprecated inbox per scout findings."""
    return dir_name in DEPRECATED_DIR_TO_CANONICAL


def deprecated_to_canonical(dir_name: str) -> str:
    """Map a deprecated dir name to its canonical replacement.

    Returns dir_name unchanged if not deprecated.
    """
    return DEPRECATED_DIR_TO_CANONICAL.get(dir_name, dir_name)


__all__ = [
    "CANONICAL_ROLE_TO_INBOX_DIR",
    "DEPRECATED_DIR_TO_CANONICAL",
    "resolve_canonical_inbox_name",
    "is_deprecated_inbox",
    "deprecated_to_canonical",
]
