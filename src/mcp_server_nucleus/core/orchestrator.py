"""
Orchestrator Initialization Module
"""

# Lazy-loaded singleton for orchestrator access
def get_orchestrator():
    """Get the orchestrator singleton (Unified)."""
    from .orchestrator_unified import get_orchestrator
    return get_orchestrator()
