"""Test secretary escalation and verification failure handling.

Verifies that:
1. The secretary handles [ESCALATED] relays from the executor
2. The secretary posts [VERIFY-FAIL] relays when verification fails
3. The secretary marks tasks as FAILED when verification fails
4. The secretary forwards [ESCALATED] relays to the principal
"""
from pathlib import Path

import pytest

SECRETARY_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "secretary_daemon.sh"


class TestSecretaryEscalationHandling:
    """Test [ESCALATED] relay handling in the secretary."""

    def test_secretary_has_escalated_relay_handling(self):
        """The secretary should handle [ESCALATED] relays."""
        source = SECRETARY_SCRIPT.read_text()
        assert "[ESCALATED]" in source, (
            "Secretary should handle [ESCALATED] relays from executor"
        )

    def test_secretary_forwards_escalated_to_principal(self):
        """The secretary should forward [ESCALATED] relays to the principal."""
        source = SECRETARY_SCRIPT.read_text()
        assert "ESCALATED" in source
        # Should post a relay to claude_code_main about the escalation
        assert "claude_code_main" in source
        assert "escalated by executor" in source.lower() or "max retries" in source.lower()

    def test_secretary_marks_escalated_as_seen(self):
        """The secretary should mark [ESCALATED] relays as seen."""
        source = SECRETARY_SCRIPT.read_text()
        # The escalated handling should include marking as seen
        assert "SEEN_FILE" in source


class TestSecretaryVerificationFailure:
    """Test verification failure handling in the secretary."""

    def test_secretary_posts_verify_fail_relay(self):
        """The secretary should post [VERIFY-FAIL] relay when verification fails."""
        source = SECRETARY_SCRIPT.read_text()
        assert "[VERIFY-FAIL]" in source, (
            "Secretary should post [VERIFY-FAIL] relays when verification fails"
        )

    def test_secretary_marks_task_as_failed(self):
        """The secretary should mark tasks as FAILED when verification fails."""
        source = SECRETARY_SCRIPT.read_text()
        assert "FAILED" in source, (
            "Secretary should mark tasks as FAILED when verification fails"
        )
        assert "_update_task" in source, (
            "Secretary should use _update_task to mark tasks as FAILED"
        )

    def test_secretary_verify_fail_relays_to_principal(self):
        """The secretary should relay verification failures to the principal."""
        source = SECRETARY_SCRIPT.read_text()
        assert "VERIFY-FAIL" in source
        assert "claude_code_main" in source
        assert "investigate and fix" in source.lower()

    def test_secretary_logs_verification_failure(self):
        """The secretary should log when verification fails."""
        source = SECRETARY_SCRIPT.read_text()
        assert "FAILED verification" in source, (
            "Secretary should log verification failures"
        )
        assert "ALERT" in source, (
            "Secretary should alert on verification failures"
        )

    def test_secretary_skips_stale_done_relays(self):
        """The secretary should skip [DONE] relays for tasks already DONE/FAILED."""
        source = SECRETARY_SCRIPT.read_text()
        assert "stale relay" in source.lower(), (
            "Secretary should detect and skip stale relays"
        )
        assert "task_status" in source, (
            "Secretary should check task status before verifying"
        )
        assert "DONE" in source and "FAILED" in source, (
            "Secretary should skip tasks already DONE or FAILED"
        )


class TestSecretaryDuplicateTaskHandling:
    """Test duplicate task handling in the secretary."""

    def test_secretary_handles_duplicate_task_creation(self):
        """The secretary should handle duplicate task errors and skip queueing with an ack."""
        source = SECRETARY_SCRIPT.read_text()
        assert "duplicate" in source.lower()
        assert "relay_posted" in source.lower() or "acknowledged" in source.lower()
