"""hook.py's error handler must be able to log, not raise.

_process_autonomous_wake ends with a deliberate catch-all whose comment reads:

    # NEVER let autonomous wake errors bubble up + break the hook.
    # PR #480 hook-break-broke-all-sessions precedent — but silence is
    # not the same as safety: a corrupt config or import error means
    # autonomous wakes stop firing for every offline role, forever,
    # with zero signal. Keep the fail-safe exit contract, log the loss.
    logger.exception(...)

The reasoning is exactly right. The implementation defeated it: `logger` was
never defined in the module and there was no `import logging`, so the call
raised NameError. The loss the author insisted on recording was never recorded.

An error handler that raises is worse than no handler at all -- it replaces the
real exception with its own, so the thing you needed to see is the one thing
you cannot.
"""

import logging


def test_module_defines_a_logger():
    from mcp_server_nucleus.mirror import hook
    assert isinstance(getattr(hook, "logger", None), logging.Logger), (
        "hook.py calls logger.exception() in its catch-all; without a module "
        "logger that handler raises NameError"
    )


def test_every_logger_use_in_the_module_resolves():
    """Guards the general case, not just the one call site. A second
    logger.<method>() added later in a module that only accidentally has a
    logger would fail the same way."""
    import inspect
    from mcp_server_nucleus.mirror import hook
    src = inspect.getsource(hook)
    if "logger." in src:
        assert "logger = logging.getLogger(" in src


def test_the_handler_logs_instead_of_raising(caplog):
    """The behaviour, not just the binding: calling the logger must produce a
    record rather than an exception."""
    from mcp_server_nucleus.mirror import hook
    with caplog.at_level(logging.ERROR, logger="nucleus.mirror.hook"):
        try:
            raise ValueError("simulated wake failure")
        except ValueError:
            hook.logger.exception("test: autonomous wake failed for role=%s", "peer")
    assert any("autonomous wake failed" in r.getMessage() for r in caplog.records)
