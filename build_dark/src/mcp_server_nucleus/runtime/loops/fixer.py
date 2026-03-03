
import subprocess
import time
import json
from pathlib import Path
from typing import Callable, Tuple, Dict, Any

class FixerLoop:
    """
    Manages the 'Verify -> Diagnose -> Fix' cycle for autonomous code repair.
    Phase 4: Self-Healing v2
    """
    
    def __init__(
        self, 
        target_file: str, 
        verification_command: str, 
        fixer_func: Callable[[str, str], str],
        max_retries: int = 3
    ):
        self.target_file = Path(target_file)
        self.verification_command = verification_command
        self.fixer_func = fixer_func
        self.max_retries = max_retries
        self.logs = []

    def _log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        print(entry)
        self.logs.append(entry)

    def _run_verification(self) -> Tuple[bool, str]:
        """Runs the verification command and returns (success, output)."""
        self._log(f"Running verification: {self.verification_command}")
        try:
            result = subprocess.run(
                self.verification_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            output = result.stdout + "\n" + result.stderr
            return (result.returncode == 0, output)
        except subprocess.TimeoutExpired:
            return (False, "Verification timed out after 60s")
        except Exception as e:
            return (False, f"Verification failed to run: {e}")

    def run(self) -> Dict[str, Any]:
        """Execute the repair loop."""
        
        if not self.target_file.exists():
            return {
                "status": "error", 
                "message": f"Target file {self.target_file} not found"
            }

        self._log(f"Starting Fixer Loop for {self.target_file.name}")
        
        # Initial Verification
        success, output = self._run_verification()
        if success:
            self._log("Initial verification PASSED. No fix needed.")
            return {
                "status": "success",
                "message": "File passed verification initially.",
                "logs": self.logs
            }

        self._log("Initial verification FAILED. Starting repair cycles.")
        
        for attempt in range(1, self.max_retries + 1):
            self._log(f"--- Attempt {attempt}/{self.max_retries} ---")
            
            # Diagnose & Fix
            issues_context = f"Verification Command: {self.verification_command}\n\nOutput:\n{output[-2000:]}" # Truncate output
            
            self._log("Invoking Fixer Agent...")
            try:
                # Calls brain_fix_code(path, context)
                fix_result_json = self.fixer_func(str(self.target_file), issues_context)
                fix_result = json.loads(fix_result_json)
                
                if fix_result.get("status") == "error":
                    self._log(f"Fixer Agent Error: {fix_result.get('message')}")
                    # Continue anyway? No, probably fatal.
                    # But maybe transient.
            except Exception as e:
                self._log(f"Exception calling fixer: {e}")
            
            # Verify Again
            success, output = self._run_verification()
            if success:
                self._log("✅ Verification PASSED after fix.")
                return {
                    "status": "success",
                    "message": f"Fixed in {attempt} attempts.",
                    "logs": self.logs
                }
            else:
                self._log("❌ Verification FAILED. Retrying...")

        return {
            "status": "failure",
            "message": f"Failed to fix after {self.max_retries} attempts.",
            "last_output": output,
            "logs": self.logs
        }
