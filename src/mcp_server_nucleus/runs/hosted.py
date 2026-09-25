"""Fake hosted execution target and in-memory event journal for S6-1."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Any

from .models import Run, RunState
from .reconciler import EventReconciler, ReconciliationError, ReconciliationResult
from .store import InvalidRunTransition, RunStore
from .targets import ExecutionTarget, TargetResult
from .verifiers import NoopVerifier
from .worker import RunWorker
from .workspace import WorkspaceResolver


@dataclass(frozen=True)
class JournalEvent:
    """A single record in an in-memory event journal.

    The ``checksum`` is the sha256 of the canonical JSON of the record
    without the ``checksum`` field itself.
    """

    seq: int
    run_id: str
    state: str
    payload: dict
    checksum: str


@dataclass
class EventJournal:
    """Append-only in-memory journal of events for a single run."""

    run_id: str
    _events: list[JournalEvent] = field(default_factory=list, init=False, repr=False)
    _next_seq: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def checksum_for(self, seq: int, run_id: str, state: str, payload: dict) -> str:
        """Return the canonical sha256 checksum for a record."""
        record = {
            "seq": seq,
            "run_id": run_id,
            "state": state,
            "payload": payload,
        }

        def _default(obj: Any) -> Any:
            from dataclasses import asdict, is_dataclass

            if is_dataclass(obj):
                return asdict(obj)
            return str(obj)

        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=_default)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def reserve_seq(self) -> int:
        """Reserve a sequence number without writing an event (simulates a lost frame)."""
        with self._lock:
            seq = self._next_seq
            self._next_seq += 1
            return seq

    def append(
        self,
        state: str,
        payload: dict,
        seq: int | None = None,
    ) -> JournalEvent:
        """Append an event and return it.

        If ``seq`` is provided the journal accepts it (used for fault injection);
        otherwise the next monotonic sequence number is used.
        """
        with self._lock:
            if seq is None:
                seq = self._next_seq
                self._next_seq += 1
            else:
                self._next_seq = max(self._next_seq, seq + 1)
            payload = copy.deepcopy(payload)
            event = JournalEvent(
                seq=seq,
                run_id=self.run_id,
                state=state,
                payload=payload,
                checksum=self.checksum_for(seq, self.run_id, state, payload),
            )
            self._events.append(event)
            return event

    def list_events(self) -> list[JournalEvent]:
        """Return a copy of the events in insertion order."""
        with self._lock:
            return list(self._events)

    def truncate_after(self, seq: int) -> None:
        """Remove every event with a sequence number greater than ``seq``."""
        with self._lock:
            self._events = [e for e in self._events if e.seq <= seq]


class _HostedStoreProxy:
    """Proxy that lets a ``RunWorker`` execute while streaming transitions to a journal.

    State transitions are validated against a local shadow state and forwarded to
    the ``FakeHostedWorker`` for journaling; other store operations delegate to the
    real ``RunStore``.
    """

    def __init__(self, store: RunStore, worker: "FakeHostedWorker") -> None:
        self._store = store
        self._worker = worker
        self._shadow_state: RunState | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)

    def get_run(self, run_id: str) -> Run:
        run = self._store.get_run(run_id)
        if self._shadow_state is not None:
            run = replace(run, state=self._shadow_state)
        return run

    def transition_run(
        self,
        run_id: str,
        new_state: RunState,
        event_type: str,
        payload: dict | None = None,
        owner_id: str | None = None,
        fencing_token: int | None = None,
    ) -> Run:
        if run_id != self._worker._run_id:
            return self._store.transition_run(
                run_id,
                new_state,
                event_type,
                payload,
                owner_id=owner_id,
                fencing_token=fencing_token,
            )
        current = self._shadow_state or self._store.get_run(run_id).state
        allowed = RunStore._TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise InvalidRunTransition(
                f"Cannot transition run {run_id} from {current.value} to {new_state.value}"
            )
        self._shadow_state = new_state
        self._worker._append_state_event(new_state.value, payload or {})
        run = self._store.get_run(run_id)
        return replace(run, state=new_state)


class FakeHostedWorker:
    """Wraps a ``RunWorker`` and journals each state transition.

    The worker runs in a background thread started by ``FakeHostedExecutionTarget``.
    Injectable faults simulate network/journal failures for the reconciler to handle.
    """

    def __init__(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        journal: EventJournal | None = None,
        workspace_resolver: WorkspaceResolver | None = None,
        faults: dict | None = None,
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._owner_id = owner_id
        self._journal = journal or EventJournal(run_id=run_id)
        self._proxy = _HostedStoreProxy(store, self)
        self._worker = RunWorker(
            self._proxy, run_id, owner_id, workspace_resolver=workspace_resolver
        )
        self._faults = faults or {}
        self._drop_remaining = self._int_fault("drop_next_frame")
        self._dup_remaining = self._int_fault("duplicate_next_frame")
        self._reorder_remaining = self._int_fault("reorder_frames")
        self._reorder_buffer: list[dict] = []
        self._truncate_after = self._faults.get("truncate_journal_after")
        self._disconnect_until: float | None = None
        disconnect_s = self._faults.get("disconnect_for_s")
        if disconnect_s is not None:
            self._disconnect_until = time.monotonic() + float(disconnect_s)
        self._lock = threading.Lock()

    def _int_fault(self, key: str) -> int:
        value = self._faults.get(key)
        if value is True:
            return 1
        if isinstance(value, int) and value > 0:
            return value
        return 0

    def execute(self, handler, verifiers: list | None = None) -> None:
        if verifiers is None:
            verifiers = [NoopVerifier()]
        self._worker.execute(handler, verifiers)

    def _append_state_event(self, state: str, payload: dict) -> JournalEvent | None:
        with self._lock:
            # Simulate a network partition: frames are produced but not journaled.
            if self._disconnect_until is not None and time.monotonic() < self._disconnect_until:
                self._journal.reserve_seq()
                return None

            # Buffer a burst of frames and later flush them in reverse order.
            if self._reorder_remaining > 0:
                self._reorder_remaining -= 1
                self._reorder_buffer.append({"state": state, "payload": payload})
                if self._reorder_remaining == 0:
                    self._flush_reorder_buffer()
                return None

            # Drop the next frame (reserve its sequence number so a gap is visible).
            if self._drop_remaining > 0:
                self._drop_remaining -= 1
                self._journal.reserve_seq()
                return None

            # Write the next frame twice with the same sequence number.
            if self._dup_remaining > 0:
                self._dup_remaining -= 1
                event = self._journal.append(state, payload)
                self._journal.append(state, payload, seq=event.seq)
                return event

            event = self._journal.append(state, payload)

            # Simulate a journal crash by truncating everything after a sequence number.
            if self._truncate_after is not None and event.seq > self._truncate_after:
                self._journal.truncate_after(self._truncate_after)

            return event

    def _flush_reorder_buffer(self) -> None:
        n = len(self._reorder_buffer)
        for i, ev in enumerate(reversed(self._reorder_buffer)):
            seq = n - 1 - i
            self._journal.append(ev["state"], ev["payload"], seq=seq)
            if i < n - 1:
                time.sleep(0.02)
        self._reorder_buffer = []


class FakeHostedExecutionTarget:
    """Runs a worker in a background thread and reconciles its event journal."""

    def __init__(
        self,
        reconcile_timeout_s: float = 300.0,
        faults: dict | None = None,
    ) -> None:
        self._reconcile_timeout_s = reconcile_timeout_s
        self._faults = faults or {}

    def run(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        handler_factory,
        verifiers: list | None = None,
        wait: bool = True,
    ) -> TargetResult:
        journal = EventJournal(run_id=run_id)
        worker = FakeHostedWorker(
            store,
            run_id,
            owner_id,
            journal=journal,
            workspace_resolver=WorkspaceResolver(),
            faults=self._faults,
        )
        handler = handler_factory()
        thread = threading.Thread(
            target=worker.execute,
            args=(handler, verifiers),
            name=f"fake-hosted-worker-{run_id}",
            daemon=True,
        )
        thread.start()
        try:
            reconciler = EventReconciler(journal, store)
            result = reconciler.reconcile(run_id, timeout_s=self._reconcile_timeout_s)
        except ReconciliationError as exc:
            return TargetResult(False, error=str(exc))
        finally:
            thread.join(timeout=1.0)

        success = result.success and result.state in {
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.APPLIED,
            RunState.DISMISSED,
        }
        return TargetResult(success=success, state=result.state, error=result.error)


class HostedWorkerExecutionTarget:
    """Real hosted worker target; falls back to WORKSPACE_UNAVAILABLE without config."""

    def _admit(self, store: RunStore, run_id: str) -> None:
        """Walk the run through admission states up to PREPARING."""
        run = store.get_run(run_id)
        if run.state is RunState.CREATED:
            store.transition_run(run_id, RunState.QUEUED, "run.queued")
            run = store.get_run(run_id)
        if run.state is RunState.QUEUED:
            store.transition_run(run_id, RunState.PREPARING, "run.preparing")

    def _fail(
        self,
        store: RunStore,
        run_id: str,
        message: str,
        provider: str = "",
    ) -> TargetResult:
        self._admit(store, run_id)
        payload = {
            "error_type": "WorkspaceUnavailable",
            "message": message,
            "phase": "provider_admission",
        }
        if provider:
            payload["provider"] = provider
        store.transition_run(run_id, RunState.FAILED, "run.failed", payload=payload)
        return TargetResult(
            success=False,
            state=RunState.FAILED,
            error=f"WORKSPACE_UNAVAILABLE: {message}",
        )

    def run(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        handler_factory,
        verifiers: list | None = None,
        wait: bool = True,
    ) -> TargetResult:
        provider = os.environ.get("NUCLEUS_HOSTED_PROVIDER", "").strip().lower()

        if provider == "fake":
            return FakeHostedExecutionTarget().run(
                store,
                run_id,
                owner_id,
                handler_factory,
                verifiers=verifiers,
                wait=wait,
            )

        if not provider:
            return self._fail(
                store,
                run_id,
                "No hosted provider configured (set NUCLEUS_HOSTED_PROVIDER).",
            )

        # Real provider not yet implemented.
        return self._fail(
            store,
            run_id,
            f"Hosted provider {provider!r} is not yet supported.",
            provider=provider,
        )


# FakeHostedExecutionTarget implements the ExecutionTarget protocol.
