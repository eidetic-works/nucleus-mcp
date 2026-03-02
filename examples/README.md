# Nucleus Examples

This directory contains example scripts demonstrating Nucleus usage.

## Files

| File | Description |
|------|-------------|
| `basic_usage.py` | Overview of core Nucleus features |
| `engram_demo.py` | Engram Ledger tutorial (persistent memory) |
| `depth_tracker_demo.py` | Depth Tracker tutorial (rabbit hole protection) |
| `governance_demo.py` | Governance Moat tutorial (security features) |
| `task_management_demo.py` | Task Queue tutorial (orchestration) |
| `mounter_demo.py` | Recursive Mounter tutorial (MCP aggregation) |

## Running Examples

```bash
# Set up Python path
cd mcp-server-nucleus
export PYTHONPATH=src

# Run basic usage
python examples/basic_usage.py
```

## Note

These examples are for **development and testing**. In production, Nucleus runs as an MCP server and you interact with it through your MCP client (Claude Desktop, Cursor, Windsurf, etc.).

For MCP client setup, see [docs/QUICK_START.md](../docs/QUICK_START.md).
