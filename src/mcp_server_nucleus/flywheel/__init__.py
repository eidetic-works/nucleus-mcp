"""Nucleus Flywheel — the compounding loop engine.

Every failure → ticket → curriculum pair → next training run.
Every success → CSR claim bump → dashboard delta.

This subpackage inlines what would become the `nucleus-flywheel` pip-installable
SDK; for now it ships as a module inside mcp-server-nucleus to keep the first PR
atomic. The public API below is stable and will be the entry point when the
package is extracted to its own repo.

Public API
----------
    Flywheel — the main class, bootstraps .brain/flywheel/ on first use
    record_survived(phase, step) — bump CSR claims_survived
    file_ticket(step, error, logs) — the 6-action accountability helper
    render_dashboard_json() — dashboard state as JSON
    render_dashboard_html() — dashboard as a self-contained HTML page
    generate_week_report() — weekly markdown report
    curriculum_refresh() — close the training loop
"""

from .core import Flywheel, file_ticket, record_survived
from .csr import bump_survived, bump_unsurvived, read_csr
from .dashboard import render_dashboard_html, render_dashboard_json
from .report import generate_week_report
from .curriculum import curriculum_refresh

__all__ = [
    "Flywheel",
    "file_ticket",
    "record_survived",
    "bump_survived",
    "bump_unsurvived",
    "read_csr",
    "render_dashboard_html",
    "render_dashboard_json",
    "generate_week_report",
    "curriculum_refresh",
]

__version__ = "0.1.0"
