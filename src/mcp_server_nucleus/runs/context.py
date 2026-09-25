"""Read-only context adapters for Renaissance runs.

These adapters deliberately avoid any write path. They expose `.brain` and
project-workspace state to runners and to prompt construction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .workspace import Workspace, WorkspaceBackend


class ContextEscape(Exception):
    """Raised when a requested context path escapes its container."""


@dataclass
class BrainContext:
    """Read-only view into a Nucleus `.brain` directory."""

    brain_path: Path

    def _safe_path(self, rel_or_abs: str) -> Path:
        if Path(rel_or_abs).is_absolute():
            candidate = Path(rel_or_abs)
        else:
            candidate = self.brain_path / rel_or_abs
        resolved = candidate.resolve()
        base = self.brain_path.resolve()
        if not resolved.is_relative_to(base):
            raise ContextEscape(f"{resolved} is outside {base}")
        return resolved

    def exists(self, rel_path: str) -> bool:
        try:
            return self._safe_path(rel_path).exists()
        except ContextEscape:
            return False

    def read_text(self, rel_path: str, limit: int = 50_000) -> str:
        path = self._safe_path(rel_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:limit]

    def read_jsonl_tail(self, rel_path: str, limit: int = 50) -> list[dict[str, Any]]:
        path = self._safe_path(rel_path)
        if not path.is_file():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"_raw": line})
        return records

    def list_markdown(self, directory: str) -> list[str]:
        path = self._safe_path(directory)
        if not path.is_dir():
            return []
        return sorted(
            str(p.relative_to(self.brain_path))
            for p in path.rglob("*.md")
            if p.is_file()
        )


@dataclass
class ProjectContext:
    """Read-only view into the run's isolated workspace target."""

    workspace: Workspace
    backend: WorkspaceBackend

    def read(self, rel_path: str, limit: int = 50_000) -> str:
        try:
            resolved = self.backend.resolve(self.workspace, rel_path)
        except Exception as exc:
            raise ContextEscape(f"context path {rel_path!r} escapes workspace") from exc
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        return resolved.read_text(encoding="utf-8", errors="replace")[:limit]

    def list_files(self, pattern: str = "*") -> list[str]:
        return sorted(
            str(p.relative_to(self.workspace.target_path))
            for p in self.workspace.target_path.rglob(pattern)
            if p.is_file() and not p.name.startswith(".")
        )


@dataclass
class RunContext:
    """Read-only context bundle for one run."""

    run_id: str
    conversation_id: str
    project_id: str
    prompt: str
    brain_context: BrainContext | None
    project_context: ProjectContext | None

    def prompt_prefix(self, max_brain_records: int = 5) -> str:
        parts = [
            f"Run: {self.run_id}",
            f"Conversation: {self.conversation_id}",
            f"Project: {self.project_id}",
            f"Task: {self.prompt}",
        ]
        if self.brain_context is not None:
            events = self.brain_context.read_jsonl_tail("ledger/events.jsonl", limit=max_brain_records)
            if events:
                parts.append("Recent events:")
                for ev in events:
                    parts.append(f"  - {json.dumps(ev, default=str)}")
        if self.project_context is not None:
            files = self.project_context.list_files()[:20]
            if files:
                parts.append("Workspace files:")
                for f in files:
                    parts.append(f"  - {f}")
        return "\n".join(parts)
