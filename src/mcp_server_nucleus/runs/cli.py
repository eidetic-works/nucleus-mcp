"""Minimal `nucleus work` CLI surface for the Renaissance run engine."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import shutil
import subprocess
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .dispatcher import RunDispatcher
from .mcp_adapter import RunMcpAdapter
from .models import ProductCaseState
from .product_loop import ProductLoopController
from .store import RunStore


_TERMINAL_STATES = frozenset(
    {
        "ready_for_review",
        "completed",
        "failed",
        "cancelled",
        "dismissed",
        "applied",
        "previewed",
    }
)

_ACTIVE_STATES = frozenset({"preparing", "running", "verifying"})

_PRODUCT_CASE_TERMINAL_STATES = frozenset(
    {
        ProductCaseState.BASELINE_ACCEPTED,
        ProductCaseState.LIMITATION_RECORDED,
        ProductCaseState.RETAINED,
        ProductCaseState.REJECTED,
    }
)

_HUMAN_DECISION_ACTIONS = frozenset({"request-baseline-decision", "request-decision"})

_EVOLVE_LOOP_MAX_CONSECUTIVE_ERRORS = 3

# An in-process executor binds the run's lifetime to the invoker: when the
# caller exits, the run orphans mid-flight and the case spins forever. Evolve
# baselines are unattended by construction, so they default to a detached
# subprocess worker that survives the invoker. Explicit `--target` still wins.
_DEFAULT_EVOLVE_EXECUTION_TARGET = "subprocess"


def _adapter(brain_path: Path) -> RunMcpAdapter:
    db = brain_path / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    return RunMcpAdapter(db)


def _brain_path() -> Path:
    from mcp_server_nucleus.runtime.common import get_brain_path

    return Path(get_brain_path())


def _pidfile_path() -> Path:
    return _brain_path() / "dispatcher.pid"


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _format_run(run: dict) -> str:
    return f"{run['id'][:8]}  {run['state']:16}  {run['runner_id']}  {run['created_at']}"


def _run_daemon(pidfile: Path, db_path: Path) -> int:
    """Run the dispatcher in the current process until stopped."""
    stop = threading.Event()
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(str(os.getpid()))

    def _on_sigterm(signum: int, frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _on_sigterm)

    def _watch_pidfile() -> None:
        while not stop.is_set():
            if not pidfile.exists():
                stop.set()
                break
            time.sleep(0.5)

    watcher = threading.Thread(target=_watch_pidfile, daemon=True)
    watcher.start()

    dispatcher = RunDispatcher(db_path)
    try:
        dispatcher.serve(stop)
    finally:
        pidfile.unlink(missing_ok=True)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    runs = adapter.list_runs(args.conversation)
    if not runs:
        print("No runs found.")
        return 0
    for run in runs:
        print(_format_run(run))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    data = adapter.show_run(args.run_id)
    bundle = data.get("bundle", {})
    # Expose the full evidence bundle, not a stripped subset.
    data["bundle"] = {
        "status": bundle.get("status"),
        "verdict": bundle.get("verdict"),
        "warning": bundle.get("warning"),
        "reason": bundle.get("reason"),
        "apply_eligible": bundle.get("apply_eligible"),
        "diff_sha256": bundle.get("diff_sha256"),
        "diff_size": bundle.get("diff_size"),
        "is_clean": bundle.get("is_clean"),
        "base_revision": bundle.get("base_revision"),
        "patch": bundle.get("patch"),
        "test_report": bundle.get("test_report"),
        "stdout_log": bundle.get("stdout_log"),
        "stderr_log": bundle.get("stderr_log"),
        "work_log": bundle.get("work_log"),
        "route": bundle.get("route"),
        "usage": bundle.get("usage"),
        "metadata": bundle.get("metadata"),
        "unknowns": bundle.get("unknowns"),
    }
    print(json.dumps(data, indent=2, default=str))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Human-readable review of a run's evidence and outcome."""
    adapter = _adapter(_brain_path())
    data = adapter.show_run(args.run_id)
    run = data.get("run", {})
    bundle = data.get("bundle", {})

    state = run.get("state", "unknown")
    verdict = bundle.get("verdict", "unknown")
    reason = bundle.get("reason")
    apply_eligible = bundle.get("apply_eligible", False)
    diff_size = bundle.get("diff_size", 0)
    diff_sha = bundle.get("diff_sha256", "")
    has_patch = bool(bundle.get("patch"))
    has_test_report = bool(bundle.get("test_report"))
    warning = bundle.get("warning", False)

    print(f"{'=' * 60}")
    print(f"  Run {run.get('id', '?')[:12]}")
    print(f"  State:         {state}")
    print(f"  Verdict:       {verdict}")
    if reason:
        print(f"  Reason:        {reason}")
    if warning:
        print(f"  Warning:       execution issue (see events)")
    print(f"  Apply eligible: {apply_eligible}")
    print(f"{'=' * 60}")
    print(f"  Diff size:     {diff_size} bytes")
    if diff_sha:
        print(f"  Diff SHA-256:  {diff_sha[:24]}...")
    print(f"  Patch stored:  {'yes' if has_patch else 'no'}")
    print(f"  Test report:   {'yes' if has_test_report else 'no'}")
    print(f"{'=' * 60}")

    # Show runner/route info
    route = bundle.get("route", {})
    if route:
        print(f"  Runner:        {route.get('vendor', '?')}")
        print(f"  Model:         {route.get('model', '?')}")
        print(f"  Target:        {route.get('execution_target', '?')}")
        print(f"  Trust policy:  {route.get('policy', '?')}")

    # Show requirements if present
    requirements = run.get("requirements")
    if requirements:
        try:
            req = json.loads(requirements)
            check = req.get("check", {})
            if check:
                print(f"{'=' * 60}")
                print(f"  Approved check: {' '.join(check.get('argv', []))}")
                print(f"  Check timeout:  {check.get('timeout', '?')}s")
        except (json.JSONDecodeError, TypeError):
            pass

    print(f"{'=' * 60}")

    # Next action guidance
    if state == "ready_for_review":
        if apply_eligible:
            print(f"  Next: `nucleus work apply {args.run_id}` to apply the checked diff")
        else:
            print("  Next: review evidence; apply is blocked (not eligible)")
    elif state == "applied":
        print("  This run has been applied.")
    elif state == "failed":
        print(f"  Next: inspect events with `nucleus work show {args.run_id}`")
    elif state == "cancelled":
        print("  Run was cancelled.")
    print(f"{'=' * 60}")

    return 0 if state in ("ready_for_review", "applied", "completed") else 1


def cmd_create(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    if args.project_root:
        project_id = adapter.create_project(args.project_root, trust_mode=args.trust_mode)
        conversation_id = adapter.create_conversation(project_id, args.prompt or "CLI")
    elif args.conversation:
        conversation_id = args.conversation
    else:
        print("error: --conversation or --project-root is required", file=sys.stderr)
        return 1
    run_id = adapter.create_run(
        conversation_id=conversation_id,
        prompt=args.prompt,
        runner_id=args.runner,
        model_id=args.model or "",
        execution_target=args.target,
        mode=args.mode,
        idempotency_key=args.idempotency or "",
    )
    print(run_id)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    resp = adapter.apply_run(args.run_id)
    print(resp.to_json())
    return 0 if resp.success else 1


def cmd_dismiss(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    resp = adapter.dismiss_run(args.run_id)
    print(resp.to_json())
    return 0 if resp.success else 1


def cmd_preview(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    try:
        adapter._store.get_run(args.run)
    except ValueError:
        print(f"Run {args.run} not found.", file=sys.stderr)
        return 1
    artifacts = adapter._store.list_artifacts(args.run)
    preview = next((a for a in artifacts if a.mime_type == "text/x-preview-url"), None)
    if preview is None:
        print(
            f"No preview URL captured for run {args.run}.",
            file=sys.stderr,
        )
        return 1
    url = preview.metadata.get("url")
    if not url:
        print(f"Preview artifact for run {args.run} has no URL.", file=sys.stderr)
        return 1
    print(url)
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    brain = _brain_path()
    db = brain / "runs" / "store.sqlite"
    if not db.exists():
        print(f"No database found at {db}", file=sys.stderr)
        return 1

    backup_dir = Path(args.output) if args.output else brain / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"store-{timestamp}.sqlite"

    try:
        shutil.copy2(db, dest)
    except Exception as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"backup_path": str(dest), "source": str(db)}))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    try:
        data = adapter.export_run(args.run_id)
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2, default=str))
        print(json.dumps({"output": str(output)}))
    else:
        print(json.dumps(data, indent=2, default=str))
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    resp = adapter.cancel_run(args.run_id)
    print(resp.to_json())
    return 0 if resp.success else 1


def cmd_submit(args: argparse.Namespace) -> int:
    """One-command workflow: create, dispatch, follow, and print a receipt.

    This is the pilot's primary user-facing command.  It:
    1. Preflight checks the project (HEAD, cleanliness, runner).
    2. Creates a project, conversation, and run with optional requirements.
    3. Dispatches exactly that run through the engine.
    4. Streams live output until the run reaches a terminal state.
    5. Prints a structured receipt with the final state and evidence summary.
    """
    brain = _brain_path()
    db_path = brain / "runs" / "store.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    adapter = _adapter(brain)
    service = adapter._service

    # 1. Build check argv if provided.
    check_argv = None
    if args.check:
        import shlex as _shlex
        check_argv = _shlex.split(args.check)

    # 2. Submit through RunService (includes preflight).
    if args.project_root:
        run_id, reason = service.submit_run(
            project_root=args.project_root,
            prompt=args.prompt,
            runner_id=args.runner,
            model_id=args.model or "",
            execution_target=args.target,
            mode=args.mode,
            trust_mode=args.trust_mode,
            check_argv=check_argv,
            check_name=args.check_name,
            check_timeout=args.check_timeout,
            idempotency_key=args.idempotency or "",
        )
    elif args.conversation:
        # Use existing conversation — skip preflight, create run directly.
        run_id = adapter.create_run(
            conversation_id=args.conversation,
            prompt=args.prompt,
            runner_id=args.runner,
            model_id=args.model or "",
            execution_target=args.target,
            mode=args.mode,
            idempotency_key=args.idempotency or "",
            requirements=json.dumps({
                "check": {
                    "name": args.check_name or "approved_check",
                    "argv": check_argv,
                    "timeout": args.check_timeout,
                }
            }) if check_argv else None,
        )
        reason = ""
    else:
        print("error: --conversation or --project-root is required", file=sys.stderr)
        return 1

    if run_id is None:
        print(f"error: preflight blocked: {reason}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"run_id": run_id, "state": "queued"}))
    else:
        print(f"Run {run_id} queued")

    # 3. Dispatch exactly this run.
    dispatcher = RunDispatcher(db_path)
    dispatcher.run_once(run_id=run_id)

    after_state = adapter._store.get_run(run_id).state.value
    if after_state == "queued":
        print(f"Run {run_id} was not dispatched (still queued)", file=sys.stderr)
        return 1

    # 4. Follow live output until terminal, with Ctrl+C handling.
    if not args.no_follow:
        try:
            _follow_run(run_id, adapter)
        except KeyboardInterrupt:
            print("\n^C — requesting cancellation...", file=sys.stderr)
            adapter.cancel_run(run_id)
            # Wait briefly for cancellation to take effect.
            for _ in range(50):
                st = adapter._store.get_run(run_id).state.value
                if st in _TERMINAL_STATES:
                    break
                time.sleep(0.1)
            print("Cancelled.", file=sys.stderr)
            return 130

    # 5. Print the receipt.
    final_state = adapter._store.get_run(run_id).state.value
    bundle_data = adapter.show_run(run_id).get("bundle", {})

    receipt = {
        "run_id": run_id,
        "state": final_state,
        "apply_eligible": bundle_data.get("apply_eligible", False),
        "verdict": bundle_data.get("verdict", "unknown"),
        "diff_size": bundle_data.get("diff_size", 0),
        "diff_sha256": bundle_data.get("diff_sha256", ""),
        "has_patch": bool(bundle_data.get("patch")),
        "has_test_report": bool(bundle_data.get("test_report")),
        "reason": bundle_data.get("reason"),
        "warning": bundle_data.get("warning", False),
    }

    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print(f"\n--- Receipt ---")
        print(f"Run:    {run_id}")
        print(f"State:  {final_state}")
        print(f"Verdict: {receipt['verdict']}")
        if receipt["reason"]:
            print(f"Reason: {receipt['reason']}")
        print(f"Apply eligible: {receipt['apply_eligible']}")
        print(f"Diff size: {receipt['diff_size']} bytes")
        if receipt["diff_sha256"]:
            print(f"Diff sha256: {receipt['diff_sha256'][:16]}...")
        print(f"Patch: {'yes' if receipt['has_patch'] else 'no'}")
        print(f"Test report: {'yes' if receipt['has_test_report'] else 'no'}")

    # Exit code: 0 for ready_for_review/applied/completed, 1 for failed/cancelled
    return 0 if final_state in ("ready_for_review", "applied", "completed") else 1


def cmd_run(args: argparse.Namespace) -> int:
    brain = _brain_path()
    db_path = brain / "runs" / "store.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    adapter = _adapter(brain)
    before = {r["id"]: r["state"] for r in adapter.list_runs()}

    if args.run:
        if before.get(args.run) != "queued":
            print(
                f"Run {args.run} is not queued (state: {before.get(args.run)})",
                file=sys.stderr,
            )
            return 1

    dispatcher = RunDispatcher(db_path)
    if args.run:
        dispatcher.run_once(run_id=args.run)
    else:
        dispatcher.run_once()

    after = {r["id"]: r["state"] for r in adapter.list_runs()}
    dispatched_ids = [
        rid
        for rid, before_state in before.items()
        if before_state == "queued" and after.get(rid) != "queued"
    ]

    if args.run:
        if args.run not in dispatched_ids:
            print(f"Run {args.run} was not dispatched", file=sys.stderr)
            return 1
        print(f"Dispatched {args.run} (state: {after[args.run]})")
        if args.follow:
            return _follow_run(args.run, adapter)
        return 0

    print(f"Dispatched {len(dispatched_ids)} run(s)")
    if dispatched_ids:
        print(" ".join(dispatched_ids))
    if args.follow:
        if len(dispatched_ids) == 1:
            return _follow_run(dispatched_ids[0], adapter)
        print(
            "error: --follow requires --run when multiple runs are dispatched",
            file=sys.stderr,
        )
        return 1
    return 0


def _follow_run(run_id: str, adapter: RunMcpAdapter) -> int:
    """Follow run output using cursor-based event reads (no full-history reload)."""
    last_seq = 0
    while True:
        try:
            run = adapter._store.get_run(run_id)
        except Exception as exc:
            print(f"Run not found: {exc}", file=sys.stderr)
            return 1

        # Read only new events since last cursor.
        for ev in adapter._store.list_events(run_id, after_seq=last_seq):
            last_seq = ev.seq
            if ev.type == "run.output":
                payload = ev.payload or {}
                chunk = payload.get("chunk", "")
                if chunk:
                    print(chunk, end="")

        if run.state.value in _TERMINAL_STATES:
            break

        time.sleep(0.2)

    return 0


def cmd_start(args: argparse.Namespace) -> int:
    brain = _brain_path()
    pidfile = _pidfile_path()

    if args.daemon:
        return _run_daemon(pidfile, brain / "runs" / "store.sqlite")

    if pidfile.exists():
        try:
            pid = int(pidfile.read_text().strip())
            if _is_process_alive(pid):
                print(f"Dispatcher already running (PID {pid})", file=sys.stderr)
                return 1
        except Exception:
            pass
        pidfile.unlink(missing_ok=True)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)

    if shutil.which("nucleus"):
        cmd = ["nucleus", "work", "start", "--daemon"]
    else:
        cmd = [sys.executable, "-m", "mcp_server_nucleus.cli", "work", "start", "--daemon"]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(50):
        if pidfile.exists():
            break
        if proc.poll() is not None:
            print("Dispatcher process exited early.", file=sys.stderr)
            return 1
        time.sleep(0.1)

    if pidfile.exists():
        daemon_pid = int(pidfile.read_text().strip())
    else:
        daemon_pid = proc.pid
        pidfile.write_text(str(daemon_pid))

    print(f"Dispatcher started (PID {daemon_pid})")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    pidfile = _pidfile_path()

    if not pidfile.exists():
        print("No dispatcher running")
        return 0

    try:
        pid = int(pidfile.read_text().strip())
    except Exception as exc:
        print(f"Invalid pidfile: {exc}", file=sys.stderr)
        pidfile.unlink(missing_ok=True)
        return 1

    if not _is_process_alive(pid):
        print(f"Process {pid} not running (stale pidfile).")
        pidfile.unlink(missing_ok=True)
        return 0

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print(f"Process {pid} not running.")
        pidfile.unlink(missing_ok=True)
        return 0
    except Exception as exc:
        print(f"Failed to stop dispatcher: {exc}", file=sys.stderr)
        return 1

    for _ in range(50):
        if not _is_process_alive(pid):
            break
        time.sleep(0.1)

    pidfile.unlink(missing_ok=True)
    print(f"Dispatcher stopped (PID {pid})")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    pidfile = _pidfile_path()
    running = False
    pid = None

    if pidfile.exists():
        try:
            pid = int(pidfile.read_text().strip())
            running = _is_process_alive(pid)
        except Exception:
            pass

    adapter = _adapter(_brain_path())
    in_flight = [r for r in adapter.list_runs() if r["state"] in _ACTIVE_STATES]

    print(f"Dispatcher running: {running}" + (f" (PID {pid})" if pid else ""))
    print(f"In-flight runs: {len(in_flight)}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    adapter = _adapter(_brain_path())
    seen: set[int] = set()

    while True:
        try:
            data = adapter.show_run(args.run_id)
        except Exception as exc:
            print(f"Run not found: {exc}", file=sys.stderr)
            return 1

        for ev in data["events"]:
            if ev["seq"] not in seen:
                seen.add(ev["seq"])
                if args.text:
                    if ev.get("type") == "run.output":
                        payload = ev.get("payload") or {}
                        chunk = payload.get("chunk", "")
                        if chunk:
                            print(chunk, end="")
                else:
                    print(json.dumps(ev, default=str))

        if data["run"]["state"] in _TERMINAL_STATES:
            break

        time.sleep(0.2)

    return 0


def _check_python() -> tuple[bool, str, str]:
    v = sys.version_info
    fix = "Use python3.10 or newer."
    if v >= (3, 10):
        return True, f"{v.major}.{v.minor}.{v.micro}", fix
    return False, f"Python {v.major}.{v.minor}.{v.micro} is too old", fix


def _check_agent_client_protocol() -> tuple[bool, str, str]:
    fix = "pip install agent-client-protocol==0.12.1"
    try:
        v = version("agent-client-protocol")
    except PackageNotFoundError:
        return False, "agent-client-protocol is not installed", fix
    if v == "0.12.1":
        return True, v, fix
    return False, f"agent-client-protocol version is {v} (expected 0.12.1)", fix


def _check_git() -> tuple[bool, str, str]:
    fix = "Install git."
    cmd = shutil.which("git")
    if not cmd:
        return False, "git is not on PATH", fix
    try:
        proc = subprocess.run(
            [cmd, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return False, str(exc), fix
    if proc.returncode == 0:
        return True, "", fix
    return False, f"git --version exited {proc.returncode}", fix


def _check_sandbox_exec() -> tuple[bool, str, str]:
    fix = "Sandbox is unavailable; strict trust mode will require approval."
    if shutil.which("sandbox-exec"):
        return True, "", fix
    return False, "sandbox-exec is not on PATH", fix


def _check_scripts() -> tuple[bool, str, str]:
    fix = "Reinstall package with `pip install -e mcp-server-nucleus`."
    scripts = ("nucleus-work", "nucleus-acp", "nucleus-run-worker")
    missing = [s for s in scripts if not shutil.which(s)]
    if not missing:
        return True, "", fix
    return False, f"missing scripts: {', '.join(missing)}", fix


def _check_vendor_cli() -> tuple[bool, str, str]:
    fix = "Install at least one vendor CLI and authenticate."
    for cmd in ("agy", "devin"):
        if not shutil.which(cmd):
            continue
        for arg in ("--version", "version"):
            try:
                proc = subprocess.run(
                    [cmd, arg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if proc.returncode == 0:
                    return True, f"{cmd} {arg}", fix
            except Exception:
                pass
    return False, "no vendor CLI found on PATH", fix


def _check_acp() -> tuple[bool, str, str]:
    fix = "Reinstall package with `pip install -e mcp-server-nucleus`."
    cmd = shutil.which("nucleus-acp")
    if not cmd:
        return False, "nucleus-acp is not on PATH", fix
    try:
        proc = subprocess.run(
            [cmd, "--check"],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip() or "ok", fix
        return False, f"nucleus-acp --check exited {proc.returncode}", fix
    except Exception as exc:
        return False, str(exc), fix


def _check_disk_space() -> tuple[bool, str, str]:
    fix = "Free up disk space or set NUCLEUS_BRAIN_PATH to a volume with more room."
    try:
        brain = _brain_path()
        brain.parent.mkdir(parents=True, exist_ok=True)
        st = os.statvfs(brain)
        free_gb = (st.f_bavail * st.f_frsize) / (1024**3)
        if free_gb < 0.5:
            return False, f"only {free_gb:.2f} GiB free", fix
        return True, f"{free_gb:.2f} GiB free", fix
    except Exception as exc:
        return False, str(exc), fix


def _check_dispatcher() -> tuple[bool, str, str]:
    fix = "Run `nucleus work start` to start the dispatcher."
    pidfile = _pidfile_path()
    if not pidfile.exists():
        return False, "no pidfile found", fix
    try:
        pid = int(pidfile.read_text().strip())
    except Exception as exc:
        return False, f"invalid pidfile: {exc}", fix
    if _is_process_alive(pid):
        return True, f"PID {pid}", fix
    return False, f"pidfile points to dead process {pid}", fix


def _check_brain_writable() -> tuple[bool, str, str]:
    fix = "Set NUCLEUS_BRAIN_PATH to a writable directory."
    try:
        brain = _brain_path()
    except Exception as exc:
        return False, str(exc), fix
    if brain.exists() and brain.is_dir() and os.access(brain, os.W_OK):
        return True, str(brain), fix
    return False, f"{brain} does not exist or is not writable", fix


def _check_store_openable() -> tuple[bool, str, str]:
    fix = "Run `nucleus work list` to init the store."
    try:
        brain = _brain_path()
    except Exception as exc:
        return False, str(exc), fix
    if not (brain.exists() and os.access(brain, os.W_OK)):
        return False, "brain path does not exist or is not writable", fix
    try:
        _adapter(brain)
        return True, "", fix
    except Exception as exc:
        return False, str(exc), fix


def cmd_serve(args: argparse.Namespace) -> int:
    brain = _brain_path()
    adapter = _adapter(brain)
    from .api import build_app  # lazy import: HTTP deps are optional
    import uvicorn

    app = build_app(adapter, brain_path=brain)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    from .workspace import _workspace_root

    ws_root = _workspace_root()
    store = RunStore(str(_brain_path() / "runs" / "store.sqlite"))
    cutoff = time.time() - args.days * 86400
    removed, kept, freed_bytes = [], [], 0
    for entry in sorted(ws_root.glob("nucleus-run-*")):
        run_id = entry.name[len("nucleus-run-"):]
        try:
            run = store.get_run(run_id)
        except ValueError:
            kept.append(run_id)
            continue
        if run.state.value not in _TERMINAL_STATES:
            kept.append(run_id)
            continue
        if entry.stat().st_mtime > cutoff:
            kept.append(run_id)
            continue
        size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
        freed_bytes += size
        removed.append(run_id)
        if not args.dry_run:
            shutil.rmtree(entry)
            store.append_event(
                run_id,
                "run.workspace_gc",
                {"workspace": str(entry), "freed_bytes": size},
            )
    print(
        json.dumps(
            {
                "workspace_root": str(ws_root),
                "days": args.days,
                "dry_run": args.dry_run,
                "removed": removed,
                "kept": kept,
                "freed_bytes": freed_bytes,
            }
        )
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = [
        ("python", _check_python),
        ("agent-client-protocol", _check_agent_client_protocol),
        ("git", _check_git),
        ("sandbox-exec", _check_sandbox_exec),
        ("scripts", _check_scripts),
        ("vendor_cli", _check_vendor_cli),
        ("acp", _check_acp),
        ("brain_writable", _check_brain_writable),
        ("disk_space", _check_disk_space),
        ("store_openable", _check_store_openable),
        ("dispatcher", _check_dispatcher),
    ]
    all_pass = True
    for name, fn in checks:
        passed, message, fix = fn()
        if passed:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}: {message}  fix: {fix}")
            all_pass = False
    return 0 if all_pass else 1


def _evolve_next(controller: ProductLoopController, store: RunStore, case_id: str) -> dict:
    """Advance a product case by one step if its current state allows it."""
    # A baseline or replay run whose executor died leaves the run active
    # forever, so the case would spin on "none" until a human noticed. Sweep
    # abandoned runs to FAILED first: a terminal run is something the case can
    # classify.
    store.recover_abandoned_runs()
    case = store.get_product_case(case_id)
    state = case.state
    if state is ProductCaseState.WAITING_FOR_GOAL:
        goal = store.claim_next_goal(case.project_root, case_id)
        if goal is None:
            return {"action": "none", "state": state.value, "reason": "NO_QUEUED_GOAL"}
        try:
            run_id = controller.start_baseline(
                case_id,
                goal["goal_source"],
                goal["goal"],
                goal["permitted_paths"],
                goal["acceptance_check"],
                runner_id=goal["runner_id"],
                model_id=goal["model_id"],
                execution_target=goal["execution_target"] or _DEFAULT_EVOLVE_EXECUTION_TARGET,
                trust_mode=goal["trust_mode"],
                mode=goal["mode"],
                check_timeout=goal["check_timeout"],
            )
        except Exception:
            store.mark_goal_failed(goal["id"])
            raise
        store.mark_goal_done(goal["id"])
        return {
            "action": "start-baseline",
            "state": store.get_product_case(case_id).state.value,
            "run_id": run_id,
            "goal_id": goal["id"],
        }
    if state is ProductCaseState.BASELINE_RUNNING:
        run = store.get_run(case.baseline_run_id) if case.baseline_run_id else None
        if run is None or run.state.value not in _TERMINAL_STATES:
            return {"action": "none", "state": state.value, "reason": "BASELINE_RUN_NOT_TERMINAL"}
        challenge = controller.request_baseline_decision(case_id)
        return {
            "action": "request-baseline-decision",
            "state": store.get_product_case(case_id).state.value,
            "challenge": challenge,
        }
    if state is ProductCaseState.FRICTION_CLASSIFIED:
        if case.failure_owner == "PRODUCT":
            return {
                "action": "none",
                "state": state.value,
                "reason": "PRODUCT_FRICTION_REQUIRES_IMPROVEMENT",
            }
        return {"action": "record-limitation", "state": controller.record_limitation(case_id)}
    if state is ProductCaseState.IMPROVEMENT_REVIEWED:
        run_id = controller.start_replay(case_id)
        return {
            "action": "replay",
            "state": store.get_product_case(case_id).state.value,
            "run_id": run_id,
        }
    if state is ProductCaseState.REPLAY_RUNNING:
        run = store.get_run(case.replay_run_id) if case.replay_run_id else None
        if run is None or run.state.value not in _TERMINAL_STATES:
            return {"action": "none", "state": state.value, "reason": "REPLAY_RUN_NOT_TERMINAL"}
        new_state = controller.evaluate_replay(case_id, 0)
        return {
            "action": "evaluate-replay",
            "state": new_state,
            "run_id": case.replay_run_id,
        }
    if state is ProductCaseState.HUMAN_REVIEW:
        challenge = controller.request_decision(case_id)
        return {
            "action": "request-decision",
            "state": store.get_product_case(case_id).state.value,
            "challenge": challenge,
        }
    return {"action": "none", "state": state.value}


def _evolve_loop(
    controller: ProductLoopController,
    store: RunStore,
    case_id: str,
    interval: float = 5.0,
    max_steps: int = 100,
    sleep=time.sleep,
) -> int:
    """Repeatedly advance a product case, one `_evolve_next` step at a time.

    Stops when the case reaches a terminal state, when a step asks a human to
    decide, or after `max_steps` iterations. Three consecutive failing steps
    re-raise the last exception so the caller reports it.
    """
    consecutive_errors = 0
    for step in range(max_steps):
        if step:
            sleep(interval)
        try:
            result = _evolve_next(controller, store, case_id)
        except Exception:
            consecutive_errors += 1
            if consecutive_errors >= _EVOLVE_LOOP_MAX_CONSECUTIVE_ERRORS:
                raise
            continue
        consecutive_errors = 0
        print(json.dumps({"ok": True, "result": result}, default=str), flush=True)
        if result.get("action") in _HUMAN_DECISION_ACTIONS:
            return 0
        if store.get_product_case(case_id).state in _PRODUCT_CASE_TERMINAL_STATES:
            return 0
    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    brain = _brain_path()
    db_path = brain / "runs" / "store.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = RunStore(str(db_path))
    product_root = getattr(args, "product_root", None) or os.getcwd()
    controller = ProductLoopController(store, db_path, product_root)
    try:
        if args.evolve_action == "init":
            result = {"case_id": controller.initialize(args.project_root)}
        elif args.evolve_action == "start":
            result = {
                "run_id": controller.start_baseline(
                    args.case_id,
                    args.goal_source,
                    args.goal,
                    args.files,
                    shlex.split(args.check),
                    runner_id=args.runner,
                    model_id=args.model,
                    execution_target=args.target,
                    trust_mode=args.trust_mode,
                    mode=args.mode,
                    check_timeout=args.check_timeout,
                )
            }
        elif args.evolve_action == "queue":
            result = {
                "goal_id": store.enqueue_goal(
                    args.project_root,
                    args.goal,
                    goal_source=args.goal_source,
                    permitted_paths=args.files,
                    acceptance_check=shlex.split(args.check),
                    runner_id=args.runner,
                    model_id=args.model,
                    execution_target=args.target,
                    trust_mode=args.trust_mode,
                    mode=args.mode,
                    check_timeout=args.check_timeout,
                )
            }
        elif args.evolve_action == "evaluate-baseline":
            accepted = {"true": True, "false": False}.get(args.accepted)
            result = controller.evaluate_baseline(
                args.case_id,
                accepted,
                args.interventions,
                failure_owner=args.owner,
                friction=args.friction,
            )
        elif args.evolve_action == "record-limitation":
            result = {"state": controller.record_limitation(args.case_id)}
        elif args.evolve_action == "attach-improvement":
            result = {"run_id": controller.attach_improvement(args.case_id, args.run_id)}
        elif args.evolve_action == "approve-improvement":
            result = controller.approve_improvement(
                args.case_id,
                args.review_event_seq,
                shlex.split(args.regression),
                timeout=args.timeout,
            )
        elif args.evolve_action == "replay":
            result = {"run_id": controller.start_replay(args.case_id)}
        elif args.evolve_action == "evaluate-replay":
            result = {"state": controller.evaluate_replay(args.case_id, args.interventions)}
        elif args.evolve_action == "request-baseline-decision":
            result = {"challenge": controller.request_baseline_decision(args.case_id)}
        elif args.evolve_action == "next":
            if getattr(args, "loop", False):
                return _evolve_loop(
                    controller,
                    store,
                    args.case_id,
                    interval=args.interval,
                    max_steps=args.max_steps,
                )
            result = _evolve_next(controller, store, args.case_id)
        elif args.evolve_action == "status":
            result = controller.status(args.case_id, args.project_root)
        elif args.evolve_action == "history":
            case = store.get_product_case(args.case_id)
            result = {
                "case_id": case.id,
                "events": [
                    {
                        "seq": event.seq,
                        "type": event.type,
                        "payload": event.payload,
                        "created_at": event.created_at.isoformat(),
                    }
                    for event in store.list_product_case_events(case.id)
                ],
            }
        else:
            raise ValueError("UNKNOWN_EVOLVE_ACTION")
        print(json.dumps({"ok": True, "result": result}, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "reason": str(exc)}))
        return 1
    finally:
        store.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nucleus work")
    subparsers = parser.add_subparsers(dest="action", required=True)

    list_parser = subparsers.add_parser("list", help="List runs")
    list_parser.add_argument("--conversation", default=None, help="Filter by conversation ID")

    show_parser = subparsers.add_parser("show", help="Show a run (JSON)")
    show_parser.add_argument("run_id", help="Run ID")

    review_parser = subparsers.add_parser("review", help="Human-readable review of a run")
    review_parser.add_argument("run_id", help="Run ID")

    create_parser = subparsers.add_parser("create", help="Create and queue a run")
    create_parser.add_argument("--conversation", default=None, help="Conversation ID")
    create_parser.add_argument("--project-root", default=None, help="Project root (creates project and conversation)")
    create_parser.add_argument("--prompt", default="", help="Prompt text")
    create_parser.add_argument("--runner", default="agy", help="Runner/vendor ID")
    create_parser.add_argument("--model", default=None, help="Model ID")
    create_parser.add_argument("--target", default="in-process", choices=["in-process", "subprocess", "mac-sandbox", "hosted"], help="Execution target")
    create_parser.add_argument("--trust-mode", default="default", choices=["permissive", "default", "strict"], help="Project trust mode when creating a project")
    create_parser.add_argument("--mode", default="write", choices=["read", "write"])
    create_parser.add_argument("--idempotency", default=None, help="Idempotency key")

    submit_parser = subparsers.add_parser("submit", help="One-command: create, dispatch, follow, and print a receipt")
    submit_parser.add_argument("--conversation", default=None, help="Existing conversation ID")
    submit_parser.add_argument("--project-root", default=None, help="Project root (creates project and conversation)")
    submit_parser.add_argument("--prompt", default="", help="Prompt text")
    submit_parser.add_argument("--runner", default="agy", help="Runner/vendor ID")
    submit_parser.add_argument("--model", default=None, help="Model ID")
    submit_parser.add_argument("--target", default="in-process", choices=["in-process", "subprocess", "mac-sandbox", "hosted"], help="Execution target")
    submit_parser.add_argument("--trust-mode", default="default", choices=["permissive", "default", "strict"], help="Project trust mode when creating a project")
    submit_parser.add_argument("--mode", default="write", choices=["read", "write"])
    submit_parser.add_argument("--idempotency", default=None, help="Idempotency key")
    submit_parser.add_argument("--check", default=None, help="Check command to run for verification (shell-quoted)")
    submit_parser.add_argument("--check-name", default=None, help="Name for the check verifier")
    submit_parser.add_argument("--check-timeout", type=int, default=300, help="Check command timeout in seconds")
    submit_parser.add_argument("--no-follow", action="store_true", help="Do not stream live output")
    submit_parser.add_argument("--json", action="store_true", help="Output structured JSON")

    apply_parser = subparsers.add_parser("apply", help="Apply a run's diff to the base")
    apply_parser.add_argument("run_id", help="Run ID")

    dismiss_parser = subparsers.add_parser("dismiss", help="Dismiss a run")
    dismiss_parser.add_argument("run_id", help="Run ID")

    preview_parser = subparsers.add_parser("preview", help="Print the captured preview URL for a run")
    preview_parser.add_argument("--run", required=True, help="Run ID")

    cancel_parser = subparsers.add_parser("cancel", help="Request cancellation of a run")
    cancel_parser.add_argument("run_id", help="Run ID")

    run_parser = subparsers.add_parser("run", help="Run the dispatcher once")
    run_parser.add_argument("--run", default=None, help="Execute a specific run ID")
    run_parser.add_argument("--follow", "-f", action="store_true", help="Stream run.output chunks in real time after dispatch")

    start_parser = subparsers.add_parser("start", help="Start a background dispatcher daemon")
    start_parser.add_argument("--daemon", action="store_true", help=argparse.SUPPRESS)
    start_parser.add_argument("--pidfile", default=None, help=argparse.SUPPRESS)

    stop_parser = subparsers.add_parser("stop", help="Stop the background dispatcher daemon")

    status_parser = subparsers.add_parser("status", help="Show dispatcher status")

    watch_parser = subparsers.add_parser("watch", help="Watch a run until it reaches a terminal state")
    watch_parser.add_argument("run_id", help="Run ID")
    watch_parser.add_argument("--text", "-t", action="store_true", help="Print only chunk text from run.output events")

    backup_parser = subparsers.add_parser("backup", help="Back up the run database")
    backup_parser.add_argument("--output", default=None, help="Optional backup directory (defaults to brain/backups)")

    export_parser = subparsers.add_parser("export", help="Export a run and its records to JSON")
    export_parser.add_argument("run_id", help="Run ID")
    export_parser.add_argument("--output", default=None, help="Output file (stdout if omitted)")

    serve_parser = subparsers.add_parser("serve", help="Run the headless HTTP API")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    serve_parser.add_argument("--port", type=int, default=8080, help="Bind port")
    serve_parser.add_argument("--log-level", default="info", help="Uvicorn log level")

    gc_parser = subparsers.add_parser(
        "gc", help="Reclaim workspaces of terminal runs older than --days"
    )
    gc_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Only prune workspaces whose mtime is older than this many days (0 = all terminal)",
    )
    gc_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be pruned without deleting",
    )

    subparsers.add_parser("doctor", help="Run environment health checks")

    evolve_parser = subparsers.add_parser("evolve", help="Run the product evolution loop")
    evolve_subparsers = evolve_parser.add_subparsers(dest="evolve_action", required=True)

    evolve_init = evolve_subparsers.add_parser("init")
    evolve_init.add_argument("--project-root", required=True)
    evolve_init.add_argument("--product-root", default=os.getcwd())

    evolve_start = evolve_subparsers.add_parser("start")
    evolve_start.add_argument("case_id")
    evolve_start.add_argument("--goal-source", required=True)
    evolve_start.add_argument("--goal", required=True)
    evolve_start.add_argument("--file", dest="files", action="append", required=True)
    evolve_start.add_argument("--check", required=True)
    evolve_start.add_argument("--runner", default="")
    evolve_start.add_argument("--model", default="")
    evolve_start.add_argument("--target", default=_DEFAULT_EVOLVE_EXECUTION_TARGET)
    evolve_start.add_argument("--trust-mode", default="default")
    evolve_start.add_argument("--mode", default="write")
    evolve_start.add_argument("--check-timeout", type=int, default=300)

    evolve_queue = evolve_subparsers.add_parser(
        "queue", help="Enqueue a goal for an unattended `evolve next` to claim"
    )
    evolve_queue.add_argument("--project-root", required=True)
    evolve_queue.add_argument("--goal-source", required=True)
    evolve_queue.add_argument("--goal", required=True)
    evolve_queue.add_argument("--file", dest="files", action="append", required=True)
    evolve_queue.add_argument("--check", required=True)
    evolve_queue.add_argument("--runner", default="")
    evolve_queue.add_argument("--model", default="")
    evolve_queue.add_argument("--target", default=_DEFAULT_EVOLVE_EXECUTION_TARGET)
    evolve_queue.add_argument("--trust-mode", default="default")
    evolve_queue.add_argument("--mode", default="write")
    evolve_queue.add_argument("--check-timeout", type=int, default=300)
    evolve_queue.add_argument("--product-root", default=os.getcwd())

    evolve_baseline = evolve_subparsers.add_parser("evaluate-baseline")
    evolve_baseline.add_argument("case_id")
    evolve_baseline.add_argument("--accepted", required=True, choices=["false"])
    evolve_baseline.add_argument("--interventions", required=True, type=int)
    evolve_baseline.add_argument("--owner")
    evolve_baseline.add_argument("--friction")

    evolve_limitation = evolve_subparsers.add_parser("record-limitation")
    evolve_limitation.add_argument("case_id")

    evolve_attach = evolve_subparsers.add_parser("attach-improvement")
    evolve_attach.add_argument("case_id")
    evolve_attach.add_argument("run_id")
    evolve_attach.add_argument("--product-root", default=os.getcwd())

    evolve_approve = evolve_subparsers.add_parser("approve-improvement")
    evolve_approve.add_argument("case_id")
    evolve_approve.add_argument("--review-event-seq", required=True, type=int)
    evolve_approve.add_argument("--regression", required=True)
    evolve_approve.add_argument("--timeout", type=int, default=300)
    evolve_approve.add_argument("--product-root", default=os.getcwd())

    evolve_replay = evolve_subparsers.add_parser("replay")
    evolve_replay.add_argument("case_id")
    evolve_replay.add_argument("--product-root", default=os.getcwd())

    evolve_evaluate_replay = evolve_subparsers.add_parser("evaluate-replay")
    evolve_evaluate_replay.add_argument("case_id")
    evolve_evaluate_replay.add_argument("--interventions", required=True, type=int)
    evolve_evaluate_replay.add_argument("--product-root", default=os.getcwd())

    evolve_baseline_decision = evolve_subparsers.add_parser("request-baseline-decision")
    evolve_baseline_decision.add_argument("case_id")
    evolve_baseline_decision.add_argument("--product-root", default=os.getcwd())

    evolve_next = evolve_subparsers.add_parser(
        "next", help="Advance the product case by one step if its state allows it"
    )
    evolve_next.add_argument("case_id")
    evolve_next.add_argument("--product-root", default=os.getcwd())
    evolve_next.add_argument(
        "--loop",
        action="store_true",
        default=False,
        help="Keep stepping until a terminal state, a human decision, repeated errors, or --max-steps",
    )
    evolve_next.add_argument(
        "--interval", type=float, default=5, help="Seconds to sleep between loop steps"
    )
    evolve_next.add_argument(
        "--max-steps", type=int, default=100, help="Maximum number of loop steps to perform"
    )

    evolve_status = evolve_subparsers.add_parser("status")
    evolve_status.add_argument("case_id", nargs="?")
    evolve_status.add_argument("--project-root")
    evolve_status.add_argument("--product-root", default=os.getcwd())

    evolve_history = evolve_subparsers.add_parser("history", help="Print the product case event log as JSON")
    evolve_history.add_argument("case_id")
    evolve_history.add_argument("--product-root", default=os.getcwd())

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["--help"]
    args = parser.parse_args(argv)
    action = globals()[f"cmd_{args.action}"]
    return action(args)


if __name__ == "__main__":
    sys.exit(main())
