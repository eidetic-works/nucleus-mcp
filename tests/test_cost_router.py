"""Unit tests for mcp_server_nucleus.runtime.cost_router (W5).

Covers:
  - Complexity auto-detection (token count, code blocks, structured output)
  - Routing table: routine → haiku, complex → sonnet, sovereign → local-tb
  - Sovereign fallback to oauth-shim when local-TB is unreachable
  - Cost estimate sanity (non-negative, free for local models)
  - Pricing table completeness (all routed models have entries)
  - context sovereign-override flag
  - cost_summary helper shape
  - edge cases: empty prompt, very large prompt, structured-output markers
"""

import pytest
from unittest.mock import patch

from mcp_server_nucleus.runtime.cost_router import (
    RouteDecision,
    PRICING_PER_1K,
    ROUTE_TABLE,
    _detect_complexity,
    _estimate_tokens,
    _is_local_tb_available,
    cost_summary,
    route_call,
)


# ── Token estimator ──────────────────────────────────────────────────────────

class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") >= 1  # guard: never 0

    def test_short_string(self):
        tokens = _estimate_tokens("hello world")
        assert 1 <= tokens <= 5

    def test_large_string(self):
        big = "x" * 40_000  # 10k tokens approx
        assert _estimate_tokens(big) > 2_000


# ── Complexity detection ─────────────────────────────────────────────────────

class TestDetectComplexity:
    def test_routine_short_plain(self):
        assert _detect_complexity("summarise this email", "routine") == "routine"

    def test_sovereign_never_downgraded(self):
        # Even a short plain prompt stays sovereign if hint says so
        assert _detect_complexity("hi", "sovereign") == "sovereign"

    def test_long_prompt_upgrades_to_complex(self):
        # 2001+ tokens estimated → complex
        long_prompt = "word " * 10_000
        result = _detect_complexity(long_prompt, "routine")
        assert result == "complex"

    def test_code_block_upgrades_to_complex(self):
        prompt = "Can you review this code?\n```python\nprint('hello')\n```"
        assert _detect_complexity(prompt, "routine") == "complex"

    def test_def_keyword_upgrades(self):
        assert _detect_complexity("def my_function(x):", "routine") == "complex"

    def test_class_keyword_upgrades(self):
        assert _detect_complexity("class MyModel(BaseModel):", "routine") == "complex"

    def test_pydantic_marker_upgrades(self):
        assert _detect_complexity("using pydantic to validate", "routine") == "complex"

    def test_json_schema_marker_upgrades(self):
        prompt = 'response_format={"type": "object", "properties": {}}'
        assert _detect_complexity(prompt, "routine") == "complex"

    def test_hint_complex_preserved(self):
        # Caller says complex, short plain prompt: stays complex
        assert _detect_complexity("quick task", "complex") == "complex"


# ── Routing table sanity ─────────────────────────────────────────────────────

class TestRouteTable:
    def test_all_complexities_in_table(self):
        for key in ("routine", "complex", "sovereign"):
            assert key in ROUTE_TABLE

    def test_routine_maps_to_haiku(self):
        assert ROUTE_TABLE["routine"]["model"] == "claude-haiku-3-5"

    def test_complex_maps_to_sonnet(self):
        assert ROUTE_TABLE["complex"]["model"] == "claude-sonnet-4-5"

    def test_sovereign_maps_to_local_tb(self):
        assert ROUTE_TABLE["sovereign"]["model"] == "local-tb"
        assert ROUTE_TABLE["sovereign"]["provider"] == "local"
        assert ROUTE_TABLE["sovereign"]["sovereignty_tier"] == "sovereign"


# ── Pricing table ────────────────────────────────────────────────────────────

class TestPricingTable:
    def test_all_routed_models_have_pricing(self):
        for tier_cfg in ROUTE_TABLE.values():
            model = tier_cfg["model"]
            assert model in PRICING_PER_1K, f"{model} missing from PRICING_PER_1K"

    def test_local_tb_is_free(self):
        assert PRICING_PER_1K["local-tb"]["input"] == 0.0
        assert PRICING_PER_1K["local-tb"]["output"] == 0.0

    def test_oauth_shim_is_free(self):
        assert PRICING_PER_1K["claude-oauth-shim"]["input"] == 0.0

    def test_haiku_cheaper_than_sonnet(self):
        haiku_in = PRICING_PER_1K["claude-haiku-3-5"]["input"]
        sonnet_in = PRICING_PER_1K["claude-sonnet-4-5"]["input"]
        assert haiku_in < sonnet_in


# ── route_call: routine ──────────────────────────────────────────────────────

class TestRouteCallRoutine:
    def test_routine_returns_haiku(self):
        d = route_call("please summarise this", complexity="routine", skip_tb_check=True)
        assert d.model == "claude-haiku-3-5"
        assert d.provider == "anthropic"
        assert d.sovereignty_tier == "standard"

    def test_routine_cost_is_small(self):
        d = route_call("hello", complexity="routine", skip_tb_check=True)
        assert d.expected_input_cost >= 0
        assert d.expected_output_cost >= 0

    def test_decision_has_token_estimate(self):
        d = route_call("four words exactly here", complexity="routine", skip_tb_check=True)
        assert d.estimated_input_tokens >= 1


# ── route_call: complex ──────────────────────────────────────────────────────

class TestRouteCallComplex:
    def test_complex_hint_returns_sonnet(self):
        d = route_call("explain quantum entanglement", complexity="complex", skip_tb_check=True)
        assert d.model == "claude-sonnet-4-5"
        assert d.provider == "anthropic"

    def test_code_prompt_auto_upgrades_to_sonnet(self):
        prompt = "Please review:\n```python\ndef fib(n):\n    return n if n < 2 else fib(n-1)+fib(n-2)\n```"
        d = route_call(prompt, complexity="routine", skip_tb_check=True)
        assert d.model == "claude-sonnet-4-5"
        assert d.complexity == "complex"


# ── route_call: sovereign ────────────────────────────────────────────────────

class TestRouteCallSovereign:
    def test_sovereign_with_tb_available(self):
        with patch(
            "mcp_server_nucleus.runtime.cost_router._is_local_tb_available",
            return_value=True,
        ):
            d = route_call("private data", complexity="sovereign")
        assert d.model == "local-tb"
        assert d.sovereignty_tier == "sovereign"
        assert not d.fallback_used

    def test_sovereign_fallback_when_tb_down(self):
        with patch(
            "mcp_server_nucleus.runtime.cost_router._is_local_tb_available",
            return_value=False,
        ):
            d = route_call("private data", complexity="sovereign")
        assert d.model == "claude-oauth-shim"
        assert d.fallback_used
        assert d.sovereignty_tier == "sovereign"

    def test_sovereign_via_context_flag(self):
        with patch(
            "mcp_server_nucleus.runtime.cost_router._is_local_tb_available",
            return_value=True,
        ):
            d = route_call("secret prompt", context={"sovereign": True})
        assert d.sovereignty_tier == "sovereign"

    def test_sovereign_skip_tb_check(self):
        d = route_call("private", complexity="sovereign", skip_tb_check=True)
        # skip_tb_check: goes direct to local-tb without HTTP
        assert d.model == "local-tb"
        assert not d.fallback_used

    def test_sovereign_cost_is_zero(self):
        d = route_call("classified info", complexity="sovereign", skip_tb_check=True)
        assert d.expected_input_cost == 0.0
        assert d.expected_output_cost == 0.0


# ── cost_summary helper ───────────────────────────────────────────────────────

class TestCostSummary:
    def test_shape(self):
        d = route_call("test", skip_tb_check=True)
        summary = cost_summary(d)
        for key in (
            "provider",
            "model",
            "complexity",
            "sovereignty_tier",
            "estimated_input_tokens",
            "expected_input_cost_usd",
            "expected_output_cost_usd",
            "expected_total_cost_usd",
            "fallback_used",
            "routing_note",
        ):
            assert key in summary, f"Missing key: {key}"

    def test_total_equals_sum(self):
        d = route_call("some prompt for cost check", skip_tb_check=True)
        summary = cost_summary(d)
        expected = round(
            summary["expected_input_cost_usd"] + summary["expected_output_cost_usd"], 8
        )
        assert summary["expected_total_cost_usd"] == expected


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_prompt(self):
        d = route_call("", complexity="routine", skip_tb_check=True)
        assert d.model == "claude-haiku-3-5"
        assert d.estimated_input_tokens >= 1  # never 0

    def test_custom_output_token_estimate(self):
        d = route_call(
            "short",
            complexity="routine",
            estimated_output_tokens=500,
            skip_tb_check=True,
        )
        pricing = PRICING_PER_1K["claude-haiku-3-5"]
        expected_out = (500 / 1_000) * pricing["output"]
        assert abs(d.expected_output_cost - expected_out) < 1e-10

    def test_very_long_prompt_routes_complex(self):
        huge = "explain this in detail " * 2_000
        d = route_call(huge, complexity="routine", skip_tb_check=True)
        assert d.complexity == "complex"
        assert d.model == "claude-sonnet-4-5"
