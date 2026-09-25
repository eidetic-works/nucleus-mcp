"""Tests for relay domain metrics (feat/relay-health-metrics).

Covers:
    - test_relay_post_increments_queued_counter
    - test_relay_ack_increments_acked_counter
    - test_rate_limit_hit_increments_counter
    - test_metrics_endpoint_returns_200
    - test_queue_depth_gauge_reflects_unread_count
    - test_metrics_endpoint_content_type
"""

import json
import os
import pytest

from mcp_server_nucleus.runtime.prometheus import (
    reset_metrics,
    get_prometheus_metrics,
    get_metrics_json,
    RELAY_MESSAGES_TOTAL,
    RATE_LIMIT_HITS_TOTAL,
    RELAY_QUEUE_DEPTH,
)


@pytest.fixture(autouse=True)
def _clean_metrics():
    """Reset metrics before each test to avoid cross-test pollution."""
    reset_metrics()
    yield
    reset_metrics()


# ── 1. relay_post increments queued counter ──────────────────────────────────

def test_relay_post_increments_queued_counter(tmp_path, monkeypatch):
    """relay_post should call inc_relay_message('queued'), incrementing the counter."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    from mcp_server_nucleus.runtime import relay_ops
    monkeypatch.setattr(relay_ops, "detect_session_type", lambda: "claude_code_main")

    relay_ops.relay_post(
        to="cowork",
        subject="test subject",
        body="hello",
        sender="claude_code_main",
    )

    data = get_metrics_json()
    # The queued counter key: nucleus_relay_messages_total{status="queued"}
    queued_key = 'nucleus_relay_messages_total{status="queued"}'
    assert data["tool_calls"].get(queued_key, 0) >= 1, (
        f"Expected queued counter >=1, got {data['tool_calls']}"
    )


# ── 2. relay_ack increments acked counter ─────────────────────────────────────

def test_relay_ack_increments_acked_counter(tmp_path, monkeypatch):
    """relay_ack on an existing message should increment nucleus_relay_messages_total{status='acked'}."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))

    # Write a fake relay message to disk so relay_ack can find it
    from datetime import datetime, timezone
    bucket_dir = tmp_path / "relay" / "cowork"
    bucket_dir.mkdir(parents=True)
    msg_id = "relay_20260101_000000_abcd1234"
    msg = {
        "id": msg_id,
        "from": "claude_code_main",
        "to": "cowork",
        "subject": "test",
        "body": "body",
        "priority": "normal",
        "context": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "read_at": None,
        "read_by": None,
        "read_by_sessions": {},
    }
    msg_file = bucket_dir / f"20260101_000000_{msg_id}.json"
    msg_file.write_text(json.dumps(msg), encoding="utf-8")

    from mcp_server_nucleus.runtime import relay_ops
    result = relay_ops.relay_ack(msg_id, recipient="cowork")

    assert result.get("acknowledged") is True, f"Expected ack, got {result}"

    data = get_metrics_json()
    acked_key = 'nucleus_relay_messages_total{status="acked"}'
    assert data["tool_calls"].get(acked_key, 0) >= 1, (
        f"Expected acked counter >=1, got {data['tool_calls']}"
    )


# ── 3. rate_limit_hit increments counter ─────────────────────────────────────

def test_rate_limit_hit_increments_counter():
    """check_or_raise should increment nucleus_rate_limit_hits_total on rejection."""
    from mcp_server_nucleus.runtime.rate_limiter import RateLimiter, RateLimitError

    # fill_rate must be >0 to avoid ZeroDivisionError in time_until_available;
    # capacity=0 ensures every request is rejected immediately.
    limiter = RateLimiter(default_capacity=0.0, default_fill_rate=1.0,
                         global_capacity=0.0, global_fill_rate=1.0)

    with pytest.raises(RateLimitError):
        limiter.check_or_raise(client_id="test_client", tool_name="test_tool")

    data = get_metrics_json()
    assert data["tool_calls"].get(RATE_LIMIT_HITS_TOTAL, 0) >= 1, (
        f"Expected rate_limit counter >=1, got {data['tool_calls']}"
    )


# ── 4. /metrics endpoint returns 200 ─────────────────────────────────────────

def test_metrics_endpoint_returns_200():
    """GET /metrics should return HTTP 200."""
    from starlette.testclient import TestClient
    from mcp_server_nucleus.http_transport.app import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/metrics")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"


# ── 5. queue depth gauge reflects unread count ───────────────────────────────

def test_queue_depth_gauge_reflects_unread_count(tmp_path, monkeypatch):
    """scan_relay_queue_depth should count unread files and emit set_gauge."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))

    # Seed the relay dir with 2 unread + 1 read in bucket "claude_code_main"
    bucket = tmp_path / "relay" / "claude_code_main"
    bucket.mkdir(parents=True)

    for i in range(2):
        (bucket / f"msg_{i}.json").write_text(
            json.dumps({"id": f"m{i}", "read": False}), encoding="utf-8"
        )
    (bucket / "msg_read.json").write_text(
        json.dumps({"id": "m_read", "read": True}), encoding="utf-8"
    )

    from mcp_server_nucleus.runtime.jobs.health_job import scan_relay_queue_depth
    depths = scan_relay_queue_depth()

    assert depths.get("claude_code_main") == 2, (
        f"Expected 2 unread, got {depths}"
    )

    # Verify the gauge was set
    data = get_metrics_json()
    gauge_key = 'nucleus_relay_queue_depth{recipient="claude_code_main"}'
    assert data["gauges"].get(gauge_key) == 2.0, (
        f"Expected gauge=2.0, got {data['gauges']}"
    )


# ── 6. /metrics endpoint content-type ────────────────────────────────────────

def test_metrics_endpoint_content_type():
    """GET /metrics should return text/plain content-type."""
    from starlette.testclient import TestClient
    from mcp_server_nucleus.http_transport.app import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/metrics")
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct, f"Expected text/plain content-type, got: {ct}"
