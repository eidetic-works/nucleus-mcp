"""
Recursive Mounter Prototype (AG-021).
Enables Nucleus to act as a Host-Runtime for external MCP servers.
Supported Transports: stdio (MVP).
"""

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MOUNTER")


class MountedServer:
    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        self.process: Optional[asyncio.subprocess.Process] = None
        self.id = f"mnt-{uuid.uuid4().hex[:6]}"
        self.mounted_at = asyncio.get_event_loop().time()
        self.tools: List[Dict] = []

    async def start(self):
        """Starts the external MCP server via stdio."""
        logger.info(f"🚀 Starting Mounted Server: {self.name} ({self.command} {' '.join(self.args)})")
        self.process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # In a real implementation, we would now negotiate list_tools
        # For the prototype, we assume it's running.
        return True

    async def stop(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logger.info(f"🛑 Stopped Mounted Server: {self.name}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Proxies a tool call to the mounted server via MCP (stdio)."""
        if not self.process:
            raise RuntimeError(f"Server {self.name} is not running")

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": str(uuid.uuid4())
        }

        # Send request
        self.process.stdin.write((json.dumps(request) + "\n").encode())
        await self.process.stdin.drain()

        # Read response (one line)
        line = await self.process.stdout.readline()
        if not line:
            return {"success": False, "error": "No response from mounted server"}
        
        return json.loads(line.decode())

    async def list_tools(self) -> List[Dict]:
        """Discover tools from the mounted server via MCP protocol."""
        if not self.process:
            return []

        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": str(uuid.uuid4())
        }

        try:
            self.process.stdin.write((json.dumps(request) + "\n").encode())
            await self.process.stdin.drain()

            # Read response with timeout
            line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=5.0
            )
            if not line:
                return []
            
            response = json.loads(line.decode())
            if "result" in response and "tools" in response["result"]:
                self.tools = response["result"]["tools"]
                return self.tools
            return []
        except asyncio.TimeoutError:
            logger.warning(f"Timeout discovering tools from {self.name}")
            return []
        except Exception as e:
            logger.error(f"Error discovering tools from {self.name}: {e}")
            return []



class RecursiveMounter:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.mounted_servers: Dict[str, MountedServer] = {}
        self.mounts_file = brain_path / "ledger" / "mounts.json"
        self.mounts_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_mounts()

    def _load_mounts(self):
        """Load persistent mounts from disk."""
        if not self.mounts_file.exists():
            return
            
        try:
            data = json.loads(self.mounts_file.read_text())
            for mount_data in data:
                # We don't auto-start on load in this MVP, but we restore the config
                # In a real OS, we would have a startup supervisor.
                # For now, we just track them.
                server = MountedServer(
                    name=mount_data["name"],
                    command=mount_data["command"],
                    args=mount_data["args"]
                )
                server.id = mount_data["id"]
                self.mounted_servers[server.id] = server
        except Exception as e:
            logger.error(f"Failed to load mounts: {e}")

    def _save_mounts(self):
        """Save persistent mounts to disk."""
        data = [
            {
                "id": s.id,
                "name": s.name,
                "command": s.command,
                "args": s.args
            }
            for s in self.mounted_servers.values()
        ]
        self.mounts_file.write_text(json.dumps(data, indent=2))

    async def mount(self, name: str, command: str, args: List[str]) -> str:
        """Mounts an external MCP server."""
        # Check for existing name
        if not name or len(name.strip()) < 2:
            return "Error: Server name must be at least 2 characters"

        # V9.1 Security: Recursive Self-Mount Detection
        # Check if the command or args try to launch the nucleus server itself
        forbidden_patterns = ["mcp_server_nucleus", "mcp-server-nucleus"]
        cmd_str = f"{command} {' '.join(args)}".lower()
        for pattern in forbidden_patterns:
            if pattern in cmd_str:
                import sys
                print("[NUCLEUS] SECURITY VIOLATION: Recursive mount detected", file=sys.stderr)
                return f"Error: Recursive mounting of {pattern} is forbidden for stability."

        for s in self.mounted_servers.values():
            if s.name == name:
                 return f"Server {name} is already mounted as {s.id}"
        
        server = MountedServer(name, command, args)
        try:
            await server.start()
            self.mounted_servers[server.id] = server
            self._save_mounts()
            return f"Successfully mounted {name} as {server.id}"
        except Exception as e:
            return f"Failed to mount {name}: {e}"

    async def unmount(self, server_id: str) -> str:
        """Unmounts and stops a server."""
        if server_id not in self.mounted_servers:
            return f"Server {server_id} not found"
            
        server = self.mounted_servers[server_id]
        await server.stop()
        del self.mounted_servers[server_id]
        self._save_mounts()
        return f"Unmounted {server.name} ({server_id})"

    def list_mounted(self) -> List[Dict]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "command": s.command,
                "status": "Running" if s.process and s.process.returncode is None else "Stopped"
            }
            for s in self.mounted_servers.values()
        ]

# Global singleton for prototype
_mounter: Optional[RecursiveMounter] = None

def get_mounter(brain_path: Path) -> RecursiveMounter:
    global _mounter
    if _mounter is None:
        _mounter = RecursiveMounter(brain_path)
    return _mounter
