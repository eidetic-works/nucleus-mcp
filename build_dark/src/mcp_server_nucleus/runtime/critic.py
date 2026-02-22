
import os
import json
import time
from pathlib import Path
from typing import Dict
import logging

# Configure logger
logger = logging.getLogger("nucleus.critic")

try:
    from mcp_server_nucleus.runtime.llm_client import DualEngineLLM
except ImportError:
    # Fallback for when running in simpler contexts
    DualEngineLLM = None

def get_brain_path() -> Path:
    """Get the brain path from environment variable."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
    if not brain_path:
        # Fallback for dev/test if env not set, check common locations
        cwd = Path.cwd()
        if (cwd / ".brain").exists():
            return cwd / ".brain"
        # Try finding in parent directories
        for parent in cwd.parents:
            if (parent / ".brain").exists():
                return parent / ".brain"
        raise ValueError("NUCLEAR_BRAIN_PATH environment variable not set and .brain not found")
    
    path = Path(brain_path)
    if not path.exists():
         raise ValueError(f"Brain path does not exist: {brain_path}")
    return path

def _critique_code(file_path: str) -> Dict:
    """
    Critique a specific file using the Critic Agent persona.
    """
    try:
        brain = get_brain_path()
        
        # 1. Resolve Target File
        # Handle absolute or relative paths
        if file_path.startswith("/"):
            target_path = Path(file_path)
        else:
            # Assume relative to project root (parent of .brain)
            target_path = brain.parent / file_path

        if not target_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        code_content = target_path.read_text()

        # 2. Read System Prompt
        critic_prompt_path = brain / "agents" / "critic.md"
        if not critic_prompt_path.exists():
            return {"success": False, "error": "Critic persona not found in .brain/agents/critic.md"}
        
        system_prompt = critic_prompt_path.read_text()

        # 3. Initialize LLM
        if not DualEngineLLM:
             return {"success": False, "error": "LLM Client not available (ImportError)"}

        try:
            llm = DualEngineLLM(
                model_name="gemini-2.0-flash-exp",
                system_instruction=system_prompt
            )
        except Exception as e:
            return {"success": False, "error": f"LLM Init failed: {e}"}

        # 4. Construct Prompt
        user_prompt = f"""
ACTION: Review the following code file.

TARGET: {file_path}

CONTENT:
```
{code_content}
```

INSTRUCTIONS:
1. Analyze for bugs, security flaws, style violations, and adherence to best practices.
2. Check against the Prime Directives.
3. Output your critique in valid JSON format ONLY. 
   Do not include markdown formatting (like ```json), just the raw JSON string.
   Use the schema defined in 'Completion Events' (e.g., event_type="review_approved" or "review_blocked").
   
   Example Success:
   {{
     "event_type": "review_approved",
     "severity": "ROUTINE",
     "payload": {{ "target": "...", "notes": "LGTM" }}
   }}
   
   Example Failure:
   {{
     "event_type": "review_blocked", 
     "severity": "HIGH",
     "payload": {{ "issues": [...] }}
   }}
"""

        # 5. Call LLM
        logger.info(f"Invoking Critic on {file_path}")
        response = llm.generate_content(user_prompt)
        
        if not response or not hasattr(response, 'text'):
            return {"success": False, "error": "LLM returned empty response"}

        raw_text = response.text
        
        # Naive JSON extraction
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        
        if start != -1 and end != -1:
            json_str = raw_text[start:end]
            try:
                critique_data = json.loads(json_str)
            except json.JSONDecodeError:
                 return {"success": False, "error": "Invalid JSON from Critic", "raw": raw_text}
        else:
            return {"success": False, "error": "No JSON found in Critic response", "raw": raw_text}
            
        # 6. Save Artifact
        timestamp = int(time.time())
        filename = f"code_review_{target_path.name}_{timestamp}.json"
        review_path = brain / "artifacts" / "reviews" / filename
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(json.dumps(critique_data, indent=2))
        
        # 7. Extract status for easy consumption
        status = "APPROVED" if critique_data.get("event_type") == "review_approved" else "BLOCKED"
        
        return {
            "success": True, 
            "status": status,
            "review_path": str(review_path),
            "critique": critique_data
        }

    except Exception as e:
        logger.error(f"Critique failed: {e}")
        return {"success": False, "error": f"Critique generation failed: {str(e)}"}
