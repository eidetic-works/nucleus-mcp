# Fix Perplexity Configuration

## Issue
Perplexity returns empty task list despite having 25 tools loaded.

## Root Cause
Wrong brain path in Perplexity MCP config:
- **Current:** `/path/to/your/project/mcp-server-nucleus`
- **Should be:** `/path/to/your/project/.brain`

## Fix

### Step 1: Open Perplexity MCP Settings
1. Open Perplexity
2. Go to Settings → MCP Servers
3. Find "nucleus" server configuration

### Step 2: Update NUCLEUS_BRAIN_PATH

**Change from:**
```json
{
  "env": {
    "NUCLEUS_BRAIN_PATH": "/path/to/your/project/mcp-server-nucleus"
  }
}
```

**Change to:**
```json
{
  "env": {
    "NUCLEUS_BRAIN_PATH": "/path/to/your/project/.brain"
  }
}
```

### Step 3: Restart Perplexity
1. Quit Perplexity completely
2. Reopen Perplexity
3. Wait for MCP server initialization

### Step 4: Test
Ask in Perplexity: "Can you check my pending tasks?"

**Expected:** Should return 6 tasks from Brain Task Ledger (same as Windsurf/Antigravity)

---

## Current Perplexity Config (for reference)

```json
{
  "args": ["-m", "mcp_server_nucleus"],
  "command": "/path/to/your/project/mcp-server-nucleus/.venv/bin/python3",
  "env": {
    "FASTMCP_LOG_LEVEL": "WARNING",
    "FASTMCP_SHOW_CLI_BANNER": "False",
    "NUCLEAR_BRAIN_PATH": "/path/to/your/project/mcp-server-nucleus",
    "NUCLEUS_BETA_TOKEN": "titan-sovereign-godmode",
    "NUCLEUS_BRAIN_PATH": "/path/to/your/project/mcp-server-nucleus",  ← FIX THIS
    "NUCLEUS_TOOL_TIER": "2",
    "PYTHONPATH": "/path/to/your/project/mcp-server-nucleus/src"
  },
  "useBuiltInNode": true
}
```

**Note:** Also fix `NUCLEAR_BRAIN_PATH` (typo?) to use same path as `NUCLEUS_BRAIN_PATH`.

---

## After Fix

Perplexity should:
- ✅ Return same 6 tasks as Windsurf/Antigravity
- ✅ Use Brain Task Ledger correctly
- ✅ Show 25 tools loaded
- ✅ Phase 73 protection active
