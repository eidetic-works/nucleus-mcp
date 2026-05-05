"""Nucleus admin — portable control-plane primitives.

Each module owns one stand-alone operator command:

- ``switch_brain`` — swap the brain preset (warm/prod/cold/dogfood) that an
  MCP host (Gemini Antigravity today; any MCP-config JSON in the future) uses
  for the Nucleus server. Rewrites the host config, kills running Nucleus
  processes, and optionally wipes cold-brain state for a clean-slate test.
- ``triggers`` — writes the canonical default-triggers JSON (v2.2) into the
  ledger. Reusable primitive for bootstrap + recovery; the v2.2 trigger list
  is exposed as ``default_triggers_v22()`` for callers that want to merge
  rather than overwrite.

Env contract (each module resolves paths through
``mcp_server_nucleus.paths`` and its own override):

- ``NUCLEUS_ROOT`` / ``NUCLEUS_BRAIN`` / ``NUCLEUS_BRAIN_PATH`` (shared).
- ``NUCLEUS_ANTIGRAVITY_CONFIG`` — MCP-host config path for ``switch_brain``.
- ``NUCLEUS_TEST_BRAIN``         — cold-brain path override for ``switch_brain``.
- ``NUCLEUS_TRIGGERS_PATH``      — ledger triggers file for ``triggers``.

Portability rule (primitive-gate): shipped code must not reintroduce
developer-machine absolute paths. All filesystem roots flow from the env
contract above or from ``paths.nucleus_root()`` / ``paths.brain_path()``.
"""
