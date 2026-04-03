"""ALIGN — Human correction frontier.

Verify. Correct. Compound.
GROUND catches machine errors. ALIGN catches human-visible errors.
Every correction trains the system.

Super-Tools Facade: correct + approve + stats via nucleus_align(action, params).
"""

import json
from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_align facade tool with the MCP server."""

    def _correct(context="", correction="", expected="", severity="medium"):
        from ..runtime.align_ops import record_correction
        result = record_correction(
            context=context, correction=correction,
            expected=expected, severity=severity,
        )
        return json.dumps(result, indent=2, default=str)

    def _approve(context="", notes=""):
        from ..runtime.align_ops import record_approval
        result = record_approval(context=context, notes=notes)
        return json.dumps(result, indent=2, default=str)

    def _stats():
        from ..runtime.align_ops import get_align_stats
        result = get_align_stats()
        return json.dumps(result, indent=2, default=str)

    ROUTER = {
        "correct": lambda context="", correction="", expected="",
                         severity="medium": _correct(context, correction, expected, severity),
        "approve": lambda context="", notes="": _approve(context, notes),
        "stats": lambda: _stats(),
    }

    @mcp.tool()
    def nucleus_align(action: str, params: dict = None) -> str:
        """ALIGN — Human correction frontier. Every correction trains the system.

Actions:
  correct  - Record a correction. params: {context, correction, expected?, severity?}
             context: what the AI produced (wrong output)
             correction: what it should have been
             expected: what was originally asked for (optional)
             severity: low/medium/high (default: medium)
  approve  - Approve an output (positive signal). params: {context, notes?}
  stats    - Get alignment statistics (approval rate, severity breakdown)

Each correction automatically:
  1. Writes verdict to human_verdicts.jsonl
  2. Records ALIGN Delta (gap measurement)
  3. Creates DPO training pair (chosen=correction, rejected=original)
  4. Emits align_reviewed event (feeds substrate)
"""
        params = params or {}
        return dispatch(action, params, ROUTER, "nucleus_align")

    return [("nucleus_align", nucleus_align)]
