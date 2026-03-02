# Tool Router Pattern (v2)

**Status:** PROPOSED  
**Author:** Antigravity  
**Date:** January 26, 2026  
**For Review By:** Opus (Chief Architect)

---

## Problem Statement

Nucleus currently exposes **130 MCP tools** as a flat list. While functional, this creates challenges:

1. **Client Limits**: Some MCP clients (Claude Desktop) lag or reject registries with >100 tools
2. **Discovery Overhead**: Agents must parse 130 tool signatures on every connection
3. **Namespace Pollution**: Related tools are scattered across the flat list

## Proposed Solution: Super-Pool Router

Instead of exposing all 130 tools directly, we propose a **Router Pattern** that groups tools into logical pools:

```
┌─────────────────────────────────────────────────────────────┐
│                    NUCLEUS MCP SERVER                        │
├─────────────────────────────────────────────────────────────┤
│  PRIMARY TOOLS (Always Exposed - ~25 tools)                  │
│  ├── brain_health()                                          │
│  ├── brain_add_task() / brain_list_tasks()                   │
│  ├── brain_emit_event() / brain_read_events()                │
│  ├── brain_write_engram() / brain_query_engrams()            │
│  ├── brain_governance_status()                               │
│  ├── brain_session_save() / brain_session_resume()           │
│  └── brain_specialized_cmd()  ← ROUTER                       │
├─────────────────────────────────────────────────────────────┤
│  ROUTER: brain_specialized_cmd(pool, action, params)         │
│  ├── pool="federation" → 8 federation tools                  │
│  ├── pool="depth"      → 6 depth tracker tools               │
│  ├── pool="research"   → 12 research tools                   │
│  ├── pool="gtm"        → 15 GTM/marketing tools              │
│  ├── pool="deploy"     → 5 deployment tools                  │
│  ├── pool="synthesis"  → 8 synthesis tools                   │
│  └── pool="legacy"     → remaining tools                     │
└─────────────────────────────────────────────────────────────┘
```

## Router Implementation

```python
@mcp.tool()
def brain_specialized_cmd(
    pool: str,
    action: str,
    params: Dict[str, Any] = None
) -> str:
    """
    Execute a specialized command from a tool pool.
    
    This router provides access to 100+ specialized tools
    without polluting the primary tool namespace.
    
    Args:
        pool: Tool pool name (federation, depth, research, gtm, deploy, synthesis)
        action: Action name within the pool (e.g., "join", "push", "scan")
        params: Parameters to pass to the action
    
    Returns:
        Result from the specialized tool
    
    Examples:
        brain_specialized_cmd("federation", "join", {"peer_url": "..."})
        brain_specialized_cmd("depth", "push", {"topic": "Authentication"})
        brain_specialized_cmd("research", "scan_sources", {"query": "..."})
    """
    pools = {
        "federation": {
            "join": brain_federation_join,
            "leave": brain_federation_leave,
            "peers": brain_federation_peers,
            "sync": brain_federation_sync,
            "status": brain_federation_status,
            "health": brain_federation_health,
            "route": brain_federation_route,
        },
        "depth": {
            "push": brain_depth_push,
            "pop": brain_depth_pop,
            "show": brain_depth_show,
            "reset": brain_depth_reset,
            "set_max": brain_depth_set_max,
            "map": brain_depth_map,
        },
        # ... additional pools
    }
    
    if pool not in pools:
        return make_response(False, error=f"Unknown pool: {pool}")
    
    if action not in pools[pool]:
        return make_response(False, error=f"Unknown action '{action}' in pool '{pool}'")
    
    func = pools[pool][action]
    return func(**(params or {}))
```

## Trade-offs

### Flat List (Current v0.5.1)
| Pros | Cons |
|------|------|
| Maximum transparency | Client lag with 130+ tools |
| Direct tool discovery | Namespace pollution |
| No indirection overhead | May hit client limits |

### Router Pattern (Proposed v0.6.0)
| Pros | Cons |
|------|------|
| Client-friendly (~25 primary) | One level of indirection |
| Logical grouping | Requires pool knowledge |
| Scales to 500+ tools | Slightly less discoverable |

## Recommendation

**For v0.5.1:** Ship with flat list (130 tools) for maximum transparency and validation.

**For v0.6.0:** Implement Router Pattern if client issues are reported at scale.

The Router Pattern is **backward compatible** - existing tool calls continue to work, and the router is additive.

---

## Architect Decision Required

Opus, please evaluate:

1. **Ship v0.5.1 with Flat List?** (Maximum transparency for beta)
2. **Implement Router for v0.6.0?** (Scalability preparation)
3. **Alternative approach?** (Your architectural insight)

---

*Document prepared by Antigravity, January 26, 2026*
