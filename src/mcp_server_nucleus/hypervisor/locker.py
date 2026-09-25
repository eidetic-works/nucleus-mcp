
import subprocess
import os
import logging
from typing import List

logger = logging.getLogger(__name__)


# ── NEVER-LOCK POLICY ────────────────────────────────────────────────────────
# One list, one rule, instead of a growing pile of special cases.
#
# Every incident today was the same: the hypervisor locked something a LIVE
# process needed to write, and the resulting error named the wrong thing, so
# the real cause stayed invisible:
#
#   .git/**            git could not create index.lock -> commit and push both
#                      dead. The error names a lock FILE, never the immutable
#                      FLAG. Unlocked 3,576+ paths FOUR separate times today.
#   .brain/plans/**    `nucleus build` crashed writing its own state.tmp. The
#                      operator sees "plan review timed out after 1200s" — but
#                      the review had FINISHED; only the write failed.
#   .brain/relay/**    vendor capture silently failed, so dispatches ran with
#   .brain/engrams/**  NO audit record — invisible to every ledger, which is
#                      the one thing nucleus_delegate exists to prevent.
#   *.lock / *.tmp     lock/temp files are by definition mid-transaction.
#
# The principle: LOCK FINISHED ARTIFACTS, NEVER LIVE WORKING STATE. A lock on
# something a process is actively writing is not protection, it is a crash —
# and a crash reported as something else entirely.
#
# Silent-write-failure is the aggravating factor. ruff --fix, py_compile,
# open() and pip each "succeeded" against locked paths today while changing
# nothing. A tool that does not check its own write cannot tell you.
#
# Extend with NUCLEUS_NEVER_LOCK (colon-separated path segments). This list is
# a floor, not a ceiling: adding to it is cheap, and a wrongly-locked live path
# has cost hours today.
_NEVER_LOCK_SEGMENTS = {
    ".git",             # every recoverable version of everything else
    "plans",            # nucleus build / plan_review_loop scratch
    "relay",            # inter-agent envelopes, written continuously
    "engrams",          # memory appends
    "ledger",           # change ledger appends
    "sessions",         # live session state
    "telemetry",        # relay_metrics.jsonl: appended on EVERY dispatch
    "locks",
    "tmp",
    ".venv",
    "__pycache__",      # py_compile writes here; blocking it fakes syntax errors
    "node_modules",
}
_NEVER_LOCK_SUFFIXES = (".lock", ".tmp", ".pid", ".sock")


def _never_lock_reason(path: str):
    """Return a human reason if `path` must never be locked, else None."""
    ap = os.path.abspath(path)
    parts = ap.split(os.sep)

    if ap.endswith(_NEVER_LOCK_SUFFIXES):
        return "a transaction/temp file"

    extra = {s for s in os.environ.get("NUCLEUS_NEVER_LOCK", "").split(":") if s}
    for seg in _NEVER_LOCK_SEGMENTS | extra:
        if seg in parts:
            # ".brain/plans" and ".git" are meaningful; a source file that merely
            # happens to sit in a dir called "tmp" is caught too, and that is the
            # safe direction to err.
            return f"live working state (matched {seg!r})"
    return None


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

        # Policy lives in _never_lock_reason() above — one list, one rule.
        refusal = _never_lock_reason(path)
        if refusal:
            logger.warning(f"⛔ REFUSED to lock {refusal}: {path}")
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
            logger.warning("Windows 'attrib' command not found. Lock NOT applied.")
            return False

        import sys
        if sys.platform == 'linux':
            import shutil
            if not shutil.which("chattr"):
                logger.warning("Locker: 'chattr' not found on Linux. Lock NOT applied.")
                return False
            # Linux requires sudo for chattr immutable flags. 
            # Non-interactive sudo must be allowed for the agent user or it will prompt/fail.
            if os.path.isdir(path):
                return self._run_cmd(["sudo", "chattr", "-R", "+i", path])
            else:
                return self._run_cmd(["sudo", "chattr", "+i", path])

        # Check if chflags exists (macOS/BSD)
        import shutil
        if not shutil.which("chflags"):
            logger.warning("Locker: 'chflags' not found. Lock NOT applied.")
            return False

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
            return False

        import sys
        if sys.platform == 'linux':
            import shutil
            if not shutil.which("chattr"):
                return False
            if os.path.isdir(path):
                return self._run_cmd(["sudo", "chattr", "-R", "-i", path])
            else:
                return self._run_cmd(["sudo", "chattr", "-i", path])

        import shutil
        if not shutil.which("chflags"):
            return False

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

        import sys
        if sys.platform == 'linux':
            try:
                import subprocess
                result = subprocess.run(
                    ["lsattr", path],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if output and len(output) > 5:
                        # e.g., "----i---------e---- file.txt" -> check if 'i' is in the attributes part
                        attrs = output.split()[0]
                        return 'i' in attrs
            except Exception:
                logger.debug("Swallowed exception in is_locked", exc_info=True)
                pass
            return False

        # macOS/BSD Check
        try:
            st = os.stat(path)
            if hasattr(st, 'st_flags'):
                return (st.st_flags & 0x2) != 0
            return False
        except Exception:
            logger.debug("Swallowed exception in is_locked", exc_info=True)
            return False

    # --- METADATA (Layer 4) ---
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

    def unlock_then_rm(self, path: str) -> dict:
        """Unlock and remove a file or directory tree, freeing bytes.

        Designed for the backup-dir rotation scenario: a locked backup dir
        needs to be unlocked before shutil.rmtree can remove it on macOS.

        Returns a dict with keys:
          success (bool), bytes_freed (int), error (str | None)
        """
        if not os.path.exists(path):
            return {"success": False, "bytes_freed": 0, "error": "path not found"}

        # Compute size before removal
        import shutil
        bytes_freed = 0
        try:
            if os.path.isfile(path):
                bytes_freed = os.path.getsize(path)
            else:
                for dirpath, _dirs, files in os.walk(path):
                    for f in files:
                        try:
                            bytes_freed += os.path.getsize(os.path.join(dirpath, f))
                        except OSError:
                            pass
        except OSError:
            pass

        # Unlock first (idempotent — noop if not locked)
        self.unlock(path)

        # Remove
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            return {"success": True, "bytes_freed": bytes_freed, "error": None}
        except Exception as e:
            return {"success": False, "bytes_freed": 0, "error": str(e)}

    def get_metadata(self, path: str) -> dict:
        """Retrieves lock metadata from xattrs (macOS/Linux)."""
        if not os.path.exists(path):
            return {}
        
        if os.name == 'nt':
            return {} # Windows does not support xattr natively

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
            logger.debug("Swallowed exception in get_metadata", exc_info=True)
            return {}
