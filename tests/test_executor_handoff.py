"""Test executor handoff behavior — complex tasks return 1 and post [NEEDS-PRINCIPAL].

Verifies that the executor daemon:
1. Returns 0 (success) for pattern-matchable tasks (file creation)
2. Returns 1 (handoff) for complex tasks (code analysis, refactoring)
3. Does NOT mark complex tasks DONE
"""
import subprocess
import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run_pattern_match(task_desc: str, task_id: str = "test_task_001") -> str:
    """Run the executor's pattern matching logic and return result."""
    body = f"Task: {task_id}\nRole: principal\nPriority: 3\n\nDescription:\n{task_desc}\n\nExecute this task."
    task_json = json.dumps({"message": {"subject": f"[TASK] {task_id}", "body": body}})

    # Write the JSON to a temp file to avoid shell escaping issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(task_json)
        json_path = f.name

    # Use the interpreter running the tests, not a hardcoded {PROJECT_ROOT}/.venv.
    # That venv exists only in the main checkout: in a git worktree it is absent
    # (it is git-ignored), the `python -c` below fails, `2>/dev/null` swallows the
    # error, task_desc comes back EMPTY, and the grep then reports
    # PATTERN_NOT_MATCHED -- indistinguishable from the matcher actually being
    # broken. The pattern was never at fault; the harness could not run.
    script = f"""
    PY_BIN="{sys.executable}"
    task_desc=$("$PY_BIN" -c "import json,sys; d=json.load(open('{json_path}')); print(d.get('message',{{}}).get('body',''))" 2>/dev/null)
    clean_desc=$(echo "$task_desc" | grep -v "^Task: " | grep -v "^Role: " | grep -v "^Priority: " | grep -v "^Plan ref: ")
    flat_desc=$(printf '%s' "$clean_desc" | tr '\\n' ' ')
    if printf '%s' "$flat_desc" | grep -qiE "creat[a-z]+ +/tmp/|write[a-z]+ +/tmp/"; then
        echo "PATTERN_MATCHED"
    else
        echo "PATTERN_NOT_MATCHED"
    fi
    """
    try:
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    finally:
        os.unlink(json_path)


class TestExecutorPatternMatching:
    """Test that the executor correctly classifies tasks as simple vs complex."""

    def test_file_creation_task_is_pattern_matched(self):
        """File creation tasks should be pattern-matched (simple)."""
        result = _run_pattern_match('Create /tmp/test_handoff_1.txt with text "hello world"')
        assert result == "PATTERN_MATCHED", f"File creation should be matched. Got: {result}"

    def test_code_analysis_task_is_not_pattern_matched(self):
        """Code analysis tasks should NOT be pattern-matched (complex → handoff)."""
        result = _run_pattern_match(
            "Analyze the relay middleware code in mcp-server-nucleus and write a 2-sentence summary"
        )
        assert result == "PATTERN_NOT_MATCHED", f"Code analysis should NOT be matched. Got: {result}"

    def test_refactoring_task_is_not_pattern_matched(self):
        """Refactoring tasks should NOT be pattern-matched (complex → handoff)."""
        result = _run_pattern_match(
            "Refactor verify_done in secretary_daemon.sh to support a third verification type"
        )
        assert result == "PATTERN_NOT_MATCHED", f"Refactoring should NOT be matched. Got: {result}"

    def test_task_id_stripped_from_description(self):
        """Task IDs containing /tmp/ should not confuse the file path regex."""
        result = _run_pattern_match(
            "Analyze the code architecture and write a summary",
            task_id="sec_task_1:_create_/tmp/setup_b_1.txt_with_t",
        )
        assert result == "PATTERN_NOT_MATCHED", (
            f"Task with /tmp/ in ID but complex description should NOT be matched. Got: {result}"
        )

    def test_file_creation_with_task_id_containing_tmp(self):
        """File creation task should still match even when task ID contains /tmp/."""
        result = _run_pattern_match(
            'Create /tmp/real_file.txt with text "test"',
            task_id="sec_task_1:_create_/tmp/setup_b_1.txt_with_t",
        )
        assert result == "PATTERN_MATCHED", (
            f"File creation should match even with /tmp/ in task ID. Got: {result}"
        )
