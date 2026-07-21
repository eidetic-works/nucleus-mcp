"""Nucleus Autonomous Lane — reusable autonomous execution loop for any repo.

This package provides the core machinery for running an autonomous task-execution
loop in any git repository. It is the generalized form of the principal_control /
executor_daemon / secretary_daemon pattern that completed the G1 gate in
ai-mvp-backend.

Architecture:
    SPEC.md (user-authored)  →  SpecParser  →  WorkItem list
    ControlWatcher           →  dispatches tasks via relay to executor lanes
    ExecutorDaemon           →  claims task, invokes vendor CLI (devin/agy), marks DONE
    SecretaryDaemon          →  independently verifies DONE tasks with pytest

Isolation:
    Each project gets its own .brain/ directory (NUCLEUS_BRAIN_PATH).
    The nucleus.db, relay/, state/, logs/ all live under that brain path.
    No cross-project contamination — each lane is fully isolated.

Surfaces:
    1. CLI: `nucleus lane init/start/stop/status/feedback`
    2. pip: `nucleus-autonomous-lane` package with `nucleus-lane` entry point
    3. Template: copyable scripts/ for git clone
    4. MCP: lane_init, lane_start, lane_stop, lane_status, lane_feedback tools

Ownership:
    The core code in this package is owned and maintained by the nucleus team.
    Other agents only use the surfaces (CLI, pip, template, MCP) and share
    feedback via the feedback channel.
"""

from .config import LaneConfig, WorkItem
from .spec_parser import SpecParser, SpecParseError
from .validator import validate_spec, ValidationResult
from .control_watcher import ControlWatcher
from .executor_daemon import ExecutorDaemon
from .secretary_daemon import SecretaryDaemon
from .isolation import isolate_brain, validate_isolation
from .feedback import submit_feedback, FeedbackStore

__all__ = [
    "LaneConfig",
    "WorkItem",
    "SpecParser",
    "SpecParseError",
    "validate_spec",
    "ValidationResult",
    "ControlWatcher",
    "ExecutorDaemon",
    "SecretaryDaemon",
    "isolate_brain",
    "validate_isolation",
    "submit_feedback",
    "FeedbackStore",
]
