"""
Environment Adaptation Layer
===============================
Phase 73.2: Cross-Platform & Cross-Host Reliability

Detects and adapts to:
1. OS: Windows, macOS, Linux
2. MCP Host: Windsurf, Claude Desktop, Perplexity, Antigravity, Cursor, CLI
3. Path normalization across platforms
4. Environment variable validation
5. Filesystem capability detection

Target: 99.9% reliability across all deployment environments.
"""

import logging
import os
import platform
import sys
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("nucleus.environment")


# ============================================================
# OS DETECTION
# ============================================================

class OSType(str, Enum):
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


class MCPHost(str, Enum):
    WINDSURF = "windsurf"
    CLAUDE_DESKTOP = "claude_desktop"
    PERPLEXITY = "perplexity"
    ANTIGRAVITY = "antigravity"
    CURSOR = "cursor"
    OPENCLAW = "openclaw"
    CLI = "cli"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentInfo:
    """Complete environment information snapshot."""
    os_type: OSType
    os_version: str
    mcp_host: MCPHost
    python_version: str
    brain_path: str
    home_dir: str
    is_writable: bool
    has_network: bool
    available_disk_mb: float
    env_vars_present: List[str]
    env_vars_missing: List[str]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_type": self.os_type.value,
            "os_version": self.os_version,
            "mcp_host": self.mcp_host.value,
            "python_version": self.python_version,
            "brain_path": self.brain_path,
            "home_dir": self.home_dir,
            "is_writable": self.is_writable,
            "has_network": self.has_network,
            "available_disk_mb": round(self.available_disk_mb, 1),
            "env_vars_present": self.env_vars_present,
            "env_vars_missing": self.env_vars_missing,
            "warnings": self.warnings,
        }


class EnvironmentDetector:
    """
    Detects runtime environment and adapts Nucleus behavior accordingly.
    
    Cross-platform: Mac, Windows, Linux
    Cross-host: Windsurf, Claude Desktop, Perplexity, Antigravity, Cursor, CLI
    """

    # Environment variables that Nucleus uses
    REQUIRED_ENV_VARS = ["GEMINI_API_KEY"]
    OPTIONAL_ENV_VARS = [
        "NUCLEUS_BRAIN_PATH", "NUCLEAR_BRAIN_PATH",
        "NUCLEUS_INTENT_MODEL", "NUCLEUS_VALIDATOR_MODEL", "NUCLEUS_LEARNER_MODEL",
        "NUCLEUS_LLM_TIMEOUT", "NUCLEUS_TOOL_TIER",
        "GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT",
    ]

    # MCP host detection signatures
    MCP_HOST_SIGNATURES = {
        MCPHost.WINDSURF: [
            "WINDSURF", "windsurf",
            lambda: _check_process("windsurf"),
            lambda: _check_env_contains("EDITOR", "windsurf"),
        ],
        MCPHost.CLAUDE_DESKTOP: [
            "CLAUDE_DESKTOP", "claude",
            lambda: _check_process("claude"),
            lambda: _check_path_exists("~/Library/Application Support/Claude"),
            lambda: _check_path_exists(os.path.expandvars("%APPDATA%/Claude")),
        ],
        MCPHost.PERPLEXITY: [
            "PERPLEXITY",
            lambda: _check_process("perplexity"),
        ],
        MCPHost.ANTIGRAVITY: [
            "ANTIGRAVITY", "antigravity",
            lambda: _check_process("antigravity"),
            lambda: _check_env_contains("TERM_PROGRAM", "antigravity"),
        ],
        MCPHost.CURSOR: [
            "CURSOR",
            lambda: _check_process("cursor"),
            lambda: _check_env_contains("TERM_PROGRAM", "cursor"),
        ],
        MCPHost.OPENCLAW: [
            "OPENCLAW", "openclaw",
            lambda: _check_process("openclaw"),
        ],
    }

    def __init__(self):
        self._cached_info: Optional[EnvironmentInfo] = None

    def detect(self, force_refresh: bool = False) -> EnvironmentInfo:
        """Detect current environment. Cached unless force_refresh."""
        if self._cached_info and not force_refresh:
            return self._cached_info

        warnings = []

        # OS Detection
        os_type = self._detect_os()
        os_version = platform.platform()

        # MCP Host Detection
        mcp_host = self._detect_mcp_host()

        # Brain path (cross-platform)
        brain_path = self._resolve_brain_path(os_type)

        # Home directory
        home_dir = str(Path.home())

        # Writable check
        is_writable = self._check_writable(brain_path)
        if not is_writable:
            warnings.append(f"Brain path not writable: {brain_path}")

        # Network check (lightweight)
        has_network = self._check_network()
        if not has_network:
            warnings.append("No network connectivity detected")

        # Disk space
        available_disk_mb = self._check_disk_space(brain_path)
        if available_disk_mb < 100:
            warnings.append(f"Low disk space: {available_disk_mb:.0f}MB available")

        # Environment variables
        present, missing = self._check_env_vars()
        if missing:
            warnings.append(f"Missing required env vars: {missing}")

        self._cached_info = EnvironmentInfo(
            os_type=os_type,
            os_version=os_version,
            mcp_host=mcp_host,
            python_version=platform.python_version(),
            brain_path=brain_path,
            home_dir=home_dir,
            is_writable=is_writable,
            has_network=has_network,
            available_disk_mb=available_disk_mb,
            env_vars_present=present,
            env_vars_missing=missing,
            warnings=warnings,
        )

        if warnings:
            for w in warnings:
                logger.warning(f"Environment: {w}")

        return self._cached_info

    def _detect_os(self) -> OSType:
        """Detect operating system."""
        system = platform.system().lower()
        if system == "darwin":
            return OSType.MACOS
        elif system == "windows":
            return OSType.WINDOWS
        elif system == "linux":
            return OSType.LINUX
        return OSType.UNKNOWN

    def _detect_mcp_host(self) -> MCPHost:
        """Detect which MCP host we're running in."""
        # Check explicit env var first
        explicit = os.environ.get("NUCLEUS_MCP_HOST", "").lower()
        for host in MCPHost:
            if host.value == explicit:
                return host

        # Check signatures
        for host, signatures in self.MCP_HOST_SIGNATURES.items():
            for sig in signatures:
                if callable(sig):
                    try:
                        if sig():
                            return host
                    except Exception:
                        continue
                elif isinstance(sig, str):
                    if os.environ.get(sig):
                        return host

        # Check parent process name
        try:
            import psutil
            parent = psutil.Process(os.getppid())
            pname = parent.name().lower()
            for host in MCPHost:
                if host.value in pname:
                    return host
        except (ImportError, Exception):
            pass

        # Fallback: check if running as MCP server (stdio mode)
        if not sys.stdin.isatty():
            return MCPHost.UNKNOWN  # Some MCP host, just can't determine which

        return MCPHost.CLI

    def _resolve_brain_path(self, os_type: OSType) -> str:
        """Resolve brain path cross-platform."""
        # Explicit env var
        explicit = os.environ.get(
            "NUCLEUS_BRAIN_PATH",
            os.environ.get("NUCLEAR_BRAIN_PATH", "")
        )
        if explicit:
            return str(Path(explicit).resolve())

        # Default: .brain in current directory or home
        cwd_brain = Path.cwd() / ".brain"
        if cwd_brain.exists():
            return str(cwd_brain)

        # Home-based fallback
        home_brain = Path.home() / ".nucleus" / "brain"
        return str(home_brain)

    def _check_writable(self, path: str) -> bool:
        """Check if path is writable (cross-platform)."""
        try:
            p = Path(path)
            if p.exists():
                return os.access(str(p), os.W_OK)
            # Check parent
            parent = p.parent
            while not parent.exists() and parent != parent.parent:
                parent = parent.parent
            return os.access(str(parent), os.W_OK)
        except Exception:
            return False

    def _check_network(self) -> bool:
        """Lightweight network connectivity check."""
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except (socket.timeout, OSError):
            return False

    def _check_disk_space(self, path: str) -> float:
        """Check available disk space in MB."""
        try:
            p = Path(path)
            check_path = p if p.exists() else p.parent
            while not check_path.exists() and check_path != check_path.parent:
                check_path = check_path.parent
            usage = shutil.disk_usage(str(check_path))
            return usage.free / (1024 * 1024)
        except Exception:
            return float('inf')  # Assume enough if check fails

    def _check_env_vars(self) -> tuple:
        """Check required and optional environment variables."""
        present = []
        missing = []
        for var in self.REQUIRED_ENV_VARS:
            if os.environ.get(var):
                present.append(var)
            else:
                missing.append(var)
        for var in self.OPTIONAL_ENV_VARS:
            if os.environ.get(var):
                present.append(var)
        return present, missing

    def normalize_path(self, path: str) -> str:
        """Normalize path for current OS."""
        if not path:
            return path
        # Convert to Path and resolve
        try:
            return str(Path(path).resolve())
        except Exception:
            return path

    def get_safe_brain_path(self) -> Path:
        """Get a guaranteed-writable brain path, creating if needed."""
        info = self.detect()
        brain = Path(info.brain_path)

        if info.is_writable:
            brain.mkdir(parents=True, exist_ok=True)
            return brain

        # Fallback to home directory
        fallback = Path.home() / ".nucleus" / "brain"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback brain path: {fallback}")
            return fallback
        except Exception:
            # Last resort: temp directory
            import tempfile
            tmp = Path(tempfile.gettempdir()) / "nucleus_brain"
            tmp.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using temp brain path: {tmp}")
            return tmp


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _check_process(name: str) -> bool:
    """Check if a process with given name is running."""
    try:
        import subprocess
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist"], capture_output=True, text=True, timeout=5
            )
            return name.lower() in result.stdout.lower()
        else:
            result = subprocess.run(
                ["pgrep", "-i", name], capture_output=True, timeout=5
            )
            return result.returncode == 0
    except Exception:
        return False


def _check_env_contains(var: str, value: str) -> bool:
    """Check if env var contains value."""
    return value.lower() in os.environ.get(var, "").lower()


def _check_path_exists(path: str) -> bool:
    """Check if expanded path exists."""
    try:
        return Path(os.path.expanduser(path)).exists()
    except Exception:
        return False


# ============================================================
# SINGLETON
# ============================================================

_detector_instance: Optional[EnvironmentDetector] = None

def get_environment_detector() -> EnvironmentDetector:
    """Get singleton environment detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EnvironmentDetector()
    return _detector_instance
