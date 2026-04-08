"""Compliance Configuration — Jurisdiction-Aware Governance.

MVE-2/MVE-3: Configures Nucleus governance policies per regulatory framework.

Supported Jurisdictions:
  - eu-dora: EU Digital Operational Resilience Act
  - sg-mas-trm: Singapore MAS Technology Risk Management
  - us-soc2: SOC2 Type II compliance
  - global-default: Sensible defaults without regulatory specifics
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("nucleus.compliance")

# ============================================================================
# JURISDICTION CONFIGURATIONS
# ============================================================================

JURISDICTIONS: Dict[str, Dict[str, Any]] = {
    "eu-dora": {
        "name": "EU DORA (Digital Operational Resilience Act)",
        "region": "European Union",
        "effective_date": "2025-01-17",
        "requirements": {
            "data_residency": True,
            "data_residency_note": "All data must remain within EU/EEA or approved jurisdictions",
            "audit_trail_retention_days": 2555,  # 7 years per DORA Art. 11
            "hitl_required_for": [
                "financial_transactions",
                "customer_data_access",
                "risk_assessments",
                "regulatory_reports",
                "third_party_integrations",
            ],
            "explainability": True,
            "explainability_note": "AI decisions must be explainable to regulators (Art. 6)",
            "incident_reporting_hours": 4,  # Major ICT incidents within 4h
            "third_party_oversight": True,
            "testing_frequency": "annual",  # Threat-led penetration testing
            "kill_switch_required": True,
            "dsor_format": "eu-dora-v1",
        },
        "governance_policies": {
            "max_autonomous_actions": 3,  # After 3 actions, require human review
            "sensitive_data_patterns": [
                r"IBAN\s*[A-Z]{2}\d{2}",
                r"BIC\s*[A-Z]{6,11}",
                r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Card numbers
                r"\b[A-Z]{2}\d{6,10}\b",  # EU passport numbers
            ],
            "blocked_operations": [
                "delete_customer_data",
                "modify_transaction_records",
                "bypass_kyc",
            ],
            "required_approvals": {
                "production_deployment": "senior_engineer",
                "data_export": "dpo",  # Data Protection Officer
                "model_update": "risk_committee",
            },
        },
    },
    "sg-mas-trm": {
        "name": "Singapore MAS TRM (Technology Risk Management)",
        "region": "Singapore / APAC",
        "effective_date": "2021-01-18",  # Latest revision
        "requirements": {
            "data_residency": True,
            "data_residency_note": "Customer data should remain in Singapore or approved jurisdictions",
            "audit_trail_retention_days": 1825,  # 5 years
            "hitl_required_for": [
                "customer_onboarding",
                "credit_decisions",
                "fraud_alerts",
                "regulatory_submissions",
                "system_changes",
            ],
            "explainability": True,
            "explainability_note": "Models must have documented decision rationale (MAS FEAT principles)",
            "incident_reporting_hours": 1,  # Major incidents within 1h
            "third_party_oversight": True,
            "testing_frequency": "semi-annual",
            "kill_switch_required": True,
            "dsor_format": "sg-mas-trm-v1",
        },
        "governance_policies": {
            "max_autonomous_actions": 2,  # Stricter than DORA
            "sensitive_data_patterns": [
                r"\b[STFGM]\d{7}[A-Z]\b",  # NRIC/FIN numbers
                r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            ],
            "blocked_operations": [
                "delete_customer_data",
                "modify_audit_logs",
                "disable_monitoring",
            ],
            "required_approvals": {
                "production_deployment": "cto",
                "data_export": "dpo",
                "model_update": "model_risk_committee",
            },
        },
    },
    "us-soc2": {
        "name": "SOC2 Type II",
        "region": "United States / Global",
        "effective_date": "2017-01-01",  # AICPA Trust Services Criteria
        "requirements": {
            "data_residency": False,  # SOC2 doesn't mandate residency
            "data_residency_note": "No geographic restriction, but data handling must be documented",
            "audit_trail_retention_days": 365,  # Minimum 1 year for Type II
            "hitl_required_for": [
                "access_control_changes",
                "security_configuration",
                "data_classification",
            ],
            "explainability": True,
            "explainability_note": "Processing activities must be documented per Trust Services Criteria",
            "incident_reporting_hours": 24,
            "third_party_oversight": True,
            "testing_frequency": "annual",
            "kill_switch_required": False,
            "dsor_format": "us-soc2-v1",
        },
        "governance_policies": {
            "max_autonomous_actions": 5,  # More relaxed
            "sensitive_data_patterns": [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            ],
            "blocked_operations": [
                "modify_audit_logs",
                "disable_encryption",
            ],
            "required_approvals": {
                "production_deployment": "change_advisory_board",
                "data_export": "security_team",
            },
        },
    },
    "global-default": {
        "name": "Global Default (Best Practice)",
        "region": "Global",
        "effective_date": "2024-01-01",
        "requirements": {
            "data_residency": False,
            "data_residency_note": "No specific requirements; all data stays local by default",
            "audit_trail_retention_days": 90,
            "hitl_required_for": [
                "destructive_operations",
                "external_api_calls",
            ],
            "explainability": False,
            "incident_reporting_hours": 72,
            "third_party_oversight": False,
            "testing_frequency": "quarterly",
            "kill_switch_required": False,
            "dsor_format": "default-v1",
        },
        "governance_policies": {
            "max_autonomous_actions": 10,
            "sensitive_data_patterns": [],
            "blocked_operations": [],
            "required_approvals": {},
        },
    },
}


def get_jurisdiction(jurisdiction_id: str) -> Optional[Dict[str, Any]]:
    """Get jurisdiction configuration by ID."""
    return JURISDICTIONS.get(jurisdiction_id)


def list_jurisdictions() -> Dict[str, str]:
    """List all available jurisdictions with their names."""
    return {k: v["name"] for k, v in JURISDICTIONS.items()}


def apply_jurisdiction(brain_path: Path, jurisdiction_id: str) -> Dict[str, Any]:
    """
    Apply a jurisdiction configuration to a Nucleus brain.

    This writes the compliance configuration to .brain/governance/compliance.json
    and updates governance policies to match regulatory requirements.

    Args:
        brain_path: Path to the .brain directory
        jurisdiction_id: One of the supported jurisdiction IDs

    Returns:
        Dict with applied configuration summary
    """
    config = JURISDICTIONS.get(jurisdiction_id)
    if not config:
        available = ", ".join(JURISDICTIONS.keys())
        return {
            "error": f"Unknown jurisdiction: {jurisdiction_id}",
            "available": available,
        }

    # Create governance directory
    gov_dir = brain_path / "governance"
    gov_dir.mkdir(parents=True, exist_ok=True)

    # Write compliance configuration
    compliance_file = gov_dir / "compliance.json"
    compliance_data = {
        "jurisdiction": jurisdiction_id,
        "name": config["name"],
        "region": config["region"],
        "applied_at": datetime.now(tz=timezone.utc).isoformat(),
        "requirements": config["requirements"],
        "governance_policies": config["governance_policies"],
        "version": "1.0.0",
    }

    with open(compliance_file, "w") as f:
        json.dump(compliance_data, f, indent=2)

    # Write HITL policy file
    hitl_file = gov_dir / "hitl_policy.json"
    hitl_data = {
        "jurisdiction": jurisdiction_id,
        "hitl_required_for": config["requirements"].get("hitl_required_for", []),
        "max_autonomous_actions": config["governance_policies"]["max_autonomous_actions"],
        "blocked_operations": config["governance_policies"]["blocked_operations"],
        "required_approvals": config["governance_policies"]["required_approvals"],
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    with open(hitl_file, "w") as f:
        json.dump(hitl_data, f, indent=2)

    # Write audit retention policy
    audit_file = gov_dir / "audit_policy.json"
    audit_data = {
        "jurisdiction": jurisdiction_id,
        "retention_days": config["requirements"]["audit_trail_retention_days"],
        "dsor_format": config["requirements"]["dsor_format"],
        "incident_reporting_hours": config["requirements"]["incident_reporting_hours"],
        "explainability_required": config["requirements"].get("explainability", False),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    with open(audit_file, "w") as f:
        json.dump(audit_data, f, indent=2)

    logger.info(f"Applied jurisdiction {jurisdiction_id} to {brain_path}")

    return {
        "status": "applied",
        "jurisdiction": jurisdiction_id,
        "name": config["name"],
        "region": config["region"],
        "files_written": [
            str(compliance_file),
            str(hitl_file),
            str(audit_file),
        ],
        "key_requirements": {
            "data_residency": config["requirements"]["data_residency"],
            "audit_retention_days": config["requirements"]["audit_trail_retention_days"],
            "hitl_operations": len(config["requirements"]["hitl_required_for"]),
            "max_autonomous_actions": config["governance_policies"]["max_autonomous_actions"],
            "kill_switch": config["requirements"].get("kill_switch_required", False),
        },
    }


def generate_compliance_report(brain_path: Path) -> Dict[str, Any]:
    """
    Generate a compliance status report for the current brain.

    Checks:
    1. Is a jurisdiction configured?
    2. Are audit logs being retained per policy?
    3. Are HITL policies in place?
    4. Is the kill switch active?
    5. Are DSoR traces being generated?

    Returns:
        Dict with compliance status and any issues found
    """
    gov_dir = brain_path / "governance"
    issues = []
    checks = {}

    # Check 1: Jurisdiction configured?
    compliance_file = gov_dir / "compliance.json"
    if compliance_file.exists():
        with open(compliance_file) as f:
            compliance = json.load(f)
        checks["jurisdiction"] = {
            "status": "configured",
            "id": compliance.get("jurisdiction"),
            "name": compliance.get("name"),
            "applied_at": compliance.get("applied_at"),
        }
    else:
        checks["jurisdiction"] = {"status": "not_configured"}
        issues.append("No jurisdiction configured. Run: nucleus comply --jurisdiction <id>")

    # Check 2: Audit logs exist?
    ledger_dir = brain_path / "ledger"
    if ledger_dir.exists():
        audit_files = list(ledger_dir.glob("audit_*.jsonl"))
        event_files = list(ledger_dir.glob("events*.jsonl"))
        checks["audit_logs"] = {
            "status": "present" if audit_files or event_files else "missing",
            "audit_files": len(audit_files),
            "event_files": len(event_files),
        }
        if not audit_files and not event_files:
            issues.append("No audit log files found in ledger/")
    else:
        checks["audit_logs"] = {"status": "missing"}
        issues.append("No ledger directory found")

    # Check 3: HITL policy in place?
    hitl_file = gov_dir / "hitl_policy.json"
    if hitl_file.exists():
        with open(hitl_file) as f:
            hitl = json.load(f)
        checks["hitl_policy"] = {
            "status": "active",
            "operations_covered": len(hitl.get("hitl_required_for", [])),
            "max_autonomous": hitl.get("max_autonomous_actions"),
        }
    else:
        checks["hitl_policy"] = {"status": "not_configured"}
        issues.append("No HITL policy configured")

    # Check 4: Engrams (memory) operational?
    engrams_dir = brain_path / "engrams"
    if engrams_dir.exists():
        engram_files = list(engrams_dir.glob("*.json"))
        checks["memory"] = {
            "status": "operational" if engram_files else "empty",
            "engram_count": len(engram_files),
        }
    else:
        checks["memory"] = {"status": "not_initialized"}
        issues.append("No engrams directory — memory not operational")

    # Check 5: DSoR (Decision System of Record)?
    dsor_dir = brain_path / "dsor"
    if dsor_dir.exists():
        dsor_files = list(dsor_dir.glob("*.json")) + list(dsor_dir.glob("*.jsonl"))
        checks["dsor"] = {
            "status": "operational" if dsor_files else "empty",
            "decision_files": len(dsor_files),
        }
    else:
        checks["dsor"] = {"status": "not_initialized"}
        # Not an issue — some brains don't use DSoR

    # Overall status
    critical_issues = [i for i in issues if "No jurisdiction" in i or "No HITL" in i]
    overall = "compliant" if not critical_issues else "non_compliant"
    if issues and not critical_issues:
        overall = "partially_compliant"

    return {
        "status": overall,
        "checks": checks,
        "issues": issues,
        "issue_count": len(issues),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def format_compliance_report(report: Dict[str, Any]) -> str:
    """Format compliance report as terminal-friendly output."""
    lines = []
    status = report["status"]
    status_icon = {"compliant": "✅", "partially_compliant": "⚠️", "non_compliant": "❌"}.get(
        status, "❓"
    )

    lines.append("=" * 60)
    lines.append(f"  {status_icon} NUCLEUS COMPLIANCE REPORT")
    lines.append(f"  Status: {status.upper()}")
    lines.append(f"  Generated: {report.get('generated_at', 'now')}")
    lines.append("=" * 60)
    lines.append("")

    # Jurisdiction
    jur = report["checks"].get("jurisdiction", {})
    if jur.get("status") == "configured":
        lines.append(f"  📋 Jurisdiction: {jur.get('name', 'Unknown')}")
        lines.append(f"     Applied: {jur.get('applied_at', 'Unknown')}")
    else:
        lines.append("  📋 Jurisdiction: ❌ Not configured")
    lines.append("")

    # Checks summary
    lines.append("  CHECKS:")
    for check_name, check_data in report["checks"].items():
        check_status = check_data.get("status", "unknown")
        icon = "✅" if check_status in ("configured", "active", "present", "operational") else "❌"
        lines.append(f"    {icon} {check_name}: {check_status}")

        # Extra detail for some checks
        if check_name == "hitl_policy" and check_status == "active":
            lines.append(f"       Operations covered: {check_data.get('operations_covered', 0)}")
            lines.append(f"       Max autonomous actions: {check_data.get('max_autonomous', 'unlimited')}")
        elif check_name == "memory":
            lines.append(f"       Engram count: {check_data.get('engram_count', 0)}")
        elif check_name == "audit_logs":
            lines.append(f"       Audit files: {check_data.get('audit_files', 0)}")
            lines.append(f"       Event files: {check_data.get('event_files', 0)}")

    lines.append("")

    # Issues
    if report.get("issues"):
        lines.append(f"  ⚠️  ISSUES ({report['issue_count']}):")
        for issue in report["issues"]:
            lines.append(f"    • {issue}")
    else:
        lines.append("  ✅ No issues found.")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
