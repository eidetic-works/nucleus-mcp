"""Both SDKs must return one mailbox in the same order (CS-5).

They implement one protocol against one on-disk layout, and they disagreed. For
the merged all-buckets `read()`, Python sorted by filename — which always begins
with the timestamp — while TypeScript sorted by envelope `id`. Ids are
caller-suppliable: any 8-128 character string, only falling back to a
chronological shape when the caller omits one.

So a client that supplied its own ids got an order that was not newest-first,
contradicting TypeScript's own doc comment, and the two SDKs returned **opposite**
orders for the same directory. Demonstrated against a real mailbox before the
fix:

    python:     alpha-third-NEWEST, mike-second, zeta-first
    typescript: zeta-first, mike-second, alpha-third-NEWEST

This test builds that fixture and runs both clients for real, rather than
comparing source. A sort order is behaviour; reading two implementations and
judging them equivalent is exactly the reasoning that let them diverge.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY_SDK = ROOT / "sdk" / "python"
TS_SDK = ROOT / "sdk" / "typescript"

pytestmark = pytest.mark.skipif(
    not (PY_SDK.is_dir() and TS_SDK.is_dir()), reason="SDKs not in this export"
)

# Ids whose lexical order is the reverse of their chronological order. That is
# the whole point: with chronological ids the bug is invisible.
FIXTURE = [
    ("alpha", "20260101T000001", "zeta-first"),
    ("bravo", "20260101T000002", "mike-second"),
    ("alpha", "20260101T000003", "alpha-third-newest"),
]
NEWEST_FIRST = ["alpha-third-newest", "mike-second", "zeta-first"]


@pytest.fixture
def mailbox(tmp_path):
    brain = tmp_path / ".brain"
    for bucket, stamp, mid in FIXTURE:
        inbox = brain / "relay" / bucket
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / f"{stamp}_{mid}.json").write_text(
            json.dumps({
                "id": mid, "sender": "s", "recipient": bucket, "subject": "x",
                "body": "y", "created_at": "2026-01-01T00:00:00Z",
                "status": "unread",
            }),
            encoding="utf-8",
        )
    return brain


def _python_order(brain: Path):
    out = subprocess.run(
        [sys.executable, "-c",
         "from nucleus_relay_sdk.client import RelayClient;"
         f"print(','.join(m['id'] for m in RelayClient('t', brain_path=r'{brain}').read()))"],
        capture_output=True, text=True, env={"PYTHONPATH": str(PY_SDK), "PATH": "/usr/bin:/bin"},
        timeout=60,
    )
    if out.returncode != 0:
        pytest.skip(f"python SDK not runnable here: {out.stderr.strip()[:200]}")
    return out.stdout.strip().split(",")


def _typescript_order(brain: Path):
    built = TS_SDK / "dist" / "index.js"
    if not built.exists():
        pytest.skip("TS SDK not built (run `npm install && npm run build` in sdk/typescript)")
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    script = (
        f"const {{RelayClient}} = require({str(built)!r});"
        "(async()=>{const m = await new RelayClient({sender:'t',brainPath:"
        f"{str(brain)!r}"
        "}).read(); console.log(m.map(x=>x.id).join(','));})();"
    )
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        pytest.skip(f"TS SDK not runnable here: {out.stderr.strip()[:200]}")
    return out.stdout.strip().split(",")


def test_the_python_sdk_returns_newest_first(mailbox):
    assert _python_order(mailbox) == NEWEST_FIRST


def test_the_typescript_sdk_returns_newest_first(mailbox):
    assert _typescript_order(mailbox) == NEWEST_FIRST, (
        "the TypeScript SDK is not ordering by filename; caller-supplied ids "
        "make an id sort non-chronological"
    )


def test_both_sdks_return_the_same_order(mailbox):
    """The finding itself: one mailbox, two clients, one answer."""
    py = _python_order(mailbox)
    ts = _typescript_order(mailbox)
    assert py == ts, (
        f"the two SDKs disagree about the same mailbox: python={py} typescript={ts}. "
        "They implement one protocol against one on-disk layout."
    )


def test_the_typescript_sort_key_is_the_filename_not_the_id():
    """Source check, so the reason survives even where node cannot run."""
    source = (TS_SDK / "src" / "index.ts").read_text(encoding="utf-8")
    merged = source.split("async read(", 1)[1].split("async ", 1)[0]
    assert "_filename" in merged, "read() no longer sorts the merged listing by filename"
    assert "a.id < b.id" not in merged, (
        "read() is sorting the merged listing by envelope id again; ids are "
        "caller-suppliable and need not be chronological"
    )


def test_both_sdks_attach_the_filename_they_sort_by():
    """Python has always attached _filename; TypeScript now does too."""
    py = (PY_SDK / "nucleus_relay_sdk" / "client.py").read_text(encoding="utf-8")
    ts = (TS_SDK / "src" / "index.ts").read_text(encoding="utf-8")
    assert "_filename" in py and "_filename" in ts
