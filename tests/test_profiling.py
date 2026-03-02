"""
Tests for Nucleus Performance Profiling (AG-014)
"""

import unittest
import os
import time
import importlib


class TestProfiling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Enable profiling for tests BEFORE importing
        os.environ["NUCLEUS_PROFILING"] = "true"
        os.environ["NUCLEUS_SLOW_THRESHOLD_MS"] = "10"
        # Import after setting env vars
        from mcp_server_nucleus.runtime import profiling
        # Reload to pick up env vars
        importlib.reload(profiling)
        cls.profiling = profiling
    
    def setUp(self):
        self.profiling.reset_metrics()
    
    def tearDown(self):
        self.profiling.reset_metrics()
    
    def test_timed_decorator_records_metrics(self):
        """Test that @timed decorator records call metrics."""
        @self.profiling.timed("test_operation")
        def sample_function():
            time.sleep(0.01)  # 10ms
            return "result"
        
        result = sample_function()
        self.assertEqual(result, "result")
        
        metrics = self.profiling.get_metrics()
        self.assertIn("test_operation", metrics)
        self.assertEqual(metrics["test_operation"]["calls"], 1)
        self.assertGreater(metrics["test_operation"]["total_ms"], 0)
    
    def test_multiple_calls_accumulate(self):
        """Test that multiple calls accumulate in metrics."""
        @self.profiling.timed("multi_call_test")
        def fast_function():
            return True
        
        for _ in range(5):
            fast_function()
        
        metrics = self.profiling.get_metrics()
        self.assertEqual(metrics["multi_call_test"]["calls"], 5)
    
    def test_metrics_summary_format(self):
        """Test that metrics summary returns markdown table."""
        @self.profiling.timed("summary_test")
        def dummy():
            pass
        
        dummy()
        
        summary = self.profiling.get_metrics_summary()
        self.assertIn("# Performance Metrics", summary)
        self.assertIn("| Operation |", summary)
        self.assertIn("summary_test", summary)
    
    def test_timed_io_decorator(self):
        """Test timed_io convenience decorator."""
        @self.profiling.timed_io
        def read_file():
            return "data"
        
        read_file()
        
        metrics = self.profiling.get_metrics()
        self.assertIn("io.read_file", metrics)
    
    def test_reset_metrics_clears_data(self):
        """Test that reset_metrics clears all data."""
        @self.profiling.timed("reset_test")
        def sample():
            pass
        
        sample()
        self.assertIn("reset_test", self.profiling.get_metrics())
        
        self.profiling.reset_metrics()
        self.assertEqual(self.profiling.get_metrics(), {})
    
    def test_min_max_tracking(self):
        """Test that min/max latencies are tracked."""
        @self.profiling.timed("minmax_test")
        def variable_time(duration):
            time.sleep(duration)
        
        variable_time(0.005)  # 5ms
        variable_time(0.015)  # 15ms
        
        metrics = self.profiling.get_metrics()
        m = metrics["minmax_test"]
        self.assertLess(m["min_ms"], m["max_ms"])


if __name__ == "__main__":
    unittest.main()
