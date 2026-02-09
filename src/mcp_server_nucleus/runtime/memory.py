
import os
import subprocess
from pathlib import Path
from typing import Dict
import logging
import time

from .common import get_brain_path

logger = logging.getLogger("nucleus.memory")

def _search_memory(query: str) -> Dict:
    try:
        brain = get_brain_path()
        memory_dir = brain / "memory"
        ledger_dir = brain / "ledger"
        
        search_paths = [str(memory_dir)]
        if (ledger_dir / "decisions.md").exists():
            search_paths.append(str(ledger_dir / "decisions.md"))
            
        snippets = []
        lowered = query.lower()
        for path_str in search_paths:
            path = Path(path_str)
            if not path.exists(): continue
            files = list(path.glob("**/*.md")) + list(path.glob("**/*.txt"))
            for file_path in files:
                try:
                    for line in file_path.read_text().splitlines():
                        if lowered in line.lower():
                            snippets.append(f"{file_path.name}:{line}")
                except Exception: continue

        return {"query": query, "count": len(snippets), "results": snippets[:20]}
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return {"error": str(e)}

def _write_memory(content: str, category: str = "learnings") -> str:
    try:
        brain = get_brain_path()
        memory_dir = brain / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{category}.md"
        file_path = memory_dir / filename
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n## [{timestamp}] Engram\n{content}"
        
        with open(file_path, "a") as f:
            f.write(entry)
            
        return f"Memory written to {filename}"
    except Exception as e:
        logger.error(f"Write memory failed: {e}")
        return f"Error writing memory: {str(e)}"
