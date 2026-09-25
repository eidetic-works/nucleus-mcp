"""The README's privacy section must describe the path it recommends first (RL-3).

The Privacy section said all state stays on your machine "unless you explicitly
configure a remote relay", and described what a relay receives as "engram
metadata" going to "your own relay server".

None of that was true of Quick Start Option A, which is the first option offered
and the one needing least effort to adopt: it connects the user to
`relay.nucleusos.dev`, a hosted service the project operates. In that mode there
is no local `.brain/` at all, and the record the server stores includes `value`
— the full content of the memory — not a key or a digest.

A user cannot correct for a privacy claim they were never given, so these tests
pin the disclosure rather than the wording of any one sentence: the section must
distinguish the two options, must not claim the hosted path is local, and must
say that full content is stored. If the sync record ever stops carrying content,
this should be revisited — the test names the field so that shows up.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

README = ROOT / "README.md"
SYNC_ROUTE = SRC / "mcp_server_nucleus" / "http_transport" / "engram_sync_route.py"

pytestmark = pytest.mark.skipif(not README.exists(), reason="README not in this export")


@pytest.fixture(scope="module")
def privacy():
    text = README.read_text(encoding="utf-8")
    assert "## Privacy" in text, "the README has no Privacy section"
    section = text.split("## Privacy", 1)[1]
    # Stop at the next top-level heading.
    return section.split("\n## ", 1)[0]


def test_the_privacy_section_distinguishes_the_two_quick_start_options(privacy):
    assert "Option A" in privacy and "Option B" in privacy, (
        "the Privacy section makes one claim for both Quick Start options, but "
        "they put memories in entirely different places"
    )


def test_it_does_not_claim_the_hosted_path_keeps_data_local(privacy):
    """The exact sentence that was false, in the form it took."""
    assert "unless you explicitly configure a remote relay" not in privacy, (
        "the section still says nothing leaves the machine unless the user "
        "configures a relay — Option A is a hosted relay, offered first"
    )


def test_it_does_not_describe_the_synced_record_as_metadata(privacy):
    assert "engram metadata" not in privacy, (
        "the synced record carries the full value of each memory, not metadata"
    )


def test_it_says_full_content_is_stored_on_the_hosted_path(privacy):
    assert "full content" in privacy.lower(), (
        "the section does not tell the user that their memories' contents, not "
        "just keys or timestamps, are stored on the hosted relay"
    )


def test_it_does_not_tell_every_relay_user_the_server_is_theirs(privacy):
    """True for a self-hosted relay, false for the hosted one."""
    stray = [
        line.strip() for line in privacy.splitlines()
        if "your own relay server" in line and "Option B" not in line
    ]
    assert not stray, (
        f"unqualified 'your own relay server' claim: {stray}. On Option A the "
        "relay is operated by the project, not the user."
    )


def test_the_quick_start_points_at_the_privacy_section(privacy):
    """The disclosure has to be where the choice is made, not only at the end."""
    text = README.read_text(encoding="utf-8")
    quick_start = text.split("## Quick Start", 1)[1].split("\n## ", 1)[0]
    assert "Privacy" in quick_start or "privacy" in quick_start, (
        "Option A is chosen in the Quick Start, and nothing there mentions that "
        "it stores memories on someone else's server"
    )


@pytest.mark.skipif(not SYNC_ROUTE.exists(), reason="sync route not in this export")
def test_the_sync_record_still_carries_content():
    """Why the claim was wrong. If this changes, the Privacy wording can too."""
    source = SYNC_ROUTE.read_text(encoding="utf-8")
    assert '"value"' in source, (
        "the sync record no longer mentions a value field — re-check whether the "
        "README's 'full content' wording is still the accurate description"
    )
