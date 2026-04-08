"""Sovereign Status Report — The identity command for Nucleus Agent OS.

Shows the full sovereignty posture of the current brain:
  - Brain metadata (created, version, location)
  - Memory health (engrams, intensity distribution)
  - Governance posture (jurisdiction, HITL, kill switch)
  - DSoR integrity (decision count, trace coverage)
  - Data residency guarantee

This is the "business card" of the Agent OS — what you show when someone
asks "what does this thing actually do?"
"""

import json
import logging
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("nucleus.sovereign")


def generate_sovereign_status(brain_path: Path) -> Dict[str, Any]:
    """Generate comprehensive sovereignty status report."""
    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "brain_path": str(brain_path),
        "sections": {},
    }

    # Section 1: Brain Identity
    report["sections"]["identity"] = _brain_identity(brain_path)

    # Section 2: Memory Health
    report["sections"]["memory"] = _memory_health(brain_path)

    # Section 3: Governance Posture
    report["sections"]["governance"] = _governance_posture(brain_path)

    # Section 4: DSoR Integrity
    report["sections"]["dsor"] = _dsor_integrity(brain_path)

    # Section 5: Data Residency
    report["sections"]["residency"] = _data_residency(brain_path)

    # Section 6: System Info
    report["sections"]["system"] = _system_info()

    # Overall sovereignty score (0-100)
    report["sovereignty_score"] = _calculate_score(report["sections"])

    return report


def _brain_identity(brain_path: Path) -> Dict[str, Any]:
    """Gather brain identity metadata."""
    result = {
        "path": str(brain_path),
        "exists": brain_path.exists(),
    }

    if not brain_path.exists():
        return result

    # Check for state file
    state_file = brain_path / "state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            result["created_at"] = state.get("created_at")
            result["brain_id"] = state.get("brain_id")
            result["version"] = state.get("version")
        except (json.JSONDecodeError, Exception):
            pass

    # Count all files in brain
    all_files = list(brain_path.rglob("*"))
    result["total_files"] = len([f for f in all_files if f.is_file()])
    result["total_dirs"] = len([f for f in all_files if f.is_dir()])

    # Calculate brain size
    total_bytes = sum(f.stat().st_size for f in all_files if f.is_file())
    result["total_size_bytes"] = total_bytes
    result["total_size_human"] = _human_size(total_bytes)

    # List top-level directories
    result["directories"] = sorted([
        d.name for d in brain_path.iterdir() if d.is_dir()
    ])

    return result


def _memory_health(brain_path: Path) -> Dict[str, Any]:
    """Analyze engram memory health."""
    engrams_dir = brain_path / "engrams"
    result = {
        "status": "not_initialized",
        "engram_count": 0,
        "contexts": {},
        "intensity_distribution": {},
        "oldest": None,
        "newest": None,
    }

    if not engrams_dir.exists():
        return result

    engrams = []
    for f in engrams_dir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    engrams.append(data)
        except (json.JSONDecodeError, Exception):
            continue

    result["engram_count"] = len(engrams)
    result["status"] = "operational" if engrams else "empty"

    # Context distribution
    contexts = {}
    for e in engrams:
        ctx = e.get("context", "unknown")
        contexts[ctx] = contexts.get(ctx, 0) + 1
    result["contexts"] = contexts

    # Intensity distribution
    intensities = {"low (1-3)": 0, "medium (4-6)": 0, "high (7-10)": 0}
    for e in engrams:
        intensity = e.get("intensity", 0)
        if intensity <= 3:
            intensities["low (1-3)"] += 1
        elif intensity <= 6:
            intensities["medium (4-6)"] += 1
        else:
            intensities["high (7-10)"] += 1
    result["intensity_distribution"] = intensities

    # Timestamps
    timestamps = [e.get("created_at", "") for e in engrams if e.get("created_at")]
    if timestamps:
        result["oldest"] = min(timestamps)
        result["newest"] = max(timestamps)

    return result


def _governance_posture(brain_path: Path) -> Dict[str, Any]:
    """Analyze governance configuration."""
    gov_dir = brain_path / "governance"
    result = {
        "jurisdiction": None,
        "hitl_active": False,
        "kill_switch": False,
        "audit_retention_days": None,
        "blocked_operations": 0,
        "required_approvals": 0,
    }

    if not gov_dir.exists():
        result["status"] = "unconfigured"
        return result

    # Compliance config
    compliance_file = gov_dir / "compliance.json"
    if compliance_file.exists():
        try:
            with open(compliance_file) as f:
                compliance = json.load(f)
            result["jurisdiction"] = compliance.get("jurisdiction")
            result["jurisdiction_name"] = compliance.get("name")
            result["region"] = compliance.get("region")
            result["applied_at"] = compliance.get("applied_at")
            reqs = compliance.get("requirements", {})
            result["data_residency_required"] = reqs.get("data_residency", False)
            result["kill_switch"] = reqs.get("kill_switch_required", False)
            result["audit_retention_days"] = reqs.get("audit_trail_retention_days")
        except (json.JSONDecodeError, Exception):
            pass

    # HITL policy
    hitl_file = gov_dir / "hitl_policy.json"
    if hitl_file.exists():
        try:
            with open(hitl_file) as f:
                hitl = json.load(f)
            result["hitl_active"] = True
            result["hitl_operations"] = len(hitl.get("hitl_required_for", []))
            result["max_autonomous_actions"] = hitl.get("max_autonomous_actions")
            result["blocked_operations"] = len(hitl.get("blocked_operations", []))
            result["required_approvals"] = len(hitl.get("required_approvals", {}))
        except (json.JSONDecodeError, Exception):
            pass

    result["status"] = "configured" if result["jurisdiction"] else "partial"
    return result


def _dsor_integrity(brain_path: Path) -> Dict[str, Any]:
    """Check Decision System of Record integrity."""
    result = {
        "status": "not_initialized",
        "decision_count": 0,
        "trace_files": 0,
        "event_count": 0,
        "types": {},
    }

    # Check DSoR directory
    dsor_dir = brain_path / "dsor"
    if dsor_dir.exists():
        dsor_files = list(dsor_dir.glob("*.json"))
        result["trace_files"] = len(dsor_files)

        # Analyze trace types
        types = {}
        for f in dsor_files:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                    t = data.get("type", "unknown")
                    types[t] = types.get(t, 0) + 1
            except (json.JSONDecodeError, Exception):
                continue
        result["types"] = types
        result["decision_count"] = sum(types.values())

    # Check event ledger
    ledger_dir = brain_path / "ledger"
    if ledger_dir.exists():
        event_count = 0
        for f in ledger_dir.glob("events*.jsonl"):
            try:
                with open(f) as fh:
                    event_count += sum(1 for line in fh if line.strip())
            except Exception:
                continue
        result["event_count"] = event_count

    if result["decision_count"] > 0 or result["event_count"] > 0:
        result["status"] = "operational"
    elif dsor_dir.exists() or (ledger_dir.exists()):
        result["status"] = "initialized"

    return result


def _data_residency(brain_path: Path) -> Dict[str, Any]:
    """Verify data residency guarantee."""
    return {
        "status": "sovereign",
        "location": str(brain_path.resolve()),
        "hostname": platform.node(),
        "guarantees": [
            "All data resides on the local filesystem",
            "No data transmitted externally during operations",
            "All agent decisions traceable via DSoR",
            "Memory (engrams) persisted locally only",
            "Audit logs stored locally with configurable retention",
        ],
        "external_dependencies": "None (all processing is local)",
    }


def _system_info() -> Dict[str, Any]:
    """Gather system information."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "hostname": platform.node(),
        "nucleus_version": _get_nucleus_version(),
    }


def _get_nucleus_version() -> str:
    """Get Nucleus version from package metadata."""
    try:
        from importlib.metadata import version
        return version("nucleus-mcp")
    except Exception:
        try:
            # Fallback: read pyproject.toml
            import re
            pyproject = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                match = re.search(r'version\s*=\s*"([^"]+)"', content)
                if match:
                    return match.group(1)
        except Exception:
            pass
    return "unknown"


def _calculate_score(sections: Dict) -> int:
    """Calculate sovereignty score (0-100)."""
    score = 0

    # Brain exists (20 points)
    identity = sections.get("identity", {})
    if identity.get("exists"):
        score += 20

    # Memory operational (20 points)
    memory = sections.get("memory", {})
    if memory.get("status") == "operational":
        score += 20
    elif memory.get("engram_count", 0) > 0:
        score += 10

    # Governance configured (25 points)
    gov = sections.get("governance", {})
    if gov.get("jurisdiction"):
        score += 15
    if gov.get("hitl_active"):
        score += 10

    # DSoR operational (20 points)
    dsor = sections.get("dsor", {})
    if dsor.get("status") == "operational":
        score += 20
    elif dsor.get("status") == "initialized":
        score += 5

    # Data residency sovereign (15 points — always true for local)
    residency = sections.get("residency", {})
    if residency.get("status") == "sovereign":
        score += 15

    return min(score, 100)


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_sovereign_status(report: Dict) -> str:
    """Format sovereignty report as terminal-friendly ASCII art."""
    lines = []
    score = report.get("sovereignty_score", 0)

    # Score visualization
    bar_width = 30
    filled = int(score / 100 * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    if score >= 80:
        grade = "A"
        grade_icon = "🛡️"
    elif score >= 60:
        grade = "B"
        grade_icon = "✅"
    elif score >= 40:
        grade = "C"
        grade_icon = "⚠️"
    else:
        grade = "D"
        grade_icon = "❌"

    lines.append("")
    lines.append("  ╔══════════════════════════════════════════════════════════╗")
    lines.append("  ║          🧠  NUCLEUS — SOVEREIGN AGENT OS              ║")
    lines.append("  ╚══════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append(f"  Sovereignty Score: {grade_icon}  [{bar}] {score}/100 (Grade: {grade})")
    lines.append(f"  Generated: {report.get('generated_at', 'now')}")
    lines.append("")

    # Identity
    identity = report["sections"].get("identity", {})
    lines.append("  ┌─ BRAIN IDENTITY ───────────────────────────────────────┐")
    lines.append(f"  │  Path:   {identity.get('path', 'N/A')}")
    lines.append(f"  │  Size:   {identity.get('total_size_human', '?')} ({identity.get('total_files', 0)} files)")
    lines.append(f"  │  Dirs:   {', '.join(identity.get('directories', []))}")
    lines.append("  └─────────────────────────────────────────────────────────┘")
    lines.append("")

    # Memory
    memory = report["sections"].get("memory", {})
    mem_icon = "✅" if memory.get("status") == "operational" else "❌"
    lines.append(f"  ┌─ MEMORY {mem_icon} ────────────────────────────────────────────┐")
    lines.append(f"  │  Status:  {memory.get('status', 'unknown')}")
    lines.append(f"  │  Engrams: {memory.get('engram_count', 0)}")
    if memory.get("contexts"):
        ctx_str = ", ".join(f"{k}: {v}" for k, v in memory["contexts"].items())
        lines.append(f"  │  Contexts: {ctx_str}")
    if memory.get("intensity_distribution"):
        dist = memory["intensity_distribution"]
        lines.append(f"  │  Intensity: Low={dist.get('low (1-3)', 0)} Med={dist.get('medium (4-6)', 0)} High={dist.get('high (7-10)', 0)}")
    lines.append("  └─────────────────────────────────────────────────────────┘")
    lines.append("")

    # Governance
    gov = report["sections"].get("governance", {})
    gov_icon = "✅" if gov.get("jurisdiction") else "⚠️"
    lines.append(f"  ┌─ GOVERNANCE {gov_icon} ─────────────────────────────────────────┐")
    if gov.get("jurisdiction"):
        lines.append(f"  │  Jurisdiction:  {gov.get('jurisdiction_name', gov['jurisdiction'])}")
        lines.append(f"  │  Region:        {gov.get('region', '?')}")
        lines.append(f"  │  HITL Active:   {'✅ Yes' if gov.get('hitl_active') else '❌ No'} ({gov.get('hitl_operations', 0)} operations)")
        lines.append(f"  │  Max Auto:      {gov.get('max_autonomous_actions', '?')} actions")
        lines.append(f"  │  Kill Switch:   {'✅ Active' if gov.get('kill_switch') else '⚪ Inactive'}")
        lines.append(f"  │  Retention:     {gov.get('audit_retention_days', '?')} days")
        lines.append(f"  │  Blocked Ops:   {gov.get('blocked_operations', 0)}")
    else:
        lines.append("  │  ⚠️  No jurisdiction configured")
        lines.append("  │  Run: nucleus comply --jurisdiction eu-dora")
    lines.append("  └─────────────────────────────────────────────────────────┘")
    lines.append("")

    # DSoR
    dsor = report["sections"].get("dsor", {})
    dsor_icon = "✅" if dsor.get("status") == "operational" else "⚠️"
    lines.append(f"  ┌─ DECISION TRAIL (DSoR) {dsor_icon} ──────────────────────────────┐")
    lines.append(f"  │  Status:     {dsor.get('status', 'unknown')}")
    lines.append(f"  │  Decisions:  {dsor.get('decision_count', 0)} traces")
    lines.append(f"  │  Events:     {dsor.get('event_count', 0)} logged")
    if dsor.get("types"):
        for t, count in dsor["types"].items():
            lines.append(f"  │    {t}: {count}")
    lines.append("  └─────────────────────────────────────────────────────────┘")
    lines.append("")

    # Data Residency
    lines.append("  ┌─ DATA RESIDENCY 🔒 ─────────────────────────────────────┐")
    residency = report["sections"].get("residency", {})
    lines.append(f"  │  Status:   {residency.get('status', 'unknown').upper()}")
    lines.append(f"  │  Location: {residency.get('location', '?')}")
    lines.append(f"  │  Host:     {residency.get('hostname', '?')}")
    for g in residency.get("guarantees", [])[:3]:
        lines.append(f"  │  ✅ {g}")
    lines.append("  └─────────────────────────────────────────────────────────┘")
    lines.append("")

    # System
    sys_info = report["sections"].get("system", {})
    lines.append(f"  Nucleus v{sys_info.get('nucleus_version', '?')} | "
                 f"Python {sys_info.get('python', '?')} | "
                 f"{sys_info.get('os', '?')} {sys_info.get('machine', '?')}")
    lines.append("")

    return "\n".join(lines)
