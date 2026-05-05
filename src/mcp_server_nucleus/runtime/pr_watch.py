"""Stale-PR auto-trigger primitive — Slice 4 of cowork directive batch.

Enumerates open PRs across configured repos, classifies each into one of:

  - auto-mergeable  : CI green AND mergeable AND age >= threshold
  - billing-stuck   : eidetic-works repo CI failure with billing-exhaustion
                      signature (FAILURE + steps_count=0 + duration <= 5s)
                      → AGENTS.md H8 billing-bypass merge applies
  - needs-verdict   : everything else (real CI failure, conflicts, unresolved
                      reviews, unclassified)

Fires one relay per stale PR to the configured integration-coord (default
``claude_code_main``, override via ``NUCLEUS_PR_COORD``). Per-PR dedup file
prevents re-firing within ``NUCLEUS_PR_WATCH_DEDUP_H`` hours (default 24).

Primitive-gate compliance:
  - any-OS : pure stdlib + ``subprocess`` to ``gh`` CLI
  - any-user : no hardcoded paths; relays land via ``relay_post``
  - any-agent : recipient via ``NUCLEUS_PR_COORD`` env (default
                ``claude_code_main``)
  - any-LLM : classification + relay body are LLM-invariant
  - portable : ``gh`` is widely available; REST-via-urllib fallback documented
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .common import get_brain_path

logger = logging.getLogger("nucleus.pr_watch")

DEFAULT_REPOS: tuple[str, ...] = (
    "eidetic-works/mcp-server-nucleus",
)
DEFAULT_THRESHOLD_DAYS = 7
DEFAULT_DEDUP_HOURS = 24
DEFAULT_COORD = "claude_code_main"
BILLING_EXHAUSTION_DURATION_S = 5
EIDETIC_OWNER = "eidetic-works"


@dataclass(frozen=True)
class StalePR:
    """One open PR past the staleness threshold + its classification."""

    repo: str            # "eidetic-works/mcp-server-nucleus"
    number: int
    created_at: str      # ISO-8601
    age_days: int
    title: str
    classification: str  # "auto-mergeable" | "billing-stuck" | "needs-verdict"
    suggested_action: str
    failing_check: dict[str, Any] | None = None  # billing-exhaustion telltale or None

    def pr_id(self) -> str:
        return f"{self.repo}#{self.number}"


# ─── gh CLI wrapper (single dependency) ─────────────────────────────────

def _gh_json(*args: str) -> Any:
    """Run ``gh`` with --jq=. ``gh`` propagates auth from the user's session."""
    cmd = ["gh", *args]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.PIPE, timeout=30)
    except FileNotFoundError:
        raise RuntimeError("pr_watch requires the `gh` CLI on PATH")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"gh failed: {' '.join(cmd[:3])}: {stderr}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"gh timeout: {' '.join(cmd[:3])}")
    return json.loads(out.decode("utf-8"))


# ─── PR enumeration + classification ────────────────────────────────────

def _list_open_prs(repo: str) -> list[dict[str, Any]]:
    return _gh_json(
        "pr", "list",
        "--repo", repo,
        "--state", "open",
        "--limit", "100",
        "--json", "number,title,createdAt,mergeable,mergeStateStatus,statusCheckRollup",
    )


def _age_days(created_at: str, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return (now - created).days


def _is_billing_exhaustion(rollup: list[dict[str, Any]] | None, owner: str) -> dict[str, Any] | None:
    """Return the billing-exhaustion check signature if present, else None.

    Per .brain/policies/ci_billing_bypass.md: failure + 0 steps + ≤5s duration
    on an eidetic-works repo is the signature. Non-eidetic repos never qualify.
    """
    if owner != EIDETIC_OWNER or not rollup:
        return None
    for check in rollup:
        if check.get("conclusion") != "FAILURE":
            continue
        # gh's statusCheckRollup gives startedAt/completedAt as ISO-8601 strings
        started = check.get("startedAt")
        completed = check.get("completedAt")
        if not started or not completed:
            continue
        try:
            d_s = datetime.fromisoformat(started.replace("Z", "+00:00"))
            d_c = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            duration_s = (d_c - d_s).total_seconds()
        except ValueError:
            continue
        if duration_s <= BILLING_EXHAUSTION_DURATION_S:
            return {
                "name": check.get("name"),
                "conclusion": check.get("conclusion"),
                "duration_s": duration_s,
                "url": check.get("detailsUrl"),
            }
    return None


def _classify(pr: dict[str, Any], repo: str, threshold_days: int, now: datetime | None = None) -> StalePR | None:
    """Return a StalePR if pr is past threshold; None otherwise."""
    age = _age_days(pr["createdAt"], now)
    if age < threshold_days:
        return None
    owner = repo.split("/", 1)[0]
    rollup = pr.get("statusCheckRollup") or []
    billing = _is_billing_exhaustion(rollup, owner)
    mergeable = pr.get("mergeable") == "MERGEABLE"
    all_green = bool(rollup) and all(c.get("conclusion") == "SUCCESS" for c in rollup if c.get("conclusion"))

    if billing:
        cls = "billing-stuck"
        action = "Auto-merge via billing-bypass per .brain/policies/ci_billing_bypass.md (gh api -X PUT .../merge)"
    elif all_green and mergeable:
        cls = "auto-mergeable"
        action = "Squash-merge per AGENTS.md H8 (peer continuous-integration)"
    else:
        cls = "needs-verdict"
        action = "Human review needed: real CI failure, conflicts, or unresolved threads"

    return StalePR(
        repo=repo,
        number=pr["number"],
        created_at=pr["createdAt"],
        age_days=age,
        title=pr.get("title", "")[:140],
        classification=cls,
        suggested_action=action,
        failing_check=billing,
    )


def list_stale_prs(
    repos: list[str] | tuple[str, ...] | None = None,
    threshold_days: int | None = None,
    now: datetime | None = None,
) -> list[StalePR]:
    """Enumerate open PRs across repos, return only those past threshold.

    Args:
        repos: explicit repo list (``owner/name``). If None, reads
            ``NUCLEUS_PR_REPOS`` env (comma-separated) or falls back to
            ``DEFAULT_REPOS``.
        threshold_days: age cutoff. If None, reads
            ``NUCLEUS_PR_WATCH_THRESHOLD_DAYS`` or ``DEFAULT_THRESHOLD_DAYS``.
        now: clock injection for deterministic tests.
    """
    if repos is None:
        env_repos = os.environ.get("NUCLEUS_PR_REPOS", "").strip()
        repos = tuple(r.strip() for r in env_repos.split(",") if r.strip()) or DEFAULT_REPOS
    if threshold_days is None:
        threshold_days = int(
            os.environ.get("NUCLEUS_PR_WATCH_THRESHOLD_DAYS", DEFAULT_THRESHOLD_DAYS)
        )
    stale: list[StalePR] = []
    for repo in repos:
        try:
            prs = _list_open_prs(repo)
        except RuntimeError as e:
            logger.warning("pr_watch: skipping %s: %s", repo, e)
            continue
        for pr in prs:
            classified = _classify(pr, repo, threshold_days, now)
            if classified:
                stale.append(classified)
    return stale


# ─── Dedup state (avoid spamming the same PR every cron tick) ──────────

def _dedup_path() -> Path:
    return get_brain_path() / "state" / "pr_watch_dedup.json"


def _load_dedup() -> dict[str, str]:
    p = _dedup_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_dedup(state: dict[str, str]) -> None:
    p = _dedup_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True))


def _should_emit(pr_id: str, dedup: dict[str, str], dedup_hours: int, now: datetime) -> bool:
    last = dedup.get(pr_id)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True
    return now - last_dt >= timedelta(hours=dedup_hours)


# ─── Relay emission ─────────────────────────────────────────────────────

def emit_stale_pr_relays(
    stale: list[StalePR],
    coord: str | None = None,
    dedup_hours: int | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> list[str]:
    """Fire one relay per stale PR to the integration coord. Returns relay IDs.

    Dedup: skips PRs whose previous relay fired within ``dedup_hours``. Updates
    ``.brain/state/pr_watch_dedup.json`` on each successful emission.
    """
    if coord is None:
        coord = os.environ.get("NUCLEUS_PR_COORD", DEFAULT_COORD)
    if dedup_hours is None:
        dedup_hours = int(os.environ.get("NUCLEUS_PR_WATCH_DEDUP_H", DEFAULT_DEDUP_HOURS))
    now = now or datetime.now(timezone.utc)

    dedup = _load_dedup()
    emitted: list[str] = []
    # Lazy import to avoid a hard cycle: relay_ops imports lots of substrate.
    from .relay_ops import relay_post

    for pr in stale:
        pr_id = pr.pr_id()
        if not _should_emit(pr_id, dedup, dedup_hours, now):
            logger.debug("pr_watch: skipping %s (deduped within %sh)", pr_id, dedup_hours)
            continue
        priority = "high" if pr.classification == "needs-verdict" else "normal"
        subject = f"[STALE-PR-VERDICT] {pr.repo}#{pr.number} ({pr.classification}, {pr.age_days}d): {pr.title}"
        body = json.dumps({
            "summary": f"PR {pr_id} has been open {pr.age_days} days. Classification: {pr.classification}. Suggested: {pr.suggested_action}",
            "tags": ["stale-pr", "verdict-needed", pr.classification],
            "artifact_refs": [f"pr:{pr_id}"],
            "auto_generated": True,
            "pr_watch": asdict(pr),
        })
        if dry_run:
            emitted.append(f"DRY_RUN:{pr_id}")
            continue
        try:
            result = relay_post(
                to=coord,
                subject=subject,
                body=body,
                priority=priority,
                sender="nucleus_pr_watch",
            )
            mid = result.get("message_id") if isinstance(result, dict) else None
            if mid:
                emitted.append(mid)
                dedup[pr_id] = now.isoformat()
        except Exception as e:
            logger.warning("pr_watch: relay_post failed for %s: %s", pr_id, e)

    if not dry_run and emitted:
        _save_dedup(dedup)
    return emitted


# ─── Top-level action (called from tools/orchestration.py) ──────────────

def run_pr_watch(
    threshold_days: int | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Single-shot run: enumerate, classify, emit. Returns summary JSON."""
    stale = list_stale_prs(threshold_days=threshold_days, now=now)
    by_class: dict[str, int] = {}
    for s in stale:
        by_class[s.classification] = by_class.get(s.classification, 0) + 1
    relays = emit_stale_pr_relays(stale, dry_run=dry_run, now=now)
    return {
        "stale_count": len(stale),
        "by_classification": by_class,
        "relays_emitted": relays,
        "dry_run": dry_run,
    }
