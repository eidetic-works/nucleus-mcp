"""
Tests for Nucleus Pulse Telemetry (v1.1.0 Scaffold)
====================================================
Validates the core Sovereign Manifest requirements:
  1. Local-only storage
  2. Salt rotation
  3. Consent handshake
  4. Differential privacy (decoy injection)
  5. Audit CLI (view)
  6. Purge (nuclear option)
"""

import os
import json
import shutil
import tempfile
import pytest
from pathlib import Path

# Set test brain path before import
TEST_BRAIN = tempfile.mkdtemp(prefix="nucleus_pulse_test_")
os.environ["NUCLEAR_BRAIN_PATH"] = TEST_BRAIN

from mcp_server_nucleus.runtime.pulse import (
    PulseStore, PulseEvent, PulseConsent, SaltManager,
    CONSENT_ALLOWED, CONSENT_DENIED, CONSENT_PENDING, CONSENT_REVOKED,
    HUBS, pulse_record, pulse_view,
)


@pytest.fixture(autouse=True)
def clean_pulse_dir():
    """Ensure a fresh pulse directory for each test."""
    pulse_dir = Path(TEST_BRAIN) / "pulse"
    if pulse_dir.exists():
        shutil.rmtree(pulse_dir)
    pulse_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup after test
    if pulse_dir.exists():
        shutil.rmtree(pulse_dir)


@pytest.fixture
def store():
    """Create a fresh PulseStore."""
    return PulseStore(brain_path=Path(TEST_BRAIN))


# ============================================================
# CONSENT TESTS (The Handshake)
# ============================================================

class TestConsent:
    def test_initial_state_is_pending(self, store):
        consent = store.get_consent()
        assert consent.state == CONSENT_PENDING
    
    def test_needs_handshake_on_fresh_install(self, store):
        assert store.needs_handshake() is True
    
    def test_allow_consent(self, store):
        consent = store.set_consent(CONSENT_ALLOWED)
        assert consent.state == CONSENT_ALLOWED
        assert consent.decided_at is not None
        assert store.needs_handshake() is False
    
    def test_deny_consent(self, store):
        consent = store.set_consent(CONSENT_DENIED)
        assert consent.state == CONSENT_DENIED
        assert store.needs_handshake() is False
    
    def test_revoke_consent(self, store):
        store.set_consent(CONSENT_ALLOWED)
        consent = store.set_consent(CONSENT_REVOKED)
        assert consent.state == CONSENT_REVOKED
    
    def test_invalid_consent_raises(self, store):
        with pytest.raises(ValueError):
            store.set_consent("invalid_state")
    
    def test_handshake_message_not_empty(self, store):
        msg = store.handshake_message()
        assert "Nucleus Pulse" in msg
        assert "mcp pulse --view" in msg
        assert "mcp pulse --deny" in msg


# ============================================================
# EVENT RECORDING TESTS
# ============================================================

class TestEventRecording:
    def test_record_event(self, store):
        store.set_consent(CONSENT_ALLOWED)
        event = store.record("memory", "write", {"count": 1})
        assert event is not None
        assert event.hub == "memory"
        assert event.action == "write"
        assert event.is_decoy is False
        assert len(event.pulse_id) == 16
    
    def test_record_blocked_when_denied(self, store):
        store.set_consent(CONSENT_DENIED)
        event = store.record("memory", "write")
        assert event is None
    
    def test_record_blocked_when_revoked(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.set_consent(CONSENT_REVOKED)
        event = store.record("memory", "write")
        assert event is None
    
    def test_record_allowed_when_pending(self, store):
        # Pending state still records locally (pre-handshake accumulation)
        event = store.record("memory", "read")
        assert event is not None
    
    def test_events_persisted_to_file(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.record("memory", "write")
        store.record("filesystem", "lock")
        
        # Verify file exists and has content
        events_file = Path(TEST_BRAIN) / "pulse" / "events.jsonl"
        assert events_file.exists()
        
        with open(events_file) as f:
            lines = [l.strip() for l in f if l.strip()]
        
        # At least 2 real events (may have decoys too)
        assert len(lines) >= 2
    
    def test_event_count(self, store):
        store.set_consent(CONSENT_ALLOWED)
        for i in range(5):
            store.record("memory", "write")
        
        count = store.event_count()
        # At least 5 real events, possibly more with decoys
        assert count >= 5


# ============================================================
# SALT MANAGEMENT TESTS
# ============================================================

class TestSaltManager:
    def test_generate_pulse_id_is_stable_within_session(self, store):
        """Same salt → same pulse ID within a session."""
        salt_mgr = SaltManager(Path(TEST_BRAIN) / "pulse")
        id1 = salt_mgr.generate_pulse_id()
        id2 = salt_mgr.generate_pulse_id()
        assert id1 == id2  # Same salt, same machine proxy
        assert len(id1) == 16
    
    def test_monthly_salt_created_on_first_use(self, store):
        salt_mgr = SaltManager(Path(TEST_BRAIN) / "pulse")
        salt = salt_mgr.get_monthly_salt()
        assert len(salt) == 64  # 32 hex bytes
    
    def test_yearly_salt_created_on_first_use(self, store):
        salt_mgr = SaltManager(Path(TEST_BRAIN) / "pulse")
        salt = salt_mgr.get_yearly_salt()
        assert len(salt) == 64


# ============================================================
# AUDIT CLI TESTS (mcp pulse --view)
# ============================================================

class TestAuditView:
    def test_view_empty(self, store):
        events = store.view()
        assert events == []
    
    def test_view_returns_events(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.record("memory", "write")
        store.record("governance", "query")
        
        events = store.view()
        assert len(events) >= 2
        
        # Most recent first
        hubs = [e["hub"] for e in events if not e.get("is_decoy")]
        assert "memory" in hubs
        assert "governance" in hubs
    
    def test_view_summary_structure(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.record("memory", "write")
        
        summary = store.view_summary()
        assert "consent" in summary
        assert "total_events" in summary
        assert "hub_breakdown" in summary
        assert "salt_rotation" in summary
        assert summary["consent"] == CONSENT_ALLOWED
        assert summary["sharing_enabled"] is True


# ============================================================
# SHARE PAYLOAD TESTS (Attribution Wall)
# ============================================================

class TestSharePayload:
    def test_payload_blocked_when_denied(self, store):
        store.set_consent(CONSENT_DENIED)
        payload = store.prepare_payload()
        assert payload is None
    
    def test_payload_structure_when_allowed(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.record("memory", "write", {"count": 1})
        
        payload = store.prepare_payload()
        assert payload is not None
        assert "schema_version" in payload
        assert "pulse_id" in payload
        assert "events" in payload
        assert payload["transmission_note"].startswith("STUB")
    
    def test_payload_sanitizes_metadata(self, store):
        store.set_consent(CONSENT_ALLOWED)
        # Record with potentially sensitive metadata
        store.record("memory", "write", {
            "count": 1,
            "file_path": "/secret/path",  # Should be stripped
            "duration_ms": 42,  # Should be kept
        })
        
        payload = store.prepare_payload()
        events = payload["events"]
        real_events = [e for e in events if not e.get("is_decoy")]
        assert len(real_events) >= 1
        
        meta = real_events[0].get("metadata", {})
        assert "file_path" not in meta  # Stripped
        assert "duration_ms" in meta    # Kept


# ============================================================
# PURGE TESTS (Nuclear Option)
# ============================================================

class TestPurge:
    def test_purge_deletes_events(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.record("memory", "write")
        assert store.event_count() >= 1
        
        result = store.purge()
        assert "purged" in result.lower()
        assert store.event_count() == 0
    
    def test_purge_sets_consent_to_denied(self, store):
        store.set_consent(CONSENT_ALLOWED)
        store.purge()
        
        consent = store.get_consent()
        assert consent.state == CONSENT_DENIED


# ============================================================
# DIFFERENTIAL PRIVACY TESTS
# ============================================================

class TestDifferentialPrivacy:
    def test_decoy_events_injected_over_many_recordings(self, store):
        """Over 100 recordings, at least some decoys should appear."""
        store.set_consent(CONSENT_ALLOWED)
        
        for i in range(100):
            store.record("memory", "write")
        
        events = store.view(limit=10000)
        decoys = [e for e in events if e.get("is_decoy")]
        
        # With 10% probability, we expect ~10 decoys in 100 events
        # Allow for randomness: at least 1 decoy in 100 recordings
        assert len(decoys) >= 1, f"Expected at least 1 decoy in 100 recordings, got {len(decoys)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
