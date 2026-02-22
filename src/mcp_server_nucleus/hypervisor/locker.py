
import subprocess
import os
import logging
from typing import List

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
        Locks a file or directory using 'chflags uchg' (macOS) or legacy attributes (Windows).
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
                self._set_xattr(path, key, v)

        # OS Specific Locking
        if os.name == 'nt':
            # Windows: Set read-only attribute
            import shutil
            if shutil.which("attrib"):
                return self._run_cmd(["attrib", "+r", path])
            logger.warning("Windows 'attrib' command not found. Skipping lock.")
            return True # Graceful skip
            
        # Check if chflags exists (macOS/BSD)
        import shutil
        if not shutil.which("chflags"):
            logger.warning("Locker: 'chflags' not found. Skipping immutable lock.")
            return True

        if os.path.isdir(path):
            return self._run_cmd(["chflags", "-R", "uchg", path])
        else:
            return self._run_cmd(["chflags", "uchg", path])

    def unlock(self, path: str) -> bool:
        """
        Unlocks a file or directory.
        """
        if not os.path.exists(path):
            logger.error(f"Cannot unlock non-existent path: {path}")
            return False

        logger.info(f"🔓 Unlocking: {path}")
        
        if os.name == 'nt':
            import shutil
            if shutil.which("attrib"):
                return self._run_cmd(["attrib", "-r", path])
            return True

        import shutil
        if not shutil.which("chflags"):
            return True

        if os.path.isdir(path):
            return self._run_cmd(["chflags", "-R", "nouchg", path])
        else:
            return self._run_cmd(["chflags", "nouchg", path])

    def is_locked(self, path: str) -> bool:
        """
        Checks if the file is locked / read-only.
        """
        if not os.path.exists(path):
            return False
        
        # Windows Check
        if os.name == 'nt':
            import stat
            return not (os.stat(path).st_mode & stat.S_IWRITE)

        # macOS/BSD Check
        try:
            st = os.stat(path)
            if hasattr(st, 'st_flags'):
                return (st.st_flags & 0x2) != 0
            return False
        except Exception:
            return False

    # --- METADATA (Phase 28) ---
    def _set_xattr(self, path: str, key: str, value: str):
        if os.name == 'nt':
            return # Windows does not support xattr natively

        import shutil
        if not shutil.which("xattr"):
            return

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
