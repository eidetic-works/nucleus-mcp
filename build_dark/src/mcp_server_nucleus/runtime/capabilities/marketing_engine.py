"""
Nucleus Marketing Engine
========================
The Content Brain for GentleQuest.
Auto-generates strategy and content from raw logs.

Capabilities:
- brain_synthesize_strategy: Reads marketing_log.md -> Updates strategy.md
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging
import time

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

logger = logging.getLogger(__name__)

# Constants
MARKETING_LOG_PATH = "docs/marketing/marketing_log.md"
STRATEGY_PATH = "docs/marketing/strategy.md"

def _get_api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY")

def brain_synthesize_strategy(
    project_root: str,
    focus_topic: Optional[str] = None
) -> Dict[str, str]:
    """
    Analyze marketing logs and update the strategy document.
    
    Args:
        project_root: Absolute path to project root
        focus_topic: Optional specific topic to focus on
        
    Returns:
        Dict with status and path to updated strategy
    """
    if not HAS_GENAI:
        return {"status": "error", "message": "google-genai library not installed"}
        
    api_key = _get_api_key()
    if not api_key:
        return {"status": "error", "message": "GEMINI_API_KEY not found in environment"}
        
    root_path = Path(project_root)
    log_path = root_path / MARKETING_LOG_PATH
    strategy_path = root_path / STRATEGY_PATH
    
    if not log_path.exists():
        return {"status": "error", "message": f"Log file not found at {log_path}"}
        
    # Read the log
    with open(log_path, 'r') as f:
        log_content = f.read()
        
    # Read existing strategy if valid
    existing_strategy = ""
    if strategy_path.exists():
        with open(strategy_path, 'r') as f:
            existing_strategy = f.read()

    # Construct Prompt
    prompt = f"""
    You are the Chief Strategy Officer for GentleQuest (an AI mental health app for developers).
    
    TASK:
    Analyze the daily marketing log and update the High-Level Strategy.
    
    INPUT DATA (Marketing Log):
    {log_content[-2000:]}  # Last 2000 chars for context
    
    EXISTING STRATEGY:
    {existing_strategy}
    
    INSTRUCTIONS:
    1. Identify 'Rising Trends' and 'High Engagement' items from the log.
    2. Synthesize them into concrete strategic 'Angles' (e.g., "Pivot to Anti-Streak messaging").
    3. Output the FULL content for the new 'strategy.md' file.
    4. Keep it concise, actionable, and formatted in Markdown.
    5. Include a 'Recent Insights' section based on the logs.
    
    OUTPUT FORMAT:
    (Markdown only)
    """
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        new_strategy = response.text
        
        # Write to file
        strategy_path.parent.mkdir(parents=True, exist_ok=True)
        with open(strategy_path, 'w') as f:
            f.write(new_strategy)
            
    except Exception as e:
        logger.error(f"GenAI Strategy Synthesis failed: {e}")
        return {"status": "error", "message": str(e)}

def brain_optimize_workflow(
    project_root: str
) -> Dict[str, str]:
    """
    Scan marketing logs for 'META-FEEDBACK' and suggest workflow improvements.
    
    Args:
        project_root: Absolute path to project root
        
    Returns:
        Dict with status and suggestions
    """
    if not HAS_GENAI:
        return {"status": "error", "message": "google-genai library not installed"}
        
    api_key = _get_api_key()
    if not api_key:
        return {"status": "error", "message": "GEMINI_API_KEY not found"}
        
    root_path = Path(project_root)
    log_path = root_path / MARKETING_LOG_PATH
    cheatsheet_path = root_path / ".agent/workflows/marketing_autopilot_cheatsheet.md"
    
    if not log_path.exists():
        return {"status": "error", "message": "Log file not found"}

    with open(log_path, 'r') as f:
        log_content = f.read()
        
    # Check if there is any meta-feedback
    if "META-FEEDBACK" not in log_content:
        return {"status": "skipped", "message": "No META-FEEDBACK found in logs."}
        
    # Read existing cheatsheet for context
    current_cheatsheet = ""
    if cheatsheet_path.exists():
        with open(cheatsheet_path, 'r') as f:
            current_cheatsheet = f.read()

    prompt = f"""
    You are the 'Process Optimizer' for the Marketing Autopilot.
    
    INPUT DATA:
    1. Marketing Log (Looking for 'META-FEEDBACK' tags):
    {log_content[-5000:]}
    
    2. Current Cheatsheet (The Rules):
    {current_cheatsheet}
    
    TASK:
    1. Extract all 'META-FEEDBACK' suggestions from the log.
    2. Analyze if the Cheatsheet needs updating.
    3. Generate a list of actionable tasks for 'task.md'.
    
    OUTPUT FORMAT:
    (Markdown Checklist Items Only)
    - [ ] Update Cheatsheet: [Specific Prompt Change]
    - [ ] Fix Dashboard UI: [Specific Bug]
    """
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        new_tasks = response.text
        
        # Determine where to write tasks
        # Plan A: Try to find the specific conversation task.md (This is hard from here without context)
        # Plan B: Write to the Central Ledger (V2) or a dedicated improvements file
        
        # We'll use a dedicated file for Workflow Improvements that the Human can triage
        # This avoids messing up specific task.lhs if IDs change
        improvement_path = root_path / ".brain/ledger/WORKFLOW_IMPROVEMENTS.md"
        improvement_path.parent.mkdir(parents=True, exist_ok=True)
        
        # If the file exists, append. If not, create.
        mode = 'a' if improvement_path.exists() else 'w'
        with open(improvement_path, mode) as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n\n## 🧬 Workflow Upgrades (Auto-Generated {timestamp})\n{new_tasks}")
            
        return {
            "status": "success",
            "message": "Optimization tasks generated in WORKFLOW_IMPROVEMENTS.md",
            "path": str(improvement_path)
        }
        
    except Exception as e:
        logger.error(f"Workflow Optimization failed: {e}")
        return {"status": "error", "message": str(e)}

