# Agent Runtime V2 - Enhanced Agent Execution Engine

> **Version**: 0.6.1
> **Phase**: 68
> **Date**: 2026-02-24
> **Status**: ✅ Complete

## Overview

Agent Runtime V2 provides comprehensive agent execution management including:
- **Rate Limiting** for agent spawning (prevents runaway agent creation)
- **Cost Tracking** per agent execution (tokens, tool calls, USD estimates)
- **Dashboard Metrics** for monitoring and observability
- **Timeout/Cancellation** support for long-running agents

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AgentExecutionManager                       │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ AgentSpawnLimiter│  │ AgentCostTracker │                 │
│  │ (Token Bucket)   │  │ (Per-Agent)      │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              AgentExecution Registry                  │   │
│  │  - Pending/Running/Completed/Cancelled executions    │   │
│  │  - Cancellation events                                │   │
│  │  - Timeout tracking                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EphemeralAgent                            │
│  - Spawn → Rate limit check → Execution tracking            │
│  - LLM calls → Token recording                              │
│  - Tool calls → Tool call recording                         │
│  - Complete → Finalize cost record                          │
└─────────────────────────────────────────────────────────────┘
```

## Components

### AgentSpawnLimiter

Token bucket rate limiter for agent spawning.

```python
from mcp_server_nucleus.runtime import AgentSpawnLimiter

limiter = AgentSpawnLimiter(capacity=10, fill_rate=2)  # 10 burst, 2/sec refill

if limiter.can_spawn("devops"):
    # Spawn allowed
    pass
else:
    # Rate limited
    pass

# Or raise on limit exceeded
limiter.spawn_or_raise("researcher")  # Raises RateLimitError
```

### AgentCostTracker

Tracks costs per agent execution.

```python
from mcp_server_nucleus.runtime import AgentCostTracker

tracker = AgentCostTracker()

# Start tracking
record = tracker.start_tracking("agent-123", "researcher")

# Record usage
tracker.record_tokens("agent-123", input_tokens=500, output_tokens=200)
tracker.record_tool_call("agent-123")

# Finalize
cost = tracker.finalize("agent-123", "completed")
print(f"Cost: ${cost.estimated_cost_usd:.6f}")
```

### AgentExecutionManager

Orchestrates the full agent lifecycle.

```python
from mcp_server_nucleus.runtime import get_execution_manager

manager = get_execution_manager()

# Spawn (with rate limiting)
execution = manager.spawn_agent("devops", "deploy app", timeout_seconds=300)

# Track execution
manager.start_execution(execution.agent_id)
manager.record_tokens(execution.agent_id, 100, 50)
manager.record_tool_call(execution.agent_id)

# Complete
manager.complete_execution(execution.agent_id, "completed")

# Dashboard metrics
metrics = manager.get_dashboard_metrics()
```

### Timeout & Cancellation

```python
from mcp_server_nucleus.runtime import with_timeout, check_cancellation

@with_timeout(60)
async def my_agent_task(agent_id: str):
    while processing:
        check_cancellation(agent_id)  # Raises if cancelled
        # ... do work ...
```

## MCP Tools

7 new MCP tools for agent dashboard:

| Tool | Description |
|------|-------------|
| `brain_agent_dashboard` | Comprehensive metrics overview |
| `brain_agent_spawn_stats` | Spawn rate limiting stats |
| `brain_agent_costs` | Cost tracking summary by persona |
| `brain_agent_list_active` | List active executions |
| `brain_agent_cancel` | Cancel a running agent |
| `brain_agent_cleanup` | Clean up old executions |
| `brain_agent_get` | Get specific execution details |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NUCLEUS_AGENT_SPAWN_CAPACITY` | 10 | Max burst agent spawns |
| `NUCLEUS_AGENT_SPAWN_RATE` | 2 | Agent spawns per second |
| `NUCLEUS_AGENT_TIMEOUT` | 300 | Default timeout (seconds) |
| `NUCLEUS_COST_INPUT` | 0.000001 | Cost per input token (USD) |
| `NUCLEUS_COST_OUTPUT` | 0.000003 | Cost per output token (USD) |

## Integration with EphemeralAgent

Agent Runtime V2 is automatically integrated with `EphemeralAgent`:

1. **On spawn**: Rate limit check, execution record created
2. **During LLM calls**: Token usage recorded (estimated)
3. **During tool calls**: Tool call count incremented
4. **On completion**: Execution finalized, cost persisted

## Cost Persistence

Costs are persisted to:
```
.brain/metrics/agent_costs.jsonl
```

Each line is a JSON record:
```json
{
  "agent_id": "agent-abc123",
  "persona": "researcher",
  "input_tokens": 1500,
  "output_tokens": 500,
  "tool_calls": 3,
  "duration_ms": 45000,
  "estimated_cost_usd": 0.003,
  "status": "completed"
}
```

## Budget Monitoring

### BudgetMonitor

Monitors agent execution costs and triggers alerts when thresholds are exceeded.

```python
from mcp_server_nucleus.runtime import get_budget_monitor

monitor = get_budget_monitor()

# Check current status
status = monitor.get_status()
# {
#   "daily": {"budget_usd": 10.0, "spent_usd": 2.5, ...},
#   "hourly": {"budget_usd": 2.0, "spent_usd": 0.5, ...},
#   "per_agent_limit_usd": 0.5
# }

# Alerts are sent via Telegram when thresholds are exceeded
```

### Budget MCP Tools

| Tool | Description |
|------|-------------|
| `brain_budget_status` | Get current budget status |
| `brain_budget_set_daily` | Set daily budget threshold |
| `brain_budget_set_hourly` | Set hourly budget threshold |
| `brain_budget_set_per_agent` | Set per-agent limit |
| `brain_budget_reset_counters` | Reset spend counters |

### Budget Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NUCLEUS_BUDGET_DAILY_USD` | 10.0 | Daily budget threshold |
| `NUCLEUS_BUDGET_HOURLY_USD` | 2.0 | Hourly budget threshold |
| `NUCLEUS_BUDGET_PER_AGENT_USD` | 0.5 | Per-agent cost limit |

## Phase 71: Tool Calling Enforcement Layer

### The Problem
LLMs take the path of least resistance — they claim to perform actions without actually calling tools. Over 50% of the time, required tools aren't called.

### The Solution: LLM-Supervising-LLM
Use a fast/cheap LLM (Flash) to supervise the main agent's tool calling behavior.

### Architecture
```
User Request
    │
    ▼
[Pre-Flight] LLM analyzes intent → determines required tools
    │
    ▼
[Execution] Agent runs with enforcement prompt injected
    │
    ▼
[Post-Flight] LLM validates tool calls were made
    │
    ▼
[Retry] If validation fails → stronger enforcement → retry
    │
    ▼
[Learn] Record failures → analyze patterns → improve prompts
```

### Components

| Component | File | Purpose |
|-----------|------|--------|
| `LLMIntentAnalyzer` | `runtime/llm_intent_analyzer.py` | Pre-flight: detect required tools |
| `LLMToolValidator` | `runtime/llm_tool_validator.py` | Post-flight: validate tool calls |
| `LLMToolEnforcer` | `runtime/llm_tool_enforcer.py` | Orchestrate enforcement flow |
| `LLMPatternLearner` | `runtime/llm_pattern_learner.py` | Learn from failures |
| `EnforcementOps` | `capabilities/enforcement_ops.py` | MCP tools for monitoring |

### MCP Tools

| Tool | Description |
|------|-------------|
| `brain_enforcement_stats` | Get enforcement success rate and statistics |
| `brain_enforcement_patterns` | View learned patterns from failures |
| `brain_enforcement_analyze` | Trigger pattern learning from recent failures |
| `brain_enforcement_test` | Test intent analysis on a sample request |

### How It Works

```python
# Pre-flight: What tools are needed?
result = enforcer.pre_flight("Add this to my task list", tools)
# → required_tools: ["brain_add_task"]

# Enforcement prompt injected into agent:
# "You MUST call brain_add_task. If you don't, your response will be REJECTED."

# Post-flight: Did the agent actually call them?
validation = enforcer.post_flight(request, required, called, response)
# → passed: False (agent didn't call brain_add_task)

# Retry with stronger prompt:
# "CRITICAL: Your response was REJECTED. You MUST call brain_add_task NOW."

# Pattern learning (after enough failures):
patterns = learner.analyze_failures(failure_log)
# → "Agent frequently forgets brain_add_task for 'add task' requests"
# → Saved as engram for future sessions
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NUCLEUS_INTENT_MODEL` | `gemini-2.0-flash-exp` | Model for intent analysis |
| `NUCLEUS_VALIDATOR_MODEL` | `gemini-2.0-flash-exp` | Model for validation |
| `NUCLEUS_LEARNER_MODEL` | `gemini-2.0-flash-exp` | Model for pattern learning |

### Cost Impact
- Intent analysis: ~$0.0001 per request (Flash model)
- Validation: ~$0.0001 per request (Flash model)
- Pattern learning: ~$0.0001 per 20 failures
- **Negligible overhead for massive reliability improvement**

---

# Phase 73: Production-Grade Hardening (v1.3.0)

## Problem
Phase 71/72 achieved ~85-90% reliability. For production-grade autonomous operation (99.9% target), comprehensive hardening is needed across:
- LLM API failures (timeouts, rate limits, quota exhaustion)
- Cross-platform differences (Mac/Windows/Linux)
- MCP host differences (Windsurf, Claude Desktop, Perplexity, Antigravity, Cursor, OpenClaw, CLI)
- File system edge cases (concurrent access, disk full, permissions, corruption)
- Error observability (structured codes, aggregation, alerting)

## Solution: 4 Resilience Layers

### Layer 1: LLM API Resilience (`llm_resilience.py`)
- **Timeout handling**: Configurable (default 30s), thread-based for cross-platform support
- **Retry with exponential backoff**: 3 retries, jitter, respects Retry-After headers
- **Circuit breaker**: Opens after 5 failures, half-open after 60s cooldown, closes after 2 successes
- **Rate limit detection**: Detects 429 errors, extracts Retry-After
- **Fallback chain**: LLM → deterministic → graceful failure
- **Response validation**: Handles None, empty, malformed, markdown-wrapped JSON

### Layer 2: Environment Adaptation (`environment_detector.py`)
- **OS detection**: macOS, Windows, Linux (via `platform.system()`)
- **MCP host detection**: Windsurf, Claude Desktop, Perplexity, Antigravity, Cursor, OpenClaw, CLI
- **Path normalization**: Cross-platform path handling
- **Environment validation**: Required/optional env var checks
- **Safe brain path**: Guaranteed-writable path with fallback chain

### Layer 3: File System Resilience (`file_resilience.py`)
- **Atomic writes**: Write to temp file, then rename (prevents corruption from partial writes)
- **File locking**: fcntl (Unix) / msvcrt (Windows) / fallback (.lock file)
- **Disk space checks**: Pre-write validation with 50MB minimum
- **Permission checks**: Read/write/create verification
- **JSON corruption recovery**: Truncated file recovery, BOM handling, backup file fallback
- **JSONL resilience**: Line-level error skipping, concurrent append safety

### Layer 4: Error Telemetry (`error_telemetry.py`)
- **Structured error codes**: E001-E999 across 8 domains (LLM, Filesystem, Network, Validation, Auth, Concurrency, Environment, Tool Calling)
- **Error aggregation**: Count by domain/code, sliding-window rate calculation
- **Threshold alerting**: Configurable per-domain thresholds with callback support
- **Persistent error log**: JSONL-based error log for post-mortem analysis

## Integration
All Phase 71/72 modules upgraded:
- `LLMIntentAnalyzer` → Uses `ResilientLLMClient`, falls back to keyword analysis
- `LLMToolValidator` → Uses `ResilientLLMClient`, falls back to deterministic check
- `LLMToolEnforcer` → Persists via `ResilientFileOps` (atomic + locked)
- `LLMPatternLearner` → Reads/writes via `ResilientFileOps`, LLM calls via `ResilientLLMClient`
- `ToolRecommender` → Usage data via `ResilientFileOps`

## Environment Variables
| Variable | Default | Description |
|---|---|---|
| `NUCLEUS_LLM_TIMEOUT` | `30.0` | LLM call timeout in seconds |
| `NUCLEUS_MCP_HOST` | auto-detect | Force MCP host identity |

## Tests

- 26 tests for core Agent Runtime V2
- 9 tests for Agent Dashboard capability
- 11 tests for Budget Alerts
- 8 tests for Budget Operations
- 60 tests for Tool Calling Enforcement (Phase 71)
- 28 tests for Autonomous Tool Discovery (Phase 72)
- **137 tests for Production-Grade Hardening (Phase 73)**
  - 14 error categorization tests
  - 8 circuit breaker tests (including thread safety)
  - 4 retry/backoff tests
  - 12 response validation + JSON extraction tests
  - 7 resilient LLM client tests
  - 12 OS/MCP host detection tests
  - 10 environment info tests
  - 3 path normalization tests
  - 3 file locking tests
  - 6 atomic writer tests (including concurrent)
  - 8 JSON reader tests (including corruption recovery)
  - 3 disk space tests
  - 4 permission tests
  - 4 resilient file ops tests
  - 10 error telemetry tests
  - 3 alert manager tests
  - 9 integration tests
  - 11 cross-environment edge case tests
  - 4 module import tests
- All integrated with existing test suite (583 total)

---

**Maintained by**: Nucleus Team
**Last Updated**: 2026-02-24
