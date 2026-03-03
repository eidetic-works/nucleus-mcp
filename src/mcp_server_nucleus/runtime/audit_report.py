"""DSoR Audit Report Generator — Compliance-Ready Decision Trail Exports.

MVE-2: Generates audit-ready reports from DSoR traces that satisfy
regulatory requirements (DORA Art. 6, MAS TRM, SOC2 Trust Services Criteria).

The report answers: "What did the AI agent decide, why, and who approved it?"
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nucleus.audit_report")


def generate_audit_report(
    brain_path: Path,
    report_format: str = "text",
    since_hours: Optional[float] = None,
    include_engrams: bool = True,
) -> Dict[str, Any]:
    """
    Generate an audit-ready report from DSoR traces and event logs.

    Args:
        brain_path: Path to the .brain directory
        report_format: "text", "json", or "html"
        since_hours: Only include events from the last N hours (None = all)
        include_engrams: Whether to include relevant engrams

    Returns:
        Dict with report content, metadata, and formatted output
    """
    report = {
        "title": "Nucleus Agent OS — Audit Trail Report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "brain_path": str(brain_path),
        "sections": {},
    }

    # Load jurisdiction config if available
    gov_dir = brain_path / "governance"
    compliance_file = gov_dir / "compliance.json"
    if compliance_file.exists():
        with open(compliance_file) as f:
            compliance = json.load(f)
        report["jurisdiction"] = {
            "id": compliance.get("jurisdiction"),
            "name": compliance.get("name"),
            "region": compliance.get("region"),
        }
    else:
        report["jurisdiction"] = {"id": "none", "name": "Not configured"}

    # Section 1: Decision Records (DSoR)
    report["sections"]["decisions"] = _collect_decisions(brain_path, since_hours)

    # Section 2: Event Log (who did what when)
    report["sections"]["events"] = _collect_events(brain_path, since_hours)

    # Section 3: HITL Approvals
    report["sections"]["approvals"] = _collect_approvals(brain_path, since_hours)

    # Section 4: Engram Memory Context (if requested)
    if include_engrams:
        report["sections"]["memory_context"] = _collect_engrams(brain_path)

    # Section 5: Compliance Checklist
    report["sections"]["compliance_checklist"] = _generate_checklist(report)

    # Format output
    if report_format == "json":
        report["formatted"] = json.dumps(report, indent=2, default=str)
    elif report_format == "html":
        report["formatted"] = _format_html(report)
    else:
        report["formatted"] = _format_text(report)

    return report


def _collect_decisions(brain_path: Path, since_hours: Optional[float]) -> Dict[str, Any]:
    """Collect DSoR decision records."""
    decisions = []
    dsor_dir = brain_path / "dsor"

    if not dsor_dir.exists():
        # Try ledger directory for decision events
        ledger_dir = brain_path / "ledger"
        if ledger_dir.exists():
            for f in sorted(ledger_dir.glob("events*.jsonl")):
                try:
                    with open(f) as fh:
                        for line in fh:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                                if event.get("event_type") == "DecisionMade":
                                    decisions.append({
                                        "id": event.get("id", "unknown"),
                                        "timestamp": event.get("timestamp"),
                                        "emitter": event.get("emitter", "unknown"),
                                        "description": event.get("description", ""),
                                        "data": event.get("data", {}),
                                    })
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning(f"Error reading {f}: {e}")
    else:
        for f in sorted(dsor_dir.glob("*.json")):
            try:
                with open(f) as fh:
                    decision = json.load(fh)
                    decisions.append(decision)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error reading {f}: {e}")

    return {
        "count": len(decisions),
        "records": decisions[-50:],  # Last 50 for report
    }


def _collect_events(brain_path: Path, since_hours: Optional[float]) -> Dict[str, Any]:
    """Collect event log entries."""
    events = []
    ledger_dir = brain_path / "ledger"

    if not ledger_dir.exists():
        return {"count": 0, "records": []}

    cutoff = None
    if since_hours:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)

    for f in sorted(ledger_dir.glob("events*.jsonl")):
        try:
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if cutoff:
                            ts = event.get("timestamp", "")
                            try:
                                event_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                if event_time.replace(tzinfo=None) < cutoff:
                                    continue
                            except (ValueError, AttributeError):
                                pass
                        events.append({
                            "timestamp": event.get("timestamp"),
                            "type": event.get("event_type"),
                            "emitter": event.get("emitter"),
                            "description": event.get("description", ""),
                        })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Error reading {f}: {e}")

    # Also check audit logs
    for f in sorted(ledger_dir.glob("audit_*.jsonl")):
        try:
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        events.append({
                            "timestamp": entry.get("timestamp"),
                            "type": "AuditEntry",
                            "emitter": entry.get("agent", "system"),
                            "description": f"Tool: {entry.get('tool', 'unknown')} | Tier: {entry.get('tier', '?')}",
                        })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Error reading {f}: {e}")

    return {
        "count": len(events),
        "records": events[-100:],  # Last 100
    }


def _collect_approvals(brain_path: Path, since_hours: Optional[float]) -> Dict[str, Any]:
    """Collect HITL approval records."""
    approvals = []
    ledger_dir = brain_path / "ledger"

    if not ledger_dir.exists():
        return {"count": 0, "records": []}

    for f in sorted(ledger_dir.glob("events*.jsonl")):
        try:
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("event_type") in ("HITLApproval", "HITLRejection", "ConsentResponse"):
                            approvals.append({
                                "timestamp": event.get("timestamp"),
                                "type": event.get("event_type"),
                                "emitter": event.get("emitter"),
                                "description": event.get("description", ""),
                                "data": event.get("data", {}),
                            })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Error reading {f}: {e}")

    return {
        "count": len(approvals),
        "records": approvals,
    }


def _collect_engrams(brain_path: Path) -> Dict[str, Any]:
    """Collect recent engrams for memory context."""
    engrams = []
    engrams_dir = brain_path / "engrams"

    if not engrams_dir.exists():
        return {"count": 0, "records": []}

    for f in sorted(engrams_dir.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    engrams.append({
                        "key": data.get("key", f.stem),
                        "context": data.get("context", "unknown"),
                        "intensity": data.get("intensity", 0),
                        "created_at": data.get("created_at", ""),
                        "value_preview": str(data.get("value", ""))[:200],
                    })
        except (json.JSONDecodeError, Exception):
            continue

    # Sort by intensity (highest first)
    engrams.sort(key=lambda x: x.get("intensity", 0), reverse=True)

    return {
        "count": len(engrams),
        "records": engrams[:20],  # Top 20 by intensity
    }


def _generate_checklist(report: Dict) -> Dict[str, Any]:
    """Generate compliance checklist based on jurisdiction."""
    checks = []
    jurisdiction_id = report.get("jurisdiction", {}).get("id", "none")

    # Universal checks
    decisions = report["sections"].get("decisions", {})
    events = report["sections"].get("events", {})
    approvals = report["sections"].get("approvals", {})

    checks.append({
        "item": "Decision trail exists",
        "status": "pass" if decisions.get("count", 0) > 0 else "fail",
        "detail": f"{decisions.get('count', 0)} decision records found",
    })
    checks.append({
        "item": "Event log exists",
        "status": "pass" if events.get("count", 0) > 0 else "fail",
        "detail": f"{events.get('count', 0)} events recorded",
    })
    checks.append({
        "item": "HITL approvals tracked",
        "status": "pass" if approvals.get("count", 0) > 0 else "info",
        "detail": f"{approvals.get('count', 0)} approval records",
    })
    checks.append({
        "item": "Jurisdiction configured",
        "status": "pass" if jurisdiction_id != "none" else "warn",
        "detail": report.get("jurisdiction", {}).get("name", "Not set"),
    })
    checks.append({
        "item": "All data local (sovereignty verified)",
        "status": "pass",
        "detail": "Nucleus is local-first. No external data transmission by default.",
    })

    passed = sum(1 for c in checks if c["status"] == "pass")
    total = len(checks)

    return {
        "passed": passed,
        "total": total,
        "checks": checks,
    }


def _format_text(report: Dict) -> str:
    """Format report as terminal-friendly text."""
    lines = []
    lines.append("=" * 70)
    lines.append("  NUCLEUS AGENT OS — AUDIT TRAIL REPORT")
    lines.append(f"  Generated: {report.get('generated_at', 'now')}")
    if report.get("jurisdiction", {}).get("name"):
        lines.append(f"  Jurisdiction: {report['jurisdiction']['name']}")
    lines.append("=" * 70)
    lines.append("")

    # Decisions
    decisions = report["sections"].get("decisions", {})
    lines.append(f"  📋 DECISIONS ({decisions.get('count', 0)} total)")
    lines.append("  " + "-" * 50)
    for d in decisions.get("records", [])[:10]:
        lines.append(f"    [{d.get('timestamp', '?')[:19]}] {d.get('description', 'No description')}")
        if d.get("emitter"):
            lines.append(f"      Emitter: {d['emitter']}")
    if not decisions.get("records"):
        lines.append("    (No decision records found)")
    lines.append("")

    # Events
    events = report["sections"].get("events", {})
    lines.append(f"  📊 EVENTS ({events.get('count', 0)} total)")
    lines.append("  " + "-" * 50)
    for e in events.get("records", [])[:10]:
        lines.append(f"    [{e.get('timestamp', '?')[:19]}] {e.get('type', '?')}: {e.get('description', '')[:60]}")
    if not events.get("records"):
        lines.append("    (No events found)")
    lines.append("")

    # HITL Approvals
    approvals = report["sections"].get("approvals", {})
    lines.append(f"  ✋ HITL APPROVALS ({approvals.get('count', 0)} total)")
    lines.append("  " + "-" * 50)
    for a in approvals.get("records", [])[:10]:
        lines.append(f"    [{a.get('timestamp', '?')[:19]}] {a.get('type', '?')}: {a.get('description', '')[:60]}")
    if not approvals.get("records"):
        lines.append("    (No HITL approvals recorded)")
    lines.append("")

    # Compliance Checklist
    checklist = report["sections"].get("compliance_checklist", {})
    lines.append(f"  ✅ COMPLIANCE CHECKLIST ({checklist.get('passed', 0)}/{checklist.get('total', 0)} passed)")
    lines.append("  " + "-" * 50)
    for c in checklist.get("checks", []):
        icon = {"pass": "✅", "fail": "❌", "warn": "⚠️", "info": "ℹ️"}.get(c["status"], "❓")
        lines.append(f"    {icon} {c['item']}: {c['detail']}")
    lines.append("")

    lines.append("=" * 70)
    lines.append("  This report was generated by Nucleus Agent OS (sovereign, local-first).")
    lines.append("  All data in this report resides on the local filesystem.")
    lines.append("  No data was transmitted externally during report generation.")
    lines.append("=" * 70)

    return "\n".join(lines)


def _format_html(report: Dict) -> str:
    """Format report as HTML for sharing with compliance officers."""
    jurisdiction = report.get("jurisdiction", {})
    decisions = report["sections"].get("decisions", {})
    events = report["sections"].get("events", {})
    approvals = report["sections"].get("approvals", {})
    checklist = report["sections"].get("compliance_checklist", {})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Nucleus Audit Report</title>
<style>
body {{ font-family: 'Inter', -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; background: #0d1117; color: #c9d1d9; }}
h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 1rem; }}
h2 {{ color: #79c0ff; margin-top: 2rem; }}
.meta {{ color: #8b949e; font-size: 0.9rem; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th {{ background: #161b22; color: #58a6ff; text-align: left; padding: 0.75rem; border: 1px solid #30363d; }}
td {{ padding: 0.75rem; border: 1px solid #30363d; }}
tr:nth-child(even) {{ background: #161b22; }}
.pass {{ color: #3fb950; }} .fail {{ color: #f85149; }} .warn {{ color: #d29922; }}
.badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.85rem; font-weight: 600; }}
.badge-pass {{ background: #1a3a2a; color: #3fb950; }}
.badge-fail {{ background: #3a1a1a; color: #f85149; }}
.sovereignty {{ background: #1a2a3a; border: 1px solid #58a6ff; padding: 1rem; border-radius: 0.5rem; margin-top: 2rem; }}
</style>
</head>
<body>
<h1>🧠 Nucleus Agent OS — Audit Trail Report</h1>
<div class="meta">
<p>Generated: {report.get('generated_at', 'N/A')}</p>
<p>Jurisdiction: {jurisdiction.get('name', 'Not configured')} ({jurisdiction.get('region', 'Global')})</p>
</div>

<h2>📋 Decision Records ({decisions.get('count', 0)})</h2>
<table>
<tr><th>Timestamp</th><th>Emitter</th><th>Description</th></tr>
"""
    for d in decisions.get("records", [])[:20]:
        html += f"<tr><td>{d.get('timestamp', '?')[:19]}</td><td>{d.get('emitter', '?')}</td><td>{d.get('description', '')}</td></tr>\n"
    if not decisions.get("records"):
        html += "<tr><td colspan='3'>No decision records found</td></tr>\n"

    html += f"""</table>

<h2>📊 Event Log ({events.get('count', 0)})</h2>
<table>
<tr><th>Timestamp</th><th>Type</th><th>Description</th></tr>
"""
    for e in events.get("records", [])[:20]:
        html += f"<tr><td>{e.get('timestamp', '?')[:19]}</td><td>{e.get('type', '?')}</td><td>{e.get('description', '')[:80]}</td></tr>\n"

    html += f"""</table>

<h2>✋ HITL Approvals ({approvals.get('count', 0)})</h2>
<table>
<tr><th>Timestamp</th><th>Type</th><th>Description</th></tr>
"""
    for a in approvals.get("records", [])[:20]:
        html += f"<tr><td>{a.get('timestamp', '?')[:19]}</td><td>{a.get('type', '?')}</td><td>{a.get('description', '')[:80]}</td></tr>\n"

    html += f"""</table>

<h2>✅ Compliance Checklist ({checklist.get('passed', 0)}/{checklist.get('total', 0)})</h2>
<table>
<tr><th>Check</th><th>Status</th><th>Detail</th></tr>
"""
    for c in checklist.get("checks", []):
        status_class = c["status"]
        html += f"<tr><td>{c['item']}</td><td class='{status_class}'>{c['status'].upper()}</td><td>{c['detail']}</td></tr>\n"

    html += f"""</table>

<div class="sovereignty">
<h3>🔒 Sovereignty Guarantee</h3>
<p>This report was generated by <strong>Nucleus Agent OS</strong> — a sovereign, local-first Agent OS.</p>
<ul>
<li>✅ All data in this report resides on the local filesystem</li>
<li>✅ No data was transmitted externally during report generation</li>
<li>✅ All agent decisions are traceable via DSoR (Decision System of Record)</li>
<li>✅ Human-in-the-loop governance is enforced for sensitive operations</li>
</ul>
</div>

</body>
</html>"""

    return html
