"""No shipped default may silently target a repository nobody owns.

Four defaults in the published package pointed at `eidetic-works/...`, an org
whose repos return 404:

    cli.py:5804                --repo default for `nucleus build --merge`
    build_and_merge.py:74      _DEFAULT_REPO for the same pipeline
    feedback.py:151            where lane feedback opens GitHub issues
    pr_watch.py:40/46          which repos to watch, and the billing-policy owner

None of them could work — for a stranger OR for the operator. A default that
cannot succeed is worse than no default: `nucleus build --merge` would run the
whole pipeline and fail at the GitHub call, and lane feedback would post user
reports into the void. The cure is not a different hardcoded owner, which just
moves the problem; it is to require explicit configuration and say so.

These tests pin the two halves that matter:
  * unconfigured -> refuse with a message naming the env var (not a 404 later);
  * configured   -> behave exactly as before.

The second half is the control. A fix that made everything refuse
unconditionally would satisfy the first half and break the product.
"""
from __future__ import annotations

import pytest


# ── build-and-merge pipeline ───────────────────────────────────────────────


def test_pipeline_refuses_when_no_repo_is_configured(monkeypatch):
    monkeypatch.delenv("NUCLEUS_BUILD_REPO", raising=False)
    from mcp_server_nucleus.runtime import build_and_merge

    rc = build_and_merge.run_build_and_merge_pipeline("do a thing", repo=None)
    assert rc != 0, "pipeline ran with no target repo"


def test_pipeline_names_the_env_var_when_refusing(monkeypatch, capsys):
    monkeypatch.delenv("NUCLEUS_BUILD_REPO", raising=False)
    from mcp_server_nucleus.runtime import build_and_merge

    build_and_merge.run_build_and_merge_pipeline("do a thing", repo=None)
    cap = capsys.readouterr()          # ONE call: a second drains an empty buffer
    out = (cap.out + cap.err).lower()
    assert "nucleus_build_repo" in out or "--repo" in out


def test_default_repo_is_not_a_hardcoded_org(monkeypatch):
    monkeypatch.delenv("NUCLEUS_BUILD_REPO", raising=False)
    from importlib import reload

    from mcp_server_nucleus.runtime import build_and_merge

    reload(build_and_merge)
    assert not build_and_merge._DEFAULT_REPO, (
        f"_DEFAULT_REPO ships a hardcoded repo: {build_and_merge._DEFAULT_REPO!r}"
    )


def test_configured_repo_is_honoured(monkeypatch):
    """CONTROL: the fix must not break the configured path."""
    monkeypatch.setenv("NUCLEUS_BUILD_REPO", "someone/their-repo")
    from importlib import reload

    from mcp_server_nucleus.runtime import build_and_merge

    reload(build_and_merge)
    assert build_and_merge._DEFAULT_REPO == "someone/their-repo"


# ── lane feedback issue routing ────────────────────────────────────────────


def test_feedback_does_not_post_to_a_hardcoded_repo(monkeypatch):
    import inspect

    from mcp_server_nucleus.runtime.lane import feedback

    src = inspect.getsource(feedback)
    assert "eidetic-works" not in src, "lane feedback still names a dead org"


# ── pr_watch ───────────────────────────────────────────────────────────────


def test_pr_watch_ships_no_default_repos():
    from mcp_server_nucleus.runtime import pr_watch

    assert pr_watch.DEFAULT_REPOS == (), (
        f"pr_watch ships repos nobody else owns: {pr_watch.DEFAULT_REPOS}"
    )


def test_billing_policy_owner_is_configurable_and_empty_by_default(monkeypatch):
    monkeypatch.delenv("NUCLEUS_PR_WATCH_OWNER", raising=False)
    from mcp_server_nucleus.runtime import pr_watch

    assert pr_watch._billing_policy_owner() == ""


def test_billing_exhaustion_never_fires_without_a_configured_owner(monkeypatch):
    """Unconfigured, no repo qualifies for the billing bypass — which is the
    safe direction: the policy grants an exception, so defaulting it OPEN would
    hand every stranger's repo a bypass."""
    monkeypatch.delenv("NUCLEUS_PR_WATCH_OWNER", raising=False)
    from mcp_server_nucleus.runtime import pr_watch

    rollup = [{"conclusion": "FAILURE", "startedAt": "2026-01-01T00:00:00Z",
               "completedAt": "2026-01-01T00:00:02Z", "name": "ci"}]
    assert pr_watch._is_billing_exhaustion(rollup, "anyone") is None


def test_billing_exhaustion_fires_for_the_configured_owner(monkeypatch):
    """CONTROL: the policy must still work when someone configures it."""
    monkeypatch.setenv("NUCLEUS_PR_WATCH_OWNER", "someorg")
    from mcp_server_nucleus.runtime import pr_watch

    rollup = [{"conclusion": "FAILURE", "startedAt": "2026-01-01T00:00:00Z",
               "completedAt": "2026-01-01T00:00:02Z", "name": "ci"}]
    assert pr_watch._is_billing_exhaustion(rollup, "someorg") is not None


# ── role aliases ───────────────────────────────────────────────────────────


def test_role_aliases_name_no_sibling_product():
    from nucleus_wedge import role_normalize

    flat = [a for aliases in role_normalize._CANONICAL_ALIASES.values() for a in aliases]
    assert "gentlequest" not in flat


def test_gq_role_still_normalizes():
    """CONTROL: dropping one alias must not break the role itself."""
    from nucleus_wedge.role_normalize import _normalize_role

    for alias in ("gq", "cc_gq", "cc-gq"):
        assert _normalize_role(alias) == "gq"


# ── the class, not the instances ───────────────────────────────────────────


def test_no_shipped_module_hardcodes_the_dead_org():
    """The gate this file backs: scripts/check_product_leak.sh. Kept as a test
    so a plain `pytest` catches a regression without anyone remembering to run
    the shell gate."""
    import pathlib

    src_root = pathlib.Path(__file__).resolve().parents[1] / "src"
    hits = []
    for p in src_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "eidetic-works" in line or "gentlequest" in line.lower():
                hits.append(f"{p.relative_to(src_root)}:{i}: {line.strip()[:90]}")
    assert not hits, "shipped source names a dead org or sibling product:\n  " + "\n  ".join(hits)
