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
import logging
logger = logging.getLogger(__name__)

import json
import re
import os
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .csr import bump_survived, bump_unsurvived, read_csr, _ensure_flywheel_dir
from .demand_signal import record_signal, latest_verdict


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


def _scrub_home_paths(text: str) -> str:
    """Replace the absolute home-directory prefix with ``~``.

    Ticket error/log text routinely carries ``/Users/<name>/...`` absolute
    paths from the machine the run happened on. Those paths are local
    metadata — they leak the operator's username into records that get
    filed to GitHub issues — and they make dedup/clustering noisier.
    """
    if not text:
        return text
    home = os.path.expanduser("~")
    return text.replace(home + os.sep, "~" + os.sep)


# Per-process monotonic counter for ticket-id uniqueness.
_ticket_counter = 0


# Exception-shaped errors start with a type name; free prose does not.
_EXC_HEAD = re.compile(r"^\s*([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning))\s*:\s*(.+)", re.S)


def error_signature(error: Optional[str]) -> Optional[str]:
    """A regex that matches OTHER occurrences of the same failure, or None.

    Wiring `evidence_pattern` up meant deciding what pattern a ticket should
    carry, and that is the hard part: an auto-derived regex over free prose
    either matches every ticket or none, and both yield a confident wrong
    prevalence -- the exact failure this evidence machinery exists to prevent.

    So this recognises only the one shape that has a stable head: an exception
    type followed by a message. It keeps the type and the message up to the
    first em dash (tickets append a narrative tail there, which differs between
    two occurrences of the same bug), and normalises digits and hex so ids and
    line numbers do not split one failure into many.

    Everything else returns None, and a ticket with no signature carries no
    evidence. No signature is a fine outcome. A junk one is not.
    """
    if not error or not isinstance(error, str):
        return None
    m = _EXC_HEAD.match(error)
    if not m:
        return None
    exc, msg = m.group(1), m.group(2)
    msg = msg.split("\u2014")[0].split(" - ")[0].strip()          # drop the narrative tail
    msg = re.sub(r"0x[0-9a-fA-F]+|\b[0-9a-fA-F]{8,}\b", "#", msg)  # hex ids
    msg = re.sub(r"\d+", "#", msg)                                 # line numbers, counts
    msg = msg[:120].strip()
    if not msg:
        return None
    # Escape, then re-open the normalised slots so the pattern matches the
    # variants it was normalised over.
    return re.escape(f"{exc}: {msg}").replace(r"\#", r"\w+")


def _generate_ticket_id() -> str:
    global _ticket_counter
    _ticket_counter += 1
    epoch = int(datetime.now(timezone.utc).timestamp())
    hex4 = secrets.token_hex(2)
    return f"fw-{epoch}-{_ticket_counter}-{hex4}"


def parse_ticket_epoch(ticket_id: str) -> Optional[int]:
    """Extract the epoch timestamp from a flywheel ticket id.

    Accepts both legacy (``fw-1786207260``) and new
    (``fw-1786207260-a3f1-7c2d``) shapes. Returns ``None`` on any failure
    (missing prefix, non-numeric epoch, empty input, etc.).
    """
    try:
        if not ticket_id.startswith("fw-"):
            return None
        body = ticket_id[len("fw-"):]
        first_segment = body.split("-", 1)[0]
        return int(first_segment)
    except (AttributeError, ValueError, TypeError):
        return None


class Flywheel:
    """The compounding loop engine.

    Instantiate once per process. Pass an explicit brain_path for tests;
    production callers can let it auto-resolve from env.
    """

    def __init__(
        self,
        brain_path: Optional[Path] = None,
        github_repo: Optional[str] = None,
    ) -> None:
        self.brain_path = Path(brain_path) if brain_path else _default_brain_path()
        # Explicit per-instance override for the GitHub issue target repo.
        # None → resolve from NUCLEUS_FLYWHEEL_REPO env at call time, then
        # fall back to the public default (works for anyone; internal users
        # set NUCLEUS_FLYWHEEL_REPO to your own destination repo).
        self.github_repo = github_repo
        _ensure_flywheel_dir(self.brain_path)

    # ── CSR ────────────────────────────────────────────────────────────────

    def record_survived(self, phase: str = "unknown", step: str = "") -> Dict[str, Any]:
        """Bump CSR for a survived claim. Returns updated state.

        Also closes the gap demand_signal.py exists to prevent: marking
        something PROVEN (correctness, via CSR) must never silently imply it
        was also WANTED (demand, a different axis this same call knows
        nothing about). If this artifact has no demand-signal record at all,
        stamp one at UNKNOWN -- the honest default -- so the ledger never
        goes quiet on the question just because CSR went green. Only fires
        when no record exists yet (an artifact re-verified as survived
        multiple times does not get re-stamped UNKNOWN over a real verdict
        someone already recorded). Best-effort: a demand-ledger write must
        never cost the actual CSR bump, which is the load-bearing half.
        """
        label = f"{phase}:{step}" if step else phase
        result = bump_survived(self.brain_path, step=label)
        try:
            if latest_verdict(self.brain_path, artifact=label) is None:
                record_signal(
                    self.brain_path, artifact=label, verdict="unknown",
                    source="agent_search",
                    evidence="",
                    phase=phase,
                )
        except Exception:
            logger.debug("Swallowed exception in record_survived", exc_info=True)
            pass  # demand-ledger bookkeeping must never cost the CSR bump
        return result

    def csr(self) -> Dict[str, Any]:
        """Read current CSR state."""
        return read_csr(self.brain_path)

    # ── Ticket backlog with closure signal (fw-1786151012) ───────────────────

    def list_pending_tickets(self, include_closed: bool = False) -> list:
        """Read pending_issues.jsonl and annotate each ticket with closure status.

        fw-1786151012: the backlog file carries no status field, so ~37% of
        tickets that are already fixed (have a matching survived claim in
        csr.json or a non-empty fix_description) look equally open. This
        method cross-references csr.json's recent_claims by 'phase:step'
        label and checks fix_description to add a ``closure_status`` field:

        - ``"open"`` — no fix_description and no matching survived claim
        - ``"fixed"`` — has a non-empty fix_description
        - ``"survived"`` — has a matching survived claim in csr.json

        Pass ``include_closed=True`` to return all tickets; default skips
        closed ones so callers see only actionable work.
        """
        fw_dir = self.brain_path / "flywheel"
        pending_path = fw_dir / "pending_issues.jsonl"
        if not pending_path.exists():
            return []
        # Build a set of survived step labels from csr.json
        csr = read_csr(self.brain_path)
        survived_labels = {
            claim["step"] for claim in csr.get("recent_claims", [])
            if claim.get("survived")
        }
        tickets = []
        with open(pending_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    t = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                # Determine closure status
                has_fix = bool(t.get("fix_description", "").strip())
                label = f"{t.get('phase','')}:{t.get('step','')}" if t.get("phase") else t.get("step", "")
                has_survived = label in survived_labels
                # triage_status is set by hand to retire a ticket. It is NOT
                # evidence of a fix, and must not be laundered into one: a
                # ticket marked closed with no fix_description and no survived
                # claim gets its own state, "closed_unverified". Observed live
                # — 131 tickets were stamped triage_status=closed while only 66
                # carried a fix_description, and the summary read "0 open"
                # because it counted the field that had been written rather
                # than asking this function. Collapsing that into "fixed" would
                # make 65 unfixed tickets indistinguishable from 65 fixed ones.
                triaged = str(t.get("triage_status", "")).strip().lower() == "closed"
                if has_fix:
                    t["closure_status"] = "fixed"
                elif has_survived:
                    t["closure_status"] = "survived"
                elif triaged:
                    t["closure_status"] = "closed_unverified"
                else:
                    t["closure_status"] = "open"
                # Only a fix or a survived claim counts as closed here.
                # closed_unverified stays in the actionable list by default,
                # because "someone decided to stop tracking this" is not the
                # same as "this no longer happens" — it is the third state.
                if not include_closed and t["closure_status"] in ("fixed", "survived"):
                    continue
                tickets.append(t)
        return tickets

    # ── Tickets ────────────────────────────────────────────────────────────

    def file_ticket(
        self,
        step: str,
        error: str,
        logs: str = "",
        phase: str = "",
        fix_description: str = "",
        evidence_pattern: str = "",
        evidence_roots: Optional[list] = None,
        evidence_max_sessions: int = 200,
    ) -> Dict[str, Any]:
        """The 6-action accountability helper.

        Returns a dict summarizing which actions fired. All actions are
        best-effort; one failing does not block the others.

        ``fix_description`` is an optional structured fix prompt — a concrete,
        actionable task description that a build pipeline or human can execute
        to resolve the failure. Unlike ``error`` (which is diagnostic), this
        is prescriptive: "Fix the sort in slots.py status_dashboard to cast
        slot IDs to int before comparison." When empty (default), the ticket
        only carries the error and awaits human triage to attach a fix.

        ``evidence_pattern`` opts the ticket into a prevalence reading: how many
        distinct SESSIONS that pattern appears in, with citations. It is opt-in
        because there are thousands of transcripts and scanning them on every
        ticket would make filing cost minutes.

        The reading follows ``prevalence``'s refusal: if the scan was capped or
        skipped files, the ticket records ``complete: False`` and a summary
        beginning INSUFFICIENT rather than a bare number. A ticket that launders
        a partial reading into a statistic is worse than a ticket with no
        statistic — 349 of these already assert without evidence; the point is
        to stop asserting, not to assert with more decimal places.
        """
        when = _now_iso()
        fw_dir = _ensure_flywheel_dir(self.brain_path)

        # Prevalence, opt-in and best-effort. The contract for every action in
        # this method is "one failing does not block the others" -- a scan that
        # throws must cost the evidence, never the ticket.
        evidence: Dict[str, Any] = {}
        if evidence_pattern:
            try:
                from . import prevalence as _prev

                r = _prev.scan(
                    evidence_pattern,
                    roots=evidence_roots,
                    max_sessions=evidence_max_sessions,
                )
                d = r.as_dict()
                # Citations carry absolute transcript paths. Every other field
                # here is scrubbed; evidence must be too, or attaching it would
                # quietly defeat a guard this repo already has.
                d["examples"] = [
                    {
                        "session": e["session"],
                        "file": _scrub_home_paths(e["file"]),
                        "line": e["line"],
                        "excerpt": _scrub_home_paths(e["excerpt"]),
                    }
                    for e in d.get("examples", [])
                ]
                d["roots"] = [_scrub_home_paths(x) for x in d.get("roots", [])]
                d["summary"] = _scrub_home_paths(r.summary())
                evidence = {"evidence": d}
            except Exception:  # noqa: BLE001
                logger.debug("Swallowed exception gathering ticket evidence", exc_info=True)
                evidence = {
                    "evidence": {
                        "complete": False,
                        "insufficient_reason": (
                            "the prevalence scan failed; the ticket was filed "
                            "without evidence rather than not filed"
                        ),
                        "summary": "INSUFFICIENT: prevalence scan failed.",
                    }
                }
        report: Dict[str, Any] = {
            "ticket_id": _generate_ticket_id(),
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
                    "error": _scrub_home_paths(error),
                    "logs": _scrub_home_paths(logs[:2000]),  # cap payload
                    "fix_description": fix_description,
                    **evidence,
                },
            )
            report["actions"]["memory_note"] = "ok"
        except Exception as e:  # noqa: BLE001
            logger.debug("Swallowed exception in file_ticket", exc_info=True)
            report["actions"]["memory_note"] = f"error: {e}"

        # Action 2 — CSR bump (unsurvived)
        try:
            bump_unsurvived(self.brain_path, step=step, reason=error[:200])
            report["actions"]["csr_bump"] = "ok"
        except Exception as e:  # noqa: BLE001
            logger.debug("Swallowed exception in file_ticket", exc_info=True)
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
            logger.debug("Swallowed exception in file_ticket", exc_info=True)
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
            logger.debug("Swallowed exception in file_ticket", exc_info=True)
            report["actions"]["week_report"] = f"error: {e}"

        # Action 5 — GitHub issue (best-effort, fallback to queued file)
        try:
            gh_result = self._try_gh_issue(step, error, logs, report["ticket_id"])
            report["actions"]["github_issue"] = gh_result
        except Exception as e:  # noqa: BLE001
            logger.debug("Swallowed exception in file_ticket", exc_info=True)
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
                    "fix_description": fix_description,
                },
            )
            report["actions"]["task_register"] = "ok"
        except Exception as e:  # noqa: BLE001
            logger.debug("Swallowed exception in file_ticket", exc_info=True)
            report["actions"]["task_register"] = f"error: {e}"

        return report

    def _try_gh_issue(
        self, step: str, error: str, logs: str, ticket_id: str
    ) -> str:
        """Attempt to create a GitHub issue via gh CLI. Queue if unavailable.

        Target repo resolution (first wins):
            1. per-instance ``Flywheel(github_repo=...)`` override
            2. ``NUCLEUS_FLYWHEEL_REPO`` env var
            3. no default — the finding is QUEUED LOCALLY and no issue is filed

        THERE IS DELIBERATELY NO HARDCODED DEFAULT REPO. An earlier version
        shipped one, and because this module is published to PyPI that meant a
        specific account name travelled inside a package anyone can download.
        A library must not name its author's accounts; the operator of a given
        install is the only party who knows where their findings belong.

        The history that produced the old default is worth keeping, with the
        account names removed, because the failure was silent: a default that
        was documented as "public — works for anyone" did not resolve for any
        account tested, and 260 of 307 queued findings accumulated against it
        without one error surfacing. A later stopgap pointed at an unrelated
        application's tracker, so nucleus findings were filed into a product
        that had nothing to do with them.

        The lesson, which is why the default is now absent rather than merely
        corrected: AN UNREACHABLE DEFAULT AND A CORRECT ONE ARE INDISTINGUISHABLE
        FROM INSIDE THIS FUNCTION. Queueing locally and filing nothing is the
        honest behaviour when no destination has been configured.

        Labels are restricted to ones that exist on the target repo
        (``nucleus-bug``); ``flywheel-auto`` was dropped as invalid there.
        """
        target_repo = (
            self.github_repo
            or os.environ.get("NUCLEUS_FLYWHEEL_REPO", "")
        )
        title = f"[flywheel] {step}: {error[:60]}"
        body = (
            f"**Ticket:** `{ticket_id}`\n\n"
            f"**Step:** {step}\n\n"
            f"**Error:**\n```\n{_scrub_home_paths(error)}\n```\n\n"
        )
        if logs:
            body += f"**Logs (first 1KB):**\n```\n{_scrub_home_paths(logs[:1000])}\n```\n"
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
                "labels": ["nucleus-bug"],
                "repo": target_repo,
                "queued_at": _now_iso(),
            },
        )

        # Under pytest/test mode, skip the real gh call — only queue.
        # This prevents accidental creation of live GitHub issues from
        # test runs (PYTEST_CURRENT_TEST is set by pytest; NUCLEUS_TEST=1
        # is a manual opt-in for any test harness).
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("NUCLEUS_TEST") == "1":
            return "queued: test mode (no subprocess)"

        try:
            proc = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--repo",
                    target_repo,
                    "--title",
                    title,
                    "--body",
                    body,
                    "--label",
                    "nucleus-bug",
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
    fix_description: str = "",
    brain_path: Optional[Path] = None,
    evidence_pattern: str = "",
    evidence_roots: Optional[list] = None,
    evidence_max_sessions: int = 200,
) -> Dict[str, Any]:
    """Shortcut: instantiate Flywheel and file a ticket.

    This used to forward a fixed list of kwargs that did NOT include
    ``evidence_pattern``, so any caller using this convenience wrapper had its
    argument silently discarded — the shape that makes a feature look wired
    when it is not.
    """
    return Flywheel(brain_path).file_ticket(
        step=step, error=error, logs=logs, phase=phase,
        fix_description=fix_description,
        evidence_pattern=evidence_pattern,
        evidence_roots=evidence_roots,
        evidence_max_sessions=evidence_max_sessions,
    )


def record_survived(
    phase: str = "unknown",
    step: str = "",
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Shortcut: instantiate Flywheel and bump CSR survived."""
    return Flywheel(brain_path).record_survived(phase=phase, step=step)
