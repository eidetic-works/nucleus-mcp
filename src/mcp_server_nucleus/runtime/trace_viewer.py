"""DSoR Trace Viewer — Browse and inspect decision trails.

Provides CLI access to Decision System of Record (DSoR) traces:
  - List all traces with summary
  - View detailed trace by ID
  - Query traces by type, date, or recommendation
  - Export traces for regulatory submission
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nucleus.trace_viewer")


def list_traces(brain_path: Path, trace_type: Optional[str] = None) -> Dict[str, Any]:
    """List all DSoR traces in the brain."""
    dsor_dir = brain_path / "dsor"
    traces = []

    if not dsor_dir.exists():
        return {"count": 0, "traces": [], "status": "no_dsor_directory"}

    for f in sorted(dsor_dir.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
                summary = {
                    "file": f.name,
                    "type": data.get("type", "unknown"),
                    "review_id": data.get("review_id", f.stem),
                    "recommendation": data.get("recommendation", "N/A"),
                    "risk_score": data.get("risk_score"),
                    "applicant": data.get("applicant"),
                    "started_at": data.get("started_at"),
                    "completed_at": data.get("completed_at"),
                    "trail_steps": len(data.get("decision_trail", [])),
                }
                if trace_type and data.get("type") != trace_type:
                    continue
                traces.append(summary)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error reading {f}: {e}")

    return {
        "count": len(traces),
        "traces": traces,
        "types": list(set(t["type"] for t in traces)),
    }


def get_trace(brain_path: Path, trace_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific DSoR trace by ID."""
    dsor_dir = brain_path / "dsor"

    if not dsor_dir.exists():
        return None

    # Try exact filename match first
    trace_file = dsor_dir / f"{trace_id}.json"
    if trace_file.exists():
        with open(trace_file) as f:
            return json.load(f)

    # Try partial match on review_id
    for f in dsor_dir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
                if data.get("review_id", "").startswith(trace_id):
                    return data
        except (json.JSONDecodeError, Exception):
            continue

    return None


def format_trace_list(data: Dict) -> str:
    """Format trace list for terminal output."""
    lines = []
    lines.append("")
    lines.append("  📋 DSoR TRACES")
    lines.append("  " + "=" * 60)

    if data["count"] == 0:
        lines.append("    (No traces found)")
        lines.append("")
        lines.append("  Run `nucleus kyc demo` to generate sample traces.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"  Total: {data['count']} traces | Types: {', '.join(data.get('types', []))}")
    lines.append("")

    for t in data["traces"]:
        icon = {"APPROVE": "✅", "ESCALATE": "⚠️", "REJECT": "❌"}.get(t.get("recommendation", ""), "📋")
        lines.append(f"  {icon}  {t['review_id']}")
        lines.append(f"     Type: {t['type']} | Rec: {t.get('recommendation', 'N/A')}")
        if t.get("applicant"):
            lines.append(f"     Applicant: {t['applicant']}")
        if t.get("risk_score") is not None:
            lines.append(f"     Risk: {t['risk_score']}/100 | Steps: {t['trail_steps']}")
        if t.get("completed_at"):
            lines.append(f"     Date: {t['completed_at'][:19]}")
        lines.append("")

    lines.append(f"  View details: nucleus trace view <TRACE_ID>")
    lines.append("")
    return "\n".join(lines)


def format_trace_detail(trace: Dict) -> str:
    """Format a single trace for detailed terminal output."""
    lines = []
    rec = trace.get("recommendation", "N/A")
    icon = {"APPROVE": "✅", "ESCALATE": "⚠️", "REJECT": "❌"}.get(rec, "📋")

    lines.append("")
    lines.append("  " + "=" * 65)
    lines.append(f"  {icon}  DSoR TRACE — {trace.get('review_id', 'Unknown')}")
    lines.append("  " + "=" * 65)
    lines.append("")
    lines.append(f"  Type:           {trace.get('type', 'unknown')}")
    lines.append(f"  Application:    {trace.get('application_id', 'N/A')}")
    lines.append(f"  Applicant:      {trace.get('applicant', 'N/A')}")
    lines.append(f"  Risk Score:     {trace.get('risk_score', 'N/A')}/100")
    lines.append(f"  Risk Level:     {trace.get('risk_level', 'N/A')}")
    lines.append(f"  Recommendation: {icon} {rec}")
    lines.append(f"  Started:        {trace.get('started_at', 'N/A')}")
    lines.append(f"  Completed:      {trace.get('completed_at', 'N/A')}")
    lines.append(f"  HITL Required:  {'Yes' if trace.get('hitl_required') else 'No'}")
    lines.append("")

    # Decision trail
    trail = trace.get("decision_trail", [])
    if trail:
        lines.append("  DECISION TRAIL:")
        lines.append("  " + "-" * 55)
        for step in trail:
            lines.append(f"    Step {step.get('step', '?')}: {step.get('action', 'Unknown')}")
            lines.append(f"      Result:    {step.get('result', '?')}")
            lines.append(f"      Reasoning: {step.get('reasoning', '?')[:70]}")
            lines.append(f"      Risk +/-:  {step.get('risk_impact', 0)}")
            lines.append(f"      Time:      {step.get('timestamp', '?')}")
            lines.append("")

    # Sovereignty guarantee
    if trace.get("sovereign_guarantee"):
        lines.append(f"  🔒 {trace['sovereign_guarantee']}")

    lines.append("  " + "=" * 65)
    lines.append("")
    return "\n".join(lines)
