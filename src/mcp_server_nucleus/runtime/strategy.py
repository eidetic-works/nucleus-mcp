
import os
import logging
from pathlib import Path
from typing import Dict, Optional

# Configure logger
logger = logging.getLogger("nucleus.strategy")

def get_brain_path() -> Path:
    """Get the brain path from environment variable."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
    if not brain_path:
        cwd = Path.cwd()
        if (cwd / ".brain").exists():
            return cwd / ".brain"
        for parent in cwd.parents:
            if (parent / ".brain").exists():
                return parent / ".brain"
        raise ValueError("NUCLEAR_BRAIN_PATH environment variable not set")
    return Path(brain_path)

def _manage_strategy(action: str, content: Optional[str] = None) -> Dict:
    """
    Manage the Strategy Document.
    """
    try:
        brain = get_brain_path()
        strategy_file = brain / "strategy.md"
        
        if action == "read":
            if not strategy_file.exists():
                return {"status": "empty", "content": ""}
            return {"status": "success", "content": strategy_file.read_text()}
            
        elif action == "update":
            if not content:
                return {"error": "Content required for update"}
            strategy_file.write_text(content)
            return {"status": "success", "message": "Strategy updated"}
        
        elif action == "append":
             if not content:
                return {"error": "Content required for append"}
             current = strategy_file.read_text() if strategy_file.exists() else ""
             strategy_file.write_text(current + "\n\n" + content)
             return {"status": "success", "message": "Strategy appended"}
             
        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Strategy op failed: {e}")
        return {"error": str(e)}

def _update_roadmap(action: str, item: str = None) -> Dict:
    """
    Update the Roadmap.
    """
    try:
        brain = get_brain_path()
        roadmap_file = brain / "roadmap.md"
        
        if action == "read":
            if not roadmap_file.exists():
                return {"status": "empty", "content": ""}
            return {"status": "success", "content": roadmap_file.read_text()}
            
        elif action == "add":
            current = roadmap_file.read_text() if roadmap_file.exists() else "# Roadmap\n"
            new_content = current + f"\n- [ ] {item}"
            roadmap_file.write_text(new_content)
            return {"status": "success", "message": f"Added to roadmap: {item}"}
            
        elif action == "complete":
             if not roadmap_file.exists():
                 return {"error": "Roadmap not found"}
             content = roadmap_file.read_text()
             if item not in content:
                 return {"error": f"Item not found: {item}"}
             # Simple string replacement for checkmark
             new_content = content.replace(f"- [ ] {item}", f"- [x] {item}")
             roadmap_file.write_text(new_content)
             return {"status": "success", "message": f"Completed: {item}"}

        else:
             return {"error": f"Unknown action: {action}. Use 'read', 'add', or 'complete'."}
             
    except Exception as e:
        logger.error(f"Roadmap op failed: {e}")
        return {"error": str(e)}
