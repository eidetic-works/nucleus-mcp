"""Nucleus Agent OS — the runtime an agent lives INSIDE.

Stage 0 (`boot.py`) is THE FIRST CELL: the minimal loop where one agent's
cognition routes through the Nucleus gateway, memory is recalled + injected
before it thinks, and the turn is recorded to the flywheel after.

See ``docs/AGENT_OS_MANIFESTO.md`` and ``docs/AGENT_OS_ROADMAP.md`` (Stage 0).

Everything here is gated behind ``NUCLEUS_AGENT_OS_BOOT`` (default OFF).
Importing this package runs nothing.
"""

from .boot import (  # noqa: F401
    BOOT_FLAG,
    BootResult,
    GatewayResult,
    NucleusGateway,
    boot_cell,
    boot_flag_enabled,
    recall_and_inject,
    record_turn_to_flywheel,
)
