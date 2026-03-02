"""
Tests for prometheus.py dispatch telemetry bridge.

Verifies:
- Dispatch telemetry metrics appear in Prometheus output
- Dispatch counters, errors, and latency are correctly formatted
- Empty dispatch telemetry produces no dispatch section
"""

import pytest

from mcp_server_nucleus.runtime.prometheus import (
    get_prometheus_metrics,
    reset_metrics,
)
from mcp_server_nucleus.tools._dispatch import (
    dispatch,
    get_dispatch_telemetry,
)


@pytest.fixture(autouse=True)
def clean_metrics():
    """Reset both prometheus and dispatch metrics before each test."""
    reset_metrics()
    get_dispatch_telemetry().reset()
    yield
    reset_metrics()
    get_dispatch_telemetry().reset()


def _echo_handler(msg="hello"):
    return {"echo": msg}


def _error_handler():
    raise ValueError("intentional error")


SAMPLE_ROUTER = {
    "echo": _echo_handler,
    "error": _error_handler,
}


class TestPrometheusDispatchBridge:
    def test_no_dispatch_metrics_when_empty(self):
        output = get_prometheus_metrics()
        assert "nucleus_dispatch_total" not in output

    def test_dispatch_metrics_appear_after_calls(self):
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_test")
        dispatch("echo", {"msg": "world"}, SAMPLE_ROUTER, "nucleus_test")

        output = get_prometheus_metrics()
        assert "nucleus_dispatch_total" in output
        assert 'facade="nucleus_test",action="echo"' in output
        assert "} 2" in output  # 2 calls

    def test_dispatch_errors_appear(self):
        dispatch("error", {}, SAMPLE_ROUTER, "nucleus_test")

        output = get_prometheus_metrics()
        assert "nucleus_dispatch_errors_total" in output
        assert 'facade="nucleus_test",action="error"' in output

    def test_dispatch_latency_appears(self):
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_test")

        output = get_prometheus_metrics()
        assert "nucleus_dispatch_latency_avg_ms" in output
        assert 'facade="nucleus_test",action="echo"' in output

    def test_multiple_facades_in_output(self):
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_tasks")
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_engrams")

        output = get_prometheus_metrics()
        assert 'facade="nucleus_tasks"' in output
        assert 'facade="nucleus_engrams"' in output

    def test_prometheus_format_correctness(self):
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_test")

        output = get_prometheus_metrics()
        lines = output.strip().split("\n")

        # Find dispatch section
        dispatch_lines = [l for l in lines if "nucleus_dispatch" in l]
        for line in dispatch_lines:
            if line.startswith("#"):
                assert line.startswith("# HELP") or line.startswith("# TYPE")
            else:
                # metric lines should have format: metric_name{labels} value
                assert "{" in line or line.strip() == ""

    def test_no_errors_section_when_no_errors(self):
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_test")

        output = get_prometheus_metrics()
        assert "nucleus_dispatch_errors_total{" not in output
