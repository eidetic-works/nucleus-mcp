import subprocess
import os
import signal
import sys
import time
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

class SovereignProcess:
    """Wrapper for subprocess.Popen with group isolation and hard preemption."""

    def __init__(
        self,
        args: Union[str, List[str]],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Union[str, Path]] = None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **kwargs
    ):
        self.args = args
        self.env = env
        self.cwd = cwd
        
        # Ensure process group isolation
        # start_new_session=True creates a new process group and makes the child the leader
        self._proc = subprocess.Popen(
            args,
            env=env,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL, # Prevent SIGTTIN background stops
            start_new_session=True,  # Critical for hard preemption (macOS/Unix)
            **kwargs
        )
        self.pid = self._proc.pid

    def poll(self) -> Optional[int]:
        return self._proc.poll()

    def wait(self, timeout: Optional[float] = None) -> int:
        return self._proc.wait(timeout=timeout)

    @property
    def stdout(self):
        return self._proc.stdout

    @property
    def stderr(self):
        return self._proc.stderr

    @property
    def returncode(self) -> Optional[int]:
        return self._proc.returncode

    def communicate(self, timeout: Optional[float] = None):
        """Communicate with the process, with hard preemption on timeout."""
        try:
            return self._proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.kill_group()
            raise

    def kill_group(self):
        """Send SIGKILL to the entire process group, ensuring no orphans remain."""
        try:
            # Send SIGKILL to the process group (using negative PID)
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass # Already gone
        except Exception as e:
            print(f"[SEE] Error killing process group {self.pid}: {e}", file=sys.stderr)
            # Fallback to single kill if pgkill fails
            try:
                self._proc.kill()
            except:
                pass

    def terminate_group(self):
        """Gracious termination attempted first, then hard kill."""
        try:
            os.killpg(self.pid, signal.SIGTERM)
            # Short grace period
            time.sleep(0.5)
            if self.poll() is None:
                self.kill_group()
        except ProcessLookupError:
            pass
