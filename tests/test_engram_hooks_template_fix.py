"""Tests for the unfilled-template-placeholder fix (fw-1786166399).

Verifies that _fill_template returns (str, had_missing) and that
_create_auto_engram rejects templates with missing fields instead of
writing garbage like 'Session started — ? tasks loaded'.
"""
import sys
import pytest


@pytest.fixture
def engram_mod():
    """Import engram_hooks fresh."""
    if "mcp_server_nucleus.runtime.engram_hooks" in sys.modules:
        del sys.modules["mcp_server_nucleus.runtime.engram_hooks"]
    return __import__("mcp_server_nucleus.runtime.engram_hooks", fromlist=["x"])


# ---------------------------------------------------------------------------
# _fill_template tests
# ---------------------------------------------------------------------------


class TestFillTemplate:
    def test_all_fields_present(self, engram_mod):
        desc, missing = engram_mod._fill_template(
            "Session started — {task_count} tasks loaded", {"task_count": 5}
        )
        assert desc == "Session started — 5 tasks loaded"
        assert missing is False

    def test_missing_field_produces_question_mark(self, engram_mod):
        desc, missing = engram_mod._fill_template(
            "Session started — {task_count} tasks loaded", {}
        )
        assert "?" in desc
        assert missing is True

    def test_partial_missing_detected(self, engram_mod):
        """One field missing out of several → had_missing=True."""
        desc, missing = engram_mod._fill_template(
            "DELTA recorded for {task_id}: {delta_type} — {description}",
            {"task_id": "t1", "delta_type": "code"},
        )
        assert "?" in desc
        assert missing is True

    def test_all_fields_present_no_missing(self, engram_mod):
        desc, missing = engram_mod._fill_template(
            "GROUND verified task {task_id}: {verdict} ({tiers_passed} tiers passed)",
            {"task_id": "t1", "verdict": "PASS", "tiers_passed": 4},
        )
        assert "PASS" in desc
        assert "4" in desc
        assert missing is False

    def test_none_field_renders_none_not_missing(self, engram_mod):
        """A None field renders as 'None' — not the '?' garbage pattern."""
        desc, missing = engram_mod._fill_template(
            "GROUND verified task {task_id}: {verdict} ({tiers_passed} tiers passed)",
            {"task_id": "t1", "verdict": None, "tiers_passed": 2},
        )
        assert "None" in desc
        assert missing is False  # field was present, just None

    def test_fallback_on_format_error(self, engram_mod):
        """If template.format_map fails entirely, fall back to data fields."""
        # _SafeDict prevents format_map from raising, so all missing fields
        # render as '?'. The fallback only triggers on actual exceptions
        # (e.g. malformed format string with stray braces).
        desc, missing = engram_mod._fill_template(
            "Bad {template} {with} {invalid}", {"description": "fallback text"}
        )
        # All three fields are missing → '?' rendered, had_missing=True
        assert "?" in desc
        assert missing is True


# ---------------------------------------------------------------------------
# _create_auto_engram tests
# ---------------------------------------------------------------------------


class TestCreateAutoEngram:
    def test_missing_fields_returns_none(self, engram_mod, tmp_path, monkeypatch):
        """fw-1786166399: missing template fields → return None, not garbage."""
        # Mock MemoryPipeline to avoid actually writing
        class MockPipeline:
            def __init__(self, brain_path):
                pass
            def process(self, **kwargs):
                return {"key": kwargs.get("key"), "text": kwargs.get("text")}

        monkeypatch.setattr(engram_mod, "MemoryPipeline", MockPipeline, raising=False)
        # Patch the import inside _create_auto_engram
        import mcp_server_nucleus.runtime.memory_pipeline as mp
        monkeypatch.setattr(mp, "MemoryPipeline", MockPipeline, raising=False)

        result = engram_mod._create_auto_engram(
            "session_started", {}, tmp_path / ".brain"
        )
        # Should return None because task_count is missing
        assert result is None

    def test_all_fields_present_creates_engram(self, engram_mod, tmp_path, monkeypatch):
        """All fields present → engram is created."""
        class MockPipeline:
            def __init__(self, brain_path):
                pass
            def process(self, **kwargs):
                return {"key": kwargs.get("key"), "text": kwargs.get("text")}

        monkeypatch.setattr(engram_mod, "MemoryPipeline", MockPipeline, raising=False)
        import mcp_server_nucleus.runtime.memory_pipeline as mp
        monkeypatch.setattr(mp, "MemoryPipeline", MockPipeline, raising=False)

        result = engram_mod._create_auto_engram(
            "session_started", {"task_count": 5}, tmp_path / ".brain"
        )
        # Should NOT return None — all fields are present
        assert result is not None
        assert "5" in result["text"]
