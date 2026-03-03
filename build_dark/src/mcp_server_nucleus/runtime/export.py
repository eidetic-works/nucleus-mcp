
"""
DataExporter: The Anti-Sherlock "Eject Button".
Ensures Sovereign Data Portability.

Strategic Role:
- Exports entire Brain state (Ledger, Memory, Config).
- Formats: JSON (Standard), SQLite (Future).
- Guarantees: "You can always leave with your data."
"""

import json
import time
from pathlib import Path
from zipfile import ZipFile
from typing import Dict


class DataExporter:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.export_dir = brain_path / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_full_state(self) -> Dict[str, str]:
        """
        Create a full snapshot of the Sovereign Brain.
        Returns path to the export artifact.
        """
        timestamp = int(time.time())
        export_name = f"sovereign_dump_{timestamp}"
        zip_path = self.export_dir / f"{export_name}.zip"
        
        # We need a shared 'top level' read lock on critical subsystems if possible
        # Or just best-effort copy. For "Eject", consistency is slightly less critical 
        # than just "getting the files".
        
        # Files to include
        include_dirs = ["ledger", "memory", "swarms", "agents", "checkpoints"]
        
        with ZipFile(zip_path, 'w') as zipf:
            # Metadata
            meta = {
                "version": "1.0",
                "timestamp": timestamp,
                "system": "Nucleus Daemon Phase 59"
            }
            zipf.writestr("metadata.json", json.dumps(meta, indent=2))
            
            # Recursive add
            for d in include_dirs:
                src_dir = self.brain_path / d
                if src_dir.exists():
                    for file in src_dir.rglob("*"):
                        if file.is_file():
                            # Rel path inside zip
                            rel_path = file.relative_to(self.brain_path)
                            zipf.write(file, arcname=str(rel_path))
                            
        return {
            "status": "success",
            "path": str(zip_path),
            "size_bytes": zip_path.stat().st_size
        }
