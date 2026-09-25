"""Tests for scripts/merge_gate_authorize.py — the keyed/trusted side of the
merge gate trust split.

Exercises the core refusal behaviors (missing env vars, fork PR, GROUND
failure, bad SHA) by monkeypatching external subprocess calls — same style
as test_merge_gate.py. Never touches real .brain files, GitHub, or the network.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
_spec = importlib.util.spec_from_file_location("merge_gate_authorize", _SCRIPTS_DIR / "merge_gate_authorize.py")
merge_gate_authorize = importlib.util.module_from_spec(_spec)
sys.modules["merge_gate_authorize"] = merge_gate_authorize
_spec.loader.exec_module(merge_gate_authorize)


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Set up the two required env vars + a real brain dir."""
    brain = tmp_path / "brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-signing-key")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    yield brain


# ── Env precondition tests ───────────────────────────────────────────────

class TestEnvPreconditions:
    def test_refuses_without_sign_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_WITNESS_SIGN_KEY", raising=False)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        assert merge_gate_authorize._check_sign_key("test") is None

    def test_refuses_without_brain_path(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-key")
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        assert merge_gate_authorize._check_brain_path("test") is None

    def test_refuses_if_brain_path_does_not_exist(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-key")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "nonexistent"))
        assert merge_gate_authorize._check_brain_path("test") is None

    def test_passes_with_both_env_vars(self, isolated_env):
        assert merge_gate_authorize._check_sign_key("test") == "test-signing-key"
        assert merge_gate_authorize._check_brain_path("test") == isolated_env


# ── Repo resolution tests ────────────────────────────────────────────────

class TestRepoResolution:
    def test_uses_explicit_repo(self, monkeypatch):
        monkeypatch.delenv("GH_REPO", raising=False)
        assert merge_gate_authorize._resolve_repo("test", "owner/repo") == "owner/repo"

    def test_refuses_when_no_repo_and_gh_fails(self, monkeypatch):
        monkeypatch.delenv("GH_REPO", raising=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="not in a repo"
            )
            assert merge_gate_authorize._resolve_repo("test", None) is None

    def test_resolves_from_gh_repo_view(self, monkeypatch):
        monkeypatch.delenv("GH_REPO", raising=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout="owner/resolved\n", stderr=""
            )
            assert merge_gate_authorize._resolve_repo("test", None) == "owner/resolved"


# ── PR validation tests (fork refusal, state check, SHA validation) ──────

class TestPRValidation:
    _VALID_SHA = "a" * 40

    def _make_pr_json(self, *, state="OPEN", head_owner="owner", sha=None):
        return json.dumps({
            "headRefOid": sha or self._VALID_SHA,
            "headRefName": "feature-branch",
            "baseRefName": "main",
            "headRepositoryOwner": {"login": head_owner},
            "state": state,
        })

    def test_refuses_non_open_pr(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=self._make_pr_json(state="CLOSED"), stderr=""
            )
            result = merge_gate_authorize._fetch_and_validate_pr(
                "test", "42", "owner/repo", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_refuses_fork_pr(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=self._make_pr_json(head_owner="fork-owner"), stderr=""
            )
            result = merge_gate_authorize._fetch_and_validate_pr(
                "test", "42", "owner/repo", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_accepts_same_owner_pr(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=self._make_pr_json(head_owner="owner"), stderr=""
            )
            result = merge_gate_authorize._fetch_and_validate_pr(
                "test", "42", "owner/repo", str(tmp_path), str(tmp_path)
            )
        assert result is not None
        assert result["head_sha"] == self._VALID_SHA

    def test_refuses_short_sha(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=self._make_pr_json(sha="abc123"), stderr=""
            )
            result = merge_gate_authorize._fetch_and_validate_pr(
                "test", "42", "owner/repo", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_refuses_malicious_sha(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=self._make_pr_json(sha="abc; rm -rf /"), stderr=""
            )
            result = merge_gate_authorize._fetch_and_validate_pr(
                "test", "42", "owner/repo", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_refuses_when_gh_pr_view_fails(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="PR not found"
            )
            result = merge_gate_authorize._fetch_and_validate_pr(
                "test", "999", "owner/repo", str(tmp_path), str(tmp_path)
            )
        assert result is None


# ── GROUND verify tests ──────────────────────────────────────────────────

class TestGroundVerify:
    def test_refuses_on_ground_failure(self, monkeypatch, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="GROUND failed: syntax error"
            )
            result = merge_gate_authorize._ground_verify(
                "test", brain, "main", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_refuses_when_no_receipt_in_brain(self, monkeypatch, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout='{"verified": true}', stderr=""
            )
            result = merge_gate_authorize._ground_verify(
                "test", brain, "main", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_reads_receipt_from_verification_log(self, monkeypatch, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        # Write a valid GROUND receipt to the verification log
        receipt = {"verified": True, "tiers_passed": [0, 1, 2], "tiers_failed": []}
        (brain / "verification_log.jsonl").write_text(json.dumps(receipt) + "\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout='{"verified": true}', stderr=""
            )
            result = merge_gate_authorize._ground_verify(
                "test", brain, "main", str(tmp_path), str(tmp_path)
            )
        assert result is not None
        # The receipt file should contain the last line of the log
        receipt_data = json.loads(Path(result).read_text().strip())
        assert receipt_data["verified"] is True


# ── Review dispatch + VERDICT parsing tests ──────────────────────────────

class TestReviewDispatch:
    def test_refuses_on_reject_verdict(self, monkeypatch, tmp_path):
        review_output = json.dumps({
            "result": "This change is bad.\n\nVERDICT: REJECT\n\nReasoning here."
        })
        with patch("subprocess.run") as mock_run:
            # First call: git diff (returns non-empty diff)
            # Second call: nucleus dispatch (returns review JSON)
            mock_run.side_effect = [
                subprocess.CompletedProcess([], 0, stdout="some diff content", stderr=""),
                subprocess.CompletedProcess([], 0, stdout=review_output, stderr=""),
            ]
            result = merge_gate_authorize._dispatch_review(
                "test", "devin", "main", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_refuses_on_ambiguous_verdict(self, monkeypatch, tmp_path):
        review_output = json.dumps({
            "result": "I'm not sure about this change.\n\nMaybe it's fine?"
        })
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess([], 0, stdout="some diff content", stderr=""),
                subprocess.CompletedProcess([], 0, stdout=review_output, stderr=""),
            ]
            result = merge_gate_authorize._dispatch_review(
                "test", "devin", "main", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_accepts_approve_verdict(self, monkeypatch, tmp_path):
        # The VERDICT line must be the first non-blank line (same as the
        # original bash script's normalization — it only checks lines[0]).
        review_output = json.dumps({
            "result": "VERDICT: APPROVE\n\nLooks good. Ship it."
        })
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess([], 0, stdout="some diff content", stderr=""),
                subprocess.CompletedProcess([], 0, stdout=review_output, stderr=""),
            ]
            result = merge_gate_authorize._dispatch_review(
                "test", "devin", "main", str(tmp_path), str(tmp_path)
            )
        assert result is not None
        assert "VERDICT: APPROVE" in Path(result).read_text()

    def test_accepts_markdown_bold_verdict(self, monkeypatch, tmp_path):
        """Real LLM replies routinely wrap verdict in markdown bold — must
        still parse correctly (same normalization as the original bash script)."""
        review_output = json.dumps({
            "result": "**VERDICT: APPROVE**\n\nLooks good."
        })
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess([], 0, stdout="some diff content", stderr=""),
                subprocess.CompletedProcess([], 0, stdout=review_output, stderr=""),
            ]
            result = merge_gate_authorize._dispatch_review(
                "test", "devin", "main", str(tmp_path), str(tmp_path)
            )
        assert result is not None

    def test_refuses_on_empty_diff(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            result = merge_gate_authorize._dispatch_review(
                "test", "devin", "main", str(tmp_path), str(tmp_path)
            )
        assert result is None

    def test_refuses_on_unparseable_dispatch_output(self, monkeypatch, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess([], 0, stdout="some diff content", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="not valid json at all", stderr=""),
            ]
            result = merge_gate_authorize._dispatch_review(
                "test", "devin", "main", str(tmp_path), str(tmp_path)
            )
        assert result is None


# ── CLI integration tests (authorize subcommand) ─────────────────────────

class TestAuthorizeCLI:
    def test_cli_refuses_without_sign_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_WITNESS_SIGN_KEY", raising=False)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        argv = ["merge_gate_authorize.py", "authorize", "42", "--repo", "owner/repo"]
        old_argv = sys.argv
        try:
            sys.argv = argv
            rc = merge_gate_authorize.main()
        finally:
            sys.argv = old_argv
        assert rc == 1

    def test_cli_refuses_without_brain_path(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-key")
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        argv = ["merge_gate_authorize.py", "authorize", "42", "--repo", "owner/repo"]
        old_argv = sys.argv
        try:
            sys.argv = argv
            rc = merge_gate_authorize.main()
        finally:
            sys.argv = old_argv
        assert rc == 1

    def test_cli_has_output_flag(self):
        """The --output flag is the trust-boundary crossing point — the JSON
        auth blob goes there, keeping stdout clean for operator-readable
        diagnostics."""
        import subprocess
        help_out = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "merge_gate_authorize.py"), "authorize", "--help"],
            capture_output=True, text=True,
        ).stdout
        assert "--output" in help_out

    def test_cli_has_reconcile_subcommand(self):
        import subprocess
        help_out = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "merge_gate_authorize.py"), "--help"],
            capture_output=True, text=True,
        ).stdout
        assert "reconcile" in help_out


# ── Reconcile CLI tests ──────────────────────────────────────────────────

class TestReconcileCLI:
    def test_reconcile_refuses_without_brain_path(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        argv = ["merge_gate_authorize.py", "reconcile", "42", "a" * 40,
                "--audit-record-id", "1", "--witness-id", "w1",
                "--repo", "owner/repo"]
        old_argv = sys.argv
        try:
            sys.argv = argv
            rc = merge_gate_authorize.main()
        finally:
            sys.argv = old_argv
        assert rc == 1

    def test_reconcile_has_executor_outcome_flag(self):
        """The --executor-outcome flag is how the untrusted side's output
        crosses back to the keyed side as a HINT (never trusted)."""
        import subprocess
        help_out = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "merge_gate_authorize.py"), "reconcile", "--help"],
            capture_output=True, text=True,
        ).stdout
        assert "--executor-outcome" in help_out


# ── autonomous_merge_loop.sh exit-code propagation tests ──────────────────
# Regression for the `if ! cmd; then RC=$?` bug: inside an `if !` block,
# `$?` reflects the `!` operator's own 0/1 result, NOT cmd's actual exit
# code. The reconcile step can exit 0/1/2/3 with distinct meanings
# (2 = audit-chain FREEZE, 3 = SHA-mismatch INCIDENT) — the wrapper MUST
# propagate the real code, not flatten it to 0.

_LOOP_SCRIPT = _SCRIPTS_DIR / "autonomous_merge_loop.sh"

_STUB_AUTHORIZE = '''#!/usr/bin/env python3
import json, sys, os
sub = sys.argv[1]
if sub == "authorize":
    # Find --output <path> in argv and write a valid auth blob there.
    out = None
    for i, a in enumerate(sys.argv):
        if a == "--output" and i + 1 < len(sys.argv):
            out = sys.argv[i + 1]
    blob = {
        "pr_number": 42,
        "head_sha": "a" * 40,
        "repo": "owner/repo",
        "witness_id": "w1",
        "audit_record_id": 1,
        "vendor_instructions": [
            "git push -u origin HEAD",
            "gh api -X DELETE repos/owner/repo/branches/main/protection/enforce_admins",
            "gh pr merge 42 --admin --squash --match-head-commit " + "a" * 40,
            "gh api -X POST repos/owner/repo/branches/main/protection/enforce_admins",
        ],
    }
    (open(out, "w") if out else sys.stdout).write(json.dumps(blob))
    sys.exit(0)
elif sub == "reconcile":
    # Exit with a configurable code (default 3 = INCIDENT) to test
    # propagation. The real cmd_reconcile returns 0/1/2/3/4.
    sys.exit(int(os.environ.get("STUB_RECONCILE_RC", "3")))
else:
    sys.exit(1)
'''

_STUB_EXECUTE = '''#!/usr/bin/env bash
# Minimal stub: write valid JSON to stdout, exit 0.
cat <<'JSON'
{"pr_number": 42, "head_sha": "%s", "repo": "owner/repo", "steps": [], "merge_exit_code": 0, "enforce_admins_restored": true}
JSON
exit 0
''' % ("a" * 40)


class TestLoopExitCodePropagation:
    """The wrapper autonomous_merge_loop.sh MUST propagate reconcile's real
    exit code (0/1/2/3/4), not flatten it to 0 via the `if ! cmd; then RC=$?`
    bug. These tests stub both subprocess calls the wrapper makes and
    verify the wrapper's own exit code matches the stubbed reconcile code."""

    def _make_stub_dir(self, tmp_path):
        """Create a temp dir with the real loop script + stub siblings.
        The loop resolves its siblings via SCRIPT_DIR=$(dirname $0), so
        placing stubs next to a copy of the loop makes it use them."""
        import shutil
        stub_dir = tmp_path / "stubs"
        stub_dir.mkdir()
        # Copy the REAL loop script (we're testing IT, not stubbing it).
        shutil.copy(_LOOP_SCRIPT, stub_dir / "autonomous_merge_loop.sh")
        # Stub the two siblings it calls.
        (stub_dir / "merge_gate_authorize.py").write_text(_STUB_AUTHORIZE)
        (stub_dir / "merge_gate_execute.sh").write_text(_STUB_EXECUTE)
        return stub_dir

    def _run_loop(self, stub_dir, *extra_args, env=None):
        import subprocess
        full_env = {"PATH": "/usr/bin:/bin"}
        if env:
            full_env.update(env)
        return subprocess.run(
            ["bash", str(stub_dir / "autonomous_merge_loop.sh"), "42",
             "--repo", "owner/repo", "--dry-run", *extra_args],
            capture_output=True, text=True, env=full_env, timeout=15,
        )

    def test_reconcile_exit_3_propagates_as_3(self, tmp_path):
        """INCIDENT (exit 3) must propagate as 3, NOT 0. This is the exact
        bug: the old `if ! cmd; then RC=$?` code would report 0 (success)
        here, hiding a SHA-mismatch incident."""
        stub_dir = self._make_stub_dir(tmp_path)
        result = self._run_loop(stub_dir, env={"STUB_RECONCILE_RC": "3"})
        assert result.returncode == 3, (
            f"expected exit 3 (INCIDENT propagation), got {result.returncode}\n"
            f"stderr:\n{result.stderr}"
        )

    def test_reconcile_exit_2_propagates_as_2(self, tmp_path):
        """FREEZE (exit 2 = audit chain broken) must propagate as 2."""
        stub_dir = self._make_stub_dir(tmp_path)
        result = self._run_loop(stub_dir, env={"STUB_RECONCILE_RC": "2"})
        assert result.returncode == 2, (
            f"expected exit 2 (FREEZE propagation), got {result.returncode}\n"
            f"stderr:\n{result.stderr}"
        )

    def test_reconcile_exit_1_propagates_as_1(self, tmp_path):
        """Generic failure (exit 1) must propagate as 1."""
        stub_dir = self._make_stub_dir(tmp_path)
        result = self._run_loop(stub_dir, env={"STUB_RECONCILE_RC": "1"})
        assert result.returncode == 1, (
            f"expected exit 1, got {result.returncode}\n"
            f"stderr:\n{result.stderr}"
        )

    def test_reconcile_exit_0_propagates_as_0(self, tmp_path):
        """Success (exit 0) must still propagate as 0 — the fix must not
        break the happy path."""
        stub_dir = self._make_stub_dir(tmp_path)
        result = self._run_loop(stub_dir, env={"STUB_RECONCILE_RC": "0"})
        assert result.returncode == 0, (
            f"expected exit 0 (success), got {result.returncode}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "done — merged clean" in result.stderr
