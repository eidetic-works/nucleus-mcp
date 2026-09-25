"""Attribute objects and run state enum for the Nucleus run store."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any


class RunState(str, Enum):
    """Canonical run lifecycle states."""

    CREATED = "created"
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_INPUT = "waiting_input"
    PAUSED_BUDGET = "paused_budget"
    TAKEOVER = "takeover"
    VERIFYING = "verifying"
    READY_FOR_REVIEW = "ready_for_review"
    APPLYING = "applying"
    APPLIED = "applied"
    PREVIEWED = "previewed"
    DISMISSED = "dismissed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandKind(str, Enum):
    """Canonical run command kinds."""

    CANCEL = "CANCEL"
    STEER = "STEER"
    ANSWER = "ANSWER"
    APPROVE = "APPROVE"
    PAUSE = "PAUSE"
    RESUME = "RESUME"


class TrustMode(str, Enum):
    """Project trust modes for R2 execution policy."""

    STRICT = "strict"
    DEFAULT = "default"
    PERMISSIVE = "permissive"


@dataclass(frozen=True)
class Project:
    id: str
    root_uri: str
    trust_mode: str
    policy_json: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Conversation:
    id: str
    project_id: str
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Run:
    id: str
    conversation_id: str
    runner_id: str
    model_id: str
    execution_target: str
    mode: str
    idempotency_key: str
    prompt: str = ""
    state: RunState = RunState.CREATED
    workspace: str | None = None
    base_revision: str | None = None
    requirements: str | None = None  # JSON-encoded task/check contract (schema v7+)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Event:
    id: str
    run_id: str
    seq: int
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RunCommand:
    id: str
    run_id: str
    seq: int
    kind: CommandKind
    issuer: str
    payload: dict[str, Any] = field(default_factory=dict)
    consumed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Lease:
    resource: str
    owner_id: str
    fencing_token: int
    expires_at: datetime
    acquired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Artifact:
    id: str
    run_id: str
    kind: str
    sha256: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = field(default_factory=dict)
    path: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCaseState(str, Enum):
    WAITING_FOR_GOAL = "waiting_for_goal"
    CONTRACTED = "contracted"
    BASELINE_RUNNING = "baseline_running"
    BASELINE_ACCEPTED = "baseline_accepted"
    FRICTION_CLASSIFIED = "friction_classified"
    LIMITATION_RECORDED = "limitation_recorded"
    IMPROVEMENT_RUNNING = "improvement_running"
    IMPROVEMENT_REVIEWED = "improvement_reviewed"
    REPLAY_RUNNING = "replay_running"
    HUMAN_REVIEW = "human_review"
    RETAINED = "retained"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ProductCase:
    id: str
    project_root: str
    contract_json: str | None = None
    contract_sha256: str | None = None
    state: ProductCaseState = ProductCaseState.WAITING_FOR_GOAL
    failure_owner: str | None = None
    friction: str | None = None
    baseline_run_id: str | None = None
    improvement_run_id: str | None = None
    replay_run_id: str | None = None
    baseline_outcome: str | None = None
    replay_outcome: str | None = None
    independent_review: str | None = None
    regression_passed: bool | None = None
    human_accepted: bool | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ProductCaseEvent:
    id: str
    product_case_id: str
    seq: int
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def outcome_score(outcome: dict[str, Any] | str) -> tuple[int, int, int, int, int]:
    if isinstance(outcome, str):
        outcome = json.loads(outcome)
    if not isinstance(outcome, dict):
        raise TypeError("outcome must be a dict or JSON string")
    return (
        1 if outcome["accepted"] is True else 0,
        1 if outcome["verdict"] == "ok" else 0,
        1 if outcome["apply_eligible"] is True else 0,
        -outcome["safety_violations"],
        -outcome["human_interventions"],
    )
