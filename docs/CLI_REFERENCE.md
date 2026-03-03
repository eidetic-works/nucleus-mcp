# Nucleus v1.3.0 — CLI Quick Reference Card

## 🏛️ Compliance Governance

```bash
# List available regulatory jurisdictions
nucleus comply --list

# Apply a jurisdiction (one command)
nucleus comply --jurisdiction eu-dora
nucleus comply --jurisdiction sg-mas-trm
nucleus comply --jurisdiction us-soc2

# Check compliance status
nucleus comply --report
```

## 📝 KYC Demo Workflow

```bash
# List demo applications
nucleus kyc list

# Review a single application
nucleus kyc review APP-001     # Low risk → APPROVE
nucleus kyc review APP-002     # Medium risk → ESCALATE 
nucleus kyc review APP-003     # High risk → REJECT

# Run full demo (all 3 applications)
nucleus kyc demo

# Output as JSON
nucleus kyc review APP-001 --json
```

## 📊 Audit Reports

```bash
# Generate text report (stdout)
nucleus audit-report

# Generate JSON report
nucleus audit-report --format json

# Generate HTML report and save to file
nucleus audit-report --format html -o report.html

# Filter by time window
nucleus audit-report --hours 24
```

## 📜 DSoR Trace Viewer

```bash
# List all decision traces
nucleus trace list

# Filter by type
nucleus trace list --type KYC_REVIEW

# View detailed trace
nucleus trace view KYC-ABCD1234

# Output as JSON
nucleus trace view KYC-ABCD1234 --json
```

## 🛡️ Sovereignty Status

```bash
# Show sovereignty posture report
nucleus sovereign

# Output as JSON
nucleus sovereign --json

# Specify brain directory
nucleus sovereign --brain /path/to/.brain
```

## 🧠 Daily Operations

```bash
# Morning brief (compounding intelligence)
nucleus morning-brief

# End of day (capture learnings)
nucleus end-of-day

# God Combos
nucleus combo pulse-and-polish
nucleus combo self-healing-sre --symptom "high latency"
nucleus combo fusion-reactor --observation "new pattern"
```

## 🐳 Deployment

```bash
# One-command deployment
./deploy/deploy.sh eu-dora

# Docker build with jurisdiction
docker build --build-arg JURISDICTION=eu-dora -t nucleus:eu-dora .

# Docker Compose per jurisdiction
docker compose -f deploy/docker-compose.eu-dora.yml up -d
docker compose -f deploy/docker-compose.sg-mas-trm.yml up -d
```
