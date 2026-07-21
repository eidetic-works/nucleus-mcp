
import os
import subprocess
from pathlib import Path
from typing import Dict
import logging
import time

# Configure logger
logger = logging.getLogger("nucleus.memory")

# --- Move 2 batch 5: flag-gated SoR read-model repoint ---------------------
# Self-contained env check (mirrors runtime/memory_pipeline.py::_sor_flag_on) so
# the flag-OFF (and explicit ``mode="grep"``) path stays a byte-for-byte ripgrep
# scan and nothing from ``mcp_server_nucleus.memory`` is imported until flag-ON.
_SOR_FLAG = "NUCLEUS_MEMORY_SOR"
_SOR_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _sor_flag_on() -> bool:
    """True iff ``NUCLEUS_MEMORY_SOR`` is set truthy (default False)."""
    return os.environ.get(_SOR_FLAG, "").strip().lower() in _SOR_TRUTHY


def _merge_sor_grep(query: str, brain: Path, snippets: list) -> Dict:
    """Union the unified SoR (``MemoryFacade.recall``, hybrid) onto the ripgrep
    snippets, dedup by line. Fault-isolated → returns the grep-only result on any
    SoR read failure (the SoR read is purely additive, never worse than grep)."""
    try:
        from mcp_server_nucleus.memory.facade import MemoryFacade

        facade = MemoryFacade(brain_path=brain, enabled=True)
        hits = facade.recall(query=query or "", limit=40, mode="hybrid")
    except Exception as exc:  # noqa: BLE001 — additive read must not break search
        logger.warning("SoR grep-union read failed; returning grep-only result: %s", exc)
        return {"query": query, "count": len(snippets), "results": snippets[:20]}
    merged = list(snippets)
    seen = set(snippets)
    for h in hits:
        line = f"sor:{h.get('kind') or 'note'}:{h.get('text')}"
        if line in seen:
            continue
        seen.add(line)
        merged.append(line)
    return {"query": query, "count": len(merged), "results": merged[:20]}

def get_brain_path() -> Path:
    """Get the brain path from environment variable."""
    brain_path = os.environ.get("NUCLEUS_BRAIN_PATH")
    if not brain_path:
        # Fallback for dev environment
        cwd = Path.cwd()
        if (cwd / ".brain").exists():
            return cwd / ".brain"
        for parent in cwd.parents:
            if (parent / ".brain").exists():
                return parent / ".brain"
        raise ValueError("NUCLEUS_BRAIN_PATH environment variable not set")
    return Path(brain_path)

def _search_memory(query: str, mode: str = "auto") -> Dict:
    """Search the 'Long-term Memory' (artifacts/memory and ledger/decisions.md).

    Move 2 batch 5: flag-OFF (default) and the explicit ``mode="grep"`` fallback
    are byte-for-byte the legacy ripgrep scan (RETAINED — never deleted). Flag-ON
    with the default/``"hybrid"`` mode additionally unions the unified SoR
    (``MemoryFacade.recall``, hybrid) on top — additive and fault-isolated, so
    ``mode="grep"`` remains a reachable escape hatch even under the flag.
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
        # Use -- to prevent query from being interpreted as ripgrep flags
        cmd_text = ["rg", "-i", "-n", "--no-heading", "--", query] + search_paths
        try:
            result_text = subprocess.run(cmd_text, capture_output=True, text=True)
            snippets = []
            if result_text.stdout:
                snippets = result_text.stdout.strip().splitlines()
        except FileNotFoundError:
            # Fallback when ripgrep is not available
            snippets = []
            lowered = query.lower()
            for path_str in search_paths:
                path = Path(path_str)
                if path.is_file():
                    files = [path]
                else:
                    files = list(path.glob("*.md")) + list(path.glob("*.txt"))
                for file_path in files:
                    try:
                        for line in file_path.read_text().splitlines():
                            if lowered in line.lower():
                                snippets.append(f"{file_path}:{line}")
                    except Exception:
                        continue

        # Flag-OFF (default) or explicit grep mode: byte-for-byte the pre-batch-5
        # ripgrep result — the RETAINED explicit grep fallback (mode="grep").
        if mode == "grep" or not _sor_flag_on():
            return {
                "query": query,
                "count": len(snippets),
                "results": snippets[:20]  # Limit to 20 results
            }

        # Flag-ON hybrid: union the unified SoR recall on top of the grep result.
        return _merge_sor_grep(query, brain, snippets)

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

def _write_memory(content: str, category: str = "learnings") -> str:
    """
    Write a memory engram to a specific category file in Markdown format.
    """
    try:
        brain = get_brain_path()
        memory_dir = brain / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        allowed_files = {
            "context": "context.md",
            "patterns": "patterns.md",
            "learnings": "learnings.md",
            "decisions": "decisions.md" 
        }
        
        # Default to learnings if unknown category, or map "memory" to learnings
        if category == "memory":
            category = "learnings"
            
        target_file = allowed_files.get(category, "learnings.md")
        
        # Special case for decisions (in ledger)
        if category == "decisions":
            file_path = brain / "ledger" / "decisions.md"
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            file_path = memory_dir / target_file
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n## [{timestamp}] Engram\n{content}"
        
        mode = "a" if file_path.exists() else "w"
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(entry)
            
        return f"Memory written to {target_file}"

    except Exception as e:
        logger.error(f"Write memory failed: {e}")
        return f"Error writing memory: {str(e)}"
