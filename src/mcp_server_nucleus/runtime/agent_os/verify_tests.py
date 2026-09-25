"""Agent OS — run a test command and witness its real result.

The missing writer. ``witness_test_results.log_test_result`` has existed since
ADR-0047 D3 and the verifier has read it since (verifier.py, ``tests_passed``
evidence kind), but NOTHING in production ever called the writer — its only
callers were the reader and one test. A claim class routed at that anchor would
therefore have been unable to reach CONFIRMED no matter what the agent did: a
control that can only ever refuse, which is as useless as one that can only ever
pass.

This module closes that loop. It runs a real command, takes its real exit code,
and records a signed witness entry the agent cannot forge (the HMAC key lives in
the environment, not in the agent's context).

Three rules it exists to honour, each paid for elsewhere in this repo:

1. **Never trust a piped exit code.** ``subprocess.run`` returns the command's
   own ``returncode``; a shell pipeline returns the LAST stage's status, which
   once reported a 24-failure pytest run as success.
2. **"Could not run" is not "failed".** A timeout, a missing binary, or an
   unsigned witness is INSUFFICIENT — no witness entry is written at all. Writing
   ``failed=1`` for a run that never happened would be a fabricated refutation,
   which is the same defect as a fabricated pass pointed the other way.
3. **Counts come from the runner, not from a guess.** If the summary line cannot
   be parsed, that is INSUFFICIENT too, not "0 failures".
"""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

# pytest's terminal summary, e.g.
#   "5 failed, 120 passed, 3 skipped in 4.20s"
#   "13 passed in 3.59s"
_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|skipped|error|errors)\b")

# Sentinel exit codes distinguishable from a test failure.
RC_TIMEOUT = -1
RC_NOT_RUN = -2


@dataclass
class TestRunOutcome:
    """The result of trying to run a test command.

    ``state`` is the third state made explicit:
      "recorded"     -- the command ran and a signed witness entry was written
      "insufficient" -- the command did not produce a usable result; NOTHING was
                        written. Never conflate this with a failing test run.
    """

    state: str
    test_run_id: Optional[str]
    witness_id: Optional[str]
    passed: int
    failed: int
    skipped: int
    returncode: Optional[int]
    reason: str


def parse_counts(output: str) -> Optional[dict]:
    """Extract passed/failed/skipped from a pytest summary line.

    Returns None when no counts can be found — the caller must treat that as
    INSUFFICIENT rather than assuming zero failures. A run whose output we
    cannot read is a run we cannot vouch for.
    """
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    found = False
    for n, kind in _COUNT_RE.findall(output or ""):
        found = True
        if kind.startswith("error"):
            counts["failed"] += int(n)
        else:
            counts[kind] += int(n)
    return counts if found else None


def run_and_witness(
    command: List[str],
    *,
    timeout_s: int = 1800,
    brain_path: Optional[str] = None,
    agent_id: str = "verify-tests",
    session_id: str = "cli",
    test_run_id: Optional[str] = None,
) -> TestRunOutcome:
    """Run ``command``, then witness what actually happened.

    No shell, no pipe: the returncode is the command's own.
    """
    run_id = test_run_id or f"run-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    printable = " ".join(command)

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError:
        return TestRunOutcome(
            "insufficient", None, None, 0, 0, 0, RC_NOT_RUN,
            f"could not RUN {command[0]!r}: not found. This is NOT a test "
            f"failure -- nothing was executed, so nothing is witnessed.",
        )
    except subprocess.TimeoutExpired:
        return TestRunOutcome(
            "insufficient", None, None, 0, 0, 0, RC_TIMEOUT,
            f"{printable} exceeded {timeout_s}s and was killed. A partial run "
            f"proves neither pass nor failure.",
        )
    except OSError as exc:
        return TestRunOutcome(
            "insufficient", None, None, 0, 0, 0, RC_NOT_RUN,
            f"could not RUN {printable}: {exc}",
        )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    counts = parse_counts(combined)
    if counts is None:
        return TestRunOutcome(
            "insufficient", None, None, 0, 0, 0, proc.returncode,
            f"{printable} exited {proc.returncode} but emitted no parseable "
            f"test summary. Refusing to assume zero failures from an "
            f"unreadable run.",
        )

    # Belt and braces: a non-zero exit with zero parsed failures means the two
    # signals disagree. Trust the exit code -- it is the runner's own verdict --
    # and refuse to witness rather than silently recording a pass.
    if proc.returncode != 0 and counts["failed"] == 0:
        return TestRunOutcome(
            "insufficient", None, None,
            counts["passed"], counts["failed"], counts["skipped"],
            proc.returncode,
            f"{printable} exited {proc.returncode} but the summary reports 0 "
            f"failures. Exit code and summary disagree; not witnessing either.",
        )

    from .witness_test_results import log_test_result

    try:
        witness_id = log_test_result(
            run_id,
            passed=counts["passed"],
            failed=counts["failed"],
            skipped=counts["skipped"],
            agent_id=agent_id,
            session_id=session_id,
            brain_path=brain_path,
            test_command=printable,
        )
    except RuntimeError as exc:
        # The witness refuses to sign without NUCLEUS_WITNESS_SIGN_KEY. That
        # refusal is correct -- an unsigned entry the agent could have forged is
        # worth nothing -- but it means we have no witness, not a failed run.
        return TestRunOutcome(
            "insufficient", run_id, None,
            counts["passed"], counts["failed"], counts["skipped"],
            proc.returncode,
            f"tests ran (passed={counts['passed']}, failed={counts['failed']}) "
            f"but the result could NOT be witnessed: {exc}",
        )

    return TestRunOutcome(
        "recorded", run_id, witness_id,
        counts["passed"], counts["failed"], counts["skipped"],
        proc.returncode,
        f"witnessed {run_id}: passed={counts['passed']} "
        f"failed={counts['failed']} skipped={counts['skipped']}",
    )
