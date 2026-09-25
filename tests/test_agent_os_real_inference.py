"""Agent-OS moat loop — REAL inference end-to-end test.

Proves the moat loop works with a real LLM provider (not stubbed):
  boot_cell → real Groq call → response contains a git SHA →
  verifier probes the repo → CONFIRMED → persisted to flywheel →
  corpus counts it → canary re-verifies clean.

Skips if NUCLEUS_GROQ_API_KEY is not set (no free lane available).
This is the test that proves the moat loop is alive with real cognition,
not just stubbed.
"""
from __future__ import annotations

import json
import os

import pytest

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod
from mcp_server_nucleus.runtime.agent_os import canary_cli, corpus_cli


def _seed_prior_memory(brain_path: str, text: str) -> None:
    """Verbatim from test_agent_os_run_cli._seed_prior_memory."""
    from nucleus_wedge.store import Store

    Store(brain_path).append(
        value=text,
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )


_VALID_STATUSES = {"CONFIRMED", "REFUTED", "UNVERIFIABLE", "PARTIAL"}


@pytest.fixture
def groq_api_key():
    """Skip if no Groq API key is set — this test needs real inference."""
    key = os.environ.get("NUCLEUS_GROQ_API_KEY")
    if not key:
        pytest.skip("NUCLEUS_GROQ_API_KEY not set — real inference test skipped")
    return key


def test_moat_loop_real_inference_confirmed(tmp_path, monkeypatch, capsys, groq_api_key):
    """The moat loop with REAL inference: Groq → git SHA → CONFIRMED → canary clean.

    The prompt asks the agent to confirm a real commit SHA exists. The verifier
    probes the git repo and CONFIRMS it. This is the first test that proves the
    moat loop works with real cognition, not just stubbed.
    """
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "0")  # REAL inference, not stubbed
    monkeypatch.setenv(boot_mod.PAGER_FLAG, "1")
    monkeypatch.setenv(boot_mod.VERIFIED_RECORD_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    monkeypatch.setenv("NUCLEUS_GROQ_API_KEY", groq_api_key)

    # Use a real commit SHA from the repo — the verifier will probe git and CONFIRM
    # Get a real SHA from the current repo
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, "must be in a git repo for this test"
    real_sha = result.stdout.strip()[:8]  # 8-char short SHA

    prior = f"Commit {real_sha} exists in this repository."
    _seed_prior_memory(str(brain), prior)

    # ── 1. RUN: boot one turn inside the OS with REAL inference ────────────
    result = boot_mod.boot_cell(
        f"Confirm that commit {real_sha} exists in this repository. "
        f"State the SHA in your response.",
        recall_query="commit exists",
        brain_path=str(brain),
    )

    # Real inference must have produced non-empty text
    assert result.gateway_result.text, (
        "real inference (Groq) must produce non-empty response text"
    )

    # Referee verdict must be attached
    assert result.verified_label is not None, (
        "VERIFIED_RECORD=ON must attach a referee verdict to BootResult"
    )
    assert result.verified_label.get("status") in _VALID_STATUSES

    # The response contains a real git SHA → verifier should CONFIRM it
    # (if the SHA exists in the repo, which it does by construction)
    status = result.verified_label.get("status")
    assert status == "CONFIRMED", (
        f"real inference response with a valid git SHA should be CONFIRMED, "
        f"got {status}: {result.verified_label.get('detail', '')[:200]}"
    )

    # ── 2. PERSIST: the CONFIRMED verdict landed in loop_turns.jsonl ────────
    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert rows, "boot_cell must write at least one turn to the flywheel"
    last = rows[-1]
    assert "verified_label" in last, "verified_label must be persisted to disk"
    assert last["verified_label"].get("status") == "CONFIRMED", (
        "the persisted turn must be CONFIRMED"
    )

    # ── 3. CORPUS: the corpus reader counts the CONFIRMED turn ─────────────
    capsys.readouterr()
    rc = corpus_cli.corpus(brain_path=str(brain))
    assert rc == 0
    out = capsys.readouterr().out
    assert "CONFIRMED: 1" in out, (
        f"corpus must count 1 CONFIRMED turn; got:\n{out}"
    )

    # ── 4. CANARY: re-verify the CONFIRMED turn — must be clean ────────────
    capsys.readouterr()
    rc = canary_cli.canary(brain_path=str(brain))
    assert rc == 0, "canary must exit 0"
    out = capsys.readouterr().out
    assert "clean — all re-verified CONFIRMED" in out, (
        f"canary must re-verify the CONFIRMED turn as clean; got:\n{out}"
    )
    assert "DRIFT" not in out
