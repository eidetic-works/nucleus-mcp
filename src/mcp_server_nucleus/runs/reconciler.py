"""Event journal reconciler for the fake hosted execution target."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import RunState
from .store import RunStore

if TYPE_CHECKING:
    from .hosted import EventJournal


class ReconciliationError(Exception):
    """Raised when the event journal cannot be reconciled."""


@dataclass
class ReconciliationResult:
    """Outcome of a reconcile pass."""

    success: bool
    state: RunState | None = None
    error: str | None = None


class EventReconciler:
    """Reads a hosted event journal and applies state transitions to the store.

    The reconciler waits for the next expected sequence number, validates checksums,
    deduplicates repeated sequence numbers, and fails the run when a permanent
    sequence gap is detected.
    """

    _TERMINAL_STATES = frozenset(
        {
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
            RunState.DISMISSED,
            RunState.APPLIED,
        }
    )
    _POLL_INTERVAL = 0.05

    def __init__(self, journal: "EventJournal", store: RunStore) -> None:
        self._journal = journal
        self._store = store
        self._checksums: dict[int, str] = {}

    @staticmethod
    def _run_state_values() -> set[str]:
        return {s.value for s in RunState}

    def _force_terminal(
        self,
        run_id: str,
        target: RunState,
        final_payload: dict,
    ) -> None:
        """Find a valid transition path to ``target`` and apply it.

        This is used when the journal itself is too broken to apply the
        remaining events; the reconciler must still be able to mark the run
        terminal (for example, FAILED due to a sequence gap).
        """
        run = self._store.get_run(run_id)
        if run.state == target:
            return

        queue: deque[list[RunState]] = deque([[run.state]])
        seen = {run.state}
        while queue:
            path = queue.popleft()
            current = path[-1]
            if current == target:
                # Walk the intermediate states with a bridge payload, then
                # apply the final target transition with the intended payload.
                for state in path[1:-1]:
                    self._store.transition_run(
                        run_id,
                        state,
                        f"run.{state.value}",
                        payload={"phase": "reconcile_bridge"},
                    )
                self._store.transition_run(
                    run_id,
                    target,
                    f"run.{target.value}",
                    payload=final_payload,
                )
                return
            for nxt in RunStore._TRANSITIONS.get(current, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(path + [nxt])
        raise ReconciliationError(f"no transition path from {run.state} to {target}")

    def _verify(self, event) -> None:
        expected = self._journal.checksum_for(
            event.seq, event.run_id, event.state, event.payload
        )
        if event.checksum != expected:
            raise ReconciliationError(
                f"checksum mismatch at seq {event.seq}: expected {expected}, got {event.checksum}"
            )

    def reconcile(self, run_id: str, timeout_s: float = 300.0) -> ReconciliationResult:
        """Replay journal events into ``store`` until the run is terminal or a fault is found."""
        start = time.monotonic()
        expected_seq = 0

        while True:
            events = self._journal.list_events()

            # Validate any late arrivals for sequences we already passed.  Duplicates
            # of already-processed events must have the same checksum, otherwise the
            # journal has been tampered with.
            for ev in events:
                if ev.seq < expected_seq:
                    self._verify(ev)
                    recorded = self._checksums.get(ev.seq)
                    if recorded is not None and ev.checksum != recorded:
                        raise ReconciliationError(
                            f"duplicate seq {ev.seq} with differing payload"
                        )

            matching = [ev for ev in events if ev.seq == expected_seq]

            if not matching:
                if time.monotonic() - start >= timeout_s:
                    try:
                        self._force_terminal(
                            run_id,
                            RunState.FAILED,
                            {"reason": "sequence_gap", "expected_seq": expected_seq},
                        )
                    except Exception as exc:
                        # The run may already be terminal; return its actual state.
                        run = self._store.get_run(run_id)
                        return ReconciliationResult(
                            False, state=run.state, error=f"sequence_gap: {exc}"
                        )
                    run = self._store.get_run(run_id)
                    return ReconciliationResult(False, state=run.state, error="sequence_gap")

                time.sleep(self._POLL_INTERVAL)
                continue

            if len(matching) > 1:
                checksums = {ev.checksum for ev in matching}
                if len(checksums) > 1:
                    raise ReconciliationError(
                        f"conflicting duplicates for seq {expected_seq}"
                    )
                # Identical duplicates: use the first and ignore the rest.

            event = matching[0]
            self._verify(event)
            self._checksums[event.seq] = event.checksum

            if event.state in self._run_state_values():
                self._store.transition_run(
                    run_id,
                    RunState(event.state),
                    f"run.{event.state}",
                    payload=event.payload,
                )

            run = self._store.get_run(run_id)
            if run.state in self._TERMINAL_STATES:
                return ReconciliationResult(True, state=run.state)

            expected_seq += 1
