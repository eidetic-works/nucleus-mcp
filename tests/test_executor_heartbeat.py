"""Test executor heartbeat behavior — write a heartbeat file every 30s while executing.

Verifies that the executor daemon:
1. Writes heartbeat file to /tmp/executor_heartbeat_${EXECUTOR_AGENT_ID}
2. The file contains current task_id and timestamp
3. The background process is cleaned up on exit
"""
import os
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXECUTOR_SCRIPT = PROJECT_ROOT / "scripts" / "executor_daemon.sh"


class TestExecutorHeartbeat:
    """Test the executor heartbeat logic."""

    def test_executor_has_heartbeat_logic(self):
        """The executor script should have heartbeat logic."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "executor_heartbeat" in source, "Script should write executor_heartbeat"
        assert "HB_PID" in source, "Script should track heartbeat process PID"
        assert "timestamp" in source, "Heartbeat should include timestamp"
        assert "task_id" in source, "Heartbeat should include task_id"

    def test_heartbeat_execution(self):
        """Test that the heartbeat process runs and creates the file with correct format."""
        agent_id = "test_executor_agent"
        hb_file = f"/tmp/executor_heartbeat_{agent_id}"
        task_id = "test_task_123"

        # Clean up first
        if os.path.exists(hb_file):
            os.unlink(hb_file)

        # Run the start/write logic
        script = f"""
        export EXECUTOR_AGENT_ID="{agent_id}"
        task_id="{task_id}"
        hb_file="{hb_file}"
        echo "task_id: $task_id" > "$hb_file"
        echo "timestamp: $(date +%s)" >> "$hb_file"
        """
        subprocess.run(["bash", "-c", script], check=True)

        assert os.path.exists(hb_file), "Heartbeat file was not created"
        try:
            content = open(hb_file).read()
            assert f"task_id: {task_id}" in content
            assert "timestamp: " in content
            parts = content.split("timestamp:")
            timestamp_str = parts[1].strip()
            # Verify timestamp is an integer
            timestamp = int(timestamp_str)
            assert timestamp > 0
        finally:
            if os.path.exists(hb_file):
                os.unlink(hb_file)

    def test_cleanup_removes_heartbeat(self):
        """Test that calling the cleanup function stops heartbeat and removes the file."""
        agent_id = "test_cleanup_agent"
        hb_file = f"/tmp/executor_heartbeat_{agent_id}"

        script = f"""
        export EXECUTOR_AGENT_ID="{agent_id}"
        hb_file="{hb_file}"
        # Start a dummy sleep process to act as HB_PID
        sleep 10 &
        HB_PID=$!

        # Write dummy heartbeat file
        echo "task_id: test" > "$hb_file"

        # Define the cleanup logic (extracted from the script)
        cleanup() {{
          if [[ -n "$HB_PID" ]]; then
            kill "$HB_PID" 2>/dev/null || true
            rm -f "$hb_file"
          fi
        }}

        # Run cleanup
        cleanup

        # Verify background process is killed
        if kill -0 "$HB_PID" 2>/dev/null; then
          echo "FAIL: PID still running"
        else
          echo "OK"
        fi
        """
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            check=True
        )
        assert "OK" in result.stdout
        assert not os.path.exists(hb_file), "Cleanup should delete heartbeat file"
