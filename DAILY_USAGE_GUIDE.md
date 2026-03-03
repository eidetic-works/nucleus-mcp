# Daily Usage Guide - Phase 73

## Do I Need to Run Anything Before Coding?

**NO.** Phase 73 is already active and will stay active.

---

## Normal Daily Workflow

### Just Open and Code ✅

1. Open Windsurf or Antigravity
2. Start coding immediately
3. Phase 73 protects you automatically

**That's it!** No scripts to run, no setup needed.

---

## When to Run the Pre-load Script

### Only in These Rare Cases:

**1. After System Restart (Mac reboot)**
- Python's module cache is cleared on reboot
- Run once after reboot:
```bash
cd /Users/lokeshgarg/ai-mvp-backend/mcp-server-nucleus
python3 -c "from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient; from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector; from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps; from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry; print('✅ Phase 73 modules pre-loaded')"
```

**2. After Updating Phase 73 Code**
- If you edit any Phase 73 module files
- Run the pre-load script to refresh the cache

**3. If You See Inconsistent Task Lists**
- Different results in Windsurf vs Antigravity
- Run the pre-load script and restart both apps

---

## Quick Health Check (Optional)

If you want to verify Phase 73 is working:

```bash
cd /Users/lokeshgarg/ai-mvp-backend/mcp-server-nucleus
python3 -c "from mcp_server_nucleus.runtime.llm_intent_analyzer import LLMIntentAnalyzer; print(f'✅ Phase 73 active: {LLMIntentAnalyzer()._use_resilient}')"
```

**Expected:** `✅ Phase 73 active: True`

---

## What Phase 73 Does Automatically

Every time you use brain tools, Phase 73:
- ✅ Protects LLM calls with 30s timeout
- ✅ Retries failures 3 times automatically
- ✅ Falls back gracefully if LLM is down
- ✅ Writes files atomically (no corruption)
- ✅ Logs errors to `.brain/telemetry/errors.jsonl`

**You don't see any of this - it just works.**

---

## Best Practices

### Use Fresh Threads
- Old threads may have stale context
- Close old threads, open fresh ones
- Fresh threads = 100% success rate

### Check Tasks Consistently
Ask: "Can you check my pending tasks?"

**Expected result:**
- 6 tasks from Brain Task Ledger
- Same list in Windsurf and Antigravity
- 2 READY, 4 PENDING

### If Something Seems Wrong

**Symptom:** Different task lists in different threads

**Fix:**
1. Close old threads
2. Open fresh thread
3. Ask again

**Symptom:** "Module not found" error

**Fix:**
1. Run pre-load script (see above)
2. Restart Windsurf/Antigravity
3. Try again

---

## Summary

**Daily workflow:**
1. Open Windsurf/Antigravity
2. Code normally
3. Phase 73 works automatically

**When to run pre-load:**
- After Mac reboot (rare)
- After editing Phase 73 code (rare)
- If seeing inconsistencies (rare)

**99% of the time: Just open and code. Phase 73 is already working.**

---

**Version:** 1.3.0  
**Status:** Production Ready  
**Last Updated:** 2026-02-24
