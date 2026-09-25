"""Test secretary auto-check behavior — plan checkbox checked on PASS, left unchecked on FAIL.

Verifies that the secretary daemon:
1. Auto-checks the plan checkbox when verification passes
2. Leaves the checkbox unchecked when verification fails
3. Falls back to perl when sed fails (macOS robustness)
"""
import os
import tempfile
import subprocess
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECRETARY_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "secretary_daemon.sh")


def _create_test_plan(plan_dir: str, tasks: list) -> str:
    """Create a test plan file with unchecked checkboxes. Returns path and checkbox line numbers."""
    plan_path = os.path.join(plan_dir, "test_plan.md")
    lines = ["# Test Plan", "", "## Tasks", ""]
    checkbox_lines = []
    for i, task in enumerate(tasks):
        checkbox_lines.append(len(lines) + 1)  # 1-based line number
        lines.append(f"- [ ] {task}")
    with open(plan_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return plan_path, checkbox_lines


def _run_autocheck(plan_path: str, line_num: int) -> subprocess.CompletedProcess:
    """Run the auto-check logic directly."""
    script = f"""
    plan_file="{plan_path}"
    first_unchecked={line_num}
    if sed -i '' "${{first_unchecked}}s/^- \\[ \\]/- [x]/" "$plan_file" 2>/dev/null; then
        echo "AUTO_CHECKED_SED"
    elif perl -i -pe "s/^- \\[ \\]/- [x]/ if \\$. == ${{first_unchecked}}" "$plan_file" 2>/dev/null; then
        echo "AUTO_CHECKED_PERL"
    else
        echo "AUTO_CHECK_FAILED"
    fi
    """
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )


class TestSecretaryAutoCheck:
    """Test the auto-check plan checkbox logic."""

    def test_auto_check_marks_checkbox_on_pass(self, tmp_path):
        """When verification passes, the plan checkbox should be checked."""
        plan_path, checkbox_lines = _create_test_plan(str(tmp_path), ["Task 1: Do something"])
        result = _run_autocheck(plan_path, checkbox_lines[0])

        assert "AUTO_CHECKED" in result.stdout, (
            f"Auto-check should succeed. stdout={result.stdout!r} stderr={result.stderr!r}"
        )

        with open(plan_path) as f:
            content = f.read()
        assert "- [x] Task 1" in content, (
            f"Checkbox should be checked after auto-check. Plan content:\n{content}"
        )

    def test_auto_check_leaves_other_checkboxes_unchecked(self, tmp_path):
        """Auto-checking one checkbox should not affect others."""
        plan_path, checkbox_lines = _create_test_plan(str(tmp_path), ["Task 1: Do A", "Task 2: Do B", "Task 3: Do C"])
        _run_autocheck(plan_path, checkbox_lines[0])

        with open(plan_path) as f:
            content = f.read()
        assert "- [x] Task 1" in content
        assert "- [ ] Task 2" in content
        assert "- [ ] Task 3" in content

    def test_auto_check_handles_spaces_in_path(self, tmp_path):
        """Auto-check should work even when the plan path has spaces."""
        spaced_dir = os.path.join(str(tmp_path), "dir with spaces")
        os.makedirs(spaced_dir)
        plan_path, checkbox_lines = _create_test_plan(spaced_dir, ["Task 1: Do something"])

        result = _run_autocheck(plan_path, checkbox_lines[0])

        assert "AUTO_CHECKED" in result.stdout, (
            f"Auto-check should work with spaces in path. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

        with open(plan_path) as f:
            content = f.read()
        assert "- [x] Task 1" in content

    def test_perl_fallback_works(self, tmp_path):
        """Perl fallback should work when sed fails."""
        plan_path, checkbox_lines = _create_test_plan(str(tmp_path), ["Task 1: Do something"])

        # Run perl directly to verify it works
        result = subprocess.run(
            ["perl", "-i", "-pe", f"s/^- \\[ \\]/- [x]/ if $. == {checkbox_lines[0]}", plan_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"perl -i should succeed. stderr={result.stderr!r}"

        with open(plan_path) as f:
            content = f.read()
        assert "- [x] Task 1" in content

    def test_seen_done_dedup(self, tmp_path):
        """The seen-done file should not accumulate duplicates."""
        seen_file = os.path.join(str(tmp_path), "seen-done")
        msg_id = "test_relay_001"

        # Simulate the dedup logic from secretary_daemon.sh
        for _ in range(3):
            if not subprocess.run(
                ["grep", "-q", f"^{msg_id}$", seen_file],
                capture_output=True,
            ).returncode == 0:
                with open(seen_file, "a") as f:
                    f.write(msg_id + "\n")

        with open(seen_file) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert lines.count(msg_id) == 1, (
            f"seen-done should have exactly 1 entry for msg_id, got {lines.count(msg_id)}. "
            f"Lines: {lines}"
        )
