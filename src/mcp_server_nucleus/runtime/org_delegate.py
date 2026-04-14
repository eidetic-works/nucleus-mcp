"""Org delegate: assemble Sonnet persona prompts from charters.

Pure-logic module. Emits NO events — by the plan's 1A decision, Opus emits
`agent_spawn` and `agent_return` itself, around the actual `Agent()` call.
This module just loads the charter and builds the prompt string, returning
metadata the caller uses for emission.
"""

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
