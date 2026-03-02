"""
v0.6.0 DSoR: IPC Authentication & Token Metering

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from mcp_server_nucleus.runtime.auth instead.

Migration:
    # Old (deprecated)
    from mcp_server_nucleus.runtime.ipc_auth import get_ipc_auth_manager
    
    # New
    from mcp_server_nucleus.runtime.auth import get_ipc_auth_manager

See docs/AUTH_ARCHITECTURE.md for the OAuth-Ready Architecture design.
"""

import warnings

warnings.warn(
    "mcp_server_nucleus.runtime.ipc_auth is deprecated. "
    "Use mcp_server_nucleus.runtime.auth instead.",
    DeprecationWarning,
    stacklevel=2
)

from .auth.ipc_provider import (
    IPCToken,
    TokenMeterEntry,
    IPCAuthProvider as IPCAuthManager,
    get_ipc_auth_manager,
    require_ipc_token,
    get_brain_path,
)

__all__ = [
    "IPCToken",
    "TokenMeterEntry",
    "IPCAuthManager",
    "get_ipc_auth_manager",
    "require_ipc_token",
    "get_brain_path",
]
