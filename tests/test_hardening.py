"""
Exhaustive Test Suite for Nucleus-MCP Hardening Modules
========================================================
Tests for security, concurrency, and reliability fixes identified
in the Feb 24, 2026 Design Thinking Analysis.

Coverage Targets:
- C20: Path traversal (CRITICAL)
- C25: JSONL concurrent write (CRITICAL)
- C30: UTF-8 encoding
- C18: Timeout bounds
- C33: Info leakage

Environment Matrix:
- macOS (Windsurf, Claude Desktop, Perplexity)
- Windows (Antigravity, Windsurf)
- Linux (CI/CD)
"""

import os
import sys
import json
import tempfile
import threading
import time
from pathlib import Path
from typing import List
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.path_sanitizer import (
    sanitize_path,
    sanitize_filename,
    safe_join,
    is_safe_path,
    PathTraversalError,
    InvalidPathError,
)
from mcp_server_nucleus.runtime.file_lock import (
    file_lock,
    atomic_write_json,
    atomic_append_jsonl,
    safe_read_jsonl,
    safe_read_json,
    repair_jsonl,
    LockError,
    AtomicWriteError,
)
from mcp_server_nucleus.runtime.error_sanitizer import (
    sanitize_error,
    SanitizedError,
    safe_error_handler,
    format_safe_response,
)
from mcp_server_nucleus.runtime.timeout_handler import (
    with_timeout,
    run_with_timeout,
    TimeoutError as NucleusTimeoutError,
)


# ============================================================================
# C20: PATH TRAVERSAL TESTS (CRITICAL SECURITY)
# ============================================================================

class TestPathSanitizer:
    """Test suite for path traversal prevention."""
    
    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir) / "brain"
        self.base_dir.mkdir()
    
    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # --- Basic Path Traversal Attacks ---
    
    def test_simple_traversal_blocked(self):
        """Block simple ../ traversal."""
        with pytest.raises(PathTraversalError):
            sanitize_path("../../../etc/passwd", self.base_dir)
    
    def test_double_dot_in_middle(self):
        """Block ../ in middle of path."""
        with pytest.raises(PathTraversalError):
            sanitize_path("tasks/../../../etc/passwd", self.base_dir)
    
    def test_backslash_traversal(self):
        """Block Windows-style backslash traversal."""
        with pytest.raises(PathTraversalError):
            sanitize_path("..\\..\\..\\windows\\system32", self.base_dir)
    
    def test_url_encoded_traversal(self):
        """Block URL-encoded traversal attempts."""
        with pytest.raises(PathTraversalError):
            sanitize_path("%2e%2e/%2e%2e/etc/passwd", self.base_dir)
    
    def test_null_byte_injection(self):
        """Block null byte injection."""
        with pytest.raises(PathTraversalError):
            sanitize_path("valid\x00/../../../etc/passwd", self.base_dir)
    
    def test_absolute_path_blocked(self):
        """Block absolute paths."""
        with pytest.raises(PathTraversalError):
            sanitize_path("/etc/passwd", self.base_dir)
    
    def test_windows_absolute_path(self):
        """Block Windows absolute paths."""
        with pytest.raises(PathTraversalError):
            sanitize_path("C:\\Windows\\System32", self.base_dir)
    
    def test_unc_path_blocked(self):
        """Block UNC paths."""
        with pytest.raises(PathTraversalError):
            sanitize_path("\\\\server\\share\\file", self.base_dir)
    
    # --- Valid Paths ---
    
    def test_simple_filename_allowed(self):
        """Allow simple filenames."""
        result = sanitize_path("task_123", self.base_dir)
        # Resolve paths to handle macOS /var -> /private/var symlink
        assert result.parent.resolve() == self.base_dir.resolve()
        assert result.name == "task_123"
    
    def test_alphanumeric_with_underscore(self):
        """Allow alphanumeric with underscores."""
        result = sanitize_path("my_task_2024_01_15", self.base_dir)
        assert is_safe_path(result, self.base_dir)
    
    def test_subdirectory_allowed(self):
        """Allow subdirectories when enabled."""
        result = sanitize_path("tasks/subtask", self.base_dir, allow_subdirs=True)
        assert is_safe_path(result, self.base_dir)
    
    # --- Edge Cases ---
    
    def test_empty_path_rejected(self):
        """Reject empty paths."""
        with pytest.raises(InvalidPathError):
            sanitize_path("", self.base_dir)
    
    def test_whitespace_only_rejected(self):
        """Reject whitespace-only paths."""
        with pytest.raises(InvalidPathError):
            sanitize_path("   ", self.base_dir)
    
    def test_special_chars_sanitized(self):
        """Sanitize special characters."""
        result = sanitize_filename("task<>:\"|?*name")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
    
    def test_unicode_filename(self):
        """Handle Unicode filenames."""
        result = sanitize_filename("任务_タスク_задача")
        assert len(result) > 0
    
    def test_very_long_filename_truncated(self):
        """Truncate very long filenames."""
        long_name = "a" * 500
        result = sanitize_filename(long_name)
        assert len(result) <= 200


# ============================================================================
# C25: CONCURRENT WRITE TESTS (CRITICAL DATA INTEGRITY)
# ============================================================================

class TestFileLocking:
    """Test suite for concurrent file access safety."""
    
    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_atomic_write_creates_file(self):
        """Atomic write creates file correctly."""
        path = Path(self.temp_dir) / "test.json"
        data = {"key": "value", "number": 42}
        
        atomic_write_json(path, data)
        
        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data
    
    def test_atomic_write_overwrites(self):
        """Atomic write overwrites existing file."""
        path = Path(self.temp_dir) / "test.json"
        
        atomic_write_json(path, {"old": "data"})
        atomic_write_json(path, {"new": "data"})
        
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {"new": "data"}
    
    def test_jsonl_append_creates_file(self):
        """JSONL append creates file if not exists."""
        path = Path(self.temp_dir) / "test.jsonl"
        
        atomic_append_jsonl(path, {"record": 1})
        
        assert path.exists()
        records = safe_read_jsonl(path)
        assert len(records) == 1
        assert records[0] == {"record": 1}
    
    def test_jsonl_append_multiple(self):
        """Multiple JSONL appends work correctly."""
        path = Path(self.temp_dir) / "test.jsonl"
        
        for i in range(5):
            atomic_append_jsonl(path, {"record": i})
        
        records = safe_read_jsonl(path)
        assert len(records) == 5
        assert [r["record"] for r in records] == [0, 1, 2, 3, 4]
    
    def test_concurrent_appends_no_corruption(self):
        """Concurrent appends don't corrupt data."""
        path = Path(self.temp_dir) / "concurrent.jsonl"
        num_threads = 10
        records_per_thread = 20
        errors: List[Exception] = []
        
        def append_records(thread_id: int):
            try:
                for i in range(records_per_thread):
                    atomic_append_jsonl(path, {"thread": thread_id, "seq": i})
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=append_records, args=(i,))
            for i in range(num_threads)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors during concurrent write: {errors}"
        
        records = safe_read_jsonl(path)
        assert len(records) == num_threads * records_per_thread
    
    def test_corrupted_jsonl_recovery(self):
        """Recover from corrupted JSONL."""
        path = Path(self.temp_dir) / "corrupted.jsonl"
        
        # Write some valid records
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"valid": 1}\n')
            f.write('{"valid": 2}\n')
            f.write('not valid json\n')  # Corrupted line
            f.write('{"valid": 3}\n')
        
        result = repair_jsonl(path)
        
        assert result["repaired"] == True
        assert result["valid_records"] == 3
        assert 3 in result["corrupted_lines"]
    
    def test_safe_read_skips_corrupted(self):
        """Safe read skips corrupted lines."""
        path = Path(self.temp_dir) / "partial_corrupt.jsonl"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"ok": 1}\n')
            f.write('bad line\n')
            f.write('{"ok": 2}\n')
        
        records = safe_read_jsonl(path)
        assert len(records) == 2


# ============================================================================
# C30: UTF-8 ENCODING TESTS
# ============================================================================

class TestEncoding:
    """Test suite for UTF-8 encoding handling."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_unicode_json_write_read(self):
        """Write and read Unicode data correctly."""
        path = Path(self.temp_dir) / "unicode.json"
        data = {
            "chinese": "中文测试",
            "japanese": "日本語テスト",
            "russian": "Русский тест",
            "emoji": "🧠💡🚀",
            "arabic": "اختبار عربي",
        }
        
        atomic_write_json(path, data)
        loaded = safe_read_json(path)
        
        assert loaded == data
    
    def test_unicode_jsonl_append(self):
        """Append Unicode records to JSONL."""
        path = Path(self.temp_dir) / "unicode.jsonl"
        
        atomic_append_jsonl(path, {"text": "Hello 世界"})
        atomic_append_jsonl(path, {"text": "Привет мир"})
        
        records = safe_read_jsonl(path)
        assert records[0]["text"] == "Hello 世界"
        assert records[1]["text"] == "Привет мир"
    
    def test_bom_handling(self):
        """Handle BOM in JSON files."""
        path = Path(self.temp_dir) / "bom.json"
        
        # Write with BOM
        with open(path, "wb") as f:
            f.write(b'\xef\xbb\xbf{"key": "value"}')
        
        # safe_read_json should handle BOM
        data = safe_read_json(path)
        assert data == {"key": "value"}


# ============================================================================
# C18: TIMEOUT TESTS
# ============================================================================

class TestTimeout:
    """Test suite for timeout handling."""
    
    def test_fast_function_completes(self):
        """Fast function completes within timeout."""
        @with_timeout(5.0)
        def fast_func():
            return "done"
        
        result = fast_func()
        assert result == "done"
    
    def test_slow_function_times_out(self):
        """Slow function raises timeout."""
        @with_timeout(0.5)
        def slow_func():
            time.sleep(2)
            return "done"
        
        with pytest.raises(NucleusTimeoutError):
            slow_func()
    
    def test_run_with_timeout_default(self):
        """run_with_timeout returns default on timeout."""
        def slow_func():
            time.sleep(2)
            return "done"
        
        result = run_with_timeout(slow_func, timeout=0.5, default="timed_out")
        assert result == "timed_out"
    
    def test_timeout_preserves_exception(self):
        """Timeout preserves raised exceptions."""
        @with_timeout(5.0)
        def error_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError, match="test error"):
            error_func()


# ============================================================================
# C33: ERROR SANITIZATION TESTS
# ============================================================================

class TestErrorSanitization:
    """Test suite for error message sanitization."""
    
    def test_path_not_in_sanitized_error(self):
        """Filesystem paths not leaked in errors."""
        try:
            raise FileNotFoundError("/Users/secret/path/file.txt")
        except Exception as e:
            sanitized = sanitize_error(e, "file_not_found")
        
        assert "/Users" not in sanitized
        assert "secret" not in sanitized
        assert "file.txt" not in sanitized
    
    def test_sanitized_error_has_id(self):
        """Sanitized errors have tracking IDs."""
        try:
            raise Exception("internal details")
        except Exception as e:
            sanitized = sanitize_error(e, "internal_error")
        
        assert "Error ID:" in sanitized or len(sanitized.split()) < 20
    
    def test_safe_error_handler_decorator(self):
        """safe_error_handler decorator works."""
        @safe_error_handler("file_not_found")
        def read_file(path):
            raise FileNotFoundError(f"Cannot find {path}")
        
        with pytest.raises(SanitizedError) as exc_info:
            read_file("/secret/path")
        
        assert "/secret" not in str(exc_info.value)
    
    def test_format_safe_response_success(self):
        """Format success response correctly."""
        response = format_safe_response(True, data={"result": "ok"})
        
        assert response["success"] == True
        assert response["data"] == {"result": "ok"}
    
    def test_format_safe_response_error(self):
        """Format error response without sensitive info."""
        response = format_safe_response(
            False,
            error="An error occurred",
            error_id="abc123"
        )
        
        assert response["success"] == False
        assert "abc123" in response.get("error_id", "")


# ============================================================================
# CROSS-PLATFORM EDGE CASES
# ============================================================================

class TestCrossPlatform:
    """Test suite for cross-platform compatibility."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_with_spaces(self):
        """Handle paths with spaces."""
        base = Path(self.temp_dir) / "path with spaces"
        base.mkdir()
        
        result = sanitize_path("file name", base)
        assert is_safe_path(result, base)
    
    def test_very_long_path(self):
        """Handle very long paths gracefully."""
        # Create nested directories approaching path limit
        deep_path = Path(self.temp_dir)
        for i in range(10):
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True, exist_ok=True)
        
        result = sanitize_path("file", deep_path)
        assert is_safe_path(result, deep_path)
    
    def test_mixed_line_endings(self):
        """Handle mixed line endings in JSONL."""
        path = Path(self.temp_dir) / "mixed.jsonl"
        
        with open(path, "wb") as f:
            f.write(b'{"a": 1}\r\n')  # Windows
            f.write(b'{"b": 2}\n')    # Unix
            f.write(b'{"c": 3}\r')    # Old Mac
        
        records = safe_read_jsonl(path)
        assert len(records) >= 2  # Should handle gracefully


# ============================================================================
# GOLDMAN SACHS / ENTERPRISE READINESS TESTS
# ============================================================================

class TestEnterpriseReadiness:
    """Tests for enterprise-grade requirements."""
    
    def test_no_path_leakage_on_any_error(self):
        """Verify no path leakage across all error scenarios."""
        test_cases = [
            FileNotFoundError("/secret/internal/path.txt"),
            PermissionError("/root/sensitive/file"),
            OSError("Cannot access /etc/shadow"),
        ]
        
        for error in test_cases:
            sanitized = sanitize_error(error, "internal_error")
            assert "/secret" not in sanitized
            assert "/root" not in sanitized
            assert "/etc" not in sanitized
    
    def test_concurrent_operations_safe(self):
        """Verify no data loss under concurrent load."""
        # This is the Goldman Sachs test - if we lose even one record
        # under concurrent load, we fail
        temp_dir = tempfile.mkdtemp()
        path = Path(temp_dir) / "stress_test.jsonl"
        
        num_threads = 20
        records_per_thread = 100
        expected_total = num_threads * records_per_thread
        
        def write_records(thread_id):
            for i in range(records_per_thread):
                atomic_append_jsonl(path, {
                    "thread": thread_id,
                    "seq": i,
                    "timestamp": time.time()
                })
        
        threads = [
            threading.Thread(target=write_records, args=(i,))
            for i in range(num_threads)
        ]
        
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start
        
        records = safe_read_jsonl(path)
        
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # MUST have all records - zero data loss
        assert len(records) == expected_total, \
            f"DATA LOSS: Expected {expected_total}, got {len(records)}"
        
        print(f"✅ Wrote {expected_total} records in {elapsed:.2f}s with zero data loss")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
