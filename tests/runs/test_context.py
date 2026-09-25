"""R3 context adapter tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.context import BrainContext, ContextEscape, ProjectContext
from mcp_server_nucleus.runs.workspace import CopyWorkspaceBackend


def test_brain_context_read_text_and_list_markdown(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    notes = brain / "notes"
    notes.mkdir()
    (notes / "a.md").write_text("# A")
    (notes / "b.md").write_text("# B")

    ctx = BrainContext(brain)
    assert ctx.exists("notes/a.md")
    assert ctx.read_text("notes/a.md") == "# A"
    assert ctx.list_markdown("notes") == ["notes/a.md", "notes/b.md"]


def test_brain_context_read_jsonl_tail(tmp_path):
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True)
    with open(brain / "ledger" / "events.jsonl", "w") as f:
        f.write(json.dumps({"seq": 1}) + "\n")
        f.write(json.dumps({"seq": 2}) + "\n")

    ctx = BrainContext(brain)
    records = ctx.read_jsonl_tail("ledger/events.jsonl", limit=2)
    assert records == [{"seq": 1}, {"seq": 2}]


def test_brain_context_rejects_escape(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    ctx = BrainContext(brain)
    with pytest.raises(ContextEscape):
        ctx.read_text("../etc/passwd")


def test_project_context_read_and_list_files(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("# code")

    backend = CopyWorkspaceBackend()
    ws = backend.create(project, "ctx-1")
    try:
        ctx = ProjectContext(ws, backend)
        assert ctx.read("src/main.py") == "# code"
        assert "src/main.py" in ctx.list_files()
    finally:
        backend.dispose(ws)


def test_project_context_rejects_escape(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "file.txt").write_text("safe")

    backend = CopyWorkspaceBackend()
    ws = backend.create(project, "ctx-2")
    try:
        ctx = ProjectContext(ws, backend)
        with pytest.raises(ContextEscape):
            ctx.read("../etc/passwd")
    finally:
        backend.dispose(ws)
