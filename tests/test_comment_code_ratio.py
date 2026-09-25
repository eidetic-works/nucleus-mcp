"""Tests for comment-to-code ratio check (fw-1786154034).

Verifies that _comment_code_ratio_check flags files with a low code-to-
comment ratio — the signature of a script whose comments describe features
the code does not implement.
"""
import pytest
from pathlib import Path


class TestCommentCodeRatio:
    def test_flags_low_code_ratio_file(self, tmp_path):
        """A file with 4:1 comment-to-code ratio is flagged."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        f = tmp_path / "deploy.sh"
        f.write_text(
            "# This script does a local next build\n"
            "# It captures the exit code\n"
            "# It restarts the systemd unit\n"
            "# It supports --skip-build, --skip-smoke, --dry-run\n"
            "# It supports --host and --ssh-key\n"
            "SYSTEMD_UNIT=app.service\n"
            "# rsync the standalone build\n"
            "rsync -a build/ server:\n"
            "# smoke test the running process\n"
            "curl -s http://localhost:3000/health\n"
        )
        warnings = _comment_code_ratio_check(["deploy.sh"], tmp_path)
        assert len(warnings) == 1
        assert warnings[0]["file"] == "deploy.sh"
        assert warnings[0]["code_ratio"] < 0.40

    def test_no_warning_for_code_heavy_file(self, tmp_path):
        """A file with mostly code is not flagged."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        f = tmp_path / "module.py"
        f.write_text(
            "import os\n"
            "import sys\n"
            "# main entry point\n"
            "def main():\n"
            "    print('hello')\n"
            "    return 0\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main())\n"
        )
        warnings = _comment_code_ratio_check(["module.py"], tmp_path)
        assert warnings == []

    def test_ignores_non_script_files(self, tmp_path):
        """Non-script files (.md, .json) are not checked."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        f = tmp_path / "README.md"
        f.write_text("# Title\n# More comments\n# Even more\n# And more\n")
        warnings = _comment_code_ratio_check(["README.md"], tmp_path)
        assert warnings == []

    def test_empty_file_not_flagged(self, tmp_path):
        """An empty file produces no warning."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        f = tmp_path / "empty.py"
        f.write_text("")
        warnings = _comment_code_ratio_check(["empty.py"], tmp_path)
        assert warnings == []

    def test_blank_lines_not_counted(self, tmp_path):
        """Blank lines are excluded from the total."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        f = tmp_path / "script.sh"
        f.write_text(
            "# comment 1\n"
            "# comment 2\n"
            "# comment 3\n"
            "# comment 4\n"
            "\n"
            "\n"
            "echo hello\n"
            "echo world\n"
        )
        warnings = _comment_code_ratio_check(["script.sh"], tmp_path)
        # 2 code / 6 total = 0.33 < 0.40 → flagged
        assert len(warnings) == 1
        assert warnings[0]["code_lines"] == 2
        assert warnings[0]["total_lines"] == 6

    def test_multiple_files_flagged(self, tmp_path):
        """Multiple low-ratio files are all flagged."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        for name in ["a.sh", "b.py"]:
            (tmp_path / name).write_text(
                "# c1\n# c2\n# c3\n# c4\ncode\n"
            )
        warnings = _comment_code_ratio_check(["a.sh", "b.py"], tmp_path)
        assert len(warnings) == 2
        flagged = {w["file"] for w in warnings}
        assert flagged == {"a.sh", "b.py"}

    def test_missing_file_skipped(self, tmp_path):
        """A non-existent file is silently skipped."""
        from mcp_server_nucleus.runtime.build_runner import _comment_code_ratio_check
        warnings = _comment_code_ratio_check(["nonexistent.py"], tmp_path)
        assert warnings == []
