"""Sanity tests for scripts/merge_gate_execute.sh — the untrusted/vendor side
of the merge gate trust split.

Verifies:
  1. `bash -n` passes (no syntax errors).
  2. The witness signing key env var name NEVER appears anywhere in the file
     (not in code, not in comments) — this is the core trust-split property:
     the executor must be safe to hand to an untrusted vendor process.
  3. The script refuses to run without an input file.
  4. The script refuses a malformed head_sha (not a clean 40-char hex SHA).
  5. The script refuses a malformed repo string.
"""
import subprocess
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
EXECUTE_SCRIPT = _SCRIPTS_DIR / "merge_gate_execute.sh"

# The exact env var name that must NEVER appear in the executor script.
# This is the whole point of the trust split: the keyed side holds this,
# the untrusted executor must not reference it at all.
_SIGN_KEY_ENV = "NUCLEUS_WITNESS_SIGN_KEY"


class TestExecuteScriptSyntax:
    def test_bash_n_passes(self):
        """The script must have no bash syntax errors."""
        result = subprocess.run(
            ["bash", "-n", str(EXECUTE_SCRIPT)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"

    def test_signing_key_env_var_never_appears(self):
        """The witness signing key env var name must NEVER appear in the
        executor script — not in code, not in comments, not in strings.
        This is the core trust-split invariant: if this string appears,
        a vendor process could find and exfiltrate the key."""
        content = EXECUTE_SCRIPT.read_text()
        assert _SIGN_KEY_ENV not in content, (
            f"{_SIGN_KEY_ENV} found in merge_gate_execute.sh — this violates "
            f"the trust split. The executor must never reference the signing key."
        )

    def test_script_is_executable(self):
        """The script should have execute permissions set."""
        assert EXECUTE_SCRIPT.stat().st_mode & 0o100, (
            "merge_gate_execute.sh is not executable"
        )


class TestExecuteScriptRefusals:
    """The executor must refuse invalid inputs before executing anything."""

    def _run_execute(self, *args, stdin_data=None):
        return subprocess.run(
            ["bash", str(EXECUTE_SCRIPT), *args],
            capture_output=True, text=True, stdin=stdin_data,
            timeout=10,
        )

    def test_refuses_without_input_file(self, tmp_path):
        result = self._run_execute()
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "no input file" in result.stderr

    def test_refuses_nonexistent_input_file(self, tmp_path):
        result = self._run_execute("--input", str(tmp_path / "nonexistent.json"))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "not found" in result.stderr

    def test_refuses_malformed_head_sha(self, tmp_path):
        """A malformed head_sha could inject shell tokens into the
        gh pr merge --match-head-commit instruction — must be rejected."""
        import json
        auth = {
            "pr_number": 42,
            "head_sha": "abc; rm -rf /",  # malicious, not a clean SHA
            "repo": "owner/repo",
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": [],
        }
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "not a clean 40-char hex SHA" in result.stderr

    def test_refuses_short_head_sha(self, tmp_path):
        """A short SHA must be rejected — prefix-matching a short SHA is a
        real vulnerability (collision-groundable in seconds)."""
        import json
        auth = {
            "pr_number": 42,
            "head_sha": "abc123",  # too short
            "repo": "owner/repo",
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": [],
        }
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "not a clean 40-char hex SHA" in result.stderr

    def test_refuses_malformed_repo(self, tmp_path):
        """A malformed repo string could inject shell tokens into the
        enforce_admins API calls — must be rejected."""
        import json
        auth = {
            "pr_number": 42,
            "head_sha": "a" * 40,
            "repo": "owner; rm -rf /",  # malicious
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": [],
        }
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "not a clean owner/repo string" in result.stderr

    def test_refuses_empty_instructions(self, tmp_path):
        """An auth blob with no vendor_instructions is invalid — the keyed
        side should always produce 3 instructions."""
        import json
        auth = {
            "pr_number": 42,
            "head_sha": "a" * 40,
            "repo": "owner/repo",
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": [],
        }
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "no vendor_instructions" in result.stderr


def _expected_instructions(pr_number, head_sha, repo):
    """Mirror scripts/merge_gate.py _mechanical_merge_steps() exactly.
    3 instructions (fw-1785844026): the dead `git push -u origin HEAD` step
    was removed — the gated head_sha is always already on origin."""
    return [
        f"gh api -X DELETE repos/{repo}/branches/main/protection/enforce_admins",
        f"gh pr merge {pr_number} --admin --squash --match-head-commit {head_sha}",
        f"gh api -X POST repos/{repo}/branches/main/protection/enforce_admins",
    ]


class TestExecuteScriptInstructionValidation:
    """Finding 1: the executor must refuse a tampered vendor_instructions
    array before eval'ing anything, by exact-match against the 4 strings
    reconstructed locally from the already-validated scalar fields."""

    def _run_execute(self, *args, stdin_data=None, timeout=30):
        return subprocess.run(
            ["bash", str(EXECUTE_SCRIPT), *args],
            capture_output=True, text=True, stdin=stdin_data,
            timeout=timeout,
        )

    def _valid_auth(self, pr_number=42, head_sha=None, repo="owner/repo",
                    instructions=None):
        head_sha = head_sha or ("a" * 40)
        auth = {
            "pr_number": pr_number,
            "head_sha": head_sha,
            "repo": repo,
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": instructions
            if instructions is not None
            else _expected_instructions(pr_number, head_sha, repo),
        }
        return auth

    def test_refuses_injected_fourth_instruction(self, tmp_path):
        """(a) An injected 4th instruction must be refused before any eval
        runs — the injected instruction must NOT produce its side effect."""
        import json
        marker = tmp_path / "injected_marker"
        # The 3 legitimate instructions + a 4th that would create a marker
        # file if it were ever eval'd.
        instructions = _expected_instructions(42, "a" * 40, "owner/repo") + [
            f"touch {marker}",
        ]
        auth = self._valid_auth(instructions=instructions)
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "expected exactly 3" in result.stderr
        # The injected instruction must never have executed.
        assert not marker.exists(), (
            "injected 4th instruction executed (marker file created) — "
            "the exact-match gate failed to refuse before eval"
        )

    def test_refuses_subtly_modified_instruction(self, tmp_path):
        """(b) One of the 3 expected instructions subtly modified (an extra
        flag appended) must be refused."""
        import json
        head_sha = "a" * 40
        instructions = _expected_instructions(42, head_sha, "owner/repo")
        # Subtly modify the merge instruction: append an extra flag.
        instructions[1] = instructions[1] + " --extra-flag"
        auth = self._valid_auth(instructions=instructions)
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "not an exact match" in result.stderr

    def test_legitimate_instructions_pass_gate(self, tmp_path):
        """(c) Regression — the exact 4 instructions in the correct order
        built from valid PR_NUMBER/HEAD_SHA/REPO must pass the gate and
        proceed to execution. The steps themselves fail without gh auth /
        a git repo (the DELETE step REFUSES on its own and exits 1), but
        that is a step-level failure, NOT a gate failure. The gate's job is
        to let the legitimate set through; we assert the gate-specific
        refusal messages are absent and the executing banner fired."""
        import json
        auth = self._valid_auth()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path), timeout=30)
        # Gate-specific refusals must be absent — the gate let the set through.
        assert "expected exactly 4" not in result.stderr, (
            f"gate refused a legitimate 4-instruction set on count:\n{result.stderr}"
        )
        assert "not an exact match" not in result.stderr, (
            f"gate refused a legitimate 4-instruction set on content:\n{result.stderr}"
        )
        # The executing banner fired — proving we reached the eval loop
        # (i.e. the gate passed). The DELETE step then REFUSES on its own
        # because gh is unauthenticated in the test env; that is expected
        # and is NOT a gate failure.
        assert "executing 42@" in result.stderr

    def test_refuses_reordered_instructions(self, tmp_path):
        """Order matters (DELETE→merge→POST is load-bearing for the trap).
        A reordered-but-otherwise-correct set must be refused."""
        import json
        head_sha = "a" * 40
        instructions = _expected_instructions(42, head_sha, "owner/repo")
        # Swap the DELETE and POST steps (indices 0 and 2 in the 3-step format).
        instructions[0], instructions[2] = instructions[2], instructions[0]
        auth = self._valid_auth(instructions=instructions)
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        assert "not an exact match" in result.stderr


class TestExecuteScriptInputFilePathInjection:
    """Finding 2: $INPUT_FILE must be passed as sys.argv, not interpolated
    into the Python source string — a path containing a single quote must
    not break out of the Python string literal."""

    def _run_execute(self, *args, timeout=30):
        return subprocess.run(
            ["bash", str(EXECUTE_SCRIPT), *args],
            capture_output=True, text=True, timeout=timeout,
        )

    def test_single_quote_in_path_does_not_break_extraction(self, tmp_path):
        """(d) An input file whose PATH contains a single quote character
        must not cause a Python SyntaxError or unintended behavior. With
        the sys.argv fix, the scalar extraction succeeds and the script
        proceeds to the vendor_instructions check (refusing on empty). With
        the old interpolation, `open('a'b.json')` would be a Python
        SyntaxError and the script would REFUSE with 'could not parse
        pr_number' instead."""
        import json
        # macOS filesystem permits single quotes in filenames.
        auth = {
            "pr_number": 42,
            "head_sha": "a" * 40,
            "repo": "owner/repo",
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": [],
        }
        auth_path = tmp_path / "in'ject.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path))
        # The path-with-quote must NOT trigger a Python parse failure on the
        # scalar extraction. The proof: we reach the vendor_instructions
        # refusal, not the pr_number/head_sha/repo parse refusal.
        assert "could not parse pr_number" not in result.stderr, (
            f"single-quote-in-path broke the pr_number extraction "
            f"(Python injection still open):\n{result.stderr}"
        )
        assert "could not parse head_sha" not in result.stderr
        assert "could not parse repo" not in result.stderr
        assert result.returncode == 1
        assert "REFUSED" in result.stderr
        # We reached the vendor_instructions stage — extraction survived.
        assert "no vendor_instructions" in result.stderr

class TestExecuteScriptDeleteFailureJsonValidity:
    """Regression for a bug caught live by an adversarial review dispatch:
    when `git push` (step 1) succeeds and the DELETE enforce_admins step
    (step 2) fails, the early-exit path must still emit VALID, PARSEABLE
    JSON with exactly 2 well-formed step entries.

    The OLD early-exit code built the DELETE step's JSON inline with direct
    concatenation onto STEPS_JSON_PARTS and a trailing comma, producing
    `{push_obj}{delete_obj},` — two adjacent dict literals with no comma
    separator, which is a Python SyntaxError once interpolated into
    `'steps': [${STEPS_JSON_PARTS}]` in the output block. The fix reuses
    the normal per-step comma-handling pattern (`if [ -z ... ]; then ...
    else ... fi`).

    This test reproduces the exact failure mode: a preceding successful
    step (git push) populates STEPS_JSON_PARTS, THEN the DELETE step fails
    and the early-exit path fires. On the OLD code `json.loads(stdout)`
    raises (the output python3 -c crashes on the malformed list literal);
    on the fix it returns a dict with a 2-element `steps` array."""

    def _run_execute(self, *args, cwd=None, timeout=30, env=None):
        return subprocess.run(
            ["bash", str(EXECUTE_SCRIPT), *args],
            capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env,
        )

    def _make_pushable_repo(self, tmp_path):
        """Create a bare origin + a working repo with one commit so that
        `git push -u origin HEAD` (step 1) genuinely succeeds."""
        origin = tmp_path / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", str(origin)],
            check=True, capture_output=True,
        )
        work = tmp_path / "work"
        work.mkdir()
        subprocess.run(
            ["git", "init", str(work)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work), "config", "user.email", "test@test.test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work), "remote", "add", "origin", str(origin)],
            check=True, capture_output=True,
        )
        (work / "file.txt").write_text("hello")
        subprocess.run(
            ["git", "-C", str(work), "add", "."],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(work), "commit", "-m", "init"],
            check=True, capture_output=True,
        )
        return work

    @staticmethod
    def _extract_last_json(stdout):
        """Extract the last JSON object from stdout — the script's output
        block. `git push -u origin HEAD` prints a tracking message
        ('branch X set up to track ...') to stdout that precedes the JSON;
        the script does not redirect command stdout (pre-existing, out of
        scope for this fix). The script's JSON is pretty-printed with
        indent=2, so it starts with '{' on its own line. We find the last
        such line and parse from there."""
        import json
        lines = stdout.split('\n')
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '{':
                candidate = '\n'.join(lines[i:])
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"no valid JSON object found in stdout:\n{stdout!r}")

    def test_delete_failure_after_successful_push_emits_valid_json(self, tmp_path):
        """DELETE enforce_admins step fails (gh unauthenticated via
        GH_CONFIG_DIR → exit 4, no stdout) → the early-exit path fires.
        The stdout MUST contain parseable JSON with a 1-element `steps`
        array (the failed DELETE step). The git push step was removed
        (fw-1785844026) so there is no push step to populate
        STEPS_JSON_PARTS first — only the failed DELETE appears."""
        import json
        import os
        work = self._make_pushable_repo(tmp_path)
        head_sha = "a" * 40
        auth = {
            "pr_number": 42,
            "head_sha": head_sha,
            "repo": "owner/repo",
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": _expected_instructions(42, head_sha, "owner/repo"),
        }
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps(auth))

        # Use an empty GH_CONFIG_DIR so gh is unauthenticated → exit 4
        # with NO stdout (only stderr, which the script captures). This
        # isolates the JSON-validity assertion to the early-exit path's
        # STEPS_JSON_PARTS construction. Without this, gh's 404 response
        # body would pollute stdout too.
        empty_gh_config = tmp_path / "empty_gh_config"
        empty_gh_config.mkdir()
        test_env = dict(os.environ)
        test_env["GH_CONFIG_DIR"] = str(empty_gh_config)
        test_env.pop("GH_TOKEN", None)
        test_env.pop("GH_AUTH_TOKEN", None)

        # Run from inside the working repo (no git push step anymore,
        # but the repo setup is still needed for the merge step's checkout).
        result = self._run_execute(
            "--input", str(auth_path), cwd=str(work), env=test_env,
        )

        # Extract the script's JSON output block from stdout.
        parsed = self._extract_last_json(result.stdout)
        assert "steps" in parsed, (
            f"missing 'steps' in output:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        steps = parsed["steps"]
        assert len(steps) == 1, (
            f"expected exactly 1 step (failed DELETE — no push step anymore), got "
            f"{len(steps)}: {steps}"
        )
        # The entry must be a well-formed dict with the 3 required keys.
        s = steps[0]
        assert isinstance(s, dict), f"step is not a dict: {s}"
        assert "instruction" in s, f"step missing 'instruction': {s}"
        assert "exit_code" in s, f"step missing 'exit_code': {s}"
        assert "stderr" in s, f"step missing 'stderr': {s}"
        # The DELETE enforce_admins step failed — this is what triggers
        # the early-exit path.
        assert s["exit_code"] != 0, (
            f"DELETE step should have failed (gh unauthenticated), got "
            f"rc={s['exit_code']}: {s}"
        )
        assert "DELETE" in s["instruction"]
        assert "enforce_admins" in s["instruction"]

    def test_single_quote_in_path_with_valid_content_proceeds(self, tmp_path):
        """A second, stronger check: a quote-containing path with a fully
        valid auth blob must pass the scalar extraction AND the
        vendor_instructions extraction (proving both python3 -c blocks
        handle the quoted path), reaching the gate / execution stage."""
        import json
        head_sha = "a" * 40
        auth = {
            "pr_number": 42,
            "head_sha": head_sha,
            "repo": "owner/repo",
            "witness_id": "w1",
            "audit_record_id": 1,
            "vendor_instructions": _expected_instructions(42, head_sha, "owner/repo"),
        }
        auth_path = tmp_path / "a'b'c.json"
        auth_path.write_text(json.dumps(auth))
        result = self._run_execute("--input", str(auth_path), timeout=30)
        # No parse refusal, no gate refusal — the quoted path was handled
        # cleanly through BOTH python3 -c extraction blocks. (The DELETE
        # step may REFUSE on its own due to unauthenticated gh in the test
        # env; that is a step failure, not a path-injection symptom.)
        assert "could not parse" not in result.stderr
        assert "expected exactly 4" not in result.stderr
        assert "not an exact match" not in result.stderr
        assert "executing 42@" in result.stderr
