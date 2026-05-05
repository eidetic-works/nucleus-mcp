"""Tests for the stale-PR auto-trigger primitive (Slice 4).

Covers:
  - Classification logic (auto-mergeable / billing-stuck / needs-verdict)
  - Age threshold filter (PRs younger than threshold are skipped)
  - Billing-exhaustion signature detection (eidetic-works only, ≤5s duration)
  - Dedup: re-runs within DEDUP_H window don't re-fire for same PR
  - dry_run=True returns counts but emits no relays
  - Empty repo list returns clean empty result
  - relay_post integration (mocked) gets the right envelope shape
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server_nucleus.runtime import pr_watch  # noqa: E402


NOW = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)


def _pr(number, age_days, *, mergeable="MERGEABLE", rollup=None, title="example PR"):
    """Build a fake gh-pr-list JSON record."""
    created = NOW - timedelta(days=age_days)
    return {
        "number": number,
        "title": title,
        "createdAt": created.isoformat().replace("+00:00", "Z"),
        "mergeable": mergeable,
        "mergeStateStatus": "CLEAN" if mergeable == "MERGEABLE" else "BLOCKED",
        "statusCheckRollup": rollup or [],
    }


def _green_check(name="ci"):
    return {
        "name": name,
        "conclusion": "SUCCESS",
        "startedAt": NOW.isoformat().replace("+00:00", "Z"),
        "completedAt": (NOW + timedelta(seconds=120)).isoformat().replace("+00:00", "Z"),
        "detailsUrl": "https://example.com/run/1",
    }


def _billing_failure_check(name="lint", duration_s=3):
    return {
        "name": name,
        "conclusion": "FAILURE",
        "startedAt": NOW.isoformat().replace("+00:00", "Z"),
        "completedAt": (NOW + timedelta(seconds=duration_s)).isoformat().replace("+00:00", "Z"),
        "detailsUrl": "https://example.com/run/2",
    }


def _real_failure_check(duration_s=180):
    return _billing_failure_check(name="real_test", duration_s=duration_s)


@pytest.fixture(autouse=True)
def _isolate_brain(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.pr_watch.get_brain_path",
        lambda: tmp_path,
    )
    yield


# ─── Classification ──────────────────────────────────────────────────────

def test_under_threshold_is_skipped():
    pr = _pr(101, age_days=3)
    result = pr_watch._classify(pr, "eidetic-works/mcp-server-nucleus", threshold_days=7, now=NOW)
    assert result is None


def test_auto_mergeable_classifies_when_green_and_old():
    pr = _pr(102, age_days=10, rollup=[_green_check(), _green_check("test")])
    result = pr_watch._classify(pr, "eidetic-works/mcp-server-nucleus", 7, NOW)
    assert result is not None
    assert result.classification == "auto-mergeable"
    assert "Squash-merge" in result.suggested_action
    assert result.failing_check is None


def test_billing_stuck_classifies_for_eidetic_short_failure():
    pr = _pr(103, age_days=10, rollup=[_billing_failure_check(duration_s=3)])
    result = pr_watch._classify(pr, "eidetic-works/mcp-server-nucleus", 7, NOW)
    assert result is not None
    assert result.classification == "billing-stuck"
    assert result.failing_check is not None
    assert result.failing_check["duration_s"] == 3
    assert "billing-bypass" in result.suggested_action


def test_long_failed_run_pr_human_review():
    """A long-duration FAILURE on eidetic is a real failure, not billing-exhaustion."""
    pr = _pr(104, age_days=10, rollup=[_real_failure_check(duration_s=180)])
    result = pr_watch._classify(pr, "eidetic-works/mcp-server-nucleus", 7, NOW)
    assert result is not None
    assert result.classification == "needs-verdict"
    assert result.failing_check is None


def test_non_eidetic_short_failure_no_billing_bypass():
    """The billing-bypass policy is org-specific (eidetic-works only)."""
    pr = _pr(105, age_days=10, rollup=[_billing_failure_check(duration_s=3)])
    result = pr_watch._classify(pr, "someother-org/repo", 7, NOW)
    assert result is not None
    assert result.classification == "needs-verdict"
    assert result.failing_check is None


def test_blocked_pr_with_green_checks_is_needs_verdict():
    """Mergeable=BLOCKED (e.g. unresolved review) should not be auto-mergeable even if CI green."""
    pr = _pr(106, age_days=10, mergeable="CONFLICTING", rollup=[_green_check()])
    result = pr_watch._classify(pr, "eidetic-works/mcp-server-nucleus", 7, NOW)
    assert result is not None
    assert result.classification == "needs-verdict"


# ─── Enumeration + env wiring ────────────────────────────────────────────

def test_list_stale_prs_uses_default_repos_when_env_unset(monkeypatch):
    monkeypatch.delenv("NUCLEUS_PR_REPOS", raising=False)
    monkeypatch.delenv("NUCLEUS_PR_WATCH_THRESHOLD_DAYS", raising=False)
    seen_repos = []

    def fake_list(repo):
        seen_repos.append(repo)
        return [_pr(201, 10, rollup=[_green_check()])]

    with patch.object(pr_watch, "_list_open_prs", side_effect=fake_list):
        result = pr_watch.list_stale_prs(now=NOW)
    assert tuple(seen_repos) == pr_watch.DEFAULT_REPOS
    assert len(result) == len(pr_watch.DEFAULT_REPOS)


def test_list_stale_prs_respects_repos_env(monkeypatch):
    monkeypatch.setenv("NUCLEUS_PR_REPOS", "owner1/repoA, owner2/repoB ")
    seen_repos = []

    def fake_list(repo):
        seen_repos.append(repo)
        return []

    with patch.object(pr_watch, "_list_open_prs", side_effect=fake_list):
        pr_watch.list_stale_prs(now=NOW)
    assert seen_repos == ["owner1/repoA", "owner2/repoB"]


def test_list_stale_prs_handles_gh_failure_gracefully(monkeypatch, caplog):
    """If gh fails for one repo, others continue."""
    monkeypatch.setenv("NUCLEUS_PR_REPOS", "good/repo,bad/repo")

    def fake_list(repo):
        if repo == "bad/repo":
            raise RuntimeError("gh exploded")
        return [_pr(301, 10, rollup=[_green_check()])]

    with patch.object(pr_watch, "_list_open_prs", side_effect=fake_list):
        result = pr_watch.list_stale_prs(now=NOW)
    assert len(result) == 1
    assert result[0].repo == "good/repo"


# ─── Dedup state ─────────────────────────────────────────────────────────

def test_dedup_skips_recent_emissions(tmp_path):
    pr = pr_watch.StalePR(
        repo="eidetic-works/mcp-server-nucleus", number=400, created_at=NOW.isoformat(),
        age_days=10, title="t", classification="auto-mergeable", suggested_action="x",
    )
    recent = (NOW - timedelta(hours=2)).isoformat()
    with patch.object(pr_watch, "_load_dedup", return_value={pr.pr_id(): recent}):
        with patch("mcp_server_nucleus.runtime.relay_ops.relay_post") as mock_post:
            emitted = pr_watch.emit_stale_pr_relays([pr], dedup_hours=24, now=NOW)
    assert emitted == []
    mock_post.assert_not_called()


def test_dedup_allows_emission_after_window(tmp_path):
    pr = pr_watch.StalePR(
        repo="eidetic-works/mcp-server-nucleus", number=401, created_at=NOW.isoformat(),
        age_days=10, title="t", classification="auto-mergeable", suggested_action="x",
    )
    long_ago = (NOW - timedelta(hours=48)).isoformat()
    with patch.object(pr_watch, "_load_dedup", return_value={pr.pr_id(): long_ago}):
        with patch("mcp_server_nucleus.runtime.relay_ops.relay_post",
                   return_value={"message_id": "relay_xxx"}) as mock_post:
            emitted = pr_watch.emit_stale_pr_relays([pr], dedup_hours=24, now=NOW)
    assert emitted == ["relay_xxx"]
    mock_post.assert_called_once()


# ─── dry_run + envelope shape ────────────────────────────────────────────

def test_dry_run_returns_synthetic_ids_emits_nothing():
    pr = pr_watch.StalePR(
        repo="eidetic-works/mcp-server-nucleus", number=500, created_at=NOW.isoformat(),
        age_days=10, title="t", classification="auto-mergeable", suggested_action="x",
    )
    with patch("mcp_server_nucleus.runtime.relay_ops.relay_post") as mock_post:
        emitted = pr_watch.emit_stale_pr_relays([pr], dry_run=True, now=NOW)
    assert emitted == [f"DRY_RUN:{pr.pr_id()}"]
    mock_post.assert_not_called()


def test_relay_envelope_shape():
    pr = pr_watch.StalePR(
        repo="eidetic-works/mcp-server-nucleus", number=501, created_at=NOW.isoformat(),
        age_days=12, title="My stale PR title",
        classification="needs-verdict", suggested_action="Human review needed",
    )
    captured = {}

    def fake_post(**kwargs):
        captured.update(kwargs)
        return {"message_id": "relay_yyy"}

    with patch("mcp_server_nucleus.runtime.relay_ops.relay_post", side_effect=fake_post):
        with patch.object(pr_watch, "_load_dedup", return_value={}):
            pr_watch.emit_stale_pr_relays([pr], coord="claude_code_main", now=NOW)

    assert captured["to"] == "claude_code_main"
    assert "[STALE-PR-VERDICT]" in captured["subject"]
    assert "needs-verdict" in captured["subject"]
    assert "12d" in captured["subject"]
    assert captured["priority"] == "high"  # needs-verdict → high
    assert captured["sender"] == "nucleus_pr_watch"
    body = json.loads(captured["body"])
    assert body["tags"] == ["stale-pr", "verdict-needed", "needs-verdict"]
    assert body["artifact_refs"] == [f"pr:{pr.pr_id()}"]
    assert body["auto_generated"] is True


def test_priority_normal_for_billing_stuck():
    pr = pr_watch.StalePR(
        repo="eidetic-works/mcp-server-nucleus", number=502, created_at=NOW.isoformat(),
        age_days=10, title="t", classification="billing-stuck", suggested_action="x",
    )
    captured = {}

    def fake_post(**kwargs):
        captured.update(kwargs)
        return {"message_id": "relay_zzz"}

    with patch("mcp_server_nucleus.runtime.relay_ops.relay_post", side_effect=fake_post):
        with patch.object(pr_watch, "_load_dedup", return_value={}):
            pr_watch.emit_stale_pr_relays([pr], now=NOW)
    assert captured["priority"] == "normal"


# ─── End-to-end run_pr_watch summary ────────────────────────────────────

def test_run_pr_watch_aggregates_classifications():
    fake_prs = [
        _pr(601, 10, rollup=[_green_check()]),
        _pr(602, 10, rollup=[_billing_failure_check(duration_s=2)]),
        _pr(603, 10, rollup=[_real_failure_check()]),
        _pr(604, 3,  rollup=[_green_check()]),  # too young, skipped
    ]
    with patch.object(pr_watch, "_list_open_prs", return_value=fake_prs):
        result = pr_watch.run_pr_watch(threshold_days=7, dry_run=True, now=NOW)
    assert result["stale_count"] == 3
    assert result["by_classification"] == {
        "auto-mergeable": 1,
        "billing-stuck": 1,
        "needs-verdict": 1,
    }
    assert len(result["relays_emitted"]) == 3
    assert all(rid.startswith("DRY_RUN:") for rid in result["relays_emitted"])
    assert result["dry_run"] is True
