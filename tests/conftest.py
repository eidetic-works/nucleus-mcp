"""
Nucleus Test Suite — conftest.py
================================
Global test configuration to prevent hanging and ensure fixture isolation.

Fixes the full-suite hang (1191 tests).
Root cause: resource contention makes some tests excessively slow when
run together, causing the suite to appear "hung". Timeout prevents this.

v0.3.1 addition: subprocess_runner fixture for one-shot subprocess
lifecycle testing (per cc-peer 2026-06-09T13:15Z Q4 STRONG-CONCUR +
review-tooling recalibration). USE FOR any module whose production
lifecycle differs from pytest (one-shot hooks, daemons, disk-persistent
state that must survive process boundaries).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Tuple

import pytest

# ──────────────────────────────────────────────────────────────
# Skip tests that import symbols not yet shipped to this branch
# ──────────────────────────────────────────────────────────────
collect_ignore_glob = [
    "test_coder_agent.py",
    "test_fixer_loop.py",
    "test_fluid_sync.py",
]


# ──────────────────────────────────────────────────────────────
# Global timeout: No single test should take more than 30 seconds
# ──────────────────────────────────────────────────────────────
def pytest_collection_modifyitems(items):
    """Apply a 30-second timeout to every test that doesn't have one."""
    for item in items:
        if not any(marker.name == "timeout" for marker in item.iter_markers()):
            item.add_marker(pytest.mark.timeout(30))


# ──────────────────────────────────────────────────────────────
# Ensure NUCLEUS_BRAIN_PATH is set for tests that need it
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _ensure_brain_path(tmp_path, monkeypatch):
    """Always set a temporary brain path for tests.

    Sets BOTH NUCLEUS_BRAIN_PATH and NUCLEAR_BRAIN_PATH (legacy alias) to
    the same temp dir so all code paths use the isolated brain.
    """
    test_brain = tmp_path / "_nucleus_test_brain"
    test_brain.mkdir(exist_ok=True)
    (test_brain / "ledger").mkdir(exist_ok=True)
    (test_brain / "engrams").mkdir(exist_ok=True)
    (test_brain / "sessions").mkdir(exist_ok=True)
    (test_brain / "memory").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(test_brain))
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(test_brain))
    yield
    # Clean up circuit breaker registry to prevent test order dependencies
    try:
        from mcp_server_nucleus.runtime.circuit_breaker import _breakers
        _breakers.clear()
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# nest_asyncio isolation: production code (brain_ops.py, swarm.py)
# calls nest_asyncio.apply() which globally patches asyncio with no
# undo. This corrupts the event loop for subsequent TestClient tests.
# Save/restore the patched functions around each test.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _undo_nest_asyncio():
    """Save and restore asyncio attributes that nest_asyncio patches.

    nest_asyncio.apply() patches:
    - asyncio.run, get_event_loop (module level)
    - asyncio.Task, Future (replaced with pure Python versions)
    - asyncio._nest_patched flag
    - Event loop policy's get_event_loop method
    - Event loop class's run_until_complete, run_forever, _run_once

    The pure-Python Task/Future replacements break anyio (used by
    Starlette's TestClient) with AttributeError: 'NoneType' object has
    no attribute 'set_name'. The policy/class-level patches persist across
    tests and corrupt all subsequent async test infrastructure.
    """
    import asyncio
    import asyncio.events as events
    import asyncio.tasks as tasks_mod
    import asyncio.futures as futures_mod
    saved_run = asyncio.run
    saved_get_event_loop = asyncio.get_event_loop
    saved_get_running_loop = asyncio.get_running_loop
    saved_Task = asyncio.Task
    saved_Future = asyncio.Future
    saved_nest_patched = getattr(asyncio, "_nest_patched", None)
    # Save tasks/futures submodule attributes that nest_asyncio swaps
    saved_tasks_Task = tasks_mod.Task
    saved_tasks_CTask = getattr(tasks_mod, "_CTask", None)
    saved_futures_Future = futures_mod.Future
    saved_futures_CFuture = getattr(futures_mod, "_CFuture", None)
    # Save events module get_event_loop
    saved_events_get_event_loop = events.get_event_loop
    saved_events__get_event_loop = getattr(events, "_get_event_loop", None)
    # Save the event loop policy and its class's get_event_loop method
    saved_policy = asyncio.get_event_loop_policy()
    policy_cls = type(saved_policy)
    saved_policy_get_event_loop = policy_cls.get_event_loop
    # Save the event loop class methods (patched on the class, not instance)
    _probe_loop = asyncio.new_event_loop()
    loop_cls = type(_probe_loop)
    _probe_loop.close()
    saved_run_until_complete = loop_cls.run_until_complete
    saved_run_forever = loop_cls.run_forever
    saved__run_once = loop_cls._run_once
    saved__check_running = loop_cls._check_running
    saved__num_runs_pending = getattr(loop_cls, "_num_runs_pending", None)
    saved__is_proactorloop = getattr(loop_cls, "_is_proactorloop", None)
    saved__nest_patched_loop = getattr(loop_cls, "_nest_patched", None)
    saved__set_coroutine_origin_tracking = getattr(loop_cls, "_set_coroutine_origin_tracking", None)
    yield
    # Restore module-level attributes
    asyncio.run = saved_run
    asyncio.get_event_loop = saved_get_event_loop
    asyncio.get_running_loop = saved_get_running_loop
    asyncio.Task = saved_Task
    asyncio.Future = saved_Future
    # Restore tasks/futures submodule attributes
    tasks_mod.Task = saved_tasks_Task
    if saved_tasks_CTask is not None:
        tasks_mod._CTask = saved_tasks_CTask
    futures_mod.Future = saved_futures_Future
    if saved_futures_CFuture is not None:
        futures_mod._CFuture = saved_futures_CFuture
    # Restore events module get_event_loop
    events.get_event_loop = saved_events_get_event_loop
    if saved_events__get_event_loop is not None:
        events._get_event_loop = saved_events__get_event_loop
    if saved_nest_patched is None:
        if hasattr(asyncio, "_nest_patched"):
            del asyncio._nest_patched
    else:
        asyncio._nest_patched = saved_nest_patched
    # Restore event loop policy class method
    policy_cls.get_event_loop = saved_policy_get_event_loop
    # Restore event loop class methods
    loop_cls.run_until_complete = saved_run_until_complete
    loop_cls.run_forever = saved_run_forever
    loop_cls._run_once = saved__run_once
    loop_cls._check_running = saved__check_running
    if saved__num_runs_pending is not None:
        loop_cls._num_runs_pending = saved__num_runs_pending
    if saved__is_proactorloop is not None:
        loop_cls._is_proactorloop = saved__is_proactorloop
    if saved__nest_patched_loop is not None:
        loop_cls._nest_patched = saved__nest_patched_loop
    elif hasattr(loop_cls, "_nest_patched"):
        del loop_cls._nest_patched
    if saved__set_coroutine_origin_tracking is not None:
        loop_cls._set_coroutine_origin_tracking = saved__set_coroutine_origin_tracking


# ──────────────────────────────────────────────────────────────
# FS-mode isolation: a shell with NUCLEUS_RELAY_URL exported (Mac
# HTTP flip) silently routes relay code paths to the HTTP branch and
# breaks FS-mode assertions. Tests that exercise HTTP mode opt back
# in via monkeypatch.setenv, which runs after this autouse delenv.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clean_relay_env(monkeypatch):
    """Each test starts with NUCLEUS_RELAY_URL, BEARER, SENDER_ANCHOR, and
    ARTIFACT_REF_VENDOR_DERIVED unset.

    The sender anchor flag (NUCLEUS_RELAY_SENDER_ANCHOR) and artifact_ref
    vendor-derived flag (NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED) are set in the
    live environment but break relay/vendor tests that use caller-provided
    values. Tests that specifically test these features re-enable them via
    monkeypatch.setenv.
    """
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_SENDER_ANCHOR", raising=False)
    monkeypatch.delenv("NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED", raising=False)
    # Session-type env vars — tests that need them re-enable via monkeypatch.setenv
    monkeypatch.delenv("NUCLEUS_SESSION_TYPE", raising=False)
    monkeypatch.delenv("GEMINI_CLI", raising=False)
    monkeypatch.delenv("WINDSURF_SESSION", raising=False)
    monkeypatch.delenv("CURSOR_SESSION", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_SESSION", raising=False)
    monkeypatch.delenv("CLAUDE_DESKTOP", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_INFER_SENDER", raising=False)
    # Agent registry override — if set, find_session_in_ancestry() can
    # find sessions from a previous test's registry, breaking session
    # type detection.
    monkeypatch.delenv("NUCLEUS_AGENT_REGISTRY", raising=False)


# ──────────────────────────────────────────────────────────────
# Render API key isolation: ensure RENDER_API_KEY doesn't leak
# between tests. Some tests set it via monkeypatch (which auto-cleans),
# but belt-and-suspenders: delete it before every test.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clean_render_env(monkeypatch):
    """Each test starts with RENDER_API_KEY unset."""
    monkeypatch.delenv("RENDER_API_KEY", raising=False)


# ──────────────────────────────────────────────────────────────
# sync_ops global state isolation: _current_identity is a module-level
# global that leaks between tests. Reset it before every test.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_sync_ops_identity():
    """Reset sync_ops._current_identity to None before each test."""
    try:
        import mcp_server_nucleus.runtime.sync_ops as sync_mod
        sync_mod._current_identity = None
    except Exception:
        pass
    yield


# ──────────────────────────────────────────────────────────────
# Tenant ContextVar isolation: _tenant_brain_path is a module-level
# ContextVar in common.py that can leak between tests if a prior test
# sets it (via set_tenant_brain_path or the tenant middleware) and
# doesn't clean up. When leaked, get_brain_path() returns the stale
# ContextVar value instead of NUCLEUS_BRAIN_PATH, causing tests that
# rely on env-var-based brain path resolution to search the wrong
# directory (e.g. test_recall_beats_grep ripgrep sanity check fails).
# Reset it before and after every test.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_tenant_contextvar():
    """Clear the _tenant_brain_path ContextVar before and after each test."""
    try:
        from mcp_server_nucleus.runtime.common import set_tenant_brain_path
        set_tenant_brain_path(None)
    except Exception:
        pass
    yield
    try:
        from mcp_server_nucleus.runtime.common import set_tenant_brain_path
        set_tenant_brain_path(None)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# Project ContextVar isolation (ADR-0042 D6): _current_project is a
# module-level ContextVar in common.py set at entrypoint init under
# NUCLEUS_PROJECT_SPINE. A test that flips the flag ON and drives an
# entrypoint (or init_project_context) leaves it populated; clear it
# before and after every test so it never leaks a stale project.
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_project_contextvar():
    """Clear the _current_project ContextVar before and after each test."""
    try:
        from mcp_server_nucleus.runtime.common import set_current_project
        set_current_project(None)
    except Exception:
        pass
    yield
    try:
        from mcp_server_nucleus.runtime.common import set_current_project
        set_current_project(None)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# sys.modules pollution cleanup
# test_stripe_billing.py and test_license_elt.py do module-level
# _load() calls that replace sys.modules entries for
# mcp_server_nucleus.runtime.identity.keygen with manually-loaded
# copies. This leaks into subsequent tests (nuke_protocol, emergence_rate,
# orchestration) that depend on the real module.
#
# We snapshot the identity-related sys.modules entries ONCE at conftest
# import time (before any test modules are collected/imported) and restore
# from that clean snapshot after every test, preventing cross-test pollution.
#
# NOTE: mcp_server_nucleus.runtime.common is intentionally EXCLUDED —
# preserving it causes ContextVar issues because re-imported modules
# create new ContextVar objects while existing references still point
# to the old ones.
# ──────────────────────────────────────────────────────────────
_PRESERVED_MODULE_PREFIXES = (
    "mcp_server_nucleus.runtime.identity",
    "mcp_server_nucleus.runtime.license",
    "mcp_server_nucleus.runtime.stripe_billing",
    "mcp_server_nucleus.tools.orchestration",
)

# Snapshot once at conftest import — this is BEFORE pytest collects any
# test modules, so sys.modules still has the real (unpolluted) entries.
_CLEAN_MODULE_SNAPSHOT = {}
for _key, _mod in list(sys.modules.items()):
    if _key.startswith(_PRESERVED_MODULE_PREFIXES):
        _CLEAN_MODULE_SNAPSHOT[_key] = _mod


@pytest.fixture(autouse=True)
def _restore_identity_modules():
    """Restore identity-related sys.modules entries from the clean snapshot."""
    yield
    # Restore: remove any new/modified entries, restore from clean snapshot
    for key in list(sys.modules.keys()):
        if key.startswith(_PRESERVED_MODULE_PREFIXES):
            if key in _CLEAN_MODULE_SNAPSHOT:
                sys.modules[key] = _CLEAN_MODULE_SNAPSHOT[key]
            else:
                del sys.modules[key]


# ──────────────────────────────────────────────────────────────
# v0.3.1 — subprocess_runner fixture for one-shot lifecycle tests
# Per cc-peer 2026-06-09T13:15Z Q4 STRONG-CONCUR + review-tooling
# recalibration. Spawns a fresh Python subprocess + runs arbitrary
# module code + returns (exit_code, stdout, stderr). Use for any
# module whose production lifecycle differs from pytest (one-shot
# hooks, daemons, disk-persistent state across process boundaries).
# ──────────────────────────────────────────────────────────────
def _spawn_python_subprocess(
    code: str,
    *,
    env_overrides: dict = None,
    timeout: float = 30.0,
) -> Tuple[int, str, str]:
    """Spawn a fresh Python subprocess running `code` via `python -c`."""
    env = os.environ.copy()
    if env_overrides:
        env.update({k: str(v) for k, v in env_overrides.items()})
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def subprocess_runner() -> Callable[..., Tuple[int, str, str]]:
    """Fixture returning a Python-subprocess spawn helper.

    Returns a callable (code: str, *, env_overrides: dict | None,
    timeout: float) -> (exit_code, stdout, stderr).

    Use to verify behavior that requires a clean Python process — e.g.,
    coalesce_queue state-across-invocations, hook.py one-shot
    subprocess lifecycle, daemon-vs-one-shot transitions.
    """
    return _spawn_python_subprocess


# ──────────────────────────────────────────────────────────────
# Session-scoped safety nets for OS-level test residue
#
# Two full-suite landmines empirically observed:
#   1. chflags uchg locks left under the pytest tmp root break the
#      numbered-dir GC on the *next* run ("Operation not permitted"),
#      after which every tmp_path fixture errors with FileNotFoundError.
#   2. chief/coordinator tests that reach the tmux spawn boundary leak a
#      live detached `tmux new-session -d -s chief_<slug>_<pid>` that
#      outlives the suite (one accumulates per run).
# These session-scoped finalizers guarantee cleanup even if an individual
# test crashes mid-flight (fixture teardown still runs at session end).
# ──────────────────────────────────────────────────────────────
def _chflags_available() -> bool:
    return sys.platform == "darwin" and shutil.which("chflags") is not None


@pytest.fixture(scope="session", autouse=True)
def _unlock_pytest_basetemp(tmp_path_factory):
    """At session end, recursively clear chflags uchg locks under this run's
    pytest basetemp so the next run's tmp-root GC never hits a locked file."""
    yield
    if not _chflags_available():
        return
    basetemp = tmp_path_factory.getbasetemp()
    subprocess.run(
        ["chflags", "-R", "nouchg", str(basetemp)],
        check=False,
        capture_output=True,
    )


# Coordinator tmux sessions are named chief_<task_slug>_<pid> by the chief
# command (default-task slug is "autonomic_direc"). Only sessions matching
# this prefix that appear DURING the test session are reaped, so a
# pre-existing operator session is never touched.
_COORDINATOR_SESSION_PREFIX = "chief_"


def _list_tmux_sessions() -> set:
    """Return the set of current tmux session names (empty if tmux absent)."""
    if shutil.which("tmux") is None:
        return set()
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return set()
    # A non-zero rc with "no server running" just means there are no sessions.
    return {ln.strip() for ln in result.stdout.splitlines() if ln.strip()}


@pytest.fixture(scope="session", autouse=True)
def _reap_leaked_tmux_coordinator_sessions():
    """Kill any coordinator tmux session the suite leaks.

    Snapshot matching sessions before the suite runs; at session end kill only
    the ones that newly appeared. Diffing against the snapshot protects any
    pre-existing operator chief_* session from being reaped."""
    pre_existing = {
        s for s in _list_tmux_sessions()
        if s.startswith(_COORDINATOR_SESSION_PREFIX)
    }
    yield
    leaked = {
        s for s in _list_tmux_sessions()
        if s.startswith(_COORDINATOR_SESSION_PREFIX)
    } - pre_existing
    for name in leaked:
        subprocess.run(
            ["tmux", "kill-session", "-t", name],
            check=False,
            capture_output=True,
        )


# ──────────────────────────────────────────────────────────────
# Tracked .mcp.json guard: the repo-root .mcp.json is git-tracked
# (HEAD:.mcp.json). Tests that exercise _finish_init_with_value or
# the cold-start instrument chdir into tmp_path to avoid touching it,
# but a missing chdir or an incidental CWD write can silently mutate
# the tracked file. Snapshot its bytes before each test and restore
# on teardown so test side effects never corrupt the tracked config.
# Filesystem primitives bound at IMPORT time, before any test can patch them.
#
# test_gcloud_ops_coverage.py monkeypatches os.path.exists globally to return
# False. The guard below runs at teardown and asks the filesystem whether
# .mcp.json still exists -- so a test that stubs out existence checks can make
# the guard report a mutation that never happened. It did: the guard failed 7
# tests over two .mcp.json files that were byte-identical to HEAD the whole
# time, verified independently.
#
# A guard that the code under test can disable is unreliable in BOTH
# directions: it cries wolf here, and a test that patched the same primitive
# while genuinely corrupting the file would be waved through. os.stat is
# captured directly so no later patch of os.path.exists or Path.exists can
# reach it.
@pytest.fixture(autouse=True)
def _restore_nucleus_env():
    """Snapshot and restore every NUCLEUS_*/NUCLEAR_* env var around each test.

    The shape is not "some tests forget to clean up an env var". It is
    "anything running inside a test can mutate this process's environment,
    and monkeypatch will not put it back" -- monkeypatch only restores what
    monkeypatch itself set.

    The measured instance: agent_os/boot.py deliberately sets
    NUCLEUS_VERIFIER_MANDATORY_ANCHORS=1 as a documented one-way ratchet. That
    is correct production behaviour. But once any Agent-OS boot test runs, the
    doctrine stays ON for the rest of the process, so RuleReasoner.adjudicate
    caps later verdicts at PARTIAL and test_verifier.py contributes 6 failures
    to the full run while passing 113/113 alone.

    An earlier version of this fixture restored NUCLEUS_BRAIN_PATH only, and
    its docstring claimed that was "the mechanism behind this suite's
    aggregate-only failures". That claim was wrong -- BRAIN_PATH does leak, but
    fixing it changed the failure count not at all. Restoring the whole
    NUCLEUS_* namespace covers the ratchet, the brain path, and the next
    production ratchet nobody has written yet.

    Scoped to NUCLEUS_* rather than the whole environment: a blanket snapshot
    would also revert PATH/HOME changes that some fixtures make deliberately.
    Restoring cannot break a test that behaves correctly -- it only puts back
    what the test's own execution changed.
    """
    # NUCLEAR_* is the legacy alias for NUCLEUS_* (see runtime/common.py) and
    # is written directly by at least two test files with no restore, so it
    # leaks exactly the same way. Restoring one prefix and not its own alias
    # is a guard with a hole in the shape of the thing it guards.
    _PREFIXES = ("NUCLEUS_", "NUCLEAR_")
    saved = {k: v for k, v in os.environ.items() if k.startswith(_PREFIXES)}
    # CWD is the other process-global a test can move and not put back, and it
    # fails in a way that looks like a product bug rather than a test bug:
    # vendor_dispatch shells out to git, a leaked chdir puts that call outside
    # any repo, the SHA lookup returns nothing, and dispatch correctly FAILS
    # CLOSED with worktree_sha_unavailable -- so the relay envelope is never
    # written and 9 tests assert on an empty list. Nothing in that chain is
    # wrong except the working directory.
    saved_cwd = os.getcwd()
    # logging.disable() is process-global and sticky, and production code calls
    # it legitimately (cli.py silences logging for --json output). One such call
    # in-process mutes caplog for every later test. Restoring it here means a
    # test that triggers that path cannot blind the rest of the run.
    import logging as _lg
    saved_disable = _lg.root.manager.disable
    try:
        yield
    finally:
        try:
            if os.getcwd() != saved_cwd:
                os.chdir(saved_cwd)
        except (FileNotFoundError, OSError):
            # The test deleted the dir it was standing in; getcwd() itself can
            # raise. Restoring is still correct and still possible.
            os.chdir(saved_cwd)
        if _lg.root.manager.disable != saved_disable:
            _lg.disable(saved_disable)
        for k in [k for k in os.environ if k.startswith(_PREFIXES)]:
            if k not in saved:
                os.environ.pop(k, None)
        for k, v in saved.items():
            if os.environ.get(k) != v:
                os.environ[k] = v


_REAL_STAT = os.stat


def _real_exists(path) -> bool:
    """Existence check that cannot be monkeypatched away by a test."""
    try:
        _REAL_STAT(path)
        return True
    except (OSError, ValueError):
        return False


# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _guard_tracked_mcp_json(request):
    """Restore watched .mcp.json files if a test mutates/creates/deletes them, and fail loudly.

    Two git-tracked .mcp.json files are watched: the package-root file
    (``parents[1]``) and the monorepo-root file (``parents[2]``). A test
    that writes .mcp.json to the CWD without first chdir-ing into a tmp
    dir would clobber one or both. Snapshot the pre-test bytes (and
    existed/absent state) per path and restore-or-delete on teardown so
    test side effects never corrupt the tracked configs — but also fail
    the test so the regression is visible, not silently papered over.
    Creation of a previously-absent watched file is treated as a
    violation too, and is deleted on teardown; deletion of a previously
    present watched file is restored on teardown.

    Repo roots are resolved from ``Path(__file__)`` (never ``Path.cwd()``)
    so the guard is immune to a test that chdir-ed away before teardown.
    """
    base = Path(__file__).resolve()
    watched = [base.parents[1] / ".mcp.json", base.parents[2] / ".mcp.json"]
    snapshots = []
    for path in watched:
        existed = _real_exists(path)
        snapshots.append((path, existed, path.read_bytes() if existed else None))
    yield
    violations = []
    for path, existed, saved in snapshots:
        try:
            now_exists = _real_exists(path)
            now_bytes = path.read_bytes() if now_exists else None
            if existed and (not now_exists or now_bytes != saved):
                # mutation or deletion of a previously-present watched file → restore
                mutated_bytes = now_bytes if now_exists else b""
                path.write_bytes(saved)
                violations.append((path, mutated_bytes))
            elif (not existed) and now_exists:
                # creation of a previously-absent watched file → delete
                mutated_bytes = now_bytes or b""
                path.unlink(missing_ok=True)
                violations.append((path, mutated_bytes))
        except Exception:
            pass
    if violations:
        lines = [
            f"\n[tracked .mcp.json guard] test mutated/created/deleted a watched .mcp.json.",
            f"  nodeid     : {request.node.nodeid}",
        ]
        for path, mutated_bytes in violations:
            excerpt = mutated_bytes[:200].decode("utf-8", errors="replace")
            lines.append(f"  abs path   : {path}")
            lines.append(f"  excerpt    : {excerpt!r}")
        lines.append(
            f"  guidance   : the test wrote .mcp.json to the CWD without "
            f"chdir-ing into a tmp dir first. Pin the working directory by "
            f"chdir-ing into tmp_path (or monkeypatch.chdir(tmp_path)) before "
            f"any code path that can write .mcp.json, so the tracked config "
            f"is never the target of an incidental CWD write."
        )
        pytest.fail("\n".join(lines))
