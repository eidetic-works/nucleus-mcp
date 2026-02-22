from typing import List, Optional
from .common import get_brain_path

def _read_artifact(path: str) -> str:
    """Core logic for reading an artifact."""
    try:
        brain = get_brain_path()
        target = brain / "artifacts" / path
        
        if not str(target.resolve()).startswith(str((brain / "artifacts").resolve())):
             return "Error: Access denied (path traversal)"

        if not target.exists():
            return f"Error: File not found: {path}"
            
        return target.read_text()
    except Exception as e:
        return f"Error reading artifact: {str(e)}"

def _write_artifact(path: str, content: str) -> str:
    """Core logic for writing an artifact."""
    try:
        brain = get_brain_path()
        target = brain / "artifacts" / path
        
        if not str(target.resolve()).startswith(str((brain / "artifacts").resolve())):
             return "Error: Access denied (path traversal)"
             
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing artifact: {str(e)}"

def _list_artifacts(folder: Optional[str] = None) -> List[str]:
    """Core logic for listing artifacts."""
    try:
        brain = get_brain_path()
        root = brain / "artifacts"
        if folder:
            root = root / folder
            
        if not root.exists():
            return []
            
        files = []
        for p in root.rglob("*"):
            if p.is_file():
                try:
                    files.append(str(p.relative_to(brain / "artifacts")))
                except ValueError:
                    pass # Should not happen if root is correct
        return files[:50]
    except Exception:
        return []
