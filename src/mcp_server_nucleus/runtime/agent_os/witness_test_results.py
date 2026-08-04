"""Agent OS — Test-Result Witness (regime-2 attribution for test runs).

The third external witness for the referee. Logs test run results to
``.brain/witness/test_results.jsonl`` with test run ID + timestamp + pass/fail
counts + signature, so the referee can verify "the tests passed" claims.

The witness signs results with a key the agent doesn't hold — the signature
proves the result came from the test runner, not from the agent fabricating
it. This closes the causation gap for test claims.

ADR-0047 Workstream D3: extends the referee's regime-2 reach to test-result
claims. Closes the causation gap for "tests passed" — the third most common
agent claim type.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.agent_os.witness_test_results")

WITNESS_DIR = "witness"
TEST_RESULTS_LOG_FILE = "test_results.jsonl"

# The signing key is read from the environment — the agent doesn't have it.
# In production, this key is set by the CI/CD system, not by the agent.
_SIGN_KEY_ENV = "NUCLEUS_WITNESS_SIGN_KEY"


def _witness_path(brain_path: Optional[str] = None) -> Path:
    root = Path(brain_path) if brain_path else Path(
        os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")
    )
    witness_dir = root / WITNESS_DIR
    witness_dir.mkdir(parents=True, exist_ok=True)
    return witness_dir / TEST_RESULTS_LOG_FILE


def _sign(payload: str, key: Optional[str] = None) -> str:
    """Sign a payload with HMAC-SHA256. The key comes from the environment."""
    sign_key = key or os.environ.get(_SIGN_KEY_ENV)
    if not sign_key:
        raise RuntimeError(
            f"{_SIGN_KEY_ENV} is not set — refusing to sign with a hardcoded "
            f"default key (any agent that read this source could forge witness entries)."
        )
    return hmac.new(sign_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def log_test_result(
    test_run_id: str,
    *,
    passed: int,
    failed: int,
    skipped: int = 0,
    agent_id: str = "cell-0",
    session_id: str = "agent-os-cell",
    brain_path: Optional[str] = None,
    test_command: Optional[str] = None,
) -> str:
    """Log a test run result to the witness file.

    Returns the witness entry ID (``witness-test-<test_run_id>``).

    The entry is signed with HMAC-SHA256 using a key from the environment.
    The agent doesn't have the key, so it can't fabricate test results.
    """
    path = _witness_path(brain_path)
    ts = time.time()
    entry_id = f"witness-test-{test_run_id}"

    entry = {
        "witness_id": entry_id,
        "test_run_id": test_run_id,
        "timestamp": ts,
        "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": passed + failed + skipped,
        "all_passed": failed == 0 and skipped == 0,
        "agent_id": agent_id,
        "session_id": session_id,
        "test_command": test_command,
    }

    # Sign the entry (excluding the signature field itself)
    payload = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    entry["signature"] = _sign(payload)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(
        "witness: logged test result — %s (passed=%d, failed=%d)",
        test_run_id, passed, failed,
    )
    return entry_id


def query_test_result(
    test_run_id: Optional[str] = None,
    *,
    brain_path: Optional[str] = None,
    agent_id: Optional[str] = None,
    since_timestamp: Optional[float] = None,
    require_all_passed: bool = False,
) -> bool:
    """Query the witness log for a matching test result.

    Returns True if any logged test result matches the query.

    If ``require_all_passed`` is True, only returns True if the matched
    result has all tests passing (failed=0, skipped=0).
    """
    path = _witness_path(brain_path)
    if not path.exists():
        return False

    run_id_lower = (test_run_id or "").lower().strip()

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if agent_id and entry.get("agent_id") != agent_id:
                continue
            if since_timestamp and entry.get("timestamp", 0) < since_timestamp:
                continue

            # Match by test_run_id (substring) if provided
            if run_id_lower:
                logged_id = (entry.get("test_run_id") or "").lower()
                if run_id_lower not in logged_id:
                    continue

            # If require_all_passed, check the result
            if require_all_passed and not entry.get("all_passed", False):
                continue

            return True

    return False


def verify_signature(entry: dict, key: Optional[str] = None) -> bool:
    """Verify the HMAC signature on a test result entry.

    This lets the referee confirm the entry was written by the witness
    (which holds the key), not fabricated by the agent.
    """
    entry = dict(entry)  # avoid mutating the caller's dict
    sig = entry.pop("signature", None)
    if not sig:
        return False

    payload = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    expected = _sign(payload, key)
    return hmac.compare_digest(sig, expected)


def get_test_result_entries(
    *,
    brain_path: Optional[str] = None,
    limit: int = 100,
    agent_id: Optional[str] = None,
) -> list[dict]:
    """Read test-result witness entries (for debugging / inspection)."""
    path = _witness_path(brain_path)
    if not path.exists():
        return []

    entries = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent_id and entry.get("agent_id") != agent_id:
                continue
            entries.append(entry)

    return entries[-limit:]


__all__ = [
    "log_test_result",
    "query_test_result",
    "verify_signature",
    "get_test_result_entries",
]
