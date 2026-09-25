"""Coverage tests for runtime/export.py."""
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.export import DataExporter


def test_init_creates_export_dir(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    de = DataExporter(brain)
    assert (brain / "exports").exists()


def test_export_full_state_empty(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    de = DataExporter(brain)
    res = de.export_full_state()
    assert res["status"] == "success"
    assert Path(res["path"]).exists()
    assert res["size_bytes"] > 0


def test_export_full_state_with_content(tmp_path):
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True)
    (brain / "memory").mkdir(parents=True)
    (brain / "ledger" / "state.json").write_text('{"k": "v"}')
    (brain / "memory" / "learnings.md").write_text("engram")
    de = DataExporter(brain)
    res = de.export_full_state()
    import zipfile
    with zipfile.ZipFile(res["path"]) as zf:
        names = zf.namelist()
    assert "metadata.json" in names
    assert "ledger/state.json" in names
    assert "memory/learnings.md" in names


def test_export_full_state_skips_missing_dirs(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    de = DataExporter(brain)
    res = de.export_full_state()
    assert res["status"] == "success"


def test_export_metadata_content(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    de = DataExporter(brain)
    res = de.export_full_state()
    import zipfile, json
    with zipfile.ZipFile(res["path"]) as zf:
        meta = json.loads(zf.read("metadata.json"))
    assert meta["version"] == "1.0"
    assert meta["system"] == "Nucleus Daemon Phase 59"
    assert "timestamp" in meta
