"""Seed Real Engrams — Option 1 from the Design Thinking output.

Seeds the founder's real decisions, constraints, and learnings into the 
engram store so the Morning Brief has actual data to retrieve.

Run once: python3 scripts/seed_engrams.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline


# ── THE REAL ENGRAMS ──────────────────────────────────────────
# Extracted from: Founder Rant, DT-1 Deliverables, DT Output, 
# and actual architectural decisions made in the codebase.

SEED_ENGRAMS = [
    # ── ARCHITECTURE (intensity 8-10) ─────────────────────────
    {
        "key": "mcp_standard",
        "value": "Nucleus is built on MCP (Model Context Protocol) standard — this is the distribution rail. Everything is an MCP tool, resource, or prompt. Non-negotiable.",
        "context": "Architecture",
        "intensity": 10,
    },
    {
        "key": "monolith_decomposed",
        "value": "__init__.py decomposed from 8,689 to 5,300 LOC. 16 runtime modules extracted. Never re-monolith.",
        "context": "Architecture",
        "intensity": 8,
    },
    {
        "key": "adun_protocol",
        "value": "All engram writes go through ADUN pipeline (ADD/UPDATE/DELETE/NOOP). No raw appends. memory_pipeline.py is the gate. MDR_014.",
        "context": "Architecture",
        "intensity": 9,
    },
    {
        "key": "engram_jsonl_store",
        "value": "Engrams stored in engrams/ledger.jsonl (JSONL format). Versioned, soft-deletable, audited via history.jsonl. V0 uses keyword similarity, not embeddings.",
        "context": "Architecture",
        "intensity": 7,
    },
    {
        "key": "hypervisor_layers",
        "value": "Nucleus has 4 hypervisor layers: L1 Watchdog (file monitoring), L2 Injector (visual context), L3 God-Mode Lock (chflags uchg), L4 Governance (audit trail).",
        "context": "Architecture",
        "intensity": 7,
    },

    # ── DECISIONS (intensity 8-10) ────────────────────────────
    {
        "key": "no_openai",
        "value": "Budget constraint — Gemini only, no OpenAI. Flash plus disciplined prompting beats Opus for most tasks. Cost matters.",
        "context": "Decision",
        "intensity": 10,
    },
    {
        "key": "workflow_first",
        "value": "Nucleus was built tool-first (140+ tools). That's the root cause of zero adoption. Fix: workflow-first. Morning Brief is workflow #1.",
        "context": "Decision",
        "intensity": 10,
    },
    {
        "key": "morning_brief_is_alive",
        "value": "The Alive Moment = when Nucleus remembers yesterday's decision and applies it today without being told. brain_morning_brief is the proof. MDR_015.",
        "context": "Decision",
        "intensity": 9,
    },
    {
        "key": "dogfood_or_die",
        "value": "If the founder doesn't use Nucleus daily, it's dead. 7-day experiment: use brain_morning_brief every morning. Success = 50% output improvement.",
        "context": "Decision",
        "intensity": 9,
    },

    # ── STRATEGY (intensity 7-9) ──────────────────────────────
    {
        "key": "solo_founder_constraint",
        "value": "Solo founder, one-person team. No co-founder, no employees. AI agents must compensate. Discipline > team size.",
        "context": "Strategy",
        "intensity": 8,
    },
    {
        "key": "five_k_marketing",
        "value": "Marketing budget: $5,000 total. Must be surgical — Reddit r/ClaudeAI, Hacker News, Dev.to. No paid ads. Value-first content only.",
        "context": "Strategy",
        "intensity": 8,
    },
    {
        "key": "openclaw_competitor",
        "value": "OpenClaw had viral moment 1 month ago. Key lesson: they won on autonomous ACTION via familiar channels (WhatsApp/Telegram), not on memory. Differentiator: Nucleus = governed agents.",
        "context": "Strategy",
        "intensity": 8,
    },
    {
        "key": "compounding_flywheel",
        "value": "Core value prop: each day of Nucleus use makes the next day better. Engrams compound. This is what no competitor does. 7-day loop: Write → Recall → Apply → Measure.",
        "context": "Strategy",
        "intensity": 9,
    },

    # ── BRAND (intensity 6-8) ─────────────────────────────────
    {
        "key": "nucleus_positioning",
        "value": "Nucleus = The OS that makes your AI agents predictable, governed, and compounding. Not another agent framework — an operating system for agent governance.",
        "context": "Brand",
        "intensity": 8,
    },
    {
        "key": "sovereign_reddit",
        "value": "Reddit presence: u/SovereignStack persona. u/nucleusos was shadowbanned. New account needs 30-day warmup before Nucleus posts.",
        "context": "Brand",
        "intensity": 6,
    },

    # ── FEATURE (intensity 6-7) ───────────────────────────────
    {
        "key": "jit_consent",
        "value": "Agent respawn uses Just-In-Time Consent: agent reaches capacity → AWAITING_CONSENT state → user chooses warm (keep context) or cold (reset). MDR_013.",
        "context": "Feature",
        "intensity": 7,
    },
    {
        "key": "context_guardrail",
        "value": "Context Guardrail toggle in AgentPool controls whether agents retain context across respawns. Default: ON (security). JIT consent can override per-agent.",
        "context": "Feature",
        "intensity": 6,
    },
    {
        "key": "gentlequest_separate",
        "value": "GentleQuest (mental health app) is a separate product stream. Don't mix GentleQuest tasks with Nucleus tasks. Separate brain directories.",
        "context": "Feature",
        "intensity": 6,
    },
]


def seed_engrams():
    """Seed all engrams via the ADUN pipeline."""
    # Use the actual brain path
    brain = Path(__file__).parent.parent / "engrams"
    brain_root = brain.parent  # The root where engrams/ lives
    
    # The pipeline expects brain_path to be the root containing engrams/
    pipeline = MemoryPipeline(brain_root)
    
    print(f"=" * 60)
    print(f"🌱 SEEDING {len(SEED_ENGRAMS)} REAL ENGRAMS")
    print(f"   Target: {pipeline.ledger_path}")
    print(f"=" * 60)
    
    added = 0
    updated = 0
    skipped = 0
    
    for eng in SEED_ENGRAMS:
        result = pipeline.process(
            text=eng["value"],
            context=eng["context"],
            intensity=eng["intensity"],
            source_agent="seed_engrams_script",
            key=eng["key"],
        )
        
        op = result.get("mode", "?")
        a = result.get("added", 0)
        u = result.get("updated", 0)
        s = result.get("skipped", 0)
        added += a
        updated += u
        skipped += s
        
        status = "✅ ADD" if a else ("🔄 UPDATE" if u else "⏭️ SKIP")
        print(f"  {status} [{eng['context']:12}] {eng['key']}")
    
    print(f"\n{'=' * 60}")
    print(f"📊 RESULTS: {added} added, {updated} updated, {skipped} skipped")
    
    # Verify
    engrams = pipeline._load_active_engrams()
    print(f"📦 TOTAL ENGRAMS IN STORE: {len(engrams)}")
    print(f"{'=' * 60}")
    
    return added, updated, skipped


if __name__ == "__main__":
    seed_engrams()
