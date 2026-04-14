"""
Nucleus HTTP Transport Layer
==============================
Provides Option 1 (local HTTP/SSE) and Option 2 (Cloud Run ASGI) entrypoints.

Tenant-aware by default — see tenant.py for the isolation contract.
"""

from .tenant import NucleusTenantMiddleware, brain_path_for_tenant, resolve_tenant

__all__ = ["NucleusTenantMiddleware", "brain_path_for_tenant", "resolve_tenant"]
