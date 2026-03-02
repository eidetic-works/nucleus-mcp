# 🔄 Force Phase 73 Reload - Complete Process

## The Issue
Phase 73 modules are installed but the MCP server is using cached/old code in memory. The integrations exist but aren't active.

## The Solution: Full Process Restart

### Option 1: Restart Windsurf Completely (Recommended)

1. **Quit Windsurf entirely** (Cmd+Q or Windsurf → Quit)
2. **Wait 5 seconds**
3. **Reopen Windsurf**
4. **Wait for MCP server to initialize** (check status bar)

This forces Python to reload all modules from disk, including Phase 73.

### Option 2: Kill MCP Server Process

```bash
# Find the MCP server process
ps aux | grep mcp-server-nucleus

# Kill it (replace PID with actual process ID)
kill -9 <PID>

# Then restart via Windsurf: Cmd+Shift+P → MCP: Restart Server
```

---

## ✅ Verification After Restart

Run this to confirm Phase 73 is active:

```bash
cd /path/to/your/project/mcp-server-nucleus

python3 -c "
from mcp_server_nucleus.runtime.llm_intent_analyzer import LLMIntentAnalyzer

# Check if resilient client is being used
analyzer = LLMIntentAnalyzer()
print(f'Using resilient client: {analyzer._use_resilient}')

# This should be True if Phase 73 is active
"
```

**Expected output:** `Using resilient client: True`

---

## 🧪 Test Phase 73 is Working

After restart, ask in Windsurf:
```
Can you check my pending tasks?
```

**What should happen (Phase 73 active):**
1. Intent analyzer uses ResilientLLMClient
2. Timeout protection active (30s)
3. Retry logic active (3 attempts)
4. Error telemetry logs any issues
5. Consistent results across environments

**What should NOT happen (Phase 73 not active):**
- Different task lists in Windsurf vs Antigravity
- No error logging
- No timeout protection
- Raw tool calls without resilience

---

## 📊 Check Error Telemetry

After using brain tools, check if errors are being logged:

```bash
python3 -c "
from mcp_server_nucleus.runtime.error_telemetry import get_error_telemetry

telemetry = get_error_telemetry()
stats = telemetry.get_stats()

print(f'Total errors: {stats[\"total_errors\"]}')
print(f'By domain: {stats[\"by_domain\"]}')

# Get recent errors
recent = telemetry.get_recent_errors(limit=5)
for err in recent:
    print(f'[{err[\"code\"]}] {err[\"category\"]}: {err[\"message\"][:60]}')
"
```

If Phase 73 is active, you should see error telemetry data (even if 0 errors).

---

## 🚨 If Still Not Working

### Check 1: Verify Integration Code

```bash
# Check if llm_intent_analyzer has Phase 73 integration
grep -n "resilient" /path/to/your/project/mcp-server-nucleus/src/mcp_server_nucleus/runtime/llm_intent_analyzer.py
```

**Expected:** Should show lines with `_use_resilient`, `_get_resilient_client()`, etc.

### Check 2: Verify Module Imports

```bash
python3 -c "
import sys
sys.path.insert(0, '/path/to/your/project/mcp-server-nucleus/src')

from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
from mcp_server_nucleus.runtime.llm_intent_analyzer import LLMIntentAnalyzer

print('✅ Both modules import successfully')
print(f'Analyzer has _use_resilient: {hasattr(LLMIntentAnalyzer, \"__init__\")}')
"
```

### Check 3: Check MCP Server Logs

Look for Phase 73 initialization messages in Windsurf's output panel:
- Open: View → Output
- Select: "MCP Server - nucleus" from dropdown
- Look for: Import errors, module loading messages

---

## 🎯 Expected Behavior After Fix

### Before Phase 73 (Current State)
- ❌ Different task lists in Windsurf vs Antigravity
- ❌ No timeout protection
- ❌ No retry logic
- ❌ No error telemetry
- ❌ Can hang on LLM timeouts

### After Phase 73 (Target State)
- ✅ Consistent task lists (same brain state)
- ✅ 30s timeout protection
- ✅ 3 automatic retries
- ✅ Circuit breaker (opens after 5 failures)
- ✅ Error telemetry logging
- ✅ Graceful fallback to keyword analysis

---

## 📝 Summary

**Problem:** MCP server has old code in memory  
**Solution:** Quit and reopen Windsurf (full process restart)  
**Verification:** Check `_use_resilient = True` in analyzer  
**Test:** Ask "Can you check my pending tasks?" - should get consistent results  

**Time:** 2 minutes  
**Risk:** None (just a restart)  
**Impact:** Phase 73 becomes fully active  

---

**Next:** After confirming Phase 73 works in Windsurf, repeat for Antigravity.
