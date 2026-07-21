"""
Nucleus Runtime - Common Utilities
==================================
Shared utilities and constants for the Nucleus runtime.
"""

import os
import json
import logging
import shutil
import sqlite3
import sys
from contextvars import ContextVar
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    # Type-only: runtime.project is imported lazily inside function bodies
    # (mirrors get_brain_path) so the flag-OFF path never loads the detector.
    from mcp_server_nucleus.runtime.project import ProjectInfo

# ============================================================
# STRUCTURED LOGGING SYSTEM (AG-010)
# ============================================================

class JSONFormatter(logging.Formatter):
    """Formats log records as JSON objects for machine readability."""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_nucleus_logging(name: str = "nucleus", level: int = logging.INFO):
    """Setup structured logging for a component."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # stderr, not stdout: stdio MCP transport reads newline-delimited
        # JSON-RPC from stdout. A log line like "2026-04-14 10:45:20 - …"
        # parses "2026" as a 4-char JSON number, then chokes on "-" at
        # position 4 → "Unexpected non-whitespace character after JSON
        # at position 4 (line 1 column 5)" on the client side.
        handler = logging.StreamHandler(sys.stderr)
        
        # Use JSON if specified via env
        if os.environ.get("NUCLEUS_LOG_JSON", "false").lower() == "true":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        logger.addHandler(handler)
    return logger

# Common logger
logger = setup_nucleus_logging()


# ============================================================
# PROJECT SPINE FLAG (ADR-0042)
# ============================================================
# Gates the D1 precedence inversion in get_brain_path(). Default OFF; when
# OFF the check short-circuits here without importing runtime.project, so
# get_brain_path stays byte-identical to its pre-spine behavior. Idiom mirrors
# NUCLEUS_MEMORY_SOR (memory/facade.py, runtime/memory.py).
_PROJECT_SPINE_FLAG = "NUCLEUS_PROJECT_SPINE"
_PROJECT_SPINE_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _project_spine_on() -> bool:
    """True iff ``NUCLEUS_PROJECT_SPINE`` is set truthy (default False)."""
    return os.environ.get(_PROJECT_SPINE_FLAG, "").strip().lower() in _PROJECT_SPINE_TRUTHY


# ============================================================
# SHARED SQLITE CONCURRENCY POSTURE
# ============================================================
# Primary-store hardening (runtime/db.py SQLiteBackend._get_conn): WAL lets
# concurrent readers coexist with one writer, busy_timeout makes writers wait on
# a lock instead of raising immediately, synchronous=NORMAL is durable enough
# under WAL while faster than FULL. Secondary stores (vector_store, audit_log)
# route their connects through open_hardened_sqlite() to inherit this posture.
_SQLITE_HARDENING_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA busy_timeout=5000",
    "PRAGMA synchronous=NORMAL",
)
_sqlite_pragma_warned = False


def open_hardened_sqlite(
    db_path: Union[str, Path],
    *,
    timeout: float = 10,
    check_same_thread: bool = True,
) -> sqlite3.Connection:
    """Open a SQLite connection with the primary-store concurrency posture.

    ``connect(timeout=10)`` + WAL + ``busy_timeout=5000`` + ``synchronous=NORMAL``
    — the same hardening ``runtime/db.py`` applies to the primary store — so
    concurrent writers wait on the lock rather than failing with
    ``database is locked``.

    PRAGMA application degrades gracefully: on a read-only filesystem WAL cannot
    create the ``-wal``/``-shm`` sidecars, so a PRAGMA failure is logged once and
    the (still usable) connection is returned in whatever journal mode the DB
    already has, rather than raising. Default ``isolation_level`` is preserved so
    ``with open_hardened_sqlite(p) as conn:`` keeps committing on block exit.
    """
    conn = sqlite3.connect(str(db_path), timeout=timeout, check_same_thread=check_same_thread)
    global _sqlite_pragma_warned
    try:
        for pragma in _SQLITE_HARDENING_PRAGMAS:
            conn.execute(pragma)
    except sqlite3.Error as exc:  # pragma: no cover - read-only-FS degrade path
        if not _sqlite_pragma_warned:
            logger.warning("SQLite PRAGMA hardening skipped (%s); continuing", exc)
            _sqlite_pragma_warned = True
    return conn


def get_nucleus_bin_path() -> str:
    """Return the directory containing the nucleus executable."""
    nucleus_bin = shutil.which("nucleus")
    if nucleus_bin:
        return str(Path(nucleus_bin).resolve().parent)
    # Fallback: same directory as the running Python interpreter
    return str(Path(sys.executable).resolve().parent)


def get_nucleus_mcp_command() -> list:
    """Return the command list for MCP config. Prefers nucleus-mcp binary (full path)."""
    bin_path = shutil.which("nucleus-mcp")
    if bin_path:
        return [str(Path(bin_path).resolve())]
    # Fallback: exact python that has nucleus installed + module
    return [sys.executable, "-m", "mcp_server_nucleus"]


# ── Per-request tenant brain path (async-safe) ───────────────────────────
#
# ContextVar that holds the brain path for the current async request context.
# Set by NucleusTenantMiddleware on each HTTP request; checked by
# get_brain_path() BEFORE os.environ so concurrent multi-tenant requests
# on a single process don't cross-read each other's brains.
#
# os.environ is process-wide and races under async interleaving (one tenant's
# await-point yields to another tenant's request, which overwrites the env
# var; the first tenant resumes and reads the wrong brain). ContextVar is
# per-async-task — each request keeps its own value across await points.
#
# CLI/stdio mode: the contextvar is never set, so get_brain_path() falls
# through to os.environ as before. Backward compatible.
_tenant_brain_path: ContextVar[Optional[str]] = ContextVar(
    "nucleus_tenant_brain_path", default=None
)


def set_tenant_brain_path(path: Optional[str]) -> None:
    """Set the per-request brain path contextvar.

    Called by NucleusTenantMiddleware.dispatch() after resolving the tenant.
    Pass None to clear (middleware does this in a finally block after the
    request completes to prevent contextvar leakage).
    """
    _tenant_brain_path.set(path)


# ── Project ContextVar (ADR-0042 D6 — entrypoint lifecycle) ──────────────
#
# THE single process/request-scoped ContextVar that carries the detected
# project (``runtime.project.ProjectInfo``) for the current context. Set once
# per process at entrypoint init by ``init_project_context()`` — which
# ``_ensure_initialized()`` (the unified stdio/http/cli-schema entry contract)
# calls under ``NUCLEUS_PROJECT_SPINE``. It is orthogonal to
# ``_tenant_brain_path``: that var carries the per-request *brain path* (managed
# by the HTTP tenant middleware, unchanged here); this one carries project
# *identity*.
#
# #653 root cause: a bare ``from common import _current_project`` in a consumer
# module snapshots the reference at that module's import time and reads a stale
# value. The var is therefore module-private and reached ONLY through
# ``get_current_project()`` / ``set_current_project()`` — never from-imported.
#
# Flag OFF ⇒ ``init_project_context()`` returns before this var is ever set from
# detection ⇒ it stays at its ``None`` default and no consumer diverges:
# byte-identical to pre-spine startup.
_current_project: "ContextVar[Optional[ProjectInfo]]" = ContextVar(
    "nucleus_current_project", default=None
)


def get_current_project() -> "Optional[ProjectInfo]":
    """Return the current context's detected project, or ``None`` when unset.

    THE accessor for the project ContextVar. Consumers MUST call this instead
    of from-importing ``_current_project`` (the #653 stale-reference trap).
    ``None`` whenever detection declined or the flag is OFF.
    """
    return _current_project.get()


def set_current_project(project: "Optional[ProjectInfo]") -> None:
    """Set the project ContextVar for the current context.

    Called by ``init_project_context()`` at per-process entrypoint init, and
    available to the HTTP tenant middleware for per-request set/clear. Pass
    ``None`` to clear.
    """
    _current_project.set(project)


def init_project_context() -> None:
    """Populate the project ContextVar from cwd detection (ADR-0042 D6).

    Called once per process by ``_ensure_initialized()`` — the unified
    entrypoint contract shared by stdio ``main()``, the HTTP
    ``build_app()``/``main()``, and the ``nucleus schema`` (cli-schema) export.
    Under ``NUCLEUS_PROJECT_SPINE`` it resolves the project owning
    ``Path.cwd()`` and stores it; a declined detection (no project root) leaves
    the var at its ``None`` default so the env var stays authoritative.

    Flag OFF ⇒ returns immediately WITHOUT importing ``runtime.project`` and
    WITHOUT touching the ContextVar ⇒ byte-identical to pre-spine startup. The
    ``runtime.project`` import is function-local (mirrors ``get_brain_path``) so
    the OFF path never loads the detection module.
    """
    if not _project_spine_on():
        return
    from mcp_server_nucleus.runtime.project import resolve_project

    proj = resolve_project(Path.cwd())
    if proj is not None:
        set_current_project(proj)


def get_brain_path() -> Path:
    """Get the brain path for the current request context.

    Resolution order:
      1. Per-request contextvar (set by tenant middleware; async-safe)
      2. Project detection from cwd (ADR-0042 D2; flag NUCLEUS_PROJECT_SPINE)
      3. NUCLEUS_BRAIN_PATH env var (process-wide; races under concurrency)
      4. Auto-detect .brain in cwd or parent directories

    The contextvar takes precedence because it is the only mechanism that
    is safe under concurrent multi-tenant async requests on a single
    process. os.environ is process-wide and can be overwritten by a
    different tenant's request during an await-point yield.

    Under NUCLEUS_PROJECT_SPINE (default OFF), project detection is inserted
    below the contextvar and above the env var (ADR-0042 D1 precedence
    inversion: local project context beats a global env pin). Flag OFF => this
    function's behavior is byte-identical to before; the detection layer is
    never entered and its module is never imported.
    """
    # 1. Per-request contextvar (async-safe, set by tenant middleware)
    brain_path = _tenant_brain_path.get()
    if brain_path:
        path = Path(brain_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                for subdir in ["engrams", "ledger", "sessions", "memory",
                              "tasks", "artifacts", "proofs", "strategy",
                              "governance", "channels", "federation"]:
                    (path / subdir).mkdir(exist_ok=True)
                logger.info(f"Auto-created brain directory at {path}")
            except OSError as e:
                raise ValueError(f"Brain path does not exist and could not be created: {brain_path} ({e})")
        return path

    # 2. Project detection from cwd (ADR-0042 D1/D2, flag-gated).
    #    Lazy import inside the guard so the OFF path never touches project.py.
    if _project_spine_on():
        from mcp_server_nucleus.runtime.project import resolve_project

        proj = resolve_project(Path.cwd())
        if proj is not None and proj.brain_root.exists():
            # Diverge from the env pin only when a real project brain exists.
            env_brain = os.environ.get("NUCLEUS_BRAIN_PATH")
            if env_brain and Path(env_brain).resolve() != proj.brain_root.resolve():
                # Silent-skip policy: state what won, what lost, and why.
                logger.warning(
                    "NUCLEUS_BRAIN_PATH (%s) overridden by detected project "
                    "%s at %s (NUCLEUS_PROJECT_SPINE on)",
                    env_brain, proj.slug, proj.brain_root,
                )
            return proj.brain_root
        # proj is None or its brain is absent → fall through to env/cwd,
        # unchanged from today.

    # 3. Process-wide env vars (races under concurrent multi-tenant load;
    #    safe for CLI/stdio single-tenant mode)
    brain_path = os.environ.get("NUCLEUS_BRAIN_PATH")

    if brain_path:
        path = Path(brain_path)
        if not path.exists():
            # Auto-create brain directory structure instead of crashing
            try:
                path.mkdir(parents=True, exist_ok=True)
                for subdir in ["engrams", "ledger", "sessions", "memory",
                              "tasks", "artifacts", "proofs", "strategy",
                              "governance", "channels", "federation"]:
                    (path / subdir).mkdir(exist_ok=True)
                logger.info(f"Auto-created brain directory at {path}")
            except OSError as e:
                raise ValueError(f"Brain path does not exist and could not be created: {brain_path} ({e})")
        return path

    # Smart fallback: Find .brain in cwd or parent directories
    cwd = Path.cwd()
    if (cwd / ".brain").exists():
        return cwd / ".brain"

    for parent in cwd.parents:
        if (parent / ".brain").exists():
            return parent / ".brain"

    # If we get here, no brain was found
    raise ValueError("NUCLEUS_BRAIN_PATH environment variable not set and no .brain directory found in current or parent directories.")

def make_response(success: bool, data=None, error=None, error_code=None):
    """Standardized API response formatter.
    
    Args:
        success: Whether the operation succeeded
        data: Successful payload (dict, list, string)
        error: Error message if failed
        error_code: Optional short code for error (e.g. ERR_NOT_FOUND)
    
    Returns:
        JSON string matching Nucleus Standard Response Schema
    """
    return json.dumps({
        "success": success,
        "data": data,
        "error": error,
        "error_code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }, indent=2)

def _get_state(path: Optional[str] = None) -> Dict:
    """Core logic for getting state."""
    try:
        brain = get_brain_path()
        state_path = brain / "ledger" / "state.json"
        
        if not state_path.exists():
            return {}
            
        from .sync_ops import sync_lock
        with sync_lock(brain, timeout=2):
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
        if path:
            keys = path.split('.')
            val = state
            for k in keys:
                val = val.get(k, {})
            return val
            
        return state
    except Exception as e:
        logger.error(f"Error reading state: {e}")
        return {}

def _update_state(updates: Dict[str, Any]) -> str:
    """Core logic for updating state."""
    try:
        brain = get_brain_path()
        state_path = brain / "ledger" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        from .sync_ops import sync_lock
        with sync_lock(brain, timeout=5):
            current_state = {}
            if state_path.exists():
                with open(state_path, "r", encoding="utf-8") as f:
                    current_state = json.load(f)
            
            current_state.update(updates)
            
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(current_state, f, indent=2, ensure_ascii=False)
            
        return "State updated successfully"
    except Exception as e:
        return f"Error updating state: {str(e)}"
# ============================================================
# MOCK MCP SERVER (For fallback/verification mode)
# ============================================================

class MockMCP:
    """Mock FastMCP server for when the package is not installed."""
    def tool(self, *args, **kwargs):
        def decorator(f): return f
        return decorator
    def resource(self, *args, **kwargs):
        def decorator(f): return f
        return decorator
    def prompt(self, *args, **kwargs):
        def decorator(f): return f
        return decorator
    def run(self):
        pass
