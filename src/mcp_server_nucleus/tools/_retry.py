"""Client-side retry helper for facade tool dispatch.

Consumers that see a `transport_closed` envelope error can wrap their
dispatch call in `with_retry(...)` to auto-retry once with exponential
backoff. Deliberately small surface — one retry, one backoff, no
stateful client.

Usage:
    from mcp_server_nucleus.tools._retry import with_retry

    result = with_retry(
        lambda: dispatch("foo", {}, ROUTER, "mod"),
        max_retries=1,
        initial_backoff=0.5,
    )

Retry triggers:
  - Return value is an envelope with `ok=False` and an `error_type`
    in {transport_closed, timeout, rate_limited}.
  - Otherwise the result passes through untouched.

Non-goals:
  - Server-side retry (that would mask real failures).
  - Retry budgets / circuit breakers (belongs in higher-level orchestration).
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Iterable, Optional

_DEFAULT_RETRY_ON = frozenset({"transport_closed", "timeout", "rate_limited"})


def _extract_error_type(result: Any) -> Optional[str]:
    """Return the error_type if `result` is an envelope-shaped failure."""
    payload = result
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except ValueError:
            return None
    if not isinstance(payload, dict):
        return None
    if payload.get("ok") is True:
        return None
    err = payload.get("error")
    if isinstance(err, dict):
        et = err.get("error_type")
        if isinstance(et, str):
            return et
    return None


def with_retry(
    fn: Callable[[], Any],
    *,
    max_retries: int = 1,
    initial_backoff: float = 0.5,
    backoff_multiplier: float = 2.0,
    retry_on: Iterable[str] = _DEFAULT_RETRY_ON,
) -> Any:
    """Execute `fn()` with bounded retry on envelope error types.

    Args:
      fn: Zero-arg callable. Typically `lambda: dispatch(...)`.
      max_retries: Number of retries AFTER the first attempt. Default 1.
      initial_backoff: Seconds to wait before first retry.
      backoff_multiplier: Multiplier applied per retry.
      retry_on: error_types that trigger retry. Default covers transient
                transport failures.

    Returns:
      The last `fn()` result. Note: if a retriable failure persists,
      the failure envelope is returned — callers must check ok.
    """
    retry_on = frozenset(retry_on)
    attempts = max_retries + 1
    backoff = initial_backoff
    last = None
    for i in range(attempts):
        last = fn()
        et = _extract_error_type(last)
        if et is None or et not in retry_on or i == attempts - 1:
            return last
        time.sleep(backoff)
        backoff *= backoff_multiplier
    return last


__all__ = ["with_retry"]
