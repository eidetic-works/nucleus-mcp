#!/usr/bin/env python3
import sys
from pathlib import Path

# Security: Ensure we can import our own package
# This makes the script standalone and robust against PYTHONPATH issues in Claude Desktop
current_path = Path(__file__).resolve()
current_dir = current_path.parent

# Robustly find the 'src' directory by looking for 'mcp_server_nucleus' in the path
# This handles cases where file structure might be slightly different or symlinked
src_p = current_path
while src_p.name != 'src' and src_p.parent != src_p:
    src_p = src_p.parent

if src_p.name == 'src':
    # found it
    pass
else:
    # Fallback to hardcoded relative path if traversal fails
    # script is in src/mcp_server_nucleus/runtime/stdio_server.py
    # we need src in path
    src_p = current_dir.parent.parent

src_root = str(src_p)

# Debug logging to stderr (because stdout is for JSON-RPC)
sys.stderr.write(f"[Nucleus] Bootstrapping standalone server...\n")
sys.stderr.write(f"[Nucleus] Script path: {current_path}\n")
sys.stderr.write(f"[Nucleus] Injected src root: {src_root}\n")

if src_root not in sys.path:
    # Use insert(0) to prioritize our local source
    sys.path.insert(0, src_root)

try:
    import mcp_server_nucleus
    sys.stderr.write(f"[Nucleus] Successfully imported mcp_server_nucleus package.\n")
except ImportError as e:
    sys.stderr.write(f"[Nucleus] FATAL: Could not import mcp_server_nucleus: {e}\n")
    sys.stderr.write(f"[Nucleus] sys.path: {sys.path}\n")
    # Fallback to hardcoded relative path if traversal fails
    sys.path.append(src_root)

import json
import logging
import traceback
import time
import os
import re
from typing import Any, Dict, List, Optional
from mcp_server_nucleus.hypervisor.locker import Locker
from mcp_server_nucleus.hypervisor.watchdog import Watchdog
from mcp_server_nucleus.hypervisor.injector import Injector
from mcp_server_nucleus.runtime.task_ops import (
    _list_tasks, _add_task, _update_task, 
    _claim_task, _get_next_task
)
from mcp_server_nucleus.runtime.memory import _write_memory, _search_memory
from pathlib import Path
from datetime import datetime
import asyncio
from mcp_server_nucleus.runtime.mounter_ops import get_mounter

# Configure logging to stderr to not corrupt stdout (which is for JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format='[Nucleus] %(message)s')
logger = logging.getLogger("nucleus_server")

# Silence watchdog library internals to prevent stdout/stderr pollution from internal threads
logging.getLogger("watchdog").setLevel(logging.ERROR)

START_TIME = time.time()

def make_response(success: bool, data: Any = None, error: str = None) -> str:
    """Helper to create a formatted JSON response string."""
    response = {"success": success}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return json.dumps(response, indent=2)

class StdioServer:
    def __init__(self):
        # Resolve paths first
        self.brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".")).resolve()
        workspace_root = self.brain_path
        
        self.locker = Locker()
        self.injector = Injector(str(workspace_root))
        self.watchdog = Watchdog(str(workspace_root))
        
        try:
            self.watchdog.start()
        except Exception as e:
            logger.error(f"Failed to start watchdog: {e}")
            
        self.mounter = get_mounter(self.brain_path)

    async def run(self):
        # Restore mounts from persistence
        await self.mounter.restore_mounts()
        
        loop = asyncio.get_running_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line)
                
                response = await self.handle_request(request)
                if response:
                    out = json.dumps(response)
                    print(out, flush=True)
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON")
            except Exception as e:
                logger.error(f"Server loop error: {e}")
                traceback.print_exc(file=sys.stderr)

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        msg_id = request.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05", # Updated protocol version
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "nucleus",
                        "version": "1.0.1"
                    }
                }
            }
        
        elif method == "notifications/initialized":
            # No response needed for notification
            return None
            
        elif method == "tools/list":
            # Create standard tools list
            tools = [
                        {
                            "name": "lock_resource",
                            "description": "✨ [NUCLEUS] Hypervisor: Lock a resource (file/folder) within the Sovereign Infrastructure to prevent any modification. High-tier governance tool.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "Absolute path to lock"},
                                    "reason": {"type": "string", "description": "Governance justification"},
                                    "agent_id": {"type": "string", "description": "Locking agent identifier"}
                                },
                                "required": ["path"]
                            }
                        },
                        {
                            "name": "status",
                            "description": "✨ [NUCLEUS] Hypervisor: Retrieve the operational status of the Sovereign Infrastructure and the COMMAND DECK Connectivity. USE THIS TO VERIFY THE SYSTEM IS ALIVE.",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "watch_resource",
                            "description": "[HYPERVISOR] key file/folder monitoring (Layer 1).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "Path to watch"}
                                },
                                "required": ["path"]
                            }
                        },
                        {
                            "name": "hypervisor_status",
                            "description": "[HYPERVISOR] Reports the current security state of the Agent OS.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}, 
                            }
                        },
                        {
                            "name": "set_hypervisor_mode",
                            "description": "[HYPERVISOR] Switch Visual Context (Injector).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "mode": {"type": "string", "enum": ["red", "blue", "reset"]}
                                },
                                "required": ["mode"]
                            }
                        },
                        {
                            "name": "brain_health",
                            "description": "Get comprehensive system health status.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "brain_audit_log",
                            "description": "View the cryptographic interaction log for trust verification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "limit": {"type": "integer", "description": "Number of recent entries", "default": 20}
                                }
                            }
                        },
                        {
                            "name": "brain_write_engram",
                            "description": "Write a long-term memory engram (learning/pattern).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string", "description": "Unique identifier"},
                                    "value": {"type": "string", "description": "Memory content"},
                                    "context": {"type": "string", "enum": ["Feature", "Architecture", "Brand", "Strategy", "Decision"], "default": "Decision"},
                                    "intensity": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
                                },
                                "required": ["key", "value"]
                            }
                        },
                        {
                            "name": "brain_query_engrams",
                            "description": "Query context-aware memory engrams.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "context": {"type": "string", "enum": ["Feature", "Architecture", "Brand", "Strategy", "Decision"]},
                                    "min_intensity": {"type": "integer", "minimum": 1, "maximum": 10, "default": 1}
                                }
                            }
                        },
                        {
                            "name": "brain_governance_status",
                            "description": "Get the current governance status and statistics.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "brain_list_tasks",
                            "description": "List all tasks from the Brain (Task Ledger).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "priority": {"type": "integer"},
                                    "skill": {"type": "string"},
                                    "claimed_by": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "brain_add_task",
                            "description": "Add a new task to the Brain.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "priority": {"type": "integer"},
                                    "blocked_by": {"type": "array", "items": {"type": "string"}},
                                    "required_skills": {"type": "array", "items": {"type": "string"}}
                                },
                                "required": ["description"]
                            }
                        },
                        {
                            "name": "brain_update_task",
                            "description": "Update an existing task in the Brain.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "status": {"type": "string"},
                                    "description": {"type": "string"},
                                    "priority": {"type": "integer"}
                                },
                                "required": ["task_id"]
                            }
                        },
                        {
                            "name": "brain_claim_task",
                            "description": "Claim a task for execution.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "agent_id": {"type": "string"}
                                },
                                "required": ["task_id"]
                            }
                        },
                        {
                            "name": "brain_get_next_task",
                            "description": "Get the highest priority actionable task.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "skills": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        }
            ]
            
            # --- MOUNTING TOOLS ---
            tools.append({
                "name": "brain_mount_server",
                "description": "Mount an external MCP server (Recursive/Aggregator).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mount_id": {"type": "string", "description": "Unique ID for this mount"},
                        "transport": {"type": "string", "enum": ["stdio", "sse"], "default": "stdio"},
                        "command": {"type": "string", "description": "Executable for stdio"},
                        "args": {"type": "array", "items": {"type": "string"}, "description": "Arguments for stdio"},
                        "env": {"type": "object", "description": "Environment vars"},
                        "url": {"type": "string", "description": "URL for SSE"}
                    },
                    "required": ["mount_id"]
                }
            })
            tools.append({
                "name": "brain_unmount_server",
                "description": "Unmount an external MCP server.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mount_id": {"type": "string"}
                    },
                    "required": ["mount_id"]
                }
            })
            tools.append({
               "name": "brain_traverse_and_mount",
               "description": "Recursively explore and mount downstream servers.",
               "inputSchema": {
                   "type": "object",
                   "properties": {
                       "root_mount_id": {"type": "string"}
                   },
                   "required": ["root_mount_id"]
               }
            })
            tools.append({
                "name": "thanos_snap",
                "description": "✨ [NUCLEUS] Hypervisor: Trigger the 'Thanos Snap' - Instantiating the SOVEREIGN COMMAND DECK Infrastructure (Stripe, Postgres, Search). THIS IS THE PRIMARY DEMO TRIGGER.",
                "inputSchema": {"type": "object", "properties": {}}
            })
            tools.append({
                "name": "list_mounted",
                "description": "✨ [NUCLEUS] Hypervisor: List all active mounted servers currently occupying the SOVEREIGN COMMAND DECK.",
                "inputSchema": {"type": "object", "properties": {}}
            })
            tools.append({
                "name": "discover_mounted_tools",
                "description": "🔍 [NUCLEUS] Hypervisor: Aggregates every tool from the SOVEREIGN COMMAND DECK into the current session. USE THIS AS THE 'SNAP' RESULT.",
                "inputSchema": {"type": "object", "properties": {}}
            })
            tools.append({
                "name": "brain_rescue_restoration",
                "description": "🛠️ [RESCUE] Force re-establishment of all infrastructure connections if they were missed at startup.",
                "inputSchema": {"type": "object", "properties": {}}
            })
            tools.append({
                "name": "brain_invoke_mounted_tool",
                "description": "Invoke a tool on a mounted MCP server.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "server_id": {"type": "string", "description": "Mount ID (e.g. mnt-123456)"},
                        "tool_name": {"type": "string", "description": "Tool name on that server"},
                        "arguments": {"type": "object", "description": "Tool arguments", "default": {}}
                    },
                    "required": ["server_id", "tool_name"]
                }
            })
            
            # Aggregate Tools from Mounts
            try:
                mounted_tools = await self.mounter.list_tools()
                tools.extend(mounted_tools)
            except Exception as e:
                logger.error(f"Failed to list mounted tools: {e}")

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": tools
                }
            }
            
        elif method == "tools/call":
            params = request.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            
            try:
                # --- MOUNTER DISPATCH ---
                if "__" in name:
                    # Delegate to mounted server
                    result = await self.mounter.call_tool(name, args)
                    # Result is a ToolCallResult object from mcp SDK. We need to serialize it.
                    # The SDK usually returns an object with `content`.
                    # We need to adapt it to the dict format this server expects.
                    
                    # Inspect result structure or assume it matches
                    content = []
                    if hasattr(result, "content"):
                         for item in result.content:
                             item_dict = item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                             content.append(item_dict)
                    else:
                        content = [{"type": "text", "text": str(result)}]
                        
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": content,
                            "isError": getattr(result, "isError", False)
                        }
                    }

                # --- LOCAL DISPATCH ---
                if name == "brain_mount_server":
                    res = await self.mounter.mount_server(
                        mount_id=args["mount_id"],
                        transport=args.get("transport", "stdio"),
                        command=args.get("command"),
                        args=args.get("args"),
                        env=args.get("env"),
                        url=args.get("url")
                    )
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}], "isError": False}}
                    
                elif name == "brain_unmount_server":
                    await self.mounter.unmount_server(args["mount_id"])
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": f"Unmounted server {args['mount_id']}"}], "isError": False}}
                    
                elif name == "thanos_snap":
                    from mcp_server_nucleus import brain_thanos_snap as snap_impl
                    res = await snap_impl()
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": res}], "isError": False}}
                    
                elif name == "status":
                    res = {
                        "status": "OPERATIONAL",
                        "mesh_tier": os.environ.get("NUCLEUS_TOOL_TIER", "UNKNOWN"),
                        "uptime": time.time() - START_TIME,
                        "mounts": len(self.mounter.sessions)
                    }
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}], "isError": False}}
                    
                elif name == "list_mounted":
                    res = await self.mounter.list_mounts()
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}], "isError": False}}
                    
                elif name == "discover_mounted_tools":
                    tools_list = await self.mounter.list_tools()
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(tools_list, indent=2)}], "isError": False}}
                    
                elif name == "brain_rescue_restoration":
                    await self.mounter.restore_mounts()
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": "Restoration rescue sequence triggered."}], "isError": False}}
                    
                elif name == "brain_invoke_mounted_tool":
                    server_id = args["server_id"]
                    tool_name = args["tool_name"]
                    tool_args = args.get("arguments", {})
                    # Regex fix: ^[a-zA-Z0-9_-]{1,64}$ prevents colons. Using double underscore.
                    namespaced_name = f"{server_id}__{tool_name}"
                    result = await self.mounter.call_tool(namespaced_name, tool_args)
                    # Convert MCP SDK result to JSON-RPC format
                    content = []
                    if hasattr(result, "content"):
                        for item in result.content:
                            item_dict = item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                            content.append(item_dict)
                    else:
                        content = [{"type": "text", "text": str(result)}]
                    return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": content, "isError": False}}

                result = self.execute_tool(name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ],
                        "isError": False
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    }
                }

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "lock_resource":
            metadata = {}
            if "reason" in args:
                metadata["reason"] = args["reason"]
            if "agent_id" in args:
                metadata["agent_id"] = args["agent_id"]
                
            self.locker.lock(args["path"], metadata=metadata)
            return f"🔒 LOCKED: {args['path']}"
            
        elif name == "unlock_resource":
            self.locker.unlock(args["path"])
            return f"🔓 UNLOCKED: {args['path']}"
            
        elif name == "get_lock_metadata":
            meta = self.locker.get_metadata(args["path"])
            return json.dumps(meta, indent=2)

        elif name == "watch_resource":
            self.watchdog.protect(args["path"])
            return f"👁️ WATCHING: {args['path']}"
            
        elif name == "hypervisor_status":
            status = []
            status.append("🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode / Python 3.9 Shim)")
            status.append(f"👁️  Watchdog: {'Active' if self.watchdog.observer.is_alive() else 'Inactive'}")
            status.append(f"🔒 Protected Paths: {len(self.watchdog.protected_paths)}")
            return "\n".join(status)
            
        elif name == "set_hypervisor_mode":
            mode = args["mode"]
            if mode == "red":
                self.injector.inject_identity("RED TEAM", "#ff0000")
                return "🔴 Hypervisor Mode: RED TEAM"
            elif mode == "blue":
                self.injector.inject_identity("BLUE TEAM", "#007acc")
                return "🔵 Hypervisor Mode: BLUE TEAM"
            elif mode == "reset":
                self.injector.reset_identity()
                return "⚪ Hypervisor Mode: RESET"
                
        # --- GOVERNANCE & HEALTH ---
        elif name == "brain_health":
            try:
                return json.dumps({
                    "status": "healthy",
                    "version": "1.0.0",
                    "tools_registered": 15,
                    "brain_path": str(self.brain_path),
                    "uptime_seconds": int(time.time() - START_TIME),
                    "python_version": sys.version.split()[0]
                }, indent=2)
            except Exception as e:
                return json.dumps({"status": "unhealthy", "error": str(e)})

        elif name == "brain_audit_log":
            return self._audit_log_impl(args.get("limit", 20))

        elif name == "brain_governance_status":
            return self._governance_status_impl()

        elif name == "brain_write_engram":
            return self._write_engram_impl(
                args["key"], 
                args["value"], 
                args.get("context", "Decision"), 
                args.get("intensity", 5)
            )

        elif name == "brain_query_engrams":
            return self._query_engrams_impl(
                args.get("context"), 
                args.get("min_intensity", 1)
            )

        # --- TASK TOOLS ---
        elif name == "brain_list_tasks":
            return json.dumps(_list_tasks(
                status=args.get("status"),
                priority=args.get("priority"),
                skill=args.get("skill"),
                claimed_by=args.get("claimed_by")
            ), indent=2)

        elif name == "brain_add_task":
            return json.dumps(_add_task(
                description=args.get("description"),
                priority=args.get("priority", 3),
                blocked_by=args.get("blocked_by"),
                required_skills=args.get("required_skills"),
                source="hypervisor"
            ), indent=2)

        elif name == "brain_update_task":
            updates = {k: v for k, v in args.items() if k != "task_id"}
            return json.dumps(_update_task(
                task_id=args.get("task_id"),
                updates=updates
            ), indent=2)

        elif name == "brain_claim_task":
             return json.dumps(_claim_task(
                 task_id=args.get("task_id"),
                 agent_id=args.get("agent_id", "hypervisor_agent")
             ), indent=2)

        elif name == "brain_get_next_task":
            return json.dumps(_get_next_task(
                skills=args.get("skills", [])
            ), indent=2)
                
        raise ValueError(f"Unknown tool: {name}")

    def _audit_log_impl(self, limit: int) -> str:
        try:
            log_path = self.brain_path / "ledger" / "interaction_log.jsonl"
            if not log_path.exists():
                return make_response(True, data={"entries": [], "count": 0, "message": "No log found."})
            
            entries = []
            with open(log_path, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            
            recent = entries[-limit:] if len(entries) > limit else entries
            recent.reverse()
            return make_response(True, data={"entries": recent, "count": len(recent), "total": len(entries)})
        except Exception as e:
            return make_response(False, error=str(e))

    def _governance_status_impl(self) -> str:
        try:
            audit_path = self.brain_path / "ledger" / "interaction_log.jsonl"
            audit_count = 0
            if audit_path.exists():
                with open(audit_path, "r") as f:
                    audit_count = sum(1 for line in f if line.strip())
            
            engram_path = self.brain_path / "engrams" / "ledger.jsonl"
            engram_count = 0
            if engram_path.exists():
                with open(engram_path, "r") as f:
                    engram_count = sum(1 for line in f if line.strip())
            
            governance = {
                "policies": {"default_deny": True, "isolation_boundaries": True, "immutable_audit": True},
                "statistics": {"audit_log_entries": audit_count, "engram_count": engram_count},
                "status": "ENFORCED"
            }
            return make_response(True, data=governance)
        except Exception as e:
            return make_response(False, error=str(e))

    def _write_engram_impl(self, key: str, value: str, context: str, intensity: int) -> str:
        try:
            if not re.match(r"^[a-zA-Z0-9_.-]+$", key):
                return make_response(False, error="Invalid key characters")
            
            engram_path = self.brain_path / "engrams" / "ledger.jsonl"
            engram_path.parent.mkdir(parents=True, exist_ok=True)
            
            engram = {
                "key": key, "value": value, "context": context,
                "intensity": intensity, "timestamp": datetime.now().isoformat()
            }
            with open(engram_path, "a") as f:
                f.write(json.dumps(engram) + "\n")
            
            return make_response(True, data={"engram": engram, "message": f"Engram '{key}' written."})
        except Exception as e:
            return make_response(False, error=str(e))

    def _query_engrams_impl(self, context: Optional[str], min_intensity: int) -> str:
        try:
            engram_path = self.brain_path / "engrams" / "ledger.jsonl"
            if not engram_path.exists():
                return make_response(True, data={"engrams": [], "count": 0})
            
            engrams = []
            with open(engram_path, "r") as f:
                for line in f:
                    if line.strip():
                        e = json.loads(line)
                        if context and e.get("context", "").lower() != context.lower():
                            continue
                        if e.get("intensity", 5) < min_intensity:
                            continue
                        engrams.append(e)
            
            engrams.sort(key=lambda x: x.get("intensity", 5), reverse=True)
            return make_response(True, data={"engrams": engrams, "count": len(engrams)})
        except Exception as e:
            return make_response(False, error=str(e))

def main():
    server = StdioServer()
    # Run async main loop
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
