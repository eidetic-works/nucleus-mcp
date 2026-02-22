
import os
import subprocess
from pathlib import Path
from typing import Dict
import logging

# Configure logger
logger = logging.getLogger("nucleus.memory")

def get_brain_path() -> Path:
    """Get the brain path from environment variable."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
    if not brain_path:
        # Fallback for dev environment
        cwd = Path.cwd()
        if (cwd / ".brain").exists():
            return cwd / ".brain"
        for parent in cwd.parents:
            if (parent / ".brain").exists():
                return parent / ".brain"
        raise ValueError("NUCLEAR_BRAIN_PATH environment variable not set")
    return Path(brain_path)

def _search_memory(query: str) -> Dict:
    """
    Search the 'Long-term Memory' (artifacts/memory and ledger/decisions.md) using ripgrep.
    """
    try:
        brain = get_brain_path()
        memory_dir = brain / "memory"
        ledger_dir = brain / "ledger"
        
        # Paths to search
        search_paths = [str(memory_dir)]
        if (ledger_dir / "decisions.md").exists():
            search_paths.append(str(ledger_dir / "decisions.md"))
            
        # Run ripgrep
        # -i: case insensitive
        # -C 2: 2 lines of context
        # --json: output as json
        
        # V1: Simple Text Search
        cmd_text = ["rg", "-i", "-n", "--no-heading", query] + search_paths
        result_text = subprocess.run(cmd_text, capture_output=True, text=True)
        
        snippets = []
        if result_text.stdout:
            snippets = result_text.stdout.strip().splitlines()
            
        return {
            "query": query,
            "count": len(snippets),
            "results": snippets[:20] # Limit to 20 results
        }

    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return {"error": str(e)}

def _read_memory(category: str) -> Dict:
    """
    Read specific memory categories (context, patterns, learnings).
    """
    try:
        brain = get_brain_path()
        memory_dir = brain / "memory"
        
        allowed_files = {
            "context": "context.md",
            "patterns": "patterns.md",
            "learnings": "learnings.md",
            "decisions": "decisions.md" # Actually in ledger, but handled here
        }
        
        if category not in allowed_files:
            return {"error": f"Invalid category. Allowed: {list(allowed_files.keys())}"}
            
        filename = allowed_files[category]
        file_path = memory_dir / filename
        
        if category == "decisions":
            file_path = brain / "ledger" / "decisions.md"
            
        if not file_path.exists():
             return {"error": f"Memory file {filename} not found."}
             
        content = file_path.read_text()
        return {
            "category": category,
            "path": str(file_path),
            "content": content
        }

    except Exception as e:
        logger.error(f"Read memory failed: {e}")
        return {"error": str(e)}
