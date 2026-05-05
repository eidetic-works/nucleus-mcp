"""Org delegate: assemble Sonnet persona prompts from charters.

Two surfaces:

1. `assemble_prompt` (original) — pure-logic charter loader. Returns the
   assembled prompt + metadata. Caller is responsible for emitting
   `agent_spawn` / `agent_return` events around its own `Agent()` call.
2. `spawn_prep` / `spawn_close` (added per cost-consult convergence
   2026-05-02) — two-phase API that wraps `assemble_prompt` AND emits
   the events itself, eliminating per-callsite emit boilerplate. Use
   this in `/delegate` skill and any other callsite that wants
   zero-glue cost telemetry.

The two surfaces coexist; `assemble_prompt` callers are not affected.
"""

import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


_DEFAULT_CHARTERS_SUBDIR = Path("docs") / "org" / "charters"


def _charter_path(role: str, charters_dir: Path) -> Path:
    return charters_dir / f"{role}.md"


def _default_charters_dir() -> Path:
    return Path.cwd() / _DEFAULT_CHARTERS_SUBDIR


def load_charter(role: str, charters_dir: Optional[Path] = None) -> str:
    """Read charter body from `<charters_dir>/<role>.md`.

    Fails loud with FileNotFoundError naming the exact path searched, so a
    missing charter can't silently degrade to a prompt-less Agent call.
    """
    base = charters_dir if charters_dir is not None else _default_charters_dir()
    path = _charter_path(role, base)
    if not path.exists():
        raise FileNotFoundError(f"Charter not found: {path}")
    return path.read_text(encoding="utf-8")


def assemble_prompt(role: str, brief: str,
                    charters_dir: Optional[Path] = None
                    ) -> Tuple[str, Dict[str, Any]]:
    """Return `(prompt, metadata)` for a Sonnet persona spawn.

    - `prompt`: charter body + brief, concatenated with a divider.
    - `metadata`: dict suitable for an `agent_spawn` event payload —
      `{role, charter_path, prompt_chars, brief_chars}`. The caller (Opus)
      is responsible for emitting `agent_spawn` before `Agent()` and
      `agent_return` after.
    """
    base = charters_dir if charters_dir is not None else _default_charters_dir()
    charter = load_charter(role, base)
    prompt = (
        f"# Charter: {role}\n\n"
        f"{charter}\n\n"
        f"---\n\n"
        f"# Brief\n\n"
        f"{brief.strip()}\n"
    )
    metadata = {
        "role": role,
        "charter_path": str(_charter_path(role, base)),
        "prompt_chars": len(prompt),
        "brief_chars": len(brief),
    }
    return prompt, metadata


def _new_spawn_id() -> str:
    """spawn_<unix>_<8hex> — chronologically sortable; pairs spawn↔return."""
    return f"spawn_{int(time.time())}_{secrets.token_hex(4)}"


# In-memory store mapping spawn_id → spawn_prep metadata. spawn_close pulls
# from here to emit agent_return paired with agent_spawn. Lives only for the
# Opus session that called spawn_prep — no cross-session persistence (events
# in .brain/ledger/events.jsonl are the durable trace).
_INFLIGHT_SPAWNS: Dict[str, Dict[str, Any]] = {}


def spawn_prep(role: str, brief: str, model: str, parent: str,
               charters_dir: Optional[Path] = None
               ) -> Tuple[str, str]:
    """Phase 1 of spawn_and_emit. Returns `(prompt, spawn_id)`.

    Caller invokes `Agent(model=model, prompt=prompt, ...)` after this,
    then calls `spawn_close(spawn_id, response_text)` to close the loop.

    Emits `agent_spawn` event with payload:
      {spawn_id, role, model, parent, prompt_chars, brief_chars, charter_path}
    """
    prompt, metadata = assemble_prompt(role, brief, charters_dir=charters_dir)
    spawn_id = _new_spawn_id()
    spawn_data = {
        "spawn_id": spawn_id,
        "role": role,
        "model": model,
        "parent": parent,
        "prompt_chars": metadata["prompt_chars"],
        "brief_chars": metadata["brief_chars"],
        "charter_path": metadata["charter_path"],
        "started_at_ms": int(time.time() * 1000),
    }
    _INFLIGHT_SPAWNS[spawn_id] = spawn_data
    try:
        from .event_ops import _emit_event
        _emit_event(
            event_type="agent_spawn",
            emitter=parent,
            data=spawn_data,
            description=f"{parent} spawned {role} ({model})",
        )
    except Exception:
        pass  # never block the spawn flow on emit failure
    try:
        from .marketplace import register_tool
        slug = role.lower().replace("_", "-")
        address = f"{slug}@nucleus"
        register_tool({
            "address": address,
            "display_name": role,
            "accepts": ["spawn_brief"],
            "emits": ["spawn_response"],
            "tags": ["spawned-agent", model],
            "model": model,
            "parent": parent,
            "spawn_id": spawn_id,
        })
        spawn_data["registry_address"] = address
    except Exception:
        pass  # registry is supplementary — never block spawn
    return prompt, spawn_id


def spawn_close(spawn_id: str, response_text: str, *, success: bool = True) -> Dict[str, Any]:
    """Phase 2 of spawn_and_emit. Emits `agent_return` paired with the
    `agent_spawn` from spawn_prep. Returns the data payload that was emitted.

    Idempotent: calling with an unknown spawn_id (already-closed or never-prepped)
    emits a `agent_return` with `orphan=True` so audit_token_cost.py can detect
    the gap rather than silently dropping.
    """
    prep = _INFLIGHT_SPAWNS.pop(spawn_id, None)
    end_ms = int(time.time() * 1000)
    if prep is None:
        return_data = {
            "spawn_id": spawn_id,
            "response_chars": len(response_text),
            "duration_ms": None,
            "success": success,
            "orphan": True,
        }
        emitter = "unknown"
    else:
        return_data = {
            "spawn_id": spawn_id,
            "role": prep["role"],
            "model": prep["model"],
            "parent": prep["parent"],
            "response_chars": len(response_text),
            "duration_ms": end_ms - prep["started_at_ms"],
            "success": success,
            "orphan": False,
        }
        emitter = prep["parent"]
    try:
        from .event_ops import _emit_event
        _emit_event(
            event_type="agent_return",
            emitter=emitter,
            data=return_data,
            description=f"agent_return for {spawn_id}",
        )
    except Exception:
        pass
    if prep is not None and return_data.get("duration_ms") is not None:
        try:
            from .marketplace import ReputationSignals
            slug = prep["role"].lower().replace("_", "-")
            ReputationSignals.record_interaction(
                to_address=f"{slug}@nucleus",
                from_address=prep["parent"],
                latency_ms=return_data["duration_ms"],
                success=success,
            )
        except Exception:
            pass  # reputation tracking is supplementary
    return return_data
