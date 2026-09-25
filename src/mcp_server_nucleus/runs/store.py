"""SQLite-backed run store for Nucleus Renaissance."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar

from typing_extensions import Self

from .models import (
    Artifact,
    CommandKind,
    Conversation,
    Event,
    Lease,
    ProductCase,
    ProductCaseEvent,
    ProductCaseState,
    Project,
    Run,
    RunCommand,
    RunState,
    outcome_score,
)


class InvalidRunTransition(Exception):
    """Raised when a run state transition is not allowed."""


class IdempotencyConflict(Exception):
    """Raised when an idempotency key is reused with mismatched identity fields."""


class StaleLease(Exception):
    """Raised when a lease is not active or the token is stale."""


class LeaseConflict(Exception):
    """Raised when a lease is held by another owner."""


class ArtifactConflict(Exception):
    pass


class UnsupportedSchemaVersion(Exception):
    pass


class InvalidProductCaseContract(Exception):
    pass


class InvalidProductCaseOutcome(Exception):
    pass


class InvalidProductCaseUpdate(Exception):
    pass


class InvalidProductCaseTransition(Exception):
    pass


class StaleProductCaseState(Exception):
    pass


class ProductCaseHashMismatch(Exception):
    pass


class ProductCasePreconditionError(Exception):
    pass


class ActiveProductCaseExists(Exception):
    pass


class ProductCaseNotFound(Exception):
    pass


@dataclass(frozen=True)
class Session:
    """Persistent ACP session record."""

    id: str
    run_id: str
    conversation_id: str
    project_id: str
    cwd: str | None
    prompt: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class UsageRow:
    """Recorded token/cost usage for a single run."""

    run_id: str
    tokens: int | None
    cost: float | None
    source: str
    confidence: str
    quota_class: str
    model_family: str
    model_id: str
    vendor: str
    duration: float
    created_at: datetime


class RunStore:
    """Persistent store for projects, conversations, runs, and their events."""

    _SCHEMA_VERSION = 9

    _TRANSITIONS: ClassVar[dict[RunState, set[RunState]]] = {
        RunState.CREATED: {RunState.QUEUED, RunState.CANCELLED},
        RunState.QUEUED: {RunState.PREPARING, RunState.CANCELLED},
        RunState.PREPARING: {RunState.RUNNING, RunState.FAILED, RunState.CANCELLED},
        RunState.RUNNING: {
            RunState.WAITING_APPROVAL,
            RunState.WAITING_INPUT,
            RunState.PAUSED_BUDGET,
            RunState.TAKEOVER,
            RunState.VERIFYING,
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.WAITING_APPROVAL: {
            RunState.RUNNING,
            RunState.TAKEOVER,
            RunState.READY_FOR_REVIEW,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.WAITING_INPUT: {RunState.RUNNING, RunState.FAILED, RunState.CANCELLED},
        RunState.PAUSED_BUDGET: {RunState.RUNNING, RunState.FAILED, RunState.CANCELLED},
        RunState.TAKEOVER: {RunState.RUNNING, RunState.FAILED, RunState.CANCELLED},
        RunState.VERIFYING: {
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.READY_FOR_REVIEW: {
            RunState.APPLYING,
            RunState.APPLIED,
            RunState.PREVIEWED,
            RunState.DISMISSED,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.APPLYING: {RunState.APPLIED, RunState.READY_FOR_REVIEW, RunState.FAILED, RunState.CANCELLED},
        RunState.PREVIEWED: {RunState.APPLYING, RunState.APPLIED, RunState.DISMISSED, RunState.FAILED, RunState.CANCELLED},
        RunState.APPLIED: set(),
        RunState.DISMISSED: set(),
        RunState.COMPLETED: {RunState.PREVIEWED},
        RunState.FAILED: set(),
        RunState.CANCELLED: set(),
    }

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._ensure_schema()
        except Exception:
            self._conn.close()
            raise

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _ensure_schema(self) -> None:
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                table = self._conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
                ).fetchone()
                if table:
                    row = self._conn.execute(
                        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
                    ).fetchone()
                    version = row[0] if row else 0
                else:
                    version = 0
                if version > self._SCHEMA_VERSION:
                    raise UnsupportedSchemaVersion(
                        f"schema version {version} > supported {self._SCHEMA_VERSION}"
                    )
                self._conn.execute(
                    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
                )
                for v in range(version + 1, self._SCHEMA_VERSION + 1):
                    self._migrate(v)
                self._conn.execute("DELETE FROM schema_version")
                self._conn.execute(
                    "INSERT INTO schema_version(version) VALUES (?)",
                    (self._SCHEMA_VERSION,),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def _migrate(self, version: int) -> None:
        if version == 1:
            self._create_v1_tables()
        elif version == 2:
            self._create_v2_tables()
        elif version == 3:
            self._create_v3_tables()
        elif version == 4:
            self._create_v4_tables()
        elif version == 5:
            self._create_v5_tables()
        elif version == 6:
            self._create_v6_tables()
        elif version == 7:
            self._create_v7_tables()
        elif version == 8:
            self._create_v8_tables()
        elif version == 9:
            self._create_v9_tables()

    def _create_v1_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                root_uri TEXT NOT NULL,
                trust_mode TEXT NOT NULL,
                policy_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                runner_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                execution_target TEXT NOT NULL,
                mode TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                prompt TEXT,
                state TEXT NOT NULL,
                workspace TEXT,
                base_revision TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(conversation_id, idempotency_key)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                seq INTEGER NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(run_id, seq)
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq)")

    def _create_v2_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                seq INTEGER NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                issuer TEXT NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, seq)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_commands_run_seq ON commands(run_id, seq)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_commands_run_consumed ON commands(run_id, consumed)"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leases (
                resource TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                fencing_token INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                acquired_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lease_counters (
                resource TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                metadata TEXT,
                path TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, kind, sha256)
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id)")

    def _has_column(self, table: str, column: str) -> bool:
        rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row["name"] == column for row in rows)

    def _create_v3_tables(self) -> None:
        if not self._has_column("projects", "policy_json"):
            self._conn.execute("ALTER TABLE projects ADD COLUMN policy_json TEXT")
        if not self._has_column("runs", "base_revision"):
            self._conn.execute("ALTER TABLE runs ADD COLUMN base_revision TEXT")

    def _create_v4_tables(self) -> None:
        if not self._has_column("runs", "prompt"):
            self._conn.execute("ALTER TABLE runs ADD COLUMN prompt TEXT")

    def _create_v5_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                cwd TEXT,
                prompt TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_run_id ON sessions(run_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_conversation_id ON sessions(conversation_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)"
        )

    def _create_v6_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                run_id TEXT PRIMARY KEY,
                tokens INTEGER,
                cost REAL,
                source TEXT,
                confidence TEXT,
                quota_class TEXT,
                model_family TEXT,
                model_id TEXT,
                vendor TEXT,
                duration REAL,
                created_at TEXT
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_run_id ON usage(run_id)"
        )

    def _create_v7_tables(self) -> None:
        """Add requirements column to runs for persisted task/check contracts."""
        if not self._has_column("runs", "requirements"):
            self._conn.execute("ALTER TABLE runs ADD COLUMN requirements TEXT")

    def _create_v8_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_cases (
                id TEXT PRIMARY KEY,
                project_root TEXT NOT NULL,
                contract_json TEXT,
                contract_sha256 TEXT,
                state TEXT NOT NULL,
                failure_owner TEXT,
                friction TEXT,
                baseline_run_id TEXT REFERENCES runs(id) ON DELETE RESTRICT,
                improvement_run_id TEXT REFERENCES runs(id) ON DELETE RESTRICT,
                replay_run_id TEXT REFERENCES runs(id) ON DELETE RESTRICT,
                baseline_outcome TEXT,
                replay_outcome TEXT,
                independent_review TEXT,
                regression_passed INTEGER,
                human_accepted INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_case_events (
                id TEXT PRIMARY KEY,
                product_case_id TEXT NOT NULL REFERENCES product_cases(id) ON DELETE CASCADE,
                seq INTEGER NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(product_case_id, seq)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_case_events_case_seq ON product_case_events(product_case_id, seq)"
        )
        self._conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_product_cases_active_root
            ON product_cases(project_root)
            WHERE state NOT IN ('baseline_accepted', 'limitation_recorded', 'retained', 'rejected')
            """
        )

    def _create_v9_tables(self) -> None:
        """Add the persistent product goal queue `evolve next` claims from."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_goals (
                id TEXT PRIMARY KEY,
                project_root TEXT NOT NULL,
                goal TEXT NOT NULL,
                goal_source TEXT NOT NULL DEFAULT '',
                permitted_paths_json TEXT NOT NULL,
                acceptance_check_json TEXT NOT NULL,
                runner_id TEXT NOT NULL DEFAULT '',
                model_id TEXT NOT NULL DEFAULT '',
                execution_target TEXT NOT NULL DEFAULT 'in-process',
                trust_mode TEXT NOT NULL DEFAULT 'default',
                mode TEXT NOT NULL DEFAULT 'write',
                check_timeout INTEGER NOT NULL DEFAULT 300,
                state TEXT NOT NULL DEFAULT 'pending'
                    CHECK (state IN ('pending', 'claimed', 'done', 'failed')),
                case_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_goals_pending "
            "ON product_goals(project_root, state, created_at)"
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _uuid(self) -> str:
        return str(uuid.uuid4())

    def _project_from_row(self, row: sqlite3.Row) -> Project:
        return Project(
            id=row["id"],
            root_uri=row["root_uri"],
            trust_mode=row["trust_mode"],
            policy_json=row["policy_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _conversation_from_row(self, row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _run_from_row(self, row: sqlite3.Row) -> Run:
        return Run(
            id=row["id"],
            conversation_id=row["conversation_id"],
            runner_id=row["runner_id"],
            model_id=row["model_id"],
            execution_target=row["execution_target"],
            mode=row["mode"],
            idempotency_key=row["idempotency_key"],
            prompt=row["prompt"] or "",
            state=RunState(row["state"]),
            workspace=row["workspace"],
            base_revision=row["base_revision"],
            requirements=row["requirements"] if "requirements" in row.keys() else None,  # noqa: SIM118 - sqlite3.Row needs .keys()
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _event_from_row(self, row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            run_id=row["run_id"],
            seq=row["seq"],
            type=row["type"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _command_from_row(self, row: sqlite3.Row) -> RunCommand:
        return RunCommand(
            id=row["id"],
            run_id=row["run_id"],
            seq=row["seq"],
            kind=CommandKind(row["kind"]),
            payload=json.loads(row["payload"] or "{}"),
            issuer=row["issuer"],
            consumed=bool(row["consumed"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _lease_from_row(self, row: sqlite3.Row) -> Lease:
        return Lease(
            resource=row["resource"],
            owner_id=row["owner_id"],
            fencing_token=row["fencing_token"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
            acquired_at=datetime.fromisoformat(row["acquired_at"]),
        )

    def _artifact_from_row(self, row: sqlite3.Row) -> Artifact:
        return Artifact(
            id=row["id"],
            run_id=row["run_id"],
            kind=row["kind"],
            sha256=row["sha256"],
            mime_type=row["mime_type"],
            size=row["size"],
            metadata=json.loads(row["metadata"] or "{}"),
            path=row["path"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _session_from_row(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            run_id=row["run_id"],
            conversation_id=row["conversation_id"],
            project_id=row["project_id"],
            cwd=row["cwd"],
            prompt=row["prompt"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _usage_from_row(self, row: sqlite3.Row) -> UsageRow:
        return UsageRow(
            run_id=row["run_id"],
            tokens=row["tokens"],
            cost=row["cost"],
            source=row["source"],
            confidence=row["confidence"],
            quota_class=row["quota_class"],
            model_family=row["model_family"],
            model_id=row["model_id"],
            vendor=row["vendor"],
            duration=row["duration"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _product_case_from_row(self, row: sqlite3.Row) -> ProductCase:
        return ProductCase(
            id=row["id"],
            project_root=row["project_root"],
            contract_json=row["contract_json"],
            contract_sha256=row["contract_sha256"],
            state=ProductCaseState(row["state"]),
            failure_owner=row["failure_owner"],
            friction=row["friction"],
            baseline_run_id=row["baseline_run_id"],
            improvement_run_id=row["improvement_run_id"],
            replay_run_id=row["replay_run_id"],
            baseline_outcome=row["baseline_outcome"],
            replay_outcome=row["replay_outcome"],
            independent_review=row["independent_review"],
            regression_passed=None if row["regression_passed"] is None else bool(row["regression_passed"]),
            human_accepted=None if row["human_accepted"] is None else bool(row["human_accepted"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _product_case_event_from_row(self, row: sqlite3.Row) -> ProductCaseEvent:
        return ProductCaseEvent(
            id=row["id"],
            product_case_id=row["product_case_id"],
            seq=row["seq"],
            type=row["type"],
            payload=json.loads(row["payload"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _same_request(
        self,
        run: Run,
        conversation_id: str,
        runner_id: str,
        model_id: str,
        execution_target: str,
        mode: str,
        idempotency_key: str,
        prompt: str,
        requirements: str | None = None,
    ) -> bool:
        return (
            run.conversation_id == conversation_id
            and run.runner_id == runner_id
            and run.model_id == model_id
            and run.execution_target == execution_target
            and run.mode == mode
            and run.idempotency_key == idempotency_key
            and run.prompt == prompt
            and (run.requirements or None) == (requirements or None)
        )

    def _next_fencing_token(self, resource: str) -> int:
        self._conn.execute(
            """
            INSERT INTO lease_counters(resource, value)
            VALUES (?, 1)
            ON CONFLICT(resource) DO UPDATE SET value = value + 1
            """,
            (resource,),
        )
        row = self._conn.execute(
            "SELECT value FROM lease_counters WHERE resource = ?", (resource,)
        ).fetchone()
        return row[0]

    def _validate_ttl(self, ttl_seconds: float) -> None:
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, (int, float))
            or not math.isfinite(ttl_seconds)
            or ttl_seconds <= 0
        ):
            raise ValueError("ttl_seconds must be a positive number")

    def _verify_lease(
        self,
        resource: str,
        owner_id: str,
        fencing_token: int,
        now: datetime,
    ) -> None:
        row = self._conn.execute(
            "SELECT owner_id, fencing_token, expires_at FROM leases WHERE resource = ?",
            (resource,),
        ).fetchone()
        if row is None:
            raise StaleLease
        if row["owner_id"] != owner_id or row["fencing_token"] != fencing_token:
            raise StaleLease
        if datetime.fromisoformat(row["expires_at"]) <= now:
            raise StaleLease

    def create_project(
        self, root_uri: str, trust_mode: str, policy_json: str | None = None
    ) -> Project:
        project_id = self._uuid()
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """
                    INSERT INTO projects(id, root_uri, trust_mode, policy_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (project_id, root_uri, trust_mode, policy_json, now),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Project:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Project {project_id!r} not found")
            return self._project_from_row(row)

    def set_project_policy(self, project_id: str, policy_json: str | None) -> Project:
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    "UPDATE projects SET policy_json = ? WHERE id = ?",
                    (policy_json, project_id),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_project(project_id)

    def get_project_by_root(self, root_uri: str) -> Project | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE root_uri = ?", (root_uri,)
            ).fetchone()
            if row is None:
                return None
            return self._project_from_row(row)

    def set_project_trust_mode(self, project_id: str, trust_mode: str) -> Project:
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    "UPDATE projects SET trust_mode = ?, created_at = created_at WHERE id = ?",
                    (trust_mode, project_id),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_project(project_id)

    def create_conversation(self, project_id: str, title: str) -> Conversation:
        conversation_id = self._uuid()
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """
                    INSERT INTO conversations(id, project_id, title, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (conversation_id, project_id, title, now),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> Conversation:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Conversation {conversation_id!r} not found")
            return self._conversation_from_row(row)

    def get_project_for_run(self, run_id: str) -> Project:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT p.* FROM projects p
                JOIN conversations c ON c.project_id = p.id
                JOIN runs r ON r.conversation_id = c.id
                WHERE r.id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"No project found for run {run_id!r}")
            return self._project_from_row(row)

    def _find_run_by_idempotency(self, conversation_id: str, idempotency_key: str) -> Run | None:
        row = self._conn.execute(
            "SELECT * FROM runs WHERE conversation_id = ? AND idempotency_key = ?",
            (conversation_id, idempotency_key),
        ).fetchone()
        return self._run_from_row(row) if row else None

    def create_run(
        self,
        conversation_id: str,
        runner_id: str,
        model_id: str,
        execution_target: str,
        mode: str,
        idempotency_key: str,
        prompt: str = "",
        requirements: str | None = None,
    ) -> Run:
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                existing_row = self._conn.execute(
                    "SELECT * FROM runs WHERE conversation_id = ? AND idempotency_key = ?",
                    (conversation_id, idempotency_key),
                ).fetchone()
                if existing_row:
                    existing = self._run_from_row(existing_row)
                    if self._same_request(
                        existing,
                        conversation_id,
                        runner_id,
                        model_id,
                        execution_target,
                        mode,
                        idempotency_key,
                        prompt,
                        requirements,
                    ):
                        self._conn.rollback()
                        return existing
                    self._conn.rollback()
                    raise IdempotencyConflict(
                        f"Idempotency conflict for conversation {conversation_id!r} "
                        f"and key {idempotency_key!r}"
                    )

                run_id = self._uuid()
                now = self._now()
                if self._has_column("runs", "requirements"):
                    self._conn.execute(
                        """
                        INSERT INTO runs(
                            id, conversation_id, runner_id, model_id, execution_target,
                            mode, idempotency_key, prompt, state, workspace, requirements,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            conversation_id,
                            runner_id,
                            model_id,
                            execution_target,
                            mode,
                            idempotency_key,
                            prompt,
                            RunState.CREATED.value,
                            None,
                            requirements,
                            now,
                            now,
                        ),
                    )
                else:
                    self._conn.execute(
                        """
                        INSERT INTO runs(
                            id, conversation_id, runner_id, model_id, execution_target,
                            mode, idempotency_key, prompt, state, workspace,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            conversation_id,
                            runner_id,
                            model_id,
                            execution_target,
                            mode,
                            idempotency_key,
                            prompt,
                            RunState.CREATED.value,
                            None,
                            now,
                            now,
                        ),
                    )
                self._conn.execute(
                    """
                    INSERT INTO events(id, run_id, seq, type, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (self._uuid(), run_id, 1, "run.created", json.dumps({}), now),
                )
                self._conn.commit()
                row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
                return self._run_from_row(row)
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                existing = self._find_run_by_idempotency(conversation_id, idempotency_key)
                if existing is None:
                    raise
                if self._same_request(
                    existing,
                    conversation_id,
                    runner_id,
                    model_id,
                    execution_target,
                    mode,
                    idempotency_key,
                    prompt,
                    requirements,
                ):
                    return existing
                raise IdempotencyConflict(
                    f"Idempotency conflict for conversation {conversation_id!r} "
                    f"and key {idempotency_key!r}"
                ) from exc
            except Exception:
                self._conn.rollback()
                raise

    def get_run(self, run_id: str) -> Run:
        with self._lock:
            row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise ValueError(f"Run {run_id!r} not found")
            return self._run_from_row(row)

    def list_runs(self, conversation_id: str | None = None) -> list[Run]:
        with self._lock:
            if conversation_id is None:
                rows = self._conn.execute(
                    "SELECT * FROM runs ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM runs WHERE conversation_id = ? ORDER BY created_at DESC",
                    (conversation_id,),
                ).fetchall()
            return [self._run_from_row(row) for row in rows]

    def set_run_workspace(
        self,
        run_id: str,
        workspace: str | None = None,
        base_revision: str | None = None,
        owner_id: str | None = None,
        fencing_token: int | None = None,
    ) -> Run:
        now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if owner_id is not None and fencing_token is not None:
                    self._verify_lease(f"run:{run_id}", owner_id, fencing_token, now)
                self._conn.execute(
                    "UPDATE runs SET workspace = ?, base_revision = ?, updated_at = ? WHERE id = ?",
                    (workspace, base_revision, now.isoformat(), run_id),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_run(run_id)

    def recover_abandoned_runs(
        self,
        threshold_seconds: float = 300.0,
        event_type: str = "recovery.crash",
        now: datetime | None = None,
    ) -> list[str]:
        """Transition stale active runs to FAILED and clean up their leases.

        A run is considered abandoned when it is in an active state and its
        `updated_at` is older than ``threshold_seconds``.  This is used by the
        dispatcher on startup to recover from a previous crash.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=threshold_seconds)
        active_states = {
            RunState.PREPARING.value,
            RunState.RUNNING.value,
            RunState.VERIFYING.value,
        }
        recovered: list[str] = []

        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                rows = self._conn.execute(
                    """
                    SELECT r.id, r.workspace, r.updated_at FROM runs r
                    WHERE r.state IN (?, ?, ?)
                    AND NOT EXISTS (
                        SELECT 1 FROM leases l
                        WHERE l.resource = 'run:' || r.id
                        AND l.expires_at > ?
                    )
                    """,
                    (*active_states, now.isoformat()),
                ).fetchall()

                for row in rows:
                    if datetime.fromisoformat(row["updated_at"]) > cutoff:
                        continue

                    run_id = row["id"]
                    self._conn.execute(
                        "UPDATE runs SET state = ?, updated_at = ? WHERE id = ?",
                        (RunState.FAILED.value, now.isoformat(), run_id),
                    )

                    next_seq = self._conn.execute(
                        "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?",
                        (run_id,),
                    ).fetchone()[0]

                    self._conn.execute(
                        """
                        INSERT INTO events(id, run_id, seq, type, payload, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            self._uuid(),
                            run_id,
                            next_seq,
                            event_type,
                            json.dumps(
                                {
                                    "reason": "abandoned",
                                    "threshold_seconds": threshold_seconds,
                                    "updated_at": row["updated_at"],
                                }
                            ),
                            now.isoformat(),
                        ),
                    )

                    # Remove stale run and workspace leases so new dispatchers can
                    # re-acquire the workspace.
                    self._conn.execute(
                        "DELETE FROM leases WHERE resource = ?",
                        (f"run:{run_id}",),
                    )
                    if row["workspace"]:
                        self._conn.execute(
                            "DELETE FROM leases WHERE resource = ?",
                            (f"workspace:{row['workspace']}",),
                        )

                    recovered.append(run_id)

                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

        return recovered

    def list_events(self, run_id: str, after_seq: int = 0) -> list[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE run_id = ? AND seq > ? ORDER BY seq",
                (run_id, after_seq),
            ).fetchall()
            return [self._event_from_row(row) for row in rows]

    def transition_run(
        self,
        run_id: str,
        new_state: RunState,
        event_type: str,
        payload: dict | None = None,
        owner_id: str | None = None,
        fencing_token: int | None = None,
    ) -> Run:
        payload = payload or {}
        now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if owner_id is not None and fencing_token is not None:
                    self._verify_lease(f"run:{run_id}", owner_id, fencing_token, now)
                row = self._conn.execute(
                    "SELECT state FROM runs WHERE id = ?", (run_id,)
                ).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise ValueError(f"Run {run_id!r} not found")
                current_state = RunState(row["state"])
                if new_state not in self._TRANSITIONS.get(current_state, set()):
                    self._conn.rollback()
                    raise InvalidRunTransition(
                        f"Cannot transition run {run_id} from {current_state.value} "
                        f"to {new_state.value}"
                    )

                now_str = now.isoformat()
                next_seq = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
                self._conn.execute(
                    "UPDATE runs SET state = ?, updated_at = ? WHERE id = ?",
                    (new_state.value, now_str, run_id),
                )
                self._conn.execute(
                    """
                    INSERT INTO events(id, run_id, seq, type, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (self._uuid(), run_id, next_seq, event_type, json.dumps(payload), now_str),
                )
                self._conn.commit()
                row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
                return self._run_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict | None = None,
        owner_id: str | None = None,
        fencing_token: int | None = None,
    ) -> Event:
        payload = payload or {}
        now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if owner_id is not None and fencing_token is not None:
                    self._verify_lease(f"run:{run_id}", owner_id, fencing_token, now)
                row = self._conn.execute(
                    "SELECT state FROM runs WHERE id = ?", (run_id,)
                ).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise ValueError(f"Run {run_id!r} not found")
                next_seq = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
                event_id = self._uuid()
                now_str = now.isoformat()
                self._conn.execute(
                    """
                    INSERT INTO events(id, run_id, seq, type, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, run_id, next_seq, event_type, json.dumps(payload), now_str),
                )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM events WHERE id = ?", (event_id,)
                ).fetchone()
                return self._event_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def enqueue_command(
        self,
        run_id: str,
        kind: CommandKind,
        payload: dict | None = None,
        issuer: str = "system",
    ) -> RunCommand:
        payload = payload or {}
        if not isinstance(kind, CommandKind):
            kind = CommandKind(kind)
        command_id = self._uuid()
        now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise ValueError(f"Run {run_id!r} not found")
                next_seq = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM commands WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
                self._conn.execute(
                    """
                    INSERT INTO commands(
                        id, run_id, seq, kind, payload, issuer, consumed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        command_id,
                        run_id,
                        next_seq,
                        kind.value,
                        json.dumps(payload),
                        issuer,
                        0,
                        now.isoformat(),
                    ),
                )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM commands WHERE id = ?", (command_id,)
                ).fetchone()
                return self._command_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def list_commands(
        self,
        run_id: str,
        after_seq: int = 0,
        include_consumed: bool = True,
    ) -> list[RunCommand]:
        with self._lock:
            if include_consumed:
                rows = self._conn.execute(
                    "SELECT * FROM commands WHERE run_id = ? AND seq > ? ORDER BY seq",
                    (run_id, after_seq),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT * FROM commands
                    WHERE run_id = ? AND seq > ? AND consumed = 0
                    ORDER BY seq
                    """,
                    (run_id, after_seq),
                ).fetchall()
            return [self._command_from_row(row) for row in rows]

    def consume_command(
        self,
        command_id: str,
        owner_id: str,
        fencing_token: int,
        now: datetime | None = None,
    ) -> RunCommand:
        if now is None:
            now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                cmd_row = self._conn.execute(
                    "SELECT run_id, consumed FROM commands WHERE id = ?", (command_id,)
                ).fetchone()
                if cmd_row is None:
                    self._conn.rollback()
                    raise ValueError(f"Command {command_id!r} not found")
                self._verify_lease(f"run:{cmd_row['run_id']}", owner_id, fencing_token, now)
                if not cmd_row["consumed"]:
                    self._conn.execute(
                        "UPDATE commands SET consumed = 1 WHERE id = ? AND consumed = 0",
                        (command_id,),
                    )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM commands WHERE id = ?", (command_id,)
                ).fetchone()
                return self._command_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def acquire_lease(
        self,
        resource: str,
        owner_id: str,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> Lease:
        self._validate_ttl(ttl_seconds)
        if now is None:
            now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT * FROM leases WHERE resource = ?", (resource,)
                ).fetchone()
                if row is not None:
                    expires = datetime.fromisoformat(row["expires_at"])
                    if expires > now:
                        self._conn.rollback()
                        raise LeaseConflict
                    self._conn.execute("DELETE FROM leases WHERE resource = ?", (resource,))
                token = self._next_fencing_token(resource)
                expires_at = now + timedelta(seconds=ttl_seconds)
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO leases(
                        resource, owner_id, fencing_token, expires_at, acquired_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        resource,
                        owner_id,
                        token,
                        expires_at.isoformat(),
                        now.isoformat(),
                    ),
                )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM leases WHERE resource = ?", (resource,)
                ).fetchone()
                return self._lease_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def renew_lease(
        self,
        resource: str,
        owner_id: str,
        fencing_token: int,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> Lease:
        self._validate_ttl(ttl_seconds)
        if now is None:
            now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT * FROM leases WHERE resource = ?", (resource,)
                ).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise StaleLease
                self._verify_lease(resource, owner_id, fencing_token, now)
                expires_at = now + timedelta(seconds=ttl_seconds)
                self._conn.execute(
                    "UPDATE leases SET expires_at = ? WHERE resource = ?",
                    (expires_at.isoformat(), resource),
                )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM leases WHERE resource = ?", (resource,)
                ).fetchone()
                return self._lease_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def release_lease(
        self,
        resource: str,
        owner_id: str,
        fencing_token: int,
        now: datetime | None = None,
    ) -> None:
        if now is None:
            now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT * FROM leases WHERE resource = ?", (resource,)
                ).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise StaleLease
                self._verify_lease(resource, owner_id, fencing_token, now)
                self._conn.execute("DELETE FROM leases WHERE resource = ?", (resource,))
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def get_lease(self, resource: str) -> Lease | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM leases WHERE resource = ?", (resource,)
            ).fetchone()
            if row is None:
                return None
            if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
                return None
            return self._lease_from_row(row)

    def record_artifact(
        self,
        run_id: str,
        kind: str,
        sha256: str,
        mime_type: str,
        size: int,
        metadata: dict | None = None,
        path: str | None = None,
    ) -> Artifact:
        now = datetime.now(timezone.utc)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise ValueError(f"Run {run_id!r} not found")
                metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
                existing = self._conn.execute(
                    "SELECT * FROM artifacts WHERE run_id = ? AND kind = ? AND sha256 = ?",
                    (run_id, kind, sha256),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["mime_type"] != mime_type
                        or existing["size"] != size
                        or existing["path"] != path
                        or (existing["metadata"] or "{}") != metadata_json
                    ):
                        raise ArtifactConflict(
                            f"Artifact conflict for run {run_id!r} kind {kind!r} sha256 {sha256!r}"
                        )
                    self._conn.rollback()
                    return self._artifact_from_row(existing)
                artifact_id = self._uuid()
                self._conn.execute(
                    """
                    INSERT INTO artifacts(
                        id, run_id, kind, sha256, mime_type, size, metadata, path, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        run_id,
                        kind,
                        sha256,
                        mime_type,
                        size,
                        metadata_json,
                        path,
                        now.isoformat(),
                    ),
                )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
                ).fetchone()
                return self._artifact_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def get_artifact(self, artifact_id: str) -> Artifact:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Artifact {artifact_id!r} not found")
            return self._artifact_from_row(row)

    def list_artifacts(self, run_id: str) -> list[Artifact]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM artifacts
                WHERE run_id = ?
                ORDER BY created_at
                """,
                (run_id,),
            ).fetchall()
            return [self._artifact_from_row(row) for row in rows]

    def record_usage(
        self,
        run_id: str,
        tokens: int | None,
        cost: float | None,
        source: str,
        confidence: str,
        quota_class: str,
        model_family: str,
        model_id: str,
        vendor: str,
        duration: float,
    ) -> UsageRow:
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT 1 FROM runs WHERE id = ?", (run_id,)
                ).fetchone()
                if row is None:
                    self._conn.rollback()
                    raise ValueError(f"Run {run_id!r} not found")
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO usage(
                        run_id, tokens, cost, source, confidence, quota_class,
                        model_family, model_id, vendor, duration, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        tokens,
                        cost,
                        source,
                        confidence,
                        quota_class,
                        model_family,
                        model_id,
                        vendor,
                        duration,
                        now,
                    ),
                )
                self._conn.commit()
                row = self._conn.execute(
                    "SELECT * FROM usage WHERE run_id = ?", (run_id,)
                ).fetchone()
                return self._usage_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def get_usage(self, run_id: str) -> UsageRow | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM usage WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                return None
            return self._usage_from_row(row)

    def create_session(
        self,
        session_id: str,
        run_id: str,
        conversation_id: str,
        project_id: str,
        cwd: str | None = None,
        prompt: str = "",
    ) -> Session:
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """
                    INSERT INTO sessions(
                        id, run_id, conversation_id, project_id, cwd, prompt, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, run_id, conversation_id, project_id, cwd, prompt, now, now),
                )
                self._conn.commit()
                row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                return self._session_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def get_session(self, session_id: str) -> Session:
        with self._lock:
            row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise ValueError(f"Session {session_id!r} not found")
            return self._session_from_row(row)

    def list_sessions(self) -> list[Session]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            return [self._session_from_row(row) for row in rows]

    def update_session(self, session_id: str, **kwargs: Any) -> Session:
        allowed = {"run_id", "conversation_id", "project_id", "cwd", "prompt"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            raise ValueError("No valid fields provided for session update")
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                values = list(updates.values()) + [now, session_id]
                self._conn.execute(
                    f"UPDATE sessions SET {set_clause}, updated_at = ? WHERE id = ?",
                    values,
                )
                self._conn.commit()
                row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row is None:
                    raise ValueError(f"Session {session_id!r} not found")
                return self._session_from_row(row)
            except Exception:
                self._conn.rollback()
                raise

    def _canonical_project_root(self, path: str) -> str:
        if not isinstance(path, str) or not path.strip() or "\x00" in path:
            raise ValueError("project_root must be a nonblank, NUL-free string")
        try:
            return str(Path(path.strip()).expanduser().resolve(strict=False))
        except Exception as exc:
            raise ValueError(f"project_root is not a valid path: {exc}") from exc

    def _validate_permitted_paths(self, paths: Any) -> list[str]:
        if not isinstance(paths, list):
            raise InvalidProductCaseContract("permitted_paths must be a list")
        normalized_paths = []
        seen = set()
        for value in paths:
            if not isinstance(value, str) or not value.strip():
                raise InvalidProductCaseContract("permitted path must be a nonblank string")
            if value != value.strip():
                raise InvalidProductCaseContract("permitted path must not have surrounding whitespace")
            if "\x00" in value or "\\" in value:
                raise InvalidProductCaseContract("permitted path contains an invalid character")
            if re.match(r"^[A-Za-z]:", value):
                raise InvalidProductCaseContract("permitted path has a drive prefix")
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts:
                raise InvalidProductCaseContract("permitted path must be relative and non-traversing")
            normalized = str(path)
            if normalized in {"", "."}:
                raise InvalidProductCaseContract("permitted path must identify a path")
            if normalized in seen:
                raise InvalidProductCaseContract("permitted_paths contains normalized duplicates")
            seen.add(normalized)
            normalized_paths.append(normalized)
        return normalized_paths

    def _validate_contract(self, contract: Any, case_root: str) -> tuple[str, str]:
        if isinstance(contract, str):
            try:
                obj = json.loads(contract, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise InvalidProductCaseContract("contract is not valid finite JSON") from exc
        elif isinstance(contract, dict):
            obj = contract
        else:
            raise InvalidProductCaseContract("contract must be a JSON string or dict")
        required = {
            "goal_source", "goal", "project_root", "base_revision", "permitted_paths",
            "acceptance_check", "human_acceptance_required",
        }
        if not isinstance(obj, dict) or set(obj) != required:
            raise InvalidProductCaseContract("contract has unknown or missing keys")
        for key in ("goal_source", "goal", "base_revision"):
            value = obj[key]
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise InvalidProductCaseContract(f"contract {key} must be a nonblank, NUL-free string")
        try:
            contract_root = self._canonical_project_root(obj["project_root"])
        except ValueError as exc:
            raise InvalidProductCaseContract(str(exc)) from exc
        if contract_root != case_root:
            raise InvalidProductCaseContract("contract project_root does not match case project_root")
        acceptance_check = obj["acceptance_check"]
        if not isinstance(acceptance_check, list) or not acceptance_check:
            raise InvalidProductCaseContract("acceptance_check must be a non-empty list")
        if any(not isinstance(arg, str) or not arg.strip() or "\x00" in arg for arg in acceptance_check):
            raise InvalidProductCaseContract("acceptance_check entries must be nonblank, NUL-free strings")
        if obj["human_acceptance_required"] is not True:
            raise InvalidProductCaseContract("human_acceptance_required must be true")
        normalized = dict(obj)
        normalized["project_root"] = contract_root
        normalized["permitted_paths"] = self._validate_permitted_paths(obj["permitted_paths"])
        try:
            canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidProductCaseContract("contract contains non-JSON or non-finite values") from exc
        return canonical, hashlib.sha256(canonical.encode()).hexdigest()

    def _validate_outcome(self, outcome: Any) -> tuple[str, dict[str, Any]]:
        if isinstance(outcome, str):
            try:
                obj = json.loads(outcome, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise InvalidProductCaseOutcome("outcome is not valid finite JSON") from exc
        elif isinstance(outcome, dict):
            obj = outcome
        else:
            raise InvalidProductCaseOutcome("outcome must be a JSON string or dict")
        required = {"contract_sha256", "verdict", "apply_eligible", "accepted", "human_interventions", "safety_violations"}
        if not isinstance(obj, dict) or set(obj) != required:
            raise InvalidProductCaseOutcome("outcome has unknown or missing keys")
        for key in ("contract_sha256", "verdict"):
            value = obj[key]
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise InvalidProductCaseOutcome(f"{key} must be a nonblank, NUL-free string")
        if type(obj["apply_eligible"]) is not bool or type(obj["accepted"]) is not bool:
            raise InvalidProductCaseOutcome("outcome eligibility fields must be bools")
        for key in ("human_interventions", "safety_violations"):
            if type(obj[key]) is not int or obj[key] < 0:
                raise InvalidProductCaseOutcome(f"{key} must be a nonnegative int")
        try:
            canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidProductCaseOutcome("outcome contains non-JSON or non-finite values") from exc
        return canonical, obj

    def _run_exists(self, run_id: str) -> bool:
        return self._conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone() is not None

    def _required_run_id(self, updates: dict[str, Any], key: str) -> str:
        if set(updates) != {key}:
            raise InvalidProductCaseUpdate(f"{key} is the only required update")
        run_id = updates[key]
        if not isinstance(run_id, str) or not run_id.strip() or "\x00" in run_id:
            raise InvalidProductCaseUpdate(f"{key} must be a nonblank, NUL-free string")
        if not self._run_exists(run_id):
            raise ProductCasePreconditionError(f"Run {run_id!r} not found")
        return run_id

    def _compute_product_case_transition(
        self,
        case: ProductCase,
        updates: dict[str, Any],
    ) -> tuple[ProductCaseState, dict[str, Any]]:
        terminal = {
            ProductCaseState.BASELINE_ACCEPTED,
            ProductCaseState.LIMITATION_RECORDED,
            ProductCaseState.RETAINED,
            ProductCaseState.REJECTED,
        }
        if case.state in terminal:
            raise InvalidProductCaseTransition(f"Cannot transition from terminal state {case.state.value}")
        if case.state is ProductCaseState.WAITING_FOR_GOAL:
            if set(updates) != {"contract"}:
                raise InvalidProductCaseUpdate("contract is the only required update")
            canonical, digest = self._validate_contract(updates["contract"], case.project_root)
            return ProductCaseState.CONTRACTED, {"contract_json": canonical, "contract_sha256": digest}
        if case.state is ProductCaseState.CONTRACTED:
            run_id = self._required_run_id(updates, "baseline_run_id")
            return ProductCaseState.BASELINE_RUNNING, {"baseline_run_id": run_id}
        if case.state is ProductCaseState.BASELINE_RUNNING:
            if set(updates) not in ({"baseline_outcome"}, {"baseline_outcome", "failure_owner", "friction"}):
                raise InvalidProductCaseUpdate("invalid baseline_running update shape")
            canonical, outcome = self._validate_outcome(updates["baseline_outcome"])
            if outcome["contract_sha256"] != case.contract_sha256:
                raise ProductCaseHashMismatch("baseline outcome contract hash does not match")
            qualifies = (
                outcome["accepted"] is True
                and outcome["verdict"] == "ok"
                and outcome["apply_eligible"] is True
                and outcome["safety_violations"] == 0
            )
            if set(updates) == {"baseline_outcome"}:
                if not qualifies:
                    raise ProductCasePreconditionError("baseline outcome does not qualify for acceptance")
                return ProductCaseState.BASELINE_ACCEPTED, {"baseline_outcome": canonical}
            if qualifies:
                raise ProductCasePreconditionError("accepted baseline cannot be classified as friction")
            owner = updates["failure_owner"]
            if owner not in {"PRODUCT", "MODEL", "ENVIRONMENT", "CONTRACT", "TASK", "HUMAN"}:
                raise InvalidProductCaseUpdate("invalid failure_owner")
            friction = updates["friction"]
            if not isinstance(friction, str) or not friction.strip() or "\x00" in friction:
                raise InvalidProductCaseUpdate("friction must be a nonblank, NUL-free string")
            return ProductCaseState.FRICTION_CLASSIFIED, {
                "baseline_outcome": canonical,
                "failure_owner": owner,
                "friction": friction,
            }
        if case.state is ProductCaseState.FRICTION_CLASSIFIED:
            if updates == {}:
                if case.failure_owner == "PRODUCT":
                    raise ProductCasePreconditionError("PRODUCT friction cannot be limitation-recorded")
                if case.failure_owner not in {"MODEL", "ENVIRONMENT", "CONTRACT", "TASK", "HUMAN"}:
                    raise ProductCasePreconditionError("limitation requires a non-PRODUCT failure owner")
                return ProductCaseState.LIMITATION_RECORDED, {}
            if case.failure_owner != "PRODUCT":
                raise ProductCasePreconditionError("improvement requires failure_owner PRODUCT")
            run_id = self._required_run_id(updates, "improvement_run_id")
            return ProductCaseState.IMPROVEMENT_RUNNING, {"improvement_run_id": run_id}
        if case.state is ProductCaseState.IMPROVEMENT_RUNNING:
            if set(updates) != {"independent_review", "regression_passed"}:
                raise InvalidProductCaseUpdate("review and regression result are required")
            if updates["independent_review"] != "SOUND" or updates["regression_passed"] is not True:
                raise ProductCasePreconditionError("review must be SOUND and regression must pass")
            return ProductCaseState.IMPROVEMENT_REVIEWED, dict(updates)
        if case.state is ProductCaseState.IMPROVEMENT_REVIEWED:
            run_id = self._required_run_id(updates, "replay_run_id")
            return ProductCaseState.REPLAY_RUNNING, {"replay_run_id": run_id}
        if case.state is ProductCaseState.REPLAY_RUNNING:
            if set(updates) not in (
                {"replay_outcome"},
                {"replay_outcome", "self_evolution_satisfied"},
            ):
                raise InvalidProductCaseUpdate("replay_outcome is the only required update")
            canonical, outcome = self._validate_outcome(updates["replay_outcome"])
            if outcome["contract_sha256"] != case.contract_sha256:
                raise ProductCaseHashMismatch("replay outcome contract hash does not match")
            satisfied = updates.get("self_evolution_satisfied") is True
            if outcome["verdict"] != "ok" or (
                not satisfied
                and (
                    outcome["apply_eligible"] is not True
                    or outcome["safety_violations"] != 0
                )
            ):
                raise ProductCasePreconditionError("replay outcome is not reviewable")
            return ProductCaseState.HUMAN_REVIEW, {"replay_outcome": canonical}
        if case.state is ProductCaseState.HUMAN_REVIEW:
            if set(updates) != {"human_accepted"} or type(updates["human_accepted"]) is not bool:
                raise InvalidProductCaseUpdate("human_accepted bool is the only required update")
            if updates["human_accepted"] is False:
                return ProductCaseState.REJECTED, {"human_accepted": False}
            if case.baseline_outcome is None or case.replay_outcome is None:
                raise ProductCasePreconditionError("both outcomes are required")
            if outcome_score(case.replay_outcome) <= outcome_score(case.baseline_outcome):
                raise ProductCasePreconditionError("replay score must strictly exceed baseline score")
            return ProductCaseState.RETAINED, {"human_accepted": True}
        raise InvalidProductCaseTransition(f"No transition from state {case.state.value}")

    def create_product_case(self, contract: Any = None, project_root: str = "") -> ProductCase:
        canonical_root = self._canonical_project_root(project_root)
        contract_json = None
        contract_sha256 = None
        state = ProductCaseState.WAITING_FOR_GOAL
        if contract is not None:
            contract_json, contract_sha256 = self._validate_contract(contract, canonical_root)
            state = ProductCaseState.CONTRACTED
        case_id = self._uuid()
        now = self._now()
        payload = {"project_root": canonical_root, "state": state.value}
        if contract_sha256 is not None:
            payload["contract_sha256"] = contract_sha256
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """
                    INSERT INTO product_cases(
                        id, project_root, contract_json, contract_sha256, state, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (case_id, canonical_root, contract_json, contract_sha256, state.value, now, now),
                )
                self._conn.execute(
                    """
                    INSERT INTO product_case_events(id, product_case_id, seq, type, payload, created_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                    """,
                    (
                        self._uuid(), case_id,
                        "product_case.contracted" if contract is not None else "product_case.created",
                        payload_json, now,
                    ),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                if (
                    getattr(exc, "sqlite_errorname", None) == "SQLITE_CONSTRAINT_UNIQUE"
                    and str(exc) == "UNIQUE constraint failed: product_cases.project_root"
                ):
                    raise ActiveProductCaseExists(
                        f"An active product case already exists for {canonical_root!r}"
                    ) from exc
                raise
            except Exception:
                self._conn.rollback()
                raise
        return self.get_product_case(case_id)

    def get_product_case(self, case_id: str) -> ProductCase:
        with self._lock:
            row = self._conn.execute("SELECT * FROM product_cases WHERE id = ?", (case_id,)).fetchone()
            if row is None:
                raise ProductCaseNotFound(f"Product case {case_id!r} not found")
            return self._product_case_from_row(row)

    def get_active_product_case(self, project_root: str | None = None) -> ProductCase | None:
        terminal = tuple(
            state.value
            for state in (
                ProductCaseState.BASELINE_ACCEPTED,
                ProductCaseState.LIMITATION_RECORDED,
                ProductCaseState.RETAINED,
                ProductCaseState.REJECTED,
            )
        )
        if project_root is not None:
            try:
                canonical_root = self._canonical_project_root(project_root)
            except ValueError:
                return None
            query = "SELECT * FROM product_cases WHERE project_root = ? AND state NOT IN (?, ?, ?, ?) LIMIT 1"
            params = (canonical_root, *terminal)
        else:
            query = "SELECT * FROM product_cases WHERE state NOT IN (?, ?, ?, ?) ORDER BY created_at DESC LIMIT 1"
            params = terminal
        with self._lock:
            row = self._conn.execute(query, params).fetchone()
            return None if row is None else self._product_case_from_row(row)

    def list_product_case_events(self, case_id: str) -> list[ProductCaseEvent]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM product_case_events WHERE product_case_id = ? ORDER BY seq",
                (case_id,),
            ).fetchall()
            return [self._product_case_event_from_row(row) for row in rows]

    def append_product_case_event(
        self,
        case_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> ProductCaseEvent:
        if not isinstance(event_type, str) or not event_type.strip() or "\x00" in event_type:
            raise InvalidProductCaseUpdate("event_type must be a nonblank, NUL-free string")
        if not isinstance(payload, dict):
            raise InvalidProductCaseUpdate("payload must be a dict")
        try:
            payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidProductCaseUpdate("payload is not finite JSON") from exc
        event_id = self._uuid()
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if self._conn.execute("SELECT 1 FROM product_cases WHERE id = ?", (case_id,)).fetchone() is None:
                    raise ProductCaseNotFound(f"Product case {case_id!r} not found")
                next_seq = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM product_case_events WHERE product_case_id = ?",
                    (case_id,),
                ).fetchone()[0]
                self._conn.execute(
                    """
                    INSERT INTO product_case_events(id, product_case_id, seq, type, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, case_id, next_seq, event_type, payload_json, now),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        with self._lock:
            row = self._conn.execute("SELECT * FROM product_case_events WHERE id = ?", (event_id,)).fetchone()
            return self._product_case_event_from_row(row)

    def transition_product_case(
        self,
        case_id: str,
        expected_state: ProductCaseState,
        updates: dict[str, Any],
    ) -> ProductCase:
        if not isinstance(expected_state, ProductCaseState):
            raise InvalidProductCaseTransition("expected_state must be a ProductCaseState")
        if not isinstance(updates, dict):
            raise InvalidProductCaseUpdate("updates must be a dict")
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute("SELECT * FROM product_cases WHERE id = ?", (case_id,)).fetchone()
                if row is None:
                    raise ProductCaseNotFound(f"Product case {case_id!r} not found")
                case = self._product_case_from_row(row)
                if case.state is not expected_state:
                    raise StaleProductCaseState(
                        f"Expected {expected_state.value}, found {case.state.value}"
                    )
                new_state, values = self._compute_product_case_transition(case, updates)
                try:
                    payload_json = json.dumps(
                        updates,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                except (TypeError, ValueError) as exc:
                    raise InvalidProductCaseUpdate("updates are not finite JSON") from exc
                now = self._now()
                assignments = ["state = ?", *(f"{key} = ?" for key in values), "updated_at = ?"]
                parameters = [new_state.value, *values.values(), now, case_id, expected_state.value]
                cursor = self._conn.execute(
                    f"UPDATE product_cases SET {', '.join(assignments)} WHERE id = ? AND state = ?",
                    parameters,
                )
                if cursor.rowcount != 1:
                    raise StaleProductCaseState
                next_seq = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM product_case_events WHERE product_case_id = ?",
                    (case_id,),
                ).fetchone()[0]
                self._conn.execute(
                    """
                    INSERT INTO product_case_events(id, product_case_id, seq, type, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._uuid(), case_id, next_seq,
                        f"product_case.{new_state.value}", payload_json, now,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_product_case(case_id)
    _GOAL_STATES: ClassVar[tuple[str, ...]] = ("pending", "claimed", "done", "failed")

    def _product_goal_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "project_root": row["project_root"],
            "goal": row["goal"],
            "goal_source": row["goal_source"],
            "permitted_paths": json.loads(row["permitted_paths_json"]),
            "acceptance_check": json.loads(row["acceptance_check_json"]),
            "runner_id": row["runner_id"],
            "model_id": row["model_id"],
            "execution_target": row["execution_target"],
            "trust_mode": row["trust_mode"],
            "mode": row["mode"],
            "check_timeout": row["check_timeout"],
            "state": row["state"],
            "case_id": row["case_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def enqueue_goal(
        self,
        project_root: str,
        goal: str,
        goal_source: str = "",
        permitted_paths: list[str] | None = None,
        acceptance_check: list[str] | None = None,
        runner_id: str = "",
        model_id: str = "",
        execution_target: str = "in-process",
        trust_mode: str = "default",
        mode: str = "write",
        check_timeout: int = 300,
    ) -> str:
        """Append a pending goal to the queue for `project_root`; returns its id."""
        canonical_root = self._canonical_project_root(project_root)
        if not isinstance(goal, str) or not goal.strip() or "\x00" in goal:
            raise ValueError("goal must be a nonblank, NUL-free string")
        if not isinstance(check_timeout, int) or isinstance(check_timeout, bool) or check_timeout <= 0:
            raise ValueError("check_timeout must be a positive int")
        paths_json = json.dumps(
            list(permitted_paths or []), separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        check_json = json.dumps(
            list(acceptance_check or []), separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        goal_id = self._uuid()
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """
                    INSERT INTO product_goals(
                        id, project_root, goal, goal_source, permitted_paths_json,
                        acceptance_check_json, runner_id, model_id, execution_target,
                        trust_mode, mode, check_timeout, state, case_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?, ?)
                    """,
                    (
                        goal_id, canonical_root, goal, goal_source, paths_json,
                        check_json, runner_id, model_id, execution_target,
                        trust_mode, mode, check_timeout, now, now,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return goal_id

    def claim_next_goal(self, project_root: str, case_id: str) -> dict[str, Any] | None:
        """Atomically flip the oldest pending goal for `project_root` to claimed.

        The select and the update run inside one IMMEDIATE transaction and the
        update is guarded on `state = 'pending'`, so two concurrent claimers
        cannot take the same goal.
        """
        try:
            canonical_root = self._canonical_project_root(project_root)
        except ValueError:
            return None
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    """
                    SELECT * FROM product_goals
                    WHERE project_root = ? AND state = 'pending'
                    ORDER BY created_at, id LIMIT 1
                    """,
                    (canonical_root,),
                ).fetchone()
                if row is None:
                    self._conn.rollback()
                    return None
                cursor = self._conn.execute(
                    """
                    UPDATE product_goals SET state = 'claimed', case_id = ?, updated_at = ?
                    WHERE id = ? AND state = 'pending'
                    """,
                    (case_id, now, row["id"]),
                )
                if cursor.rowcount != 1:
                    self._conn.rollback()
                    return None
                claimed = self._conn.execute(
                    "SELECT * FROM product_goals WHERE id = ?", (row["id"],)
                ).fetchone()
                goal = self._product_goal_from_row(claimed)
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        return goal

    def _set_goal_state(self, goal_id: str, state: str) -> None:
        now = self._now()
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    "UPDATE product_goals SET state = ?, updated_at = ? WHERE id = ?",
                    (state, now, goal_id),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def mark_goal_done(self, goal_id: str) -> None:
        """Mark a queued goal as successfully consumed."""
        self._set_goal_state(goal_id, "done")

    def mark_goal_failed(self, goal_id: str) -> None:
        """Mark a queued goal as failed so it is not claimed again."""
        self._set_goal_state(goal_id, "failed")

    def list_goals(self, state: str | None = None) -> list[dict[str, Any]]:
        """List queued goals, oldest first, optionally filtered by state."""
        if state is not None and state not in self._GOAL_STATES:
            raise ValueError(f"state must be one of {self._GOAL_STATES}")
        with self._lock:
            if state is None:
                rows = self._conn.execute(
                    "SELECT * FROM product_goals ORDER BY created_at, id"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM product_goals WHERE state = ? ORDER BY created_at, id",
                    (state,),
                ).fetchall()
            return [self._product_goal_from_row(row) for row in rows]
