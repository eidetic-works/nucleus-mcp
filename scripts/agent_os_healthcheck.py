#!/usr/bin/env python3
"""Agent OS pre-flight health check (Track D, first minimal version).

A cheap, fast, manual, on-demand sanity check — NOT a re-run of the full
live-loop verification, and NOT wired into launchd/cron/CI (deliberately;
that's a later, separate step). Answers three narrow questions in well
under 60 seconds, at effectively zero cost:

  (a) Is the Claude Code Max OAuth credential in the macOS Keychain still
      valid (not expired)?
  (b) Is the shared Max-plan usage quota not currently exhausted? — one
      minimal, cheap-tier probe call, not a full loop run.
  (c) Does the directly-relevant test surface (verifier, agent_os, boot,
      oauth_exchange, the adversarial claim-extraction suite) still pass?

Never touches ~/.tb/oauth_bespoq_cowork.json or .brain/ — writes only to a
throwaway role file (~/.tb/oauth_healthcheck_probe.json) for check (b), and
never prints a raw access_token/refresh_token value anywhere.

Usage::

    source .venv/bin/activate   # from the repo root
    python3 mcp-server-nucleus/scripts/agent_os_healthcheck.py

Exit 0 iff all three checks pass. Exit 1 if any check fails or cannot run.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]  # mcp-server-nucleus/scripts -> repo root
MCP_SERVER_NUCLEUS = SCRIPT_DIR.parent  # mcp-server-nucleus/

# Throwaway role — never touches the real bespoq_cowork or any other
# operator-managed role file.
_PROBE_ROLE = "healthcheck_probe"
_PROBE_ROLE_PATH = Path.home() / ".tb" / f"oauth_{_PROBE_ROLE}.json"

# The relevant test surface this investigation actually touched. NOT the
# full ~13k-test repo suite -- that would blow the 60s budget by orders of
# magnitude. Scoped deliberately; widen only if the 60s budget allows it.
_TEST_TARGETS = [
    "tests/test_oauth_exchange.py",
    "tests/test_agent_os_claim_extraction_adversarial.py",
    "tests/test_verifier.py",
    "tests/test_agent_os_boot.py",
    "tests/test_agent_os_verified_record.py",
    "tests/test_agent_os_loop_cli.py",
]


class CheckResult:
    def __init__(self, name: str, ok: bool, detail: str, elapsed_s: float):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.elapsed_s = elapsed_s


def check_a_keychain_credential() -> CheckResult:
    """Is the Claude Code Max OAuth credential in Keychain still valid?

    Reads the keychain entry once, extracts only expiresAt (never the token
    values), and checks it against wall-clock time with a safety margin.
    """
    t0 = time.monotonic()
    try:
        raw = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if raw.returncode != 0 or not raw.stdout.strip():
            return CheckResult(
                "A: Keychain credential", False,
                "Keychain item 'Claude Code-credentials' not found or not readable "
                "(are you logged into Claude Code?)",
                time.monotonic() - t0,
            )
        data = json.loads(raw.stdout)
        cc = data.get("claudeAiOauth")
        if not cc or "expiresAt" not in cc:
            return CheckResult(
                "A: Keychain credential", False,
                "Keychain item present but missing claudeAiOauth.expiresAt "
                "(unexpected shape — Claude Code's credential format may have changed)",
                time.monotonic() - t0,
            )
        expires_at_s = int(cc["expiresAt"]) // 1000  # keychain is ms, not s
        seconds_left = expires_at_s - int(time.time())
        if seconds_left <= 0:
            return CheckResult(
                "A: Keychain credential", False,
                f"access_token expired {-seconds_left}s ago",
                time.monotonic() - t0,
            )
        return CheckResult(
            "A: Keychain credential", True,
            f"valid, {seconds_left}s ({seconds_left / 60:.1f} min) until access_token expiry",
            time.monotonic() - t0,
        )
    except subprocess.TimeoutExpired:
        return CheckResult("A: Keychain credential", False, "security(1) timed out after 5s", time.monotonic() - t0)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return CheckResult(
            "A: Keychain credential", False,
            f"could not parse keychain JSON: {type(exc).__name__}: {exc}",
            time.monotonic() - t0,
        )


def check_b_quota_probe() -> CheckResult:
    """Is the shared Max-plan usage quota not currently exhausted?

    One minimal, cheap-tier (haiku) call through the real claude_oauth
    provider -- not the default model, deliberately: a live investigation
    on 2026-08-21 found the 429 this check watches for is a SHARED usage
    quota, and a concurrently-running Sonnet-tier session (e.g. this very
    Claude Code session) can squeeze that quota enough that a same-tier
    probe reports a false exhaustion. Haiku's low per-call cost gives a
    cleaner, lower-noise signal for "is the account fundamentally out of
    quota" specifically. See docs/AGENT_OS_OAUTH_LIVE_VERIFICATION.md.
    """
    t0 = time.monotonic()
    try:
        raw = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if raw.returncode != 0 or not raw.stdout.strip():
            return CheckResult(
                "B: quota probe", False,
                "skipped -- Keychain credential unavailable (see check A)",
                time.monotonic() - t0,
            )
        cc = json.loads(raw.stdout).get("claudeAiOauth") or {}
        access_token = cc.get("accessToken")
        refresh_token = cc.get("refreshToken")
        expires_at_ms = cc.get("expiresAt")
        if not (access_token and refresh_token and expires_at_ms):
            return CheckResult(
                "B: quota probe", False,
                "skipped -- Keychain credential incomplete (see check A)",
                time.monotonic() - t0,
            )

        token = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": int(expires_at_ms) // 1000,
            "scope": " ".join(cc.get("scopes", [])),
            "organization_uuid": "",
            "account_uuid": "",
            "minted_at": int(time.time()),
        }
        _PROBE_ROLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(_PROBE_ROLE_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(token, f)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return CheckResult(
            "B: quota probe", False,
            f"could not build probe credential: {type(exc).__name__}: {exc}",
            time.monotonic() - t0,
        )

    try:
        env = dict(os.environ)
        env["NUCLEUS_LLM_PROVIDER"] = "claude_oauth"
        env["NUCLEUS_OAUTH_ROLE"] = _PROBE_ROLE
        env["NUCLEUS_OAUTH_MODEL"] = "claude-haiku-4-5"
        proc = subprocess.run(
            [
                sys.executable, "-c",
                "from mcp_server_nucleus.runtime.llm_client import get_llm_client\n"
                "c = get_llm_client(provider='claude_oauth')\n"
                "r = c.generate_content('Reply with the single word ALIVE and nothing else.')\n"
                "print('ENGINE=' + getattr(c, 'engine', '?'))\n"
                "print('TEXT=' + (r.text or '')[:40])\n",
            ],
            cwd=str(MCP_SERVER_NUCLEUS),
            env=env,
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            "B: quota probe", False,
            "probe call did not complete within 30s",
            time.monotonic() - t0,
        )
    finally:
        try:
            _PROBE_ROLE_PATH.unlink(missing_ok=True)
        except OSError:
            pass

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-1] if proc.stderr else "(no stderr)"
        rate_limited = "429" in (proc.stderr or "") or "rate_limit" in (proc.stderr or "")
        detail = (
            f"probe call failed{' (rate_limit_error / 429 -- quota likely exhausted)' if rate_limited else ''}: "
            f"{stderr_tail}"
        )
        return CheckResult("B: quota probe", False, detail, time.monotonic() - t0)

    return CheckResult(
        "B: quota probe", True,
        f"real call succeeded ({proc.stdout.strip().replace(chr(10), ' | ')})",
        time.monotonic() - t0,
    )


def check_c_test_suite() -> CheckResult:
    """Does the directly-relevant test surface still pass?

    Scoped to the files this investigation actually touched -- the full
    repo suite (~13k tests) would blow the 60s budget by orders of
    magnitude. Widen this list only if doing so still fits the budget.
    """
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *_TEST_TARGETS, "-q"],
            cwd=str(MCP_SERVER_NUCLEUS),
            capture_output=True, text=True, timeout=45,
        )
    except subprocess.TimeoutExpired:
        return CheckResult("C: test suite", False, "pytest did not complete within 45s", time.monotonic() - t0)

    summary_line = ""
    for line in reversed((proc.stdout or "").splitlines()):
        if " passed" in line or " failed" in line or " error" in line:
            summary_line = line.strip()
            break

    ok = proc.returncode == 0
    detail = summary_line or f"pytest exit code {proc.returncode}, no summary line found"
    return CheckResult("C: test suite", ok, detail, time.monotonic() - t0)


def main() -> int:
    start = time.monotonic()
    print("=" * 72)
    print("AGENT OS HEALTH CHECK — pre-flight sanity, not a full verification")
    print("=" * 72)

    results = [
        check_a_keychain_credential(),
        check_b_quota_probe(),
        check_c_test_suite(),
    ]

    all_ok = True
    for r in results:
        mark = "✓ PASS" if r.ok else "✗ FAIL"
        print(f"  [{mark}] {r.name} ({r.elapsed_s:.1f}s)")
        print(f"          {r.detail}")
        if not r.ok:
            all_ok = False

    total = time.monotonic() - start
    print("-" * 72)
    print(f"  Total: {total:.1f}s — {'ALL CHECKS PASSED' if all_ok else 'ONE OR MORE CHECKS FAILED'}")
    print("=" * 72)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
