
from typing import List, Dict, Any
import os
import subprocess
from .base import Capability

class SelfHealingOps(Capability):
    def __init__(self):
        # Default health command (can be overridden by env)
        self.health_cmd = os.environ.get("NUCLEUS_HEALTH_CMD", "echo 'No health check configured.'")

    @property
    def name(self) -> str:
        return "self_healing_ops"

    @property
    def description(self) -> str:
        return "Diagnose and repair codebase issues."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_scan_health",
                "description": "Run the project's configured health check (tests/lints).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_generate_fix_plan",
                "description": "Generate a markdown plan to fix a specific error.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "error_log": {"type": "string", "description": "The error output or log to analyze"},
                        "context_files": {"type": "array", "items": {"type": "string"}, "description": "List of files related to the error"}
                    },
                    "required": ["error_log"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> Any:
        if tool_name == "brain_scan_health":
            return self._scan_health()
        elif tool_name == "brain_generate_fix_plan":
            return self._generate_fix_plan(args)
        return f"Tool {tool_name} not found"

    def _scan_health(self) -> Dict:
        """Runs the configured health check command."""
        try:
            # Security: We run the command as-is. 
            # In a real scenario, this should be sandboxed or strictly defined.
            result = subprocess.run(
                self.health_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for health checks
            )
            
            success = result.returncode == 0
            return {
                "success": success,
                "output": result.stdout,
                "errors": result.stderr,
                "command": self.health_cmd
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Health check timed out."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_fix_plan(self, args: Dict) -> str:
        """
        Generates a structured plan for the user (or agent) to execute.
        This DOES NOT Apply the fix. Safety first.
        """
        error_log = args.get("error_log", "")
        context_files = args.get("context_files", [])
        
        # In a full recursive agent, we would use an LLM here to analyze the code.
        # But since we ARE the LLM (when the tool returns), we return the prompt 
        # or a structure that helps the calling agent 'think'.
        
        # Actually, if this tool is called by an Agent, the Agent expects a result.
        # Returning a template helps the Agent formulate the next step.
        
        return f"""# Fix Plan Generation
        
**Analyzed Error:**
```
{error_log[:500]}...
```

**Context Files:**
{', '.join(context_files)}

**Recommended Strategy:**
1.  Read the context files using `code_read_file`.
2.  Analyze the logic causing the error.
3.  Create a reproduction case if possible.
4.  Apply the fix using `code_write_file`.
5.  Re-run `brain_scan_health`.

*System Note: The Agent receiving this output should now proceed to Step 1.*
"""
