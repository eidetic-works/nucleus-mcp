"""Comprehensive tests for runtime/hooks.py — AgentManifest, InsightExchange,
RemoteExecutionProtocol, HostIntimacy, IdentityKey, AmbientTelemetry."""
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.hooks import (
    AgentManifest,
    InsightExchange,
    InsightPacket,
    RemoteExecutionProtocol,
    HostIntimacy,
    IdentityKey,
    AmbientTelemetry,
    CRYPTO_AVAILABLE,
)


# ── AgentManifest ────────────────────────────────────────────────

class TestAgentManifest:
    def test_defaults(self):
        m = AgentManifest(
            id="agent1",
            name="TestAgent",
            version="1.0",
            author_did="did:nucleus:abc",
            capabilities=["read", "write"],
        )
        assert m.id == "agent1"
        assert m.name == "TestAgent"
        assert m.version == "1.0"
        assert m.author_did == "did:nucleus:abc"
        assert m.capabilities == ["read", "write"]
        assert m.lifecycle_state == "active"
        assert m.price_per_invocation_usd == 0.0
        assert m.hash == ""
        assert m.signature == ""

    def test_sign(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        m = AgentManifest(
            id="agent1",
            name="TestAgent",
            version="1.0",
            author_did="did:nucleus:abc",
            capabilities=["read"],
        )
        m.sign(identity)
        assert m.signature != ""
        assert m.hash != ""

    def test_sign_sets_hash_consistently(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        m1 = AgentManifest(id="a", name="A", version="1", author_did="d", capabilities=[])
        m2 = AgentManifest(id="a", name="A", version="1", author_did="d", capabilities=[])
        m1.sign(identity)
        m2.sign(identity)
        assert m1.hash == m2.hash


# ── InsightExchange ──────────────────────────────────────────────

class TestInsightExchange:
    def test_init_creates_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        exchange = InsightExchange(brain)
        assert exchange.ledger_path == brain / "network" / "insights.jsonl"
        assert exchange.ledger_path.parent.exists()

    def test_offer_insight(self, tmp_path):
        brain = tmp_path / "brain"
        exchange = InsightExchange(brain)
        packet = exchange.offer_insight("topic1", "content here", 0.8)
        assert packet.topic == "topic1"
        assert packet.content_hash != ""
        assert packet.value_score == 0.8
        assert packet.source_did == "self"
        assert packet.timestamp > 0
        assert exchange.ledger_path.exists()
        lines = exchange.ledger_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["topic"] == "topic1"

    def test_offer_insight_content_hash(self, tmp_path):
        brain = tmp_path / "brain"
        exchange = InsightExchange(brain)
        import hashlib
        expected = hashlib.sha256("test content".encode()).hexdigest()
        packet = exchange.offer_insight("t", "test content", 1.0)
        assert packet.content_hash == expected

    def test_offer_multiple_insights(self, tmp_path):
        brain = tmp_path / "brain"
        exchange = InsightExchange(brain)
        exchange.offer_insight("t1", "c1", 0.5)
        exchange.offer_insight("t2", "c2", 0.9)
        lines = exchange.ledger_path.read_text().strip().split("\n")
        assert len(lines) == 2


# ── RemoteExecutionProtocol ──────────────────────────────────────

class TestRemoteExecutionProtocol:
    def test_init(self, tmp_path):
        brain = tmp_path / "brain"
        proto = RemoteExecutionProtocol(brain)
        assert proto.config_path == brain / "network" / "grid_config.json"

    def test_dispatch_container_returns_id(self, tmp_path):
        brain = tmp_path / "brain"
        proto = RemoteExecutionProtocol(brain)
        exec_id = proto.dispatch_container("myimage:latest", ["run"], 5.0)
        assert exec_id.startswith("grid_exec_")

    def test_dispatch_container_unique_ids(self, tmp_path):
        brain = tmp_path / "brain"
        proto = RemoteExecutionProtocol(brain)
        id1 = proto.dispatch_container("img1", [], 1.0)
        id2 = proto.dispatch_container("img2", [], 2.0)
        assert id1 != id2


# ── HostIntimacy ─────────────────────────────────────────────────

class TestHostIntimacy:
    def test_init_permissions(self):
        hi = HostIntimacy()
        assert hi.permissions["filesystem"] == "read-write"
        assert hi.permissions["geolocation"] == "denied"
        assert hi.permissions["clipboard"] == "ask"
        assert hi.permissions["biometrics"] == "unavailable"

    def test_check_permission_allowed(self):
        hi = HostIntimacy()
        assert hi.check_permission("filesystem") is True

    def test_check_permission_ask(self):
        hi = HostIntimacy()
        assert hi.check_permission("clipboard") is True

    def test_check_permission_denied(self):
        hi = HostIntimacy()
        assert hi.check_permission("geolocation") is False

    def test_check_permission_unavailable(self):
        hi = HostIntimacy()
        assert hi.check_permission("biometrics") is False

    def test_check_permission_unknown(self):
        hi = HostIntimacy()
        assert hi.check_permission("nonexistent") is False


# ── IdentityKey ──────────────────────────────────────────────────

class TestIdentityKey:
    def test_init_creates_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        assert identity.key_dir.exists()
        assert identity.private_key_path == brain / "identity" / "node.pem"
        assert identity.public_key_path == brain / "identity" / "node.pub"

    def test_did_generated(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        assert identity.did != ""
        if CRYPTO_AVAILABLE:
            assert identity.did.startswith("did:nucleus:")
        else:
            assert identity.did.startswith("did:nucleus:stub:")

    def test_load_existing_key(self, tmp_path):
        brain = tmp_path / "brain"
        identity1 = IdentityKey(brain)
        did1 = identity1.did
        identity2 = IdentityKey(brain)
        assert identity2.did == did1

    def test_sign_message(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        sig = identity.sign_message("test message")
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_sign_message_different_messages(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        sig1 = identity.sign_message("msg1")
        sig2 = identity.sign_message("msg2")
        assert sig1 != sig2

    def test_verify_signature_valid(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        msg = "test message"
        sig = identity.sign_message(msg)
        result = identity.verify_signature(msg, sig, identity.did)
        assert result is True

    def test_verify_signature_invalid(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        sig = identity.sign_message("msg1")
        result = identity.verify_signature("msg2", sig, identity.did)
        assert result is False

    def test_verify_signature_wrong_did_format(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        sig = identity.sign_message("msg")
        result = identity.verify_signature("msg", sig, "wrong:did:format")
        assert result is False

    def test_verify_signature_stub_did(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        result = identity.verify_signature("msg", "sig", "did:nucleus:stub:abc")
        assert result is True

    def test_verify_signature_bad_hex(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        result = identity.verify_signature("msg", "badhex", "did:nucleus:zzzz")
        assert result is False

    def test_corrupt_key_regenerates(self, tmp_path):
        brain = tmp_path / "brain"
        identity1 = IdentityKey(brain)
        # Corrupt the key file
        identity1.private_key_path.write_bytes(b"corrupt key data")
        identity2 = IdentityKey(brain)
        assert identity2.did != identity1.did

    def test_public_key_saved(self, tmp_path):
        brain = tmp_path / "brain"
        identity = IdentityKey(brain)
        if CRYPTO_AVAILABLE:
            assert identity.public_key_path.exists()
            content = identity.public_key_path.read_text()
            assert "BEGIN" in content


# ── AmbientTelemetry ─────────────────────────────────────────────

class TestAmbientTelemetry:
    def test_init(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        telemetry = AmbientTelemetry(brain)
        assert telemetry.pulse_file == brain / "pulse.json"
        assert telemetry.identity is None

    def test_init_with_identity(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        identity = IdentityKey(brain)
        telemetry = AmbientTelemetry(brain, identity)
        assert telemetry.identity is not None

    def test_beat_idle(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        telemetry = AmbientTelemetry(brain)
        telemetry.beat("idle", 0)
        assert telemetry.pulse_file.exists()
        data = json.loads(telemetry.pulse_file.read_text())
        assert data["status"] == "idle"
        assert data["tasks"] == 0
        assert data["color"] == "green"

    def test_beat_busy(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        telemetry = AmbientTelemetry(brain)
        telemetry.beat("busy", 3, cpu_usage=45.5)
        data = json.loads(telemetry.pulse_file.read_text())
        assert data["status"] == "busy"
        assert data["tasks"] == 3
        assert data["cpu"] == 45.5
        assert data["color"] == "gold"

    def test_beat_error(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        telemetry = AmbientTelemetry(brain)
        telemetry.beat("error", 1)
        data = json.loads(telemetry.pulse_file.read_text())
        assert data["color"] == "red"

    def test_beat_with_identity(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        identity = IdentityKey(brain)
        telemetry = AmbientTelemetry(brain, identity)
        telemetry.beat("idle", 0)
        data = json.loads(telemetry.pulse_file.read_text())
        assert "pulse_sig" in data
        assert "did" in data

    def test_beat_overwrites(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        telemetry = AmbientTelemetry(brain)
        telemetry.beat("idle", 0)
        telemetry.beat("busy", 5)
        data = json.loads(telemetry.pulse_file.read_text())
        assert data["status"] == "busy"
        assert data["tasks"] == 5

    def test_beat_exception_handled(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        telemetry = AmbientTelemetry(brain)
        # Make pulse_file a directory to trigger exception
        telemetry.pulse_file.mkdir(parents=True, exist_ok=True)
        # Should not raise
        telemetry.beat("idle", 0)
