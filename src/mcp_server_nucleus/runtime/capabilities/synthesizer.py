"""
Nucleus Synthesizer
===================
The 'Executive Brain' that synthesizes system status into human-readable reports.

Capabilities:
- brain_synthesize_status_report: Generates a 'State of the Union' roadmap.
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging
import subprocess

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

logger = logging.getLogger(__name__)

def _get_api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY")

def brain_synthesize_status_report(
    project_root: str,
    focus: str = "roadmap"
) -> Dict[str, str]:
    """
    Generates a 'State of the Union' report by analyzing tasks, logs, and vision.
    
    Args:
        project_root: Absolute path to project root
        focus: 'roadmap' (default) or 'technical' or 'marketing'
        
    Returns:
        Dict with status and output report content
    """
    if not HAS_GENAI:
        return {"status": "error", "message": "google-genai library not installed"}
        
    api_key = _get_api_key()
    if not api_key:
        return {"status": "error", "message": "GEMINI_API_KEY not found"}

    root_path = Path(project_root)
    
    # 1. Gather Context
    context = {}
    
    # Task List (What's pending)
    task_path = root_path / ".brain" / "task.md"
    if task_path.exists():
        with open(task_path, 'r') as f:
            context['tasks'] = f.read()[:5000] # Cap usage
            
    # Vision (Where we are going)
    vision_path = root_path / ".brain" / "NUCLEUS_VISION.md"
    if vision_path.exists():
        with open(vision_path, 'r') as f:
            context['vision'] = f.read()

    # System Status (invisible work)
    try:
        cron_output = subprocess.check_output(['crontab', '-l'], stderr=subprocess.STDOUT).decode('utf-8')
        context['cron'] = cron_output
    except Exception:
        context['cron'] = "No crontab accessible."
        
    # Logs (Last 20 lines of key logs)
    log_paths = [
        root_path / ".brain/ledger/cron.log",
        Path("/tmp/nucleus_nightly.log"),
        Path("/tmp/nucleus_orchestrator.log")
    ]
    logs_summary = ""
    for log_p in log_paths:
        if log_p.exists():
            try:
                tail = subprocess.check_output(['tail', '-n', '10', str(log_p)]).decode('utf-8')
                logs_summary += f"\n--- {log_p.name} ---\n{tail}\n"
            except Exception:
                pass
    context['logs'] = logs_summary

    # 2. Construct Prompt
    prompt = f"""
    You are the Nucleus Brain (Executive Function).
    
    TASK:
    Generate a 'State of the Union' report for the Founder (The User).
    
    CONTEXT:
    1. VISION (Where we are going):
    {context.get('vision', 'No vision file found.')}
    
    2. TASKS (What is pending):
    {context.get('tasks', 'No task file found.')}
    
    3. INVISIBLE MACHINERY (What is running in background):
    CRON: {context.get('cron')}
    LOGS: {context.get('logs')}
    
    INSTRUCTIONS:
    - Write a clear, high-level Roadmap Report.
    - Group status into: 
      1. ✅ Completed Capabilities (The Iron Man Suit)
      2. ⚙️ Running Machinery (Invisible Work - cite logs)
      3. 🚧 Active Construction (Next Phase)
    - Clarify the "Mac vs Cloud" status explicitly.
    - End with a concrete recommendation for the NEXT move.
    
    FORMAT:
    Markdown. Use Emoji. Be concise.
    """
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        report = response.text
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Status Generation failed: {e}")
        return {"status": "error", "message": str(e)}
