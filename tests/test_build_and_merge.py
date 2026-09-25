"""Unit tests for `nucleus build --merge` (build_and_merge shim).

Mirrors the test patterns from ``test_cli_build.py``: mocks the vendor +
plan-review + verification seams for System A (ZERO live vendor calls), and
mocks the git/gh/authorize seams for the commit → push → PR → gate handoff
(NO real git/GitHub mutations). Uses ``tmp_path`` + ``monkeypatch.chdir`` for
cwd isolation, matching sibling test idioms.

Coverage required by the task spec:
  (1) verdict-FAIL → refuses before touching git/GitHub (no branch, no
      commit, no push, no PR, no authorize call).
  (2) verdict-PASS → proceeds to commit + push + PR (mocked git/gh), then
      hands the PR number to merge_gate_authorize.
  (3) STEROID 1: plan context is threaded into the downstream call — assert
      the actual content reaches ``NUCLEUS_BUILD_PLAN_CONTEXT``.
  (4) STEROID 2: verify receipt is threaded into the downstream call —
      assert the actual content reaches
      ``NUCLEUS_BUILD_VERIFY_RECEIPT_PATH`` and contains the verify details.
"""

import importlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# build_and_merge and build_runner are re-imported fresh in the fixture below
# because test_merge_gate.py's collection-time import of merge_gate.py evicts
# all mcp_server_nucleus.* from sys.modules, which would leave these
# module-level imports holding stale references that patch() can't reach.


# ── Isolation ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_brain(tmp_path, monkeypatch):
    """Pin brain resolution to tmp_path, shrink poll budgets, and re-resolve
    module references so patch() targets the same module the shim uses.

    test_merge_gate.py's collection-time import of scripts/merge_gate.py
    evicts all mcp_server_nucleus.* from sys.modules. A module-level import
    here would hold a stale reference after that eviction. We re-import
    fresh (importlib.import_module returns the current sys.modules entry,
    or re-imports if evicted) and update the test module's globals so all
    test functions see the fresh references. No eviction is performed —
    other test files are unaffected."""
    g = globals()
    g["build_and_merge"] = importlib.import_module(
        "mcp_server_nucleus.runtime.build_and_merge")
    g["build_runner"] = importlib.import_module(
        "mcp_server_nucleus.runtime.build_runner")

    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    # The pipeline no longer ships a default repo — it used to default to an
    # org whose repos 404, so it only failed after doing all the work. Tests
    # now state the target explicitly, like a real caller must.
    monkeypatch.setenv("NUCLEUS_BUILD_REPO", "testorg/testrepo")
    monkeypatch.setattr(build_runner, "_PLAN_POLL_TIMEOUT_S", 3)
    monkeypatch.setattr(build_runner, "_PLAN_POLL_INTERVAL_S", 0.05)
    # Auth/network preflight defaults to passing so existing pipeline tests
    # don't hit real gh/git network calls. We patch the two underlying probes
    # (not _auth_preflight itself) so direct tests of the orchestrator can
    # still override _check_gh_auth / _check_origin_reachable and exercise
    # the real _auth_preflight logic. The originals are saved as globals so
    # direct probe tests (test_check_gh_auth_*, test_check_origin_reachable_*)
    # can restore them and exercise the real subprocess.run path.
    g["_ORIG_CHECK_GH_AUTH"] = build_and_merge._check_gh_auth
    g["_ORIG_CHECK_ORIGIN_REACHABLE"] = build_and_merge._check_origin_reachable
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: True)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: True)
    # Clean up steroid env vars so they don't leak between tests.
    monkeypatch.delenv("NUCLEUS_BUILD_PLAN_CONTEXT", raising=False)
    monkeypatch.delenv("NUCLEUS_BUILD_VERIFY_RECEIPT_PATH", raising=False)


# ── Helpers (shared with test_cli_build.py idioms) ───────────────────────────

def _make_response(success: bool, data=None, error=None) -> str:
    return json.dumps({"success": success, "data": data, "error": error})


def _write_state(tmp_path: Path, plan_id: str, status: str,
                 final_plan_path: str = None) -> None:
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    state = {"status": status}
    if final_plan_path is not None:
        state["final_plan_path"] = final_plan_path
    (plans_dir / "state.json").write_text(json.dumps(state))


def _write_plan(tmp_path: Path, plan_id: str, tasks: list) -> Path:
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    fp = plans_dir / "final_plan.md"
    lines = ["# Plan\n"]
    for n, desc in tasks:
        lines.append(f"- [ ] Task {n}: {desc}")
    fp.write_text("\n".join(lines) + "\n")
    return fp


def _ok_dispatch(status="ok", produced_output=True):
    return {"status": status, "produced_output": produced_output,
            "vendor": "devin", "rc": 0}


def _patch_system_a_passing(plan_id, fp):
    """Return a context-manager stack that patches System A's stages to all
    pass. Used as a base for verdict-PASS tests."""
    from contextlib import ExitStack
    stack = ExitStack()
    stack.enter_context(patch(
        "mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
        side_effect=lambda params, make_response: _make_response(True, {"plan_id": plan_id})))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
        return_value=True))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
        return_value=True))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
        return_value=_ok_dispatch()))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.build_runner._git_head",
        return_value="abc123def456abc123def456abc123def456abc12"))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
        return_value=["src/foo.py"]))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.execution_verifier._tier1_syntax_check",
        return_value=[{"passed": True}]))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.execution_verifier._tier2_import_check",
        return_value=[{"passed": True}]))
    stack.enter_context(patch(
        "mcp_server_nucleus.runtime.execution_verifier._tier3_test_execution",
        return_value=[{"passed": True}]))
    return stack


# ── (1) verdict-FAIL refuses before touching git/GitHub ───────────────────────

def test_verdict_fail_refuses_before_git(tmp_path, monkeypatch, capsys):
    """Verdict FAIL (tier-0 empty changed_files) → shim returns rc=1 and
    NEVER calls git/gh/authorize. No branch, no commit, no push, no PR."""
    monkeypatch.chdir(tmp_path)
    plan_id = "fail-refuse"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    git_calls = []
    gh_calls = []
    auth_calls = []

    def fake_branch(name):
        git_calls.append(("checkout", name))
        return True

    def fake_commit(files, msg):
        git_calls.append(("commit", files, msg))
        return True

    def fake_push(branch):
        git_calls.append(("push", branch))
        return True

    def fake_pr(branch, title, body, base):
        gh_calls.append(("pr", branch, title, body, base))
        return 42

    def fake_auth(pr, repo, vendor, dry):
        auth_calls.append(("auth", pr, repo, vendor, dry))
        return 0

    # System A: tier-0 FAIL (empty changed_files → verdict FAIL).
    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=lambda p, mr: _make_response(True, {"plan_id": plan_id})), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value=_ok_dispatch()), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123def456abc123def456abc123def456abc12"), \
         patch("mcp_server_nucleus.runtime.execution_verifier._get_changed_files",
               return_value=[]), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               side_effect=fake_branch), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               side_effect=fake_commit), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               side_effect=fake_push), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               side_effect=fake_pr), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=fake_auth):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 1
    assert git_calls == [], f"git was touched on verdict FAIL: {git_calls}"
    assert gh_calls == [], f"gh was touched on verdict FAIL: {gh_calls}"
    assert auth_calls == [], f"authorize was called on verdict FAIL: {auth_calls}"


def test_verdict_fail_task_failure_refuses_before_git(tmp_path, monkeypatch):
    """Verdict FAIL (task dispatch fail-stop) → shim returns rc=1 and never
    touches git. Distinct from tier-0 fail: here EXECUTE aborts before
    VERIFY even runs."""
    monkeypatch.chdir(tmp_path)
    plan_id = "fail-task"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    git_calls = []

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=lambda p, mr: _make_response(True, {"plan_id": plan_id})), \
         patch("mcp_server_nucleus.runtime.build_runner.is_multi_vendor_available",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.cross_vendor_enabled",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_runner.dispatch_and_capture",
               return_value={"status": "error", "produced_output": False}), \
         patch("mcp_server_nucleus.runtime.build_runner._git_head",
               return_value="abc123def456abc123def456abc123def456abc12"), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               side_effect=lambda n: git_calls.append(n) or True):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 1
    assert git_calls == [], f"git was touched on task fail-stop: {git_calls}"


# ── (2) verdict-PASS proceeds to commit + push + PR + authorize ──────────────

def test_verdict_pass_proceeds_to_commit_push_pr_authorize(tmp_path, monkeypatch):
    """Verdict PASS → shim creates branch, commits changed files, pushes,
    opens PR, and hands PR number to authorize. All seams mocked."""
    monkeypatch.chdir(tmp_path)
    plan_id = "pass-proceed"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    branch_calls = []
    commit_calls = []
    push_calls = []
    pr_calls = []
    auth_calls = []

    def fake_branch(name):
        branch_calls.append(name)
        return True

    def fake_commit(files, msg):
        commit_calls.append((sorted(files), msg))
        return True

    def fake_push(branch):
        push_calls.append(branch)
        return True

    def fake_pr(branch, title, body, base):
        pr_calls.append((branch, title, body, base))
        return 42

    def fake_auth(pr, repo, vendor, dry):
        auth_calls.append((pr, repo, vendor, dry))
        return 0

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               side_effect=fake_branch), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               side_effect=fake_commit), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               side_effect=fake_push), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               side_effect=fake_pr), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=fake_auth):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 0
    # Branch created
    assert len(branch_calls) == 1
    assert branch_calls[0].startswith("build-merge/")
    # Changed files committed (from verify_details.changed_files)
    assert len(commit_calls) == 1
    assert commit_calls[0][0] == ["src/foo.py"]
    # Branch pushed
    assert push_calls == [branch_calls[0]]
    # PR opened with the branch as head, base=main
    assert len(pr_calls) == 1
    assert pr_calls[0][0] == branch_calls[0]
    assert pr_calls[0][3] == "main"
    # Authorize called with the PR number from fake_pr
    assert auth_calls == [(42, "testorg/testrepo", "devin", False)]


def test_verdict_pass_authorize_failure_propagates(tmp_path, monkeypatch):
    """Verdict PASS but authorize returns non-zero → shim returns that code.
    PR is still opened (we can't un-open it), but the gate refused."""
    monkeypatch.chdir(tmp_path)
    plan_id = "pass-auth-fail"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=99), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               return_value=1):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 1


def test_verdict_pass_pr_creation_failure_returns_1(tmp_path, monkeypatch):
    """Verdict PASS but gh pr create fails (returns None) → shim returns 1,
    authorize is never called."""
    monkeypatch.chdir(tmp_path)
    plan_id = "pass-pr-fail"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    auth_called = []

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=None), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=lambda *a: auth_called.append(a) or 0):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 1
    assert auth_called == []


# ── (3) STEROID 1: plan context threaded into downstream call ────────────────

def test_plan_context_threaded_into_env(tmp_path, monkeypatch):
    """STEROID 1: the plan context (task prompt + execution mode + approved
    plan text) is set as NUCLEUS_BUILD_PLAN_CONTEXT before the authorize
    call. Assert the actual content reaches the env var."""
    monkeypatch.chdir(tmp_path)
    plan_id = "steroid1"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    captured_env = {}

    def fake_auth(pr, repo, vendor, dry):
        # Snapshot the env vars at the moment authorize would run.
        captured_env["NUCLEUS_BUILD_PLAN_CONTEXT"] = os.environ.get(
            "NUCLEUS_BUILD_PLAN_CONTEXT", "")
        captured_env["NUCLEUS_BUILD_VERIFY_RECEIPT_PATH"] = os.environ.get(
            "NUCLEUS_BUILD_VERIFY_RECEIPT_PATH", "")
        return 0

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=fake_auth):
        rc = build_and_merge.run_build_and_merge_pipeline("build the foo feature")

    assert rc == 0
    plan_ctx = captured_env["NUCLEUS_BUILD_PLAN_CONTEXT"]
    # Task prompt is in the context
    assert "build the foo feature" in plan_ctx
    # Execution mode is in the context
    assert "dual-vendor" in plan_ctx
    # The approved plan text is in the context
    assert "Task 1: do thing" in plan_ctx
    assert "APPROVED PLAN:" in plan_ctx


def test_plan_context_contains_plan_file_content(tmp_path, monkeypatch):
    """STEROID 1 (deeper): the plan context includes the actual content of
    the approved plan file, not just a path reference."""
    monkeypatch.chdir(tmp_path)
    plan_id = "steroid1-deep"
    # Write a plan with distinctive content we can assert on.
    plans_dir = tmp_path / ".brain" / "plans" / plan_id
    plans_dir.mkdir(parents=True, exist_ok=True)
    fp = plans_dir / "final_plan.md"
    fp.write_text("# Plan\n\n- [ ] Task 1: implement DISTINCTIVE_MARKER_XYZ\n")
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    captured = {}

    def fake_auth(pr, repo, vendor, dry):
        captured["plan_context"] = os.environ.get("NUCLEUS_BUILD_PLAN_CONTEXT", "")
        return 0

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=fake_auth):
        build_and_merge.run_build_and_merge_pipeline("build")

    assert "DISTINCTIVE_MARKER_XYZ" in captured["plan_context"]


# ── (4) STEROID 2: verify receipt threaded into downstream call ──────────────

def test_verify_receipt_threaded_into_env(tmp_path, monkeypatch):
    """STEROID 2: the verify receipt (System A's in-process verification
    outcome) is written to a file and its path set as
    NUCLEUS_BUILD_VERIFY_RECEIPT_PATH. Assert the file exists, is valid
    JSON, and contains the verify details (tier statuses, changed files)."""
    monkeypatch.chdir(tmp_path)
    plan_id = "steroid2"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    captured = {}

    def fake_auth(pr, repo, vendor, dry):
        captured["receipt_path"] = os.environ.get(
            "NUCLEUS_BUILD_VERIFY_RECEIPT_PATH", "")
        return 0

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=fake_auth):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 0
    receipt_path = captured["receipt_path"]
    assert receipt_path, "NUCLEUS_BUILD_VERIFY_RECEIPT_PATH was not set"
    assert os.path.isfile(receipt_path), f"receipt file missing at {receipt_path}"

    receipt = json.loads(Path(receipt_path).read_text())
    # Source tag
    assert receipt["source"] == "nucleus_build_verify_stage"
    # Task prompt threaded through
    assert receipt["task_prompt"] == "build foo"
    # Execution mode
    assert receipt["execution_mode"] == "dual-vendor"
    # Changed files from verify_details
    assert receipt["changed_files"] == ["src/foo.py"]
    # Summary status (all tiers pass → PASSED)
    assert receipt["summary_status"] == "PASSED"
    assert receipt["passed_count"] == 3
    assert receipt["failed_count"] == 0
    # Tier statuses present
    assert receipt["tier1"]["status"] == "PASSED"
    assert receipt["tier2"]["status"] == "PASSED"
    assert receipt["tier3"]["status"] == "PASSED"


def test_verify_receipt_reflects_insufficient_run(tmp_path, monkeypatch):
    """STEROID 2 (insufficient case): when verification is INSUFFICIENT
    (all tiers skipped), the receipt records that — but the verdict is
    still a FAIL (rc=1) so the shim refuses before git. This test confirms
    the receipt builder captures INSUFFICIENT correctly when driven
    directly."""
    # Drive _build_verify_receipt directly with an INSUFFICIENT details dict.
    details = {
        "summary_status": "INSUFFICIENT",
        "passed_count": 0,
        "failed_count": 0,
        "skipped_count": 3,
        "changed_files": ["README.md"],
        "tier0": {"status": "PASSED", "files_count": 1},
        "tier1": {"status": "SKIPPED", "signals": []},
        "tier2": {"status": "SKIPPED", "signals": []},
        "tier3": {"status": "SKIPPED", "signals": []},
    }
    receipt_json = build_and_merge._build_verify_receipt(
        "task", details, "dual-vendor",
    )
    receipt = json.loads(receipt_json)
    assert receipt["summary_status"] == "INSUFFICIENT"
    assert receipt["passed_count"] == 0
    assert receipt["skipped_count"] == 3
    assert receipt["tier1"]["status"] == "SKIPPED"


# ── Env var cleanup after authorize ──────────────────────────────────────────

def test_steroid_env_vars_cleaned_up_after_authorize(tmp_path, monkeypatch):
    """After the authorize call returns, the steroid env vars are popped so
    they don't leak into subsequent calls in the same process."""
    monkeypatch.chdir(tmp_path)
    plan_id = "env-cleanup"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               return_value=0):
        build_and_merge.run_build_and_merge_pipeline("build foo")

    assert "NUCLEUS_BUILD_PLAN_CONTEXT" not in os.environ
    assert "NUCLEUS_BUILD_VERIFY_RECEIPT_PATH" not in os.environ


# ── Empty task prompt ────────────────────────────────────────────────────────

def test_empty_task_prompt_returns_2(tmp_path, monkeypatch):
    """Empty task prompt → exit code 2 (arg-validation), before any stage runs."""
    monkeypatch.chdir(tmp_path)
    rc = build_and_merge.run_build_and_merge_pipeline("")
    assert rc == 2

    rc = build_and_merge.run_build_and_merge_pipeline("   ")
    assert rc == 2


# ── --repo / cwd mismatch warning (fw-1785863543) ───────────────────────────
# --repo only ever targeted the merge gate's PR/merge step, never the build
# phase's working directory — `nucleus build --merge --repo other/repo "..."`
# silently built against the cwd's actual repo. Fixed with a loud warning
# (not a refusal, to avoid breaking legitimate same-repo usage) the moment
# the mismatch is knowable.

def test_repo_mismatch_warns_before_stages_run(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_and_merge, "_cwd_origin_repo", lambda: "owner/actual-repo")
    with patch("mcp_server_nucleus.runtime.build_runner._run_plan_stage",
               return_value=(False, "no vendor configured", None, None)):
        rc = build_and_merge.run_build_and_merge_pipeline(
            "do a thing", repo="owner/other-repo",
        )
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "owner/other-repo" in captured.err
    assert "owner/actual-repo" in captured.err
    assert rc == 1  # PLAN stage still fails for unrelated (no-vendor) reasons


def test_repo_match_no_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_and_merge, "_cwd_origin_repo", lambda: "owner/repo")
    with patch("mcp_server_nucleus.runtime.build_runner._run_plan_stage",
               return_value=(False, "no vendor configured", None, None)):
        build_and_merge.run_build_and_merge_pipeline("do a thing", repo="owner/repo")
    captured = capsys.readouterr()
    assert "--repo=" not in captured.err


def test_repo_mismatch_no_warning_when_cwd_repo_unknown(tmp_path, monkeypatch, capsys):
    """Not a git repo / no origin remote → _cwd_origin_repo() is None → no
    warning (nothing to compare against, must not false-positive)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_and_merge, "_cwd_origin_repo", lambda: None)
    with patch("mcp_server_nucleus.runtime.build_runner._run_plan_stage",
               return_value=(False, "no vendor configured", None, None)):
        build_and_merge.run_build_and_merge_pipeline("do a thing", repo="owner/other-repo")
    captured = capsys.readouterr()
    assert "--repo=" not in captured.err


def test_preflight_blocks_before_repo_mismatch_warning_is_redundant(
    tmp_path, monkeypatch, capsys,
):
    """When both a --repo/cwd mismatch AND an auth failure exist, the
    repo-mismatch WARNING still prints (it fires first, before the auth
    preflight) AND the preflight blocks (rc == 2). Both texts must appear
    in stderr — proving the warning is not swallowed by the early return
    and the preflight is not skipped past the warning."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_and_merge, "_cwd_origin_repo", lambda: "owner/actual-repo")
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: False)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: False)
    rc = build_and_merge.run_build_and_merge_pipeline(
        "do a thing", repo="owner/other-repo",
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "WARNING" in captured.err
    assert "owner/other-repo" in captured.err
    assert "owner/actual-repo" in captured.err
    assert "preflight failed" in captured.err


def test_cwd_origin_repo_parses_ssh_and_https(tmp_path, monkeypatch):
    import subprocess as sp

    def fake_run(cmd, **kwargs):
        assert cmd[:3] == ["git", "remote", "get-url"]
        return type("R", (), {
            "returncode": 0,
            "stdout": "git@github.com:owner/name.git\n",
        })()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._cwd_origin_repo() == "owner/name"

    def fake_run_https(cmd, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": "https://github.com/owner/name\n",
        })()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run_https)
    assert build_and_merge._cwd_origin_repo() == "owner/name"


def test_cwd_origin_repo_none_on_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        return type("R", (), {"returncode": 1, "stdout": ""})()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._cwd_origin_repo() is None


# ── _check_gh_auth probe (never raises; 4 exit paths) ────────────────────────

def test_check_gh_auth_true_on_exit_0(monkeypatch):
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", _ORIG_CHECK_GH_AUTH)

    def fake_run(cmd, **kwargs):
        assert cmd == ["gh", "auth", "status"]
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_gh_auth() is True


def test_check_gh_auth_false_on_nonzero(monkeypatch):
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", _ORIG_CHECK_GH_AUTH)

    def fake_run(cmd, **kwargs):
        return type("R", (), {"returncode": 1})()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_gh_auth() is False


def test_check_gh_auth_false_on_timeout(monkeypatch):
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", _ORIG_CHECK_GH_AUTH)
    import subprocess as sp

    def fake_run(cmd, **kwargs):
        raise sp.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_gh_auth() is False


def test_check_gh_auth_false_on_oserror(monkeypatch):
    """FileNotFoundError = gh CLI not installed → False, never raises."""
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", _ORIG_CHECK_GH_AUTH)

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("gh not installed")

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_gh_auth() is False


# ── _check_origin_reachable probe (never raises; 4 exit paths) ───────────────

def test_check_origin_reachable_true_on_exit_0(monkeypatch):
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable",
                        _ORIG_CHECK_ORIGIN_REACHABLE)

    def fake_run(cmd, **kwargs):
        assert cmd == ["git", "ls-remote", "--heads", "origin"]
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_origin_reachable() is True


def test_check_origin_reachable_false_on_nonzero(monkeypatch):
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable",
                        _ORIG_CHECK_ORIGIN_REACHABLE)

    def fake_run(cmd, **kwargs):
        return type("R", (), {"returncode": 1})()

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_origin_reachable() is False


def test_check_origin_reachable_false_on_timeout(monkeypatch):
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable",
                        _ORIG_CHECK_ORIGIN_REACHABLE)
    import subprocess as sp

    def fake_run(cmd, **kwargs):
        raise sp.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_origin_reachable() is False


def test_check_origin_reachable_false_on_oserror(monkeypatch):
    """FileNotFoundError = git not installed → False, never raises."""
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable",
                        _ORIG_CHECK_ORIGIN_REACHABLE)

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git not installed")

    monkeypatch.setattr(build_and_merge.subprocess, "run", fake_run)
    assert build_and_merge._check_origin_reachable() is False


# ── CLI handler dispatch ─────────────────────────────────────────────────────

def test_cli_build_merge_flag_dispatches_to_shim(monkeypatch):
    """`nucleus build --merge` → handle_build_command calls
    run_build_and_merge_pipeline, NOT run_build_pipeline."""
    from mcp_server_nucleus import cli as cli_mod

    class FakeArgs:
        task = "do the thing"
        merge = True
        repo = "testorg/testrepo"
        review_vendor = "devin"
        base_branch = "main"
        dry_run = False

    called = {"shim": False, "plain": False}

    def fake_shim(task_prompt, *, repo, review_vendor, base_branch, dry_run):
        called["shim"] = True
        assert task_prompt == "do the thing"
        return 0

    def fake_plain(task_prompt):
        called["plain"] = True
        return 0

    with patch("mcp_server_nucleus.runtime.build_and_merge.run_build_and_merge_pipeline",
               side_effect=fake_shim), \
         patch("mcp_server_nucleus.runtime.build_runner.run_build_pipeline",
               side_effect=fake_plain):
        rc = cli_mod.handle_build_command(FakeArgs())

    assert rc == 0
    assert called["shim"] is True
    assert called["plain"] is False


def test_cli_build_without_merge_dispatches_to_plain(monkeypatch):
    """`nucleus build` (no --merge) → handle_build_command calls
    run_build_pipeline (existing behavior unchanged)."""
    from mcp_server_nucleus import cli as cli_mod

    class FakeArgs:
        task = "do the thing"
        merge = False
        repo = "testorg/testrepo"
        review_vendor = "devin"
        base_branch = "main"
        dry_run = False

    called = {"shim": False, "plain": False}

    def fake_shim(*a, **kw):
        called["shim"] = True
        return 0

    def fake_plain(task_prompt):
        called["plain"] = True
        assert task_prompt == "do the thing"
        return 0

    with patch("mcp_server_nucleus.runtime.build_and_merge.run_build_and_merge_pipeline",
               side_effect=fake_shim), \
         patch("mcp_server_nucleus.runtime.build_runner.run_build_pipeline",
               side_effect=fake_plain):
        rc = cli_mod.handle_build_command(FakeArgs())

    assert rc == 0
    assert called["plain"] is True
    assert called["shim"] is False


# ── PR number parsing from gh output ─────────────────────────────────────────

def test_create_pr_parses_pr_number_from_url():
    """_create_pr extracts the PR number from gh's stdout URL."""
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        class R:
            stdout = "https://github.com/owner/repo/pull/123\n"
            stderr = ""
        return R()

    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               side_effect=fake_run):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")

    assert pr == 123
    assert "gh" in captured["cmd"]


def test_create_pr_returns_none_on_unparseable_output():
    """_create_pr returns None when gh output has no /pull/N pattern."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {"stdout": "some weird output", "stderr": ""})()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr is None


def test_create_pr_parses_url_with_path_suffix():
    """gh may append /files, /commits, /diffs to the URL — regex must still
    extract the PR number (re.search, not re.match)."""
    for suffix in ["/files", "/commits", "/diffs", "/files/abc123"]:
        with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
                   return_value=type("R", (), {
                       "stdout": f"https://github.com/owner/repo/pull/55{suffix}\n",
                       "stderr": "",
                   })()):
            pr = build_and_merge._create_pr("branch", "title", "body", "main")
        assert pr == 55, f"failed for suffix={suffix}: got {pr}"


def test_create_pr_parses_url_with_query_string():
    """URL with query params like ?diff=unified — regex extracts PR number."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {
                   "stdout": "https://github.com/owner/repo/pull/77?diff=unified&w=1\n",
                   "stderr": "",
               })()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr == 77


def test_create_pr_parses_github_enterprise_url():
    """GitHub Enterprise uses a custom domain — regex must not hardcode
    github.com."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {
                   "stdout": "https://github.example.com/owner/repo/pull/99\n",
                   "stderr": "",
               })()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr == 99


def test_create_pr_parses_url_with_leading_text():
    """gh --verbose or future versions may print text before the URL.
    re.search finds the URL anywhere in stdout."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {
                   "stdout": "Creating pull request for feat into main in owner/repo\n"
                             "https://github.com/owner/repo/pull/42\n",
                   "stderr": "",
               })()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr == 42


def test_create_pr_parses_crlf_line_endings():
    """Windows gh may output CRLF — .strip() handles it."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {
                   "stdout": "https://github.com/owner/repo/pull/200\r\n",
                   "stderr": "",
               })()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr == 200


def test_create_pr_parses_large_pr_number():
    """Large PR numbers (8+ digits) — Python int has no overflow."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {
                   "stdout": "https://github.com/owner/repo/pull/999999999\n",
                   "stderr": "",
               })()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr == 999999999


def test_create_pr_returns_none_on_called_process_error():
    """gh exits non-zero (e.g. GraphQL error, auth failure) →
    CalledProcessError caught → returns None."""
    import subprocess as sp
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               side_effect=sp.CalledProcessError(1, "gh", stderr="GraphQL error")):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr is None


def test_create_pr_returns_none_on_empty_stdout():
    """gh succeeds (exit 0) but stdout is empty — returns None, not a crash."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               return_value=type("R", (), {"stdout": "", "stderr": ""})()):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr is None


def test_create_pr_handles_file_not_found_error():
    """gh binary not installed → FileNotFoundError (subclass of OSError).
    The shim should return None gracefully, NOT crash with an unhandled
    exception. The except clause catches (CalledProcessError, OSError)."""
    with patch("mcp_server_nucleus.runtime.build_and_merge.subprocess.run",
               side_effect=FileNotFoundError("[Errno 2] No such file or directory: 'gh'")):
        pr = build_and_merge._create_pr("branch", "title", "body", "main")
    assert pr is None


# ── _auth_preflight orchestration helper ─────────────────────────────────────

def test_auth_preflight_both_pass_returns_true(monkeypatch):
    """Both probes pass → _auth_preflight returns True, prints nothing."""
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: True)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: True)
    assert build_and_merge._auth_preflight() is True


def test_auth_preflight_both_pass_prints_nothing(monkeypatch, capsys):
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: True)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: True)
    build_and_merge._auth_preflight()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_auth_preflight_gh_auth_fail_returns_false(monkeypatch, capsys):
    """gh auth fails → returns False, prints remediation to stderr."""
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: False)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: True)
    assert build_and_merge._auth_preflight() is False
    captured = capsys.readouterr()
    assert "gh auth login" in captured.err


def test_auth_preflight_origin_fail_returns_false(monkeypatch, capsys):
    """origin unreachable → returns False, prints remediation to stderr."""
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: True)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: False)
    assert build_and_merge._auth_preflight() is False
    captured = capsys.readouterr()
    assert "git remote" in captured.err


def test_auth_preflight_both_fail_prints_both_remediations(monkeypatch, capsys):
    """Both probes fail → returns False, prints BOTH remediation commands
    (not just the first failure)."""
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: False)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: False)
    assert build_and_merge._auth_preflight() is False
    captured = capsys.readouterr()
    assert "gh auth login" in captured.err
    assert "git remote" in captured.err


# ── preflight integration into run_build_and_merge_pipeline ──────────────────

def test_preflight_fail_aborts_before_stages_returns_2(tmp_path, monkeypatch):
    """_auth_preflight returns False (non-dry-run) → shim returns 2 and
    never reaches System A stages (no plan_review_loop call)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_and_merge, "_auth_preflight", lambda: False)

    plan_called = {"count": 0}

    def fake_plan(*a, **kw):
        plan_called["count"] += 1
        return _make_response(True, {"plan_id": "should-not-run"})

    with patch("mcp_server_nucleus.tools.plan_review_loop.execute_plan_review_loop",
               side_effect=fake_plan):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 2
    assert plan_called["count"] == 0, "PLAN stage ran despite preflight failure"


def test_preflight_blocks_with_nonzero_rc_when_gh_auth_fails(
        tmp_path, monkeypatch, capsys):
    """gh auth fails (origin reachable) → real _auth_preflight returns False,
    shim returns rc == 2, and System A stages are NEVER invoked.

    Patches the two underlying probes (not _auth_preflight itself) so the
    real orchestrator logic runs end-to-end, and patches _run_plan_stage
    with a sentinel that hard-fails the test if any System A stage is
    reached. Asserts the gh-auth remediation message lands in stderr."""
    monkeypatch.chdir(tmp_path)
    # Underlying probes: gh auth fails, origin reachable. The autouse
    # fixture already sets both to True; override gh auth to False here so
    # the real _auth_preflight logic exercises the failure path.
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: False)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: True)

    def _stage_must_not_run(*a, **kw):
        pytest.fail(
            "_run_plan_stage (System A) was invoked despite preflight "
            "blocking on gh-auth failure")

    # _run_plan_stage is imported lazily inside run_build_and_merge_pipeline
    # via `from .build_runner import _run_plan_stage`, so patch it at the
    # source module — the from-import binds to the patched attribute at
    # call time, and preflight aborts before the import line is reached
    # anyway. Belt-and-suspenders: patch all three System A stage entry
    # points so a future refactor that reorders the import cannot silently
    # bypass the gate.
    with patch.object(build_runner, "_run_plan_stage",
                      side_effect=_stage_must_not_run), \
         patch.object(build_runner, "_run_execute_stage",
                      side_effect=_stage_must_not_run), \
         patch.object(build_runner, "_run_verify_stage",
                      side_effect=_stage_must_not_run):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 2
    captured = capsys.readouterr()
    assert "gh auth login" in captured.err, (
        "expected gh-auth remediation message in stderr; got: "
        f"{captured.err!r}")


def test_preflight_blocks_when_origin_unreachable(
        tmp_path, monkeypatch, capsys):
    """origin unreachable (gh auth ok) → real _auth_preflight returns False,
    shim returns rc == 2, and System A stages are NEVER invoked.

    Patches the two underlying probes (not _auth_preflight itself) so the
    real orchestrator logic runs end-to-end, and patches the System A stage
    entry points with a sentinel that hard-fails the test if any stage is
    reached. Asserts the origin-unreachable remediation message lands in
    stderr."""
    monkeypatch.chdir(tmp_path)
    # Underlying probes: gh auth ok, origin unreachable. The autouse
    # fixture already sets both to True; override origin to False here so
    # the real _auth_preflight logic exercises the failure path.
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: True)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: False)

    def _stage_must_not_run(*a, **kw):
        pytest.fail(
            "a System A stage was invoked despite preflight "
            "blocking on origin-unreachable failure")

    # Belt-and-suspenders: patch all three System A stage entry points so a
    # future refactor that reorders the lazy import cannot silently bypass
    # the gate. Preflight aborts before the import line is reached anyway.
    with patch.object(build_runner, "_run_plan_stage",
                      side_effect=_stage_must_not_run), \
         patch.object(build_runner, "_run_execute_stage",
                      side_effect=_stage_must_not_run), \
         patch.object(build_runner, "_run_verify_stage",
                      side_effect=_stage_must_not_run):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 2
    captured = capsys.readouterr()
    assert "git remote" in captured.err, (
        "expected origin-unreachable remediation message in stderr; got: "
        f"{captured.err!r}")


def test_preflight_pass_proceeds_to_stages(tmp_path, monkeypatch):
    """_auth_preflight returns True (non-dry-run) → shim proceeds normally
    into System A stages. Uses the passing-PASS fixture path."""
    monkeypatch.chdir(tmp_path)
    plan_id = "preflight-pass"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))
    # _auth_preflight already defaults to True via the autouse fixture;
    # make it explicit for clarity.
    monkeypatch.setattr(build_and_merge, "_auth_preflight", lambda: True)

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               return_value=0):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 0


def test_preflight_passing_does_not_change_behavior(tmp_path, monkeypatch):
    """A passing preflight is a no-op on existing verdict-PASS behavior.

    Patches both underlying probes → True (leaving the real
    _auth_preflight orchestrator in place so its logic runs end-to-end),
    then runs a full verdict-PASS scenario via _patch_system_a_passing +
    mocked git/gh/authorize seams — same shape as
    test_verdict_pass_proceeds_to_commit_push_pr_authorize. Asserts rc == 0
    and the full commit/push/PR/authorize sequence fires exactly as before,
    confirming a passing preflight neither short-circuits nor alters the
    downstream handoff."""
    monkeypatch.chdir(tmp_path)
    plan_id = "preflight-pass-noop"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))
    # Explicitly patch both probes → True. The autouse fixture already
    # does this, but we re-assert here for clarity and so the test is
    # self-documenting about its preflight stance. The real
    # _auth_preflight orchestrator is left in place — its logic runs
    # end-to-end and must return True, letting control flow into System A.
    monkeypatch.setattr(build_and_merge, "_check_gh_auth", lambda: True)
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable", lambda: True)

    branch_calls = []
    commit_calls = []
    push_calls = []
    pr_calls = []
    auth_calls = []

    def fake_branch(name):
        branch_calls.append(name)
        return True

    def fake_commit(files, msg):
        commit_calls.append((sorted(files), msg))
        return True

    def fake_push(branch):
        push_calls.append(branch)
        return True

    def fake_pr(branch, title, body, base):
        pr_calls.append((branch, title, body, base))
        return 42

    def fake_auth(pr, repo, vendor, dry):
        auth_calls.append((pr, repo, vendor, dry))
        return 0

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               side_effect=fake_branch), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               side_effect=fake_commit), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               side_effect=fake_push), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               side_effect=fake_pr), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               side_effect=fake_auth):
        rc = build_and_merge.run_build_and_merge_pipeline("build foo")

    assert rc == 0
    # Branch created
    assert len(branch_calls) == 1
    assert branch_calls[0].startswith("build-merge/")
    # Changed files committed (from verify_details.changed_files)
    assert len(commit_calls) == 1
    assert commit_calls[0][0] == ["src/foo.py"]
    # Branch pushed
    assert push_calls == [branch_calls[0]]
    # PR opened with the branch as head, base=main
    assert len(pr_calls) == 1
    assert pr_calls[0][0] == branch_calls[0]
    assert pr_calls[0][3] == "main"
    # Authorize called with the PR number from fake_pr
    assert auth_calls == [(42, "testorg/testrepo", "devin", False)]


def test_preflight_skipped_in_dry_run(tmp_path, monkeypatch):
    """dry_run=True → _auth_preflight is NOT called at all, even though it
    would return False. Shim proceeds to stages (which fail naturally on
    the mocked plan path, but the point is preflight didn't gate)."""
    monkeypatch.chdir(tmp_path)
    plan_id = "dry-run-skip"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    preflight_called = {"count": 0}

    def fake_preflight():
        preflight_called["count"] += 1
        return False  # would abort if called

    monkeypatch.setattr(build_and_merge, "_auth_preflight", fake_preflight)

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               return_value=0):
        rc = build_and_merge.run_build_and_merge_pipeline(
            "build foo", dry_run=True)

    assert preflight_called["count"] == 0, \
        "_auth_preflight was called in dry-run mode"
    assert rc == 0


def test_preflight_skipped_under_dry_run(tmp_path, monkeypatch):
    """dry_run=True → the preflight is skipped ENTIRELY: neither underlying
    probe (_check_gh_auth, _check_origin_reachable) is ever called, even
    though the real _auth_preflight orchestrator is left in place.

    Stronger than test_preflight_skipped_in_dry_run (which patches
    _auth_preflight itself): here the real _auth_preflight is installed, so
    if the dry-run gate ever regressed and let control reach the preflight
    block, the sentinel probes would fire pytest.fail and the test would
    catch it. Confirms the pipeline proceeds through System A (via
    _patch_system_a_passing), reaches the --dry-run early-return, and
    returns rc == 0."""
    monkeypatch.chdir(tmp_path)
    plan_id = "dry-run-under"
    fp = _write_plan(tmp_path, plan_id, [(1, "do thing")])
    _write_state(tmp_path, plan_id, "APPROVED", final_plan_path=str(fp))

    def _probe_must_not_run(*a, **kw):
        pytest.fail(
            "a preflight probe was invoked despite --dry-run skipping the "
            "entire preflight block")

    # Patch the two underlying probes (NOT _auth_preflight) with sentinels
    # that hard-fail the test if called. The real _auth_preflight is left
    # in place — if the dry-run gate regresses, control reaches the
    # preflight block, _auth_preflight calls one of these probes, and the
    # test fails loudly.
    monkeypatch.setattr(build_and_merge, "_check_gh_auth",
                        lambda: _probe_must_not_run())
    monkeypatch.setattr(build_and_merge, "_check_origin_reachable",
                        lambda: _probe_must_not_run())

    with _patch_system_a_passing(plan_id, fp), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._commit_changed_files",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._push_branch",
               return_value=True), \
         patch("mcp_server_nucleus.runtime.build_and_merge._create_pr",
               return_value=42), \
         patch("mcp_server_nucleus.runtime.build_and_merge._run_authorize",
               return_value=0):
        rc = build_and_merge.run_build_and_merge_pipeline(
            "build foo", dry_run=True)

    assert rc == 0

