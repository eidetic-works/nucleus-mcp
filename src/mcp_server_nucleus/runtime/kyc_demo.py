"""KYC Review Workflow — Simulated Compliance Demo.

MVE-2: A pre-built workflow that demonstrates Nucleus governance capabilities
by simulating a KYC (Know Your Customer) document review with:
  1. Agent receives an application
  2. Runs automated checks (sanctions, PEP, document validity)
  3. Generates DSoR trace of every step
  4. Produces audit-ready report
  5. Surfaces HITL approval request for human sign-off

This is the 15-minute demo to show BFSI contacts.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nucleus.kyc_demo")


# ============================================================================
# SIMULATED KYC APPLICATION DATA
# ============================================================================

DEMO_APPLICATIONS = {
    "APP-001": {
        "applicant": "John Smith",
        "type": "Individual Account Opening",
        "nationality": "United Kingdom",
        "document_type": "Passport",
        "document_number": "GB**7654321",
        "date_of_birth": "1985-03-15",
        "occupation": "Software Engineer",
        "annual_income_usd": 95000,
        "source_of_funds": "Employment Income",
        "risk_factors": [],
        "expected_result": "approved",
    },
    "APP-002": {
        "applicant": "Maria Rodriguez",
        "type": "Business Account Opening",
        "nationality": "Spain",
        "document_type": "National ID",
        "document_number": "ES**1234567X",
        "date_of_birth": "1978-11-22",
        "occupation": "CEO, Rodriguez Holdings Ltd",
        "annual_income_usd": 500000,
        "source_of_funds": "Business Revenue",
        "risk_factors": ["high_value_account", "complex_ownership"],
        "expected_result": "escalate",
    },
    "APP-003": {
        "applicant": "Dmitri Volkov",
        "type": "Individual Account Opening",
        "nationality": "Russia",
        "document_type": "Passport",
        "document_number": "RU**9876543",
        "date_of_birth": "1990-07-08",
        "occupation": "Import/Export Trader",
        "annual_income_usd": 200000,
        "source_of_funds": "Business Revenue",
        "risk_factors": ["sanctions_jurisdiction", "high_risk_industry"],
        "expected_result": "reject",
    },
}

# Simulated external check results
SANCTIONS_LIST = {"Russia", "North Korea", "Iran", "Syria", "Cuba"}
PEP_DATABASE = {"Maria Rodriguez": {"level": "associate", "connection": "Former council member spouse"}}
HIGH_RISK_INDUSTRIES = {"Import/Export", "Cryptocurrency", "Gambling", "Arms"}


# ============================================================================
# KYC REVIEW ENGINE
# ============================================================================


def run_kyc_review(
    application_id: str = "APP-001",
    brain_path: Optional[Path] = None,
    write_dsor: bool = True,
) -> Dict[str, Any]:
    """
    Execute a simulated KYC review workflow.

    Steps:
    1. Load application data
    2. Run automated checks (sanctions, PEP, document validity, risk scoring)
    3. Generate decision with full reasoning trail
    4. Write DSoR trace to brain
    5. Return review result with HITL approval request if needed

    Args:
        application_id: ID of the demo application to review
        brain_path: Path to .brain directory for DSoR trace storage
        write_dsor: Whether to write the DSoR trace to disk

    Returns:
        Dict with review result, decision trail, and HITL request
    """
    review_id = f"KYC-{uuid.uuid4().hex[:8].upper()}"
    started_at = datetime.utcnow().isoformat() + "Z"

    # Step 1: Load application
    app = DEMO_APPLICATIONS.get(application_id)
    if not app:
        return {
            "error": f"Unknown application: {application_id}",
            "available": list(DEMO_APPLICATIONS.keys()),
        }

    decision_trail = []
    checks = []
    risk_score = 0

    # Step 2a: Sanctions Check
    sanctions_result = _check_sanctions(app)
    checks.append(sanctions_result)
    decision_trail.append({
        "step": 1,
        "action": "Sanctions List Check",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {"nationality": app["nationality"]},
        "result": sanctions_result["status"],
        "reasoning": sanctions_result["detail"],
        "risk_impact": sanctions_result["risk_points"],
    })
    risk_score += sanctions_result["risk_points"]

    # Step 2b: PEP Check
    pep_result = _check_pep(app)
    checks.append(pep_result)
    decision_trail.append({
        "step": 2,
        "action": "PEP (Politically Exposed Persons) Check",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {"applicant": app["applicant"]},
        "result": pep_result["status"],
        "reasoning": pep_result["detail"],
        "risk_impact": pep_result["risk_points"],
    })
    risk_score += pep_result["risk_points"]

    # Step 2c: Document Validity Check
    doc_result = _check_document(app)
    checks.append(doc_result)
    decision_trail.append({
        "step": 3,
        "action": "Document Validity Check",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {"document_type": app["document_type"], "document_number": app["document_number"]},
        "result": doc_result["status"],
        "reasoning": doc_result["detail"],
        "risk_impact": doc_result["risk_points"],
    })
    risk_score += doc_result["risk_points"]

    # Step 2d: Risk Factor Assessment
    risk_result = _assess_risk_factors(app)
    checks.append(risk_result)
    decision_trail.append({
        "step": 4,
        "action": "Risk Factor Assessment",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {"risk_factors": app["risk_factors"], "income": app["annual_income_usd"]},
        "result": risk_result["status"],
        "reasoning": risk_result["detail"],
        "risk_impact": risk_result["risk_points"],
    })
    risk_score += risk_result["risk_points"]

    # Step 2e: Source of Funds Check
    sof_result = _check_source_of_funds(app)
    checks.append(sof_result)
    decision_trail.append({
        "step": 5,
        "action": "Source of Funds Verification",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input": {"source": app["source_of_funds"], "income": app["annual_income_usd"]},
        "result": sof_result["status"],
        "reasoning": sof_result["detail"],
        "risk_impact": sof_result["risk_points"],
    })
    risk_score += sof_result["risk_points"]

    # Step 3: Generate Decision
    decision = _make_decision(risk_score, checks)
    completed_at = datetime.utcnow().isoformat() + "Z"

    decision_trail.append({
        "step": 6,
        "action": "Final Decision",
        "timestamp": completed_at,
        "input": {"total_risk_score": risk_score},
        "result": decision["recommendation"],
        "reasoning": decision["reasoning"],
        "risk_impact": 0,
    })

    # Build the full review result
    review = {
        "review_id": review_id,
        "application_id": application_id,
        "applicant": app["applicant"],
        "started_at": started_at,
        "completed_at": completed_at,
        "risk_score": risk_score,
        "risk_level": decision["risk_level"],
        "recommendation": decision["recommendation"],
        "reasoning": decision["reasoning"],
        "checks": checks,
        "decision_trail": decision_trail,
        "hitl_required": decision["recommendation"] != "APPROVE",
        "hitl_request": {
            "action": "approve_or_reject",
            "review_id": review_id,
            "applicant": app["applicant"],
            "recommendation": decision["recommendation"],
            "risk_score": risk_score,
            "summary": decision["reasoning"],
        } if decision["recommendation"] != "APPROVE" else None,
    }

    # Step 4: Write DSoR trace
    if write_dsor and brain_path:
        _write_dsor_trace(brain_path, review)

    return review


def _check_sanctions(app: Dict) -> Dict:
    """Check applicant nationality against sanctions lists."""
    nationality = app["nationality"]
    if nationality in SANCTIONS_LIST:
        return {
            "check": "sanctions",
            "status": "FAIL",
            "detail": f"Nationality '{nationality}' is on the sanctions list. Account opening blocked.",
            "risk_points": 100,
        }
    return {
        "check": "sanctions",
        "status": "PASS",
        "detail": f"Nationality '{nationality}' not found on any sanctions list.",
        "risk_points": 0,
    }


def _check_pep(app: Dict) -> Dict:
    """Check if applicant is a Politically Exposed Person."""
    name = app["applicant"]
    if name in PEP_DATABASE:
        pep_info = PEP_DATABASE[name]
        return {
            "check": "pep",
            "status": "FLAG",
            "detail": f"PEP match found: {pep_info['level']} ({pep_info['connection']}). Enhanced due diligence required.",
            "risk_points": 30,
        }
    return {
        "check": "pep",
        "status": "PASS",
        "detail": "No PEP matches found in database.",
        "risk_points": 0,
    }


def _check_document(app: Dict) -> Dict:
    """Verify document validity (simulated)."""
    doc_type = app["document_type"]
    doc_number = app["document_number"]
    # Simulate: all demo documents are valid
    return {
        "check": "document",
        "status": "PASS",
        "detail": f"{doc_type} ({doc_number}) verified as valid and not expired.",
        "risk_points": 0,
    }


def _assess_risk_factors(app: Dict) -> Dict:
    """Assess declared risk factors."""
    factors = app.get("risk_factors", [])
    points = 0
    details = []

    if "sanctions_jurisdiction" in factors:
        points += 50
        details.append("Applicant has ties to sanctioned jurisdiction (+50)")
    if "high_risk_industry" in factors:
        occupation = app.get("occupation", "")
        for industry in HIGH_RISK_INDUSTRIES:
            if industry.lower() in occupation.lower():
                points += 25
                details.append(f"High-risk industry: {industry} (+25)")
                break
    if "complex_ownership" in factors:
        points += 15
        details.append("Complex ownership structure (+15)")
    if "high_value_account" in factors:
        points += 10
        details.append("High-value account opening (+10)")

    if not details:
        details = ["No risk factors identified"]

    status = "PASS" if points == 0 else ("FLAG" if points < 50 else "FAIL")

    return {
        "check": "risk_factors",
        "status": status,
        "detail": "; ".join(details),
        "risk_points": points,
    }


def _check_source_of_funds(app: Dict) -> Dict:
    """Verify source of funds."""
    source = app["source_of_funds"]
    income = app["annual_income_usd"]

    if income > 250000 and source == "Business Revenue":
        return {
            "check": "source_of_funds",
            "status": "FLAG",
            "detail": f"High income (${income:,}) from business revenue. Additional verification recommended.",
            "risk_points": 10,
        }
    return {
        "check": "source_of_funds",
        "status": "PASS",
        "detail": f"Source of funds '{source}' consistent with declared income (${income:,}).",
        "risk_points": 0,
    }


def _make_decision(risk_score: int, checks: List[Dict]) -> Dict:
    """Make the final decision based on cumulative risk score."""
    failed_checks = [c for c in checks if c["status"] == "FAIL"]
    flagged_checks = [c for c in checks if c["status"] == "FLAG"]

    if risk_score >= 100 or failed_checks:
        return {
            "recommendation": "REJECT",
            "risk_level": "HIGH",
            "reasoning": (
                f"Application REJECTED. Risk score: {risk_score}/100. "
                f"{len(failed_checks)} critical check(s) failed. "
                f"Reason: {'; '.join(c['detail'] for c in failed_checks)}"
            ),
        }
    elif risk_score >= 25 or flagged_checks:
        return {
            "recommendation": "ESCALATE",
            "risk_level": "MEDIUM",
            "reasoning": (
                f"Application ESCALATED for manual review. Risk score: {risk_score}/100. "
                f"{len(flagged_checks)} check(s) flagged. "
                f"Enhanced due diligence required before approval."
            ),
        }
    else:
        return {
            "recommendation": "APPROVE",
            "risk_level": "LOW",
            "reasoning": (
                f"Application APPROVED. Risk score: {risk_score}/100. "
                f"All checks passed. Standard onboarding procedures apply."
            ),
        }


def _write_dsor_trace(brain_path: Path, review: Dict):
    """Write the KYC review as a DSoR (Decision System of Record) trace."""
    dsor_dir = brain_path / "dsor"
    dsor_dir.mkdir(parents=True, exist_ok=True)

    trace_file = dsor_dir / f"{review['review_id']}.json"
    dsor_trace = {
        "type": "KYC_REVIEW",
        "review_id": review["review_id"],
        "application_id": review["application_id"],
        "applicant": review["applicant"],
        "started_at": review["started_at"],
        "completed_at": review["completed_at"],
        "recommendation": review["recommendation"],
        "risk_score": review["risk_score"],
        "risk_level": review["risk_level"],
        "decision_trail": review["decision_trail"],
        "hitl_required": review["hitl_required"],
        "sovereign_guarantee": "All processing occurred locally. No data transmitted externally.",
    }

    with open(trace_file, "w") as f:
        json.dump(dsor_trace, f, indent=2)

    logger.info(f"DSoR trace written: {trace_file}")


# ============================================================================
# CLI-FRIENDLY OUTPUT FORMATTER
# ============================================================================


def format_kyc_review(review: Dict) -> str:
    """Format KYC review result as terminal-friendly output."""
    lines = []
    rec = review["recommendation"]
    icon = {"APPROVE": "✅", "ESCALATE": "⚠️", "REJECT": "❌"}.get(rec, "❓")

    lines.append("=" * 65)
    lines.append(f"  {icon} KYC REVIEW RESULT — {review['review_id']}")
    lines.append("=" * 65)
    lines.append("")
    lines.append(f"  Applicant:      {review['applicant']}")
    lines.append(f"  Application:    {review['application_id']}")
    lines.append(f"  Risk Score:     {review['risk_score']}/100")
    lines.append(f"  Risk Level:     {review['risk_level']}")
    lines.append(f"  Recommendation: {icon} {rec}")
    lines.append("")

    # Checks summary
    lines.append("  AUTOMATED CHECKS:")
    lines.append("  " + "-" * 55)
    for check in review.get("checks", []):
        status_icon = {"PASS": "✅", "FAIL": "❌", "FLAG": "⚠️"}.get(check["status"], "❓")
        lines.append(f"    {status_icon} {check['check'].upper():20s} {check['status']}")
        lines.append(f"       {check['detail'][:70]}")
    lines.append("")

    # Decision trail
    lines.append("  DECISION TRAIL (DSoR):")
    lines.append("  " + "-" * 55)
    for step in review.get("decision_trail", []):
        lines.append(f"    Step {step['step']}: {step['action']}")
        lines.append(f"      Result: {step['result']}")
        lines.append(f"      Reason: {step['reasoning'][:65]}")
        lines.append(f"      Time:   {step['timestamp']}")
        lines.append("")

    # HITL request
    if review.get("hitl_required"):
        lines.append("  ✋ HUMAN APPROVAL REQUIRED:")
        lines.append("  " + "-" * 55)
        hitl = review["hitl_request"]
        lines.append(f"    Review ID: {hitl['review_id']}")
        lines.append(f"    Applicant: {hitl['applicant']}")
        lines.append(f"    Agent Recommendation: {hitl['recommendation']}")
        lines.append(f"    Risk Score: {hitl['risk_score']}/100")
        lines.append(f"    Summary: {hitl['summary'][:70]}")
        lines.append("")
        lines.append("    → Run: nucleus kyc approve <review_id>")
        lines.append("    → Or:  nucleus kyc reject <review_id>")
    else:
        lines.append("  ✅ No human approval needed (low risk, all checks passed)")

    lines.append("")
    lines.append("  🔒 Sovereignty: All processing occurred locally.")
    lines.append("     No data was transmitted to any external service.")
    lines.append("=" * 65)

    return "\n".join(lines)
