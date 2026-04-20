"""``nucleus mcp register`` implementation per ``week2_init_flow_spec.md`` §3b.

Steps:
1. Backup target config to ``<config>.bak.<ISO8601>``.
2. Validate existing config parses as JSON. Abort if corrupt; never rewrite.
3. Compute patch — insert ``nucleus_wedge`` entry (binary via ``which``,
   ``NUCLEUS_BRAIN_PATH`` from ``Store.brain_path()``).
4. Atomic write: ``<config>.tmp`` → fsync → rename.
5. Re-validate; restore from in-memory original on failure.
6. ``--dry-run`` prints computed config; no write.

Idempotence (criterion #8): if existing entry matches desired patch, skip
backup + write entirely; report ``skipping`` and return 0. Sibling MCP
entries are preserved exactly (criterion #9).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from nucleus_wedge.store import Store

WEDGE_KEY = "nucleus_wedge"
DEFAULT_CONFIG = Path.home() / ".claude.json"


def _iso_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_config_path(flag: str | None) -> Path:
    return Path(flag).expanduser() if flag else DEFAULT_CONFIG


def _resolve_binary() -> str | None:
    return shutil.which("nucleus-wedge")


def _build_entry(brain: Path, binary: str) -> dict:
    return {
        "command": binary,
        "args": [],
        "env": {"NUCLEUS_BRAIN_PATH": str(brain)},
    }


def _atomic_write(path: Path, payload: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)


def do_register(config_path_arg: str | None, dry_run: bool) -> int:
    """Execute ``nucleus mcp register``. Returns process exit code."""
    config_path = _resolve_config_path(config_path_arg)

    if not config_path.exists():
        print(
            f"nucleus mcp register: config not found at {config_path}.\n"
            f"  Pass --config-path /absolute/path or run a CC session first to create it.",
            file=sys.stderr,
        )
        return 1

    original_text = config_path.read_text(encoding="utf-8")
    try:
        config = json.loads(original_text)
    except json.JSONDecodeError as exc:
        print(
            f"nucleus mcp register: config at {config_path} is not valid JSON ({exc}).\n"
            f"  Refusing to rewrite a corrupt config.",
            file=sys.stderr,
        )
        return 1

    binary = _resolve_binary()
    if not binary:
        print(
            "nucleus mcp register: cannot locate `nucleus-wedge` binary on PATH.\n"
            "  Install via `pip install nucleus-mcp` or activate the venv that contains it.",
            file=sys.stderr,
        )
        return 1
    try:
        brain = Store.brain_path(None)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    existing_mcp_servers = config.get("mcpServers")
    if "mcpServers" in config and not isinstance(existing_mcp_servers, dict):
        print(
            f"nucleus mcp register: config at {config_path} has mcpServers of type "
            f"{type(existing_mcp_servers).__name__}, expected object/dict.\n"
            f"  Refusing to mutate a non-dict mcpServers.",
            file=sys.stderr,
        )
        return 1

    desired_entry = _build_entry(brain, binary)
    existing_entry = (existing_mcp_servers or {}).get(WEDGE_KEY)
    if existing_entry == desired_entry:
        print(f"config already contains {WEDGE_KEY} entry, skipping (idempotent no-op)")
        return 0

    patched = json.loads(json.dumps(config))
    patched.setdefault("mcpServers", {})[WEDGE_KEY] = desired_entry
    payload = json.dumps(patched, indent=2) + "\n"

    if dry_run:
        print("--- dry-run: computed config (no write) ---")
        print(payload, end="")
        return 0

    backup_path = config_path.with_suffix(config_path.suffix + f".bak.{_iso_for_filename()}")
    backup_path.write_text(original_text, encoding="utf-8")

    _atomic_write(config_path, payload)

    try:
        json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _atomic_write(config_path, original_text)
        print(
            f"nucleus mcp register: post-write validation failed; restored original. "
            f"Backup at {backup_path}.",
            file=sys.stderr,
        )
        return 1

    print(f"backup: {backup_path}")
    print(f"config: {config_path}")
    print(f"entry: {WEDGE_KEY}")
    print(f"binary: {binary}")
    print(f"brain: {brain}")
    return 0
