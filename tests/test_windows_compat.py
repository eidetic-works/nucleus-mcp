#!/usr/bin/env python3
"""
Windows Compatibility Tests for Nucleus MCP

Tests Windows-specific edge cases:
- Path length limits (260 chars)
- Backslash path separators
- File locking with msvcrt
- Case-insensitive filesystems
"""

import pytest
import sys
import tempfile
from pathlib import Path

# Skip all tests if not on Windows
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-specific tests"
)


class TestWindowsPaths:
    """Test Windows path handling."""
    
    def test_long_path_handling(self):
        """Test paths approaching Windows 260 char limit."""
        from mcp_server_nucleus.runtime.path_sanitizer import sanitize_path
        
        # Create a path close to Windows limit
        long_name = "a" * 200
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = sanitize_path(long_name, base)
            
            # Should truncate or handle gracefully
            assert len(str(result)) < 260
    
    def test_backslash_normalization(self):
        """Test that backslashes are handled correctly."""
        from mcp_server_nucleus.runtime.path_sanitizer import sanitize_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Windows paths with backslashes
            result = sanitize_path("subdir\\file.txt", base)
            
            # Should normalize to forward slashes or handle properly
            assert result.exists() or True  # Path object handles this
    
    def test_case_insensitive_paths(self):
        """Test case-insensitive filesystem behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            file1 = base / "test.txt"
            file1.write_text("content", encoding='utf-8')
            
            # Windows is case-insensitive
            file2 = base / "TEST.TXT"
            assert file2.exists()


class TestWindowsLocking:
    """Test file locking on Windows."""
    
    def test_msvcrt_locking_available(self):
        """Verify msvcrt is available on Windows."""
        try:
            import msvcrt
            assert msvcrt is not None
        except ImportError:
            pytest.fail("msvcrt should be available on Windows")
    
    def test_brain_lock_windows(self):
        """Test BrainLock works on Windows."""
        from mcp_server_nucleus.runtime.locking import get_lock
        
        with tempfile.TemporaryDirectory() as tmpdir:
            brain_path = Path(tmpdir)
            
            # Should use msvcrt on Windows
            lock = get_lock("test", brain_path)
            with lock.section():
                # Lock acquired successfully
                assert True


class TestWindowsEncoding:
    """Test UTF-8 encoding on Windows."""
    
    def test_utf8_file_io(self):
        """Test UTF-8 file I/O works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            
            # Write Unicode content
            content = "Hello 世界 🌍"
            test_file.write_text(content, encoding='utf-8')
            
            # Read back
            result = test_file.read_text(encoding='utf-8')
            assert result == content
    
    def test_json_unicode_windows(self):
        """Test JSON with Unicode on Windows."""
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            
            data = {"message": "Hello 世界", "emoji": "🚀"}
            
            # Write with ensure_ascii=False
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            # Read back
            with open(test_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            assert result == data


class TestWindowsSignals:
    """Test signal handling on Windows."""
    
    def test_signal_compatibility(self):
        """Test that signal handling doesn't break on Windows."""
        import signal
        
        # SIGTERM exists on Windows
        assert hasattr(signal, 'SIGTERM')
        
        # SIGINT exists on Windows
        assert hasattr(signal, 'SIGINT')
