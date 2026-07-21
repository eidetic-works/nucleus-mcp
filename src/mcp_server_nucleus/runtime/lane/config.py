"""Lane configuration — the dataclass that defines a lane's behavior.

A LaneConfig is derived from a SPEC.md file (via SpecParser) and controls:
    - Where the brain directory is (isolation)
    - What git tag/pin protects the spec (immutability gate)
    - Which executor lanes are available (devin, agy, etc.)
    - The source filter for task claiming
    - Polling intervals and retry limits
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class WorkItem:
    """A single unit of work projected from the SPEC.md.

    Each work item becomes a task in the nucleus task store.
    """

    task_id: str
    title: str
    spec_ref: str
    acceptance: Tuple[str, ...]
    blocked_by: Tuple[str, ...] = field(default_factory=tuple)
    priority: int = 2
    task_type: str = "llm"  # "llm" (default) or "shell" (direct command, no LLM)
    command: str = ""  # For task_type="shell": the shell command to run

    @property
    def description(self) -> str:
        dependency = ""
        if self.blocked_by:
            dependency = f"\nBlocked by: {', '.join(self.blocked_by)}"
        checks = "\n".join(f"- {item}" for item in self.acceptance)
        base = (
            f"SPEC-CITED WORK: {self.title}\n"
            f"Authority: {self.spec_ref}\n"
            f"Acceptance (rerunnable evidence, not narration):\n{checks}{dependency}\n"
            "Do not edit the SPEC.md. Return artifacts, commands, and test output."
        )
        if self.task_type == "shell" and self.command:
            base += f"\n\nTask type: shell\nCommand: {self.command}"
        return base


@dataclass
class LaneConfig:
    """Configuration for an autonomous lane.

    Attributes:
        repo_root: Path to the git repository root.
        brain_path: Path to the .brain directory (isolated per project).
        spec_path: Path to the SPEC.md file (relative to repo_root).
        spec_tag: Git tag that pins the spec (immutability gate).
        spec_tag_commit: Pinned commit SHA for the tag.
        spec_blob: Pinned blob SHA for the spec file.
        spec_body_sha256: Pinned SHA-256 of the spec body.
        role: The lane role (e.g., "principal-g1", "project-x-g1").
        source: Task source filter (e.g., "principal-control", "lane-control").
        lanes: Available executor lanes (e.g., ("lane_devin", "lane_agy")).
        poll_interval: Seconds between control watcher polls.
        executor_poll_interval: Seconds between executor polls.
        max_retries: Max retries before a task is escalated.
        max_inflight: Max concurrent executions (1 = shared-worktree safety).
        verify_only_secretary: If True, secretary only verifies (no plan processing).
        vendor: Default vendor for executors ("devin" or "agy").
    """

    repo_root: Path
    brain_path: Path
    spec_path: Path
    spec_tag: str = ""
    spec_tag_commit: str = ""
    spec_blob: str = ""
    spec_body_sha256: str = ""
    role: str = "lane-g1"
    source: str = "lane-control"
    lanes: Tuple[str, ...] = ("lane_devin", "lane_agy")
    poll_interval: int = 30
    executor_poll_interval: int = 10
    max_retries: int = 3
    max_inflight: int = 1
    verify_only_secretary: bool = True
    vendor: str = "devin"

    @property
    def state_path(self) -> Path:
        return self.brain_path / "state" / "lane_control.json"

    @property
    def progress_path(self) -> Path:
        return self.brain_path / "state" / "lane_progress.md"

    @property
    def relay_dir(self) -> Path:
        return self.brain_path / "relay"

    @property
    def logs_dir(self) -> Path:
        return self.brain_path / "logs"

    @property
    def claimable_statuses(self) -> set:
        return {"TODO", "PENDING", "READY"}

    def to_dict(self) -> dict:
        return {
            "repo_root": str(self.repo_root),
            "brain_path": str(self.brain_path),
            "spec_path": str(self.spec_path),
            "spec_tag": self.spec_tag,
            "spec_tag_commit": self.spec_tag_commit,
            "spec_blob": self.spec_blob,
            "spec_body_sha256": self.spec_body_sha256,
            "role": self.role,
            "source": self.source,
            "lanes": list(self.lanes),
            "poll_interval": self.poll_interval,
            "executor_poll_interval": self.executor_poll_interval,
            "max_retries": self.max_retries,
            "max_inflight": self.max_inflight,
            "verify_only_secretary": self.verify_only_secretary,
            "vendor": self.vendor,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LaneConfig":
        return cls(
            repo_root=Path(d["repo_root"]),
            brain_path=Path(d["brain_path"]),
            spec_path=Path(d["spec_path"]),
            spec_tag=d.get("spec_tag", ""),
            spec_tag_commit=d.get("spec_tag_commit", ""),
            spec_blob=d.get("spec_blob", ""),
            spec_body_sha256=d.get("spec_body_sha256", ""),
            role=d.get("role", "lane-g1"),
            source=d.get("source", "lane-control"),
            lanes=tuple(d.get("lanes", ["lane_devin", "lane_agy"])),
            poll_interval=d.get("poll_interval", 30),
            executor_poll_interval=d.get("executor_poll_interval", 10),
            max_retries=d.get("max_retries", 3),
            max_inflight=d.get("max_inflight", 1),
            verify_only_secretary=d.get("verify_only_secretary", True),
            vendor=d.get("vendor", "devin"),
        )
