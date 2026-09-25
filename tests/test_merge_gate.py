"""Tests for scripts/merge_gate.py — the autonomous merge gate wrapper.

Exercises the actual sign/verify/lock/audit logic against isolated temp
brain dirs. Never touches real .brain files or GitHub — the mechanical
gh/git calls always run with dry_run=True in these tests.
"""
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
_spec = importlib.util.spec_from_file_location("merge_gate", _SCRIPTS_DIR / "merge_gate.py")
merge_gate = importlib.util.module_from_spec(_spec)
sys.modules["merge_gate"] = merge_gate
_spec.loader.exec_module(merge_gate)

from mcp_server_nucleus.runtime.agent_os import witness_test_results as witness


def _write_ground_receipt(path: Path, *, verified=True, tiers_passed=(0, 1, 2, 3),
                           tiers_failed=(), age_seconds=0):
    ts = datetime.fromtimestamp(time.time() - age_seconds, tz=timezone.utc).isoformat()
    receipt = {
        "verified": verified,
        "tiers_passed": list(tiers_passed),
        "tiers_failed": list(tiers_failed),
        "timestamp": ts,
    }
    path.write_text(json.dumps(receipt) + "\n")
    return path


def _write_review_transcript(path: Path, *, verdict="APPROVE"):
    path.write_text(f"Some review prose here.\n\nVERDICT: {verdict}\n\nReasoning follows.\n")
    return path


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-signing-key")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.chdir(tmp_path)
    yield brain
    merge_gate.release_lock()


@pytest.fixture
def valid_evidence(tmp_path):
    ground = _write_ground_receipt(tmp_path / "ground_receipt.jsonl")
    review = _write_review_transcript(tmp_path / "review.txt")
    return {"ground_receipt_path": str(ground), "review_transcript_path": str(review)}


class TestPreflight:
    def test_passes_with_fixed_code(self, isolated_brain):
        merge_gate.preflight_check()  # must not raise

    def test_catches_forgeable_fallback_key_regression(self, isolated_brain, monkeypatch):
        def vulnerable_sign(payload, key=None):
            import hashlib
            import hmac
            sign_key = key or os.environ.get(witness._SIGN_KEY_ENV, "default-witness-key")
            return hmac.new(sign_key.encode(), payload.encode(), hashlib.sha256).hexdigest()

        monkeypatch.setattr(witness, "_sign", vulnerable_sign)
        with pytest.raises(merge_gate.GateError, match="did not raise"):
            merge_gate.preflight_check()

    def test_rejects_import_from_wrong_module_path(self, isolated_brain, monkeypatch):
        # Simulates a stale installed package copy already loaded in the
        # interpreter under a path outside this repo's source tree.
        monkeypatch.setattr(witness, "__file__", "/some/other/venv/site-packages/witness_test_results.py")
        with pytest.raises(merge_gate.GateError, match="not from this repo's source tree"):
            merge_gate.preflight_check()


class TestEvidenceValidation:
    """These are the tests that didn't exist before the second hardening
    pass — covering the actual C1 fix (gate reads real evidence, not a
    bare claim)."""

    def test_ground_receipt_must_exist(self, isolated_brain, tmp_path):
        with pytest.raises(merge_gate.GateError, match="not found"):
            merge_gate._load_ground_receipt(str(tmp_path / "nonexistent.jsonl"), max_age_seconds=1800)

    def test_ground_receipt_verified_false_rejected(self, isolated_brain, tmp_path):
        p = _write_ground_receipt(tmp_path / "r.jsonl", verified=False, tiers_failed=(3,))
        with pytest.raises(merge_gate.GateError, match="verified=False"):
            merge_gate._load_ground_receipt(str(p), max_age_seconds=1800)

    def test_ground_receipt_stale_rejected(self, isolated_brain, tmp_path):
        p = _write_ground_receipt(tmp_path / "r.jsonl", age_seconds=3600)
        with pytest.raises(merge_gate.GateError, match="exceeds max_age_seconds"):
            merge_gate._load_ground_receipt(str(p), max_age_seconds=1800)

    def test_ground_receipt_fresh_accepted(self, isolated_brain, tmp_path):
        p = _write_ground_receipt(tmp_path / "r.jsonl", age_seconds=10)
        receipt = merge_gate._load_ground_receipt(str(p), max_age_seconds=1800)
        assert receipt["verified"] is True

    def test_review_transcript_must_contain_approve_marker(self, isolated_brain, tmp_path):
        p = tmp_path / "review.txt"
        p.write_text("This looks fine to me, ship it.")  # no VERDICT: marker at all
        with pytest.raises(merge_gate.GateError, match="no 'VERDICT: APPROVE' marker"):
            merge_gate._load_review_verdict(str(p))

    def test_review_transcript_reject_verdict_blocks(self, isolated_brain, tmp_path):
        p = _write_review_transcript(tmp_path / "review.txt", verdict="REJECT")
        with pytest.raises(merge_gate.GateError, match="VERDICT: REJECT"):
            merge_gate._load_review_verdict(str(p))

    def test_review_transcript_approve_accepted(self, isolated_brain, tmp_path):
        p = _write_review_transcript(tmp_path / "review.txt")
        assert merge_gate._load_review_verdict(str(p)) == "APPROVE"


class TestGate:
    def test_run_gate_pins_merge_to_exact_sha(self, isolated_brain, valid_evidence):
        sha = "d" * 40
        result = merge_gate.run_gate(pr_number=42, head_sha=sha, dry_run=True, **valid_evidence)
        assert result["witness_id"] == f"witness-test-{sha}"
        assert any(f"--match-head-commit {sha}" in step for step in result["vendor_instructions"])
        merge_gate.release_lock()

    def test_short_sha_rejected(self, isolated_brain, valid_evidence):
        # A short SHA must be rejected outright, not accepted and later
        # prefix-matched — prefix-matching a short SHA against a full
        # headRefOid is a real vulnerability (a 7-char prefix can be
        # collision-ground in seconds with tools like lucky-commit).
        with pytest.raises(merge_gate.GateError, match="not a clean hex SHA"):
            merge_gate.run_gate(pr_number=100, head_sha="deadbeef123", dry_run=True, **valid_evidence)
        assert not merge_gate._lock_dir().exists()

    def test_gate_refuses_without_passing_ground_receipt(self, isolated_brain, tmp_path, valid_evidence):
        bad_ground = _write_ground_receipt(tmp_path / "bad.jsonl", verified=False)
        with pytest.raises(merge_gate.GateError, match="verified=False"):
            merge_gate.run_gate(
                pr_number=1, head_sha="1"*40, dry_run=True,
                ground_receipt_path=str(bad_ground),
                review_transcript_path=valid_evidence["review_transcript_path"],
            )
        # lock must not be leaked by this failure path
        assert not merge_gate._lock_dir().exists()

    def test_gate_refuses_without_approve_verdict(self, isolated_brain, tmp_path, valid_evidence):
        bad_review = _write_review_transcript(tmp_path / "bad_review.txt", verdict="REJECT")
        with pytest.raises(merge_gate.GateError, match="VERDICT: REJECT"):
            merge_gate.run_gate(
                pr_number=1, head_sha="1"*40, dry_run=True,
                ground_receipt_path=valid_evidence["ground_receipt_path"],
                review_transcript_path=str(bad_review),
            )
        assert not merge_gate._lock_dir().exists()

    def test_malicious_head_sha_rejected_before_instruction_construction(self, isolated_brain, valid_evidence):
        with pytest.raises(merge_gate.GateError, match="not a clean hex SHA"):
            merge_gate.run_gate(pr_number=99, head_sha="abc; rm -rf /", dry_run=True, **valid_evidence)
        assert not merge_gate._lock_dir().exists()

    def test_concurrent_gate_refused(self, isolated_brain, valid_evidence):
        merge_gate.run_gate(pr_number=1, head_sha="1"*40, dry_run=True, **valid_evidence)
        with pytest.raises(merge_gate.GateError, match="holds the lock"):
            merge_gate.run_gate(pr_number=2, head_sha="2"*40, dry_run=True, **valid_evidence)
        merge_gate.release_lock()

    def test_gate_verifies_its_own_witness_write(self, isolated_brain, valid_evidence):
        result = merge_gate.run_gate(pr_number=3, head_sha="3"*40, dry_run=True, **valid_evidence)
        entries = witness.get_test_result_entries(agent_id="merge-gate", limit=10)
        matching = [e for e in entries if e["witness_id"] == result["witness_id"]]
        assert len(matching) == 1
        assert witness.verify_signature(dict(matching[0]))
        merge_gate.release_lock()

    def test_non_gate_error_still_releases_lock(self, isolated_brain, valid_evidence, monkeypatch):
        # Simulates audit_log.log_event raising something other than
        # GateError after the witness write already succeeded.
        from mcp_server_nucleus.runtime import audit_log as audit_log_mod

        def boom(*a, **kw):
            raise RuntimeError("simulated audit DB failure")

        monkeypatch.setattr(merge_gate.audit_log, "log_event", boom)
        with pytest.raises(RuntimeError, match="simulated audit DB failure"):
            merge_gate.run_gate(pr_number=7, head_sha="7"*40, dry_run=True, **valid_evidence)
        assert not merge_gate._lock_dir().exists()  # lock released even on a non-GateError exception


class TestBrainPathAnchoring:
    """Covers the fix for the lock/audit-chain anchoring bug: they must be
    keyed on NUCLEUS_BRAIN_PATH (an explicit, required input every
    invocation shares), never on wherever this script's own file happens
    to be checked out — a fresh throwaway clone must see the SAME lock as
    every other invocation, or the concurrency mutex is worthless."""

    def test_brain_path_required(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        with pytest.raises(merge_gate.GateError, match="NUCLEUS_BRAIN_PATH is not set"):
            merge_gate._brain_path()

    def test_brain_path_must_exist(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "does_not_exist"))
        with pytest.raises(merge_gate.GateError, match="does not exist"):
            merge_gate._brain_path()

    def test_lock_dir_independent_of_script_location(self, isolated_brain, valid_evidence, tmp_path):
        # The regression this guards against: LOCK_DIR used to be
        # _REPO_ROOT-anchored (Path(__file__).resolve().parent.parent) —
        # a fresh clone per invocation meant a fresh, empty, never-shared
        # lock dir every time. Confirm the lock now lands INSIDE
        # NUCLEUS_BRAIN_PATH, which every invocation is required to share.
        sha = "c" * 40
        result = merge_gate.run_gate(pr_number=12, head_sha=sha, dry_run=True, **valid_evidence)
        assert merge_gate._lock_dir().parent == isolated_brain
        merge_gate.release_lock()


class TestReconcile:
    def test_reconcile_releases_lock(self, isolated_brain, valid_evidence):
        sha = "5" * 40
        result = merge_gate.run_gate(pr_number=5, head_sha=sha, dry_run=True, **valid_evidence)
        assert merge_gate._lock_dir().exists()
        merge_gate.reconcile(5, sha, result["audit_record_id"], result["witness_id"], dry_run=True)
        assert not merge_gate._lock_dir().exists()

    def test_reconcile_never_trusts_a_missing_report(self, isolated_brain, valid_evidence):
        # Simulates a crashed vendor dispatch: gate ran, vendor never
        # reported anything. reconcile() must still run and release the
        # lock — it does not require vendor input to function.
        sha = "6" * 40
        result = merge_gate.run_gate(pr_number=6, head_sha=sha, dry_run=True, **valid_evidence)
        recon = merge_gate.reconcile(6, sha, result["audit_record_id"], result["witness_id"], dry_run=True)
        assert recon["outcome"] in ("success", "failed", "sha_mismatch_incident", "sha_unverifiable_incident")

    def test_reconcile_detects_sha_mismatch(self, isolated_brain, valid_evidence, monkeypatch):
        # THE test for the C2 fix: PR shows MERGED but the recorded
        # headRefOid does not match the SHA that was actually gated —
        # must be flagged as an incident, not silently reported "success".
        sha = "8" * 40
        result = merge_gate.run_gate(pr_number=8, head_sha=sha, dry_run=True, **valid_evidence)

        import subprocess as sp

        def fake_run(cmd, *, dry_run=False, check=True):
            # Fully isolated fake — never falls through to a real subprocess
            # call, regardless of dry_run, so this test can never touch a
            # real gh/git binary or network.
            joined = " ".join(cmd)
            if "pr" in cmd and "view" in cmd:
                payload = json.dumps({
                    "state": "MERGED",
                    "mergeCommit": {"oid": "f" * 40},
                    "headRefOid": "f" * 40,  # deliberately != gated head_sha
                })
                return sp.CompletedProcess(cmd, 0, stdout=payload, stderr="")
            if "protection" in joined and "-X" not in cmd:
                return sp.CompletedProcess(cmd, 0, stdout='{"enabled":true}', stderr="")
            if "protection" in joined and "-X" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="", stderr="")
            if "ls-remote" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="fakehead\trefs/heads/main\n", stderr="")
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(merge_gate, "_run", fake_run)
        recon = merge_gate.reconcile(8, sha, result["audit_record_id"], result["witness_id"], dry_run=False)
        assert recon["outcome"] == "sha_mismatch_incident"
        assert recon["sha_mismatch"] is True

    def test_reconcile_matching_sha_reports_success(self, isolated_brain, valid_evidence, monkeypatch):
        # Opposed pair to test_reconcile_detects_sha_mismatch — proves the
        # mismatch check isn't just "always fire an incident". headRefOid
        # EXACTLY equals the gated head_sha (exact-match, not prefix —
        # prefix-matching a short SHA was a real vulnerability, fixed by
        # requiring a full 40-char SHA end-to-end).
        sha = "9" * 40
        result = merge_gate.run_gate(pr_number=9, head_sha=sha, dry_run=True, **valid_evidence)

        import subprocess as sp

        def fake_run(cmd, *, dry_run=False, check=True):
            joined = " ".join(cmd)
            if "pr" in cmd and "view" in cmd:
                payload = json.dumps({
                    "state": "MERGED",
                    "mergeCommit": {"oid": sha},
                    "headRefOid": sha,  # exactly matches gated head_sha
                })
                return sp.CompletedProcess(cmd, 0, stdout=payload, stderr="")
            if "protection" in joined and "-X" not in cmd:
                return sp.CompletedProcess(cmd, 0, stdout='{"enabled":true}', stderr="")
            if "protection" in joined and "-X" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="", stderr="")
            if "ls-remote" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="fakehead\trefs/heads/main\n", stderr="")
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(merge_gate, "_run", fake_run)
        recon = merge_gate.reconcile(9, sha, result["audit_record_id"], result["witness_id"], dry_run=False)
        assert recon["outcome"] == "success"
        assert recon["sha_mismatch"] is False

    def test_reconcile_similar_but_not_equal_sha_is_mismatch(self, isolated_brain, valid_evidence, monkeypatch):
        # Guards specifically against the prefix-collision vulnerability
        # fable found: a headRefOid that SHARES A PREFIX with the gated
        # head_sha but is NOT identical must still be flagged as a mismatch
        # under exact-match comparison.
        sha = "b" * 40
        near_collision = "b" * 20 + "c" * 20  # shares the first 20 chars, differs after
        result = merge_gate.run_gate(pr_number=11, head_sha=sha, dry_run=True, **valid_evidence)

        import subprocess as sp

        def fake_run(cmd, *, dry_run=False, check=True):
            joined = " ".join(cmd)
            if "pr" in cmd and "view" in cmd:
                payload = json.dumps({
                    "state": "MERGED",
                    "mergeCommit": {"oid": near_collision},
                    "headRefOid": near_collision,
                })
                return sp.CompletedProcess(cmd, 0, stdout=payload, stderr="")
            if "protection" in joined and "-X" not in cmd:
                return sp.CompletedProcess(cmd, 0, stdout='{"enabled":true}', stderr="")
            if "protection" in joined and "-X" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="", stderr="")
            if "ls-remote" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="fakehead\trefs/heads/main\n", stderr="")
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(merge_gate, "_run", fake_run)
        recon = merge_gate.reconcile(11, sha, result["audit_record_id"], result["witness_id"], dry_run=False)
        assert recon["outcome"] == "sha_mismatch_incident"

    def test_reconcile_missing_head_ref_oid_is_unverifiable_not_success(self, isolated_brain, valid_evidence, monkeypatch):
        # H-new-1 fix: a MERGED PR with no headRefOid in the API response
        # must NOT be coerced to "success" just because nothing contradicted
        # it — "couldn't verify" and "verified clean" are different states.
        sha = "a" * 40
        result = merge_gate.run_gate(pr_number=10, head_sha=sha, dry_run=True, **valid_evidence)

        import subprocess as sp

        def fake_run(cmd, *, dry_run=False, check=True):
            joined = " ".join(cmd)
            if "pr" in cmd and "view" in cmd:
                payload = json.dumps({"state": "MERGED", "mergeCommit": {"oid": "somesha"}})  # no headRefOid
                return sp.CompletedProcess(cmd, 0, stdout=payload, stderr="")
            if "protection" in joined and "-X" not in cmd:
                return sp.CompletedProcess(cmd, 0, stdout='{"enabled":true}', stderr="")
            if "protection" in joined and "-X" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="", stderr="")
            if "ls-remote" in cmd:
                return sp.CompletedProcess(cmd, 0, stdout="fakehead\trefs/heads/main\n", stderr="")
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(merge_gate, "_run", fake_run)
        recon = merge_gate.reconcile(10, sha, result["audit_record_id"], result["witness_id"], dry_run=False)
        assert recon["outcome"] == "sha_unverifiable_incident"
        assert recon["outcome"] != "success"


class TestReconcileRepoFlag:
    """Covers the fix for the multi-repo bug: reconcile() had a repo=
    keyword param but the CLI never exposed it, so every reconcile
    invocation checked/restored branch protection on the hardcoded
    DEFAULT_REPO regardless of what --repo the gate step used."""

    def test_reconcile_accepts_explicit_repo(self, isolated_brain, valid_evidence, monkeypatch):
        sha = "e" * 40
        result = merge_gate.run_gate(pr_number=13, head_sha=sha, dry_run=True, **valid_evidence)

        calls = []

        def fake_run(cmd, *, dry_run=False, check=True):
            import subprocess as sp
            calls.append(cmd)
            joined = " ".join(cmd)
            if "pr" in cmd and "view" in cmd:
                payload = json.dumps({"state": "MERGED", "mergeCommit": {"oid": sha}, "headRefOid": sha})
                return sp.CompletedProcess(cmd, 0, stdout=payload, stderr="")
            if "protection" in joined and "-X" not in cmd:
                return sp.CompletedProcess(cmd, 0, stdout='{"enabled":true}', stderr="")
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(merge_gate, "_run", fake_run)
        merge_gate.reconcile(13, sha, result["audit_record_id"], result["witness_id"],
                              repo="someorg/somerepo", dry_run=False)
        assert any("someorg/somerepo" in " ".join(c) for c in calls), \
            "reconcile must check protection against the REPO it was told, not the hardcoded default"

    def test_cli_reconcile_subparser_has_repo_flag(self):
        # Regression guard at the argparse level, not just the function
        # signature — this is what actually broke: the function always
        # had repo=, the CLI subparser never exposed it.
        import subprocess
        help_out = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "merge_gate.py"), "reconcile", "--help"],
            capture_output=True, text=True,
        ).stdout
        assert "--repo" in help_out


class TestReconcileExitCodeDryRun:
    """Regression guard for the exit-code-4 fix (see main()): a real
    `outcome == "failed"` (PR never merged) exits 4 so a caller checking
    only the exit code can't mistake it for success. But under --dry-run,
    _run() never contacts GitHub — `gh pr view` returns nothing, so
    "failed" is the EXPECTED outcome of every dry-run reconcile, not a
    signal something broke. Without a carve-out, exit code 4 fires on
    every single dry-run reconcile, which breaks any rehearsal/smoke
    tooling gating on exit 0."""

    def test_cli_reconcile_dry_run_failed_outcome_exits_zero(self, isolated_brain, valid_evidence):
        sha = "f" * 40
        gate_result = merge_gate.run_gate(pr_number=21, head_sha=sha, dry_run=True, **valid_evidence)
        argv = [
            "reconcile", "21", sha,
            "--audit-record-id", str(gate_result["audit_record_id"]),
            "--witness-id", gate_result["witness_id"],
            "--dry-run",
        ]
        import sys as _sys
        old_argv = _sys.argv
        try:
            _sys.argv = ["merge_gate.py"] + argv
            rc = merge_gate.main()
        finally:
            _sys.argv = old_argv
        assert rc == 0, (
            "a dry-run reconcile's inevitable outcome=='failed' (no real "
            "gh/git calls happen under --dry-run) must exit 0, not 4 — "
            "exit 4 is reserved for a REAL run that failed to merge"
        )


class TestLoadBuildVerifyReceipt:
    """Covers ``_load_build_verify_receipt`` — the supplementary evidence
    reader for System A's build_runner VERIFY-stage receipt. It is
    best-effort by design: the gate's own fresh GROUND re-check is
    load-bearing, so this reader must NEVER refuse the gate — it returns
    ``None`` for every degenerate input and only returns a dict for a
    genuinely parseable JSON file."""

    def test_valid_json_returned(self, tmp_path):
        p = tmp_path / "build.json"
        p.write_text(json.dumps({"verify": "ok", "tiers": [0, 1, 2, 3]}))
        receipt = merge_gate._load_build_verify_receipt(str(p))
        assert receipt == {"verify": "ok", "tiers": [0, 1, 2, 3]}

    def test_none_path_returns_none(self):
        assert merge_gate._load_build_verify_receipt(None) is None

    def test_empty_string_path_returns_none(self):
        assert merge_gate._load_build_verify_receipt("") is None

    def test_nonexistent_file_returns_none(self, tmp_path):
        # Best-effort: a missing receipt must not refuse the gate.
        assert merge_gate._load_build_verify_receipt(str(tmp_path / "nope.json")) is None

    def test_malformed_json_returns_none(self, tmp_path, capsys):
        p = tmp_path / "broken.json"
        p.write_text("{not valid json,,,")
        receipt = merge_gate._load_build_verify_receipt(str(p))
        assert receipt is None
        # The reader logs a best-effort warning to stderr rather than raising.
        captured = capsys.readouterr()
        assert "unreadable" in captured.err
        assert "proceeding without supplementary evidence" in captured.err


class TestNoModuleEvictionOnLoad:
    """Regression test for fw-1786126469: loading merge_gate must NOT evict
    or replace any pre-existing mcp_server_nucleus.* entry from sys.modules.

    The original path surgery deleted every mcp_server_nucleus* entry from
    sys.modules at import time so the script's own `from mcp_server_nucleus...
    import` would re-resolve against _SRC_DIR. That mutated the importing
    process's shared module table: other modules that had already imported
    mcp_server_nucleus submodules kept holding references to the now-removed
    module objects, so a later patch('mcp_server_nucleus.runtime.X.y') bound
    to a DIFFERENT object than the code under test called. This silently
    broke tests/test_cli_build.py (27 failures) whenever test_merge_gate.py
    was collected in the same run, because the broken mocks let real vendor
    calls escape.

    This test loads a FRESH copy of merge_gate (under a throwaway module name)
    after recording the identities of every mcp_server_nucleus* object in
    sys.modules, then asserts none of them were replaced."""

    def test_loading_merge_gate_does_not_replace_existing_modules(self):
        import importlib.util

        # Snapshot the identities of every pre-existing mcp_server_nucleus*
        # entry in sys.modules BEFORE loading merge_gate.
        before = {
            name: mod
            for name, mod in list(sys.modules.items())
            if name == "mcp_server_nucleus" or name.startswith("mcp_server_nucleus.")
        }
        assert before, (
            "test precondition: mcp_server_nucleus must already be imported "
            "(the test module imports it at module scope) — if this fails, "
            "the test is no longer exercising the regression"
        )

        # Load a FRESH copy of merge_gate under a throwaway name so we don't
        # clobber the already-loaded `merge_gate` module the rest of this
        # test file uses. exec_module re-runs the module body, including the
        # path surgery under test.
        spec = importlib.util.spec_from_file_location(
            "merge_gate_eviction_regression",
            _SCRIPTS_DIR / "merge_gate.py",
        )
        fresh = importlib.util.module_from_spec(spec)
        sys.modules["merge_gate_eviction_regression"] = fresh
        try:
            spec.loader.exec_module(fresh)
        finally:
            sys.modules.pop("merge_gate_eviction_regression", None)

        # Every mcp_server_nucleus* entry that existed before loading must
        # still be the SAME object — not evicted, not replaced.
        for name, original_mod in before.items():
            assert name in sys.modules, (
                f"merge_gate evicted {name!r} from sys.modules on load — "
                f"this is the fw-1786126469 regression: it deletes module "
                f"objects other code still holds references to"
            )
            assert sys.modules[name] is original_mod, (
                f"merge_gate replaced {name!r} in sys.modules with a new "
                f"object on load — this is the fw-1786126469 regression: "
                f"patch() would bind to the new object while code under "
                f"test still calls the original"
            )
