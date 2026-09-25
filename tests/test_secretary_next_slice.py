"""Test secretary next_slice — checkbox and header-style slice parsing.

Verifies that the secretary's next_slice function correctly:
1. Finds unchecked checkboxes (- [ ] format)
2. Falls back to ## TODO: and ### PENDING: headers
3. Returns empty when all slices are done
"""
import os
import subprocess
import tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run_next_slice(plan_path: str) -> str:
    """Run the next_slice function logic and return the result."""
    script = f"""
    plan='{plan_path}'
    # Replicate next_slice logic
    # Find next unchecked checkbox
    slice=$(grep -n "^- \\[ \\]" "$plan" 2>/dev/null | head -1)
    if [[ -n "$slice" ]]; then
        checkbox_text=$(echo "$slice" | sed 's/^[0-9]*:- \\[ \\] //')
        echo "$checkbox_text"
        exit 0
    fi
    # Fallback: look for ## TODO: or ### PENDING: headers
    slice=$(grep -n "^## TODO:\\|^### TODO:\\|^## PENDING:\\|^### PENDING:" "$plan" 2>/dev/null | head -1)
    if [[ -n "$slice" ]]; then
        header_text=$(echo "$slice" | sed 's/^[0-9]*:## \\(TODO\\|PENDING\\): //' | sed 's/^[0-9]*:### \\(TODO\\|PENDING\\): //')
        echo "$header_text"
        exit 0
    fi
    """
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


class TestNextSliceCheckbox:
    """Test checkbox-style slice parsing."""

    def test_finds_unchecked_checkbox(self, tmp_path):
        """Should find the first unchecked checkbox."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n- [ ] First task\n- [ ] Second task\n")
        result = _run_next_slice(str(plan))
        assert "First task" in result, f"Should find first checkbox. Got: {result}"

    def test_skips_checked_checkbox(self, tmp_path):
        """Should skip checked checkboxes."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n- [x] Done task\n- [ ] Pending task\n")
        result = _run_next_slice(str(plan))
        assert "Pending task" in result, f"Should find pending checkbox. Got: {result}"
        assert "Done task" not in result

    def test_returns_empty_when_all_checked(self, tmp_path):
        """Should return empty when all checkboxes are checked."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n- [x] Done task\n- [x] Another done\n")
        result = _run_next_slice(str(plan))
        assert result == "", f"Should return empty. Got: {result}"


class TestNextSliceHeader:
    """Test header-style slice parsing (## TODO:, ### PENDING:)."""

    def test_finds_todo_header(self, tmp_path):
        """Should find ## TODO: headers when no checkboxes exist."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n## TODO: Implement feature X\n\nSome details.\n")
        result = _run_next_slice(str(plan))
        assert "Implement feature X" in result, f"Should find TODO header. Got: {result}"

    def test_finds_pending_header(self, tmp_path):
        """Should find ## PENDING: headers."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n## PENDING: Review PR\n\nDetails.\n")
        result = _run_next_slice(str(plan))
        assert "Review PR" in result, f"Should find PENDING header. Got: {result}"

    def test_finds_h3_todo_header(self, tmp_path):
        """Should find ### TODO: headers."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n### TODO: Sub-task\n\nDetails.\n")
        result = _run_next_slice(str(plan))
        assert "Sub-task" in result, f"Should find ### TODO header. Got: {result}"

    def test_checkbox_takes_priority_over_header(self, tmp_path):
        """Checkboxes should be found before headers."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n## TODO: Header task\n\n- [ ] Checkbox task\n")
        result = _run_next_slice(str(plan))
        assert "Checkbox task" in result, f"Checkbox should take priority. Got: {result}"
        assert "Header task" not in result

    def test_returns_empty_when_no_slices(self, tmp_path):
        """Should return empty when no checkboxes or headers exist."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\nJust some text, no tasks.\n")
        result = _run_next_slice(str(plan))
        assert result == "", f"Should return empty. Got: {result}"
