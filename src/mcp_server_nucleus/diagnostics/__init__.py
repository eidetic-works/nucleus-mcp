"""Nucleus diagnostics — portable live-inspection primitives.

Each module owns one stand-alone verification:

- ``core``      — DualEngineLLM smoke test (RESEARCH tier, single generate_content).
- ``mcp``       — MCP server import + tool-registration check, with demo root
  configurable via ``NUCLEUS_DEMO_ROOT`` (falls back to
  ``<NUCLEUS_ROOT>/output/demos``).
- ``dashboard`` — HUD frontend-file existence + content sanity check.
- ``accuracy``  — engram SQLite update/query roundtrip; receipt JSON written
  to ``NUCLEUS_ACCURACY_RECEIPT`` or ``<NUCLEUS_ROOT>/nucleus_accuracy_receipt.json``.

All modules route user-facing paths through ``mcp_server_nucleus.paths`` so
they run on any machine with ``NUCLEUS_ROOT`` set (or from any user home as
dev-compat fallback). Shipped code must not reintroduce hardcoded paths.
"""
