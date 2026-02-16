"""
GCloud Ops - Phase 49 Implementation
====================================
Wraps the local `gcloud` CLI to query infrastructure state.

This enables "Smooth across IDEs and CLI" (Tier 4 in NUCLEUS_PRODUCT_SPECS.md).
The agent becomes the DevOps engineer using YOUR local gcloud auth.

Usage:
    ops = GCloudOps()
    status = ops.get_cloud_run_services()
"""

import os
import json
import subprocess
import shutil
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger("nucleus.gcloud_ops")


def find_gcloud() -> Optional[str]:
    """Find gcloud binary in PATH or common locations."""
    # 1. Check PATH
    gcloud_path = shutil.which("gcloud")
    if gcloud_path:
        return gcloud_path
    
    # 2. Check common locations (Mac/Linux)
    common_paths = [
        os.path.expanduser("~/google-cloud-sdk/bin/gcloud"),
        "/usr/local/bin/gcloud",
        "/opt/homebrew/bin/gcloud",
        "/usr/bin/gcloud",
        # Homebrew on Apple Silicon
        "/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gcloud",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    
    return None


@dataclass
class GCloudResult:
    """Result of a gcloud command."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    command: str = ""
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "command": self.command
        }


class GCloudOps:
    """
    Wraps gcloud CLI for infrastructure queries.
    
    Uses the user's local gcloud authentication - no API keys needed.
    """
    
    def __init__(self, project: Optional[str] = None, region: str = "us-central1"):
        self.gcloud_path = find_gcloud()
        self.project = project or os.environ.get("GCLOUD_PROJECT")
        self.region = region
        
    @property
    def is_available(self) -> bool:
        """Check if gcloud is available."""
        return self.gcloud_path is not None
    
    def _run(self, args: List[str], format_json: bool = True) -> GCloudResult:
        """Run a gcloud command and return result."""
        if not self.is_available:
            return GCloudResult(
                success=False,
                error="gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install",
                command=" ".join(args)
            )
        
        cmd = [self.gcloud_path] + args
        if format_json:
            cmd.extend(["--format", "json"])
        
        full_cmd = " ".join(cmd)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return GCloudResult(
                    success=False,
                    error=result.stderr.strip() or f"Command failed with exit code {result.returncode}",
                    command=full_cmd
                )
            
            if format_json and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    data = result.stdout.strip()
            else:
                data = result.stdout.strip()
            
            return GCloudResult(success=True, data=data, command=full_cmd)
            
        except subprocess.TimeoutExpired:
            return GCloudResult(
                success=False,
                error="Command timed out (30s)",
                command=full_cmd
            )
        except Exception as e:
            return GCloudResult(
                success=False,
                error=str(e),
                command=full_cmd
            )
    
    def get_current_project(self) -> GCloudResult:
        """Get the current active project."""
        return self._run(["config", "get-value", "project"], format_json=False)
    
    def get_account(self) -> GCloudResult:
        """Get the current authenticated account."""
        return self._run(["config", "get-value", "account"], format_json=False)
    
    def list_cloud_run_services(self, project: Optional[str] = None) -> GCloudResult:
        """List Cloud Run services."""
        args = ["run", "services", "list"]
        if project or self.project:
            args.extend(["--project", project or self.project])
        args.extend(["--region", self.region])
        return self._run(args)
    
    def get_cloud_run_service(self, service_name: str, project: Optional[str] = None) -> GCloudResult:
        """Get details of a specific Cloud Run service."""
        args = ["run", "services", "describe", service_name]
        if project or self.project:
            args.extend(["--project", project or self.project])
        args.extend(["--region", self.region])
        return self._run(args)
    
    def get_cloud_run_revisions(self, service_name: str, project: Optional[str] = None) -> GCloudResult:
        """List revisions for a Cloud Run service."""
        args = ["run", "revisions", "list", "--service", service_name]
        if project or self.project:
            args.extend(["--project", project or self.project])
        args.extend(["--region", self.region])
        return self._run(args)
    
    def check_auth_status(self) -> Dict[str, Any]:
        """Check overall gcloud authentication status."""
        return {
            "gcloud_available": self.is_available,
            "gcloud_path": self.gcloud_path,
            "project": self.get_current_project().data if self.is_available else None,
            "account": self.get_account().data if self.is_available else None,
        }


# Singleton instance
_gcloud_ops: Optional[GCloudOps] = None


def get_gcloud_ops() -> GCloudOps:
    """Get or create the global GCloudOps instance."""
    global _gcloud_ops
    if _gcloud_ops is None:
        _gcloud_ops = GCloudOps()
    return _gcloud_ops
