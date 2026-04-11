"""FLYWHEEL — the compounding loop engine.

Every failure → ticket → curriculum pair → next training run.
Every success → CSR claim bump → dashboard delta.

Super-Tools Facade: 6 actions exposed via a single
`nucleus_flywheel(action, params)` MCP tool.
"""

import json
from pathlib import Path

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_flywheel facade tool with the MCP server."""

    def _get_flywheel():
        from ..flywheel import Flywheel
        from ..runtime.common import get_brain_path
        return Flywheel(get_brain_path())

    def _ticket(step="", error="", logs="", phase=""):
        if not step or not error:
            return json.dumps({
                "error": "step and error are required",
                "usage": "nucleus_flywheel(action='ticket', params={step, error, logs?, phase?})",
            }, indent=2)
        fw = _get_flywheel()
        return json.dumps(fw.file_ticket(step=step, error=error, logs=logs, phase=phase), indent=2)

    def _survived(phase="unknown", step=""):
        fw = _get_flywheel()
        return json.dumps(fw.record_survived(phase=phase, step=step), indent=2)

    def _csr():
        fw = _get_flywheel()
        return json.dumps(fw.csr(), indent=2)

    def _dashboard(html=False):
        from ..flywheel import render_dashboard_html, render_dashboard_json
        from ..runtime.common import get_brain_path
        bp = get_brain_path()
        if html:
            return render_dashboard_html(bp)
        return json.dumps(render_dashboard_json(bp), indent=2)

    def _week_report(week=None):
        from ..flywheel import generate_week_report
        from ..runtime.common import get_brain_path
        out_path = generate_week_report(get_brain_path(), week=week)
        return json.dumps({"wrote": str(out_path)}, indent=2)

    def _curriculum_refresh():
        from ..flywheel import curriculum_refresh
        from ..runtime.common import get_brain_path
        return json.dumps(curriculum_refresh(get_brain_path()), indent=2)

    ROUTER = {
        "ticket": lambda step="", error="", logs="", phase="": _ticket(step, error, logs, phase),
        "survived": lambda phase="unknown", step="": _survived(phase, step),
        "csr": lambda: _csr(),
        "dashboard": lambda html=False: _dashboard(html),
        "week_report": lambda week=None: _week_report(week),
        "curriculum_refresh": lambda: _curriculum_refresh(),
    }

    @mcp.tool()
    def nucleus_flywheel(action: str, params: dict = None) -> str:
        """FLYWHEEL — the compounding loop engine.

Every failure files a ticket (6 actions), every success bumps CSR.
Claim Survival Rate is the scalar that proves the system is getting more
trustworthy over time.

Actions:
  ticket              - File a failure ticket. params: {step, error, logs?, phase?}
                        Fires all 6 accountability actions (memory note,
                        CSR bump, training pair seed, week report append,
                        GitHub issue, task queue).
  survived            - Record a survived claim. params: {phase?, step?}
  csr                 - Read current CSR state.
  dashboard           - Read dashboard state. params: {html?: bool}
  week_report         - Regenerate current week's report. params: {week?: int}
  curriculum_refresh  - Close the loop: promote ready pairs from pending→ready.

The flywheel writes to `.brain/flywheel/` and the unified training exports
directory. All writes are best-effort and idempotent.
"""
        params = params or {}
        return dispatch(action, params, ROUTER, "nucleus_flywheel")

    return [("nucleus_flywheel", nucleus_flywheel)]
