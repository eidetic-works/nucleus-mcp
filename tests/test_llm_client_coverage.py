"""
Comprehensive coverage tests for runtime/llm_client.py.

All external calls (HTTP, LLM API calls) are mocked — no real network.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from mcp_server_nucleus.runtime import llm_client as lc


# ---------------------------------------------------------------------------
# Helpers for lazy-imported modules (anthropic, openai)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_anthropic_module():
    """Inject a mock 'anthropic' module into sys.modules for lazy import."""
    mock_mod = MagicMock()
    mock_client = MagicMock()
    mock_mod.Anthropic.return_value = mock_client
    old = sys.modules.get("anthropic")
    sys.modules["anthropic"] = mock_mod
    try:
        yield mock_mod, mock_client
    finally:
        if old is not None:
            sys.modules["anthropic"] = old
        else:
            sys.modules.pop("anthropic", None)


@pytest.fixture
def mock_openai_module():
    """Inject a mock 'openai' module into sys.modules for lazy import."""
    mock_mod = MagicMock()
    mock_client = MagicMock()
    mock_mod.OpenAI.return_value = mock_client
    old = sys.modules.get("openai")
    sys.modules["openai"] = mock_mod
    try:
        yield mock_mod, mock_client
    finally:
        if old is not None:
            sys.modules["openai"] = old
        else:
            sys.modules.pop("openai", None)


from contextlib import contextmanager

@contextmanager
def _mock_anthropic():
    """Context manager that injects a mock anthropic module into sys.modules."""
    mock_mod = MagicMock()
    old = sys.modules.get("anthropic")
    sys.modules["anthropic"] = mock_mod
    try:
        yield mock_mod
    finally:
        if old is not None:
            sys.modules["anthropic"] = old
        else:
            sys.modules.pop("anthropic", None)


@contextmanager
def _mock_openai():
    """Context manager that injects a mock openai module into sys.modules."""
    mock_mod = MagicMock()
    old = sys.modules.get("openai")
    sys.modules["openai"] = mock_mod
    try:
        yield mock_mod
    finally:
        if old is not None:
            sys.modules["openai"] = old
        else:
            sys.modules.pop("openai", None)


@contextmanager
def _mock_genai_legacy():
    """Context manager that injects a mock google.generativeai module.

    Also sets genai_legacy on the llm_client module namespace since the
    original import may have failed (HAS_LEGACY=False at import time).
    """
    mock_mod = MagicMock()
    old_sys = sys.modules.get("google.generativeai")
    sys.modules["google.generativeai"] = mock_mod
    old_attr = getattr(lc, "genai_legacy", None)
    setattr(lc, "genai_legacy", mock_mod)
    try:
        yield mock_mod
    finally:
        if old_sys is not None:
            sys.modules["google.generativeai"] = old_sys
        else:
            sys.modules.pop("google.generativeai", None)
        if old_attr is not None:
            setattr(lc, "genai_legacy", old_attr)
        else:
            delattr(lc, "genai_legacy")


# ---------------------------------------------------------------------------
# get_active_sdk
# ---------------------------------------------------------------------------

class TestGetActiveSdk:
    def test_returns_new_or_legacy_or_none(self):
        result = lc.get_active_sdk()
        assert result in ("NEW", "LEGACY", "NONE")


# ---------------------------------------------------------------------------
# LLMTier
# ---------------------------------------------------------------------------

class TestLLMTier:
    def test_enum_values(self):
        assert lc.LLMTier.PREMIUM.value == "premium"
        assert lc.LLMTier.STANDARD.value == "standard"
        assert lc.LLMTier.ECONOMY.value == "economy"
        assert lc.LLMTier.LOCAL_PAID.value == "local_paid"
        assert lc.LLMTier.LOCAL_FREE.value == "local_free"

    def test_from_string(self):
        assert lc.LLMTier("premium") == lc.LLMTier.PREMIUM
        assert lc.LLMTier("local_free") == lc.LLMTier.LOCAL_FREE


# ---------------------------------------------------------------------------
# TierRouter
# ---------------------------------------------------------------------------

class TestTierRouter:
    def test_route_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NUCLEUS_LLM_TIER", None)
            tier = lc.TierRouter.route()
        assert tier == lc.LLMTier.STANDARD

    def test_route_critical(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="CRITICAL")
        assert tier == lc.LLMTier.PREMIUM

    def test_route_testing(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="TESTING")
        assert tier == lc.LLMTier.LOCAL_FREE

    def test_route_research(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="RESEARCH", budget_mode="balanced")
        assert tier == lc.LLMTier.STANDARD

    def test_route_background_spartan(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="BACKGROUND", budget_mode="spartan")
        # BACKGROUND maps to ECONOMY, which is in spartan budget
        assert tier == lc.LLMTier.ECONOMY

    def test_route_background_premium(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="BACKGROUND", budget_mode="premium")
        # BACKGROUND maps to ECONOMY, which is in premium budget
        assert tier == lc.LLMTier.ECONOMY

    def test_route_unknown_job(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="UNKNOWN")
        assert tier == lc.LLMTier.STANDARD

    def test_route_empty_job(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="")
        assert tier == lc.LLMTier.STANDARD

    def test_route_none_job(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type=None)
        assert tier == lc.LLMTier.STANDARD

    def test_route_forced_tier_valid(self):
        with patch.dict(os.environ, {"NUCLEUS_LLM_TIER": "economy"}):
            tier = lc.TierRouter.route(job_type="CRITICAL")
        assert tier == lc.LLMTier.ECONOMY

    def test_route_forced_tier_invalid(self):
        with patch.dict(os.environ, {"NUCLEUS_LLM_TIER": "invalid_tier"}):
            tier = lc.TierRouter.route(job_type="CRITICAL")
        # Falls through to CRITICAL → PREMIUM
        assert tier == lc.LLMTier.PREMIUM

    def test_route_orchestration(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        tier = lc.TierRouter.route(job_type="ORCHESTRATION")
        assert tier == lc.LLMTier.STANDARD

    def test_route_budget_not_containing_base(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        # RESEARCH maps to STANDARD, which is in balanced budget
        # Use spartan budget: [LOCAL_FREE, ECONOMY, STANDARD]
        # STANDARD is in spartan, so it should return STANDARD
        tier = lc.TierRouter.route(job_type="RESEARCH", budget_mode="spartan")
        assert tier == lc.LLMTier.STANDARD

    def test_route_budget_not_containing_base_fallback(self):
        os.environ.pop("NUCLEUS_LLM_TIER", None)
        # BACKGROUND maps to ECONOMY
        # spartan = [LOCAL_FREE, ECONOMY, STANDARD] → ECONOMY is in it
        tier = lc.TierRouter.route(job_type="BACKGROUND", budget_mode="spartan")
        assert tier == lc.LLMTier.ECONOMY

    def test_get_config(self):
        config = lc.TierRouter.get_config(lc.LLMTier.PREMIUM)
        assert "model" in config
        assert "platform" in config
        assert config["platform"] == "vertex"

    def test_get_config_unknown_tier(self):
        config = lc.TierRouter.get_config(MagicMock())
        # Falls back to STANDARD config
        assert config == lc.TierRouter.TIER_CONFIGS[lc.LLMTier.STANDARD]

    def test_get_fallback(self):
        fallback = lc.TierRouter.get_fallback(lc.LLMTier.PREMIUM)
        assert fallback == lc.LLMTier.STANDARD

    def test_get_fallback_last_tier(self):
        fallback = lc.TierRouter.get_fallback(lc.LLMTier.LOCAL_FREE)
        assert fallback is None

    def test_get_fallback_unknown_tier(self):
        fallback = lc.TierRouter.get_fallback(MagicMock())
        assert fallback is None

    def test_tier_configs_complete(self):
        for tier in lc.LLMTier:
            config = lc.TierRouter.get_config(tier)
            assert "model" in config
            assert "platform" in config
            assert "cost_level" in config
            assert "description" in config

    def test_job_routing_complete(self):
        for job in ["CRITICAL", "RESEARCH", "ORCHESTRATION", "BACKGROUND", "TESTING"]:
            assert job in lc.TierRouter.JOB_ROUTING

    def test_budget_modes_complete(self):
        for mode in ["spartan", "balanced", "premium"]:
            assert mode in lc.TierRouter.BUDGET_MODES
            assert len(lc.TierRouter.BUDGET_MODES[mode]) == 3


# ---------------------------------------------------------------------------
# DualEngineLLM
# ---------------------------------------------------------------------------

class TestDualEngineLLM:
    def test_init_with_explicit_tier_local_free(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        # Remove proxy port file if exists
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
        assert llm.tier == lc.LLMTier.LOCAL_FREE
        assert llm.engine == "NEW"
        assert llm.api_key == "test-key"

    def test_init_with_job_type(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(job_type="TESTING")
        assert llm.tier == lc.LLMTier.LOCAL_FREE

    def test_init_default_tier(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM()
        assert llm.tier == lc.LLMTier.STANDARD

    def test_init_no_api_key_local_tier_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        monkeypatch.delenv("FORCE_VERTEX", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai"):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)

    def test_init_with_proxy_url(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("GEMINI_API_BASE_URL", "http://127.0.0.1:8080/v1")
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
        assert llm.engine == "NEW"
        mock_genai.Client.assert_called_once()

    def test_init_with_proxy_port_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        # Create proxy port file
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        proxy_file.write_text("9090")
        try:
            with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
                 patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
                mock_genai.Client.return_value = MagicMock()
                llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            assert llm.engine == "NEW"
        finally:
            proxy_file.unlink(missing_ok=True)

    def test_init_vertex_mode(self, monkeypatch):
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.setenv("GCP_LOCATION", "us-central1")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.PREMIUM)
        assert llm.engine == "NEW"

    def test_init_vertex_missing_project_raises(self, monkeypatch):
        monkeypatch.setenv("FORCE_VERTEX", "1")
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", False), \
             patch("mcp_server_nucleus.runtime.llm_client.genai"):
            # ValueError is caught internally, falls through to ImportError
            with pytest.raises(ImportError, match="Could not initialize"):
                lc.DualEngineLLM(tier=lc.LLMTier.STANDARD)

    def test_init_genai_fails_falls_to_legacy(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             _mock_genai_legacy() as mock_legacy:
            mock_genai.Client.side_effect = Exception("genai init failed")
            mock_model = MagicMock()
            mock_legacy.GenerativeModel.return_value = mock_model
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
        assert llm.engine == "LEGACY"

    def test_init_both_sdks_fail_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             _mock_genai_legacy() as mock_legacy:
            mock_genai.Client.side_effect = Exception("genai failed")
            mock_legacy.GenerativeModel.side_effect = Exception("legacy failed")
            with pytest.raises(ImportError, match="Could not initialize"):
                lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)

    def test_init_no_sdks_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", False), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", False):
            with pytest.raises(ImportError, match="Could not initialize"):
                lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)

    def test_init_legacy_model_name_mapping(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             _mock_genai_legacy() as mock_legacy:
            mock_genai.Client.side_effect = Exception("fail")
            mock_legacy.GenerativeModel.return_value = MagicMock()
            llm = lc.DualEngineLLM(model_name="gemini-2.0-flash", tier=lc.LLMTier.LOCAL_FREE)
        # Legacy SDK remaps 2.0 models to 1.5-flash
        assert llm.model_name == "gemini-1.5-flash"

    def test_generate_content_new_engine(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "Hello world"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.generate_content("test prompt")
        assert result == mock_resp
        mock_client.models.generate_content.assert_called_once()

    def test_generate_content_with_system_instruction(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(
                tier=lc.LLMTier.LOCAL_FREE,
                system_instruction="You are helpful"
            )
            result = llm.generate_content("test")
        assert result == mock_resp

    def test_generate_content_with_tools(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            tools = {"function_declarations": [{"name": "test_tool"}]}
            result = llm.generate_content("test", tools=tools)
        assert result == mock_resp

    def test_generate_content_with_tools_list(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             patch("mcp_server_nucleus.runtime.llm_client.types") as mock_types:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            mock_types.GenerateContentConfig.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            tools = [{"name": "tool1"}]
            result = llm.generate_content("test", tools=tools)
        assert result == mock_resp

    def test_generate_content_with_tool_config(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             patch("mcp_server_nucleus.runtime.llm_client.types") as mock_types:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            mock_types.GenerateContentConfig.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.generate_content("test", tool_config={"mode": "AUTO"})
        assert result == mock_resp

    def test_generate_content_error_429(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            with pytest.raises(Exception, match="429"):
                llm.generate_content("test")

    def test_generate_content_error_generic(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("something went wrong")
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            with pytest.raises(Exception, match="something went wrong"):
                llm.generate_content("test")

    def test_generate_vision_new_engine(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        # Create a test image
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             patch("mcp_server_nucleus.runtime.llm_client.types") as mock_types:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "image description"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            mock_types.Part.from_bytes.return_value = MagicMock()
            mock_types.Part.from_text.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.generate_vision([str(img)], "describe this")
        assert result == mock_resp

    def test_generate_vision_legacy_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             _mock_genai_legacy() as mock_legacy:
            mock_genai.Client.side_effect = Exception("fail")
            mock_legacy.GenerativeModel.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            with pytest.raises(RuntimeError, match="google-genai NEW SDK"):
                llm.generate_vision(["img.png"], "desc")

    def test_embed_content_new_engine(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
            mock_client.models.embed_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.embed_content("test text")
        assert result == {"embedding": [0.1, 0.2, 0.3]}

    def test_embed_content_no_embeddings(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.embeddings = []
            mock_client.models.embed_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.embed_content("test text")
        assert result == {"embedding": []}

    def test_embed_content_with_title(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.embeddings = [MagicMock(values=[0.1])]
            mock_client.models.embed_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.embed_content("test", title="My Title")
        assert result == {"embedding": [0.1]}

    def test_embed_content_error(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.models.embed_content.side_effect = Exception("embed failed")
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            with pytest.raises(Exception, match="embed failed"):
                llm.embed_content("test")

    def test_stream_content_new_engine(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.text = "Hello "
            chunk2 = MagicMock()
            chunk2.text = "world"
            mock_client.models.generate_content_stream.return_value = iter([chunk1, chunk2])
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            chunks = list(llm.stream_content("test"))
        assert chunks == ["Hello ", "world"]

    def test_stream_content_fallback_on_error(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.models.generate_content_stream.side_effect = Exception("stream failed")
            mock_resp = MagicMock()
            mock_resp.text = "fallback response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            chunks = list(llm.stream_content("test"))
        assert "fallback response" in chunks

    def test_active_engine_property(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
        assert llm.active_engine == "NEW"

    def test_generate_alias(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
        assert llm.generate == llm.generate_content

    def test_safe_text_with_text(self):
        class Obj:
            text = "hello"
        assert lc.DualEngineLLM._safe_text(Obj()) == "hello"

    def test_safe_text_without_text(self):
        class Obj:
            pass
        assert lc.DualEngineLLM._safe_text(Obj()) == ""

    def test_safe_text_none_text(self):
        class Obj:
            text = None
        assert lc.DualEngineLLM._safe_text(Obj()) == ""

    def test_log_interaction(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            mock_resp = MagicMock()
            mock_resp.text = "response text"
            llm._log_interaction("test prompt", mock_resp)
        # Check file was written
        raw_dir = tmp_path / ".brain" / "raw"
        assert raw_dir.exists()
        files = list(raw_dir.glob("llm_interaction_*.json"))
        assert len(files) == 1

    def test_log_interaction_exception(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            # Should not raise even if logging fails
            with patch("mcp_server_nucleus.runtime.common.get_brain_path",
                       side_effect=Exception("brain fail")):
                llm._log_interaction("test", MagicMock())

    def test_record_token_usage(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            # Should not raise even if token_budget not available
            llm._record_token_usage("prompt", MagicMock(), "session1", "agent1")

    def test_generate_content_legacy_engine(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             _mock_genai_legacy() as mock_legacy:
            mock_genai.Client.side_effect = Exception("fail")
            mock_model = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "legacy response"
            mock_model.generate_content.return_value = mock_resp
            mock_legacy.GenerativeModel.return_value = mock_model
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.generate_content("test prompt")
        assert result == mock_resp

    def test_embed_content_legacy_engine(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.HAS_LEGACY", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             _mock_genai_legacy() as mock_legacy:
            mock_genai.Client.side_effect = Exception("fail")
            mock_legacy.GenerativeModel.return_value = MagicMock()
            mock_legacy.embed_content.return_value = {"embedding": [0.5]}
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            result = llm.embed_content("test text")
        assert result == {"embedding": [0.5]}


# ---------------------------------------------------------------------------
# AnthropicResponse
# ---------------------------------------------------------------------------

class TestAnthropicResponse:
    def test_defaults(self):
        resp = lc.AnthropicResponse(text="hello")
        assert resp.text == "hello"
        assert resp.model == ""
        assert resp.usage == {}

    def test_with_model_and_usage(self):
        resp = lc.AnthropicResponse(text="hi", model="claude-3", usage={"input": 10})
        assert resp.model == "claude-3"
        assert resp.usage["input"] == 10


# ---------------------------------------------------------------------------
# AnthropicLLM
# ---------------------------------------------------------------------------

class TestAnthropicLLM:
    def test_init_no_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="NUCLEUS_ANTHROPIC_API_KEY"):
            lc.AnthropicLLM()

    def test_init_with_api_key(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("NUCLEUS_ANTHROPIC_BASE_URL", raising=False)
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        assert llm.engine == "ANTHROPIC"
        assert llm.api_key == "sk-test"
        assert llm.model_name == "claude-sonnet-4-6"

    def test_init_with_custom_model(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_MODEL", "claude-opus-4")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        assert llm.model_name == "claude-opus-4"

    def test_init_with_base_url(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_BASE_URL", "http://localhost:8080")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        assert llm.base_url == "http://localhost:8080"

    def test_init_with_user_agent(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_USER_AGENT", "custom-ua")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        # Check that default_headers was passed
        call_kwargs = mock_anthropic.Anthropic.call_args.kwargs
        assert call_kwargs["default_headers"]["User-Agent"] == "custom-ua"

    def test_init_anthropic_not_installed(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        # Mock the anthropic module to not exist
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("no anthropic")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="anthropic"):
                lc.AnthropicLLM()

    def test_generate_content(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_raw = MagicMock()
            mock_raw.model = "claude-3"
            mock_raw.usage.input_tokens = 10
            mock_raw.usage.output_tokens = 20
            block = MagicMock()
            block.text = "Hello from Claude"
            mock_raw.content = [block]
            mock_client.messages.create.return_value = mock_raw
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            result = llm.generate_content("test prompt")
        assert isinstance(result, lc.AnthropicResponse)
        assert result.text == "Hello from Claude"
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 20

    def test_generate_content_with_system_instruction(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_raw = MagicMock()
            mock_raw.model = "claude-3"
            mock_raw.usage.input_tokens = 5
            mock_raw.usage.output_tokens = 10
            block = MagicMock()
            block.text = "response"
            mock_raw.content = [block]
            mock_client.messages.create.return_value = mock_raw
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM(system_instruction="Be helpful")
            result = llm.generate_content("test")
        assert result.text == "response"

    def test_generate_content_rate_limited(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("429 rate_limit")
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            with pytest.raises(Exception, match="429"):
                llm.generate_content("test")

    def test_generate_content_generic_error(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("internal error")
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            with pytest.raises(Exception, match="internal error"):
                llm.generate_content("test")

    def test_generate_vision(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_raw = MagicMock()
            mock_raw.model = "claude-3"
            mock_raw.usage.input_tokens = 15
            mock_raw.usage.output_tokens = 25
            block = MagicMock()
            block.text = "image desc"
            mock_raw.content = [block]
            mock_client.messages.create.return_value = mock_raw
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            result = llm.generate_vision([str(img)], "describe")
        assert result.text == "image desc"

    def test_stream_content_string(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)
            mock_stream.text_stream = iter(["chunk1", "chunk2"])
            mock_stream.get_final_message = MagicMock(return_value=MagicMock(
                usage=MagicMock(input_tokens=5, output_tokens=10)
            ))
            mock_client.messages.stream.return_value = mock_stream
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            chunks = list(llm.stream_content("test prompt"))
        assert chunks == ["chunk1", "chunk2"]

    def test_stream_content_messages_list(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)
            mock_stream.text_stream = iter(["a", "b"])
            mock_stream.get_final_message = MagicMock(return_value=MagicMock(
                usage=MagicMock(input_tokens=3, output_tokens=7)
            ))
            mock_client.messages.stream.return_value = mock_stream
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            messages = [{"role": "user", "content": "hi"}]
            chunks = list(llm.stream_content(messages))
        assert chunks == ["a", "b"]

    def test_stream_content_fallback(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.stream.side_effect = Exception("stream failed")
            mock_raw = MagicMock()
            mock_raw.model = "claude-3"
            mock_raw.usage.input_tokens = 5
            mock_raw.usage.output_tokens = 10
            block = MagicMock()
            block.text = "fallback"
            mock_raw.content = [block]
            mock_client.messages.create.return_value = mock_raw
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            chunks = list(llm.stream_content("test"))
        assert "fallback" in chunks

    def test_stream_with_tools(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)

            # Create events for stream
            event1 = MagicMock()
            event1.type = "content_block_delta"
            event1.delta = MagicMock(text="Hello ")

            event2 = MagicMock()
            event2.type = "content_block_delta"
            event2.delta = MagicMock(text="world")

            mock_stream.__iter__ = MagicMock(return_value=iter([event1, event2]))

            # Final message with tool_use
            final_msg = MagicMock()
            final_msg.stop_reason = "tool_use"
            final_msg.usage.input_tokens = 10
            final_msg.usage.output_tokens = 20
            tool_block = MagicMock()
            tool_block.type = "tool_use"
            tool_block.id = "tool_123"
            tool_block.name = "shell_execute"
            tool_block.input = {"command": "ls"}
            final_msg.content = [tool_block]
            mock_stream.get_final_message.return_value = final_msg

            mock_client.messages.stream.return_value = mock_stream
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            chunks = list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        assert chunks == ["Hello ", "world"]
        assert llm.last_tool_calls[0]["name"] == "shell_execute"
        assert llm.last_stop_reason == "tool_use"

    def test_stream_with_tools_error(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.stream.side_effect = Exception("429 rate_limit")
            mock_anthropic.Anthropic.return_value = mock_client
            llm = lc.AnthropicLLM()
            with pytest.raises(Exception, match="429"):
                list(llm.stream_with_tools([{"role": "user", "content": "test"}]))

    def test_anthropic_active_engine(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        assert llm.active_engine == "ANTHROPIC"

    def test_anthropic_generate_alias(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        assert llm.generate == llm.generate_content

    def test_anthropic_log_interaction(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
            resp = lc.AnthropicResponse(text="test response")
            llm._log_interaction("prompt", resp)
        raw_dir = tmp_path / ".brain" / "raw"
        assert raw_dir.exists()

    def test_anthropic_record_token_usage(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
            resp = lc.AnthropicResponse(text="resp", usage={"input_tokens": 10, "output_tokens": 5})
            llm._record_token_usage("prompt", resp)

    def test_anthropic_tools_defined(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            llm = lc.AnthropicLLM()
        assert len(llm.TOOLS) > 0
        tool_names = [t["name"] for t in llm.TOOLS]
        assert "shell_execute" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names


# ---------------------------------------------------------------------------
# GroqResponse
# ---------------------------------------------------------------------------

class TestGroqResponse:
    def test_defaults(self):
        resp = lc.GroqResponse(text="hello")
        assert resp.text == "hello"
        assert resp.model == ""
        assert resp.usage == {}


# ---------------------------------------------------------------------------
# GroqLLM
# ---------------------------------------------------------------------------

class TestGroqLLM:
    def test_init_no_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_GROQ_API_KEY", raising=False)
        with pytest.raises(ValueError, match="NUCLEUS_GROQ_API_KEY"):
            lc.GroqLLM()

    def test_init_with_api_key(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
        assert llm.engine == "GROQ"
        assert llm.api_key == "gsk-test"
        assert llm.model_name == "llama-3.3-70b-versatile"

    def test_init_with_custom_model(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        monkeypatch.setenv("NUCLEUS_GROQ_MODEL", "mixtral-8x7b")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
        assert llm.model_name == "mixtral-8x7b"

    def test_init_openai_not_installed(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("no openai")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="openai"):
                lc.GroqLLM()

    def test_generate_content(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_raw = MagicMock()
            mock_raw.model = "llama-3"
            mock_raw.choices = [MagicMock()]
            mock_raw.choices[0].message.content = "Hello from Groq"
            mock_raw.usage.prompt_tokens = 10
            mock_raw.usage.completion_tokens = 20
            mock_client.chat.completions.create.return_value = mock_raw
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            result = llm.generate_content("test prompt")
        assert isinstance(result, lc.GroqResponse)
        assert result.text == "Hello from Groq"
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 20

    def test_generate_content_with_system_instruction(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_raw = MagicMock()
            mock_raw.model = "llama-3"
            mock_raw.choices = [MagicMock()]
            mock_raw.choices[0].message.content = "response"
            mock_raw.usage.prompt_tokens = 5
            mock_raw.usage.completion_tokens = 10
            mock_client.chat.completions.create.return_value = mock_raw
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM(system_instruction="Be helpful")
            result = llm.generate_content("test")
        assert result.text == "response"

    def test_generate_content_no_choices(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_raw = MagicMock()
            mock_raw.model = "llama-3"
            mock_raw.choices = []
            mock_raw.usage = None
            mock_client.chat.completions.create.return_value = mock_raw
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            result = llm.generate_content("test")
        assert result.text == ""
        assert result.usage == {}

    def test_generate_content_rate_limited(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("429 rate_limit")
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            with pytest.raises(Exception, match="429"):
                llm.generate_content("test")

    def test_generate_content_generic_error(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("server error")
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            with pytest.raises(Exception, match="server error"):
                llm.generate_content("test")

    def test_stream_content_string(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta.content = "Hello "
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta.content = "world"
            mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            chunks = list(llm.stream_content("test"))
        assert chunks == ["Hello ", "world"]

    def test_stream_content_messages_list(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta.content = "response"
            mock_client.chat.completions.create.return_value = iter([chunk1])
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            messages = [{"role": "user", "content": "hi"}]
            chunks = list(llm.stream_content(messages))
        assert chunks == ["response"]

    def test_stream_content_fallback(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("stream failed")
            mock_raw = MagicMock()
            mock_raw.model = "llama-3"
            mock_raw.choices = [MagicMock()]
            mock_raw.choices[0].message.content = "fallback"
            mock_raw.usage = MagicMock(prompt_tokens=5, completion_tokens=10)
            # Second call (non-streaming fallback) returns mock_raw
            mock_client.chat.completions.create.side_effect = [Exception("stream failed"), mock_raw]
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            chunks = list(llm.stream_content("test"))
        assert "fallback" in chunks

    def test_stream_with_tools(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            # Create streaming chunks with text and tool calls
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].finish_reason = None
            chunk1.choices[0].delta.content = "Hello"
            chunk1.choices[0].delta.tool_calls = None

            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].finish_reason = "tool_calls"
            chunk2.choices[0].delta.content = None
            tc_delta = MagicMock()
            tc_delta.index = 0
            tc_delta.id = "call_123"
            tc_delta.function.name = "shell_execute"
            tc_delta.function.arguments = '{"command": "ls"}'
            chunk2.choices[0].delta.tool_calls = [tc_delta]

            mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            chunks = list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        assert chunks == ["Hello"]
        assert llm.last_tool_calls[0]["name"] == "shell_execute"
        assert llm.last_tool_calls[0]["input"] == {"command": "ls"}
        assert llm.last_stop_reason == "tool_calls"

    def test_stream_with_tools_bad_json(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].finish_reason = "tool_calls"
            chunk1.choices[0].delta.content = None
            tc_delta = MagicMock()
            tc_delta.index = 0
            tc_delta.id = "call_456"
            tc_delta.function.name = "shell_execute"
            tc_delta.function.arguments = "not valid json"
            chunk1.choices[0].delta.tool_calls = [tc_delta]
            mock_client.chat.completions.create.return_value = iter([chunk1])
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        # Bad JSON falls back to {"command": ...}
        assert llm.last_tool_calls[0]["input"] == {"command": "not valid json"}

    def test_stream_with_tools_error(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("429 rate_limit")
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            with pytest.raises(Exception, match="429"):
                list(llm.stream_with_tools([{"role": "user", "content": "test"}]))

    def test_stream_with_tools_string_messages(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].finish_reason = "stop"
            chunk1.choices[0].delta.content = "text response"
            chunk1.choices[0].delta.tool_calls = None
            mock_client.chat.completions.create.return_value = iter([chunk1])
            mock_openai.OpenAI.return_value = mock_client
            llm = lc.GroqLLM()
            chunks = list(llm.stream_with_tools("test string"))
        assert chunks == ["text response"]

    def test_groq_active_engine(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
        assert llm.active_engine == "GROQ"

    def test_groq_generate_alias(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
        assert llm.generate == llm.generate_content

    def test_groq_log_interaction(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
            resp = lc.GroqResponse(text="test response")
            llm._log_interaction("prompt", resp)
        raw_dir = tmp_path / ".brain" / "raw"
        assert raw_dir.exists()

    def test_groq_record_token_usage(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
            resp = lc.GroqResponse(text="resp", usage={"input_tokens": 10, "output_tokens": 5})
            llm._record_token_usage("prompt", resp)

    def test_groq_tools_defined(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            llm = lc.GroqLLM()
        assert len(llm.TOOLS) > 0
        tool_names = [t["function"]["name"] for t in llm.TOOLS]
        assert "shell_execute" in tool_names


# ---------------------------------------------------------------------------
# get_llm_client (factory)
# ---------------------------------------------------------------------------

class TestGetLLMClient:
    def test_gemini_provider(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            client = lc.get_llm_client(provider="gemini", tier=lc.LLMTier.LOCAL_FREE)
        assert isinstance(client, lc.DualEngineLLM)

    def test_anthropic_provider(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            client = lc.get_llm_client(provider="anthropic")
        assert isinstance(client, lc.AnthropicLLM)

    def test_groq_provider(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_openai.OpenAI.return_value = MagicMock()
            client = lc.get_llm_client(provider="groq")
        assert isinstance(client, lc.GroqLLM)

    def test_default_provider(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("NUCLEUS_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            client = lc.get_llm_client(tier=lc.LLMTier.LOCAL_FREE)
        assert isinstance(client, lc.DualEngineLLM)

    def test_env_var_provider(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("NUCLEUS_LLM_PROVIDER", "anthropic")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            client = lc.get_llm_client()
        assert isinstance(client, lc.AnthropicLLM)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            lc.get_llm_client(provider="nonexistent")

    def test_claude_oauth_provider(self, monkeypatch):
        # This will try to import ClaudeOAuthLLM which may not be available
        # We mock the import
        mock_oauth = MagicMock()
        mock_instance = MagicMock()
        mock_oauth.ClaudeOAuthLLM.return_value = mock_instance
        with patch.dict("sys.modules", {
            "mcp_server_nucleus.runtime.claude_oauth_llm": mock_oauth
        }):
            client = lc.get_llm_client(provider="claude_oauth")
        assert client == mock_instance

    def test_claude_max_alias(self, monkeypatch):
        mock_oauth = MagicMock()
        mock_instance = MagicMock()
        mock_oauth.ClaudeOAuthLLM.return_value = mock_instance
        with patch.dict("sys.modules", {
            "mcp_server_nucleus.runtime.claude_oauth_llm": mock_oauth
        }):
            client = lc.get_llm_client(provider="claude_max")
        assert client == mock_instance

    def test_oauth_alias(self, monkeypatch):
        mock_oauth = MagicMock()
        mock_instance = MagicMock()
        mock_oauth.ClaudeOAuthLLM.return_value = mock_instance
        with patch.dict("sys.modules", {
            "mcp_server_nucleus.runtime.claude_oauth_llm": mock_oauth
        }):
            client = lc.get_llm_client(provider="oauth")
        assert client == mock_instance

    def test_local_provider_not_available(self, monkeypatch):
        # LocalLLM is in sovereign.local_llm which may not be importable
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if "local_llm" in name:
                raise ImportError("not available")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ValueError, match="Local provider not available"):
                lc.get_llm_client(provider="local")

    def test_provider_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            client = lc.get_llm_client(provider="ANTHROPIC")
        assert isinstance(client, lc.AnthropicLLM)

    def test_provider_with_whitespace(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_anthropic.Anthropic.return_value = MagicMock()
            client = lc.get_llm_client(provider="  anthropic  ")
        assert isinstance(client, lc.AnthropicLLM)


# ---------------------------------------------------------------------------
# Additional edge-case tests for coverage gaps
# ---------------------------------------------------------------------------

class TestDualEngineLLMCoverageGaps:
    def test_generate_content_with_token_budget_import_error(self, monkeypatch):
        """Cover the ImportError path in token budget check."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            # token_budget import will fail → ImportError path
            result = llm.generate_content("test")
        assert result == mock_resp

    def test_stream_content_with_system_instruction(self, monkeypatch):
        """Cover stream_content NEW engine with system_instruction."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             patch("mcp_server_nucleus.runtime.llm_client.types") as mock_types:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.text = "Hello"
            mock_client.models.generate_content_stream.return_value = iter([chunk1])
            mock_genai.Client.return_value = mock_client
            mock_types.GenerateContentConfig.return_value = MagicMock()
            llm = lc.DualEngineLLM(
                tier=lc.LLMTier.LOCAL_FREE,
                system_instruction="Be helpful"
            )
            chunks = list(llm.stream_content("test"))
        assert chunks == ["Hello"]

    def test_stream_content_empty_chunks(self, monkeypatch):
        """Cover stream_content with chunks that have no text."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        if proxy_file.exists():
            proxy_file.unlink()
        with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
             patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai, \
             patch("mcp_server_nucleus.runtime.llm_client.types") as mock_types:
            mock_client = MagicMock()
            chunk1 = MagicMock()
            chunk1.text = ""  # Empty text
            chunk2 = MagicMock()
            chunk2.text = "real text"
            mock_client.models.generate_content_stream.return_value = iter([chunk1, chunk2])
            mock_genai.Client.return_value = mock_client
            mock_types.GenerateContentConfig.return_value = MagicMock()
            llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            chunks = list(llm.stream_content("test"))
        assert chunks == ["real text"]

    def test_proxy_auto_discovery_failure(self, monkeypatch, tmp_path):
        """Cover proxy port file read failure."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GEMINI_API_BASE_URL", raising=False)
        # Create a proxy port file that will cause read error
        proxy_file = Path("/tmp") / "gemini_proxy.port"
        proxy_file.write_text("9090")
        try:
            with patch("mcp_server_nucleus.runtime.llm_client.HAS_GENAI", True), \
                 patch("mcp_server_nucleus.runtime.llm_client.genai") as mock_genai:
                mock_genai.Client.return_value = MagicMock()
                llm = lc.DualEngineLLM(tier=lc.LLMTier.LOCAL_FREE)
            assert llm.engine == "NEW"
        finally:
            proxy_file.unlink(missing_ok=True)


class TestAnthropicLLMCoverageGaps:
    def test_stream_with_tools_non_text_event(self, monkeypatch):
        """Cover stream_with_tools with non-content_block_delta events."""
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = mock_anthropic.Anthropic.return_value
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)

            # Non-text event (should be skipped)
            event1 = MagicMock()
            event1.type = "message_start"
            event1.delta = MagicMock()

            # Text event
            event2 = MagicMock()
            event2.type = "content_block_delta"
            event2.delta = MagicMock(text="Hello")

            mock_stream.__iter__ = MagicMock(return_value=iter([event1, event2]))

            final_msg = MagicMock()
            final_msg.stop_reason = "end_turn"
            final_msg.usage.input_tokens = 5
            final_msg.usage.output_tokens = 10
            final_msg.content = []
            mock_stream.get_final_message.return_value = final_msg

            mock_client.messages.stream.return_value = mock_stream
            llm = lc.AnthropicLLM()
            chunks = list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        assert chunks == ["Hello"]
        assert llm.last_stop_reason == "end_turn"
        assert llm.last_tool_calls == []

    def test_stream_with_tools_generic_error(self, monkeypatch):
        """Cover stream_with_tools with non-rate-limit error."""
        monkeypatch.setenv("NUCLEUS_ANTHROPIC_API_KEY", "sk-test")
        with _mock_anthropic() as mock_anthropic:
            mock_client = mock_anthropic.Anthropic.return_value
            mock_client.messages.stream.side_effect = Exception("internal error")
            llm = lc.AnthropicLLM()
            with pytest.raises(Exception, match="internal error"):
                list(llm.stream_with_tools([{"role": "user", "content": "test"}]))


class TestGroqLLMCoverageGaps:
    def test_stream_with_tools_no_choices(self, monkeypatch):
        """Cover stream_with_tools with chunks that have no choices."""
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = mock_openai.OpenAI.return_value
            chunk1 = MagicMock()
            chunk1.choices = []  # No choices
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].finish_reason = "stop"
            chunk2.choices[0].delta.content = "text"
            chunk2.choices[0].delta.tool_calls = None
            mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
            llm = lc.GroqLLM()
            chunks = list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        assert chunks == ["text"]

    def test_stream_with_tools_no_delta_content(self, monkeypatch):
        """Cover stream_with_tools with delta but no content."""
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = mock_openai.OpenAI.return_value
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].finish_reason = None
            chunk1.choices[0].delta.content = None
            chunk1.choices[0].delta.tool_calls = None
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].finish_reason = "stop"
            chunk2.choices[0].delta.content = "final"
            chunk2.choices[0].delta.tool_calls = None
            mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
            llm = lc.GroqLLM()
            chunks = list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        assert chunks == ["final"]

    def test_stream_with_tools_no_tool_function(self, monkeypatch):
        """Cover stream_with_tools with tool_calls but no function."""
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = mock_openai.OpenAI.return_value
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].finish_reason = "tool_calls"
            chunk1.choices[0].delta.content = None
            tc_delta = MagicMock()
            tc_delta.index = 0
            tc_delta.id = "call_789"
            tc_delta.function = None  # No function
            chunk1.choices[0].delta.tool_calls = [tc_delta]
            mock_client.chat.completions.create.return_value = iter([chunk1])
            llm = lc.GroqLLM()
            list(llm.stream_with_tools([{"role": "user", "content": "test"}]))
        # Tool call with no function name
        assert llm.last_tool_calls[0]["name"] == ""

    def test_stream_with_tools_generic_error(self, monkeypatch):
        """Cover stream_with_tools with non-rate-limit error."""
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = mock_openai.OpenAI.return_value
            mock_client.chat.completions.create.side_effect = Exception("server error")
            llm = lc.GroqLLM()
            with pytest.raises(Exception, match="server error"):
                list(llm.stream_with_tools([{"role": "user", "content": "test"}]))

    def test_stream_content_with_system_instruction(self, monkeypatch):
        """Cover stream_content with system_instruction."""
        monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", "gsk-test")
        with _mock_openai() as mock_openai:
            mock_client = mock_openai.OpenAI.return_value
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta.content = "response"
            mock_client.chat.completions.create.return_value = iter([chunk1])
            llm = lc.GroqLLM(system_instruction="Be helpful")
            chunks = list(llm.stream_content("test"))
        assert chunks == ["response"]


class TestGetLLMClientCoverageGaps:
    def test_local_provider_available(self, monkeypatch):
        """Cover local provider with LocalLLM available."""
        mock_local = MagicMock()
        mock_instance = MagicMock()
        mock_local.LocalLLM.return_value = mock_instance
        # Need to mock the import path
        with patch.dict("sys.modules", {
            "mcp_server_nucleus.sovereign.local_llm": mock_local,
            "mcp_server_nucleus.sovereign": MagicMock(),
            "mcp_server_nucleus.sovereign.local_llm.LocalLLM": mock_local,
        }):
            client = lc.get_llm_client(provider="local")
        assert client == mock_instance

    def test_third_brother_alias(self, monkeypatch):
        """Cover 'third-brother' alias for local provider."""
        mock_local = MagicMock()
        mock_instance = MagicMock()
        mock_local.LocalLLM.return_value = mock_instance
        with patch.dict("sys.modules", {
            "mcp_server_nucleus.sovereign.local_llm": mock_local,
            "mcp_server_nucleus.sovereign": MagicMock(),
        }):
            client = lc.get_llm_client(provider="third-brother")
        assert client == mock_instance

    def test_ollama_alias(self, monkeypatch):
        """Cover 'ollama' alias for local provider."""
        mock_local = MagicMock()
        mock_instance = MagicMock()
        mock_local.LocalLLM.return_value = mock_instance
        with patch.dict("sys.modules", {
            "mcp_server_nucleus.sovereign.local_llm": mock_local,
            "mcp_server_nucleus.sovereign": MagicMock(),
        }):
            client = lc.get_llm_client(provider="ollama")
        assert client == mock_instance
