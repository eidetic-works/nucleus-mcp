"""MCP tool-handler call-count instrumentation.

Treatment criterion 2: discharge requires every registered primitive
classified with N>=1 OBSERVED invocations or a deprecation date. Static
analysis cannot prove a primitive fires; this records every invocation
to a JSONL channel so future audits can answer empirically.

Design rationale (sweep #002 hole-poke 2026-06-11T06:02Z, peer-CC'd):

- JSONL channel at .brain/instrumentation/YYYYMMDD.jsonl, NOT engram
  insert per call. The eidetic daemon currently sits at 541k engrams
  with a 5s full-table-scan deadline (cc-tb-20260611T054957Z); adding
  thousands of inserts/day worsens the count-class problem AND causes
  recursive insert-on-insert when the tool BEING invoked IS insert_engram
  or nucleus_engrams.

- Daily aggregator (sweep #003 carry) collapses each day's JSONL into a
  single (date, tool) summary engram. Engram store grows linearly with
  days, not invocations.

- Decoupled from substrate health: instrumentation keeps recording even
  when daemon is healthy:false (per 2026-06-11 incident — that's exactly
  when invocation counts would be most diagnostic).

Env knobs:
    NUCLEUS_INSTRUMENT_DISABLED=1   short-circuit at handler entry (zero
                                    overhead, opt-out per-deployment).
    NUCLEUS_INSTRUMENT_PATH=<dir>   override JSONL parent directory
                                    (default: repo's .brain/instrumentation;
                                    falls back to $HOME/.brain/instrumentation
                                    if repo path unwritable).
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

_LOCK = threading.Lock()
_JSONL_PATH_CACHE: dict[str, Path] = {}


def _jsonl_dir() -> Path:
    """Resolve the instrumentation directory; cwd-relative .brain preferred.

    Crack #6 (peer addendum 2026-06-11T06:13Z): the override branch MUST also
    mkdir, else NUCLEUS_INSTRUMENT_PATH pointing at a nonexistent dir turns the
    documented env knob into a silent /dev/null with zero signal.
    """
    override = os.environ.get("NUCLEUS_INSTRUMENT_PATH")
    if override:
        override_path = Path(override)
        override_path.mkdir(parents=True, exist_ok=True)
        return override_path
    cwd_brain = Path.cwd() / ".brain" / "instrumentation"
    try:
        cwd_brain.mkdir(parents=True, exist_ok=True)
        return cwd_brain
    except (OSError, PermissionError):
        home_brain = Path.home() / ".brain" / "instrumentation"
        home_brain.mkdir(parents=True, exist_ok=True)
        return home_brain


def _jsonl_path() -> Path:
    """Today's JSONL file. Cached per-date so we mkdir once per day."""
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    if date not in _JSONL_PATH_CACHE:
        _JSONL_PATH_CACHE[date] = _jsonl_dir() / f"{date}.jsonl"
    return _JSONL_PATH_CACHE[date]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _session_hint() -> str | None:
    """Read session hint from a strict allow-list of pseudonymous env vars.

    Pseudonymity contract (peer crack-poke 2026-06-11T06:08Z, crack #4):
    CC_SESSION_ROLE values are role names ('main', 'peer', 'operator_assistant',
    'cc_tb', etc.) — non-identifying by fleet convention. NEVER read $HOME-
    derived paths, usernames, hostnames, or cwd; JSONL records get quoted in
    PRs/ADRs/aggregator engrams (same leak vector as relay bodies).
    """
    return os.environ.get("CC_SESSION_ROLE") or None


def _emit(tool_name: str, duration_ms: float, error: str | None = None) -> None:
    if os.environ.get("NUCLEUS_INSTRUMENT_DISABLED") == "1":
        return
    record: dict[str, Any] = {
        "ts": _now_iso(),
        "tool": tool_name,
        "ms": round(duration_ms, 2),
    }
    sess = _session_hint()
    if sess:
        record["session"] = sess
    if error:
        record["error"] = error
    try:
        with _LOCK:
            with _jsonl_path().open("a") as fh:
                fh.write(json.dumps(record) + "\n")
    except Exception:
        # Instrumentation MUST NEVER break a tool call.
        # cc-main crack #2 (2026-06-11T06:45Z): the dir may have been deleted
        # mid-day by a cleanup sweep. Evict today's cache key so the next
        # call re-computes _jsonl_dir() and re-mkdirs — without this, every
        # _emit fails silently until midnight rollover (same /dev/null trap
        # as peer's crack #6 in the override-path direction).
        try:
            date = datetime.now(timezone.utc).strftime("%Y%m%d")
            _JSONL_PATH_CACHE.pop(date, None)
        except Exception:
            pass


def instrument(func: Callable, name: str | None = None) -> Callable:
    """Wrap a tool handler to emit one JSONL line per invocation.

    Async-aware (peer crack-poke 2026-06-11T06:08Z, crack #3): sync wrapper
    on a coroutine function would measure coroutine CONSTRUCTION (~0ms) not
    execution — every duration_ms uniformly wrong, undetectable for weeks.

    Idempotent (peer crack #7 fix part 2, 2026-06-11T06:52Z): the main-server
    chain traverses patched_tool TWICE per registration (outer mcp.tool entry
    + fastmcp partial(self.tool, ...) re-entry). Without this guard the
    direct-fn branch in patched_tool would double-wrap, yielding two JSONL
    records per call + nested timers.
    """
    if os.environ.get("NUCLEUS_INSTRUMENT_DISABLED") == "1":
        return func

    # cc-main 2nd-pass residual (2026-06-11T07:20Z, optional polish): functools.wraps
    # copies __dict__, so a future @wraps decorator applied ON TOP of an instrumented
    # wrapper would inherit _nucleus_instrumented=True. If re-registered through here,
    # instrument() skips — CORRECT when the outer delegates (inner still emits once);
    # silently un-instrumented ONLY for a short-circuiting outer (cache / memoize
    # shape). Zero such sites today across Servers A + B; revisit if a memoizing or
    # caching decorator gets layered between user code and @mcp.tool().
    if getattr(func, "_nucleus_instrumented", False):
        return func

    tool_name = name or getattr(func, "__name__", "<anonymous>")

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # cc-main nit #3 (2026-06-11T06:45Z, accepted-as-stated): _emit
            # is a sync blocking write inside finally; a stalled disk blocks
            # the event loop. Acceptable for current instrumentation volume
            # (one record per MCP call); revisit (e.g. background queue or
            # aiofiles) if disk slows or volume grows.
            start = time.monotonic_ns()
            error_type: str | None = None
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                error_type = type(exc).__name__
                raise
            finally:
                duration_ms = (time.monotonic_ns() - start) / 1_000_000.0
                _emit(tool_name, duration_ms, error=error_type)

        async_wrapper._nucleus_instrumented = True
        return async_wrapper

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic_ns()
        error_type: str | None = None
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            duration_ms = (time.monotonic_ns() - start) / 1_000_000.0
            _emit(tool_name, duration_ms, error=error_type)

    wrapper._nucleus_instrumented = True
    return wrapper


def install_instrumentation(mcp: Any) -> None:
    """Monkey-patch mcp.tool to wrap every registered handler.

    Idempotent: a second install_instrumentation call on the same mcp
    instance is a no-op (detected via an attribute sentinel).
    """
    if os.environ.get("NUCLEUS_INSTRUMENT_DISABLED") == "1":
        return
    if getattr(mcp, "_nucleus_instrumentation_installed", False):
        return

    original_tool = mcp.tool

    def patched_tool(*args, **kwargs):
        # Peer crack #7 (2026-06-11T06:52Z): fastmcp 2.14.3's tool() returns
        # partial(self.tool, ...) when called without a fn. The partial re-
        # enters self.tool (= patched_tool) with the function as first
        # POSITIONAL CALLABLE. Direct-fn mode MUST forward the original_tool's
        # return value (FunctionTool / CallableTool), NEVER synthesize a
        # decorator — otherwise the in-process facade re-exports + Layer-3
        # RPC firewall break. inspect.isroutine matches functions and methods
        # (the only things fastmcp's tool() accepts as fn), not strings or
        # CallableTool instances.
        if args and inspect.isroutine(args[0]):
            fn = args[0]
            rest_args = args[1:]
            explicit_name = kwargs.get("name")
            instrumented_fn = instrument(fn, name=explicit_name)
            return original_tool(instrumented_fn, *rest_args, **kwargs)

        # Decorator pattern: @mcp.tool() / @mcp.tool('alias') / @mcp.tool(name='alias').
        # cc-main crack #1 (2026-06-11T06:45Z): FastMCP's tool(name=...) accepts
        # name as the first POSITIONAL STRING too.
        positional_name = args[0] if args and isinstance(args[0], str) else None
        explicit_name = kwargs.get("name") or positional_name

        decorator = original_tool(*args, **kwargs)

        def wrapping_decorator(func):
            instrumented = instrument(func, name=explicit_name)
            return decorator(instrumented)

        return wrapping_decorator

    mcp.tool = patched_tool
    mcp._nucleus_instrumentation_installed = True

    _is_quiet = any(a in sys.argv for a in ("-q", "--quiet", "--json", "json"))
    if not _is_quiet:
        print("[NUCLEUS] tool-call instrumentation installed (JSONL @ .brain/instrumentation/)", file=sys.stderr)
