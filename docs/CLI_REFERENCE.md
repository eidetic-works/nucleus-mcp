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

## 🐕 Dog Food Experiment (30-Day Test)

```bash
# Log today's pain-if-broken score (1-10)
nucleus dogfood log 8

# Log with all fields
nucleus dogfood log 9 --pay --faster 3 --notes "Engrams saved 20min"

# Show experiment dashboard
nucleus dogfood status
```

## 🔨 build

```bash
# Run the build pipeline: plan → execute → verify → verdict
nucleus build "implement feature X in module Y"

# Build + merge: on a PASS verdict, commit → push → open PR → hand to merge gate
nucleus build "implement feature X in module Y" --merge

# Merge with explicit repo (default: eidetic-works/mcp-server-nucleus)
nucleus build "fix bug Z" --merge --repo eidetic-works/mcp-server-nucleus

# Merge with explicit review vendor (default: devin)
nucleus build "fix bug Z" --merge --review-vendor devin

# Dry-run the merge gate (no witness signing, no merge execution)
nucleus build "fix bug Z" --merge --dry-run
```

**Pipeline:** `plan` (dual-vendor adversarial plan review) → `execute`
(cross-vendor build dispatch) → `verify` (multi-tier check) → `verdict` card
+ exit code. Without `--merge`, the pipeline stops at the verdict.

**With `--merge`:** on a PASS verdict, the shim commits the changed files on a
fresh branch, pushes, opens a PR via `gh pr create`, and hands the PR number to
`merge_gate_authorize.py authorize`. On a non-PASS verdict, the shim refuses
before touching git/GitHub at all — no branch, no commit, no push, no PR.

Two steroid seams thread System A (build_runner) output into System B
(merge_gate): `NUCLEUS_BUILD_PLAN_CONTEXT` (plan text prepended to the gate's
diff-review prompt) and `NUCLEUS_BUILD_VERIFY_RECEIPT_PATH` (verify receipt
appended to the gate's audit metadata).

**Implementation:** `src/mcp_server_nucleus/runtime/build_and_merge.py`.
**Protocol:** `docs/protocols/sequence_not_merge.md` (ADR-0048).
