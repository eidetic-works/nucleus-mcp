"""Tests for runtime/verifier.py — the DSoR Verifier ground-truth auditor.

ADDITIVE feature: verifier.py + verify_cli.py. These tests exercise
ProbeEngine (git/http/fs/shell/json_get), RuleReasoner (decompose +
adjudicate), InjectedReasoner, LLMReasoner's no-API-key fallback, the
Verifier pipeline end-to-end (including the opt-in ledger record path),
the relay/claims-file/pending-ledger ingest helpers, and render_report.
"""
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.dsor import DecisionLedger
from mcp_server_nucleus.runtime.verifier import (
    Anchor,
    Claim,
    Evidence,
    InjectedReasoner,
    LLMReasoner,
    ProbeEngine,
    RuleReasoner,
    Verdict,
    Verifier,
    anchor_from_dict,
    classify_claim,
    ingest_claims_file,
    ingest_pending_ledger,
    ingest_relay,
    render_report,
)


import os
REPO = os.path.expanduser("~/nucleus")
REPO_ROOT = Path(__file__).resolve().parents[1]

_MANDATORY_FLAG = "NUCLEUS_VERIFIER_MANDATORY_ANCHORS"


def _head_sha() -> str:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


# ── Data classes ─────────────────────────────────────────────────

class TestDataClasses:
    def test_claim_defaults(self):
        c = Claim(claim_id="c1", source="pipeline", claimant="agent", assertion="it works")
        assert c.evidence_refs == []
        assert c.raw == {}
        assert c.timestamp is not None
        d = c.to_dict()
        assert d["claim_id"] == "c1"
        assert set(d.keys()) == {
            "claim_id", "source", "claimant", "assertion",
            "evidence_refs", "timestamp", "raw",
        }

    def test_anchor_defaults_critical_true(self):
        a = Anchor(anchor_id="a1", kind="fs", spec={"op": "file_exists", "path": "/tmp/x"}, description="d")
        assert a.critical is True
        assert a.to_dict()["kind"] == "fs"

    def test_evidence_ok_none_means_unverifiable(self):
        e = Evidence(anchor_id="a1", ok=None, detail="network down")
        assert e.ok is None
        assert e.to_dict()["ok"] is None

    def test_verdict_to_dict(self):
        v = Verdict(claim_id="c1", status="CONFIRMED", confidence=0.85, rationale="r")
        d = v.to_dict()
        assert d["status"] == "CONFIRMED"
        assert d["anchors"] == []
        assert d["evidence"] == []

    def test_anchor_from_dict_defaults(self):
        a = anchor_from_dict({}, idx=3, prefix="p")
        assert a.anchor_id == "p-3"
        assert a.kind == "manual"
        assert a.critical is True

    def test_anchor_from_dict_explicit(self):
        a = anchor_from_dict({
            "anchor_id": "custom", "kind": "fs", "spec": {"op": "file_exists"},
            "description": "d", "critical": False,
        })
        assert a.anchor_id == "custom"
        assert a.critical is False


# ── ProbeEngine: git ─────────────────────────────────────────────

class TestProbeEngineGit:
    def test_commit_exists_true_for_real_head(self):
        engine = ProbeEngine()
        sha = _head_sha()
        ev = engine.commit_exists(str(REPO_ROOT), sha)
        assert ev.ok is True
        assert sha in ev.detail

    def test_commit_exists_false_for_bogus_sha(self):
        engine = ProbeEngine()
        ev = engine.commit_exists(str(REPO_ROOT), "0000000deadbeef0000000deadbeef00000000")
        assert ev.ok is False

    def test_commit_exists_unverifiable_when_repo_missing(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.commit_exists(str(tmp_path / "does-not-exist"), "abc1234")
        assert ev.ok is None

    def test_commit_exists_unverifiable_when_not_a_git_repo(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.commit_exists(str(tmp_path), "abc1234")
        assert ev.ok is None
        assert "not inside a git work tree" in ev.detail

    def test_file_exists_at_head_true(self):
        engine = ProbeEngine()
        ev = engine.file_exists_at_head(str(REPO_ROOT), "pyproject.toml")
        assert ev.ok is True

    def test_file_exists_at_head_false(self):
        engine = ProbeEngine()
        ev = engine.file_exists_at_head(str(REPO_ROOT), "this/path/does/not/exist.xyz")
        assert ev.ok is False

    def test_log_grep_finds_a_commit(self):
        engine = ProbeEngine()
        # Every git repo has at least one commit; grep for something broad.
        r = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=str(REPO_ROOT),
                            capture_output=True, text=True, timeout=10)
        subject = r.stdout.strip()
        if not subject:
            pytest.skip("no commits with a subject to grep for")
        word = subject.split()[0]
        ev = engine.log_grep(str(REPO_ROOT), word)
        assert ev.ok is True

    def test_log_grep_no_match(self):
        engine = ProbeEngine()
        ev = engine.log_grep(str(REPO_ROOT), "definitely-not-a-real-commit-subject-zzzqqq")
        assert ev.ok is False

    def test_branch_contains_head_on_current_branch(self):
        engine = ProbeEngine()
        sha = _head_sha()
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(REPO_ROOT),
                            capture_output=True, text=True, timeout=10)
        branch = r.stdout.strip()
        if not branch or branch == "HEAD":
            pytest.skip("detached HEAD, no branch name to check")
        ev = engine.branch_contains(str(REPO_ROOT), sha, branch)
        assert ev.ok is True

    def test_branch_contains_false_for_bogus_branch(self):
        engine = ProbeEngine()
        sha = _head_sha()
        ev = engine.branch_contains(str(REPO_ROOT), sha, "definitely-not-a-real-branch-zzz")
        assert ev.ok is False


# ── ProbeEngine: git branch_exists (G1) ───────────────────────────

def _init_scratch_repo(tmp_path: Path) -> Path:
    """A minimal, throwaway git repo with one commit on a branch named
    'main' and one lightweight tag named 'not-a-branch' — used to test
    branch/commit anchors against known true/false cases without touching
    the real repo's branches, and to prove branch_exists does not conflate
    a same-named tag with an actual branch."""
    repo = tmp_path / "scratch_repo"
    repo.mkdir()
    run = lambda *cmd: subprocess.run(cmd, cwd=str(repo), check=True, capture_output=True, text=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    run("git", "add", "README.md")
    run("git", "commit", "-q", "-m", "initial")
    run("git", "branch", "-M", "main")  # rename current branch regardless of git's init default
    run("git", "tag", "not-a-branch")
    # An orphan branch with unrelated history — main's commit is genuinely
    # NOT an ancestor of it (a real "wrong branch" case, distinct from a
    # branch name that doesn't resolve at all).
    run("git", "checkout", "-q", "--orphan", "other-branch")
    (repo / "OTHER.md").write_text("y\n", encoding="utf-8")
    run("git", "add", "OTHER.md")
    run("git", "commit", "-q", "-m", "unrelated history")
    run("git", "checkout", "-q", "main")
    return repo


class TestProbeEngineGitBranchExists:
    def test_branch_exists_true(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        engine = ProbeEngine()
        ev = engine.branch_exists(str(repo), "main")
        assert ev.ok is True
        assert "main" in ev.detail

    def test_branch_exists_false_for_bogus_branch(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        engine = ProbeEngine()
        ev = engine.branch_exists(str(repo), "definitely-not-a-real-branch-zzz")
        assert ev.ok is False

    def test_branch_exists_false_for_a_tag_with_the_same_shape(self, tmp_path):
        """A tag is not a branch — branch_exists must not report a tag as an
        existing branch just because `git rev-parse --verify` alone would
        happily resolve it (that's why the implementation scopes the check
        to refs/heads/, not a bare ref)."""
        repo = _init_scratch_repo(tmp_path)
        engine = ProbeEngine()
        ev = engine.branch_exists(str(repo), "not-a-branch")
        assert ev.ok is False

    def test_branch_exists_unverifiable_when_repo_missing(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.branch_exists(str(tmp_path / "does-not-exist"), "main")
        assert ev.ok is None

    def test_branch_exists_unverifiable_when_not_a_git_repo(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.branch_exists(str(tmp_path), "main")
        assert ev.ok is None


# ── ProbeEngine: fs ──────────────────────────────────────────────

class TestProbeEngineFs:
    def test_file_exists_true(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hello")
        engine = ProbeEngine()
        ev = engine.file_exists(str(f))
        assert ev.ok is True

    def test_file_exists_false(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.file_exists(str(tmp_path / "nope.txt"))
        assert ev.ok is False

    def test_file_contains_true(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("the quick brown fox")
        engine = ProbeEngine()
        ev = engine.file_contains(str(f), "brown fox")
        assert ev.ok is True

    def test_file_contains_false(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("the quick brown fox")
        engine = ProbeEngine()
        ev = engine.file_contains(str(f), "purple elephant")
        assert ev.ok is False

    def test_file_contains_missing_file_is_false_not_none(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.file_contains(str(tmp_path / "missing.txt"), "x")
        assert ev.ok is False


# ── ProbeEngine: http (mocked) ───────────────────────────────────

class _FakeResponse:
    def __init__(self, status=200, body=b""):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, n=-1):
        return self._body


class TestProbeEngineHttp:
    def test_get_status_ok(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(status=200),
        )
        engine = ProbeEngine()
        ev = engine.get_status("https://example.invalid/health", expect_status=200)
        assert ev.ok is True

    def test_get_status_mismatch(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(status=200),
        )
        engine = ProbeEngine()
        ev = engine.get_status("https://example.invalid/health", expect_status=404)
        assert ev.ok is False

    def test_get_status_network_error_is_unverifiable(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        def _raise(req, timeout=10):
            raise urllib.error.URLError("no such host")

        monkeypatch.setattr(verifier_mod.urllib.request, "urlopen", _raise)
        engine = ProbeEngine()
        ev = engine.get_status("https://example.invalid/health")
        assert ev.ok is None

    def test_get_contains_true(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(body=b"<html>hello world</html>"),
        )
        engine = ProbeEngine()
        ev = engine.get_contains("https://example.invalid/", "hello world")
        assert ev.ok is True

    def test_get_contains_false(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(body=b"<html>hello world</html>"),
        )
        engine = ProbeEngine()
        ev = engine.get_contains("https://example.invalid/", "goodbye")
        assert ev.ok is False


class TestProbeEngineJsonGet:
    def _mock_json(self, monkeypatch, payload):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        body = json.dumps(payload).encode("utf-8")
        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(body=body),
        )

    def test_equals_ok(self, monkeypatch):
        self._mock_json(monkeypatch, {"total": 42})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "total", equals=42)
        assert ev.ok is True

    def test_equals_mismatch(self, monkeypatch):
        self._mock_json(monkeypatch, {"total": 42})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "total", equals=41)
        assert ev.ok is False

    def test_max_ok_and_exceeds(self, monkeypatch):
        self._mock_json(monkeypatch, {"price": 45})
        engine = ProbeEngine()
        ok_ev = engine.json_get("https://x.invalid/api", "price", max_val=200)
        assert ok_ev.ok is True
        exceed_ev = engine.json_get("https://x.invalid/api", "price", max_val=10)
        assert exceed_ev.ok is False

    def test_min_ok_and_below(self, monkeypatch):
        self._mock_json(monkeypatch, {"score": 7})
        engine = ProbeEngine()
        ok_ev = engine.json_get("https://x.invalid/api", "score", min_val=5)
        assert ok_ev.ok is True
        below_ev = engine.json_get("https://x.invalid/api", "score", min_val=9)
        assert below_ev.ok is False

    def test_contains(self, monkeypatch):
        self._mock_json(monkeypatch, {"name": "navy blazer"})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "name", contains="blazer")
        assert ev.ok is True

    def test_in_list(self, monkeypatch):
        self._mock_json(monkeypatch, {"items": [{"gender": "female"}]})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "items.0.gender", in_list=["female", "unisex", None])
        assert ev.ok is True

    def test_numeric_list_index_path(self, monkeypatch):
        self._mock_json(monkeypatch, {"items": [{"price": 10}, {"price": 20}]})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "items.1.price", equals=20)
        assert ev.ok is True

    def test_no_comparator_reports_value_unverifiable(self, monkeypatch):
        self._mock_json(monkeypatch, {"total": 42})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "total")
        assert ev.ok is None
        assert "42" in ev.detail

    def test_missing_path_is_none_value(self, monkeypatch):
        self._mock_json(monkeypatch, {"total": 42})
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "nope.nope", max_val=10)
        assert ev.ok is None  # value missing -> UNKNOWN, not a hard failure

    def test_invalid_json_is_unverifiable(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(body=b"not json{{{"),
        )
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "total", equals=1)
        assert ev.ok is None

    def test_network_error_is_unverifiable(self, monkeypatch):
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        def _raise(req, timeout=10):
            raise urllib.error.URLError("down")

        monkeypatch.setattr(verifier_mod.urllib.request, "urlopen", _raise)
        engine = ProbeEngine()
        ev = engine.json_get("https://x.invalid/api", "total", equals=1)
        assert ev.ok is None


# ── ProbeEngine: shell allowlist ─────────────────────────────────

class TestProbeEngineShell:
    def test_allowlisted_command_runs(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hi")
        engine = ProbeEngine()
        ev = engine.run_shell(["ls", str(f)])
        assert ev.ok is True

    def test_disallowed_command_rejected(self):
        engine = ProbeEngine()
        ev = engine.run_shell(["rm", "-rf", "/nonexistent"])
        assert ev.ok is None
        assert "not allowlisted" in ev.detail

    def test_empty_command_rejected(self):
        engine = ProbeEngine()
        ev = engine.run_shell([])
        assert ev.ok is None


# ── ProbeEngine.run_anchor dispatch ───────────────────────────────

class TestRunAnchorDispatch:
    def test_manual_anchor_is_unverifiable(self):
        engine = ProbeEngine()
        anchor = Anchor("m1", "manual", {}, "no deterministic check", critical=False)
        ev = engine.run_anchor(anchor)
        assert ev.ok is None
        assert ev.anchor_id == "m1"

    def test_unknown_kind_is_unverifiable(self):
        engine = ProbeEngine()
        anchor = Anchor("u1", "carrier-pigeon", {}, "?")
        ev = engine.run_anchor(anchor)
        assert ev.ok is None

    def test_git_anchor_uses_default_repo(self):
        engine = ProbeEngine(default_repo=str(REPO_ROOT))
        sha = _head_sha()
        anchor = Anchor("g1", "git", {"op": "commit_exists", "sha": sha}, "d")
        ev = engine.run_anchor(anchor)
        assert ev.ok is True
        assert ev.anchor_id == "g1"

    def test_git_anchor_without_repo_is_unverifiable(self):
        engine = ProbeEngine()
        anchor = Anchor("g2", "git", {"op": "commit_exists", "sha": "abc1234"}, "d")
        ev = engine.run_anchor(anchor)
        assert ev.ok is None

    def test_git_branch_exists_op_dispatches(self):
        engine = ProbeEngine(default_repo=str(REPO_ROOT))
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if not branch or branch == "HEAD":
            pytest.skip("detached HEAD, no branch name to check")
        anchor = Anchor("g3", "git", {"op": "branch_exists", "branch": branch}, "d")
        ev = engine.run_anchor(anchor)
        assert ev.ok is True
        assert ev.anchor_id == "g3"

    def test_fs_anchor_dispatch(self, tmp_path):
        f = tmp_path / "y.txt"
        f.write_text("data")
        engine = ProbeEngine()
        anchor = Anchor("f1", "fs", {"op": "file_exists", "path": str(f)}, "d")
        ev = engine.run_anchor(anchor)
        assert ev.ok is True

    def test_http_status_alias_dispatches_like_get_status(self, monkeypatch):
        # Curated/hand-authored anchor files commonly use the shorter
        # "status" op name instead of "get_status" — both must dispatch
        # identically.
        import mcp_server_nucleus.runtime.verifier as verifier_mod

        monkeypatch.setattr(
            verifier_mod.urllib.request, "urlopen",
            lambda req, timeout=10: _FakeResponse(status=200),
        )
        engine = ProbeEngine()
        anchor = Anchor("h1", "http", {"op": "status", "url": "https://x.invalid/", "expect_status": 200}, "d")
        ev = engine.run_anchor(anchor)
        assert ev.ok is True
        assert ev.anchor_id == "h1"


# ── RuleReasoner ─────────────────────────────────────────────────

class TestRuleReasonerDecompose:
    def test_extracts_git_sha(self):
        claim = Claim("c1", "pipeline", "agent", "commit abc1234def landed the fix")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 1
        assert anchors[0].kind == "git"
        assert anchors[0].spec["sha"] == "abc1234def"

    def test_extracts_url(self):
        claim = Claim("c2", "pipeline", "agent", "verified at https://example.com/health")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 1
        assert anchors[0].kind == "http"
        assert anchors[0].spec["url"] == "https://example.com/health"

    def test_extracts_both_sha_and_url(self):
        claim = Claim("c3", "pipeline", "agent", "commit abc1234def deployed, verify at https://example.com/status")
        anchors = RuleReasoner().decompose(claim)
        kinds = sorted(a.kind for a in anchors)
        assert kinds == ["git", "http"]

    def test_no_anchor_found_gives_manual(self):
        claim = Claim("c4", "pipeline", "agent", "I think it probably works now")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 1
        assert anchors[0].kind == "manual"
        assert anchors[0].critical is False

    def test_dedupes_repeated_shas(self):
        claim = Claim("c5", "pipeline", "agent", "abc1234def and again abc1234def")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 1


# ── RuleReasoner.decompose: GIT-BRANCH-EXISTS / GIT-COMMIT-EXISTS (G1) ──────

class TestRuleReasonerDecomposeGitClaims:
    def test_git_branch_exists_claim_shape(self):
        claim = Claim("g1", "pipeline", "agent", "GIT BRANCH EXISTS: main")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 1
        assert anchors[0].kind == "git"
        assert anchors[0].spec == {"op": "branch_exists", "branch": "main"}
        assert anchors[0].anchor_id == "git-branch-exists-main"

    def test_git_commit_exists_claim_shape_without_branch(self):
        claim = Claim("g2", "pipeline", "agent", "GIT COMMIT EXISTS: 11ed2420")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 1
        assert anchors[0].kind == "git"
        assert anchors[0].spec == {"op": "commit_exists", "sha": "11ed2420"}
        assert anchors[0].anchor_id == "git-commit-exists-11ed2420"

    def test_git_commit_exists_claim_shape_with_branch(self):
        claim = Claim("g3", "pipeline", "agent", "GIT COMMIT EXISTS: 11ed2420 on branch main")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 2
        by_op = {a.spec["op"]: a for a in anchors}
        assert by_op["commit_exists"].spec == {"op": "commit_exists", "sha": "11ed2420"}
        assert by_op["is_ancestor"].spec == {"op": "is_ancestor", "sha": "11ed2420", "ref": "main"}
        assert by_op["is_ancestor"].anchor_id == "git-commit-exists-11ed2420-on-main"

    def test_branch_and_commit_claims_compose_in_one_turn(self):
        """A single turn stating multiple facts (the demo's multi-line
        format) gets an anchor for EVERY fact, not just the first matched —
        additive, like the existing SHA+URL behavior (test_extracts_both_sha_
        and_url above), not mutually exclusive."""
        claim = Claim(
            "g4", "pipeline", "agent",
            "GIT BRANCH EXISTS: main\nGIT COMMIT EXISTS: 11ed2420 on branch main",
        )
        anchors = RuleReasoner().decompose(claim)
        anchor_ids = {a.anchor_id for a in anchors}
        assert anchor_ids == {
            "git-branch-exists-main",
            "git-commit-exists-11ed2420",
            "git-commit-exists-11ed2420-on-main",
        }

    def test_commit_exists_claim_does_not_also_get_a_generic_sha_anchor(self):
        """The generic SHA/cue-word detector (test_extracts_git_sha above)
        would otherwise ALSO fire on this text ('commit' is a cue word) and
        add a second, differently-named anchor for the identical fact —
        seen_shas is pre-seeded from the canonical-format pass specifically
        to prevent that duplication."""
        claim = Claim("g5", "pipeline", "agent", "GIT COMMIT EXISTS: 11ed2420 on branch main")
        anchors = RuleReasoner().decompose(claim)
        assert len(anchors) == 2  # commit_exists + is_ancestor, no third "git-sha-*" anchor

    def test_a_file_claim_alongside_git_claims_gets_no_fs_anchor(self):
        """The old bare-filename fallback is still gated by `if not anchors`:
        a bare filename in prose does NOT get an fs anchor when a git claim
        is also present. The explicit "FILE EXISTS:" prefix is handled
        separately and is unconditional."""
        claim = Claim(
            "g6", "pipeline", "agent",
            "AGENTS.md is on disk.\nGIT BRANCH EXISTS: main",
        )
        anchors = RuleReasoner().decompose(claim)
        assert all(a.kind == "git" for a in anchors)
        assert not any(a.kind == "fs" for a in anchors)


class TestRuleReasonerAdjudicate:
    def test_refuted_when_any_critical_false(self):
        claim = Claim("c1", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {
            "a1": Anchor("a1", "fs", {}, "d1", critical=True),
            "a2": Anchor("a2", "fs", {}, "d2", critical=True),
        }
        evidence = [Evidence("a1", True, "ok"), Evidence("a2", False, "nope")]
        verdict = reasoner.adjudicate(claim, evidence)
        assert verdict.status == "REFUTED"
        assert verdict.confidence == 0.9

    def test_confirmed_when_all_critical_true(self):
        claim = Claim("c2", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {
            "a1": Anchor("a1", "fs", {}, "d1", critical=True),
            "a2": Anchor("a2", "fs", {}, "d2", critical=True),
        }
        evidence = [Evidence("a1", True, "ok"), Evidence("a2", True, "ok")]
        verdict = reasoner.adjudicate(claim, evidence)
        assert verdict.status == "CONFIRMED"
        assert verdict.confidence == 0.85

    def test_unverifiable_when_all_none(self):
        claim = Claim("c3", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": Anchor("a1", "manual", {}, "d1", critical=False)}
        evidence = [Evidence("a1", None, "no anchor")]
        verdict = reasoner.adjudicate(claim, evidence)
        assert verdict.status == "UNVERIFIABLE"
        assert "a1" in verdict.remediation

    def test_partial_when_some_true_some_none(self):
        claim = Claim("c4", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {
            "a1": Anchor("a1", "fs", {}, "d1", critical=True),
            "a2": Anchor("a2", "http", {}, "d2", critical=True),
        }
        evidence = [Evidence("a1", True, "ok"), Evidence("a2", None, "network down")]
        verdict = reasoner.adjudicate(claim, evidence)
        assert verdict.status == "PARTIAL"
        assert verdict.confidence == 0.5

    def test_unverifiable_with_no_evidence_at_all(self):
        claim = Claim("c5", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        verdict = reasoner.adjudicate(claim, [])
        assert verdict.status == "UNVERIFIABLE"

    def test_non_critical_evidence_does_not_cause_refuted(self):
        claim = Claim("c6", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {
            "a1": Anchor("a1", "fs", {}, "d1", critical=True),
            "a2": Anchor("a2", "manual", {}, "d2", critical=False),
        }
        evidence = [Evidence("a1", True, "ok"), Evidence("a2", False, "irrelevant")]
        verdict = reasoner.adjudicate(claim, evidence)
        # a2 is non-critical, so only a1 (True) counts -> CONFIRMED
        assert verdict.status == "CONFIRMED"

    def test_rationale_mentions_every_anchor(self):
        claim = Claim("c7", "pipeline", "agent", "x")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": Anchor("a1", "fs", {}, "d1", critical=True)}
        evidence = [Evidence("a1", True, "file found")]
        verdict = reasoner.adjudicate(claim, evidence)
        assert "a1" in verdict.rationale
        assert "file found" in verdict.rationale


# ── InjectedReasoner ─────────────────────────────────────────────

class TestInjectedReasoner:
    def test_uses_injected_anchors(self):
        anchor = Anchor("special", "fs", {"op": "file_exists", "path": "/tmp/x"}, "hand-verified")
        claim = Claim("c1", "pipeline", "agent", "irrelevant text with no sha or url")
        reasoner = InjectedReasoner({"c1": [anchor]})
        anchors = reasoner.decompose(claim)
        assert anchors == [anchor]

    def test_falls_back_to_rule_reasoner_for_unmapped_claim(self):
        claim = Claim("c2", "pipeline", "agent", "commit abc1234def landed")
        reasoner = InjectedReasoner({})
        anchors = reasoner.decompose(claim)
        assert anchors[0].kind == "git"

    def test_adjudicate_delegates_to_rule_reasoner_with_correct_criticality(self):
        anchor = Anchor("special", "fs", {}, "hand-verified", critical=True)
        claim = Claim("c3", "pipeline", "agent", "x")
        reasoner = InjectedReasoner({"c3": [anchor]})
        reasoner.decompose(claim)
        evidence = [Evidence("special", True, "confirmed by probe")]
        verdict = reasoner.adjudicate(claim, evidence)
        assert verdict.status == "CONFIRMED"


# ── LLMReasoner (no API key) ─────────────────────────────────────

class TestLLMReasonerImportSafety:
    def test_imports_and_instantiates_without_api_keys(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        reasoner = LLMReasoner()
        assert reasoner._llm_capable() is False

    def test_decompose_falls_back_to_rule_reasoner_without_keys(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        reasoner = LLMReasoner()
        claim = Claim("c1", "pipeline", "agent", "commit abc1234def landed the fix")
        anchors = reasoner.decompose(claim)
        assert len(anchors) == 1
        assert anchors[0].kind == "git"

    def test_adjudicate_delegates_to_rule_reasoner(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        reasoner = LLMReasoner()
        claim = Claim("c1", "pipeline", "agent", "x")
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status in {"CONFIRMED", "PARTIAL", "UNVERIFIABLE", "REFUTED"}


# ── Verifier end-to-end ──────────────────────────────────────────

class _AllOkStubProbeEngine:
    """Stub ProbeEngine: every anchor is confirmed. Used to test the
    Verifier pipeline in isolation from real git/http/fs probing."""

    def __init__(self):
        self.calls = []

    def run_anchor(self, anchor):
        self.calls.append(anchor.anchor_id)
        return Evidence(anchor.anchor_id, True, f"stub confirmed {anchor.anchor_id}", None)


class _AllFailStubProbeEngine:
    def run_anchor(self, anchor):
        return Evidence(anchor.anchor_id, False, f"stub refuted {anchor.anchor_id}", None)


class _AllNoneStubProbeEngine:
    def run_anchor(self, anchor):
        return Evidence(anchor.anchor_id, None, "stub could not verify", None)


class TestVerifierEndToEnd:
    def test_verify_confirmed_with_stub(self):
        claim = Claim("c1", "pipeline", "agent", "see https://example.com/status for proof")
        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllOkStubProbeEngine(), record=False)
        verdict = verifier.verify(claim)
        assert verdict.status == "CONFIRMED"
        assert verdict.claim_id == "c1"

    def test_verify_refuted_with_stub(self):
        claim = Claim("c2", "pipeline", "agent", "commit abc1234def fixed it")
        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllFailStubProbeEngine(), record=False)
        verdict = verifier.verify(claim)
        assert verdict.status == "REFUTED"

    def test_verify_all_returns_one_verdict_per_claim(self):
        claims = [
            Claim("c1", "pipeline", "agent", "commit abc1234def landed"),
            Claim("c2", "pipeline", "agent", "https://example.com/ok"),
            Claim("c3", "pipeline", "agent", "just vibes, no proof"),
        ]
        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllOkStubProbeEngine(), record=False)
        verdicts = verifier.verify_all(claims)
        assert len(verdicts) == 3
        assert all(v.status in {"CONFIRMED", "REFUTED", "UNVERIFIABLE", "PARTIAL"} for v in verdicts)

    def test_verify_manual_anchor_with_real_probe_engine_is_unverifiable(self):
        # Real ProbeEngine (unlike the AllOk stub) always reports ok=None
        # for kind="manual" — this is what "no proof in the claim text"
        # actually looks like end-to-end.
        claim = Claim("c3", "pipeline", "agent", "just vibes, no proof")
        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=ProbeEngine(), record=False)
        verdict = verifier.verify(claim)
        assert verdict.status == "UNVERIFIABLE"

    def test_verify_does_not_record_without_record_flag(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="deploy", reasoning="tests pass", context_hash="h1")
        claim = ingest_pending_ledger(ledger)[0]

        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllOkStubProbeEngine(),
                             ledger=ledger, record=False)
        verifier.verify(claim)

        assert ledger.get_decision(entry.decision_id).audit_status == "PENDING"

    def test_verify_records_when_record_true_and_source_is_ledger(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="deploy", reasoning="tests pass", context_hash="h1")
        claim = ingest_pending_ledger(ledger)[0]
        assert claim.source == "ledger"

        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllNoneStubProbeEngine(),
                             ledger=ledger, record=True)
        verdict = verifier.verify(claim)

        assert verdict.status == "UNVERIFIABLE"
        updated = ledger.get_decision(entry.decision_id)
        assert updated.audit_status == "UNVERIFIABLE"
        assert updated.metadata.get("auditor_notes") == verdict.rationale

    def test_verify_does_not_record_when_source_is_not_ledger(self, tmp_path):
        brain = tmp_path / "brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="deploy", reasoning="tests pass", context_hash="h1")
        # Same decision_id, but a claim that claims to come from 'relay' —
        # Verifier must never write back for non-ledger-sourced claims.
        claim = Claim(entry.decision_id, "relay", "someone", "deploy :: tests pass")

        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllOkStubProbeEngine(),
                             ledger=ledger, record=True)
        verifier.verify(claim)

        assert ledger.get_decision(entry.decision_id).audit_status == "PENDING"

    def test_verifier_never_writes_outside_scratch_ledger(self, tmp_path):
        """Sanity check that record=True only ever touches the ledger the
        caller explicitly constructed — no ambient global brain writes."""
        brain = tmp_path / "scratch-brain"
        ledger = DecisionLedger(brain_path=brain)
        entry = ledger.record_decision(intent="x", reasoning="y", context_hash="h")
        claim = ingest_pending_ledger(ledger)[0]

        verifier = Verifier(reasoner=RuleReasoner(), probe_engine=_AllOkStubProbeEngine(),
                             ledger=ledger, record=True)
        verifier.verify(claim)

        # Only the scratch brain's ledger file was touched.
        assert ledger.ledger_file.exists()
        assert ledger.ledger_file.is_relative_to(tmp_path)


# ── Verifier end-to-end: GIT-BRANCH-EXISTS / GIT-COMMIT-EXISTS (G1/G2) ──────

class TestVerifierEndToEndGitClaims:
    """Real ProbeEngine, real (throwaway, per-test) git repo — no stubs, no
    mocking of the git subprocess calls. True/false/hedged cases per the
    G1 brief's Track G2."""

    def _verifier(self, repo: Path) -> Verifier:
        return Verifier(reasoner=RuleReasoner(), probe_engine=ProbeEngine(default_repo=str(repo)), record=False)

    def test_true_branch_claim_confirms(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        claim = Claim("t1", "agent_os", "agent", "GIT BRANCH EXISTS: main")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "CONFIRMED"
        assert "git-branch-exists-main" in verdict.rationale

    def test_false_branch_claim_refutes(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        claim = Claim("t2", "agent_os", "agent", "GIT BRANCH EXISTS: does-not-exist-zzz")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "REFUTED"

    def test_true_commit_claim_on_branch_confirms(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True).stdout.strip()
        claim = Claim("t3", "agent_os", "agent", f"GIT COMMIT EXISTS: {sha} on branch main")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "CONFIRMED"

    def test_false_commit_claim_refutes(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        fake_sha = "deadbeef" * 5  # well-formed hex, does not exist
        claim = Claim("t4", "agent_os", "agent", f"GIT COMMIT EXISTS: {fake_sha} on branch main")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "REFUTED"

    def test_true_commit_but_wrong_branch_refutes(self, tmp_path):
        """The commit is real, but it is not on the named branch (a real,
        resolvable branch with unrelated orphan history) — the is_ancestor
        anchor must fail even though commit_exists passes, because a
        claim's critical anchors are ANDed."""
        repo = _init_scratch_repo(tmp_path)
        sha = subprocess.run(["git", "rev-parse", "main"], cwd=str(repo), capture_output=True, text=True).stdout.strip()
        claim = Claim("t5", "agent_os", "agent", f"GIT COMMIT EXISTS: {sha} on branch other-branch")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "REFUTED"

    def test_commit_on_bogus_branch_name_is_unverifiable_not_refuted(self, tmp_path):
        """Distinct from the case above: a branch name that does not
        resolve to anything at all is an HONEST "cannot determine ancestry"
        (ProbeEngine.is_ancestor's tri-state: only a real 0/1 git exit code
        maps to True/False; anything else, including an unresolvable ref,
        is ok=None) — not the same as a definite "not on that branch"."""
        repo = _init_scratch_repo(tmp_path)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True).stdout.strip()
        claim = Claim("t5b", "agent_os", "agent", f"GIT COMMIT EXISTS: {sha} on branch does-not-exist-zzz")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "PARTIAL"

    def test_hedged_branch_claim_downgrades_to_partial(self, tmp_path):
        """Mirrors test_hedged_claim_downgrades_to_partial_not_confirmed in
        the adversarial suite, for the new git claim shapes: a passing
        deterministic anchor proves the branch exists, but hedge language in
        the assertion means the claimant only speculated, not asserted."""
        repo = _init_scratch_repo(tmp_path)
        claim = Claim("t6", "agent_os", "agent", "I think GIT BRANCH EXISTS: main, though I am not fully certain.")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "PARTIAL", (
            f"expected PARTIAL for a hedged branch claim, got {verdict.status}: {verdict.rationale}"
        )

    def test_hedged_commit_claim_downgrades_to_partial(self, tmp_path):
        repo = _init_scratch_repo(tmp_path)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True).stdout.strip()
        claim = Claim("t7", "agent_os", "agent", f"I believe GIT COMMIT EXISTS: {sha} on branch main may be true.")
        verdict = self._verifier(repo).verify(claim)
        assert verdict.status == "PARTIAL", (
            f"expected PARTIAL for a hedged commit claim, got {verdict.status}: {verdict.rationale}"
        )

    def test_integration_synthetic_loop_cell_exercises_both_file_and_git_anchors(self, tmp_path):
        """G2 item 4: a synthetic loop cell (two turns, mirroring how
        boot_cell verifies one outcome per turn) — one turn stating a file
        claim, one stating a git claim — with both anchors independently
        exercised and both verdicts landing CONFIRMED. Two turns, not one
        combined turn: see test_a_file_claim_alongside_git_claims_gets_no_fs_
        anchor above for why a single combined turn would silently drop the
        file anchor (a pre-existing, out-of-scope limitation of D1's
        fallback-only design, not something this brief changes)."""
        repo = _init_scratch_repo(tmp_path)
        verifier = self._verifier(repo)

        file_turn = Claim("cell-1-turn-1", "agent_os", "agent", "FILE EXISTS: README.md")
        git_turn = Claim("cell-1-turn-2", "agent_os", "agent", "GIT BRANCH EXISTS: main")

        # ProbeEngine(default_repo=repo) resolves the bare "README.md" path
        # against the scratch repo, same as production's default_repo wiring.
        file_verdict = verifier.verify(file_turn)
        git_verdict = verifier.verify(git_turn)

        assert file_verdict.status == "CONFIRMED"
        assert any(a["kind"] == "fs" for a in file_verdict.anchors)
        assert git_verdict.status == "CONFIRMED"
        assert any(a["kind"] == "git" for a in git_verdict.anchors)


# ── ingest_relay ─────────────────────────────────────────────────

class TestIngestRelay:
    def test_missing_dir_returns_empty(self, tmp_path):
        assert ingest_relay(tmp_path / "nope") == []

    def test_parses_results_and_conclusion(self, tmp_path):
        relay_dir = tmp_path / "relay"
        relay_dir.mkdir()
        (relay_dir / "20260101T000000Z_test.json").write_text(json.dumps({
            "id": "relay_1",
            "from": "cowork",
            "subject": "headline claim",
            "timestamp": "2026-01-01T00:00:00Z",
            "body": {
                "results": ["result one", "result two", ""],
                "conclusion": "everything is green",
            },
        }), encoding="utf-8")

        claims = ingest_relay(relay_dir)
        assertions = [c.assertion for c in claims]
        assert "result one" in assertions
        assert "result two" in assertions
        assert "everything is green" in assertions
        # empty-string result entries are skipped
        assert "" not in assertions
        assert all(c.source == "relay" for c in claims)
        assert all(c.claimant == "cowork" for c in claims)

    def test_falls_back_to_subject_when_no_conclusion(self, tmp_path):
        relay_dir = tmp_path / "relay"
        relay_dir.mkdir()
        (relay_dir / "msg.json").write_text(json.dumps({
            "from": "cc",
            "subject": "the headline",
            "body": {"summary": "no results or conclusion key here"},
        }), encoding="utf-8")

        claims = ingest_relay(relay_dir)
        assert len(claims) == 1
        assert claims[0].assertion == "the headline"

    def test_caps_results_at_ten(self, tmp_path):
        relay_dir = tmp_path / "relay"
        relay_dir.mkdir()
        (relay_dir / "msg.json").write_text(json.dumps({
            "from": "cc",
            "body": {"results": [f"item {i}" for i in range(25)]},
        }), encoding="utf-8")

        claims = ingest_relay(relay_dir)
        assert len(claims) == 10

    def test_recurses_into_peer_subdirectories(self, tmp_path):
        # Standard Nucleus relay layout: .brain/relay/<peer>/*.json, not
        # flat files directly under the relay directory.
        relay_dir = tmp_path / "relay"
        peer_dir = relay_dir / "claude_code_main"
        peer_dir.mkdir(parents=True)
        (peer_dir / "msg.json").write_text(json.dumps({
            "from": "cc", "subject": "nested headline", "body": {},
        }), encoding="utf-8")

        claims = ingest_relay(relay_dir)
        assert len(claims) == 1
        assert claims[0].assertion == "nested headline"

    def test_skips_unparseable_json(self, tmp_path):
        relay_dir = tmp_path / "relay"
        relay_dir.mkdir()
        (relay_dir / "bad.json").write_text("not json{{{", encoding="utf-8")
        (relay_dir / "good.json").write_text(json.dumps({
            "from": "cc", "subject": "ok", "body": {},
        }), encoding="utf-8")

        claims = ingest_relay(relay_dir)
        assert len(claims) == 1
        assert claims[0].assertion == "ok"


# ── ingest_pending_ledger ────────────────────────────────────────

class TestIngestPendingLedger:
    def test_only_pending_entries_become_claims(self, tmp_path):
        ledger = DecisionLedger(brain_path=tmp_path / "brain")
        pending = ledger.record_decision(intent="deploy", reasoning="ready", context_hash="h1")
        approved = ledger.record_decision(intent="skip", reasoning="already done", context_hash="h2")
        ledger.update_audit_status(approved.decision_id, "APPROVED")

        claims = ingest_pending_ledger(ledger)
        ids = [c.claim_id for c in claims]
        assert pending.decision_id in ids
        assert approved.decision_id not in ids

    def test_assertion_is_intent_and_reasoning(self, tmp_path):
        ledger = DecisionLedger(brain_path=tmp_path / "brain")
        ledger.record_decision(intent="deploy", reasoning="tests pass", context_hash="h1")
        claims = ingest_pending_ledger(ledger)
        assert claims[0].assertion == "deploy :: tests pass"
        assert claims[0].source == "ledger"


# ── ingest_claims_file ───────────────────────────────────────────

class TestIngestClaimsFile:
    def test_parses_bare_array(self, tmp_path):
        f = tmp_path / "claims.json"
        f.write_text(json.dumps([
            {"claim_id": "c1", "assertion": "it works", "source": "manual"},
            {"claim_id": "c2", "assertion": "it also works"},
        ]), encoding="utf-8")

        claims, anchor_map = ingest_claims_file(f)
        assert len(claims) == 2
        assert claims[0].claim_id == "c1"
        assert claims[0].source == "manual"
        assert claims[1].source == "pipeline"  # default
        assert anchor_map == {}

    def test_parses_wrapped_object(self, tmp_path):
        f = tmp_path / "claims.json"
        f.write_text(json.dumps({"claims": [{"claim_id": "c1", "assertion": "x"}]}), encoding="utf-8")
        claims, _ = ingest_claims_file(f)
        assert len(claims) == 1

    def test_inline_anchors_become_anchor_map(self, tmp_path):
        f = tmp_path / "claims.json"
        f.write_text(json.dumps([{
            "claim_id": "c1",
            "assertion": "the endpoint is healthy",
            "anchors": [
                {"kind": "http", "spec": {"op": "get_status", "url": "https://x.invalid/health"}, "description": "d"},
            ],
        }]), encoding="utf-8")

        claims, anchor_map = ingest_claims_file(f)
        assert "c1" in anchor_map
        assert len(anchor_map["c1"]) == 1
        assert anchor_map["c1"][0].kind == "http"

    def test_generates_claim_id_when_missing(self, tmp_path):
        f = tmp_path / "claims.json"
        f.write_text(json.dumps([{"assertion": "x"}]), encoding="utf-8")
        claims, _ = ingest_claims_file(f)
        assert claims[0].claim_id == "claims-0"

    def test_end_to_end_with_injected_reasoner(self, tmp_path):
        target = tmp_path / "proof.txt"
        target.write_text("shipped")
        f = tmp_path / "claims.json"
        f.write_text(json.dumps([{
            "claim_id": "c1",
            "assertion": "proof.txt exists on disk",
            "anchors": [
                {"kind": "fs", "spec": {"op": "file_exists", "path": str(target)}, "description": "d", "critical": True},
            ],
        }]), encoding="utf-8")

        claims, anchor_map = ingest_claims_file(f)
        verifier = Verifier(reasoner=InjectedReasoner(anchor_map), probe_engine=ProbeEngine(), record=False)
        verdicts = verifier.verify_all(claims)
        assert verdicts[0].status == "CONFIRMED"

    def test_rejects_non_list_non_dict_payload(self, tmp_path):
        f = tmp_path / "claims.json"
        f.write_text(json.dumps("just a string"), encoding="utf-8")
        with pytest.raises(ValueError):
            ingest_claims_file(f)


# ── render_report ────────────────────────────────────────────────

class TestRenderReport:
    def test_empty_report(self):
        report = render_report([])
        assert "TOTAL=0" in report
        assert "(no claims)" in report

    def test_report_contains_status_counts(self):
        verdicts = [
            Verdict("c1", "CONFIRMED", 0.85, "r1"),
            Verdict("c2", "CONFIRMED", 0.85, "r2"),
            Verdict("c3", "REFUTED", 0.9, "r3"),
        ]
        report = render_report(verdicts)
        assert "CONFIRMED=2" in report
        assert "REFUTED=1" in report
        assert "TOTAL=3" in report

    def test_long_claim_id_and_rationale_are_truncated(self):
        v = Verdict("c" * 50, "UNVERIFIABLE", 0.2, "r" * 200)
        report = render_report([v])
        lines = report.splitlines()
        data_line = [ln for ln in lines if ln.startswith("cccc")][0]
        assert "…" in data_line
        assert "..." in data_line


# ════════════════════════════════════════════════════════════════
# MANDATORY-ANCHOR DOCTRINE (flag-gated: NUCLEUS_VERIFIER_MANDATORY_ANCHORS)
# ANCHOR_DOCTRINE.md §3 (C1) + REFEREE_CONFINEMENT.md §3 (C2).
# Every test in this section is EXPLICIT about the flag; the flag-OFF path
# must stay byte-identical to the pre-doctrine behavior tested above.
# ════════════════════════════════════════════════════════════════

# ── ProbeEngine.is_ancestor (the mandatory git anchor) ───────────

class TestProbeEngineIsAncestor:
    def test_is_ancestor_true_reflexive(self):
        # A commit is an ancestor of itself (`--is-ancestor` is reflexive).
        engine = ProbeEngine()
        sha = _head_sha()
        ev = engine.is_ancestor(str(REPO_ROOT), sha, sha)
        assert ev.ok is True
        assert sha in ev.detail

    def test_is_ancestor_false_for_descendant_ref(self):
        engine = ProbeEngine()
        sha = _head_sha()
        r = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=str(REPO_ROOT),
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            pytest.skip("no parent commit to test non-ancestry against")
        # HEAD is NOT an ancestor of its own parent -> deterministic False.
        ev = engine.is_ancestor(str(REPO_ROOT), sha, "HEAD~1")
        assert ev.ok is False

    def test_is_ancestor_unverifiable_for_missing_ref(self):
        engine = ProbeEngine()
        sha = _head_sha()
        ev = engine.is_ancestor(str(REPO_ROOT), sha, "refs/heads/definitely-not-a-real-ref-zzz")
        assert ev.ok is None  # cannot resolve ref -> honest UNKNOWN, not False

    def test_is_ancestor_unverifiable_when_repo_missing(self, tmp_path):
        engine = ProbeEngine()
        ev = engine.is_ancestor(str(tmp_path / "nope"), "abc1234", "origin/main")
        assert ev.ok is None

    def test_is_ancestor_dispatches_via_run_anchor(self):
        engine = ProbeEngine(default_repo=str(REPO_ROOT))
        sha = _head_sha()
        anchor = Anchor("g-anc", "git", {"op": "is_ancestor", "sha": sha, "ref": sha}, "d")
        ev = engine.run_anchor(anchor)
        assert ev.ok is True
        assert ev.anchor_id == "g-anc"


# ── C2: claim-class classifier (join-UP + ⊤) ─────────────────────

class TestClassifyClaim:
    def test_deployed_live_class(self):
        assert "DEPLOYED-LIVE" in classify_claim("/one is live in production")

    def test_code_exists_class(self):
        assert "CODE-EXISTS" in classify_claim("built the feature and merged the commit")

    def test_behavior_correct_class(self):
        assert "BEHAVIOR-CORRECT" in classify_claim("the endpoint returns the correct total")

    def test_unknown_class_is_top_not_weak(self):
        # An assertion matching no known class classifies to the ⊤ element —
        # maximally strong, never silently a weak class.
        classes = classify_claim("some vague statement about vibes")
        assert classes == frozenset({"UNKNOWN"})

    def test_ambiguous_claim_joins_up(self):
        # A shipped-live claim that also mentions being built matches BOTH
        # DEPLOYED-LIVE and CODE-EXISTS — the join, not a single weaker class.
        classes = classify_claim("Feature built end-to-end and live in production")
        assert {"DEPLOYED-LIVE", "CODE-EXISTS"}.issubset(classes)


# ── C1: RuleReasoner._decompose_anchors under the flag ───────────

class TestDecomposeMandatoryAnchors:
    def test_flag_off_shipped_sha_stays_commit_exists(self, monkeypatch):
        monkeypatch.delenv(_MANDATORY_FLAG, raising=False)
        claim = Claim("c", "relay", "agent", "shipped commit abc1234def live in production")
        anchors = RuleReasoner()._decompose_anchors(claim)
        git_anchors = [a for a in anchors if a.kind == "git"]
        assert len(git_anchors) == 1
        assert git_anchors[0].spec["op"] == "commit_exists"

    def test_flag_on_shipped_sha_becomes_is_ancestor(self, monkeypatch):
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        claim = Claim("c", "relay", "agent", "shipped commit abc1234def live in production")
        anchors = RuleReasoner()._decompose_anchors(claim)
        git_anchors = [a for a in anchors if a.kind == "git"]
        assert len(git_anchors) == 1
        assert git_anchors[0].spec["op"] == "is_ancestor"
        assert git_anchors[0].spec["ref"] == "origin/main"

    def test_flag_on_non_deployment_sha_stays_commit_exists(self, monkeypatch):
        # The ancestry upgrade only applies to shipped/live/deployed claims;
        # a bare "commit exists" style claim keeps commit_exists.
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        claim = Claim("c", "relay", "agent", "commit abc1234def is in the tree")
        anchors = RuleReasoner()._decompose_anchors(claim)
        git_anchors = [a for a in anchors if a.kind == "git"]
        assert len(git_anchors) == 1
        assert git_anchors[0].spec["op"] == "commit_exists"

    def test_flag_on_live_url_becomes_build_identity_manual(self, monkeypatch):
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        claim = Claim("c", "relay", "agent", "https://composedfit.com/one is live in production")
        anchors = RuleReasoner()._decompose_anchors(claim)
        # No bare get_status 200 anchor survives; the URL becomes a critical
        # build-identity (manual) requirement instead.
        assert not any(a.kind == "http" and a.spec.get("op") == "get_status" for a in anchors)
        build = [a for a in anchors if a.kind == "manual" and "build-identity" in a.description]
        assert len(build) == 1
        assert build[0].critical is True

    def test_flag_off_live_url_stays_bare_200(self, monkeypatch):
        monkeypatch.delenv(_MANDATORY_FLAG, raising=False)
        claim = Claim("c", "relay", "agent", "https://composedfit.com/one is live in production")
        anchors = RuleReasoner()._decompose_anchors(claim)
        http = [a for a in anchors if a.kind == "http"]
        assert len(http) == 1
        assert http[0].spec["op"] == "get_status"


# ── C2: confinement cap in adjudicate ────────────────────────────

class TestConfinementCap:
    def _confirm_engine(self):
        return _AllOkStubProbeEngine()

    def test_flag_off_adjacent_anchors_still_confirm(self, monkeypatch):
        # Byte-identical old behavior: adjacent commit_exists anchors on a
        # shipped claim CONFIRM when the flag is off.
        monkeypatch.delenv(_MANDATORY_FLAG, raising=False)
        anchor = Anchor("a1", "git", {"op": "commit_exists", "sha": "abc1234"}, "d", critical=True)
        claim = Claim("c1", "relay", "agent", "shipped commit abc1234 live in production")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status == "CONFIRMED"

    def test_flag_on_adjacent_only_caps_to_partial(self, monkeypatch):
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        anchor = Anchor("a1", "git", {"op": "commit_exists", "sha": "abc1234"}, "d", critical=True)
        claim = Claim("c1", "relay", "agent", "shipped commit abc1234 live in production")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status == "PARTIAL"
        assert "mandatory" in verdict.remediation.lower()

    def test_flag_on_mandatory_anchor_present_still_confirms(self, monkeypatch):
        # A CODE-EXISTS claim whose passing anchor IS the mandatory is_ancestor
        # anchor stays CONFIRMED — the cap only bites adjacent-only sets.
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        anchor = Anchor("a1", "git", {"op": "is_ancestor", "sha": "abc1234", "ref": "origin/main"},
                        "d", critical=True)
        claim = Claim("c1", "relay", "agent", "commit abc1234 landed and merged")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status == "CONFIRMED"

    def test_flag_on_behavior_correct_value_anchor_confirms(self, monkeypatch):
        # inr-scope-style: a json_get value anchor is the mandatory anchor for
        # BEHAVIOR-CORRECT -> stays CONFIRMED under the flag.
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        anchor = Anchor("a1", "http", {"op": "json_get", "url": "https://x/api", "path": "total", "equals": 5},
                        "d", critical=True)
        claim = Claim("c1", "relay", "agent", "the catalog scope shows 5 items")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status == "CONFIRMED"

    def test_flag_on_file_exists_direct_match_confirms_despite_spurious_join(self, monkeypatch):
        # G4 scale-test regression: a FILE-EXISTS claim whose path contains
        # "/Users/..." spuriously joins BUSINESS-STATE (via \busers?\b), which
        # has no mandatory anchor. The direct-match exemption must still let
        # the passing fs:file_exists anchor yield CONFIRMED — the spurious
        # manual-only join cannot poison a direct (non-adjacent) match.
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        anchor = Anchor("a1", "fs", {"op": "file_exists", "path": "DECISIONS.md"}, "d", critical=True)
        claim = Claim("c1", "relay", "agent",
                      f"Verify that DECISIONS.md exists in {REPO}")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status == "CONFIRMED"

    def test_flag_on_file_exists_failing_anchor_refutes(self, monkeypatch):
        # A FILE-EXISTS claim whose fs:file_exists anchor FAILS (file genuinely
        # absent) is REFUTED — the direct-match exemption only lifts the cap
        # for PASSING anchors; a real negative still wins.
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        anchor = Anchor("a1", "fs", {"op": "file_exists", "path": "nope_missing.md"}, "d", critical=True)
        claim = Claim("c1", "relay", "agent",
                      f"Verify that nope_missing.md exists in {REPO}")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", False, "file does not exist")])
        assert verdict.status == "REFUTED"

    def test_flag_on_adjacent_git_for_file_claim_still_partial(self, monkeypatch):
        # The exemption is for DIRECT matches only. A passing git anchor on a
        # file-existence claim is ADJACENT (git is not FILE-EXISTS's mandatory
        # fs:file_exists), so the doctrine cap still bites -> PARTIAL.
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        anchor = Anchor("a1", "git", {"op": "commit_exists", "sha": "abc1234"}, "d", critical=True)
        claim = Claim("c1", "relay", "agent",
                      f"Verify that DECISIONS.md exists in {REPO}")
        reasoner = RuleReasoner()
        reasoner._anchor_index = {"a1": anchor}
        verdict = reasoner.adjudicate(claim, [Evidence("a1", True, "ok")])
        assert verdict.status == "PARTIAL"


# ── ACCEPTANCE (HANDOFF_BACKLOG §C, item C1) ─────────────────────

class TestMandatoryAnchorAcceptance:
    """The graded acceptance: with the flag ON, the shipped
    demo/verifier/curated_claims.json claim `one-shipped-live` must
    adjudicate PARTIAL (its commit_exists + bare-200 anchors are all
    ADJACENT per ANCHOR_DOCTRINE §3/§4), not CONFIRMED."""

    CURATED = REPO_ROOT / "demo" / "verifier" / "curated_claims.json"

    def _verdict_for(self, claim_id):
        claims, anchor_map = ingest_claims_file(self.CURATED)
        claim = next(c for c in claims if c.claim_id == claim_id)
        # Stub probe engine confirms every anchor, so the ONLY thing that can
        # move the verdict off CONFIRMED is the doctrine cap itself.
        verifier = Verifier(reasoner=InjectedReasoner(anchor_map),
                            probe_engine=_AllOkStubProbeEngine(), record=False)
        return verifier.verify(claim)

    def test_one_shipped_live_confirmed_when_flag_off(self, monkeypatch):
        monkeypatch.delenv(_MANDATORY_FLAG, raising=False)
        assert self._verdict_for("one-shipped-live").status == "CONFIRMED"

    def test_one_shipped_live_partial_when_flag_on(self, monkeypatch):
        monkeypatch.setenv(_MANDATORY_FLAG, "1")
        verdict = self._verdict_for("one-shipped-live")
        assert verdict.status == "PARTIAL"
        assert verdict.status != "CONFIRMED"


# ── RuleReasoner.decompose: explicit FILE-EXISTS (D1) ──────────────────────

class TestRuleReasonerDecomposeFileExists:
    def test_file_exists_explicit_alone(self):
        """FILE EXISTS: <path> by itself still produces exactly one fs anchor."""
        claim = Claim("f1", "pipeline", "agent", "FILE EXISTS: AGENTS.md")
        anchors = RuleReasoner().decompose(claim)
        fs = [a for a in anchors if a.kind == "fs"]
        assert len(fs) == 1
        assert fs[0].anchor_id == "fs-exists-AGENTS.md"
        assert fs[0].spec == {"op": "file_exists", "path": "AGENTS.md"}

    def test_file_exists_and_git_commit_both_anchors(self):
        """LOAD-BEARING: a combined turn must keep the fs anchor, not lose it
        to the git anchor. Fails before the explicit _FILE_EXISTS_RE fix."""
        sha = _head_sha()
        claim = Claim(
            "f2", "pipeline", "agent",
            f"FILE EXISTS: AGENTS.md and GIT COMMIT EXISTS: {sha}",
        )
        anchors = RuleReasoner().decompose(claim)
        kinds = sorted(a.kind for a in anchors)
        assert kinds == ["fs", "git"], f"got anchor kinds {kinds}"
        by_id = {a.anchor_id: a for a in anchors}
        assert by_id[f"fs-exists-AGENTS.md"].spec == {
            "op": "file_exists", "path": "AGENTS.md",
        }
        assert by_id[f"git-commit-exists-{sha}"].spec == {
            "op": "commit_exists", "sha": sha,
        }

    def test_two_explicit_file_paths_two_anchors(self):
        """Two distinct FILE EXISTS lines each get their own fs anchor."""
        claim = Claim(
            "f3", "pipeline", "agent",
            "FILE EXISTS: AGENTS.md\nFILE EXISTS: pyproject.toml",
        )
        anchors = RuleReasoner().decompose(claim)
        fs = [a for a in anchors if a.kind == "fs"]
        assert len(fs) == 2
        assert {a.spec["path"] for a in fs} == {"AGENTS.md", "pyproject.toml"}

    def test_same_explicit_path_twice_one_anchor(self):
        """The same path claimed twice is de-duplicated to one fs anchor."""
        claim = Claim(
            "f4", "pipeline", "agent",
            "FILE EXISTS: AGENTS.md\nFILE EXISTS: AGENTS.md",
        )
        anchors = RuleReasoner().decompose(claim)
        fs = [a for a in anchors if a.kind == "fs"]
        assert len(fs) == 1

    def test_bare_filename_fallback_still_works(self):
        """A bare filename in prose with no other anchor still gets an fs anchor
        from the old fallback scan."""
        claim = Claim("f5", "pipeline", "agent", "AGENTS.md is on disk")
        anchors = RuleReasoner().decompose(claim)
        fs = [a for a in anchors if a.kind == "fs"]
        assert len(fs) == 1
        assert fs[0].anchor_id == "fs-exists-AGENTS.md"

    def test_bare_filename_with_git_stays_gated(self):
        """The fallback is still gated: a bare filename in prose plus a git
        claim does not emit an fs anchor."""
        claim = Claim(
            "f6", "pipeline", "agent",
            "AGENTS.md is on disk and GIT BRANCH EXISTS: main",
        )
        anchors = RuleReasoner().decompose(claim)
        kinds = sorted(a.kind for a in anchors)
        assert kinds == ["git"]
        assert not any(a.kind == "fs" for a in anchors)
