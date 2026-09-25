"""
Phase 3 E2E — Relay HTTP service (POST/GET/ACK, 401, 429, multi-tenant, payload sizes).

Tests the relay HTTP routes against a LIVE server process:
  - POST a relay message, GET it back, ACK it
  - Test 401 (no bearer token)
  - Test 429 (rate-limit breach — send bursts)
  - Test multi-tenant isolation (tenant A posts, tenant B cannot read tenant A's messages)
  - Use realistic payload sizes (10KB, 100KB messages)

All traffic goes over real HTTP (httpx), not in-process ASGI.
"""
import json
import time

import httpx
import pytest

from .conftest import mcp_initialize

pytestmark = [pytest.mark.e2e]

TENANT_A_TOKEN = "tok-tenant-a"
TENANT_B_TOKEN = "tok-tenant-b"
TENANT_A_SENDER = "tenant-a-sender"
TENANT_B_SENDER = "tenant-b-sender"


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _valid_body(**overrides):
    sender = overrides.get("sender", TENANT_A_SENDER)
    body = {
        "subject": "e2e relay test",
        "body": "hello from e2e",
        "sender": TENANT_A_SENDER,
        "priority": "normal",
        "sender_anchor": {"role": sender, "transport": "http"},
    }
    body.update(overrides)
    return body


class TestRelayHttpE2E:
    """Relay HTTP service E2E against a live server."""

    @pytest.mark.timeout(60)
    def test_01_post_get_ack_happy_path(self, http_server_with_relay):
        """POST a relay message, GET it back, ACK it."""
        proc, base_url = http_server_with_relay
        # POST
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="e2e happy path"),
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r.status_code == 202, f"POST failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["sent"] is True
        msg_id = data.get("message_id") or data.get("id")
        assert msg_id, f"No message_id in response: {data}"
        # GET
        r2 = httpx.get(
            f"{base_url}/relay/claude_code_peer",
            params={"unread_only": "true", "limit": 50},
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r2.status_code == 200, f"GET failed: {r2.status_code} {r2.text}"
        msgs = r2.json()["messages"]
        found = [m for m in msgs if m.get("id") == msg_id]
        assert found, f"Posted message {msg_id} not found in inbox: {msgs}"
        assert found[0]["subject"] == "e2e happy path"
        # ACK
        r3 = httpx.post(
            f"{base_url}/relay/claude_code_peer/ack",
            json={"message_ids": [msg_id]},
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r3.status_code == 200, f"ACK failed: {r3.status_code} {r3.text}"
        assert r3.json()["acked"] >= 1
        # Verify it's now read
        r4 = httpx.get(
            f"{base_url}/relay/claude_code_peer",
            params={"unread_only": "true", "limit": 50},
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        unread = r4.json()["messages"]
        assert not any(m.get("id") == msg_id for m in unread), "Message still unread after ACK"

    @pytest.mark.timeout(30)
    def test_02_401_no_bearer_token(self, http_server_with_relay):
        """Test 401 when no bearer token is provided."""
        proc, base_url = http_server_with_relay
        # POST without auth
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(),
            timeout=10.0,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        assert "auth_missing" in r.json().get("error", "")
        # GET without auth
        r2 = httpx.get(f"{base_url}/relay/claude_code_peer", timeout=10.0)
        assert r2.status_code == 401, f"Expected 401, got {r2.status_code}"
        # ACK without auth
        r3 = httpx.post(
            f"{base_url}/relay/claude_code_peer/ack",
            json={"message_ids": ["fake-id"]},
            timeout=10.0,
        )
        assert r3.status_code == 401, f"Expected 401, got {r3.status_code}"

    @pytest.mark.timeout(30)
    def test_03_401_invalid_token(self, http_server_with_relay):
        """Test 401 with an unrecognized bearer token."""
        proc, base_url = http_server_with_relay
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(),
            headers=_auth("bogus-token-not-in-map"),
            timeout=10.0,
        )
        assert r.status_code == 401
        assert "auth_missing" in r.json().get("error", "")

    @pytest.mark.timeout(60)
    def test_04_429_rate_limit_breach(self, tmp_path, http_server_with_relay):
        """Test 429 by sending a burst that exceeds the rate limit.

        We start a SEPARATE server with a very low rate limit to trigger 429
        quickly without flooding the shared fixture.
        """
        from .conftest import _start_cloud_server, _stop_server
        token_map = json.dumps({"tok-low": "low-rate-sender"})
        proc, base_url = _start_cloud_server(
            tmp_path,
            extra_env={
                "NUCLEUS_RELAY_TOKEN_MAP": token_map,
                "NUCLEUS_RELAY_RATE_PER_MIN": "5",
                "NUCLEUS_RELAY_RATE_BURST": "3",
            },
        )
        try:
            # capacity = RATE_PER_MIN + RATE_BURST = 8; send 10 to breach
            statuses = []
            for i in range(10):
                r = httpx.post(
                    f"{base_url}/relay/claude_code_peer",
                    json=_valid_body(subject=f"burst {i}", sender="low-rate-sender"),
                    headers=_auth("tok-low"),
                    timeout=10.0,
                )
                statuses.append(r.status_code)
            # At least one should be 429
            assert 429 in statuses, f"No 429 in burst: {statuses}"
            # The 429 response should have Retry-After header
            idx_429 = statuses.index(429)
            # Re-send to capture the 429 response details
            r429 = httpx.post(
                f"{base_url}/relay/claude_code_peer",
                json=_valid_body(subject="after burst", sender="low-rate-sender"),
                headers=_auth("tok-low"),
                timeout=10.0,
            )
            assert r429.status_code == 429
            assert "rate_limited" in r429.json().get("error", "")
            assert "Retry-After" in r429.headers
        finally:
            _stop_server(proc)

    @pytest.mark.timeout(60)
    def test_05_multi_tenant_isolation(self, http_server_with_relay):
        """Tenant A posts, tenant B cannot read tenant A's messages.

        The relay route uses token_map for auth. The sender binding enforces
        that body.sender must match the token owner. Tenant B's token has a
        different sender, so tenant B cannot post as tenant A's sender.
        For GET: any valid token can read any recipient's inbox (GET is
        token-valid-only), BUT the tenant middleware isolates brain paths
        per-tenant, so tenant B's GET hits a different brain directory.

        We verify isolation by:
        1. Tenant A posts a message to recipient 'claude_code_peer'
        2. Tenant A GETs and finds the message
        3. Tenant B GETs the same recipient and does NOT find tenant A's message
           (because the tenant middleware routes to a different brain path)
        """
        proc, base_url = http_server_with_relay
        # Tenant A posts
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="tenant-a-secret", sender=TENANT_A_SENDER),
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r.status_code == 202, f"Tenant A POST failed: {r.status_code} {r.text}"
        msg_id = r.json().get("message_id") or r.json().get("id")
        # Tenant A GETs and finds it
        r_a = httpx.get(
            f"{base_url}/relay/claude_code_peer",
            params={"unread_only": "false", "limit": 50},
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r_a.status_code == 200
        msgs_a = r_a.json()["messages"]
        assert any(m.get("id") == msg_id for m in msgs_a), \
            f"Tenant A cannot find own message: {msgs_a}"
        # Tenant B GETs same recipient — should NOT find tenant A's message
        # (tenant middleware routes to a different brain path)
        r_b = httpx.get(
            f"{base_url}/relay/claude_code_peer",
            params={"unread_only": "false", "limit": 50},
            headers=_auth(TENANT_B_TOKEN),
            timeout=10.0,
        )
        assert r_b.status_code == 200
        msgs_b = r_b.json()["messages"]
        assert not any(m.get("id") == msg_id for m in msgs_b), \
            f"Tenant B can see tenant A's message! Isolation breach: {msgs_b}"

    @pytest.mark.timeout(30)
    def test_06_sender_mismatch_403(self, http_server_with_relay):
        """Tenant B cannot post using tenant A's sender identity (403 sender_mismatch)."""
        proc, base_url = http_server_with_relay
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="spoof attempt", sender=TENANT_A_SENDER),
            headers=_auth(TENANT_B_TOKEN),
            timeout=10.0,
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        assert "sender_mismatch" in r.json().get("error", "")

    @pytest.mark.timeout(30)
    def test_07_payload_10kb(self, http_server_with_relay):
        """Test 10KB message payload."""
        proc, base_url = http_server_with_relay
        big_body = "x" * 10_000
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="10kb payload", body=big_body),
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r.status_code == 202, f"10KB POST failed: {r.status_code} {r.text}"
        msg_id = r.json().get("message_id") or r.json().get("id")
        # GET it back and verify body size
        r2 = httpx.get(
            f"{base_url}/relay/claude_code_peer",
            params={"unread_only": "true", "limit": 50},
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        found = [m for m in msgs if m.get("id") == msg_id]
        assert found, "10KB message not found in inbox"
        assert len(found[0].get("body", "")) == 10_000, "Body size mismatch"

    @pytest.mark.timeout(30)
    def test_08_payload_100kb(self, http_server_with_relay):
        """Test 100KB message payload (within MAX_BODY_BYTES=200KB)."""
        proc, base_url = http_server_with_relay
        big_body = "y" * 100_000
        r = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="100kb payload", body=big_body),
            headers=_auth(TENANT_A_TOKEN),
            timeout=15.0,
        )
        assert r.status_code == 202, f"100KB POST failed: {r.status_code} {r.text}"
        msg_id = r.json().get("message_id") or r.json().get("id")
        # GET it back and verify body size
        r2 = httpx.get(
            f"{base_url}/relay/claude_code_peer",
            params={"unread_only": "true", "limit": 50},
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        found = [m for m in msgs if m.get("id") == msg_id]
        assert found, "100KB message not found in inbox"
        assert len(found[0].get("body", "")) == 100_000, "Body size mismatch"

    @pytest.mark.timeout(30)
    def test_09_relay_status_endpoint(self, http_server_with_relay):
        """GET /relay/{recipient}/status returns queue stats."""
        proc, base_url = http_server_with_relay
        # Post a message first
        httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="status test"),
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        r = httpx.get(
            f"{base_url}/relay/claude_code_peer/status",
            headers=_auth(TENANT_A_TOKEN),
            timeout=10.0,
        )
        assert r.status_code == 200, f"Status failed: {r.status_code} {r.text}"
        data = r.json()
        assert "recipient" in data
        assert "queue_depth" in data or "unread" in data

    @pytest.mark.timeout(30)
    def test_10_idempotency_key_dedup(self, http_server_with_relay):
        """Same Idempotency-Key returns 409 on replay."""
        proc, base_url = http_server_with_relay
        idem_key = "e2e-idem-test-001"
        headers = {**_auth(TENANT_A_TOKEN), "Idempotency-Key": idem_key}
        # First POST
        r1 = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="idempotency test"),
            headers=headers,
            timeout=10.0,
        )
        assert r1.status_code == 202
        # Replay with same key
        r2 = httpx.post(
            f"{base_url}/relay/claude_code_peer",
            json=_valid_body(subject="idempotency test replay"),
            headers=headers,
            timeout=10.0,
        )
        assert r2.status_code == 409, f"Expected 409 idempotency replay, got {r2.status_code}"
        assert "idempotency_replay" in r2.json().get("error", "")
