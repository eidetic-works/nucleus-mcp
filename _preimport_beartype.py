"""Pytest plugin: pre-import beartype.claw before coverage tracer starts.

Loaded via ``-p tests._preimport_beartype`` so it runs before pytest-cov
starts the coverage tracer. The key_value/aio package lazily imports
beartype.claw, and when that import happens under coverage's tracer it
hits a circular-import deadlock in beartype's import hook. Pre-importing
here fully resolves the module so the later import finds it cached.
"""
import beartype.claw  # noqa: F401
import beartype.claw._clawstate  # noqa: F401
