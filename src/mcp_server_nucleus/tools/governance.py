"""Governance & Hypervisor tools — lock/unlock, watch, hypervisor mode, egress proxy.

Super-Tools Facade: All 10 governance actions exposed via a single
`nucleus_governance(action, params)` MCP tool.
"""

import json
import re
import sys
from typing import Dict, Any

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_governance facade tool with the MCP server."""
    from ..runtime.hypervisor_ops import (
        lock_resource_impl, unlock_resource_impl, set_hypervisor_mode_impl,
        nucleus_list_directory_impl, nucleus_delete_file_impl,
        watch_resource_impl, hypervisor_status_impl,
    )
    from ..core.egress_proxy import nucleus_curl_impl, nucleus_pip_install_impl
    from ..runtime.event_ops import _emit_event
    from ..runtime.compliance_config import (
        list_jurisdictions, apply_jurisdiction,
        generate_compliance_report, format_compliance_report,
    )
    from ..runtime.audit_report import generate_audit_report
    from ..runtime.kyc_demo import run_kyc_review, format_kyc_review
    from ..runtime.sovereign_status import generate_sovereign_status, format_sovereign_status
    from ..runtime.trace_viewer import list_traces, get_trace, format_trace_list, format_trace_detail

    def _auto_fix_loop(file_path, verification_command):
        from ..runtime.loops.fixer import FixerLoop
        from .orchestration import _fix_code_impl
        loop = FixerLoop(
            target_file=file_path,
            verification_command=verification_command,
            fixer_func=_fix_code_impl,
            max_retries=3
        )
        return json.dumps(loop.run(), indent=2)

    def _validate_strategic_plan(plan_text, mode="strategic"):
        """Enforce v3.2 protocol: Strategic mode PLANs must reference Big Bang insights.
        
        Returns a pass/fail verdict. Refuses strategic work if no [BB##] reference found.
        """
        if mode.lower() != "strategic":
            return json.dumps({"valid": True, "mode": mode, "message": "TACTICAL mode — Big Bang reference not required."})
        
        # Match [BB##] pattern (e.g., [BB01], [BB12])
        bb_refs = re.findall(r'\[BB\d{2,}\]', plan_text or "")
        
        if not bb_refs:
            return json.dumps({
                "valid": False,
                "mode": "strategic",
                "error": "PROTOCOL VIOLATION: Strategic mode PLAN must reference at least one Big Bang insight [BB##] from docs/reports/nucleus_bigbang_30d.md.",
                "hint": "Add a 'Big Bang Insight Used:' section with at least one [BB##] reference.",
            })
        
        return json.dumps({
            "valid": True,
            "mode": "strategic",
            "big_bang_refs": bb_refs,
            "message": f"✅ Strategic PLAN validated. {len(bb_refs)} Big Bang insight(s) referenced.",
        })

    def _comply_list():
        """List available jurisdictions."""
        return json.dumps(list_jurisdictions(), indent=2)

    def _comply_apply(jurisdiction, brain_path=None):
        """Apply a jurisdiction configuration."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        result = apply_jurisdiction(bp, jurisdiction)
        return json.dumps(result, indent=2, default=str)

    def _comply_report(brain_path=None):
        """Generate compliance status report."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        report = generate_compliance_report(bp)
        return json.dumps(report, indent=2, default=str)

    def _audit_report(report_format="text", since_hours=None, brain_path=None):
        """Generate audit-ready compliance report."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        report = generate_audit_report(bp, report_format=report_format, since_hours=since_hours)
        if report_format == "json":
            return report["formatted"]
        return json.dumps({
            "formatted": report["formatted"],
            "jurisdiction": report.get("jurisdiction"),
            "sections_summary": {
                k: {"count": v.get("count", 0)} for k, v in report.get("sections", {}).items()
                if isinstance(v, dict) and "count" in v
            },
        }, indent=2, default=str)

    def _get_brain_path():
        """Auto-detect brain path."""
        import os
        from pathlib import Path
        env = os.environ.get("NUCLEAR_BRAIN_PATH")
        if env:
            return Path(env)
        cwd = Path.cwd() / ".brain"
        if cwd.exists():
            return cwd
        return Path(".brain")

    def _kyc_review(application_id="APP-001", brain_path=None):
        """Run a KYC review via MCP tool."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        result = run_kyc_review(application_id, bp, write_dsor=True)
        return json.dumps(result, indent=2, default=str)

    def _sovereign_status(brain_path=None):
        """Get sovereignty posture report."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        report = generate_sovereign_status(bp)
        formatted = format_sovereign_status(report)
        return json.dumps({
            "sovereignty_score": report["sovereignty_score"],
            "formatted": formatted,
            "brain_path": str(bp),
        }, indent=2, default=str)

    def _trace_list(trace_type=None, brain_path=None):
        """List DSoR traces."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        data = list_traces(bp, trace_type=trace_type)
        return json.dumps(data, indent=2, default=str)

    def _trace_view(trace_id, brain_path=None):
        """View a specific DSoR trace."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        trace = get_trace(bp, trace_id)
        if not trace:
            return json.dumps({"error": f"Trace not found: {trace_id}"})
        return json.dumps(trace, indent=2, default=str)

    ROUTER = {
        "auto_fix_loop": lambda file_path, verification_command: _auto_fix_loop(file_path, verification_command),
        "lock": lambda path: lock_resource_impl(path),
        "unlock": lambda path: unlock_resource_impl(path),
        "set_mode": lambda mode: set_hypervisor_mode_impl(mode),
        "list_directory": lambda path: nucleus_list_directory_impl(path),
        "delete_file": lambda path, confirm=False: nucleus_delete_file_impl(path, emit_event_fn=_emit_event, confirm=confirm),
        "watch": lambda path: watch_resource_impl(path),
        "status": lambda: hypervisor_status_impl(),
        "curl": lambda url, method="GET": nucleus_curl_impl(url, method),
        "pip_install": lambda package: nucleus_pip_install_impl(package),
        "validate_strategic_plan": lambda plan_text, mode="strategic": _validate_strategic_plan(plan_text, mode),
        "comply_list": lambda: _comply_list(),
        "comply_apply": lambda jurisdiction, brain_path=None: _comply_apply(jurisdiction, brain_path),
        "comply_report": lambda brain_path=None: _comply_report(brain_path),
        "audit_report": lambda report_format="text", since_hours=None, brain_path=None: _audit_report(report_format, since_hours, brain_path),
        "kyc_review": lambda application_id="APP-001", brain_path=None: _kyc_review(application_id, brain_path),
        "sovereign_status": lambda brain_path=None: _sovereign_status(brain_path),
        "trace_list": lambda trace_type=None, brain_path=None: _trace_list(trace_type, brain_path),
        "trace_view": lambda trace_id="", brain_path=None: _trace_view(trace_id, brain_path),
    }

    @mcp.tool()
    def nucleus_governance(action: str, params: dict = None) -> str:
        """Governance, Hypervisor & security tools for the Nucleus Agent OS.

Actions:
  auto_fix_loop   - Auto-fix loop: Verify->Diagnose->Fix->Verify (3 retries). params: {file_path, verification_command}
  lock            - [HYPERVISOR] Lock a file/dir immutable (chflags uchg). params: {path}
  unlock          - [HYPERVISOR] Unlock a file/dir. params: {path}
  set_mode        - [HYPERVISOR] Switch IDE context: "red" or "blue". params: {mode}
  list_directory  - [GOVERNANCE] List files in a directory. params: {path}
  delete_file     - [GOVERNANCE] Delete a file (governed by Hypervisor). params: {path, confirm?}. HITL: requires confirm=true.
  watch           - [HYPERVISOR] Monitor a file/folder for changes. params: {path}
  status          - [HYPERVISOR] Report current security state of Agent OS
  curl            - [EGRESS] Proxied HTTP fetch for air-gapped agents. params: {url, method?}
  pip_install     - [EGRESS] Proxied pip install for air-gapped agents. params: {package}
  validate_strategic_plan - [PROTOCOL] Validate Strategic mode PLAN has Big Bang [BB##] refs. params: {plan_text, mode?}
  comply_list     - [COMPLIANCE] List available regulatory jurisdictions
  comply_apply    - [COMPLIANCE] Apply jurisdiction config. params: {jurisdiction, brain_path?}
  comply_report   - [COMPLIANCE] Generate compliance status report. params: {brain_path?}
  audit_report    - [COMPLIANCE] Generate audit-ready report. params: {report_format?, since_hours?, brain_path?}
  kyc_review      - [COMPLIANCE] Run KYC demo review. params: {application_id?, brain_path?}
  sovereign_status - [STATUS] Get sovereignty posture report. params: {brain_path?}
  trace_list      - [DSoR] List decision traces. params: {trace_type?, brain_path?}
  trace_view      - [DSoR] View specific trace. params: {trace_id, brain_path?}
"""
        params = params or {}
        return dispatch(action, params, ROUTER, "nucleus_governance")

    return [("nucleus_governance", nucleus_governance)]
