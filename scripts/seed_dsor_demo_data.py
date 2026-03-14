#!/usr/bin/env python3
"""
Seed DSoR Demo Data
===================
Generates realistic but simulated DSoR trace data for the current brain to make 
the Sovereignty Dashboard heavily populated for external enterprise / BFSI demos.
"""
import os
import sys
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Need to know brain path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")

def generate_random_dsor_trace(base_date, i):
    """Generate a single realistic DSoR trace for a mock agent action."""
    # Add random deviation to the date
    trace_time = base_date + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
    
    trace_types = ["KYC_REVIEW", "DATA_SYNC", "DOCUMENT_PARSER", "RISK_CALCULATION", "CLIENT_ONBOARDING"]
    trace_type = random.choice(trace_types)
    prefix = trace_type.split("_")[0]
    
    trace_id = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
    
    # Simulate a recommendation
    recs = ["APPROVE", "APPROVE", "APPROVE", "ESCALATE", "REJECT"]
    recommendation = random.choice(recs)
    
    risk_score = random.randint(0, 30) if recommendation == "APPROVE" else random.randint(50, 95)
    
    passed_checks = 5
    checks = []
    
    # Mock checks
    for check_name in ["sanctions_screen", "pep_screen", "document_validity", "source_of_funds", "facial_matching"]:
        passed = True
        weight = random.randint(0, 10)
        
        if recommendation != "APPROVE" and random.random() > 0.5:
            passed = False
            passed_checks -= 1
            weight = random.randint(30, 80)
            
        checks.append({
            "check_name": check_name,
            "passed": passed,
            "risk_weight": weight
        })
        
    reasoning = f"""SOVEREIGN DECISION RATIONALE:
=============================
Agent Identity: Compliance-Risk-Agent
Process Type: {trace_type}
Entity Confidence: {random.randint(85, 99)}%

EVALUATION:
- Documents verified against primary issuance ledgers.
- Network scans triggered {5 - passed_checks} anomalies.
- Sentiment context matching returned null.

FINAL RULING:
Autonomous risk gating executed. Threshold matching result: {recommendation}
"""

    return {
        "trace_id": trace_id,
        "type": trace_type,
        "timestamp": trace_time.isoformat() + "Z",
        "jurisdiction_applied": "eu-dora",
        "recommendation": recommendation,
        "risk_score": risk_score,
        "passed_checks": passed_checks,
        "checks": checks,
        "reasoning": reasoning
    }


def seed_data(brain_path: Path, num_records: int = 50):
    dsor_dir = brain_path / "dsor"
    dsor_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🌱 Seeding {num_records} mock traces into {dsor_dir}...")
    
    # Spread records over the last 14 days
    now = datetime.utcnow()
    
    for i in range(num_records):
        days_ago = random.randint(0, 14)
        base_date = now - timedelta(days=days_ago)
        
        record = generate_random_dsor_trace(base_date, i)
        
        # Write to file
        trace_file = dsor_dir / f"trace_{record['timestamp'].replace(':','-')}_{record['trace_id']}.json"
        
        with open(trace_file, "w") as f:
            json.dump(record, f, indent=2)
            
    print(f"✅ Successfully seeded {num_records} records.")

if __name__ == "__main__":
    if "NUCLEAR_BRAIN_PATH" in os.environ:
        brain = Path(os.environ["NUCLEAR_BRAIN_PATH"])
    else:
        # Default fallback
        brain = Path.cwd() / ".brain"
        
    if not brain.exists():
        print(f"❌ Brain path {brain} does not exist. Initializing a mock brain for demo.")
        brain.mkdir(parents=True, exist_ok=True)
        
    seed_data(brain, 50)
