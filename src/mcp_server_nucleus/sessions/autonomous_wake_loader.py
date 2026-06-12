"""v0.3.0 — Autonomous-wake MAP loader from operator config file.

Per cc-peer 2026-06-09T11:55Z sketch SIGNOFF (Q1 CONCUR): loads
~/.tb/autonomous_wake_config.json mode 0o600 at MCP server startup
and populates NUCLEUS_AUTONOMOUS_WAKE_MAP via register_autonomous_role.

Config file format (JSON array):
  [
    {
      "role": "cc_tb",
      "session_id": "cse_...",
      "org_uuid": "903554b9-...",
      "model": "claude-sonnet-4-6",        # optional
      "max_tokens": 4096,                   # optional
      "history_limit": 50,                  # optional
      "prearm": true                        # optional
    },
    ...
  ]

Per cc-peer Q1 minor_consideration: JSONC-style comments (//, /* */)
are NOT stripped in v1 (operator can keep notes in sibling .md file
if needed). Strict JSON only.

Default-off posture: if file is absent, the registry stays empty,
NO role is autonomously woken. This is the explicit opt-in
semantics per cc-peer concern_1.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from mcp_server_nucleus.sessions.autonomous_wake_map import (
    NUCLEUS_AUTONOMOUS_WAKE_MAP,
    AutonomousWakeConfig,
    clear_registry,
    register_autonomous_role,
)

logger = logging.getLogger("nucleus.autonomous_wake_loader")

_CONFIG_PATH = Path.home() / ".tb" / "autonomous_wake_config.json"


def load_autonomous_wake_map(
    config_path: Optional[Path] = None,
    *,
    clear_first: bool = True,
) -> int:
    """Load operator config into the MAP. Returns count of registered roles.

    If config file is absent: returns 0 (default-off semantics).
    If config file is malformed JSON: logs WARN, returns 0.
    If individual entries are malformed: skipped with WARN; count
    reflects successful registrations only.

    `clear_first=True` (default) wipes the MAP before loading — fresh
    state per reload. Pass False to merge additively.
    """
    path = config_path if config_path is not None else _CONFIG_PATH

    if clear_first:
        clear_registry()

    try:
        raw = path.read_text()
    except OSError:
        logger.info(
            "autonomous_wake_loader: no config file at %s; default-off",
            path.name,  # don't log full path (HOME may contain identity)
        )
        return 0

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "autonomous_wake_loader: JSON parse failed err=%s; default-off",
            type(exc).__name__,
        )
        return 0

    if not isinstance(parsed, list):
        logger.warning(
            "autonomous_wake_loader: config must be JSON array; default-off",
        )
        return 0

    count = 0
    for idx, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            logger.warning(
                "autonomous_wake_loader: entry %d not a dict; skipped",
                idx,
            )
            continue
        try:
            config = AutonomousWakeConfig(
                role=entry["role"],
                session_id=entry["session_id"],
                org_uuid=entry["org_uuid"],
                # account_uuid optional per Task #63: when present,
                # discovery_context calls bespoq loader for operator
                # identity. When absent, autonomous wake fires bare LLM.
                account_uuid=entry.get("account_uuid"),
                model=entry.get("model"),
                max_tokens=entry.get("max_tokens"),
                history_limit=entry.get("history_limit", 50),
                prearm=entry.get("prearm", True),
            )
            register_autonomous_role(config.role, config)
            count += 1
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning(
                "autonomous_wake_loader: entry %d skipped err=%s",
                idx, type(exc).__name__,
            )
            continue

    # cc-peer 18:00Z Q3 LOCKED-COMPATIBLE: startup bearer-file check.
    # WARN per loaded role whose ~/.tb/relay_token_<role> is absent.
    # NOT fatal — role might be local-only; Plan B forwarder has its
    # own lazy check at call time. Visibility for operator on misconfig.
    bearer_dir = Path.home() / ".tb"
    missing_bearers = []
    for role_name in list(NUCLEUS_AUTONOMOUS_WAKE_MAP.keys()):
        if not (bearer_dir / f"relay_token_{role_name}").exists():
            missing_bearers.append(role_name)
    if missing_bearers:
        logger.warning(
            "autonomous_wake_loader: %d role(s) registered without "
            "bearer file roles=%s -- Plan B forwarder will skip POST",
            len(missing_bearers), missing_bearers,
        )

    logger.info(
        "autonomous_wake_loader: registered %d role(s) from config",
        count,
    )
    return count


__all__ = [
    "load_autonomous_wake_map",
]
