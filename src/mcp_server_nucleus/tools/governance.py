"""Governance & Hypervisor tools — lock/unlock, watch, hypervisor mode, egress proxy.

Super-Tools Facade: 19 governance actions exposed via a single
`nucleus_governance(action, params)` MCP tool. Grouped by family:

  Hypervisor (5):  lock, unlock, set_mode, watch, status
  Governance (2):  list_directory, delete_file
  Egress (2):      curl, pip_install
  Protocol (1):    validate_strategic_plan
  Compliance (5):  comply_list, comply_apply, comply_report,
                   audit_report, kyc_review
  Status (1):      sovereign_status
  DSoR (2):        trace_list, trace_view
  Auto-fix (1):    auto_fix_loop

See the `nucleus_governance` tool docstring below for per-action params.
"""
import logging
logger = logging.getLogger(__name__)

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

from ._dispatch import async_dispatch

# ── DSoR-Verifier gating seam (flag-gated; default OFF) — A12 ───────────────
# When NUCLEUS_GOVERNANCE_ANCHOR is truthy:
#   - validate_strategic_plan no longer trusts a bare regex match of the
#     submitter's own text: each [BB##] tag must map to a real entry in the
#     committed Big Bang registry artifact (docs/reports/nucleus_bigbang_30d.md,
#     the exact file the protocol's own error message already points at).
#   - the audit_report "sovereignty verified" checklist item is no longer a
#     hardcoded pass: it reflects whether the actual event log recorded any
#     egress activity (see runtime/audit_report.py::_generate_checklist).
# With the flag OFF this whole path is skipped and behavior is byte-identical
# to the legacy regex-only check.
_GOVERNANCE_ANCHOR_ENV = "NUCLEUS_GOVERNANCE_ANCHOR"

# The artifact validate_strategic_plan's own protocol error message already
# names as the Big Bang source of truth. No separate BB registry (file/DB/
# module) exists anywhere else in this repo (grep-verified) — so rather than
# inventing a new registry, the anchor check opens *this* committed artifact.
_BIGBANG_REGISTRY_REL_PATH = "docs/reports/nucleus_bigbang_30d.md"


def _governance_anchor_enabled() -> bool:
    """Is registry-anchored governance validation turned on? Read live (not
    cached) so tests can flip it per-case."""
    return os.environ.get(_GOVERNANCE_ANCHOR_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _bigbang_registry_path() -> Path:
    """Resolve the Big Bang insight registry path. Follows the same
    NUCLEUS_PROJECT_ROOT convention used elsewhere (runtime/satellite_ops.py),
    falling back to cwd."""
    root = Path(os.environ.get("NUCLEUS_PROJECT_ROOT", str(Path.cwd())))
    return root / _BIGBANG_REGISTRY_REL_PATH


def _unregistered_bb_refs(bb_refs: List[str]) -> List[str]:
    """Anchor check: which [BB##] tags do NOT map to a real entry in the
    committed Big Bang registry artifact?

    A tag is "registered" if its bare form (e.g. "BB01") appears in the
    registry file's committed content. If the registry file doesn't exist at
    all, nothing is registered — every ref is unverified (fails closed, not
    open: an absent registry proves nothing, so no [BB##] can be trusted).
    """
    registry_path = _bigbang_registry_path()
    if not registry_path.exists():
        return list(bb_refs)
    try:
        registry_text = registry_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return list(bb_refs)
    return [ref for ref in bb_refs if ref.strip("[]") not in registry_text]


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

    def _safe_emit(event_type, data, description=""):
        """Wrap _emit_event; never let event emission break the action.

        Emits with emitter='nucleus_governance' for downstream attribution.
        """
        try:
            _emit_event(event_type, "nucleus_governance", data or {}, description=description)
        except Exception:
            logger.debug("Swallowed exception in register", exc_info=True)
            pass  # Event emission failure must never break governance actions

    def _auto_fix_loop(file_path, verification_command):
        from ..runtime.loops.fixer import FixerLoop
        from .orchestration import _fix_code_impl
        _safe_emit(
            "governance_auto_fix_loop_started",
            {"file_path": file_path, "verification_command": verification_command},
            description=f"auto_fix_loop started on {file_path}",
        )
        loop = FixerLoop(
            target_file=file_path,
            verification_command=verification_command,
            fixer_func=_fix_code_impl,
            max_retries=3
        )
        try:
            result = loop.run()
            _safe_emit(
                "governance_auto_fix_loop_completed",
                {"file_path": file_path, "result_keys": sorted(list(result.keys())) if isinstance(result, dict) else None},
                description=f"auto_fix_loop completed on {file_path}",
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            _safe_emit(
                "governance_auto_fix_loop_failed",
                {"file_path": file_path, "error": str(e)[:200]},
                description=f"auto_fix_loop failed on {file_path}",
            )
            raise

    def _lock(path):
        result = lock_resource_impl(path)
        _safe_emit(
            "governance_lock_applied",
            {"path": path},
            description=f"lock applied to {path}",
        )
        return result

    def _unlock(path):
        result = unlock_resource_impl(path)
        _safe_emit(
            "governance_unlock_applied",
            {"path": path},
            description=f"unlock applied to {path}",
        )
        return result

    def _set_mode(mode):
        result = set_hypervisor_mode_impl(mode)
        _safe_emit(
            "governance_mode_changed",
            {"mode": mode},
            description=f"hypervisor mode set to {mode}",
        )
        return result

    def _list_directory(path):
        result = nucleus_list_directory_impl(path)
        _safe_emit(
            "governance_directory_listed",
            {"path": path},
            description=f"directory listed: {path}",
        )
        return result

    def _watch(path):
        result = watch_resource_impl(path)
        _safe_emit(
            "governance_watch_registered",
            {"path": path},
            description=f"watch registered for {path}",
        )
        return result

    def _curl(url, method="GET"):
        result = nucleus_curl_impl(url, method)
        # Audit trail for egress; do not log full URL query/path content,
        # but record the scheme+host for compliance review.
        # Use parsed.hostname (not parsed.netloc) to drop any user:pass@ prefix
        # so URL-embedded basic-auth credentials are not leaked into events.
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url or "")
            host_summary = f"{parsed.scheme}://{parsed.hostname}" if parsed.scheme and parsed.hostname else (url or "")[:120]
        except Exception:
            logger.debug("Swallowed exception in register", exc_info=True)
            host_summary = (url or "")[:120]
        _safe_emit(
            "governance_egress_curl",
            {"method": method, "host": host_summary},
            description=f"curl {method} {host_summary}",
        )
        return result

    def _pip_install(package):
        result = nucleus_pip_install_impl(package)
        _safe_emit(
            "governance_egress_pip_install",
            {"package": (package or "")[:200]},
            description=f"pip_install {package}",
        )
        return result

    def _validate_strategic_plan(plan_text, mode="strategic"):
        """Enforce v3.2 protocol: Strategic mode PLANs must reference Big Bang insights.

        Returns a pass/fail verdict. Refuses strategic work if no [BB##] reference found.
        """
        if not isinstance(mode, str):
            return json.dumps({"valid": False, "error": f"mode must be str, got {type(mode).__name__}"})
        if not isinstance(plan_text, str) and plan_text is not None:
            return json.dumps({"valid": False, "error": f"plan_text must be str, got {type(plan_text).__name__}"})
        if mode.lower() != "strategic":
            _safe_emit(
                "governance_strategic_plan_validated",
                {"mode": mode, "valid": True, "skipped_reason": "tactical"},
                description="strategic plan validation skipped (tactical mode)",
            )
            return json.dumps({"valid": True, "mode": mode, "message": "TACTICAL mode — Big Bang reference not required."})

        # Match [BB##] pattern (e.g., [BB01], [BB12])
        bb_refs = re.findall(r'\[BB\d{2,}\]', plan_text or "")

        if not bb_refs:
            _safe_emit(
                "governance_strategic_plan_rejected",
                {"mode": "strategic", "reason": "no_bigbang_refs"},
                description="strategic PLAN rejected: missing [BB##] reference",
            )
            return json.dumps({
                "valid": False,
                "mode": "strategic",
                "error": "PROTOCOL VIOLATION: Strategic mode PLAN must reference at least one Big Bang insight [BB##] from docs/reports/nucleus_bigbang_30d.md.",
                "hint": "Add a 'Big Bang Insight Used:' section with at least one [BB##] reference.",
            })

        anchor_on = _governance_anchor_enabled()
        if anchor_on:
            unregistered = _unregistered_bb_refs(bb_refs)
            if unregistered:
                _safe_emit(
                    "governance_strategic_plan_rejected",
                    {"mode": "strategic", "reason": "bb_ref_not_registered", "unregistered_refs": unregistered},
                    description=f"strategic PLAN rejected: [BB##] ref(s) not found in registry: {unregistered}",
                )
                return json.dumps({
                    "valid": False,
                    "mode": "strategic",
                    "error": (
                        "PROTOCOL VIOLATION: [BB##] reference(s) "
                        f"{unregistered} do not map to a real entry in "
                        f"{_BIGBANG_REGISTRY_REL_PATH}. Citing a [BB##] tag requires "
                        "a real registered Big Bang insight, not just a matching string."
                    ),
                    "hint": f"Register the insight in {_BIGBANG_REGISTRY_REL_PATH} before citing it, or remove the reference.",
                    "unregistered_refs": unregistered,
                })

        _safe_emit(
            "governance_strategic_plan_validated",
            {"mode": "strategic", "valid": True, "bb_ref_count": len(bb_refs)},
            description=f"strategic PLAN validated with {len(bb_refs)} Big Bang ref(s)",
        )
        result = {
            "valid": True,
            "mode": "strategic",
            "big_bang_refs": bb_refs,
            "message": f"✅ Strategic PLAN validated. {len(bb_refs)} Big Bang insight(s) referenced.",
        }
        if anchor_on:
            result["anchor_verified"] = True
        return json.dumps(result)

    def _comply_list():
        """List available jurisdictions."""
        return json.dumps(list_jurisdictions(), indent=2)

    def _comply_apply(jurisdiction, brain_path=None):
        """Apply a jurisdiction configuration."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        result = apply_jurisdiction(bp, jurisdiction)
        _safe_emit(
            "governance_jurisdiction_applied",
            {"jurisdiction": jurisdiction, "brain_path": str(bp)},
            description=f"jurisdiction applied: {jurisdiction}",
        )
        return json.dumps(result, indent=2, default=str)

    def _comply_report(brain_path=None):
        """Generate compliance status report."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        report = generate_compliance_report(bp)
        _safe_emit(
            "governance_compliance_report_generated",
            {"brain_path": str(bp)},
            description="compliance status report generated",
        )
        return json.dumps(report, indent=2, default=str)

    def _audit_report(report_format="text", since_hours=None, brain_path=None):
        """Generate audit-ready compliance report."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        report = generate_audit_report(bp, report_format=report_format, since_hours=since_hours)
        _safe_emit(
            "governance_audit_report_generated",
            {"report_format": report_format, "since_hours": since_hours, "brain_path": str(bp)},
            description=f"audit report generated ({report_format})",
        )
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
        env = os.environ.get("NUCLEUS_BRAIN_PATH")
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
        _safe_emit(
            "governance_kyc_review_completed",
            {"application_id": application_id, "brain_path": str(bp)},
            description=f"kyc review completed for {application_id}",
        )
        return json.dumps(result, indent=2, default=str)

    def _sovereign_status(brain_path=None):
        """Get sovereignty posture report."""
        from pathlib import Path
        bp = Path(brain_path) if brain_path else _get_brain_path()
        report = generate_sovereign_status(bp)
        formatted = format_sovereign_status(report)
        _safe_emit(
            "governance_sovereign_status_generated",
            {
                "sovereignty_score": report.get("sovereignty_score"),
                "brain_path": str(bp),
            },
            description=f"sovereign status generated (score={report.get('sovereignty_score')})",
        )
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
        "lock": lambda path: _lock(path),
        "unlock": lambda path: _unlock(path),
        "set_mode": lambda mode: _set_mode(mode),
        "list_directory": lambda path: _list_directory(path),
        "delete_file": lambda path, confirm=False: nucleus_delete_file_impl(path, emit_event_fn=_emit_event, confirm=confirm),
        "watch": lambda path: _watch(path),
        "status": lambda: hypervisor_status_impl(),
        "curl": lambda url, method="GET": _curl(url, method),
        "pip_install": lambda package: _pip_install(package),
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

    @mcp.tool(title="Governance", annotations={"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False})
    async def nucleus_governance(action: str, params: dict = None) -> str:
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
        return await async_dispatch(action, params, ROUTER, "nucleus_governance")

    return [("nucleus_governance", nucleus_governance)]
