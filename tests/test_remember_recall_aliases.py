"""Test remember/recall MCP tool aliases (issue #54).

Verifies that the 'remember' and 'recall' tool names work as aliases
for 'write_engram' and 'query_engrams' respectively.

Issue #54 asked for remember/recall MCP tools over existing engrams/history.jsonl.
The underlying tools (brain_write_engram, brain_query_engrams) already exist —
this test verifies the Week-1 vertical slice aliases are wired up.
"""
import pytest
from pathlib import Path
import re


ENGAMS_FILE = Path(__file__).resolve().parent.parent / "src" / "mcp_server_nucleus" / "tools" / "engrams.py"


def test_remember_alias_in_source():
    """The 'remember' tool alias should be in the engrams source."""
    source = ENGAMS_FILE.read_text()
    assert '"remember"' in source, (
        "'remember' alias not found in engrams.py — issue #54 requires this alias"
    )


def test_recall_alias_in_source():
    """The 'recall' tool alias should be in the engrams source."""
    source = ENGAMS_FILE.read_text()
    assert '"recall"' in source, (
        "'recall' alias not found in engrams.py — issue #54 requires this alias"
    )


def test_remember_calls_write_engram_impl():
    """'remember' should call _brain_write_engram_impl."""
    source = ENGAMS_FILE.read_text()
    # Find the remember line (not a comment) and verify it calls _brain_write_engram_impl
    remember_lines = [l for l in source.split("\n") if '"remember"' in l and not l.strip().startswith("#")]
    assert len(remember_lines) >= 1, "No 'remember' handler line found (non-comment)"
    assert "_brain_write_engram_impl" in remember_lines[0], (
        f"'remember' should call _brain_write_engram_impl. Line: {remember_lines[0]}"
    )


def test_recall_calls_query_engrams_impl():
    """'recall' should call _brain_query_engrams_impl."""
    source = ENGAMS_FILE.read_text()
    recall_lines = [l for l in source.split("\n") if '"recall"' in l and not l.strip().startswith("#")]
    assert len(recall_lines) >= 1, "No 'recall' handler line found (non-comment)"
    assert "_brain_query_engrams_impl" in recall_lines[0], (
        f"'recall' should call _brain_query_engrams_impl. Line: {recall_lines[0]}"
    )


def test_remember_and_recall_have_same_signature_as_originals():
    """'remember' and 'recall' should have the same parameters as their originals."""
    source = ENGAMS_FILE.read_text()
    lines = source.split("\n")

    # Find write_engram and remember lines
    write_line = next(l for l in lines if '"write_engram"' in l and "_brain_write_engram_impl" in l)
    remember_line = next(l for l in lines if '"remember"' in l and "_brain_write_engram_impl" in l)

    # Extract parameter lists
    def extract_params(line):
        m = re.search(r"lambda (\w+(?:, \w+(?:=\w+)?)*)", line)
        return m.group(1) if m else ""

    assert extract_params(write_line) == extract_params(remember_line), (
        f"Parameter mismatch: write_engram={extract_params(write_line)} "
        f"vs remember={extract_params(remember_line)}"
    )

    # Find query_engrams and recall lines
    query_line = next(l for l in lines if '"query_engrams"' in l and "_brain_query_engrams_impl" in l)
    recall_line = next(l for l in lines if '"recall"' in l and "_brain_query_engrams_impl" in l)

    assert extract_params(query_line) == extract_params(recall_line), (
        f"Parameter mismatch: query_engrams={extract_params(query_line)} "
        f"vs recall={extract_params(recall_line)}"
    )
