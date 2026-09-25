"""Tests for model_registry integration in plan_review_loop._dispatch_vendor.

Verifies:
1. Dynamic model selection via select_model when no explicit model is passed
2. Graceful degradation when model_registry is unavailable
3. Model fallback on dispatch failure (tries next model in chain)
4. Health registry records success/failure outcomes
"""
import importlib
import sys
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prl_module():
    """Import plan_review_loop fresh, with a clean model_registry singleton."""
    from mcp_server_nucleus.runtime import model_registry
    model_registry._registry = None
    if "mcp_server_nucleus.tools.plan_review_loop" in sys.modules:
        del sys.modules["mcp_server_nucleus.tools.plan_review_loop"]
    mod = importlib.import_module("mcp_server_nucleus.tools.plan_review_loop")
    return mod


def _reset_registry():
    from mcp_server_nucleus.runtime import model_registry
    model_registry._registry = None


# ---------------------------------------------------------------------------
# Test 1: select_model is called when no explicit model is passed
# ---------------------------------------------------------------------------


def test_select_model_called_when_no_explicit_model(prl_module):
    """When model=None, _dispatch_vendor should call select_model."""
    _reset_registry()

    fake_scored = MagicMock()
    fake_scored.vendor = "agy"
    fake_scored.model_id = "gemini-2.5-pro"

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=fake_scored) as mock_select, \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "ok", "produced_output": True, "result": "plan output",
             "model_id": "gemini-2.5-pro", "duration": 5,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="gemini-2.5-pro"):

        result = prl_module._dispatch_vendor("agy", "test prompt", "test_ref")

    assert result["success"] is True
    assert result["output"] == "plan output"
    mock_select.assert_called_once_with(task_type="plan_author")


def test_explicit_model_skips_select_model(prl_module):
    """When model is explicitly passed, select_model should NOT be called."""
    _reset_registry()

    with patch("mcp_server_nucleus.runtime.model_registry.select_model") as mock_select, \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "ok", "produced_output": True, "result": "output",
             "model_id": "custom-model", "duration": 3,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="custom-model"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref", model="custom-model")

    assert result["success"] is True
    mock_select.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Graceful degradation when model_registry is unavailable
# ---------------------------------------------------------------------------


def test_graceful_degradation_when_select_model_raises(prl_module):
    """If select_model raises, _dispatch_vendor should still work with default."""
    _reset_registry()

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", side_effect=RuntimeError("boom")), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "ok", "produced_output": True, "result": "fallback output",
             "model_id": "default-model", "duration": 2,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="default-model"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref")

    assert result["success"] is True
    assert result["output"] == "fallback output"


# ---------------------------------------------------------------------------
# Test 3: Model fallback on dispatch failure
# ---------------------------------------------------------------------------


def test_fallback_tried_on_dispatch_failure(prl_module):
    """When the first dispatch fails, _try_vendor_fallback should be attempted."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    fake_next = MagicMock()
    fake_next.vendor = "devin"
    fake_next.model_id = "devin-model-1"

    call_count = {"n": 0}

    def mock_dispatch(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"status": "error", "produced_output": False, "result": "",
                    "error": "rate limited", "model_id": "gemini-2.5-pro", "duration": 1}
        return {"status": "ok", "produced_output": True, "result": "fallback plan",
                "model_id": "devin-model-1", "duration": 4}

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[
             model_registry.ModelSpec(vendor="devin", model_id="devin-model-1"),
         ]), \
         patch("mcp_server_nucleus.runtime.model_registry.next_model_after_failure", return_value=fake_next), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", side_effect=mock_dispatch), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref")

    assert result["success"] is True
    assert result["output"] == "fallback plan"
    assert call_count["n"] == 2  # First failed, second (fallback) succeeded


def test_fallback_exhausted_returns_original_failure(prl_module):
    """When all fallback attempts fail, return the original failure."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    fake_next = MagicMock()
    fake_next.vendor = "devin"
    fake_next.model_id = "devin-model-1"

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[
             model_registry.ModelSpec(vendor="devin", model_id="devin-model-1"),
         ]), \
         patch("mcp_server_nucleus.runtime.model_registry.next_model_after_failure", return_value=fake_next), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "error", "produced_output": False, "result": "",
             "error": "all models down", "model_id": "x", "duration": 0,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref")

    assert result["success"] is False
    assert "status=error" in result["error"] or "all models down" in result["error"]


def test_no_fallback_when_no_models_discovered(prl_module):
    """When discover_models returns empty, fallback returns None gracefully."""
    _reset_registry()

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[]), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "error", "produced_output": False, "result": "",
             "error": "vendor down", "model_id": "x", "duration": 0,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref")

    assert result["success"] is False


# ---------------------------------------------------------------------------
# Test 4: Health registry records outcomes
# ---------------------------------------------------------------------------


def test_success_recorded_in_registry(prl_module):
    """On successful dispatch, record_success should be called."""
    _reset_registry()

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "ok", "produced_output": True, "result": "output",
             "model_id": "test-model", "duration": 1,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="test-model"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref")

    assert result["success"] is True
    from mcp_server_nucleus.runtime import model_registry
    reg = model_registry.get_registry()
    health = reg.get("agy", "test-model")
    assert health.total_successes >= 1


def test_failure_recorded_in_registry_on_fallback(prl_module):
    """On failed dispatch with fallback, record_failure should be called."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    fake_next = MagicMock()
    fake_next.vendor = "devin"
    fake_next.model_id = "devin-model-1"

    call_count = {"n": 0}

    def mock_dispatch(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"status": "error", "produced_output": False, "result": "",
                    "error": "rate limited", "model_id": "agy-model", "duration": 1}
        return {"status": "ok", "produced_output": True, "result": "ok",
                "model_id": "devin-model-1", "duration": 1}

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[
             model_registry.ModelSpec(vendor="devin", model_id="devin-model-1"),
         ]), \
         patch("mcp_server_nucleus.runtime.model_registry.next_model_after_failure", return_value=fake_next), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", side_effect=mock_dispatch), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor("agy", "prompt", "ref")

    assert result["success"] is True
    reg = model_registry.get_registry()
    assert any(h.total_failures > 0 for h in reg._models.values())


# ---------------------------------------------------------------------------
# Test 5: Reviewer model fallback on dispatch failure (task_type="plan_reviewer")
# ---------------------------------------------------------------------------


def test_reviewer_select_model_called_with_plan_reviewer_task_type(prl_module):
    """For task_type='plan_reviewer', select_model must be invoked with that
    task_type (not the default 'plan_author')."""
    _reset_registry()

    fake_scored = MagicMock()
    fake_scored.vendor = "agy"
    fake_scored.model_id = "gemini-3.1-pro-high"

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=fake_scored) as mock_select, \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "ok", "produced_output": True, "result": "review output",
             "model_id": "gemini-3.1-pro-high", "duration": 6,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="gemini-3.1-pro-high"):

        result = prl_module._dispatch_vendor(
            "agy", "review prompt", "ref", task_type="plan_reviewer",
        )

    assert result["success"] is True
    assert result["output"] == "review output"
    mock_select.assert_called_once_with(task_type="plan_reviewer")


def test_reviewer_fallback_tried_on_dispatch_failure(prl_module):
    """When the reviewer dispatch fails, _try_vendor_fallback should be
    attempted and the fallback chain should be consulted with
    task_type='plan_reviewer'."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    fake_next = MagicMock()
    fake_next.vendor = "devin"
    fake_next.model_id = "claude-opus-4-6-thinking"
    fake_next.score = 0.90

    call_count = {"n": 0}

    def mock_dispatch(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"status": "error", "produced_output": False, "result": "",
                    "error": "rate limited", "model_id": "gemini-3.1-pro-high",
                    "duration": 1}
        return {"status": "ok", "produced_output": True, "result": "review fallback",
                "model_id": "claude-opus-4-6-thinking", "duration": 4}

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[
             model_registry.ModelSpec(vendor="devin", model_id="claude-opus-4-6-thinking"),
         ]), \
         patch("mcp_server_nucleus.runtime.model_registry.next_model_after_failure", return_value=fake_next) as mock_next, \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", side_effect=mock_dispatch), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor(
            "agy", "review prompt", "ref", task_type="plan_reviewer",
        )

    assert result["success"] is True
    assert result["output"] == "review fallback"
    assert call_count["n"] == 2  # First failed, second (fallback) succeeded
    # next_model_after_failure must have been called with the reviewer task_type
    # (passed as the 3rd positional arg in _try_vendor_fallback)
    assert mock_next.call_count >= 1
    args, _ = mock_next.call_args
    assert args[2] == "plan_reviewer"


def test_reviewer_fallback_exhausted_returns_original_failure(prl_module):
    """When all reviewer fallback attempts fail, the original failure is
    returned (not a fallback success)."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    fake_next = MagicMock()
    fake_next.vendor = "devin"
    fake_next.model_id = "claude-opus-4-6-thinking"
    fake_next.score = 0.90

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[
             model_registry.ModelSpec(vendor="devin", model_id="claude-opus-4-6-thinking"),
         ]), \
         patch("mcp_server_nucleus.runtime.model_registry.next_model_after_failure", return_value=fake_next), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "error", "produced_output": False, "result": "",
             "error": "all reviewer models down", "model_id": "x", "duration": 0,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor(
            "agy", "review prompt", "ref", task_type="plan_reviewer",
        )

    assert result["success"] is False
    assert "all reviewer models down" in result["error"] or "status=error" in result["error"]


def test_reviewer_no_fallback_when_no_models_discovered(prl_module):
    """When discover_models returns empty for the reviewer path, fallback is
    skipped and the original failure is returned."""
    _reset_registry()

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[]), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={
             "status": "error", "produced_output": False, "result": "",
             "error": "vendor down", "model_id": "x", "duration": 0,
         }), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor(
            "agy", "review prompt", "ref", task_type="plan_reviewer",
        )

    assert result["success"] is False


def test_reviewer_failure_recorded_in_registry_on_fallback(prl_module):
    """On a failed reviewer dispatch that triggers a successful fallback, the
    original failure is recorded in the health registry."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    fake_next = MagicMock()
    fake_next.vendor = "devin"
    fake_next.model_id = "claude-opus-4-6-thinking"
    fake_next.score = 0.90

    call_count = {"n": 0}

    def mock_dispatch(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"status": "error", "produced_output": False, "result": "",
                    "error": "rate limited", "model_id": "gemini-3.1-pro-high",
                    "duration": 1}
        return {"status": "ok", "produced_output": True, "result": "review ok",
                "model_id": "claude-opus-4-6-thinking", "duration": 1}

    with patch("mcp_server_nucleus.runtime.model_registry.select_model", return_value=None), \
         patch("mcp_server_nucleus.runtime.model_registry.discover_models", return_value=[
             model_registry.ModelSpec(vendor="devin", model_id="claude-opus-4-6-thinking"),
         ]), \
         patch("mcp_server_nucleus.runtime.model_registry.next_model_after_failure", return_value=fake_next), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", side_effect=mock_dispatch), \
         patch("mcp_server_nucleus.runtime.vendor_dispatch.resolve_model", return_value="resolved"):

        result = prl_module._dispatch_vendor(
            "agy", "review prompt", "ref", task_type="plan_reviewer",
        )

    assert result["success"] is True
    reg = model_registry.get_registry()
    assert any(h.total_failures > 0 for h in reg._models.values())


# ---------------------------------------------------------------------------
# Test 6: _ensure_distinct_reviewer — different vendors, model unchanged
# ---------------------------------------------------------------------------


def test_ensure_distinct_reviewer_different_vendors_unchanged(prl_module):
    """When author and reviewer are different vendors, the reviewer model is
    returned unchanged with a ``None`` note (no substitution needed)."""
    model, note = prl_module._ensure_distinct_reviewer("agy", None, "devin", None)
    assert model is None
    assert note is None


def test_ensure_distinct_reviewer_same_vendor_both_none_gets_alternative(prl_module):
    """When author and reviewer share a vendor and both models are ``None``
    (i.e. equal), ``_ensure_distinct_reviewer`` should substitute the first
    available alternative from ``discover_models()`` and return a non-empty
    note describing the substitution."""
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    with patch(
        "mcp_server_nucleus.runtime.model_registry.discover_models",
        return_value=[
            model_registry.ModelSpec(vendor="agy", model_id="gemini-2.5-pro"),
            model_registry.ModelSpec(vendor="agy", model_id="gemini-2.5-flash"),
        ],
    ):
        model, note = prl_module._ensure_distinct_reviewer("agy", None, "agy", None)

    assert model == "gemini-2.5-pro"
    assert note is not None
    assert note != ""
    assert "gemini-2.5-pro" in note
    assert "agy" in note


def test_ensure_distinct_reviewer_same_vendor_no_alternative_notes_same_model(prl_module):
    """When author and reviewer share a vendor AND model, and
    ``discover_models()`` returns only the author's own model (no alternative),
    ``_ensure_distinct_reviewer`` must return the model UNCHANGED and emit a
    non-empty note stating plainly that no distinct reviewer model was
    available and the review is same-model.

    This is the control that stops a silent self-review from passing as
    acceptable: the caller cannot mistake the result for a successful
    substitution.
    """
    from mcp_server_nucleus.runtime import model_registry
    _reset_registry()

    with patch(
        "mcp_server_nucleus.runtime.model_registry.discover_models",
        return_value=[
            model_registry.ModelSpec(vendor="agy", model_id="gemini-2.5-pro"),
        ],
    ):
        model, note = prl_module._ensure_distinct_reviewer(
            "agy", "gemini-2.5-pro", "agy", "gemini-2.5-pro",
        )

    assert model == "gemini-2.5-pro"  # unchanged — no alternative found
    assert note is not None
    assert note != ""
    assert "same-model" in note
    assert "no alternative available" in note


def test_ensure_distinct_reviewer_same_vendor_already_distinct_unchanged(prl_module):
    """When author and reviewer share a vendor but already use distinct
    models, ``_ensure_distinct_reviewer`` must return the reviewer model
    UNCHANGED with a ``None`` note (no substitution needed)."""
    model, note = prl_module._ensure_distinct_reviewer(
        "agy", "gemini-2.5-pro", "agy", "gemini-2.5-flash",
    )
    assert model == "gemini-2.5-flash"
    assert note is None
