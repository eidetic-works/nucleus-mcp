"""
Nucleus Sovereign Backup Primitive
==================================
Portable, SSD-aware backup engine for the Nucleus Substrate.
Supports: macOS, Linux, Windows.
"""

import os
import shutil
import platform
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class SovereignBackup:
    def __init__(self, brain_path: Path, root_path: Path):
        self.brain_path = brain_path
        self.root_path = root_path
        self.os_type = platform.system()

    def detect_drive(self, drive_path: str) -> Optional[Path]:
        """Detect if the specified backup drive is mounted."""
        p = Path(drive_path)
        if p.exists() and p.is_dir():
            return p
        
        # macOS/Linux standard external mount check
        if self.os_type != "Windows":
            volumes = Path("/Volumes") if self.os_type == "Darwin" else Path("/media")
            if volumes.exists():
                for mount in volumes.iterdir():
                    if mount.name.lower() in drive_path.lower():
                        return mount
        return None

    def create_backup(self, 
                      target_drive: str, 
                      retention: int = 1, 
                      use_symlink: bool = True) -> Dict:
        """
        Perform a backup to an external drive with optional symlinking.
        """
        mount = self.detect_drive(target_drive)
        backup_name = f".brain-backup-nightly-{datetime.now().strftime('%Y%m%d')}"
        local_path = self.root_path / backup_name
        
        if mount:
            # --- EXTERNAL BACKUP PATH ---
            external_dir = mount / "nucleus_backups" / self.root_path.name
            external_dir.mkdir(parents=True, exist_ok=True)
            external_target = external_dir / backup_name
            
            if not external_target.exists():
                shutil.copytree(self.brain_path, external_target)
                
            # Create Symlink
            link_status = "skipped"
            if use_symlink:
                try:
                    if local_path.exists() or local_path.is_symlink():
                        if local_path.is_dir() and not local_path.is_symlink():
                            shutil.rmtree(local_path)
                        else:
                            local_path.unlink()
                    
                    local_path.symlink_to(external_target)
                    link_status = "created"
                except Exception as e:
                    link_status = f"failed: {str(e)}"
            
            self.prune(external_dir, retention)
            return {
                "success": True, 
                "location": "external", 
                "path": str(external_target),
                "symlink": link_status
            }
        else:
            # --- LOCAL FALLBACK (Strict Limit) ---
            existing = sorted(self.root_path.glob(".brain-backup-nightly-*"))
            if len(existing) == 0:
                shutil.copytree(self.brain_path, local_path)
                return {"success": True, "location": "local", "path": str(local_path)}
            
            return {
                "success": False, 
                "error": "SSD_NOT_FOUND", 
                "message": "SSD not connected and local backup already exists (Limit: 1)."
            }

    def prune(self, directory: Path, keep: int):
        """Remove old backups from the specified directory."""
        backups = sorted(directory.glob(".brain-backup-nightly-*"))
        if len(backups) > keep:
            for old in backups[:-keep]:
                try:
                    if old.is_symlink():
                        old.unlink()
                    else:
                        shutil.rmtree(old)
                except: pass

def run_backup_primitive(brain_path: Path, 
                         root_path: Path, 
                         drive: str, 
                         retention: int = 1) -> Dict:
    """Entry point for the backup primitive."""
    engine = SovereignBackup(brain_path, root_path)
    return engine.create_backup(drive, retention=retention)
