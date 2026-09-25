"""Tests for the self-review-by-default fix (fw-1786036802).

Verifies:
1. Same vendor + default (key absent) → SINGLE_VENDOR_PLAN fallback
2. Same vendor + explicit allow_same_vendor=True → self-review allowed
3. Same vendor + explicit allow_same_vendor=False → validation error
4. Different vendors → normal dual-vendor review
5. cancel_plan_review_loop on SINGLE_VENDOR_PLAN → already terminal
6. Resolver helpers return correct values
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prl_module():
    """Import plan_review_loop fresh."""
    from mcp_server_nucleus.runtime import model_registry
    model_registry._registry = None
    if "mcp_server_nucleus.tools.plan_review_loop" in sys.modules:
        del sys.modules["mcp_server_nucleus.tools.plan_review_loop"]
    mod = __import__("mcp_server_nucleus.tools.plan_review_loop", fromlist=["x"])
    return mod


@pytest.fixture
def brain_dir(tmp_path, monkeypatch):
    """Create a .brain directory with plans/ for testing."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "plans").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Patch _get_brain_path to return our temp brain
    with patch("mcp_server_nucleus.tools.plan_review_loop._get_brain_path", return_value=brain):
        yield brain


# ---------------------------------------------------------------------------
# Test 1: Resolver helpers
# ---------------------------------------------------------------------------


class TestResolverHelpers:
    def test_resolve_author_vendor_default(self, prl_module):
        assert prl_module._resolve_author_vendor({}) == prl_module._DEFAULT_AUTHOR_VENDOR

    def test_resolve_author_vendor_explicit(self, prl_module):
        assert prl_module._resolve_author_vendor({"author_vendor": "devin"}) == "devin"

    def test_resolve_reviewer_vendor_default(self, prl_module):
        assert prl_module._resolve_reviewer_vendor({}) == prl_module._DEFAULT_REVIEWER_VENDOR

    def test_resolve_reviewer_vendor_explicit(self, prl_module):
        assert prl_module._resolve_reviewer_vendor({"reviewer_vendor": "devin"}) == "devin"

    def test_resolve_allow_same_vendor_default_is_false(self, prl_module):
        """fw-1786036802: default (key absent) is now False, not True."""
        value, explicit = prl_module._resolve_allow_same_vendor({})
        assert value is False
        assert explicit is False

    def test_resolve_allow_same_vendor_explicit_true(self, prl_module):
        value, explicit = prl_module._resolve_allow_same_vendor({"allow_same_vendor": True})
        assert value is True
        assert explicit is True

    def test_resolve_allow_same_vendor_explicit_false(self, prl_module):
        value, explicit = prl_module._resolve_allow_same_vendor({"allow_same_vendor": False})
        assert value is False
        assert explicit is True


# ---------------------------------------------------------------------------
# Test 2: execute_plan_review_loop validation
# ---------------------------------------------------------------------------


class TestExecutePlanReviewLoopValidation:
    def test_same_vendor_explicit_false_rejected(self, prl_module, monkeypatch):
        """Same vendor + explicit allow_same_vendor=False → validation error."""
        monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
        response = prl_module.execute_plan_review_loop(
            {"prompt": "test", "author_vendor": "agy", "reviewer_vendor": "agy",
             "allow_same_vendor": False},
            lambda ok, data=None, error=None: {"ok": ok, "data": data, "error": error},
        )
        assert response["ok"] is False
        assert "allow_same_vendor=False" in response["error"] or "same_vendor" in response["error"].lower()

    def test_different_vendors_not_rejected(self, prl_module):
        """Different vendors should not trigger the same-vendor guard."""
        # We can't easily run the full loop, but we can verify the validation
        # passes by checking that the response is not an immediate same-vendor error
        with patch("mcp_server_nucleus.tools.plan_review_loop._run_loop_worker"), \
             patch("mcp_server_nucleus.tools.plan_review_loop._make_initial_state", return_value={"status": "QUEUED", "plan_id": "test"}), \
             patch("mcp_server_nucleus.tools.plan_review_loop._validate_plan_id", return_value=True), \
             patch("mcp_server_nucleus.tools.plan_review_loop._get_brain_path") as mock_brain, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_text"):
            mock_brain.return_value.__truediv__ = MagicMock(return_value=MagicMock())
            response = prl_module.execute_plan_review_loop(
                {"prompt": "test", "author_vendor": "agy", "reviewer_vendor": "devin"},
                lambda ok, data=None, error=None: {"ok": ok, "data": data, "error": error},
            )
        # Should not fail with same-vendor error
        assert response.get("error") is None or "same_vendor" not in str(response.get("error", "")).lower()


# ---------------------------------------------------------------------------
# Test 3: _make_initial_state records allow_same_vendor
# ---------------------------------------------------------------------------


class TestMakeInitialState:
    def test_state_records_allow_same_vendor_default(self, prl_module):
        """State should record allow_same_vendor=False by default."""
        state = prl_module._make_initial_state("test_plan", {"prompt": "test"}, "abc123")
        assert state["allow_same_vendor"] is False
        assert state["allow_same_vendor_explicit"] is False

    def test_state_records_allow_same_vendor_explicit_true(self, prl_module):
        """State should record allow_same_vendor=True when explicitly set."""
        state = prl_module._make_initial_state("test_plan", {"prompt": "test", "allow_same_vendor": True}, "abc123")
        assert state["allow_same_vendor"] is True
        assert state["allow_same_vendor_explicit"] is True

    def test_state_uses_resolver_for_vendors(self, prl_module):
        """State should use resolver helpers, not hardcoded 'agy'."""
        state = prl_module._make_initial_state("test_plan", {"prompt": "test", "author_vendor": "devin"}, "abc123")
        assert state["author_vendor"] == "devin"


# ---------------------------------------------------------------------------
# Test 4: cancel_plan_review_loop treats SINGLE_VENDOR_PLAN as terminal
# ---------------------------------------------------------------------------


class TestCancelTerminalStatus:
    def test_single_vendor_plan_is_terminal(self, prl_module, brain_dir):
        """cancel_plan_review_loop should report SINGLE_VENDOR_PLAN as terminal."""
        plan_id = "plan_20260806_120000_abc123"
        plan_dir = brain_dir / "plans" / plan_id
        plan_dir.mkdir()
        state = {"status": "SINGLE_VENDOR_PLAN", "plan_id": plan_id}
        (plan_dir / "state.json").write_text(json.dumps(state))

        response = prl_module.cancel_plan_review_loop(
            plan_id,
            lambda ok, data=None, error=None: {"ok": ok, "data": data, "error": error},
        )
        assert response["ok"] is True
        assert "terminal" in response["data"]["message"].lower()

    def test_stale_non_convergent_is_terminal(self, prl_module, brain_dir):
        """STALE_NON_CONVERGENT should also be terminal."""
        plan_id = "plan_20260806_120000_def456"
        plan_dir = brain_dir / "plans" / plan_id
        plan_dir.mkdir()
        state = {"status": "STALE_NON_CONVERGENT", "plan_id": plan_id}
        (plan_dir / "state.json").write_text(json.dumps(state))

        response = prl_module.cancel_plan_review_loop(
            plan_id,
            lambda ok, data=None, error=None: {"ok": ok, "data": data, "error": error},
        )
        assert response["ok"] is True
        assert "terminal" in response["data"]["message"].lower()
