
import asyncio
import json
import os
import logging
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

# Implement SimpleMCPClient for Host-Guest compatibility (Py3.9 Host -> Py3.14 Guest)
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    
    # Simple JSON-RPC Client shim for Python 3.9 Host
    # This allows the host (Nucleus) to talk to child processes (Mocks) 
    # even when the host lacks the 'mcp' package.
    class StdioServerParameters:
        def __init__(self, command, args, env=None):
            self.command = command
            self.args = args
            self.env = env

    class SimpleTool:
        def __init__(self, name, description, inputSchema):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

    class SimpleListToolsResult:
        def __init__(self, tools):
            self.tools = tools

    class SimpleMCPClient:
        def __init__(self, command, args, env):
            self.command = command
            self.args = args
            self.env = env
            self.proc = None
            self.msg_id = 0
            self.pending_requests = {}
            self.reader_task = None

    class ContentItem:
        def __init__(self, data):
            self.type = data.get("type", "text")
            self.text = data.get("text", "")
            if isinstance(data, dict):
                self.__dict__.update(data)
        def model_dump(self):
            return self.__dict__

    class ToolResult:
        def __init__(self, content_data):
            self.content = [ContentItem(c) for c in content_data]

        async def __aenter__(self):
            await self.start()
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.proc:
                try:
                    self.proc.terminate()
                    await self.proc.wait()
                except:
                    pass
            if self.reader_task:
                self.reader_task.cancel()

        async def start(self):
            self.proc = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=sys.stderr, # Pass stderr through
                env=self.env
            )
            self.reader_task = asyncio.create_task(self._reader_loop())
            
            # Initialize handshake
            init_req = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "nucleus-shim", "version": "1.0.0"}
                }
            }
            res = await self._send_request(init_req)
            
            # initialized notification
            notify = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            self._send_notification(notify)
            return res

        def _next_id(self):
            self.msg_id += 1
            return self.msg_id

        def _send_notification(self, req):
            if self.proc and self.proc.stdin:
                line = json.dumps(req) + "\n"
                self.proc.stdin.write(line.encode())
                # No await drain here in synchronous method, relies on transport buffering
                # Use create_task for drain if needed, but for small payloads usually fine

        async def _send_request(self, req):
            req_id = req["id"]
            future = asyncio.Future()
            self.pending_requests[req_id] = future
            
            if self.proc and self.proc.stdin:
                line = json.dumps(req) + "\n"
                self.proc.stdin.write(line.encode())
                await self.proc.stdin.drain()
            
            return await future

        async def _reader_loop(self):
            try:
                while True:
                    line = await self.proc.stdout.readline()
                    if not line:
                        break
                    
                    try:
                        msg = json.loads(line.decode())
                        if "id" in msg and msg["id"] in self.pending_requests:
                            if "result" in msg:
                                self.pending_requests[msg["id"]].set_result(msg["result"])
                            elif "error" in msg:
                                self.pending_requests[msg["id"]].set_exception(Exception(str(msg["error"])))
                            del self.pending_requests[msg["id"]]
                    except Exception as e:
                        logger.error(f"Shim parser error: {e}")
            except Exception:
                pass

        async def list_tools(self):
            req = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {}
            }
            res = await self._send_request(req)
            tools = []
            if "tools" in res:
                for t in res["tools"]:
                    tools.append(SimpleTool(t["name"], t.get("description", ""), t.get("inputSchema", {})))
            return SimpleListToolsResult(tools)

        async def call_tool(self, name, arguments):
            req = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments
                }
            }
            res = await self._send_request(req)
            return ToolResult(res.get("content", []))

        async def initialize(self):
            pass # Handled in start

    # Aliases
    ClientSession = SimpleMCPClient


logger = logging.getLogger("nucleus_mounter")

class Mounter:
    """
    Manages connections to external MCP servers (Recursive Mounting).
    Supports Stdio and SSE transports.
    """
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.mounts_file = brain_path / "mounts.json"
        
        # In-memory session store: mount_id -> ClientSession
        self.sessions: Dict[str, ClientSession] = {}
        # Keep track of exit stack context managers to close them later
        self.exit_stacks: Dict[str, Any] = {}
        
        self.mount_configs: Dict[str, Dict] = {}
        self._load_mounts()

    def _load_mounts(self):
        """Load persisted mount configurations."""
        if self.mounts_file.exists():
            try:
                with open(self.mounts_file, "r") as f:
                    self.mount_configs = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load mounts: {e}")
    async def restore_mounts(self):
        """Re-establish connections for all persisted mounts."""
        if os.environ.get("NUCLEUS_SKIP_AUTOSTART", "false").lower() == "true":
             return # Child processes should not restore mounts
             
        for mount_id, config in self.mount_configs.items():
            try:
                if config.get("transport") == "stdio":
                    # Timeout guard for restoration to prevent whole app hang
                    await asyncio.wait_for(
                        self.mount_server(
                            mount_id=mount_id,
                            transport="stdio",
                            command=config.get("command"),
                            args=config.get("args"),
                            env=config.get("env")
                        ),
                        timeout=5.0
                    )
                elif config.get("transport") == "sse":
                    await self.mount_server(
                        mount_id=mount_id,
                        transport="sse",
                        url=config.get("url")
                    )
            except Exception as e:
                logger.error(f"Failed to restore mount {mount_id}: {e}")
    def _save_mounts(self):
        """Persist mount configurations."""
        try:
            with open(self.mounts_file, "w") as f:
                json.dump(self.mount_configs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save mounts: {e}")

    async def mount_server(self, 
                          mount_id: str, 
                          transport: str, 
                          command: str = None, 
                          args: List[str] = None, 
                          env: Dict[str, str] = None,
                          url: str = None) -> Dict[str, Any]:
        """
        Mount an MCP server.
        
        Args:
            mount_id: Unique identifier for this mount.
            transport: "stdio" or "sse".
            command: (stdio) Executable command.
            args: (stdio) List of arguments.
            env: (stdio) Environment variables.
            url: (sse) Server URL.
        """
        # Removed hard check for MCP_AVAILABLE to allow Shim usage
        # if not MCP_AVAILABLE:
        #    raise ImportError("The 'mcp' package is not installed. Please install it to use mounting features.")

        if mount_id in self.sessions:
            raise ValueError(f"Mount ID '{mount_id}' is already active.")

        if transport == "stdio":
            if not command:
                raise ValueError("Command is required for stdio transport")
            
            # Prepare environment
            server_env = {**os.environ, **(env or {}), "NUCLEUS_SKIP_AUTOSTART": "true"}
            
            # --- SHIM PATH (Python 3.9 / No 'mcp' lib) ---
            if not MCP_AVAILABLE:
                from contextlib import AsyncExitStack
                
                # Use our Shim Client
                session = SimpleMCPClient(command, args or [], server_env)
                
                stack = AsyncExitStack()
                await stack.enter_async_context(session)
                self.exit_stacks[mount_id] = stack
                self.sessions[mount_id] = session
                
                # Persist config
                self.mount_configs[mount_id] = {
                    "transport": "stdio",
                    "command": command,
                    "args": args,
                    "env": env,
                    "status": "connected"
                }
                self._save_mounts()
                
                # List tools to confirm connection and get count
                tools_result = await session.list_tools()
                tool_count = len(tools_result.tools)
                return {"mount_id": mount_id, "status": "connected", "tools": tool_count}

            # --- STANDARD PATH (Python 3.10+ / 'mcp' lib) ---
            server_params = StdioServerParameters(
                command=command,
                args=args or [],
                env=server_env
            )
            
            # We need to maintain the context manager lifecycle
            # This is a bit tricky in an async methods that keeps the session open.
            # We'll use an AsyncExitStack stored in class state.
            from contextlib import AsyncExitStack
            
            stack = AsyncExitStack()
            stdio_transport = await stack.enter_async_context(stdio_client(server_params))
            self.exit_stacks[mount_id] = stack
            
            read, write = stdio_transport
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[mount_id] = session
            
            # Persist config
            self.mount_configs[mount_id] = {
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": env,
                "status": "connected"
            }
            self._save_mounts()
            
            return {"mount_id": mount_id, "status": "connected", "tools": len((await session.list_tools()).tools)}

        elif transport == "sse":
            if not url:
                raise ValueError("URL is required for SSE transport")
                
            from contextlib import AsyncExitStack
            stack = AsyncExitStack()
            sse_transport = await stack.enter_async_context(sse_client(url))
            self.exit_stacks[mount_id] = stack
            
            read, write = sse_transport
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[mount_id] = session
            
            self.mount_configs[mount_id] = {
                "transport": "sse",
                "url": url,
                "status": "connected"
            }
            self._save_mounts()
            
            return {"mount_id": mount_id, "status": "connected", "tools": len((await session.list_tools()).tools)}
            
        else:
            raise ValueError(f"Unknown transport: {transport}")

    async def mount(self, name: str, command: str, args: List[str]) -> str:
        """Compatibility method for legacy tool naming (mount vs mount_server)."""
        try:
            # Check for existing name to match RecursiveMounter behavior
            for mid, config in self.mount_configs.items():
                if config.get("name") == name or mid == name:
                    return f"Server {name} is already mounted as {mid}"

            res = await self.mount_server(
                mount_id=name,
                transport="stdio",
                command=command,
                args=args
            )
            # Add a name field to config for tracking
            self.mount_configs[name]["name"] = name
            self._save_mounts()
            return f"Successfully mounted {name} as {res['mount_id']}"
        except Exception as e:
            return f"Error: {e}"

    async def unmount_server(self, mount_id: str):
        """Unmount a server and close connection."""
        if mount_id in self.exit_stacks:
            await self.exit_stacks[mount_id].aclose()
            del self.exit_stacks[mount_id]
        
        if mount_id in self.sessions:
            del self.sessions[mount_id]
            
        if mount_id in self.mount_configs:
            del self.mount_configs[mount_id]
            self._save_mounts()

    async def list_mounts(self) -> List[Dict]:
        """List active mounts."""
        return [
            {"id": k, **v} for k, v in self.mount_configs.items()
        ]

    async def list_tools(self) -> List[Dict]:
        """
        Aggregate tools from all mounted servers.
        Tools are namespaced as 'mount_id:tool_name'.
        """
        aggregated_tools = []
        
        for mount_id, session in self.sessions.items():
            try:
                # Core Guard: Prevent dead sub-servers from hanging the Hypervisor
                result = await asyncio.wait_for(session.list_tools(), timeout=2.0)
                for tool in result.tools:
                    # Create a namespaced copy of the tool definition
                    tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else tool.__dict__
                    # Regex fix: ^[a-zA-Z0-9_-]{1,64}$ prevents colons. Using double underscore.
                    tool_dict["name"] = f"{mount_id}__{tool.name}"
                    tool_dict["description"] = f"[{mount_id}] {tool_dict.get('description', '')}"
                    aggregated_tools.append(tool_dict)
            except Exception as e:
                logger.error(f"Error listing tools for {mount_id}: {e}")
                
        return aggregated_tools

    async def call_tool(self, name: str, args: Dict) -> Any:
        """
        Call a namespaced tool.
        Name format: 'mount_id__tool_name'
        """
        if "__" not in name:
            raise ValueError("Invalid namespaced tool name. Format must be 'mount_id__tool_name'")
            
        mount_id, tool_name = name.split("__", 1)
        
        if mount_id not in self.sessions:
            raise ValueError(f"Mount ID '{mount_id}' not found")
            
        session = self.sessions[mount_id]
        result = await session.call_tool(tool_name, arguments=args)
        return result

    async def traverse_and_mount(self, root_mount_id: str) -> Dict:
        """
        Recursive discovery logic.
        Inspects tools of a mounted server to find other 'mount_server' compatible capabilities.
        This is a heuristic implementation for the demo.
        """
        if root_mount_id not in self.sessions:
             raise ValueError(f"Root mount '{root_mount_id}' not found")

        session = self.sessions[root_mount_id]
        tools = await session.list_tools()
        
        found_servers = []
        
        # Heuristic: Look for tools that return 'mcp_server' or have 'mount' in description
        # In a real scenario, this would use a standardized 'list_servers' tool or resource.
        # For the demo, we'll just report what we see.
        
        for tool in tools.tools:
             if "server" in tool.name.lower() or "mount" in tool.name.lower():
                 found_servers.append(tool.name)
                 
        return {
            "root": root_mount_id,
            "potential_sub_servers": found_servers,
            "status": "traversal_complete"
        }
# Global singleton for prototype
_mounter: Optional[Mounter] = None

def get_mounter(brain_path: Path) -> Mounter:
    global _mounter
    if _mounter is None:
        _mounter = Mounter(brain_path)
    return _mounter

# ============================================================
# MOUNTER IMPL FUNCTIONS (Extracted from __init__.py)
# ============================================================

from .common import get_brain_path, make_response

async def _brain_mount_server_impl(name: str, command: str, args: List[str] = []) -> str:
    """Implement brain_mount_server."""
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        return await mounter.mount(name, command, args)
    except Exception as e:
        return f"Error mounting server: {e}"

async def _brain_thanos_snap_impl() -> str:
    """Implement brain_thanos_snap."""
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        
        # Robust path resolution for mock script
        # Try to find workspace root relative to this file
        # This file is in src/mcp_server_nucleus/runtime/mounter_ops.py
        # Workspace root is 5 levels up
        workspace_root = Path(__file__).parent.parent.parent.parent.parent
        mock_script = workspace_root / "scripts" / "mock_mcp_server.py"
        
        if not mock_script.exists():
             # Fallback: try relative from cwd
             mock_script = Path("scripts/mock_mcp_server.py").resolve()
             
        # Use current Python executable to ensure compatibility
        python_cmd = sys.executable
        
        results = []
        # Mount Stripe
        res_stripe = await mounter.mount("stripe", python_cmd, [str(mock_script), "stripe"])
        results.append(f"Stripe: {res_stripe}")
        
        # Mount Postgres
        res_pg = await mounter.mount("postgres", python_cmd, [str(mock_script), "postgres"])
        results.append(f"Postgres: {res_pg}")
        
        # Mount Search
        res_search = await mounter.mount("search", python_cmd, [str(mock_script), "brave_search"])
        results.append(f"Brave Search: {res_search}")
        
        return "✨ Thanos Snap Complete! Recursive mesh populated:\n" + "\n".join(results)
    except Exception as e:
        return f"Error during Thanos Snap: {e}"

async def _brain_unmount_server_impl(server_id: str) -> str:
    """Implement brain_unmount_server."""
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        await mounter.unmount_server(server_id)
        return f"Unmounted {server_id}"
    except Exception as e:
        return f"Error unmounting server: {e}"

def _brain_list_mounted_impl() -> str:
    """Implement brain_list_mounted."""
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        # Access configs directly since list_mounts is async but this tool is sync in definition
        # If we change it to async in __init__.py, we can await. But keeping compatibility.
        # Mounter keeps state in mounter.mount_configs
        return make_response(True, data=[{"id": k, **v} for k, v in mounter.mount_configs.items()])
    except Exception as e:
        return make_response(False, error=str(e))

async def _brain_discover_mounted_tools_impl(server_id: str = None) -> str:
    """Implement brain_discover_mounted_tools."""
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        
        results = {}
        
        if server_id:
            if server_id not in mounter.sessions:
                 return make_response(False, error=f"Server {server_id} not found")
            
            session = mounter.sessions[server_id]
            name = mounter.mount_configs.get(server_id, {}).get("name", server_id)
            
            tools_result = await session.list_tools()
            tool_list = []
            for t in tools_result.tools:
                 tool_list.append(t.model_dump() if hasattr(t, "model_dump") else t.__dict__)
            
            return make_response(True, data={name: tool_list})
        
        # Query all
        for sid, session in mounter.sessions.items():
            name = mounter.mount_configs.get(sid, {}).get("name", sid)
            try:
                tools_result = await session.list_tools()
                tool_list = []
                for t in tools_result.tools:
                     tool_list.append(t.model_dump() if hasattr(t, "model_dump") else t.__dict__)
                results[name] = tool_list
            except Exception as e:
                logger.error(f"Error listing tools for {sid}: {e}")
                results[name] = {"error": str(e)}
                
        return make_response(True, data=results)
    except Exception as e:
        return make_response(False, error=str(e))

async def _brain_invoke_mounted_tool_impl(server_id: str, tool_name: str, arguments: Dict[str, Any] = {}) -> str:
    """Implement brain_invoke_mounted_tool."""
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        
        if server_id not in mounter.sessions:
             return json.dumps({"success": False, "error": f"Server {server_id} not found"})
             
        session = mounter.sessions[server_id]
        
        # Call tool
        result = await session.call_tool(tool_name, arguments)
        
        # content is list of ContentItem
        content_data = []
        for c in result.content:
            content_data.append(c.model_dump() if hasattr(c, "model_dump") else c.__dict__)
            
        return json.dumps({"content": content_data})
    except Exception as e:
        return json.dumps({"error": str(e)})

