"""
Strategy Capability
Allows the Oracle to interact with the "Cortex" (Strategy Folder).
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..capabilities.base import Capability

logger = logging.getLogger("cap.strategy")

class StrategyTool(Capability):
    def __init__(self, brain_path: Path, allowed_paths: List[str]):
        self.brain_path = brain_path
        # Resolve variables in paths
        self.allowed_paths = [
            Path(p.replace("${BRAIN_PATH}", str(brain_path))).resolve() 
            for p in allowed_paths
        ]
        self._name = "strategy_ops"
        self._desc = "Read and Evolve Strategic Protocols"

    @property
    def name(self): return self._name

    @property
    def description(self): return self._desc

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "read_strategy",
                "description": "Reads a strategy document or protocol.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Relative path to brain root (e.g. 'strategy/SOVEREIGN_TESTAMENT.md')"}
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "evolve_protocol",
                "description": "Overwrites/Updates a protocol document with new evolved content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content": {"type": "string", "description": "The new content"},
                        "reason": {"type": "string", "description": "Why was this evolution necessary?"}
                    },
                    "required": ["filename", "content", "reason"]
                }
            }
        ]

    def _validate_path(self, filename: str) -> Optional[Path]:
        # Simple security verify
        target = (self.brain_path / filename).resolve()
        
        # Check if target is within any allowed path
        allowed = False
        for parent in self.allowed_paths:
            # Check exact match (File allow)
            if target == parent:
                allowed = True
                break
            # Check directory containment
            # We assume if it doesn't have an suffix, it might be a dir, 
            # or we just check if it IS a dir on disk. 
            # If it's a non-existent dir whitelisted, we can't easily distinguish from file without trailing slash convention.
            # For now, rely on standard pathlib behavior.
            try:
                if parent.is_dir() and str(target).startswith(str(parent)):
                    allowed = True
                    break
            except OSError:
                pass
                    
        if not allowed:
            logger.warning(f"⛔ ACCESS DENIED: {target} is not in allowed strategy paths.")
            return None
            
        return target

    def execute(self, params: Dict[str, Any]) -> str:
        # Since I'm binding multiple tools to one capability execute,
        # I need a way to dispatch. 
        # But Capability.execute usually takes 'tool_name' or we rely on the implementation wrapping it.
        # Wait, the Standard we mostly used was: 
        # 'execute' takes the params of the *tool call*.
        # But which tool? 
        # Standard implementation in 'tool_manager' usually passes the Tool Name AND arguments.
        # But 'Capability.execute' interface in this codebase usually takes just params?
        # Let's check 'base.py' or 'filesystem.py'.
        # Assuming for now we need a 'name' or 'action' in params, or we implement separate capabilities.
        # Let's assume the caller passes the tool name or strict params.
        
        # Hack for MVP: Check keys
        filename = params.get("filename")
        content = params.get("content")
        reason = params.get("reason")
        
        if content is None:
            # READ
            path = self._validate_path(filename)
            if not path:
                return "Error: Access Denied"
            if not path.exists():
                return "Error: File not found"
            return path.read_text()
        else:
            # WRITE (Evolve)
            path = self._validate_path(filename)
            if not path:
                return "Error: Access Denied"
            
            # Log the evolution
            log_path = self.brain_path / "decisions" / "evolution_log.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            import datetime
            entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "file": filename,
                "reason": reason,
                "len_delta": len(content) - (path.stat().st_size if path.exists() else 0)
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return f"Protocol {filename} evolved. Reason: {reason}"

def get_capability(brain_path: Path, config: Dict):
    return StrategyTool(brain_path, config.get("paths", []))
