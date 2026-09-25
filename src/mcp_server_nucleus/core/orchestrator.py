"""
Orchestrator Initialization Module
"""

# Lazy-loaded singleton for orchestrator access
def get_orchestrator(brain_path=None):
    """Get the orchestrator for a brain, resolving per call.

    The import used to be ``from .orchestrator_unified import get_orchestrator``
    — relative, so it resolved to ``mcp_server_nucleus.core.orchestrator_unified``,
    which does not exist. There is only ``runtime/orchestrator_unified.py``. The
    module therefore imported cleanly (the bad import sits inside the function)
    and raised ``ModuleNotFoundError`` the first time anybody called it, while
    ``core/__init__.py`` re-exported it as part of the package's public surface.
    Nothing in this mirror calls it, which is why it went unnoticed (ledger CN-4).

    ``brain_path`` is threaded through because the underlying resolver is keyed
    per brain: it was a process-wide singleton until TN-3, so a wrapper that
    dropped the argument would quietly reintroduce the cross-tenant behaviour
    that fix removed.
    """
    from ..runtime.orchestrator_unified import get_orchestrator as _get
    return _get(brain_path)
