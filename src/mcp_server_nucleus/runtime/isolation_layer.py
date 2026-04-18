import os
import tempfile
from typing import Dict, List, Optional
from pathlib import Path

class EnvironmentSanitizer:
    """Strict environment whitelisting and sanitization for SEE processes."""

    # Baseline required variables
    WHITELIST = {
        "PATH",
        "PYTHONPATH",
        "LANG",
        "LC_ALL",
        "TERM",
        "NUCLEUS_TOKEN",
        "NUCLEUS_AGENT_TIER",
        "NUCLEUS_SESSION_ID",
        "GEMINI_API_KEY",
        "NUCLEAR_BRAIN_PATH",
        "GEMINI_API_BASE_URL",
        "GEMINI_BASE_URL",
        "GEMINI_NEXT_GEN_API_BASE_URL",
        "GOOGLE_GEMINI_BASE_URL",
    }

    def __init__(self, sandbox_root: Optional[Path] = None):
        self.sandbox_root = sandbox_root or Path(tempfile.gettempdir()) / "nucleus" / "sandbox"

    def get_isolated_env(self, base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Return a stripped and mapped environment."""
        source = base_env or os.environ
        isolated = {}

        # 1. Apply Whitelist
        for key in self.WHITELIST:
            if key in source:
                isolated[key] = source[key]

        # 2. Virtualize sensitive paths
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        isolated["HOME"] = str(self.sandbox_root)
        isolated["TMPDIR"] = str(self.sandbox_root / "tmp")
        (self.sandbox_root / "tmp").mkdir(parents=True, exist_ok=True)

        # 3. Prevent Shell leakage
        isolated["SHELL"] = "/bin/sh" # Force standard shell
        
        return isolated
