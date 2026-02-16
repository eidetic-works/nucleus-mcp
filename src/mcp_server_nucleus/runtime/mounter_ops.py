
import json
import os
import logging
from typing import Dict, List, Any
from pathlib import Path

# Try importing mcp, handle failure gracefully for the "no dependency" case
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Mock classes for type hinting if missing
    ClientSession = Any
    StdioServerParameters = Any

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
        print(f"🔄 Restoring {len(self.mount_configs)} mounts...")
        for mount_id, config in self.mount_configs.items():
            try:
                if config.get("transport") == "stdio":
                    await self.mount_server(
                        mount_id=mount_id,
                        transport="stdio",
                        command=config.get("command"),
                        args=config.get("args"),
                        env=config.get("env")
                    )
                    print(f"  ✅ Re-mounted: {mount_id}")
                elif config.get("transport") == "sse":
                    await self.mount_server(
                        mount_id=mount_id,
                        transport="sse",
                        url=config.get("url")
                    )
                    print(f"  ✅ Re-mounted: {mount_id}")
            except Exception as e:
                logger.error(f"Failed to restore mount {mount_id}: {e}")
                print(f"  ❌ Failed to restore {mount_id}: {e}")
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
        if not MCP_AVAILABLE:
            raise ImportError("The 'mcp' package is not installed. Please install it to use mounting features.")

        if mount_id in self.sessions:
            raise ValueError(f"Mount ID '{mount_id}' is already active.")

        if transport == "stdio":
            if not command:
                raise ValueError("Command is required for stdio transport")
            
            server_params = StdioServerParameters(
                command=command,
                args=args or [],
                env={**os.environ, **(env or {})}
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
                result = await session.list_tools()
                for tool in result.tools:
                    # Create a namespaced copy of the tool definition
                    tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else tool.__dict__
                    tool_dict["name"] = f"{mount_id}:{tool.name}"
                    tool_dict["description"] = f"[{mount_id}] {tool_dict.get('description', '')}"
                    aggregated_tools.append(tool_dict)
            except Exception as e:
                logger.error(f"Error listing tools for {mount_id}: {e}")
                
        return aggregated_tools

    async def call_tool(self, name: str, args: Dict) -> Any:
        """
        Call a namespaced tool.
        Name format: 'mount_id:tool_name'
        """
        if ":" not in name:
            raise ValueError("Invalid namespaced tool name. Format must be 'mount_id:tool_name'")
            
        mount_id, tool_name = name.split(":", 1)
        
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
