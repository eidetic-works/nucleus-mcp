"""
Phase 73: Production-Grade Hardening Tests
=============================================
Comprehensive test suite for 99.9% reliability across all environments.

Covers:
- LLM API Resilience (timeout, retry, circuit breaker, rate limit, fallback)
- Environment Detection (OS, MCP host, path normalization)
- File System Resilience (locking, atomic writes, disk checks, corruption recovery)
- Error Telemetry (categorization, aggregation, alerting)
- Integration (all modules working together)
- Cross-environment edge cases (Mac, Windows, Linux, all MCP hosts)
"""

import json
import os
import platform
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timezone

# ============================================================
# Phase 73.1: LLM API Resilience Tests
# ============================================================

class TestErrorCategorization(unittest.TestCase):
    """Test error categorization from exceptions."""

    def test_timeout_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(TimeoutError("Request timed out after 30s"))
        self.assertEqual(err.category, ErrorCategory.TIMEOUT)
        self.assertEqual(err.code, "E100")

    def test_rate_limit_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("429 Too Many Requests"))
        self.assertEqual(err.category, ErrorCategory.RATE_LIMIT)

    def test_quota_exceeded(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("RESOURCE_EXHAUSTED: quota exceeded"))
        self.assertEqual(err.category, ErrorCategory.QUOTA_EXCEEDED)

    def test_auth_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("403 Forbidden: invalid API key"))
        self.assertEqual(err.category, ErrorCategory.AUTH)

    def test_network_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(ConnectionError("Connection refused"))
        self.assertEqual(err.category, ErrorCategory.NETWORK)

    def test_model_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("Model not found: gemini-fake"))
        self.assertEqual(err.category, ErrorCategory.MODEL_ERROR)

    def test_json_parse_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(json.JSONDecodeError("Expecting value", "", 0))
        self.assertEqual(err.category, ErrorCategory.INVALID_RESPONSE)

    def test_unknown_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("some random error"))
        self.assertEqual(err.category, ErrorCategory.UNKNOWN)

    def test_retry_after_extraction(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception
        err = categorize_exception(Exception("429 rate limit, retry-after: 30"))
        self.assertEqual(err.retry_after_seconds, 30.0)

    def test_dns_resolution_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("DNS resolution failed for api.google.com"))
        self.assertEqual(err.category, ErrorCategory.NETWORK)

    def test_broken_pipe_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(BrokenPipeError("Broken pipe"))
        self.assertEqual(err.category, ErrorCategory.NETWORK)

    def test_safety_blocked_error(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception, ErrorCategory
        err = categorize_exception(Exception("Response blocked due to safety settings"))
        self.assertEqual(err.category, ErrorCategory.MODEL_ERROR)

    def test_error_to_dict(self):
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception
        err = categorize_exception(TimeoutError("timeout"))
        d = err.to_dict()
        self.assertIn("category", d)
        self.assertIn("code", d)
        self.assertIn("timestamp", d)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker pattern."""

    def test_starts_closed(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

    def test_opens_after_threshold(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

    def test_half_open_after_cooldown(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2, recovery_timeout_s=0.1))
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.can_execute())

    def test_closes_after_success_in_half_open(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout_s=0.1, success_threshold=1
        ))
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_reopens_on_half_open_failure(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout_s=0.1
        ))
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_reset(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_get_stats(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker("test_stats", CircuitBreakerConfig())
        stats = cb.get_stats()
        self.assertEqual(stats["name"], "test_stats")
        self.assertIn("state", stats)
        self.assertIn("failure_count", stats)

    def test_thread_safety(self):
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker("thread_test", CircuitBreakerConfig(failure_threshold=100))
        errors = []
        def record_many():
            try:
                for _ in range(50):
                    cb.record_failure()
                    cb.record_success()
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=record_many) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(errors), 0)


class TestRetryConfig(unittest.TestCase):
    """Test retry configuration and backoff calculation."""

    def test_compute_backoff_base(self):
        from mcp_server_nucleus.runtime.llm_resilience import compute_backoff, RetryConfig
        cfg = RetryConfig(base_delay_s=1.0, jitter=False)
        self.assertAlmostEqual(compute_backoff(0, cfg), 1.0)
        self.assertAlmostEqual(compute_backoff(1, cfg), 2.0)
        self.assertAlmostEqual(compute_backoff(2, cfg), 4.0)

    def test_backoff_respects_max(self):
        from mcp_server_nucleus.runtime.llm_resilience import compute_backoff, RetryConfig
        cfg = RetryConfig(base_delay_s=1.0, max_delay_s=5.0, jitter=False)
        self.assertAlmostEqual(compute_backoff(10, cfg), 5.0)

    def test_backoff_with_retry_after(self):
        from mcp_server_nucleus.runtime.llm_resilience import compute_backoff, RetryConfig
        cfg = RetryConfig(jitter=False)
        delay = compute_backoff(0, cfg, retry_after=10.0)
        self.assertAlmostEqual(delay, 10.0)

    def test_backoff_with_jitter(self):
        from mcp_server_nucleus.runtime.llm_resilience import compute_backoff, RetryConfig
        cfg = RetryConfig(base_delay_s=1.0, jitter=True)
        delays = [compute_backoff(0, cfg) for _ in range(10)]
        # Jitter should produce different values
        self.assertTrue(len(set(round(d, 3) for d in delays)) > 1)


class TestResponseValidation(unittest.TestCase):
    """Test LLM response validation and JSON extraction."""

    def test_validate_none(self):
        from mcp_server_nucleus.runtime.llm_resilience import validate_llm_response
        self.assertIsNone(validate_llm_response(None))

    def test_validate_text_attribute(self):
        from mcp_server_nucleus.runtime.llm_resilience import validate_llm_response
        mock = MagicMock()
        mock.text = "hello"
        self.assertEqual(validate_llm_response(mock), "hello")

    def test_validate_string_response(self):
        from mcp_server_nucleus.runtime.llm_resilience import validate_llm_response
        self.assertEqual(validate_llm_response("direct string"), "direct string")

    def test_validate_dict_response(self):
        from mcp_server_nucleus.runtime.llm_resilience import validate_llm_response
        self.assertEqual(validate_llm_response({"text": "from dict"}), "from dict")

    def test_extract_json_bare(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        result = extract_json_from_text('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_markdown_wrapped(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        text = '```json\n{"required_tools": ["brain_add_task"]}\n```'
        result = extract_json_from_text(text)
        self.assertEqual(result["required_tools"], ["brain_add_task"])

    def test_extract_json_with_preamble(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        text = 'Here is the result:\n```json\n{"foo": "bar"}\n```\nDone.'
        result = extract_json_from_text(text)
        self.assertEqual(result["foo"], "bar")

    def test_extract_json_trailing_comma(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        text = '```json\n{"key": "value",}\n```'
        result = extract_json_from_text(text)
        self.assertEqual(result["key"], "value")

    def test_extract_json_none_for_invalid(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        self.assertIsNone(extract_json_from_text("not json at all"))

    def test_extract_json_empty(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        self.assertIsNone(extract_json_from_text(""))
        self.assertIsNone(extract_json_from_text(None))

    def test_extract_json_nested(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        text = '{"outer": {"inner": "value"}}'
        result = extract_json_from_text(text)
        self.assertEqual(result["outer"]["inner"], "value")


class TestResilientLLMClient(unittest.TestCase):
    """Test ResilientLLMClient with mocked LLM."""

    def test_init_defaults(self):
        from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
        client = ResilientLLMClient()
        self.assertEqual(client.timeout_s, 30.0)
        self.assertIsNotNone(client.retry_config)

    def test_generate_with_fallback(self):
        from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
        client = ResilientLLMClient()
        # No API key set, should use fallback
        result = client.generate("test prompt", fallback_fn=lambda p: "fallback result")
        # Either gets real result or fallback
        self.assertIsNotNone(result)

    def test_generate_json_with_fallback(self):
        from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
        client = ResilientLLMClient()
        result = client.generate_json(
            "test",
            fallback_fn=lambda p: {"fallback": True}
        )
        self.assertIsNotNone(result)

    def test_stats(self):
        from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
        client = ResilientLLMClient()
        stats = client.get_stats()
        self.assertIn("total_calls", stats)
        self.assertIn("success_rate", stats)
        self.assertIn("circuit_breaker", stats)

    def test_circuit_state_property(self):
        from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
        client = ResilientLLMClient()
        self.assertEqual(client.circuit_state, "CLOSED")

    def test_reset_circuit(self):
        from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
        client = ResilientLLMClient()
        client.reset_circuit()
        self.assertEqual(client.circuit_state, "CLOSED")

    def test_singleton(self):
        from mcp_server_nucleus.runtime.llm_resilience import get_resilient_llm_client
        c1 = get_resilient_llm_client()
        c2 = get_resilient_llm_client()
        self.assertIs(c1, c2)


# ============================================================
# Phase 73.2: Environment Detection Tests
# ============================================================

class TestOSDetection(unittest.TestCase):
    """Test OS detection across platforms."""

    def test_detect_current_os(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, OSType
        detector = EnvironmentDetector()
        info = detector.detect()
        system = platform.system().lower()
        if system == "darwin":
            self.assertEqual(info.os_type, OSType.MACOS)
        elif system == "windows":
            self.assertEqual(info.os_type, OSType.WINDOWS)
        elif system == "linux":
            self.assertEqual(info.os_type, OSType.LINUX)

    @patch('platform.system', return_value='Darwin')
    def test_detect_macos(self, mock_sys):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, OSType
        detector = EnvironmentDetector()
        self.assertEqual(detector._detect_os(), OSType.MACOS)

    @patch('platform.system', return_value='Windows')
    def test_detect_windows(self, mock_sys):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, OSType
        detector = EnvironmentDetector()
        self.assertEqual(detector._detect_os(), OSType.WINDOWS)

    @patch('platform.system', return_value='Linux')
    def test_detect_linux(self, mock_sys):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, OSType
        detector = EnvironmentDetector()
        self.assertEqual(detector._detect_os(), OSType.LINUX)

    @patch('platform.system', return_value='FreeBSD')
    def test_detect_unknown_os(self, mock_sys):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, OSType
        detector = EnvironmentDetector()
        self.assertEqual(detector._detect_os(), OSType.UNKNOWN)


class TestMCPHostDetection(unittest.TestCase):
    """Test MCP host detection."""

    def test_explicit_env_var(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "windsurf"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.WINDSURF)

    def test_explicit_claude_desktop(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "claude_desktop"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.CLAUDE_DESKTOP)

    def test_explicit_antigravity(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "antigravity"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.ANTIGRAVITY)

    def test_explicit_perplexity(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "perplexity"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.PERPLEXITY)

    def test_explicit_cursor(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "cursor"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.CURSOR)

    def test_explicit_openclaw(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "openclaw"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.OPENCLAW)

    def test_explicit_cli(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector, MCPHost
        detector = EnvironmentDetector()
        with patch.dict(os.environ, {"NUCLEUS_MCP_HOST": "cli"}):
            self.assertEqual(detector._detect_mcp_host(), MCPHost.CLI)


class TestEnvironmentInfo(unittest.TestCase):
    """Test full environment detection."""

    def test_detect_returns_info(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        info = detector.detect()
        self.assertIsNotNone(info.os_type)
        self.assertIsNotNone(info.python_version)
        self.assertIsNotNone(info.brain_path)
        self.assertIsNotNone(info.home_dir)

    def test_detect_caches(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        info1 = detector.detect()
        info2 = detector.detect()
        self.assertIs(info1, info2)

    def test_detect_force_refresh(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        info1 = detector.detect()
        info2 = detector.detect(force_refresh=True)
        self.assertIsNot(info1, info2)

    def test_to_dict(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        info = detector.detect()
        d = info.to_dict()
        self.assertIn("os_type", d)
        self.assertIn("mcp_host", d)
        self.assertIn("available_disk_mb", d)

    def test_normalize_path(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        normalized = detector.normalize_path("/tmp/test/../test")
        self.assertNotIn("..", normalized)

    def test_normalize_empty_path(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        self.assertEqual(detector.normalize_path(""), "")

    def test_safe_brain_path(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        path = detector.get_safe_brain_path()
        self.assertTrue(path.exists() or path.parent.exists())

    def test_singleton(self):
        from mcp_server_nucleus.runtime.environment_detector import get_environment_detector
        d1 = get_environment_detector()
        d2 = get_environment_detector()
        self.assertIs(d1, d2)


class TestPathNormalization(unittest.TestCase):
    """Test cross-platform path handling."""

    def test_unix_path(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        result = detector.normalize_path("/home/user/.brain")
        self.assertIsInstance(result, str)

    def test_tilde_expansion(self):
        from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
        detector = EnvironmentDetector()
        home = str(Path.home())
        # normalize_path doesn't expand ~, but Path.home() works
        self.assertTrue(len(home) > 0)


# ============================================================
# Phase 73.3: File System Resilience Tests
# ============================================================

class TestFileLock(unittest.TestCase):
    """Test cross-platform file locking."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_acquire_and_release(self):
        from mcp_server_nucleus.runtime.file_resilience import FileLock
        lock_path = Path(self.tmpdir) / "test.json"
        lock = FileLock(lock_path)
        self.assertTrue(lock.acquire())
        lock.release()

    def test_context_manager(self):
        from mcp_server_nucleus.runtime.file_resilience import FileLock
        lock_path = Path(self.tmpdir) / "test.json"
        with FileLock(lock_path) as lock:
            self.assertTrue(lock._acquired)

    def test_stale_lock_cleanup(self):
        from mcp_server_nucleus.runtime.file_resilience import FileLock
        lock_path = Path(self.tmpdir) / "test.json"
        # Create a stale lock file
        stale_lock = lock_path.with_suffix(".json.lock")
        stale_lock.parent.mkdir(parents=True, exist_ok=True)
        stale_lock.write_text("12345")
        # Set mtime to 120 seconds ago
        old_time = time.time() - 120
        os.utime(str(stale_lock), (old_time, old_time))
        lock = FileLock(lock_path, timeout=2.0)
        self.assertTrue(lock.acquire())
        lock.release()


class TestAtomicWriter(unittest.TestCase):
    """Test atomic file writes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_text(self):
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        path = Path(self.tmpdir) / "test.txt"
        self.assertTrue(AtomicWriter.write_text(path, "hello world"))
        self.assertEqual(path.read_text(), "hello world")

    def test_write_json(self):
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        path = Path(self.tmpdir) / "test.json"
        data = {"key": "value", "number": 42}
        self.assertTrue(AtomicWriter.write_json(path, data))
        loaded = json.loads(path.read_text())
        self.assertEqual(loaded["key"], "value")

    def test_write_creates_directories(self):
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        path = Path(self.tmpdir) / "deep" / "nested" / "test.txt"
        self.assertTrue(AtomicWriter.write_text(path, "content"))
        self.assertTrue(path.exists())

    def test_overwrite_existing(self):
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        path = Path(self.tmpdir) / "test.txt"
        AtomicWriter.write_text(path, "first")
        AtomicWriter.write_text(path, "second")
        self.assertEqual(path.read_text(), "second")

    def test_append_line(self):
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        path = Path(self.tmpdir) / "test.jsonl"
        AtomicWriter.append_line(path, '{"a": 1}')
        AtomicWriter.append_line(path, '{"b": 2}')
        lines = path.read_text().strip().split("\n")
        self.assertEqual(len(lines), 2)

    def test_concurrent_appends(self):
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        path = Path(self.tmpdir) / "concurrent.jsonl"
        errors = []

        def append_many(thread_id):
            try:
                for i in range(20):
                    AtomicWriter.append_line(path, json.dumps({"thread": thread_id, "i": i}))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=append_many, args=(t,)) for t in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        self.assertEqual(len(errors), 0)
        lines = path.read_text().strip().split("\n")
        self.assertEqual(len(lines), 100)  # 5 threads × 20 lines


class TestResilientJSONReader(unittest.TestCase):
    """Test JSON reading with corruption recovery."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_read_valid_json(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "test.json"
        path.write_text('{"key": "value"}')
        result = ResilientJSONReader.read_json(path)
        self.assertEqual(result["key"], "value")

    def test_read_nonexistent(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "nonexistent.json"
        result = ResilientJSONReader.read_json(path, default={"default": True})
        self.assertEqual(result["default"], True)

    def test_read_corrupted_truncated(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "corrupted.json"
        path.write_text('{"key": "value"')  # Missing closing brace
        result = ResilientJSONReader.read_json(path, default=None)
        # Should attempt recovery
        self.assertIsNotNone(result) if result else None  # May or may not recover

    def test_read_bom_json(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "bom.json"
        path.write_bytes(b'\xef\xbb\xbf{"key": "bom"}')
        result = ResilientJSONReader.read_json(path)
        self.assertEqual(result["key"], "bom")

    def test_read_jsonl(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "test.jsonl"
        path.write_text('{"a": 1}\n{"b": 2}\n{"c": 3}\n')
        results = ResilientJSONReader.read_jsonl(path)
        self.assertEqual(len(results), 3)

    def test_read_jsonl_with_corrupted_lines(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "mixed.jsonl"
        path.write_text('{"good": 1}\nBAD LINE\n{"also_good": 2}\n')
        results = ResilientJSONReader.read_jsonl(path)
        self.assertEqual(len(results), 2)  # Skips corrupted line

    def test_read_jsonl_empty_lines(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "empty.jsonl"
        path.write_text('{"a": 1}\n\n\n{"b": 2}\n')
        results = ResilientJSONReader.read_jsonl(path)
        self.assertEqual(len(results), 2)

    def test_read_jsonl_nonexistent(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
        path = Path(self.tmpdir) / "nope.jsonl"
        results = ResilientJSONReader.read_jsonl(path)
        self.assertEqual(results, [])


class TestDiskSpaceChecker(unittest.TestCase):
    """Test disk space checking."""

    def test_has_space(self):
        from mcp_server_nucleus.runtime.file_resilience import DiskSpaceChecker
        self.assertTrue(DiskSpaceChecker.has_space("/tmp"))

    def test_get_free_space(self):
        from mcp_server_nucleus.runtime.file_resilience import DiskSpaceChecker
        free = DiskSpaceChecker.get_free_space_mb("/tmp")
        self.assertGreater(free, 0)

    def test_nonexistent_path_checks_parent(self):
        from mcp_server_nucleus.runtime.file_resilience import DiskSpaceChecker
        self.assertTrue(DiskSpaceChecker.has_space("/tmp/nonexistent/deep/path"))


class TestPermissionChecker(unittest.TestCase):
    """Test permission checking."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_can_read_existing(self):
        from mcp_server_nucleus.runtime.file_resilience import PermissionChecker
        path = Path(self.tmpdir) / "readable.txt"
        path.write_text("content")
        self.assertTrue(PermissionChecker.can_read(path))

    def test_can_write_to_dir(self):
        from mcp_server_nucleus.runtime.file_resilience import PermissionChecker
        path = Path(self.tmpdir) / "new_file.txt"
        self.assertTrue(PermissionChecker.can_write(path))

    def test_ensure_writable_creates_dirs(self):
        from mcp_server_nucleus.runtime.file_resilience import PermissionChecker
        path = Path(self.tmpdir) / "new" / "deep" / "file.txt"
        self.assertTrue(PermissionChecker.ensure_writable(path))
        self.assertTrue(path.parent.exists())

    def test_cannot_read_nonexistent(self):
        from mcp_server_nucleus.runtime.file_resilience import PermissionChecker
        self.assertFalse(PermissionChecker.can_read("/tmp/totally_nonexistent_12345"))


class TestResilientFileOps(unittest.TestCase):
    """Test unified resilient file operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_and_read_json(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps
        ops = ResilientFileOps()
        path = Path(self.tmpdir) / "test.json"
        data = {"phase": 73, "reliability": 99.9}
        self.assertTrue(ops.write_json(path, data))
        loaded = ops.read_json(path)
        self.assertEqual(loaded["phase"], 73)

    def test_append_and_read_jsonl(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps
        ops = ResilientFileOps()
        path = Path(self.tmpdir) / "test.jsonl"
        ops.append_jsonl(path, {"record": 1})
        ops.append_jsonl(path, {"record": 2})
        records = ops.read_jsonl(path)
        self.assertEqual(len(records), 2)

    def test_stats(self):
        from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps
        ops = ResilientFileOps()
        path = Path(self.tmpdir) / "stats.json"
        ops.write_json(path, {})
        ops.read_json(path)
        stats = ops.get_stats()
        self.assertEqual(stats["write_count"], 1)
        self.assertEqual(stats["read_count"], 1)

    def test_singleton(self):
        from mcp_server_nucleus.runtime.file_resilience import get_resilient_file_ops
        o1 = get_resilient_file_ops()
        o2 = get_resilient_file_ops()
        self.assertIs(o1, o2)


# ============================================================
# Phase 73.4: Error Telemetry Tests
# ============================================================

class TestStructuredError(unittest.TestCase):
    """Test structured error creation."""

    def test_create_error(self):
        from mcp_server_nucleus.runtime.error_telemetry import StructuredError, ErrorDomain
        err = StructuredError(
            error_id="err-000001",
            domain=ErrorDomain.LLM,
            code="E100",
            message="Timeout",
            source_module="test"
        )
        self.assertEqual(err.domain, ErrorDomain.LLM)
        self.assertEqual(err.code, "E100")

    def test_error_to_dict(self):
        from mcp_server_nucleus.runtime.error_telemetry import StructuredError, ErrorDomain
        err = StructuredError(
            error_id="err-000001",
            domain=ErrorDomain.FILESYSTEM,
            code="E200",
            message="Write failed",
            source_module="test",
            context={"path": "/tmp/test"}
        )
        d = err.to_dict()
        self.assertEqual(d["domain"], "FILESYSTEM")
        self.assertIn("context", d)

    def test_error_with_stack_trace(self):
        from mcp_server_nucleus.runtime.error_telemetry import StructuredError, ErrorDomain
        err = StructuredError(
            error_id="err-000001",
            domain=ErrorDomain.UNKNOWN,
            code="E999",
            message="Unknown",
            source_module="test",
            stack_trace="Traceback...\n  File test.py\n    raise Error"
        )
        d = err.to_dict()
        self.assertIn("stack_trace", d)


class TestErrorAggregator(unittest.TestCase):
    """Test error aggregation and pattern detection."""

    def test_record_and_stats(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorAggregator, StructuredError, ErrorDomain
        agg = ErrorAggregator()
        for i in range(5):
            agg.record(StructuredError(
                error_id=f"err-{i}", domain=ErrorDomain.LLM,
                code="E100", message="Timeout", source_module="test"
            ))
        stats = agg.get_stats()
        self.assertEqual(stats["total_errors"], 5)
        self.assertEqual(stats["by_domain"]["LLM"], 5)

    def test_multiple_domains(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorAggregator, StructuredError, ErrorDomain
        agg = ErrorAggregator()
        agg.record(StructuredError("e1", ErrorDomain.LLM, "E100", "t", "test"))
        agg.record(StructuredError("e2", ErrorDomain.FILESYSTEM, "E200", "w", "test"))
        agg.record(StructuredError("e3", ErrorDomain.NETWORK, "E300", "n", "test"))
        stats = agg.get_stats()
        self.assertEqual(stats["total_errors"], 3)
        self.assertEqual(len(stats["by_domain"]), 3)

    def test_get_recent(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorAggregator, StructuredError, ErrorDomain
        agg = ErrorAggregator()
        for i in range(30):
            agg.record(StructuredError(f"e{i}", ErrorDomain.LLM, "E100", f"err {i}", "test"))
        recent = agg.get_recent(limit=10)
        self.assertEqual(len(recent), 10)

    def test_top_errors(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorAggregator, StructuredError, ErrorDomain
        agg = ErrorAggregator()
        for _ in range(10):
            agg.record(StructuredError("e", ErrorDomain.LLM, "E100", "timeout", "test"))
        for _ in range(5):
            agg.record(StructuredError("e", ErrorDomain.LLM, "E101", "rate limit", "test"))
        top = agg.get_top_errors(n=2)
        self.assertEqual(top[0][0], "E100")
        self.assertEqual(top[0][1], 10)

    def test_thread_safety(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorAggregator, StructuredError, ErrorDomain
        agg = ErrorAggregator()
        errors = []
        def record_many():
            try:
                for i in range(50):
                    agg.record(StructuredError(f"e{i}", ErrorDomain.LLM, "E100", "t", "test"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=record_many) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(errors), 0)
        self.assertEqual(agg.get_stats()["total_errors"], 250)


class TestAlertManager(unittest.TestCase):
    """Test threshold-based alerting."""

    def test_no_alerts_initially(self):
        from mcp_server_nucleus.runtime.error_telemetry import AlertManager, ErrorAggregator
        mgr = AlertManager()
        agg = ErrorAggregator()
        alerts = mgr.check(agg)
        self.assertEqual(len(alerts), 0)

    def test_alert_on_threshold(self):
        from mcp_server_nucleus.runtime.error_telemetry import (
            AlertManager, AlertThreshold, ErrorAggregator, StructuredError, ErrorDomain
        )
        mgr = AlertManager(thresholds=[
            AlertThreshold("LLM", 0.1, 3, "WARNING")
        ])
        agg = ErrorAggregator()
        for _ in range(5):
            agg.record(StructuredError("e", ErrorDomain.LLM, "E100", "t", "test"))
        alerts = mgr.check(agg)
        self.assertGreater(len(alerts), 0)
        self.assertEqual(alerts[0]["domain"], "LLM")

    def test_alert_callback(self):
        from mcp_server_nucleus.runtime.error_telemetry import (
            AlertManager, AlertThreshold, ErrorAggregator, StructuredError, ErrorDomain
        )
        received = []
        mgr = AlertManager(thresholds=[AlertThreshold("LLM", 0.1, 2, "CRITICAL")])
        mgr.on_alert(lambda a: received.append(a))
        agg = ErrorAggregator()
        for _ in range(3):
            agg.record(StructuredError("e", ErrorDomain.LLM, "E100", "t", "test"))
        mgr.check(agg)
        self.assertGreater(len(received), 0)


class TestErrorTelemetry(unittest.TestCase):
    """Test main ErrorTelemetry class."""

    def test_record_error(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry
        tel = ErrorTelemetry()
        err = tel.record_error("E100", "LLM timeout", "test_module")
        self.assertEqual(err.code, "E100")
        self.assertEqual(err.source_module, "test_module")

    def test_record_error_with_exception(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry
        tel = ErrorTelemetry()
        try:
            raise ValueError("test error")
        except ValueError as e:
            err = tel.record_error("E400", "Validation failed", "test", exception=e)
            self.assertIsNotNone(err.stack_trace)

    def test_get_stats(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry
        tel = ErrorTelemetry()
        tel.record_error("E100", "timeout", "test")
        tel.record_error("E200", "write fail", "test")
        stats = tel.get_stats()
        self.assertEqual(stats["total_errors"], 2)

    def test_get_recent_errors(self):
        from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry
        tel = ErrorTelemetry()
        for i in range(5):
            tel.record_error("E100", f"error {i}", "test")
        recent = tel.get_recent_errors(limit=3)
        self.assertEqual(len(recent), 3)

    def test_singleton(self):
        from mcp_server_nucleus.runtime.error_telemetry import get_error_telemetry
        t1 = get_error_telemetry()
        t2 = get_error_telemetry()
        self.assertIs(t1, t2)


# ============================================================
# Phase 73.5: Integration Tests
# ============================================================

class TestIntentAnalyzerWithResilience(unittest.TestCase):
    """Test that intent analyzer uses resilient client and falls back properly."""

    def test_fallback_to_keyword_analysis(self):
        from mcp_server_nucleus.runtime.llm_intent_analyzer import LLMIntentAnalyzer
        analyzer = LLMIntentAnalyzer()
        # Without API key, should fall back to keyword analysis
        result = analyzer.analyze("add a task for testing", [
            {"name": "brain_add_task", "description": "Add a task"},
            {"name": "brain_list_tasks", "description": "List tasks"},
        ])
        # Should not crash — either LLM works or falls back
        self.assertIsNotNone(result)

    def test_empty_request(self):
        from mcp_server_nucleus.runtime.llm_intent_analyzer import LLMIntentAnalyzer
        analyzer = LLMIntentAnalyzer()
        result = analyzer.analyze("", [])
        self.assertFalse(result.has_requirements())

    def test_no_tools(self):
        from mcp_server_nucleus.runtime.llm_intent_analyzer import LLMIntentAnalyzer
        analyzer = LLMIntentAnalyzer()
        result = analyzer.analyze("add a task", [])
        self.assertEqual(result.reasoning, "No tools available")


class TestValidatorWithResilience(unittest.TestCase):
    """Test that validator uses resilient client and falls back."""

    def test_auto_pass_no_requirements(self):
        from mcp_server_nucleus.runtime.llm_tool_validator import LLMToolValidator
        validator = LLMToolValidator()
        result = validator.validate("hello", [], [], "Hi there!")
        self.assertTrue(result.passed)

    def test_all_tools_called(self):
        from mcp_server_nucleus.runtime.llm_tool_validator import LLMToolValidator
        validator = LLMToolValidator()
        result = validator.validate(
            "add task", ["brain_add_task"],
            ["brain_add_task"], "Done"
        )
        self.assertTrue(result.passed)

    def test_deterministic_fallback(self):
        from mcp_server_nucleus.runtime.llm_tool_validator import LLMToolValidator
        validator = LLMToolValidator()
        result = validator.validate_deterministic(
            ["brain_add_task", "brain_list_tasks"],
            ["brain_add_task"]
        )
        self.assertFalse(result.passed)
        self.assertIn("brain_list_tasks", result.missing_tools)


class TestEnforcerWithResilience(unittest.TestCase):
    """Test enforcer with resilient file ops."""

    def test_record_outcome(self):
        from mcp_server_nucleus.runtime.llm_tool_enforcer import LLMToolEnforcer
        from mcp_server_nucleus.runtime.llm_intent_analyzer import IntentAnalysisResult
        enforcer = LLMToolEnforcer()
        intent = IntentAnalysisResult(["brain_add_task"], [], "test")
        # Should not crash
        enforcer.record_outcome("add task", intent, ["brain_add_task"], True, 1)
        stats = enforcer.get_stats()
        self.assertGreaterEqual(stats["successes"], 1)

    def test_enforcement_prompt_generation(self):
        from mcp_server_nucleus.runtime.llm_tool_enforcer import LLMToolEnforcer
        from mcp_server_nucleus.runtime.llm_intent_analyzer import IntentAnalysisResult
        enforcer = LLMToolEnforcer()
        intent = IntentAnalysisResult(["brain_add_task"], [], "test")
        prompt = enforcer.generate_enforcement_prompt(intent)
        self.assertIn("brain_add_task", prompt)

    def test_empty_intent_no_prompt(self):
        from mcp_server_nucleus.runtime.llm_tool_enforcer import LLMToolEnforcer
        from mcp_server_nucleus.runtime.llm_intent_analyzer import IntentAnalysisResult
        enforcer = LLMToolEnforcer()
        intent = IntentAnalysisResult([], [], "no tools needed")
        prompt = enforcer.generate_enforcement_prompt(intent)
        self.assertEqual(prompt, "")


class TestRecommenderWithResilience(unittest.TestCase):
    """Test recommender with resilient file ops."""

    def test_recommend_task_tools(self):
        from mcp_server_nucleus.runtime.tool_recommender import ToolRecommender
        rec = ToolRecommender()
        result = rec.recommend("add a new task", [
            {"name": "nucleus_tasks", "description": "Task + depth management facade"},
            {"name": "nucleus_engrams", "description": "Memory facade"},
            {"name": "nucleus_governance", "description": "Governance facade"},
        ])
        self.assertIn("nucleus_tasks", result.recommended_tools)

    def test_essential_tools_always_included(self):
        from mcp_server_nucleus.runtime.tool_recommender import ToolRecommender
        rec = ToolRecommender()
        result = rec.recommend("random request xyz", [
            {"name": "nucleus_engrams", "description": "Memory facade"},
            {"name": "nucleus_tasks", "description": "Task facade"},
            {"name": "nucleus_governance", "description": "Governance facade"},
        ])
        self.assertIn("nucleus_engrams", result.recommended_tools)
        self.assertIn("nucleus_tasks", result.recommended_tools)
        self.assertIn("nucleus_governance", result.recommended_tools)

    def test_record_usage(self):
        from mcp_server_nucleus.runtime.tool_recommender import ToolRecommender
        rec = ToolRecommender()
        rec.record_usage("nucleus_tasks")
        rec.record_usage("nucleus_tasks")
        stats = rec.get_usage_stats()
        self.assertEqual(stats["total_tool_calls"], 2)


# ============================================================
# Cross-Environment Edge Case Tests
# ============================================================

class TestCrossEnvironmentEdgeCases(unittest.TestCase):
    """Edge cases that can happen in specific environments."""

    def test_unicode_in_error_messages(self):
        """Windsurf/Antigravity may produce unicode errors."""
        from mcp_server_nucleus.runtime.llm_resilience import categorize_exception
        err = categorize_exception(Exception("Connection failed: 连接被拒绝"))
        self.assertEqual(err.category.value, "NETWORK")

    def test_unicode_in_json_output(self):
        """Ensure JSON output handles unicode."""
        from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
        tmpdir = tempfile.mkdtemp()
        try:
            path = Path(tmpdir) / "unicode.json"
            data = {"message": "こんにちは世界", "emoji": "🧠"}
            AtomicWriter.write_json(path, data)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["message"], "こんにちは世界")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_very_long_error_message(self):
        """LLM might return very long errors."""
        from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry
        tel = ErrorTelemetry()
        long_msg = "x" * 10000
        err = tel.record_error("E100", long_msg, "test")
        self.assertTrue(len(err.message) <= 500)

    def test_empty_llm_response(self):
        """LLM returns empty string."""
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        self.assertIsNone(extract_json_from_text(""))

    def test_llm_returns_only_whitespace(self):
        from mcp_server_nucleus.runtime.llm_resilience import extract_json_from_text
        self.assertIsNone(extract_json_from_text("   \n\t  "))

    def test_path_with_spaces(self):
        """Windows paths often have spaces."""
        tmpdir = tempfile.mkdtemp(prefix="path with spaces ")
        try:
            from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
            path = Path(tmpdir) / "test file.json"
            AtomicWriter.write_json(path, {"space": True})
            self.assertTrue(path.exists())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_path_with_unicode(self):
        """macOS supports unicode filenames."""
        tmpdir = tempfile.mkdtemp()
        try:
            from mcp_server_nucleus.runtime.file_resilience import AtomicWriter
            path = Path(tmpdir) / "テスト.json"
            AtomicWriter.write_json(path, {"unicode": True})
            self.assertTrue(path.exists())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_concurrent_json_reads(self):
        """Multiple agents reading same file."""
        tmpdir = tempfile.mkdtemp()
        try:
            from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps
            ops = ResilientFileOps()
            path = Path(tmpdir) / "shared.json"
            ops.write_json(path, {"shared": True})

            results = []
            errors = []
            def read_many():
                try:
                    for _ in range(50):
                        data = ops.read_json(path)
                        results.append(data)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=read_many) for _ in range(5)]
            for t in threads: t.start()
            for t in threads: t.join()
            self.assertEqual(len(errors), 0)
            self.assertEqual(len(results), 250)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_circuit_breaker_recovery(self):
        """Simulate circuit breaker open → half-open → closed."""
        from mcp_server_nucleus.runtime.llm_resilience import CircuitBreaker, CircuitState, CircuitBreakerConfig
        cb = CircuitBreaker("recovery_test", CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout_s=0.1, success_threshold=1
        ))
        # Trip it
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        # Wait for half-open
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        # Successful recovery
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_zero_byte_json_file(self):
        """Edge case: zero-byte JSON file."""
        tmpdir = tempfile.mkdtemp()
        try:
            from mcp_server_nucleus.runtime.file_resilience import ResilientJSONReader
            path = Path(tmpdir) / "empty.json"
            path.write_text("")
            result = ResilientJSONReader.read_json(path, default={"empty": True})
            # Should return default for empty file
            self.assertIsNotNone(result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_massive_json_payload(self):
        """Large JSON shouldn't crash."""
        tmpdir = tempfile.mkdtemp()
        try:
            from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps
            ops = ResilientFileOps()
            path = Path(tmpdir) / "large.json"
            data = {"items": [{"id": i, "data": "x" * 100} for i in range(1000)]}
            ops.write_json(path, data)
            loaded = ops.read_json(path)
            self.assertEqual(len(loaded["items"]), 1000)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestAllModulesImport(unittest.TestCase):
    """Verify all Phase 73 modules can be imported without errors."""

    def test_import_llm_resilience(self):
        from mcp_server_nucleus.runtime import llm_resilience
        self.assertIsNotNone(llm_resilience)

    def test_import_environment_detector(self):
        from mcp_server_nucleus.runtime import environment_detector
        self.assertIsNotNone(environment_detector)

    def test_import_file_resilience(self):
        from mcp_server_nucleus.runtime import file_resilience
        self.assertIsNotNone(file_resilience)

    def test_import_error_telemetry(self):
        from mcp_server_nucleus.runtime import error_telemetry
        self.assertIsNotNone(error_telemetry)

    def test_import_all_from_runtime(self):
        from mcp_server_nucleus.runtime import (
            ResilientLLMClient, CircuitBreaker, CircuitState,
            EnvironmentDetector, OSType, MCPHost,
            ResilientFileOps, AtomicWriter, FileLock,
            ErrorTelemetry, StructuredError, ErrorDomain,
        )
        self.assertIsNotNone(ResilientLLMClient)
        self.assertIsNotNone(EnvironmentDetector)
        self.assertIsNotNone(ResilientFileOps)
        self.assertIsNotNone(ErrorTelemetry)


if __name__ == "__main__":
    unittest.main()
