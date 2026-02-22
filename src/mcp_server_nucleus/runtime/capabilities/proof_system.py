from typing import List, Dict, Any
import os
import time
from pathlib import Path
from .base import Capability

class ProofSystem(Capability):
    def __init__(self):
        # Determine brain path
        brain_path_str = os.environ.get("NUCLEAR_BRAIN_PATH")
        if not brain_path_str:
            brain_path_str = "/Users/nucleus-os/.gemini/antigravity/brain/7c654df4-b83e-43f9-8620-f15868ec39d1"
            
        self.brain_path = Path(brain_path_str)
        self.proofs_dir = self.brain_path / "features" / "proofs"
        self.proofs_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "proof_system"

    @property
    def description(self) -> str:
        return "Generates tangible evidence of work (proofs) to build trust and transparency."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_generate_proof",
                "description": "Generate a markdown proof document for a feature.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {"type": "string", "description": "Feature to generate proof for"},
                        "thinking": {"type": "string", "description": "AI's decision-making process (markdown)"},
                        "deployed_url": {"type": "string", "description": "Production URL"},
                        "files_changed": {"type": "array", "items": {"type": "string"}, "description": "List of files modified"},
                        "risk_level": {"type": "string", "description": "low/medium/high"},
                        "rollback_time": {"type": "string", "description": "Estimated time to rollback"}
                    },
                    "required": ["feature_id"]
                }
            },
            {
                "name": "brain_get_proof",
                "description": "Get the proof document for a feature.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {"type": "string", "description": "Feature ID to get proof for"}
                    },
                    "required": ["feature_id"]
                }
            },
            {
                "name": "brain_list_proofs",
                "description": "List all proof documents.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> Any:
        try:
            if tool_name == "brain_generate_proof":
                return self._generate_proof(args)
            elif tool_name == "brain_get_proof":
                return self._get_proof(args.get("feature_id"))
            elif tool_name == "brain_list_proofs":
                return self._list_proofs()
            return f"Tool {tool_name} not found"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _generate_proof(self, args: Dict) -> Dict:
        feature_id = args.get("feature_id")
        thinking = args.get("thinking", "No thinking provided.")
        deployed_url = args.get("deployed_url", "N/A")
        files_changed = args.get("files_changed", [])
        risk_level = args.get("risk_level", "low")
        rollback_time = args.get("rollback_time", "Unknown")
        
        # Format the proof markdown (Tier 1 Style)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        files_block = "\n".join([f"- {f}" for f in files_changed]) if files_changed else "None"
        
        content = f"""# Proof: {feature_id}

> Generated: {timestamp}

## Thinking
{thinking}

## Deployed URL
{deployed_url}

## Files Changed
{files_block}

## Rollback Plan
- **Risk Level:** {risk_level.upper()}
- **Estimated Time:** {rollback_time}
- **Strategy:** `git revert` or restore from backup.
"""
        
        file_path = self.proofs_dir / f"{feature_id}.md"
        file_path.write_text(content)
        
        return {
            "success": True,
            "message": f"Proof generated for {feature_id}",
            "path": str(file_path)
        }

    def _get_proof(self, feature_id: str) -> str:
        file_path = self.proofs_dir / f"{feature_id}.md"
        if not file_path.exists():
            return f"Proof for {feature_id} not found."
        return file_path.read_text()

    def _list_proofs(self) -> List[str]:
        if not self.proofs_dir.exists():
            return []
        return [p.name for p in self.proofs_dir.glob("*.md")]
