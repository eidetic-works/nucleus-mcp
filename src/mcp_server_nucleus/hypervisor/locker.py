
import subprocess
import os
import logging
from typing import List, Union

logger = logging.getLogger(__name__)

class Locker:
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
        if not os.path.exists(path):
            logger.error(f"Cannot lock non-existent path: {path}")
            return False
            
        logger.info(f"🔒 Locking: {path}")

        if metadata:
            import time
            if "timestamp" not in metadata:
                metadata["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            
            for k, v in metadata.items():
                key = k if k.startswith("nucleus.lock.") else f"nucleus.lock.{k}"
                self._set_xattr(path, key, v)

        if os.path.isdir(path):
            return self._run_cmd(["chflags", "-R", "uchg", path])
        else:
            return self._run_cmd(["chflags", "uchg", path])

    def unlock(self, path: str) -> bool:
        if not os.path.exists(path):
            logger.error(f"Cannot unlock non-existent path: {path}")
            return False

        logger.info(f"🔓 Unlocking: {path}")
        if os.path.isdir(path):
            return self._run_cmd(["chflags", "-R", "nouchg", path])
        else:
            return self._run_cmd(["chflags", "nouchg", path])

    def is_locked(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        
        try:
            st = os.stat(path)
            return (st.st_flags & 0x2) != 0
        except Exception:
            return False

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
