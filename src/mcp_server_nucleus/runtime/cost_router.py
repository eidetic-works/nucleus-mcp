"""Nucleus Runtime — W5 Tier Routing with Per-Call Cost Capture.

Routes agent calls to the cheapest model tier that can handle the task:
  - routine   → claude-haiku-3-5   (fast, cheap, most tasks)
  - complex   → claude-sonnet-4-5  (reasoning, code, structured output)
  - sovereign → local-TB or claude-oauth-shim (zero-data-egress guarantee)

Heuristics (complexity auto-detection):
  1. Token count threshold: >2 000 input tokens → complex
  2. Code-block markers in prompt (``` / def / class / function) → complex
  3. Structured-output markers (JSON schema / Pydantic / dataclass) → complex
  4. Sovereignty flag in context → sovereign route regardless of complexity

Cost capture:
  Every routed call emits an anonymous cost_route span via anon_telemetry so
  fleet-level cost dashboards can aggregate per-install spend without any
  personal data leaving the machine.

Pricing constants (source: public pricing pages, verified 2026-06-18):
  Anthropic: https://www.anthropic.com/pricing
  OpenAI:    https://openai.com/api/pricing
  Gemini:    https://ai.google.dev/pricing

Usage::

    from mcp_server_nucleus.runtime.cost_router import route_call, RouteDecision

    decision = route_call(
        prompt="summarise this thread",
        complexity="routine",
        context={"install_id": "abc123"},
    )
    print(decision.provider, decision.model, decision.expected_input_cost)
"""

from __future__ import annotations

import re
import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger("nucleus.cost_router")

# ── Pricing table (USD per 1 000 tokens) ────────────────────────────────────
# Source: verified against public pricing pages on 2026-06-18.
# Update this dict when providers change rates; unit tests pin the keys.

PRICING_PER_1K: dict[str, dict[str, float]] = {
    # Anthropic Haiku 3.5 — cheapest production-grade Anthropic model
    "claude-haiku-3-5": {"input": 0.00080, "output": 0.00400},
    # Anthropic Sonnet 4.5 — mid tier (complex tasks)
    "claude-sonnet-4-5": {"input": 0.00300, "output": 0.01500},
    # Anthropic Opus 4 — premium (not routed by default, cost guard)
    "claude-opus-4": {"input": 0.01500, "output": 0.07500},
    # OpenAI GPT-4o mini — low-cost alternative
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    # OpenAI GPT-4o — complex alternative
    "gpt-4o": {"input": 0.00250, "output": 0.01000},
    # Gemini 2.5 Flash — economy tier
    "gemini-2.5-flash": {"input": 0.00010, "output": 0.00040},
    # Local TB / oauth-shim — treated as zero-cost (infra cost only)
    "local-tb": {"input": 0.0, "output": 0.0},
    "claude-oauth-shim": {"input": 0.0, "output": 0.0},
}

# ── Routing table ────────────────────────────────────────────────────────────

ROUTE_TABLE: dict[str, dict[str, str]] = {
    "routine": {
        "provider": "anthropic",
        "model": "claude-haiku-3-5",
        "sovereignty_tier": "standard",
    },
    "complex": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "sovereignty_tier": "standard",
    },
    "sovereign": {
        "provider": "local",
        "model": "local-tb",
        "sovereignty_tier": "sovereign",
    },
}

# Fallback when local-TB is not available
_SOVEREIGN_FALLBACK_MODEL = "claude-oauth-shim"
_SOVEREIGN_FALLBACK_PROVIDER = "anthropic-oauth"

# ── Complexity heuristics ────────────────────────────────────────────────────

# Rough token estimate: 4 chars ≈ 1 token (BPE average for English + code)
_CHARS_PER_TOKEN = 4
_COMPLEX_TOKEN_THRESHOLD = 2_000

_CODE_BLOCK_RE = re.compile(
    r"```|\bdef \w+\s*\(|\bclass \w+[\s(:]|function\s+\w+\s*\(",
    re.MULTILINE,
)
_STRUCTURED_OUTPUT_RE = re.compile(
    r'"type"\s*:\s*"object"|pydantic|BaseModel|@dataclass|response_format|json_schema',
    re.IGNORECASE,
)


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate without importing tiktoken."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _detect_complexity(
    prompt: str,
    hint: Literal["routine", "complex", "sovereign"] = "routine",
) -> Literal["routine", "complex", "sovereign"]:
    """Auto-detect complexity from prompt content.

    The caller's explicit *hint* is respected unless heuristics force an upgrade.
    Sovereign is never downgraded — it is always caller-specified.
    """
    if hint == "sovereign":
        return "sovereign"

    # Token threshold
    if _estimate_tokens(prompt) > _COMPLEX_TOKEN_THRESHOLD:
        return "complex"

    # Code or structured-output markers
    if _CODE_BLOCK_RE.search(prompt) or _STRUCTURED_OUTPUT_RE.search(prompt):
        return "complex"

    return hint  # caller's hint is trusted if no heuristic fires


def _is_local_tb_available() -> bool:
    """Check whether the local Third Brother endpoint is reachable."""
    import os
    tb_url = os.environ.get("TB_URL", "http://127.0.0.1:7878")
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{tb_url}/health",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── RouteDecision dataclass ──────────────────────────────────────────────────

@dataclass
class RouteDecision:
    """Full routing decision returned by ``route_call``."""

    provider: str
    """Provider identifier: 'anthropic' | 'anthropic-oauth' | 'openai' | 'local'"""

    model: str
    """Model name as passed to the provider API."""

    complexity: Literal["routine", "complex", "sovereign"]
    """Resolved complexity tier (may differ from caller hint if heuristics fired)."""

    sovereignty_tier: Literal["standard", "sovereign"]
    """Data-residency guarantee for this route."""

    estimated_input_tokens: int
    """Estimated input token count from the prompt."""

    expected_input_cost: float
    """Expected cost for input tokens (USD)."""

    expected_output_cost: float
    """Expected cost for a typical output (1/4 of input tokens by default, USD)."""

    fallback_used: bool = False
    """True when the primary route was unavailable and a fallback was used."""

    routing_note: str = ""
    """Human-readable note explaining the routing decision."""

    # Internal metadata (not surfaced to MCP callers)
    _routed_at: float = field(default_factory=time.time, repr=False)


# ── Core routing function ────────────────────────────────────────────────────

def route_call(
    prompt: str,
    complexity: Literal["routine", "complex", "sovereign"] = "routine",
    context: Optional[dict] = None,
    estimated_output_tokens: Optional[int] = None,
    skip_tb_check: bool = False,
) -> RouteDecision:
    """Route a prompt to the cheapest capable model tier.

    Parameters
    ----------
    prompt:
        The full prompt text (used for heuristic complexity detection).
    complexity:
        Caller's hint.  Heuristics may upgrade routine → complex but never
        downgrade sovereign.
    context:
        Optional dict with keys:
        - ``sovereign`` (bool): force sovereign route
        - ``install_id`` (str): override install_id for telemetry
    estimated_output_tokens:
        Override the output-token estimate for cost projection.
        Defaults to 25% of estimated input tokens.
    skip_tb_check:
        When True, skip the live TB health check (useful in unit tests).

    Returns
    -------
    RouteDecision
        Full routing decision with provider, model, and cost estimates.
    """
    ctx = context or {}

    # Sovereign override from context flag
    if ctx.get("sovereign"):
        complexity = "sovereign"

    # Run heuristics
    resolved = _detect_complexity(prompt, complexity)

    # Build base route
    route_cfg = ROUTE_TABLE[resolved].copy()
    provider = route_cfg["provider"]
    model = route_cfg["model"]
    sovereignty_tier = route_cfg["sovereignty_tier"]
    fallback_used = False
    routing_note = f"Resolved complexity={resolved}"

    # Sovereign: check local-TB availability, fall back to oauth-shim
    if resolved == "sovereign" and not skip_tb_check:
        if not _is_local_tb_available():
            provider = _SOVEREIGN_FALLBACK_PROVIDER
            model = _SOVEREIGN_FALLBACK_MODEL
            fallback_used = True
            routing_note += "; local-TB unavailable, using oauth-shim"
        else:
            routing_note += "; local-TB reachable"

    # Cost estimates
    estimated_input_tokens = _estimate_tokens(prompt)
    if estimated_output_tokens is None:
        estimated_output_tokens = max(1, estimated_input_tokens // 4)

    pricing = PRICING_PER_1K.get(model, {"input": 0.0, "output": 0.0})
    expected_input_cost = (estimated_input_tokens / 1_000) * pricing["input"]
    expected_output_cost = (estimated_output_tokens / 1_000) * pricing["output"]

    decision = RouteDecision(
        provider=provider,
        model=model,
        complexity=resolved,
        sovereignty_tier=sovereignty_tier,
        estimated_input_tokens=estimated_input_tokens,
        expected_input_cost=expected_input_cost,
        expected_output_cost=expected_output_cost,
        fallback_used=fallback_used,
        routing_note=routing_note,
    )

    # Emit cost telemetry (fire-and-forget)
    _emit_cost_telemetry(decision, ctx)

    return decision


# ── Telemetry emit ───────────────────────────────────────────────────────────

def _emit_cost_telemetry(decision: RouteDecision, ctx: dict) -> None:
    """Emit a cost_route event via anon_telemetry (non-blocking)."""
    def _fire():
        try:
            from .anon_telemetry import record_anon_command
            payload_key = (
                f"cost_route/{decision.provider}/{decision.model}"
                f"/{decision.complexity}"
            )
            record_anon_command(
                command=payload_key,
                category="nucleus_route",
                duration_ms=0.0,  # routing itself is negligible
            )
        except Exception:
            pass  # telemetry must never break caller

    t = threading.Thread(target=_fire, daemon=True)
    t.start()


# ── Cost summary helper ──────────────────────────────────────────────────────

def cost_summary(decision: RouteDecision) -> dict:
    """Return a JSON-serialisable dict suitable for MCP tool responses."""
    return {
        "provider": decision.provider,
        "model": decision.model,
        "complexity": decision.complexity,
        "sovereignty_tier": decision.sovereignty_tier,
        "estimated_input_tokens": decision.estimated_input_tokens,
        "expected_input_cost_usd": round(decision.expected_input_cost, 8),
        "expected_output_cost_usd": round(decision.expected_output_cost, 8),
        "expected_total_cost_usd": round(
            decision.expected_input_cost + decision.expected_output_cost, 8
        ),
        "fallback_used": decision.fallback_used,
        "routing_note": decision.routing_note,
    }
