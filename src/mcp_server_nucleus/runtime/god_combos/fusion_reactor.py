"""Fusion Reactor God Combo — Self-Reinforcing Memory Loop.

Pipeline: trigger → write_engram → query_engrams → synthesize → write_engram (loop)

This combo creates a compounding knowledge loop:
1. CAPTURE — Write an observation engram from a trigger event
2. RECALL — Query related engrams to build context
3. SYNTHESIZE — Combine new observation with prior knowledge
4. COMPOUND — Write a higher-intensity synthesis engram

The loop runs once per invocation (no infinite loops). Each run
compounds knowledge by building on prior engrams, creating
increasingly rich context over time.

Circuit breakers:
- Max execution time: 30 seconds
- Max engram writes per run: 2 (capture + synthesis)
- No recursive calls

Usage:
    from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
    result = run_fusion_reactor(observation="Latency improved after cache fix", context="Architecture")
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nucleus.god_combos.fusion_reactor")

MAX_EXECUTION_SECONDS = 30
MAX_RECALL_ENGRAMS = 10


def run_fusion_reactor(
    observation: str,
    context: str = "Decision",
    intensity: int = 6,
    write_engrams: bool = True,
) -> Dict[str, Any]:
    """Execute the Fusion Reactor pipeline.
    
    Args:
        observation: New observation or insight to compound into memory.
        context: Engram context category (Feature|Architecture|Brand|Strategy|Decision).
        intensity: Base intensity for the capture engram (1-10). Synthesis gets +1.
        write_engrams: Whether to actually write engrams. Default True.
        
    Returns:
        Dict with sections: capture, recall, synthesis, meta.
    """
    start = time.time()
    result = {
        "pipeline": "fusion_reactor",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "observation": observation,
        "sections": {},
        "synthesis": None,
        "meta": {
            "steps_completed": 0,
            "execution_time_ms": 0,
            "circuit_breaker_hit": False,
            "engrams_written": 0,
        },
    }

    def _check_timeout():
        elapsed = time.time() - start
        if elapsed > MAX_EXECUTION_SECONDS:
            result["meta"]["circuit_breaker_hit"] = True
            return True
        return False

    # ── STEP 1: CAPTURE — Write the observation engram ────────
    capture_key = f"fusion_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if write_engrams:
        try:
            from ..engram_ops import _brain_write_engram_impl
            _brain_write_engram_impl(
                key=capture_key,
                value=observation,
                context=context,
                intensity=min(intensity, 10),
            )
            result["meta"]["engrams_written"] += 1
        except Exception as e:
            logger.warning(f"Capture write failed: {e}")

    result["sections"]["capture"] = {
        "key": capture_key,
        "observation": observation[:200],
        "context": context,
        "intensity": intensity,
        "written": write_engrams,
    }
    result["meta"]["steps_completed"] += 1

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 2: RECALL — Query related engrams ────────────────
    prior_engrams: List[Dict] = []
    try:
        from ..engram_ops import _brain_search_engrams_impl
        # Search for engrams related to keywords in the observation
        search_terms = observation.split()[:5]  # First 5 words as search
        search_query = " ".join(search_terms[:3]) if len(search_terms) >= 3 else observation[:50]
        
        search_raw = _brain_search_engrams_impl(
            query=search_query,
            limit=MAX_RECALL_ENGRAMS,
        )
        search_data = json.loads(search_raw)
        prior_engrams = search_data.get("data", {}).get("engrams", [])
        
        # Also query by context for broader recall
        from ..engram_ops import _brain_query_engrams_impl
        context_raw = _brain_query_engrams_impl(
            context=context,
            min_intensity=5,
            limit=MAX_RECALL_ENGRAMS,
        )
        context_data = json.loads(context_raw)
        context_engrams = context_data.get("data", {}).get("engrams", [])
        
        # Merge and deduplicate by key
        seen_keys = {e.get("key") for e in prior_engrams}
        for e in context_engrams:
            if e.get("key") not in seen_keys:
                prior_engrams.append(e)
                seen_keys.add(e.get("key"))

    except Exception as e:
        logger.warning(f"Recall step failed: {e}")

    result["sections"]["recall"] = {
        "total_recalled": len(prior_engrams),
        "search_query": search_query if 'search_query' in dir() else observation[:50],
        "top_keys": [e.get("key", "?")[:60] for e in prior_engrams[:5]],
        "contexts_found": list(set(e.get("context", "Unknown") for e in prior_engrams)),
        "avg_intensity": round(
            sum(e.get("intensity", 5) for e in prior_engrams) / max(len(prior_engrams), 1), 1
        ),
    }
    result["meta"]["steps_completed"] += 1

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 3: SYNTHESIZE — Combine new + prior knowledge ────
    prior_count = len(prior_engrams)
    prior_summary = "; ".join(
        f"{e.get('key', '?')}: {str(e.get('value', ''))[:60]}"
        for e in prior_engrams[:5]
    )

    if prior_count == 0:
        synthesis_value = f"[NOVEL] {observation}"
        synthesis_type = "novel"
    elif prior_count <= 3:
        synthesis_value = (
            f"[REINFORCED] {observation} "
            f"(builds on {prior_count} prior engrams: {prior_summary})"
        )
        synthesis_type = "reinforced"
    else:
        synthesis_value = (
            f"[COMPOUNDED] {observation} "
            f"(synthesized from {prior_count} related engrams across "
            f"{len(result['sections']['recall']['contexts_found'])} contexts. "
            f"Key priors: {prior_summary})"
        )
        synthesis_type = "compounded"

    # Synthesis intensity: base + 1, capped at 10
    synthesis_intensity = min(intensity + 1, 10)

    synthesis = {
        "type": synthesis_type,
        "value": synthesis_value[:500],
        "intensity": synthesis_intensity,
        "prior_count": prior_count,
        "compounding_factor": round(1.0 + (prior_count * 0.1), 2),
    }
    result["synthesis"] = synthesis
    result["meta"]["steps_completed"] += 1

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 4: COMPOUND — Write synthesis engram ─────────────
    if write_engrams:
        try:
            from ..engram_ops import _brain_write_engram_impl
            synthesis_key = f"fusion_synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            _brain_write_engram_impl(
                key=synthesis_key,
                value=synthesis_value[:500],
                context=context,
                intensity=synthesis_intensity,
            )
            result["meta"]["engrams_written"] += 1
            synthesis["key"] = synthesis_key
        except Exception as e:
            logger.warning(f"Synthesis write failed: {e}")

    result["meta"]["steps_completed"] += 1
    return _finalize(result, start)


def _finalize(result: Dict, start: float) -> Dict:
    """Add final timing metadata."""
    elapsed = (time.time() - start) * 1000
    result["meta"]["execution_time_ms"] = round(elapsed, 1)
    return result
