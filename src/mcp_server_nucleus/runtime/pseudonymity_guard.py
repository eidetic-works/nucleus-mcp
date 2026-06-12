"""v0.3.0 — Pseudonymity scrubber for relay body / wake_instruction text.

Per cc-peer 2026-06-09T11:55Z sketch SIGNOFF (concern_5
CONCUR-WITH-CORRECTION): empirical grep confirmed NO scrubber module
exists anywhere in mcp-server-nucleus/src/. Authored fresh to provide
the single source of truth for body-content scrubbing applied at
relay-READ time before threading into Layer 4 post_relay_to_role
(and thence into /v1/messages payload).

Why needed: relay body content travels via wake_instruction into
Anthropic's /v1/messages payload and gets stored in conversation
history server-side. Even though Layers 0/1/2/4/5 do not log body
content, the body DOES reach Anthropic's storage — pseudonymity
violation surface widens via that route.

Design (per cc-peer locked contract):
- Module-internal default patterns cover GENERIC shapes (paths,
  bearers, token-like strings) — safe to ship in public source.
- Operator-specific identity strings (real name, real email, real
  X/LinkedIn handle, other-venture product name, Telegram bot handle
  per feedback_extended_identity_strings_for_sanitization) load
  from operator-local config at ~/.tb/pseudonymity_patterns.json
  mode 0o600 at module import.
- If config file absent or invalid: generic-only mode (default-safe;
  caller still gets path/bearer scrubbing).
- Config file format: JSON array of {pattern: <regex>, replacement: <str>}
  objects. Operator extends + restarts MCP server to reload.

Pseudonymity discipline:
- Pattern set NEVER logged (even at DEBUG)
- Scrub applied to text but caller decides where to use the result
- This module does NOT enforce anything itself — it's a primitive
  utility; callers (e.g., the hook patch) must apply.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("nucleus.pseudonymity_guard")

# Operator-local config path (NEVER source-checked)
_OPERATOR_CONFIG_PATH = Path.home() / ".tb" / "pseudonymity_patterns.json"

# Generic patterns — safe to ship in public source.
# Each tuple: (compiled regex, replacement string).
_DEFAULT_GENERIC_PATTERNS: List[Tuple[str, str]] = [
    # User-home paths (any user)
    (r"/Users/[A-Za-z0-9._-]+/", "/Users/OPERATOR/"),
    (r"/home/[A-Za-z0-9._-]+/", "/home/OPERATOR/"),
    # Known operator email variants
    (r"\bmailforlk\d?@gmail\.com\b", "OPERATOR_EMAIL_SCRUBBED"),
    # Bearer tokens
    (r"Bearer\s+[A-Za-z0-9_.\-]{16,}", "Bearer SCRUBBED"),
    # OAuth access/refresh tokens (Anthropic-shape)
    (r"sk-ant-oat01-[A-Za-z0-9_.\-]{8,}", "sk-ant-oat01-SCRUBBED"),
    (r"sk-ant-ort01-[A-Za-z0-9_.\-]{8,}", "sk-ant-ort01-SCRUBBED"),
    (r"sk-ant-sid02-[A-Za-z0-9_.\-]{8,}", "sk-ant-sid02-SCRUBBED"),
    # Generic API-key-like strings
    (r"\bsk-[A-Za-z0-9_-]{20,}\b", "sk-SCRUBBED"),
    # Cookie sessionKey-like patterns
    (r"sessionKey=[^;\s]{8,}", "sessionKey=SCRUBBED"),
    (r"cf_clearance=[^;\s]{8,}", "cf_clearance=SCRUBBED"),
]


def _compile_patterns(
    raw_patterns: List[Tuple[str, str]],
) -> List[Tuple[re.Pattern, str]]:
    """Compile (regex_str, replacement) pairs. Invalid regexes are
    skipped with WARN (do not abort module import on bad config)."""
    out: List[Tuple[re.Pattern, str]] = []
    for pattern_src, replacement in raw_patterns:
        try:
            compiled = re.compile(pattern_src)
            out.append((compiled, replacement))
        except re.error as exc:
            # Pattern source itself may contain sensitive content; log
            # only the error class, not the pattern.
            logger.warning(
                "pseudonymity_guard: invalid pattern skipped err=%s",
                type(exc).__name__,
            )
    return out


def _load_operator_patterns(
    config_path: Path = _OPERATOR_CONFIG_PATH,
) -> List[Tuple[str, str]]:
    """Load operator-specific patterns from JSON config.

    Format: [{pattern: <regex>, replacement: <str>}, ...]

    Returns empty list on missing/invalid file (default-safe). The
    returned tuples are NOT compiled here — _compile_patterns handles
    that + skips invalid entries.
    """
    try:
        raw = config_path.read_text()
    except OSError:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(
            "pseudonymity_guard: operator config JSON parse failed; "
            "generic-only mode",
        )
        return []
    if not isinstance(parsed, list):
        logger.warning(
            "pseudonymity_guard: operator config not a JSON array; "
            "generic-only mode",
        )
        return []
    out: List[Tuple[str, str]] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        pattern_src = entry.get("pattern")
        replacement = entry.get("replacement", "SCRUBBED")
        if isinstance(pattern_src, str) and isinstance(replacement, str):
            out.append((pattern_src, replacement))
    return out


# Active pattern set — composed at import time + recomposable via
# reload_patterns() for tests + operator config-change scenarios.
_active_patterns: List[Tuple[re.Pattern, str]] = []


def reload_patterns(
    config_path: Optional[Path] = None,
) -> int:
    """Recompose active pattern set from generic + operator config.

    Returns the count of active compiled patterns. Tests can call this
    to inject + verify. Default config_path is _OPERATOR_CONFIG_PATH.
    """
    global _active_patterns
    path = config_path if config_path is not None else _OPERATOR_CONFIG_PATH
    operator_raw = _load_operator_patterns(path)
    combined_raw = list(_DEFAULT_GENERIC_PATTERNS) + operator_raw
    _active_patterns = _compile_patterns(combined_raw)
    logger.info(
        "pseudonymity_guard: pattern set reloaded count=%d "
        "(generic=%d operator=%d)",
        len(_active_patterns),
        len(_DEFAULT_GENERIC_PATTERNS),
        len(operator_raw),
    )
    return len(_active_patterns)


# Initial load at import
reload_patterns()


def scrub_pseudonymity(text: str) -> str:
    """Apply active pattern set to text; return scrubbed copy.

    Empty / None input returns "" / "". Non-string input is coerced
    via str() for defensiveness (caller should pass str).
    """
    if not text:
        return text or ""
    s = str(text)
    for pattern, replacement in _active_patterns:
        s = pattern.sub(replacement, s)
    return s


__all__ = [
    "scrub_pseudonymity",
    "reload_patterns",
]
