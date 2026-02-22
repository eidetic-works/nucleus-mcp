
import subprocess
import os
import logging
from typing import List, Union

logger = logging.getLogger(__name__)

class Locker:
    """
    The Nucleus Hypervisor Locking Primitive (Layer 4).
    Uses macOS 'chflags' (immutable flags) to enforce file-system level write protection.
    This prevents even root/sudo users (and other agents) from modifying locked files
    until the lock is explicitly released.
    """

    def __init__(self):
        pass

    def _run_cmd(self, cmd: List[str]) -> bool:
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Locker Command Failed: {e.stderr}")
            return False

    def lock(self, path: str, metadata: dict = None) -> bool:
        """
        Locks a file or directory using 'chflags uchg'.
        If path is a directory, it locks it recursively? 
        Current implementation: Single file/folder lock (non-recursive by default for safety).
        To do recursive: chflags -R uchg
        """
        if not os.path.exists(path):
            logger.error(f"Cannot lock non-existent path: {path}")
            return False
            
        logger.info(f"🔒 Locking: {path}")

        # Apply metadata BEFORE making immutable
        if metadata:
            import time
            if "timestamp" not in metadata:
                metadata["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            
            for k, v in metadata.items():
                key = k if k.startswith("nucleus.lock.") else f"nucleus.lock.{k}"
                # If directory, apply only to the directory itself for now (recursive xattr is tricky)
                self._set_xattr(path, key, v)

        # Using -R (recursive) to lock entire directories if needed
        if os.path.isdir(path):
            return self._run_cmd(["chflags", "-R", "uchg", path])
        else:
            return self._run_cmd(["chflags", "uchg", path])

    def unlock(self, path: str) -> bool:
        """
        Unlocks a file or directory using 'chflags nouchg'.
        """
        if not os.path.exists(path):
            logger.error(f"Cannot unlock non-existent path: {path}")
            return False

        logger.info(f"🔓 Unlocking: {path}")
        if os.path.isdir(path):
            return self._run_cmd(["chflags", "-R", "nouchg", path])
        else:
            return self._run_cmd(["chflags", "nouchg", path])

    def is_locked(self, path: str) -> bool:
        """
        Checks if the file has the 'uchg' flag set.
        """
        if not os.path.exists(path):
            return False
        
        # 'ls -lz' shows flags on macOS, or 'ls -MdO'
        # simpler: stat
        try:
            st = os.stat(path)
            # 0x2 is UF_IMMUTABLE (uchg)
            return (st.st_flags & 0x2) != 0
        except Exception:
            return False

    # --- METADATA (Phase 28) ---
    def _set_xattr(self, path: str, key: str, value: str):
        try:
            subprocess.run(
                ["xattr", "-w", key, str(value), path],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to set xattr {key}: {e}")

    def get_metadata(self, path: str) -> dict:
        """Retrieves lock metadata from xattrs."""
        if not os.path.exists(path):
            return {}
        
        try:
            result = subprocess.run(
                ["xattr", path],
                check=True,
                capture_output=True,
                text=True
            )
            keys = result.stdout.strip().split("\n")
            data = {}
            for key in keys:
                if key.startswith("nucleus.lock."):
                    val = subprocess.run(
                        ["xattr", "-p", key, path],
                        check=True,
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                    clean_key = key.replace("nucleus.lock.", "")
                    data[clean_key] = val
            return data
        except Exception:
            return {}
