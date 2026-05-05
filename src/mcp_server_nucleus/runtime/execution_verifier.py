"""
Execution Verifier — Frontier 1: GROUND (Machine Truth)
========================================================
Tiered verification of code changes. Breaks Gödel's self-referential trap
by going OUTSIDE the formal system into reality.

Cooper sends signals from inside the black hole.

Tiers:
  0 — Diff non-empty (did anything change?)
  1 — Syntax valid (py_compile, node --check, bash -n)
  2 — Imports work (python -c "import module")
  3 — Tests pass (pytest on related test files)
  4 — Runtime (start server, hit endpoints, verify responses)

Each tier is independent. If a tier can't run, it's skipped (not failed).
Total budget: configurable, default 30s.

This is the canonical engine. scripts/execution_verifier.py re-exports from here.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_execution(git_diff_text: str, pre_head: str, config: dict,
                     project_root: Path) -> dict:
    """Run tiered verification on changed files.

    Returns dict with: verified, tier_reached, tiers_passed, tiers_failed,
    tiers_skipped, signals, duration_s, receipt_id, commit_sha, task_id.
    """
    budget = config.get("execution_verification_timeout_s", 30)
    enabled_tiers = set(config.get("execution_verification_tiers", [0, 1, 2, 3]))
    task = config.get("_current_task", {})

    t0 = time.monotonic()
    signals = []
    tiers_passed = []
    tiers_failed = []
    tiers_skipped = []

    # Get clean file paths
    changed = _get_changed_files(git_diff_text, pre_head, project_root)

    def remaining():
        return max(0, budget - (time.monotonic() - t0))

    # ── Tier 0: diff non-empty ──
    if 0 in enabled_tiers:
        sig = _tier0_diff_nonempty(changed)
        signals.append(sig)
        (tiers_passed if sig["passed"] else tiers_failed).append(0)
    else:
        tiers_skipped.append(0)

    # ── Tier 1: syntax check ──
    if 1 in enabled_tiers and remaining() > 0:
        t1_sigs = _tier1_syntax_check(changed, project_root, remaining())
        signals.extend(t1_sigs)
        if t1_sigs:
            if all(s["passed"] for s in t1_sigs):
                tiers_passed.append(1)
            else:
                tiers_failed.append(1)
        else:
            tiers_skipped.append(1)  # no files to check
    elif 1 not in enabled_tiers:
        tiers_skipped.append(1)

    # ── Tier 2: import check ──
    python_path = config.get("python_path")
    if 2 in enabled_tiers and remaining() > 0:
        py_files = [f for f in changed if f.endswith(".py")]
        t2_sigs = _tier2_import_check(py_files, project_root, remaining(), python_path)
        signals.extend(t2_sigs)
        if t2_sigs:
            if all(s["passed"] for s in t2_sigs):
                tiers_passed.append(2)
            else:
                tiers_failed.append(2)
        else:
            tiers_skipped.append(2)
    elif 2 not in enabled_tiers:
        tiers_skipped.append(2)

    # ── Tier 3: test execution ──
    if 3 in enabled_tiers and remaining() > 0:
        t3_sigs = _tier3_test_execution(changed, task, project_root, remaining(), python_path)
        signals.extend(t3_sigs)
        if t3_sigs:
            if all(s["passed"] for s in t3_sigs):
                tiers_passed.append(3)
            else:
                tiers_failed.append(3)
        else:
            tiers_skipped.append(3)
    elif 3 not in enabled_tiers:
        tiers_skipped.append(3)

    # ── Tier 4: runtime verification ──
    runtime_checks = config.get("execution_verification_runtime_checks", [])
    runtime_budget = config.get("execution_verification_runtime_timeout_s", 15)
    if 4 in enabled_tiers and runtime_checks:
        t4_sigs = _tier4_runtime_check(runtime_checks, project_root, runtime_budget)
        signals.extend(t4_sigs)
        if t4_sigs:
            if all(s["passed"] for s in t4_sigs):
                tiers_passed.append(4)
            else:
                tiers_failed.append(4)
        else:
            tiers_skipped.append(4)
    elif 4 not in enabled_tiers:
        tiers_skipped.append(4)
    elif not runtime_checks:
        tiers_skipped.append(4)

    # ── Tier 5: outcome verification (delta-based) ──
    if 5 in enabled_tiers and remaining() > 0:
        baseline_path = project_root / ".brain" / "driver" / "outcome_baseline.json"
        plan_path = _find_recent_plan(project_root)
        if baseline_path.exists() and plan_path:
            t5_sigs = _tier5_outcome_check(
                plan_path.read_text(), project_root, remaining(), baseline_path,
            )
            signals.extend(t5_sigs)
            if t5_sigs:
                if all(s["passed"] for s in t5_sigs):
                    tiers_passed.append(5)
                else:
                    tiers_failed.append(5)
                # Record goal progress (best-effort)
                try:
                    from .goal_tracker import record_goal_attempt
                    record_goal_attempt(str(plan_path), {}, t5_sigs, project_root)
                except Exception:
                    pass
                # Frontier 4: report Tier 5 outcome to the flywheel — every
                # outcome verification becomes a CSR claim. Best-effort.
                try:
                    from ..flywheel import Flywheel
                    fw = Flywheel(project_root / ".brain")
                    step = f"tier5:{(task or {}).get('id', 'unknown')}"
                    if 5 in tiers_passed:
                        fw.record_survived(phase="ground_tier5", step=step)
                    else:
                        failed_signal = next(
                            (s for s in t5_sigs if not s.get("passed")), {}
                        )
                        fw.file_ticket(
                            step=step,
                            error=str(failed_signal.get("name", "tier5 outcome failed")),
                            logs=json.dumps(failed_signal, default=str)[:1500],
                            phase="ground_tier5",
                        )
                except Exception:
                    pass  # flywheel hook is best-effort
            else:
                tiers_skipped.append(5)
        else:
            tiers_skipped.append(5)  # No baseline or plan = skip, not fail
    elif 5 not in enabled_tiers:
        tiers_skipped.append(5)

    duration = round(time.monotonic() - t0, 2)
    verified = len(tiers_failed) == 0 and len(tiers_passed) > 0

    # Receipt provenance
    commit_sha = ""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                           text=True, timeout=3, cwd=str(project_root))
        commit_sha = r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        pass

    receipt_content = json.dumps(signals, sort_keys=True, default=str) + str(time.time())
    receipt_id = hashlib.sha256(receipt_content.encode()).hexdigest()[:16]

    return {
        "verified": verified,
        "tier_reached": max(tiers_passed) if tiers_passed else -1,
        "tiers_passed": tiers_passed,
        "tiers_failed": tiers_failed,
        "tiers_skipped": tiers_skipped,
        "signals": signals,
        "duration_s": duration,
        "receipt_id": receipt_id,
        "commit_sha": commit_sha,
        "task_id": task.get("id", "") if task else "",
    }


def build_calibration_dpo(task: dict, response: dict,
                          verification_result: dict) -> dict | None:
    """Build DPO pair: confident-wrong vs honestly-uncertain. Gold quality.

    Returns None if verification passed (no calibration needed).
    """
    if verification_result.get("verified", True):
        return None

    failed = [s for s in verification_result.get("signals", [])
              if not s.get("passed", True)]
    if not failed:
        return None

    issues = []
    for sig in failed:
        check = sig.get("check", "unknown")
        target = sig.get("file", sig.get("module", ""))
        err = sig.get("error", "")
        issues.append(f"{check} failed on {target}" + (f": {err}" if err else ""))

    rejected = response.get("result", "")
    chosen = (
        rejected + "\n\n"
        "Note: verification found issues that need to be addressed:\n"
        + "\n".join(f"- {i}" for i in issues)
    )

    return {
        "prompt": task.get("description", ""),
        "chosen": chosen,
        "rejected": rejected,
        "metadata": {
            "source": "calibration_dpo",
            "quality": "gold",
            "verification_failures": [s.get("check", "") for s in failed],
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    }


def detect_runtime_checks(project_root: Path) -> list[dict]:
    """Auto-detect Tier 4 runtime checks based on project type.

    Detects:
      - pyproject.toml with uvicorn/fastapi → FastAPI health check
      - package.json with "start" script → Node.js health check
      - Dockerfile with EXPOSE → Docker health check
    """
    checks = []
    root = Path(project_root)

    # FastAPI / Uvicorn detection
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text().lower()
            if "uvicorn" in content or "fastapi" in content:
                checks.append({
                    "type": "http_health",
                    "cmd": [sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", "0"],
                    "url": "/health",
                    "expect_status": 200,
                    "startup_wait_s": 8,
                    "detected_from": "pyproject.toml",
                })
        except Exception:
            pass

    # Node.js detection
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            if "start" in scripts:
                checks.append({
                    "type": "http_health",
                    "cmd": ["npm", "start"],
                    "url": "/",
                    "expect_status": 200,
                    "startup_wait_s": 10,
                    "detected_from": "package.json",
                })
        except Exception:
            pass

    # Dockerfile detection
    dockerfile = root / "Dockerfile"
    if dockerfile.exists():
        try:
            import re
            content = dockerfile.read_text()
            expose_match = re.search(r'EXPOSE\s+(\d+)', content)
            if expose_match:
                port = int(expose_match.group(1))
                checks.append({
                    "type": "http_health",
                    "cmd": ["docker", "run", "--rm", "-p", f"0:{port}",
                            "--name", "ground-check", "."],
                    "url": "/",
                    "expect_status": 200,
                    "startup_wait_s": 15,
                    "detected_from": "Dockerfile",
                })
        except Exception:
            pass

    return checks


# ---------------------------------------------------------------------------
# File extraction
# ---------------------------------------------------------------------------

def _get_changed_files(git_diff_text: str, pre_head: str,
                       project_root: Path) -> list[str]:
    """Extract changed file paths from git state."""
    files = set()

    def _run_git(*args):
        try:
            r = subprocess.run(
                ["git"] + list(args),
                capture_output=True, text=True, timeout=5,
                cwd=str(project_root),
            )
            return [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
        except Exception:
            return []

    # Unstaged
    files.update(_run_git("diff", "--name-only"))
    # Staged
    files.update(_run_git("diff", "--cached", "--name-only"))
    # Committed during session
    if pre_head:
        files.update(_run_git("log", "--name-only", "--format=", f"{pre_head}..HEAD"))

    return sorted(files)


# ---------------------------------------------------------------------------
# Tier implementations
# ---------------------------------------------------------------------------

def _tier0_diff_nonempty(changed_files: list[str]) -> dict:
    return {
        "tier": 0,
        "check": "diff_nonempty",
        "passed": len(changed_files) > 0,
        "files_count": len(changed_files),
    }


# Extension → (command_template, description)
# {file} is replaced with absolute path
_SYNTAX_CHECKS = {
    ".py": ([sys.executable, "-m", "py_compile", "{file}"], "py_compile"),
    ".js": (["node", "--check", "{file}"], "node_check"),
    ".mjs": (["node", "--check", "{file}"], "node_check"),
    ".sh": (["bash", "-n", "{file}"], "bash_syntax"),
    ".bash": (["bash", "-n", "{file}"], "bash_syntax"),
}


def _tier1_syntax_check(changed_files: list[str], project_root: Path,
                        budget_s: float) -> list[dict]:
    """Syntax check each changed file by extension."""
    signals = []
    t0 = time.monotonic()

    for relpath in changed_files:
        if time.monotonic() - t0 > budget_s:
            break

        fpath = project_root / relpath
        if not fpath.exists():
            continue

        ext = fpath.suffix.lower()

        # Python: py_compile
        if ext in _SYNTAX_CHECKS:
            cmd_template, check_name = _SYNTAX_CHECKS[ext]
            cmd = [c.replace("{file}", str(fpath)) for c in cmd_template]
            sig = _run_check(cmd, check_name, relpath, timeout=5)
            sig["tier"] = 1
            signals.append(sig)

        # JSON: load it
        elif ext == ".json":
            sig = _check_json(fpath, relpath)
            sig["tier"] = 1
            signals.append(sig)

        # YAML: safe_load
        elif ext in (".yaml", ".yml"):
            sig = _check_yaml(fpath, relpath)
            sig["tier"] = 1
            signals.append(sig)

    return signals


def _tier2_import_check(py_files: list[str], project_root: Path,
                        budget_s: float, python_path: str = None) -> list[dict]:
    """Try importing each changed Python module."""
    signals = []
    t0 = time.monotonic()

    for relpath in py_files[:5]:  # cap at 5 files
        if time.monotonic() - t0 > budget_s:
            break

        # Skip __init__, test files, and non-package files
        name = Path(relpath).name
        if name == "__init__.py" or name.startswith("test_"):
            continue

        # Skip paths with hyphens — not valid Python module names
        # (e.g. mcp-server-nucleus/src/... is imported as mcp_server_nucleus)
        if "-" in relpath:
            continue

        # Resolve Python per-file: explicit override > nearest venv > system
        python = python_path or _find_venv_python(relpath, project_root) or sys.executable

        # Build per-file environment:
        # For subproject files (e.g. backend/app/main.py), set cwd to subproject
        # and strip prefix from module — matches how code runs in production
        parts = Path(relpath).parts
        env = dict(__import__("os").environ)
        if len(parts) > 2:
            cwd = str(project_root / parts[0])
            # Strip subproject prefix: backend/app/main.py → app.main
            subrel = str(Path(*parts[1:]))
            module = subrel.replace("/", ".").replace("\\", ".")
            if module.endswith(".py"):
                module = module[:-3]
            env["PYTHONPATH"] = cwd + ":" + str(project_root)
        else:
            cwd = str(project_root)
            module = relpath.replace("/", ".").replace("\\", ".")
            if module.endswith(".py"):
                module = module[:-3]
            env["PYTHONPATH"] = str(project_root)

        cmd = [python, "-c", f"import {module}"]
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5,
                cwd=cwd, env=env,
            )
            signals.append({
                "tier": 2,
                "check": "import",
                "module": module,
                "passed": r.returncode == 0,
                "error": r.stderr.strip()[-200:] if r.returncode != 0 else "",
            })
        except subprocess.TimeoutExpired:
            signals.append({
                "tier": 2, "check": "import", "module": module,
                "passed": False, "error": "timeout",
            })
        except Exception as e:
            signals.append({
                "tier": 2, "check": "import", "module": module,
                "passed": False, "error": str(e)[:200],
            })

    return signals


def _tier3_test_execution(changed_files: list[str], task: dict,
                          project_root: Path, budget_s: float,
                          python_path: str = None) -> list[dict]:
    """Run tests related to changed files."""
    signals = []
    test_files = set()

    # Strategy 1: task specifies a test file
    task_test = task.get("test_file", "")
    if task_test and (project_root / task_test).exists():
        test_files.add(task_test)

    # Strategy 2: discover test_<name>.py for each changed file
    for relpath in changed_files:
        if not relpath.endswith(".py"):
            continue
        p = Path(relpath)
        name = p.name
        if name.startswith("test_"):
            # Changed file IS a test — run it directly
            if (project_root / relpath).exists():
                test_files.add(relpath)
            continue

        # Check same directory
        candidate = p.parent / f"test_{name}"
        if (project_root / candidate).exists():
            test_files.add(str(candidate))

        # Check tests/ sibling
        candidate = p.parent / "tests" / f"test_{name}"
        if (project_root / candidate).exists():
            test_files.add(str(candidate))

        # Check project-level tests/
        candidate = Path("tests") / f"test_{name}"
        if (project_root / candidate).exists():
            test_files.add(str(candidate))

    if not test_files:
        return []

    t0 = time.monotonic()
    for test_file in sorted(test_files)[:3]:  # cap at 3 test files
        if time.monotonic() - t0 > budget_s:
            break

        python = python_path or _find_venv_python(test_file, project_root) or sys.executable
        cmd = [python, "-m", "pytest", test_file, "-x",
               "-q", "--no-header", "-p", "no:timeout"]
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=min(30, budget_s),
                cwd=str(project_root),
            )
            signals.append({
                "tier": 3,
                "check": "pytest",
                "file": test_file,
                "passed": r.returncode == 0,
                "output": (r.stdout + r.stderr).strip()[-300:],
                "duration_s": round(time.monotonic() - t0, 1),
            })
        except subprocess.TimeoutExpired:
            signals.append({
                "tier": 3, "check": "pytest", "file": test_file,
                "passed": False, "error": "timeout",
            })
        except Exception as e:
            signals.append({
                "tier": 3, "check": "pytest", "file": test_file,
                "passed": False, "error": str(e)[:200],
            })

    return signals


# ---------------------------------------------------------------------------
# Tier 4: Runtime verification (The Mann-Killer)
# ---------------------------------------------------------------------------

def _tier4_runtime_check(checks: list[dict], project_root: Path,
                         budget_s: float) -> list[dict]:
    """Start a server, hit endpoints, verify responses, kill server.

    Check types:
      http_health  — GET url, check status code
      http_json    — GET/POST url, validate response keys
      process_exit — run command, check exit code
    """
    import re
    signals = []
    t0 = time.monotonic()

    for check in checks:
        if time.monotonic() - t0 > budget_s:
            break

        check_type = check.get("type", "")
        remaining = max(0, budget_s - (time.monotonic() - t0))

        if check_type == "process_exit":
            sig = _tier4_process_exit(check, project_root, remaining)
            sig["tier"] = 4
            signals.append(sig)
            continue

        # http_health or http_json — need to start a server
        cmd = list(check.get("cmd", []))
        if not cmd:
            continue

        # Resolve bare "python" to nearest venv Python
        cwd_rel = check.get("cwd", "")
        if cmd[0] in ("python", "python3"):
            resolved = _find_venv_python(cwd_rel, project_root) if cwd_rel else None
            if resolved:
                cmd[0] = resolved

        cwd = str(project_root / cwd_rel) if cwd_rel else str(project_root)
        startup_wait = min(check.get("startup_wait_s", 8), remaining)
        url_path = check.get("url", "/health")
        expect_status = check.get("expect_status", 200)

        proc = None
        port = None
        try:
            # Start server with port 0 for OS auto-assign
            # PYTHONUNBUFFERED ensures startup message isn't stuck in buffer
            import os as _os
            popen_env = {**_os.environ, "PYTHONUNBUFFERED": "1"}
            if cwd_rel:
                popen_env["PYTHONPATH"] = cwd + ":" + str(project_root)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=cwd, text=True, env=popen_env,
            )

            # Poll for port in stdout (exponential backoff)
            port = _poll_for_port(proc, startup_wait)
            if port is None:
                signals.append({
                    "tier": 4, "check": check_type, "url": url_path,
                    "passed": False, "error": "server did not start or announce port",
                })
                continue

            base_url = f"http://127.0.0.1:{port}"

            if check_type == "http_health":
                sig = _tier4_http_check(base_url, url_path, expect_status,
                                        remaining)
                sig["tier"] = 4
                sig["port"] = port
                signals.append(sig)

            elif check_type == "http_json":
                method = check.get("method", "GET")
                expect_keys = check.get("expect_keys", [])
                body = check.get("body")
                sig = _tier4_http_json(base_url, url_path, method,
                                       expect_status, expect_keys, body,
                                       remaining)
                sig["tier"] = 4
                sig["port"] = port
                signals.append(sig)

        except Exception as e:
            signals.append({
                "tier": 4, "check": check_type, "url": url_path,
                "passed": False, "error": str(e)[:200],
            })
        finally:
            if proc is not None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    return signals


def _poll_for_port(proc: subprocess.Popen, timeout_s: float) -> int | None:
    """Read server stdout looking for a port number. Exponential backoff."""
    import re
    import select

    collected = ""
    deadline = time.monotonic() + timeout_s
    wait = 0.1

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            # Process exited before we found a port
            remaining_out = proc.stdout.read() if proc.stdout else ""
            collected += remaining_out
            break

        # Non-blocking read
        try:
            if hasattr(select, 'select'):
                ready, _, _ = select.select([proc.stdout], [], [], wait)
                if ready:
                    line = proc.stdout.readline()
                    if line:
                        collected += line
            else:
                time.sleep(wait)
        except Exception:
            time.sleep(wait)

        # Look for HTTP server port: "Uvicorn running on http://127.0.0.1:PORT"
        # Match http(s)://host:PORT specifically to avoid DB connection strings
        m = re.search(r'https?://[\w.]+:(\d{4,5})\b', collected, re.IGNORECASE)
        if not m:
            # Fallback: "Serving HTTP on :: port PORT"
            m = re.search(r'(?:serving|listening)\s+.*port\s+(\d{4,5})\b', collected, re.IGNORECASE)
        if m:
            return int(m.group(1))

        wait = min(wait * 2, 1.0)

    return None


def _tier4_http_check(base_url: str, path: str, expect_status: int,
                      timeout_s: float) -> dict:
    """GET a URL, check status code."""
    import urllib.request
    import urllib.error

    url = base_url + path
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=min(timeout_s, 5)) as resp:
            status = resp.status
            latency_ms = round((time.monotonic() - t0) * 1000)
            return {
                "check": "http_health", "url": url, "status": status,
                "latency_ms": latency_ms,
                "passed": status == expect_status,
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.monotonic() - t0) * 1000)
        return {
            "check": "http_health", "url": url, "status": e.code,
            "latency_ms": latency_ms,
            "passed": e.code == expect_status,
        }
    except Exception as e:
        return {
            "check": "http_health", "url": url,
            "passed": False, "error": str(e)[:200],
        }


def _tier4_http_json(base_url: str, path: str, method: str,
                     expect_status: int, expect_keys: list, body: dict | None,
                     timeout_s: float) -> dict:
    """HTTP request with JSON response key validation."""
    import urllib.request
    import urllib.error

    url = base_url + path
    t0 = time.monotonic()
    try:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if body else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=min(timeout_s, 5)) as resp:
            status = resp.status
            resp_body = json.loads(resp.read().decode())
            latency_ms = round((time.monotonic() - t0) * 1000)
            missing_keys = [k for k in expect_keys if k not in resp_body]
            return {
                "check": "http_json", "url": url, "method": method,
                "status": status, "latency_ms": latency_ms,
                "passed": status == expect_status and not missing_keys,
                "missing_keys": missing_keys if missing_keys else [],
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.monotonic() - t0) * 1000)
        return {
            "check": "http_json", "url": url, "method": method,
            "status": e.code, "latency_ms": latency_ms,
            "passed": False, "error": f"HTTP {e.code}",
        }
    except Exception as e:
        return {
            "check": "http_json", "url": url, "method": method,
            "passed": False, "error": str(e)[:200],
        }


def _tier4_process_exit(check: dict, project_root: Path,
                        budget_s: float) -> dict:
    """Run a command, check exit code."""
    cmd = check.get("cmd", [])
    cwd = str(project_root / check.get("cwd", "")) if check.get("cwd") else str(project_root)
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=min(budget_s, 30), cwd=cwd)
        return {
            "check": "process_exit", "cmd": " ".join(cmd),
            "passed": r.returncode == check.get("expect_exit", 0),
            "exit_code": r.returncode,
            "duration_s": round(time.monotonic() - t0, 2),
            "output": (r.stdout + r.stderr).strip()[-200:],
        }
    except subprocess.TimeoutExpired:
        return {"check": "process_exit", "cmd": " ".join(cmd),
                "passed": False, "error": "timeout"}
    except Exception as e:
        return {"check": "process_exit", "cmd": " ".join(cmd),
                "passed": False, "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_check(cmd: list, check_name: str, relpath: str,
               timeout: int = 5) -> dict:
    """Run a subprocess check and return a signal dict."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "check": check_name,
            "file": relpath,
            "passed": r.returncode == 0,
            "error": r.stderr.strip()[-200:] if r.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"check": check_name, "file": relpath,
                "passed": False, "error": "timeout"}
    except FileNotFoundError:
        return {"check": check_name, "file": relpath,
                "passed": True, "error": "tool not found, skipped"}
    except Exception as e:
        return {"check": check_name, "file": relpath,
                "passed": False, "error": str(e)[:200]}


def _check_json(fpath: Path, relpath: str) -> dict:
    try:
        json.loads(fpath.read_text())
        return {"check": "json_parse", "file": relpath, "passed": True}
    except Exception as e:
        return {"check": "json_parse", "file": relpath,
                "passed": False, "error": str(e)[:200]}


def _find_venv_python(relpath: str, project_root: Path) -> str | None:
    """Walk up from file's directory to project_root looking for a venv Python."""
    fpath = (project_root / relpath).resolve()
    start = fpath.parent if fpath.is_file() else fpath
    root = project_root.resolve()
    current = start
    while True:
        for venv_name in (".venv", "venv"):
            candidate = current / venv_name / "bin" / "python"
            if candidate.exists():
                return str(candidate)
        if current == root or current == current.parent:
            break
        current = current.parent
    return None


def _check_yaml(fpath: Path, relpath: str) -> dict:
    try:
        import yaml
        yaml.safe_load(fpath.read_text())
        return {"check": "yaml_parse", "file": relpath, "passed": True}
    except ImportError:
        return {"check": "yaml_parse", "file": relpath,
                "passed": True, "error": "pyyaml not installed, skipped"}
    except Exception as e:
        return {"check": "yaml_parse", "file": relpath,
                "passed": False, "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# Tier 5: Outcome Verification (Delta-Based)
# ---------------------------------------------------------------------------

# Regex patterns for extracting measurable claims from plan text.
# Each pattern captures (quantity, unit/context).
_CLAIM_PATTERNS = [
    # "+N tests/files/chunks/items/lines"
    (r'\+\s*(\d+)\s+(tests?|files?|chunks?|items?|lines?|endpoints?|modules?|functions?)',
     "count"),
    # "add N tests/files/..."
    (r'(?:add|create|write|implement)\s+(\d+)\s+(tests?|files?|chunks?|items?|endpoints?|modules?|functions?)',
     "count"),
    # "increase by N"
    (r'increase\s+(?:by\s+)?(\d+)\s+(\w+)',
     "count"),
    # "N new tests/files/..."
    (r'(\d+)\s+new\s+(tests?|files?|chunks?|items?|endpoints?|modules?|functions?)',
     "count"),
    # "create/add <filename>" (file existence claim)
    (r'(?:create|add|write)\s+(?:file\s+)?[`"\']?([a-zA-Z0-9_/\-\.]+\.(?:py|js|ts|json|yaml|yml|md|sh|sql))[`"\']?',
     "file"),
]

# Map unit words to their singular form for consistency.
_UNIT_NORMALIZE = {
    "tests": "test", "files": "file", "chunks": "chunk",
    "items": "item", "lines": "line", "endpoints": "endpoint",
    "modules": "module", "functions": "function",
}


def extract_claims(plan_text: str) -> list[dict]:
    """Extract measurable claims from plan text.

    Returns list of dicts with: claim_type, quantity (for count), unit,
    target (for file), raw_match.
    """
    claims = []
    seen = set()

    for pattern, claim_type in _CLAIM_PATTERNS:
        for match in re.finditer(pattern, plan_text, re.IGNORECASE):
            raw = match.group(0)
            if raw in seen:
                continue
            seen.add(raw)

            if claim_type == "count":
                qty = int(match.group(1))
                unit = _UNIT_NORMALIZE.get(match.group(2).lower(),
                                           match.group(2).lower())
                if qty > 0:
                    claims.append({
                        "claim_type": "count",
                        "quantity": qty,
                        "unit": unit,
                        "raw_match": raw,
                    })
            elif claim_type == "file":
                target = match.group(1)
                claims.append({
                    "claim_type": "file",
                    "target": target,
                    "raw_match": raw,
                })

    return claims


def _measure_count(unit: str, project_root: Path) -> int:
    """Measure the current count of a unit type in the project."""
    try:
        if unit == "test":
            # Count test functions across all test files
            count = 0
            for tf in project_root.rglob("test_*.py"):
                content = tf.read_text(errors="ignore")
                count += len(re.findall(r'^\s*def\s+test_', content, re.MULTILINE))
            return count
        elif unit == "file":
            return sum(1 for _ in project_root.rglob("*.py"))
        elif unit in ("line", "lines"):
            total = 0
            for pf in project_root.rglob("*.py"):
                try:
                    total += sum(1 for _ in open(pf, errors="ignore"))
                except Exception:
                    pass
            return total
        elif unit == "endpoint":
            count = 0
            for pf in project_root.rglob("*.py"):
                try:
                    content = pf.read_text(errors="ignore")
                    count += len(re.findall(
                        r'@(?:app|router|mcp)\.\s*(?:get|post|put|delete|patch|route|tool)',
                        content, re.IGNORECASE))
                except Exception:
                    pass
            return count
        elif unit == "function":
            count = 0
            for pf in project_root.rglob("*.py"):
                try:
                    content = pf.read_text(errors="ignore")
                    count += len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
                except Exception:
                    pass
            return count
        elif unit == "module":
            return sum(1 for _ in project_root.rglob("*.py")
                       if not _.name.startswith("test_"))
        elif unit == "chunk":
            # Count JSONL entries in common data files
            count = 0
            brain = project_root / ".brain"
            if brain.exists():
                for jl in brain.rglob("*.jsonl"):
                    try:
                        count += sum(1 for line in open(jl, errors="ignore")
                                     if line.strip())
                    except Exception:
                        pass
            return count
    except Exception:
        pass
    return 0


def capture_outcome_baseline(plan_text: str, project_root: Path) -> dict:
    """Capture pre-implementation baseline metrics from plan claims.

    Parses plan text for measurable claims (counts, file existence).
    Records current state of each metric.
    Writes to .brain/driver/outcome_baseline.json.

    Returns: {"claims": [...], "captured_at": iso_timestamp, "plan_hash": str}
    """
    project_root = Path(project_root)
    claims = extract_claims(plan_text)

    baseline_claims = []
    for claim in claims:
        if claim["claim_type"] == "count":
            current = _measure_count(claim["unit"], project_root)
            baseline_claims.append({
                "claim_type": "count",
                "unit": claim["unit"],
                "claimed_delta": claim["quantity"],
                "baseline_value": current,
                "raw_match": claim["raw_match"],
            })
        elif claim["claim_type"] == "file":
            target = claim["target"]
            exists = (project_root / target).exists()
            baseline_claims.append({
                "claim_type": "file",
                "target": target,
                "baseline_exists": exists,
                "raw_match": claim["raw_match"],
            })

    plan_hash = hashlib.sha256(plan_text.encode()).hexdigest()[:12]
    result = {
        "claims": baseline_claims,
        "captured_at": datetime.now().isoformat(),
        "plan_hash": plan_hash,
    }

    # Persist
    driver_dir = project_root / ".brain" / "driver"
    driver_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = driver_dir / "outcome_baseline.json"
    baseline_path.write_text(json.dumps(result, indent=2))

    return result


def _tier5_outcome_check(plan_text: str, project_root: Path,
                         budget_s: float,
                         baseline_path: Path) -> list[dict]:
    """Tier 5: Compare post-implementation state against baseline claims.

    For each claimed metric in the baseline:
    - Re-measure the current value
    - Compute delta (current - baseline)
    - Compare delta to claimed improvement
    - Signal passes if actual_delta >= claimed_delta * 0.25 (25% threshold)

    Returns list of signal dicts.
    """
    t0 = time.monotonic()
    signals = []

    try:
        baseline = json.loads(baseline_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    for claim in baseline.get("claims", []):
        if time.monotonic() - t0 > budget_s:
            break

        if claim["claim_type"] == "count":
            current = _measure_count(claim["unit"], project_root)
            baseline_val = claim["baseline_value"]
            claimed_delta = claim["claimed_delta"]
            actual_delta = current - baseline_val
            hit_ratio = actual_delta / claimed_delta if claimed_delta > 0 else 0.0
            passed = hit_ratio >= 0.25  # 25% threshold

            signals.append({
                "tier": 5,
                "check": f"outcome_{claim['unit']}",
                "metric": claim["unit"],
                "claimed_delta": claimed_delta,
                "actual_delta": actual_delta,
                "baseline_value": baseline_val,
                "current_value": current,
                "hit_ratio": round(hit_ratio, 4),
                "passed": passed,
                "error": "" if passed else
                    f"PREMATURE VICTORY: claimed +{claimed_delta} {claim['unit']}, "
                    f"actual +{actual_delta} ({hit_ratio:.0%} of target)",
            })

        elif claim["claim_type"] == "file":
            target = claim["target"]
            exists_now = (project_root / target).exists()
            existed_before = claim.get("baseline_exists", False)
            # Pass if file was created (didn't exist before, exists now)
            # or if it already existed (not a creation claim violation)
            passed = exists_now
            signals.append({
                "tier": 5,
                "check": f"outcome_file",
                "metric": "file_exists",
                "target": target,
                "existed_before": existed_before,
                "exists_now": exists_now,
                "passed": passed,
                "error": "" if passed else
                    f"PREMATURE VICTORY: claimed to create {target}, file not found",
            })

    return signals


def _find_recent_plan(project_root: Path) -> Path | None:
    """Find the most recent plan file.

    Searches:
    1. ~/.claude/plans/*.md (Claude Code plan files)
    2. .brain/driver/current_plan.md (manual plan)
    """
    # Claude Code plans
    claude_plans = Path.home() / ".claude" / "plans"
    if claude_plans.exists():
        plans = sorted(claude_plans.glob("*.md"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        if plans:
            return plans[0]

    # Manual plan in brain
    manual = project_root / ".brain" / "driver" / "current_plan.md"
    if manual.exists():
        return manual

    return None
