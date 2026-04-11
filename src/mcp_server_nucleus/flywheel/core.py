"""Flywheel core — the 6-action accountability helper + CSR bookkeeping.

The "6 actions" per failure are feedback_nucleus_accountability.md made
mechanical:
    1. Memory note (markdown in .brain/flywheel/pending_issues.jsonl)
    2. CSR bump (unsurvived)
    3. Training pair seed (append to unified_dpo_pending.jsonl)
    4. Weekly report append (week-N.md)
    5. GitHub issue fallback (attempted, stored for later if gh unavailable)
    6. Task registration fallback (.brain/flywheel/pending_tasks.jsonl)

All six are best-effort and idempotent. A ticket that can't hit GitHub
(offline, no auth) still writes the other five actions so the loop keeps
turning when network comes back.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .csr import bump_survived, bump_unsurvived, read_csr, _ensure_flywheel_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_brain_path() -> Path:
    """Resolve brain path from env or fall back to cwd/.brain."""
    env = os.environ.get("NUCLEUS_BRAIN_PATH")
    if env:
        return Path(env)
    return Path.cwd() / ".brain"


def _week_index(when: Optional[datetime] = None) -> int:
    """Return ISO week number. Used to name weekly report files."""
    when = when or datetime.now(timezone.utc)
    return when.isocalendar()[1]


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


class Flywheel:
    """The compounding loop engine.

    Instantiate once per process. Pass an explicit brain_path for tests;
    production callers can let it auto-resolve from env.
    """

    def __init__(self, brain_path: Optional[Path] = None) -> None:
        self.brain_path = Path(brain_path) if brain_path else _default_brain_path()
        _ensure_flywheel_dir(self.brain_path)

    # ── CSR ────────────────────────────────────────────────────────────────

    def record_survived(self, phase: str = "unknown", step: str = "") -> Dict[str, Any]:
        """Bump CSR for a survived claim. Returns updated state."""
        label = f"{phase}:{step}" if step else phase
        return bump_survived(self.brain_path, step=label)

    def csr(self) -> Dict[str, Any]:
        """Read current CSR state."""
        return read_csr(self.brain_path)

    # ── Tickets ────────────────────────────────────────────────────────────

    def file_ticket(
        self,
        step: str,
        error: str,
        logs: str = "",
        phase: str = "",
    ) -> Dict[str, Any]:
        """The 6-action accountability helper.

        Returns a dict summarizing which actions fired. All actions are
        best-effort; one failing does not block the others.
        """
        when = _now_iso()
        fw_dir = _ensure_flywheel_dir(self.brain_path)
        report: Dict[str, Any] = {
            "ticket_id": f"fw-{int(datetime.now(timezone.utc).timestamp())}",
            "at": when,
            "step": step,
            "phase": phase,
            "actions": {},
        }

        # Action 1 — Memory note in pending_issues.jsonl
        try:
            _append_jsonl(
                fw_dir / "pending_issues.jsonl",
                {
                    "ticket_id": report["ticket_id"],
                    "at": when,
                    "step": step,
                    "phase": phase,
                    "error": error,
                    "logs": logs[:2000],  # cap payload
                },
            )
            report["actions"]["memory_note"] = "ok"
        except Exception as e:  # noqa: BLE001
            report["actions"]["memory_note"] = f"error: {e}"

        # Action 2 — CSR bump (unsurvived)
        try:
            bump_unsurvived(self.brain_path, step=step, reason=error[:200])
            report["actions"]["csr_bump"] = "ok"
        except Exception as e:  # noqa: BLE001
            report["actions"]["csr_bump"] = f"error: {e}"

        # Action 3 — Training pair seed (DPO: rejected=error, chosen=pending fix)
        try:
            training_dir = self.brain_path / "training" / "exports"
            training_dir.mkdir(parents=True, exist_ok=True)
            pair = {
                "source": "flywheel_ticket",
                "quality": "pending",
                "prompt": f"Step: {step}\nPhase: {phase}",
                "rejected": error,
                "chosen": "",  # filled in by curriculum_refresh when fix lands
                "ticket_id": report["ticket_id"],
                "at": when,
            }
            _append_jsonl(training_dir / "unified_dpo_pending.jsonl", pair)
            report["actions"]["training_pair"] = "ok"
        except Exception as e:  # noqa: BLE001
            report["actions"]["training_pair"] = f"error: {e}"

        # Action 4 — Weekly report append
        try:
            week = _week_index()
            week_path = fw_dir / f"week-{week}.md"
            header_needed = not week_path.exists()
            with open(week_path, "a") as f:
                if header_needed:
                    f.write(f"# Flywheel — Week {week}\n\n")
                    f.write("| Time | Step | Phase | Error |\n")
                    f.write("|------|------|-------|-------|\n")
                f.write(
                    f"| {when[:19]} | {step[:40]} | {phase[:20]} | "
                    f"{error[:80].replace('|', '-')} |\n"
                )
            report["actions"]["week_report"] = "ok"
        except Exception as e:  # noqa: BLE001
            report["actions"]["week_report"] = f"error: {e}"

        # Action 5 — GitHub issue (best-effort, fallback to queued file)
        try:
            gh_result = self._try_gh_issue(step, error, logs, report["ticket_id"])
            report["actions"]["github_issue"] = gh_result
        except Exception as e:  # noqa: BLE001
            report["actions"]["github_issue"] = f"queued: {e}"

        # Action 6 — Task registration fallback
        try:
            _append_jsonl(
                fw_dir / "pending_tasks.jsonl",
                {
                    "ticket_id": report["ticket_id"],
                    "at": when,
                    "title": f"[flywheel] {step}: {error[:60]}",
                    "priority": "founder-escalation",
                    "status": "open",
                },
            )
            report["actions"]["task_register"] = "ok"
        except Exception as e:  # noqa: BLE001
            report["actions"]["task_register"] = f"error: {e}"

        return report

    def _try_gh_issue(
        self, step: str, error: str, logs: str, ticket_id: str
    ) -> str:
        """Attempt to create a GitHub issue via gh CLI. Queue if unavailable."""
        title = f"[flywheel] {step}: {error[:60]}"
        body = (
            f"**Ticket:** `{ticket_id}`\n\n"
            f"**Step:** {step}\n\n"
            f"**Error:**\n```\n{error}\n```\n\n"
        )
        if logs:
            body += f"**Logs (first 1KB):**\n```\n{logs[:1000]}\n```\n"
        body += "\n_Auto-filed by nucleus-flywheel. See `.brain/flywheel/pending_issues.jsonl`._"

        # Queue first so we don't lose it if gh fails
        fw_dir = _ensure_flywheel_dir(self.brain_path)
        queue_path = fw_dir / "gh_issue_queue.jsonl"
        _append_jsonl(
            queue_path,
            {
                "ticket_id": ticket_id,
                "title": title,
                "body": body,
                "labels": ["nucleus-bug", "flywheel-auto"],
                "queued_at": _now_iso(),
            },
        )

        try:
            proc = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--label",
                    "nucleus-bug,flywheel-auto",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                return f"ok: {proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else 'created'}"
            return f"queued: gh rc={proc.returncode}"
        except FileNotFoundError:
            return "queued: gh not installed"
        except subprocess.TimeoutExpired:
            return "queued: gh timeout"
        except Exception as e:  # noqa: BLE001
            return f"queued: {e}"


# ── Module-level convenience wrappers ──────────────────────────────────────


def file_ticket(
    step: str,
    error: str,
    logs: str = "",
    phase: str = "",
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Shortcut: instantiate Flywheel and file a ticket."""
    return Flywheel(brain_path).file_ticket(step=step, error=error, logs=logs, phase=phase)


def record_survived(
    phase: str = "unknown",
    step: str = "",
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Shortcut: instantiate Flywheel and bump CSR survived."""
    return Flywheel(brain_path).record_survived(phase=phase, step=step)
