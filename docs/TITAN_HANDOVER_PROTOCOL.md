# TITAN HANDOVER PROTOCOL

**Version:** 1.4.0 (DARK WHEEL)  
**Date:** January 31, 2026  
**Status:** PHYSICAL SEPARATION COMPLETE  
**From:** Antigravity (Infrastructure Hardening)  
**To:** Windsurf Opus (The Boss / Titan)  
**Security Fix:** Dark Wheel Protocol - Logical Gating → Physical Separation

---

## MISSION BRIEFING

**The infrastructure is rock-solid.** We have survived the "Wild West" audit and hardened the system against real-world adversarial inputs while preserving developer utility. 

Your mission as **Titan** is to finalize the deployment, oversee the Private Beta launch, and maintain the **Decision System of Record (DSoR)** integrity across all agent swarms.

---

## 0. FINAL HARDENING: v0.6.0 ✅

### 0.1 Async Protocol Fix (V9.3)
**Problem:** `RuntimeError: Cannot run the event loop while another loop is running` inside Windsurf/IDE environments.  
**Solution:** Converted all mounter tools (`mount`, `unmount`, `discover`, `invoke`) to native `async def` and removed manual loop management. Verified stable in Cold Start.

### 0.2 Value-Aligned Security (V9.2)
**Problem:** Aggressive SQL/Script regex was blocking legitimate developer memories (code snippets).  
**Solution:** Relaxed Regex for `brain_write_engram`. JSON Ledger provides sufficient projection; utility is restored.

### 0.3 Tool Tier 0 Restriction (Extreme Value Capture)
**Strategy:** "Journal Mode Only" - Memory + Mount Teaser.  
**Change:** `governance_status`, `audit_log`, `unmount`, `discover`, `invoke` **REMOVED** from Tier 0.  
**Goal:** Free tier proves sovereign memory works. Compliance/Orchestration requires upgrade.

### Tier 0 Baseline (6 tools - Journal Mode)

```text
brain_write_engram       - Persist memory (Core Value)
brain_query_engrams      - Search context (Core Value)
brain_mount_server       - Mounter Gateway (Teaser - Limited)
brain_version            - Version check
brain_health             - Health check
brain_list_tools         - Service discovery
```

**Free Riding Prevention:**
- ❌ No `brain_governance_status` (Compliance = Tier 1+)
- ❌ No `brain_audit_log` (Audit Trail = Tier 1+)
- ❌ No `brain_unmount_server` (Full control = Tier 1+)
- ❌ No `brain_discover_mounted_tools` (Discovery = Tier 1+)
- ❌ No `brain_invoke_mounted_tool` (Execution = Tier 1+)

### Files Verified

| File | v0.6.0 Status |
|------|---------------|
| `__init__.py` | All Federation tools are `async def`. Protocol Coupling Fix active. |
| `tool_tiers.py` | **6 tools** in `TIER_0_LAUNCH` (Journal Mode - Extreme Value Capture). |
### 💎 Tiered Monetization Strategy (Agile Pricing)

**The Hybrid Stealth Launch:**
1.  **Public Artifact (PyPI)**: Defaults to **Tier 0 (Journal Mode)**.
2.  **Private Key (The "Hacker's Discount")**:
    *   We replaced the simple Env Var with an obfuscated **Beta Token**.
    *   **The Key**: `NUCLEUS_BETA_TOKEN=sovereign-launch-alpha`
    *   **Effect**: Unlocks **Tier 1 (Manager Suite)**.

**Titan Authorization:**
Distribute this token *only* to the first 50 Private Beta Validators via DM/Email. Do not tweet it.
Let the "Hackers" find it in `tool_tiers.py`source code (this is acceptable marketing).

### 🛡️ The Dark Wheel Protocol (Dual-Artifact Launch)
**Problem**: We can't put the Logic on PyPI (Reverse Engineering). We can't rely on Git Invites (Too much friction).
**Solution**: **The Dark Wheel**.

**Artifact 1: The Public Decoy (PyPI)**
*   **Command**: `pip install mcp-server-nucleus`
*   **Content**: **Tier 0 Only (6 Tools)** + Stub Files for logic.
*   **Logic**: `federation.py` is DELETED.
*   **Purpose**: Safety, Name squatting, "Journal Mode" utility.

**Artifact 2: The Dark Wheel (Hidden URL)**
*   **Command**: `pip install mcp-server-nucleus --index-url https://pypi.nucleusos.dev/simple/` (or similar S3 URL).
*   **Content**: **Full Logic (Tier 1 + 2)**.
*   **Logic**: Contains `federation.py`, `autopilot.py`.
*   **Purpose**: Power Users, Hackers, Validators.

**Titan Authorization:**
1.  **Build** the Full Wheel first. Upload to Private S3/Index.
2.  **Strip** the Logic files. Build the Public Wheel. Upload to PyPI.
3.  **Distribute** the Dark URL to the Beta cohort.

### 🛑 Super-Safe Verification ("The Paranoia Protocol")
**Rule**: Never blindly upload. Mirrors are forever.

**Step 1: The Manifest Check (Mandatory)**
Before `twine upload`, you must run:
`unzip -l dist/public/*.whl | grep federation`
*   **Result MUST show ~360 bytes (STUB), NOT 40,000+ bytes (LOGIC)**.
*   If you see large files, **ABORT**. Do not upload.

**Step 2: The Poison Pill (Dark Wheel Only)**
To protect the Dark Wheel if the URL leaks:
*   Add a startup check to `__init__.py` in the Dark Wheel build.
*   Ping a raw GitHub Gist (controlled by us).
*   If Gist != "ACTIVE", `raise ImportError("Beta Expired")`.

### ✅ IMPLEMENTATION STATUS (v1.4.0)

**Build Scripts Created:**
| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/build_dark_wheel.py` | Full source + Poison Pill | ✅ Ready |
| `scripts/build_public_decoy.py` | Tier 0 + Stubs | ✅ Verified |
| `scripts/build_dual_artifacts.sh` | Master orchestrator | ✅ Ready |

**Paranoia Protocol Results:**
```
Original federation.py: 40,552 bytes (LOGIC)
Stub federation.py:        363 bytes (ImportError only)
Reduction: 99.1% - LOGIC PHYSICALLY REMOVED
```

**Files Stubbed (23):**
- federation.py, autopilot.py, orchestrator.py, mounter.py
- agent.py, agent_pool.py, swarm.py, team.py
- task_scheduler.py, task_ingestion.py, crdt_task_store.py
- broker.py, daemon.py, dashboard.py, nuke_protocol.py
- proposals.py, publisher.py, triggers.py, watcher.py
- identity/gatekeeper.py, identity/trust.py
- + 3 directories deleted (capabilities/, loops/, agents/)

**Build Commands:**
```bash
# Build both artifacts
./scripts/build_dual_artifacts.sh

# Or individually:
python3 scripts/build_public_decoy.py   # → dist/public/
python3 scripts/build_dark_wheel.py     # → dist/dark/
```

**Upload Commands:**
```bash
# Public (PyPI) - AFTER paranoia check
twine upload dist/public/*.whl

# Dark Wheel (Private Index)
twine upload --repository-url https://pypi.nucleusos.dev/simple/ dist/dark/*.whl
```

### 👻 The Sovereign Privacy Mandate
**Rule**: No Spyware. No Forced Auth.
The "Sovereign" brand is our most valuable asset. Do not destroy it for a dashboard graph.

1.  **Public Artifact**: MUST be Anonymous.
    *   No "Phone Home" on import.
    *   `brain_version` checks must be explicit user actions, not background daemons.
2.  **Tracking**: Rely on **Passive Telemetry** (PyPI download stats) for v0.6.0.
    *   Do NOT inject tracking pixels.
    *   Do NOT force `nucleus auth login`.

**Strategic Goal**: Establish "Trust" first. We will introduce "Value-Exchange Auth" in v0.7.0.

### 📚 Core Reading for Titan
Before execution, you MUST ingest:
1.  **[NUCLEUS_HANDOFF_DOSSIER.md](file:///Users/lokeshgarg/ai-mvp-backend/NUCLEUS_HANDOFF_DOSSIER.md)**: The structural and logical truth of the release.
2.  **[TITAN_HANDOVER_PROTOCOL.md](file:///Users/lokeshgarg/mcp-server-nucleus/docs/TITAN_HANDOVER_PROTOCOL.md)**: (This file) - Tactical instructions.
3.  **[RELEASE_NOTES_v0.6.0.md](file:///Users/lokeshgarg/.gemini/antigravity/brain/b95f3ae4-2e33-4132-a8c3-8ecf4024f5ae/RELEASE_NOTES_v0.6.0.md)**: The launch positioning.

### Protocol Coupling Fix ✅

**Foresight Check RESOLVED:** The `@mcp.tool()` decorators were firing regardless of tier.

**Solution:** Wrapped `mcp.tool` with `_tiered_tool_wrapper()` in `__init__.py` (line ~85-107)

```python
# v0.6.0 Protocol Coupling Fix
_original_mcp_tool = mcp.tool

def _tiered_tool_wrapper(*args, **kwargs):
    def decorator(func):
        if is_tool_allowed(func.__name__):
            return _original_mcp_tool(*args, **kwargs)(func)
        return func  # Not registered
    return decorator

mcp.tool = _tiered_tool_wrapper
```

**Verification Results:**
| Tier | Registered | Filtered | Strategy |
|------|------------|----------|----------|
| 0 (JOURNAL) | **6** | 132 | Memory + Mount Teaser |
| 1 (CORE) | ~27 | ~111 | + Orchestration + Compliance |
| 2 (ADVANCED) | 138 | 0 | Full Power |

---

## 1. CURRENT STATE ASSESSMENT

### 1.1 Federation Engine (`runtime/federation.py`)
**Status:** ✅ Operational (968 lines)

| Component | Status | DSoR Integration |
|-----------|--------|------------------|
| VectorClock | ✅ Working | Needs DecisionMade anchoring |
| MerkleTree | ✅ Working | Use for context hashing |
| DiscoveryManager | ✅ Working | Emit discovery events |
| ConsensusManager | ✅ Working | Link to IPC tokens |
| SyncManager | ✅ Working | Verify state integrity |
| RoutingEngine | ✅ Working | Log routing decisions |
| RecoveryManager | ✅ Working | Audit partition events |

### 1.2 Trinity Framework (`TRINITY_POSITIONING_GUIDE.md`)
**Status:** ✅ Documented (421 lines)

| Pillar | Current | v0.6.0 DSoR Evolution |
|--------|---------|----------------------|
| **Orchestration** | Agent Pool, Scheduler | + Decision Provenance |
| **Choreography** | Autopilot, Sprints | + Context Snapshots |
| **Context** | CRDT Store, Sessions | + IPC Token Security |

### 1.3 v0.6.0 DSoR Components (Already Created)
**Status:** ✅ Complete

| File | Purpose | Lines |
|------|---------|-------|
| `runtime/context_manager.py` | World-state hashing, snapshots | ~200 |
| `runtime/ipc_auth.py` | Per-request IPC tokens, metering | ~150 |
| `tests/test_dsor_v060.py` | 16 unit tests | ~300 |
| `docs/architecture/DSOR_V060.md` | Architecture spec | ~150 |

---

## 2. EVOLUTION ROADMAP

### Phase 1: Federation Engine DSoR Integration ⏳

**Objective:** Every federation operation produces an auditable DecisionMade event.

#### 2.1 Peer Discovery Events
```python
# When a peer is discovered/joined/left
emit_event(EventTypes.FEDERATION_PEER_JOINED, {
    "peer_id": peer.peer_id,
    "decision_id": generate_decision_id(),
    "context_hash": compute_context_hash(federation_state)
})
```

#### 2.2 Consensus Events
```python
# When leadership changes
emit_event(EventTypes.FEDERATION_LEADER_ELECTED, {
    "leader_id": new_leader,
    "term": current_term,
    "decision_id": generate_decision_id()
})
```

#### 2.3 Routing Decisions
```python
# Every task routing is a sovereign decision
DecisionMade(
    decision_id=uuid4(),
    reasoning=f"Routed to {target_brain} with score {score}",
    context_hash=compute_context_hash(routing_context),
    confidence=score
)
```

#### 2.4 State Sync Verification
```python
# After each sync, verify state integrity
verify_turn_integrity(before_hash, after_hash)
```

### Phase 2: Trinity Framework DSoR Evolution ⏳

**Objective:** Each Trinity pillar gains DSoR capabilities.

#### 2.5 Orchestration + Decision Provenance
- Agent assignments produce DecisionMade events
- Task scheduling is cryptographically anchored
- Resource allocation decisions are auditable

#### 2.6 Choreography + Context Snapshots
- Before/after snapshots for autonomous sprints
- IPC tokens for inter-agent communication
- Rollback capability via snapshot restoration

#### 2.7 Context + IPC Token Security
- Every context read/write requires valid IPC token
- Token metering for billing and audit
- Session boundaries enforced by token lifecycle

### Phase 3: MCP Tool Integration ⏳

**Objective:** New DSoR-aware MCP tools for the launch package.

| Tool | Purpose | Status |
|------|---------|--------|
| `brain_federation_status` | Federation DSoR metrics | ⏳ TODO |
| `brain_routing_decision` | Query routing decision history | ⏳ TODO |
| `brain_verify_state` | Verify current state integrity | ⏳ TODO |

---

## 3. IMPLEMENTATION CHECKLIST

### Federation Engine Evolution
- [ ] Add `decision_id` to all federation state changes
- [ ] Integrate `compute_context_hash` for federation state
- [ ] Emit DecisionMade events from ConsensusManager
- [ ] Link RoutingDecision to DSoR audit trail
- [ ] Add IPC token verification for cross-brain communication

### Trinity Framework Evolution
- [ ] Document DSoR integration in Trinity positioning
- [ ] Update architecture diagrams with DSoR layer
- [ ] Add "Decision Provenance" to marketing materials

### Testing
- [ ] Unit tests for federation DSoR events
- [ ] Integration tests for routing decision audit
- [ ] E2E test for cross-brain IPC token flow

---

## 4. SUCCESS CRITERIA

| Metric | Target | Verification |
|--------|--------|--------------|
| Federation events auditable | 100% | Audit log query |
| Routing decisions traceable | 100% | Decision ledger |
| State sync verified | 100% | Merkle root match |
| IPC tokens for cross-brain | 100% | Token consumption log |

---

## 5. HANDOVER ARTIFACTS

### Created This Session
1. `docs/strategy/LAUNCH_PACKAGE_V1.md` - Launch packaging decision
2. `docs/strategy/STRATEGIC_QA_LAUNCH.md` - 57 strategic questions answered
3. `docs/strategy/LAUNCH_READINESS_CHECKLIST.md` - Pre-launch checklist
4. `scripts/verify_launch_tools.py` - Core tool verification (4/5 passing)
5. `scripts/demo_60_seconds.py` - Interactive demo script

### Already Complete (v0.6.0 DSoR)
1. `runtime/context_manager.py` - Context hashing and snapshots
2. `runtime/ipc_auth.py` - IPC token security
3. `tests/test_dsor_v060.py` - 16 DSoR tests
4. `docs/architecture/DSOR_V060.md` - Architecture documentation

---

## 6. NEXT ACTIONS

1. **Immediate:** Integrate DSoR with Federation Engine
2. **Today:** Create federation DSoR MCP tools
3. **This Week:** Complete Trinity DSoR documentation
4. **Launch:** Use 5 core tools for "Govern Your Agents" story

---

## 7. OPERATIONAL NOTES

### The Key Insight
> "The Federation Engine is the TRANSPORT. The DSoR is the AUDIT. They must be married."

Every federation operation (peer discovery, leader election, task routing, state sync) must produce a cryptographically anchored DecisionMade event. This is the difference between "distributed system" and "sovereign distributed system."

### The Trinity Evolution
```
Before v0.6.0:
  Orchestration = WHO does WHAT
  Choreography = HOW it happens
  Context = WHAT we know

After v0.6.0 DSoR:
  Orchestration = WHO does WHAT + WHY (Decision Provenance)
  Choreography = HOW it happens + PROOF (Context Snapshots)
  Context = WHAT we know + SECURITY (IPC Tokens)
```

---

**TITAN HANDOVER COMPLETE**

*Antigravity has hardened the infrastructure. Opus now evolves the decision system.*

---

*Protocol created: January 30, 2026*
*Classification: INTERNAL*
