"""Shared combo-status derivation for all god_combos.

This module is the shared mechanism by which every god_combo reduces its
list of per-step results into a single aggregate status plus the list of
degraded step names. Keeping the logic here ensures all combos agree on
the semantics of ``ok`` / ``partial`` / ``failed``.

The empty-list -> ``OK`` contract is intentional: a combo with no steps
has nothing degraded, so reporting ``OK`` (rather than ``failed`` or
``skipped``) is the correct no-op result.
"""

OK = "ok"
SKIPPED = "skipped"


def derive_combo_status(steps: list[dict]) -> tuple[str, list[str]]:
    """Derive the aggregate status of a combo from its per-step results.

    Args:
        steps: List of step dicts. Each dict is expected to carry a
            ``"name"`` key and a ``"status"`` key (compared against
            :data:`OK`). Steps missing a ``"status"`` key are treated as
            degraded.

    Returns:
        A ``(status, degraded_steps)`` tuple where ``status`` is one of
        ``"ok"``, ``"partial"``, or ``"failed"`` and ``degraded_steps`` is
        the list of step names whose status was not :data:`OK`.
    """
    degraded_steps = [s["name"] for s in steps if s.get("status") != OK]
    ok_count = len(steps) - len(degraded_steps)

    if not steps or ok_count == len(steps):
        status = OK
    elif ok_count == 0:
        status = "failed"
    else:
        status = "partial"

    return (status, degraded_steps)
