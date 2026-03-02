from typing import List, Dict, Any
import os
import subprocess
from pathlib import Path
from .base import Capability

class CodeOps(Capability):
    @property
    def name(self) -> str:
        return "code_ops"

    @property
    def description(self) -> str:
        return "FileSystem and Shell Access for Coding Agents."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "code_read_file",
                "description": "Read file contents.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "path": {"type": "string", "description": "Absolute or relative path"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "code_write_file",
                "description": "Write or overwrite file contents. Creates directories if needed.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "path": {"type": "string", "description": "Absolute or relative path"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "code_run_command",
                "description": "Execute a shell command.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "integer", "default": 30}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "code_list_files",
                "description": "List files in directory.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "path": {"type": "string", "default": "."}
                    }
                }
            }
        ]

    def _resolve_path(self, path_str: str) -> Path:
        """
        Self-Healing Path Resolver.
        """
        cwd = Path(os.getcwd())
        path = Path(path_str)
        
        # 1. Try path as-is
        if path.exists():
            return path
            
        # 2. Try relative to CWD
        if not path.is_absolute():
            candidate = cwd / path
            if candidate.exists():
                return candidate
        
        # 3. Try relative to Project Root (BRAIN_PATH.parent)
        brain_path = Path(os.environ.get("NUCLEUS_BRAIN_PATH", "./.brain"))
        project_root = brain_path.parent
        
        if not path.is_absolute():
            candidate = project_root / path
            if candidate.exists():
                return candidate
        else:
            # If absolute but invalid, try re-rooting
            # e.g. /gentlequest-blog/... -> PROJECT_ROOT/gentlequest-blog/...
            if 'ai-mvp-backend' in path_str:
                relative = path_str.split('ai-mvp-backend')[-1].lstrip('/')
                candidate = project_root / relative
                if candidate.exists():
                    return candidate
            else:
                # Try just the relative part of the absolute path
                # e.g. /foo/bar -> PROJECT_ROOT/foo/bar
                relative = path_str.lstrip('/')
                candidate = project_root / relative
                if candidate.exists():
                    return candidate

        return path

    def execute_tool(self, tool_name: str, args: Dict) -> str:
        """Execute local filesystem/shell operations."""
        cwd = os.getcwd()
        
        if tool_name == "code_read_file":
            path = self._resolve_path(args['path'])
            
            if not path.exists():
                return f"Error: File not found: {path} (in {cwd})"
            return path.read_text(encoding='utf-8')
            
        elif tool_name == "code_write_file":
            path_str = args['path']
            path = Path(path_str)
            
            # ============================================================
            # ENTERPRISE PATH RESOLUTION (Fix for Read-Only Filesystem Bug)
            # ============================================================
            # Problem: Agent subprocess may not have NUCLEUS_BRAIN_PATH set,
            # causing relative paths like 'gentlequest-blog/...' to resolve to '/'
            # Solution: Robust fallback chain with explicit validation
            
            PROJECT_ROOT = Path(".")
            
            if not path.is_absolute():
                resolved_root = None
                
                # Option 1: Use NUCLEUS_BRAIN_PATH if valid
                brain_path_str = os.environ.get("NUCLEUS_BRAIN_PATH", "")
                if brain_path_str and ".brain" in brain_path_str:
                    brain_path = Path(brain_path_str)
                    if brain_path.exists():
                        resolved_root = brain_path.parent
                
                # Option 2: Fallback to hardcoded PROJECT_ROOT
                if not resolved_root:
                    resolved_root = PROJECT_ROOT
                
                path = resolved_root / path
                # Log resolution for debugging
                print(f"[CodeOps] Path resolved: {path_str} → {path}")
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args['content'], encoding='utf-8')
            return f"✅ Wrote {len(args['content'])} bytes to {path}"

            
        elif tool_name == "code_run_command":
            cmd = args['command']
            timeout = args.get('timeout', 30)
            try:
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    cwd=cwd, 
                    timeout=timeout
                )
                return f"Exit Code: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            except subprocess.TimeoutExpired:
                return f"Error: Command timed out after {timeout}s"
            except Exception as e:
                return f"Error: {str(e)}"

        elif tool_name == "code_list_files":
            path = Path(args.get('path', '.'))
            if not path.is_absolute():
                path = Path(cwd) / path
            
            if not path.exists():
                 return f"Error: Path not found: {path}"
                 
            try:
                # Use 'ls -F' style output for simplicity
                entries = []
                for p in path.iterdir():
                    kind = "/" if p.is_dir() else ""
                    entries.append(f"{p.name}{kind}")
                return "\n".join(sorted(entries))
            except Exception as e:
                return f"Error listing files: {str(e)}"
                
        return f"Tool {tool_name} not found in CodeOps."
