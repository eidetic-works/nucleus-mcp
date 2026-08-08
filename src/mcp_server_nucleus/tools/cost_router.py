"""MCP tool facade for W5 cost routing.

Exposes ``nucleus_route`` — a single-action tool that routes a prompt to
the cheapest capable model tier and returns a cost estimate.

Action:
  route  - Route a prompt. params: {prompt, complexity?, context?}
           complexity ∈ {'routine', 'complex', 'sovereign'} (default 'routine')
           context: optional dict, e.g. {"sovereign": true}

This module follows the Super-Tools facade pattern used by other tool modules.
"""

import json
import logging

from ._dispatch import async_dispatch, resolve_make_response

logger = logging.getLogger("nucleus.tool.cost_router")


def register(mcp, helpers):
    """Register the nucleus_route facade tool."""
    make_response = resolve_make_response(helpers)

    from ..runtime.cost_router import route_call, cost_summary

    def _h_route(**params):
        prompt = params.get("prompt", "")
        complexity = params.get("complexity", "routine")
        context = params.get("context") or {}
        estimated_output_tokens = params.get("estimated_output_tokens")

        if complexity not in ("routine", "complex", "sovereign"):
            return make_response(
                False,
                error=f"Invalid complexity '{complexity}'. Choose: routine | complex | sovereign",
            )

        decision = route_call(
            prompt=prompt,
            complexity=complexity,
            context=context,
            estimated_output_tokens=estimated_output_tokens,
        )
        data = cost_summary(decision)
        return make_response(True, data=data)

    ROUTER = {"route": _h_route}

    # _h_route absorbs **params; declare its contract so _dispatch can reject
    # unknown keys (see _dispatch._allowed_param_names). Keys transcribed from
    # the handler body above — every params.get() covered, nothing extra.
    _h_route._nucleus_params = (
        "prompt", "complexity", "context", "estimated_output_tokens",
    )
    _LOG_LABELS = {"route": "nucleus_route failed"}

    @mcp.tool(title="Cost Router", annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_route(action: str, params: dict = {}) -> str:
        """W5 tier routing — route a prompt to the optimal model tier.

Actions:
  route  - Route a prompt to cheapest capable model.
           params: {prompt, complexity?, context?, estimated_output_tokens?}
           complexity ∈ 'routine' | 'complex' | 'sovereign' (default 'routine')
           Returns: provider, model, cost estimates, sovereignty tier.
"""
        return await async_dispatch(
            action,
            params,
            ROUTER,
            "nucleus_route",
        )

    return [("nucleus_route", nucleus_route)]
