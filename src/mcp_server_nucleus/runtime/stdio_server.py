
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to sys.path to handle relative imports if run as script
current_dir = Path(__file__).parent
if str(current_dir.parent.parent) not in sys.path:
    sys.path.append(str(current_dir.parent.parent))

from ..hypervisor.injector import Injector  # noqa: E402
from ..hypervisor.locker import Locker  # noqa: E402
from ..hypervisor.watchdog import Watchdog  # noqa: E402
from .common import get_brain_path, make_response  # noqa: E402

logger = logging.getLogger("nucleus.stdio_server")

class StdioServer:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.brain_path = get_brain_path()
        self.locker = Locker()
        self.injector = Injector(workspace_root)
        self.watchdog = Watchdog(workspace_root)

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        msg_id = request.get("id")

        if method == "initialize":
            return {
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Nucleus MCP Fallback Server", "version": "1.0.0"}
                }
            }

        elif method == "tools/list":
            return {
                "id": msg_id,
                "result": {
                    "tools": [
                        {"name": "lock_resource", "description": "Lock a file/folder (Layer 4)", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
                        {"name": "unlock_resource", "description": "Unlock a resource", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
                        {"name": "watch_resource", "description": "Monitor file/folder (Layer 1)", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
                        {"name": "brain_governance_status", "description": "Check security state", "inputSchema": {"type": "object", "properties": {}}},
                        {"name": "brain_write_engram", "description": "Write to long-term memory", "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}, "context": {"type": "string"}, "intensity": {"type": "integer"}}, "required": ["key", "value"]}},
                        {"name": "brain_query_engrams", "description": "Search memory engrams", "inputSchema": {"type": "object", "properties": {"context": {"type": "string"}, "min_intensity": {"type": "integer"}}}}
                    ]
                }
            }

        elif method == "tools/call":
            params = request.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            try:
                result_text = self.execute_tool(name, args)
                # Stdio tools usually return JSON strings from their impls
                try:
                    data = json.loads(result_text)
                    content = [{"type": "text", "text": json.dumps(data, indent=2)}]
                    is_error = not data.get("success", True)
                except Exception as e:
                    logger.error(f"Error parsing tool output: {e}")
                    content = [{"type": "text", "text": result_text}]
                    is_error = False

                return {
                    "id": msg_id,
                    "result": {"content": content, "isError": is_error}
                }
            except Exception as e:
                return {
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}
                }

        elif method == "resources/list":
            return {
                "id": msg_id,
                "result": {"resources": []}
            }

        elif method == "prompts/list":
            return {
                "id": msg_id,
                "result": {"prompts": []}
            }

        else:
            return {
                "id": msg_id,
                "error": {"code": -32601, "message": "Method not found"}
            }

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "lock_resource":
            success = self.locker.lock(args["path"])
            return make_response(success, data={"path": args["path"], "status": "LOCKED" if success else "FAILED"})
        elif name == "unlock_resource":
            success = self.locker.unlock(args["path"])
            return make_response(success, data={"path": args["path"], "status": "UNLOCKED" if success else "FAILED"})
        elif name == "watch_resource":
            self.watchdog.protect(args["path"])
            return make_response(True, data={"path": args["path"], "status": "WATCHING"})
        elif name == "brain_governance_status":
            return self._governance_status_impl()
        elif name == "brain_write_engram":
            return self._write_engram_impl(args["key"], args["value"], args.get("context", "General"), args.get("intensity", 5))
        elif name == "brain_query_engrams":
            return self._query_engrams_impl(args.get("context"), args.get("min_intensity", 1))
        raise ValueError(f"Unknown tool: {name}")

    def _governance_status_impl(self) -> str:
        try:
            engram_count = 0
            engram_file = self.brain_path / "engrams" / "ledger.jsonl"
            if engram_file.exists():
                engram_count = len(engram_file.read_text().splitlines())

            governance = {
                "policies": {"default_deny": True, "isolation_boundaries": True, "immutable_audit": True},
                "statistics": {"engram_count": engram_count},
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
                "key": key,
                "value": value,
                "context": context,
                "intensity": intensity,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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

            records = []
            with open(engram_path, "r") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))

            filtered = [r for r in records if r.get("intensity", 5) >= min_intensity]
            if context:
                filtered = [r for r in filtered if r.get("context") == context]

            filtered.sort(key=lambda x: x.get("intensity", 5), reverse=True)
            return make_response(True, data={"engrams": filtered, "count": len(filtered)})
        except Exception as e:
            return make_response(False, error=str(e))

def run():
    server = StdioServer(os.getcwd())
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    run()
