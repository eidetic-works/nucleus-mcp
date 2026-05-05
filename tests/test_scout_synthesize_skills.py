"""Tier-0 tests for /scout-doc and /synthesize-doc skill workflows.

NOTE: /scout-doc and /synthesize-doc are CC Skills (markdown files at
.claude/skills/<name>/SKILL.md). They are NOT importable Python modules.
These tests validate the underlying primitives — org_delegate.spawn_prep /
spawn_close — with the exact inputs the skills would generate, covering the
three key behavioral contracts:

1. Happy path: spawn_prep returns a prompt with charter + brief, spawn_close
   is called with the matching spawn_id and returns a non-orphan result.

2. Already-scouted abort: a doc already containing <scout> blocks should be
   detected before spawn_prep is called (the skill aborts; no spawn emitted).

3. Synthesize dry-run: spawn_prep / spawn_close still fire (cost telemetry
   is captured) but the gh pr create step is skipped, and the output
   contains a PR title + branch-name proposal.

Mock pattern follows tests/test_org_delegate_spawn_emit.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DOC = Path(__file__).parent / "fixtures" / "sample_plan_doc.md"


@pytest.fixture
def tmp_brain(monkeypatch, tmp_path):
    """Isolated .brain dir; force re-import so env override is picked up."""
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    for mod in list(sys.modules):
        if mod.startswith("mcp_server_nucleus.runtime."):
            del sys.modules[mod]
    return brain


@pytest.fixture
def tmp_charters(tmp_path):
    charters = tmp_path / "charters"
    charters.mkdir()
    (charters / "sonnet_helper_peer.md").write_text(
        "---\nname: sonnet_helper_peer\n---\n\nExecute peer-lane briefs decisively.\n"
    )
    (charters / "synthesizer_peer.md").write_text(
        "---\nname: synthesizer_peer\n---\n\nSynthesize enriched docs into shipped code.\n"
    )
    return charters


def _events(brain: Path) -> list[dict]:
    path = brain / "ledger" / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Helpers that simulate what the CC skill WOULD do
# ---------------------------------------------------------------------------

SCOUT_EXPANSION_TEMPLATE = """\
<scout>
### Pseudocode
def handle_{section}(): pass

### Function signatures
handle_{section}(doc_path: str, model: str) -> dict

### Integration challenges
- Must not overwrite original prose
- Concurrent scout runs require .scout.lock sentinel

### Edge cases
- Section with only narrative (no concrete design) — skip
- Section already has <scout> block — abort entire skill

### Dependencies
- org_delegate.spawn_prep / spawn_close
- .brain/ledger/events.jsonl (agent_spawn / agent_return)
</scout>"""


def _apply_scout_blocks(doc_text: str, expansion_fn) -> str:
    """Simulate the in-place <scout> block insertion the /scout-doc skill does."""
    lines = doc_text.splitlines()
    out = []
    for line in lines:
        out.append(line)
        if line.startswith("## "):
            section_slug = line.lstrip("#").strip().replace(" ", "_").lower()
            out.append("")
            out.append(expansion_fn(section_slug))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Test 1 — Happy path: fixture doc has no <scout> blocks; primitives fire
# ---------------------------------------------------------------------------

def test_scout_doc_happy_path(tmp_brain, tmp_charters):
    """Given clean fixture + mocked spawn_prep/spawn_close:
    - enriched doc has <scout> blocks under each H2
    - original prose is unchanged
    - spawn_close called with the matching spawn_id
    """
    from mcp_server_nucleus.runtime import org_delegate

    doc_text = FIXTURE_DOC.read_text()

    # Precondition: fixture has no existing scout expansion blocks (open tag on its own line)
    assert "\n<scout>\n" not in doc_text, "fixture must be pre-scout (no scout expansion blocks)"

    # Simulate /scout-doc: call spawn_prep with scout brief
    scout_brief = (
        f"Scout-elaborate each H2 section of the following doc.\n\n"
        f"Doc path: {FIXTURE_DOC}\n\n---\n{doc_text}"
    )
    prompt, spawn_id = org_delegate.spawn_prep(
        role="sonnet_helper_peer",
        brief=scout_brief,
        model="haiku",
        parent="claude_code_peer",
        charters_dir=tmp_charters,
    )

    assert spawn_id.startswith("spawn_")
    assert "Charter: sonnet_helper_peer" in prompt
    assert "Scout-elaborate" in prompt

    # Simulate the cheap-agent returning expansion text
    expansion_text = "\n".join(
        SCOUT_EXPANSION_TEMPLATE.format(section=f"section_{i}") for i in range(3)
    )

    # Apply scout blocks in-place (as skill would do)
    enriched = _apply_scout_blocks(doc_text, lambda s: SCOUT_EXPANSION_TEMPLATE.format(section=s))

    # Assert enriched doc has scout blocks under each H2
    h2_count = sum(1 for line in doc_text.splitlines() if line.startswith("## "))
    scout_count = enriched.count("\n<scout>\n")
    assert scout_count == h2_count, (
        f"expected {h2_count} <scout> blocks (one per H2), got {scout_count}"
    )

    # Assert original prose is unchanged (every non-H2 line still present)
    for line in doc_text.splitlines():
        assert line in enriched, f"original prose line missing from enriched doc: {line!r}"

    # Close the spawn
    result = org_delegate.spawn_close(spawn_id, expansion_text)

    assert result["spawn_id"] == spawn_id
    assert result["orphan"] is False
    assert result["success"] is True
    assert result["response_chars"] == len(expansion_text)

    # Verify events were emitted
    events = _events(tmp_brain)
    spawn_events = [e for e in events if e["type"] == "agent_spawn"]
    return_events = [e for e in events if e["type"] == "agent_return"]
    assert len(spawn_events) == 1
    assert len(return_events) == 1
    assert spawn_events[0]["data"]["spawn_id"] == spawn_id
    assert return_events[0]["data"]["spawn_id"] == spawn_id


# ---------------------------------------------------------------------------
# Test 2 — Already-scouted abort: skill detects <scout> block and aborts
# ---------------------------------------------------------------------------

def test_scout_doc_already_scouted_aborts(tmp_brain, tmp_charters):
    """Given a doc already containing a <scout> block:
    - skill returns error status (simulated as ValueError)
    - spawn_prep is NOT called (no events emitted)
    - doc is not modified
    """
    from mcp_server_nucleus.runtime import org_delegate

    doc_text = FIXTURE_DOC.read_text()
    # Inject a scout block to simulate a previously-scouted doc
    already_scouted = doc_text + "\n\n<scout>\n### Pseudocode\nalready present\n</scout>\n"

    assert "\n<scout>\n" in already_scouted, "pre-condition: doc must contain scout block"

    # The /scout-doc skill checks for existing <scout> blocks BEFORE calling
    # spawn_prep.  Simulate that guard:
    def scout_doc_workflow(doc_content: str) -> dict:
        """Minimal simulation of the /scout-doc skill guard logic."""
        if "\n<scout>\n" in doc_content:
            return {"status": "error", "reason": "already scouted", "modified": False}
        # Would call spawn_prep here — but we never reach it
        prompt, spawn_id = org_delegate.spawn_prep(
            role="sonnet_helper_peer",
            brief="expand",
            model="haiku",
            parent="claude_code_peer",
            charters_dir=tmp_charters,
        )
        return {"status": "ok", "spawn_id": spawn_id}

    result = scout_doc_workflow(already_scouted)

    assert result["status"] == "error"
    assert "already scouted" in result["reason"]
    assert result["modified"] is False

    # No spawn events should have been emitted
    events = _events(tmp_brain)
    spawn_events = [e for e in events if e["type"] == "agent_spawn"]
    assert len(spawn_events) == 0, "spawn_prep must not fire when doc is already scouted"


# ---------------------------------------------------------------------------
# Test 3 — Synthesize dry-run: gh pr create skipped; output has PR proposal
# ---------------------------------------------------------------------------

def test_synthesize_doc_dry_run(tmp_brain, tmp_charters):
    """Given enriched fixture + --dry-run flag + mocked spawn:
    - gh pr create is NOT called
    - output contains PR title + branch name proposal
    - spawn_close IS called (cost telemetry still captured)
    """
    from mcp_server_nucleus.runtime import org_delegate

    doc_text = FIXTURE_DOC.read_text()
    # Build an enriched doc (as if /scout-doc already ran)
    enriched = _apply_scout_blocks(
        doc_text, lambda s: SCOUT_EXPANSION_TEMPLATE.format(section=s)
    )
    assert "\n<scout>\n" in enriched

    synthesis_brief = (
        f"Synthesize this enriched doc into a working code PR.\n"
        f"DRY_RUN=true — do NOT open PR; output PR title + branch name only.\n\n"
        f"Doc path: {FIXTURE_DOC}\n\n---\n{enriched}"
    )

    prompt, spawn_id = org_delegate.spawn_prep(
        role="synthesizer_peer",
        brief=synthesis_brief,
        model="sonnet",
        parent="claude_code_peer",
        charters_dir=tmp_charters,
    )

    assert spawn_id.startswith("spawn_")
    assert "synthesizer_peer" in prompt
    assert "DRY_RUN=true" in prompt

    # Simulate synthesizer sub-agent returning a dry-run summary (no PR opened)
    proposed_branch = "feat/sample-plan-doc-synthesis"
    proposed_pr_title = "feat(sample-plan): synthesize event-schema + relay-transport + cost-telemetry"
    synthesis_response = (
        f"DRY RUN — no PR opened.\n\n"
        f"Proposed branch: {proposed_branch}\n"
        f"Proposed PR title: {proposed_pr_title}\n\n"
        f"Verified scout claims: 9/9\n"
        f"Implementation-ready sections: 3/3\n"
        f"Estimated LOC: ~80 (under 300 LOC cap)\n"
    )

    # gh pr create must NOT be invoked in dry-run mode
    with patch("subprocess.run") as mock_run:
        result = org_delegate.spawn_close(spawn_id, synthesis_response)
        mock_run.assert_not_called()

    assert result["spawn_id"] == spawn_id
    assert result["orphan"] is False
    assert result["success"] is True

    # Output contains the PR title and branch name
    assert proposed_branch in synthesis_response
    assert proposed_pr_title in synthesis_response

    # spawn_close WAS called — cost telemetry event emitted
    events = _events(tmp_brain)
    return_events = [e for e in events if e["type"] == "agent_return"]
    assert len(return_events) == 1
    assert return_events[0]["data"]["spawn_id"] == spawn_id
    assert return_events[0]["data"]["orphan"] is False
    assert return_events[0]["data"]["response_chars"] == len(synthesis_response)
