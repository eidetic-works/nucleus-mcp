"""Spec parser — reads a SPEC.md and produces WorkItem list.

The SPEC.md format is a generalized version of PRINCIPAL.md:

    # SPEC: <project name>

    ## Gate G1

    ### Task: <task_id>
    - **Title:** <human-readable title>
    - **Authority:** <spec ref, e.g., "SPEC.md:39,67-69">
    - **Acceptance:**
      - <criterion 1>
      - <criterion 2>
    - **Blocked by:** <task_id1>, <task_id2>
    - **Priority:** 1

The parser extracts tasks and their dependencies, producing a DAG of WorkItems.
The spec is pinned via a git tag (immutability gate) — the tag commit, blob hash,
and body SHA-256 are recorded in the LaneConfig.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .config import LaneConfig, WorkItem


class SpecParseError(Exception):
    """Raised when the SPEC.md cannot be parsed or is malformed."""


class SpecParser:
    """Parse a SPEC.md file into WorkItems and pin it via git tag."""

    def __init__(self, config: LaneConfig):
        self.config = config

    def parse(self) -> Tuple[WorkItem, ...]:
        """Parse the SPEC.md and return a tuple of WorkItems.

        Raises:
            SpecParseError: If the spec is malformed or cannot be read.
        """
        spec_path = self.config.spec_path
        if not spec_path.exists():
            raise SpecParseError(f"SPEC file not found: {spec_path}")

        text = spec_path.read_text(encoding="utf-8")
        return self._parse_text(text)

    def _parse_text(self, text: str) -> Tuple[WorkItem, ...]:
        """Parse spec text into WorkItems."""
        items: List[WorkItem] = []
        # Match task blocks: ### Task: <id> ... (until next ### or ## or EOF)
        task_blocks = re.findall(
            r"###\s+Task:\s*(\S+)\s*\n(.*?)(?=\n###\s+Task:|\n##\s|$)",
            text,
            re.DOTALL,
        )
        if not task_blocks:
            raise SpecParseError(
                "No tasks found in SPEC.md. Expected '### Task: <task_id>' blocks."
            )

        for task_id, body in task_blocks:
            item = self._parse_task_block(task_id.strip(), body.strip())
            items.append(item)

        # Sort by priority (lower = higher priority)
        items.sort(key=lambda x: x.priority)
        return tuple(items)

    def _parse_task_block(self, task_id: str, body: str) -> WorkItem:
        """Parse a single task block body into a WorkItem."""
        title = self._extract_field(body, "Title") or task_id
        authority = self._extract_field(body, "Authority") or f"SPEC.md (task {task_id})"
        acceptance = self._extract_list(body, "Acceptance")
        blocked_by_str = self._extract_field(body, "Blocked by") or ""
        priority_str = self._extract_field(body, "Priority") or "2"
        task_type = (self._extract_field(body, "Task type") or "llm").lower()
        command = self._extract_field(body, "Command") or ""

        # Filter out placeholder values that mean "no dependency"
        _NONE_TOKENS = {"(none)", "none", "n/a", "na", "-", "—", "nil", "null", ""}
        blocked_by = tuple(
            b.strip() for b in blocked_by_str.split(",")
            if b.strip() and b.strip().lower() not in _NONE_TOKENS
        )

        try:
            priority = int(priority_str)
        except ValueError:
            priority = 2

        if not acceptance:
            raise SpecParseError(
                f"Task {task_id} has no acceptance criteria. "
                "At least one '- <criterion>' under 'Acceptance:' is required."
            )

        return WorkItem(
            task_id=task_id,
            title=title,
            spec_ref=authority,
            acceptance=tuple(acceptance),
            blocked_by=blocked_by,
            priority=priority,
            task_type=task_type,
            command=command,
        )

    def _extract_field(self, body: str, field_name: str) -> Optional[str]:
        """Extract a '- **Field:** value' line from the body."""
        pattern = rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)"
        match = re.search(pattern, body)
        return match.group(1).strip() if match else None

    def _extract_list(self, body: str, field_name: str) -> List[str]:
        """Extract a '- **Field:**' followed by bullet list items."""
        pattern = rf"\*\*{re.escape(field_name)}:\*\*\s*\n((?:\s*-\s+.+\n?)+)"
        match = re.search(pattern, body)
        if not match:
            return []
        items = re.findall(r"-\s+(.+)", match.group(1))
        return [item.strip() for item in items]

    def pin_spec(self) -> None:
        """Pin the spec via git tag and record the hashes in config.

        Creates a git tag pointing at the current HEAD and records:
        - spec_tag_commit: the commit the tag points to
        - spec_blob: the blob SHA of the spec file at that tag
        - spec_body_sha256: SHA-256 of the spec body text
        """
        repo = self.config.repo_root
        spec_rel = self.config.spec_path.relative_to(repo)
        tag = self.config.spec_tag

        if not tag:
            raise SpecParseError("No spec_tag in config — cannot pin spec")

        # Create or update the tag
        subprocess.run(
            ["git", "-C", str(repo), "tag", "-f", tag],
            check=True,
            capture_output=True,
        )

        # Record the commit the tag points to
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{tag}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.config.spec_tag_commit = result.stdout.strip()

        # Record the blob SHA of the spec file
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{tag}:{spec_rel}"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.config.spec_blob = result.stdout.strip()

        # Record the body SHA-256
        body = self.config.spec_path.read_bytes()
        self.config.spec_body_sha256 = hashlib.sha256(body).hexdigest()

    def verify_spec(self) -> dict:
        """Verify the spec hasn't moved from its pinned values.

        Returns a dict with verification status. Raises if the spec has moved.
        """
        repo = self.config.repo_root
        spec_rel = self.config.spec_path.relative_to(repo)
        tag = self.config.spec_tag

        if not tag or not self.config.spec_tag_commit:
            raise SpecParseError("Spec not pinned — no tag/commit in config")

        # Check tag commit
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{tag}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        actual_commit = result.stdout.strip()
        if actual_commit != self.config.spec_tag_commit:
            raise SpecParseError(
                f"Spec tag {tag} moved from pinned commit "
                f"{self.config.spec_tag_commit[:12]} to {actual_commit[:12]}"
            )

        # Check blob
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{tag}:{spec_rel}"],
            capture_output=True,
            text=True,
            check=True,
        )
        actual_blob = result.stdout.strip()
        if actual_blob != self.config.spec_blob:
            raise SpecParseError(
                f"Spec blob moved from pinned {self.config.spec_blob[:12]} "
                f"to {actual_blob[:12]}"
            )

        # Check body SHA-256
        body = self.config.spec_path.read_bytes()
        actual_sha = hashlib.sha256(body).hexdigest()
        if actual_sha != self.config.spec_body_sha256:
            raise SpecParseError(
                f"Spec body SHA-256 changed from {self.config.spec_body_sha256[:12]} "
                f"to {actual_sha[:12]}"
            )

        return {
            "tag": tag,
            "tag_commit": actual_commit,
            "blob": actual_blob,
            "body_sha256": actual_sha,
            "verified": True,
        }
