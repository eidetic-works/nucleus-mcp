"""Governance & Hypervisor tools — lock/unlock, watch, hypervisor mode, egress proxy.

Super-Tools Facade: All 10 governance actions exposed via a single
`nucleus_governance(action, params)` MCP tool.
"""

import json
import sys
from typing import Dict, Any

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_governance facade tool with the MCP server."""
    from ..runtime.hypervisor_ops import (
        lock_resource_impl, unlock_resource_impl, set_hypervisor_mode_impl,
        nucleus_list_directory_impl, nucleus_delete_file_impl,
        watch_resource_impl, hypervisor_status_impl,
    )
    from ..core.egress_proxy import nucleus_curl_impl, nucleus_pip_install_impl
    from ..runtime.event_ops import _emit_event

    def _auto_fix_loop(file_path, verification_command):
        from ..runtime.loops.fixer import FixerLoop
        from .orchestration import _fix_code_impl
        loop = FixerLoop(
            target_file=file_path,
            verification_command=verification_command,
            fixer_func=_fix_code_impl,
            max_retries=3
        )
        return json.dumps(loop.run(), indent=2)

    ROUTER = {
        "auto_fix_loop": lambda file_path, verification_command: _auto_fix_loop(file_path, verification_command),
        "lock": lambda path: lock_resource_impl(path),
        "unlock": lambda path: unlock_resource_impl(path),
        "set_mode": lambda mode: set_hypervisor_mode_impl(mode),
        "list_directory": lambda path: nucleus_list_directory_impl(path),
        "delete_file": lambda path, confirm=False: nucleus_delete_file_impl(path, emit_event_fn=_emit_event, confirm=confirm),
        "watch": lambda path: watch_resource_impl(path),
        "status": lambda: hypervisor_status_impl(),
        "curl": lambda url, method="GET": nucleus_curl_impl(url, method),
        "pip_install": lambda package: nucleus_pip_install_impl(package),
    }

    @mcp.tool()
    def nucleus_governance(action: str, params: dict = None) -> str:
        """Governance, Hypervisor & security tools for the Nucleus Agent OS.

Actions:
  auto_fix_loop   - Auto-fix loop: Verify->Diagnose->Fix->Verify (3 retries). params: {file_path, verification_command}
  lock            - [HYPERVISOR] Lock a file/dir immutable (chflags uchg). params: {path}
  unlock          - [HYPERVISOR] Unlock a file/dir. params: {path}
  set_mode        - [HYPERVISOR] Switch IDE context: "red" or "blue". params: {mode}
  list_directory  - [GOVERNANCE] List files in a directory. params: {path}
  delete_file     - [GOVERNANCE] Delete a file (governed by Hypervisor). params: {path, confirm?}. HITL: requires confirm=true.
  watch           - [HYPERVISOR] Monitor a file/folder for changes. params: {path}
  status          - [HYPERVISOR] Report current security state of Agent OS
  curl            - [EGRESS] Proxied HTTP fetch for air-gapped agents. params: {url, method?}
  pip_install     - [EGRESS] Proxied pip install for air-gapped agents. params: {package}
"""
        params = params or {}
        return dispatch(action, params, ROUTER, "nucleus_governance")

    return [("nucleus_governance", nucleus_governance)]
