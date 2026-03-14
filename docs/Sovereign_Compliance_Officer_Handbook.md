# Nucleus Sovereign Agent OS — Compliance Officer Handbook

## 1. Introduction: The Agent Governance Crisis
AI agents possess autonomy; they act sequentially, synthesize external inputs, and route data independently. This autonomy inherently clashes with financial, healthcare, and governmental compliance regimes (DORA, MAS TRM, SOC2, HIPAA), which require explicit, immutable reasoning chains to prove non-discriminatory, data-resident logic.

**The Nucleus Promise:** Nucleus provides a "Sovereign Agent OS" layer underneath any Language Model or Agent Swarm. It intercepts tasks and guarantees 100% data residency, immutable tracing, and programmable Human-In-The-Loop (HITL) kill switches.

## 2. The Decision System of Record (DSoR)
Every action an agent takes on Nucleus is intercepted and written to the Decision System of Record (DSoR). 

### 2.1 Technical Architecture
- **Storage:** Appendix-only local JSON ledger.
- **Data Escrow:** Zero transmission to external servers. No cloud databases are required for audit reporting.
- **Trace Lifespan:** DSoR traces outlive the ephemeral conversational memory of the LLM. 
- **Retrieval:** Traces are retrievable via `nucleus trace view <ID>` or automatically aggregated via the visual Governance Dashboard.

### 2.2 Trace Contents
Each record contains:
1. **Timestamp (UTC/ISO8601)**
2. **Agent Identity/Role**
3. **Trigger Event**
4. **Context Window Parameters** (Hash of what the agent observed)
5. **Reasoning Trail** (Explicit justification for the action)
6. **Risk Calculation** (If compliance hooks are active)
7. **Execution Result**

## 3. Jurisdiction Configuration Engine
Nucleus natively understands global regulatory frameworks. A simple CLI command enforces rigid operating parameters.

### `eu-dora` (Digital Operational Resilience Act - EU)
- **Data Residency Check:** Validated at the filesystem level.
- **Incident Reporting Timeline:** DSoR traces locked and retained for 3 years to comply with post-incident analysis mandates.
- **Autonomous Constraints:** Agents cannot execute high-risk functions without cryptographically verifying the presence of local watchdog processes.

### `sg-mas-trm` (Monetary Authority of Singapore - TRM Guidelines)
- **HITL Thresholds:** Heavily constrained. Max 2 autonomous actions per critical operation cluster before a mandatory Human-In-The-Loop validation is injected into the event stream. 
- **Vendor Risk:** Nullified. Because Nucleus is run 100% locally on existing approved infrastructure, third-party vendor analysis is bypassed.

### `us-soc2` (SOC2 Type II - General Enterprise)
- **Audit Reports:** Automated generation of the `audit_report.html` file mapping to SOC2 Trust Services Criteria (Security, Availability, Processing Integrity).
- **Rate Limiting:** Loosened to 200 autonomous operations per minute, prioritizing speed while maintaining an immutable audit log.

## 4. Testing the Infrastructure
To prove these controls during an audit:

1. **Sovereignty Check:** Run `nucleus sovereign` to calculate the mathematical confidence of data isolation.
2. **Test Compliance Rules:** Attempt to trigger a restricted tool action without HITL approval under the MAS TRM jurisdiction. Observe the failure state written to the immutable log.
3. **Export the Run-book:** Run `nucleus audit-report --format html -o /shared/compliance/audit_2026_q1.html` and attach it to your regulatory filing.

## 5. Deployment Security
For air-gapped or maximum-security deployments, operations teams should utilize the provided `Dockerfile` applying read-only attributes, restricting capability drops, and ensuring the `USER appuser` non-root execution path is strictly utilized.
