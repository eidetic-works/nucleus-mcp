"""Comprehensive tests for mcp_server_nucleus.runtime.consolidation_ops.

Covers _get_archive_path, _rotate_jsonl_if_needed, _rotate_all_jsonl,
_archive_resolved_files, _detect_redundant_artifacts, _generate_merge_proposals,
_garbage_collect_tasks.
"""
import json
import os
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import consolidation_ops


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    """Set up a brain directory and env var."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


# ── _get_archive_path ──

class TestGetArchivePath:
    def test_creates_archive_dir(self, brain_env):
        result = consolidation_ops._get_archive_path()
        assert result == brain_env / "archive"
        assert result.exists()


# ── _rotate_jsonl_if_needed ──

class TestRotateJsonl:
    def test_file_missing(self, brain_env):
        path = brain_env / "nonexistent.jsonl"
        result = consolidation_ops._rotate_jsonl_if_needed(path)
        assert result == {"rotated": False, "reason": "file_missing"}

    def test_under_threshold(self, brain_env):
        path = brain_env / "ledger" / "events.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text('{"a": 1}\n')
        result = consolidation_ops._rotate_jsonl_if_needed(path, max_mb=50.0)
        assert result["rotated"] is False
        assert result["reason"] == "under_threshold"

    def test_few_lines(self, brain_env):
        path = brain_env / "ledger" / "events.jsonl"
        path.parent.mkdir(parents=True)
        # Create a large file with few lines
        path.write_text('{"big": "' + "x" * 60000 + '"}\n')
        result = consolidation_ops._rotate_jsonl_if_needed(path, keep_lines=1000, max_mb=0.05)
        assert result["rotated"] is False
        assert result["reason"] == "few_lines"

    def test_rotation_success(self, brain_env):
        path = brain_env / "ledger" / "events.jsonl"
        path.parent.mkdir(parents=True)
        # Create 100 lines, keep 10
        lines = [json.dumps({"i": i, "data": "x" * 600}) for i in range(100)]
        path.write_text("\n".join(lines) + "\n")
        result = consolidation_ops._rotate_jsonl_if_needed(path, keep_lines=10, max_mb=0.05)
        assert result["rotated"] is True
        assert result["archived_lines"] == 90
        assert result["kept_lines"] == 10
        # Verify archive file
        archive_file = Path(result["archive_file"])
        assert archive_file.exists()
        # Verify kept file
        kept = path.read_text().strip().split("\n")
        assert len(kept) == 10


# ── _rotate_all_jsonl ──

class TestRotateAllJsonl:
    def test_no_files(self, brain_env):
        results = consolidation_ops._rotate_all_jsonl()
        assert len(results) == 3
        for r in results:
            assert r["rotated"] is False

    def test_with_files(self, brain_env):
        # Create events.jsonl
        events = brain_env / "ledger" / "events.jsonl"
        events.parent.mkdir(parents=True)
        events.write_text('{"a": 1}\n')
        # Create interaction_log.jsonl
        ilog = brain_env / "ledger" / "interaction_log.jsonl"
        ilog.write_text('{"b": 2}\n')
        # Create error_telemetry.jsonl
        etel = brain_env / "metrics" / "error_telemetry.jsonl"
        etel.parent.mkdir(parents=True)
        etel.write_text('{"c": 3}\n')
        results = consolidation_ops._rotate_all_jsonl()
        assert len(results) == 3
        names = [r["file"] for r in results]
        assert "events.jsonl" in names


# ── _archive_resolved_files ──

class TestArchiveResolvedFiles:
    def test_no_files(self, brain_env):
        result = consolidation_ops._archive_resolved_files()
        assert result["success"] is True
        assert result["files_moved"] == 0

    def test_moves_resolved_files(self, brain_env):
        (brain_env / "test.md.resolved").write_text("resolved content")
        (brain_env / "other.md.resolved.1").write_text("version 1")
        result = consolidation_ops._archive_resolved_files()
        assert result["success"] is True
        assert result["files_moved"] == 2
        archive_dir = brain_env / "archive" / "resolved"
        assert (archive_dir / "test.md.resolved").exists()
        assert (archive_dir / "other.md.resolved.1").exists()

    def test_moves_metadata_files(self, brain_env):
        (brain_env / "file.metadata.json").write_text('{"meta": true}')
        result = consolidation_ops._archive_resolved_files()
        assert result["success"] is True
        assert result["files_moved"] == 1

    def test_duplicate_name_in_archive(self, brain_env):
        archive_dir = brain_env / "archive" / "resolved"
        archive_dir.mkdir(parents=True)
        (archive_dir / "dup.md.resolved").write_text("existing")
        (brain_env / "dup.md.resolved").write_text("new")
        result = consolidation_ops._archive_resolved_files()
        assert result["success"] is True
        # Original archived file still exists
        assert (archive_dir / "dup.md.resolved").exists()
        # Dedup creates: stem + .dupN + suffix = dup.md.dup1.resolved
        assert any("dup.md.dup" in f.name and f.name.endswith(".resolved")
                    for f in archive_dir.iterdir())

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consolidation_ops, "get_brain_path",
                            lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        result = consolidation_ops._archive_resolved_files()
        assert result["success"] is False
        assert "fail" in result["error"]


# ── _detect_redundant_artifacts ──

class TestDetectRedundantArtifacts:
    def test_empty_brain(self, brain_env):
        result = consolidation_ops._detect_redundant_artifacts()
        assert result["success"] is True
        assert result["total_files_scanned"] == 0

    def test_versioned_duplicates(self, brain_env):
        (brain_env / "implementation_plan.md").write_text("old plan")
        (brain_env / "IMPLEMENTATION_PLAN_V0_4_0.md").write_text("new plan")
        result = consolidation_ops._detect_redundant_artifacts()
        assert result["success"] is True
        assert len(result["findings"]["versioned_duplicates"]) > 0

    def test_related_series(self, brain_env):
        for i in range(4):
            (brain_env / f"SYNTHESIS_PART{i}.md").write_text(f"part {i}")
        result = consolidation_ops._detect_redundant_artifacts()
        assert result["success"] is True
        assert len(result["findings"]["related_series"]) > 0

    def test_stale_files(self, brain_env):
        old_file = brain_env / "old_notes.md"
        old_file.write_text("old content")
        # Set mtime to 40 days ago
        old_time = time.time() - (40 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))
        result = consolidation_ops._detect_redundant_artifacts()
        assert result["success"] is True
        assert len(result["findings"]["stale_files"]) > 0

    def test_stale_preserved_files_skipped(self, brain_env):
        old_file = brain_env / "NORTH_STAR.md"
        old_file.write_text("star")
        old_time = time.time() - (40 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))
        result = consolidation_ops._detect_redundant_artifacts()
        assert len(result["findings"]["stale_files"]) == 0

    def test_archive_candidates(self, brain_env):
        (brain_env / "test_exploration.md").write_text("exploration")
        (brain_env / "test_draft.md").write_text("draft")
        result = consolidation_ops._detect_redundant_artifacts()
        assert result["success"] is True
        assert len(result["findings"]["archive_candidates"]) >= 2

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consolidation_ops, "get_brain_path",
                            lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        result = consolidation_ops._detect_redundant_artifacts()
        assert result["success"] is False
        assert "fail" in result["error"]


# ── _generate_merge_proposals ──

class TestGenerateMergeProposals:
    def test_empty_brain(self, brain_env):
        result = consolidation_ops._generate_merge_proposals()
        assert result["success"] is True
        assert result["total_proposals"] == 0
        assert "Brain is clean" in result["proposal_text"]

    def test_with_findings(self, brain_env):
        (brain_env / "plan.md").write_text("old")
        (brain_env / "PLAN_V0_4_0.md").write_text("new")
        result = consolidation_ops._generate_merge_proposals()
        assert result["success"] is True
        assert result["total_proposals"] > 0
        assert "Versioned Duplicates" in result["proposal_text"]

    def test_detection_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consolidation_ops, "get_brain_path",
                            lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        result = consolidation_ops._generate_merge_proposals()
        assert result["success"] is False

    def test_stale_files_section(self, brain_env):
        old_file = brain_env / "old_notes.md"
        old_file.write_text("old")
        old_time = time.time() - (40 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))
        result = consolidation_ops._generate_merge_proposals()
        assert "Stale Files" in result["proposal_text"]

    def test_archive_candidates_section(self, brain_env):
        (brain_env / "test_exploration.md").write_text("explore")
        result = consolidation_ops._generate_merge_proposals()
        assert "Archive Candidates" in result["proposal_text"]

    def test_related_series_section(self, brain_env):
        for i in range(4):
            (brain_env / f"SYNTHESIS_PART{i}.md").write_text(f"part {i}")
        result = consolidation_ops._generate_merge_proposals()
        assert "Related File Series" in result["proposal_text"]

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consolidation_ops, "_detect_redundant_artifacts",
                            lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        result = consolidation_ops._generate_merge_proposals()
        assert result["success"] is False


# ── _garbage_collect_tasks ──

class TestGarbageCollectTasks:
    def test_no_tasks_file(self, brain_env):
        result = consolidation_ops._garbage_collect_tasks()
        assert result["success"] is True
        assert result["archived"] == 0
        assert result["kept"] == 0

    def test_empty_tasks_list(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks_file.write_text("[]")
        result = consolidation_ops._garbage_collect_tasks()
        assert result["success"] is True
        assert result["archived"] == 0

    def test_empty_tasks_dict(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks_file.write_text('{"tasks": []}')
        result = consolidation_ops._garbage_collect_tasks()
        assert result["success"] is True

    def test_keeps_in_progress(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = [{"id": "t1", "status": "IN_PROGRESS", "description": "active"}]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["kept"] == 1
        assert result["archived"] == 0

    def test_keeps_done(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = [{"id": "t1", "status": "DONE", "description": "done"}]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["kept"] == 1

    def test_archives_auto_generated(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = [{"id": "auto_1", "status": "PENDING", "description": "auto task",
                  "updated_at": "2099-01-01T00:00:00"}]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["archived"] == 1

    def test_archives_stale(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        old_date = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 100 * 3600))
        tasks = [{"id": "t1", "status": "PENDING", "description": "stale task",
                  "updated_at": old_date}]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["archived"] == 1

    def test_dry_run(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = [{"id": "auto_1", "status": "PENDING", "description": "auto"}]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks(dry_run=True)
        assert result["dry_run"] is True
        assert result["archived"] == 1
        # File should not be modified
        assert json.loads(tasks_file.read_text()) == tasks

    def test_dedup_keeps_newest(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = [
            {"id": "t1", "status": "PENDING", "description": "duplicate task",
             "updated_at": "2026-01-01T00:00:00"},
            {"id": "t2", "status": "PENDING", "description": "duplicate task",
             "updated_at": "2026-06-01T00:00:00"},
        ]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["archived"] >= 1

    def test_dict_format_with_tasks_key(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = {"tasks": [{"id": "auto_1", "status": "PENDING", "description": "auto"}]}
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["archived"] == 1
        # Verify file was rewritten with tasks key
        saved = json.loads(tasks_file.read_text())
        assert "tasks" in saved

    def test_non_dict_non_list_tasks(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks_file.write_text('{"other": "data"}')
        result = consolidation_ops._garbage_collect_tasks()
        assert result["success"] is True
        assert result["archived"] == 0

    def test_non_dict_items_skipped(self, brain_env):
        tasks_file = brain_env / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True)
        tasks = ["not a dict", 42, {"id": "auto_1", "status": "PENDING", "description": "auto"}]
        tasks_file.write_text(json.dumps(tasks))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["archived"] == 1

    def test_exception_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consolidation_ops, "get_brain_path",
                            lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        result = consolidation_ops._garbage_collect_tasks()
        assert result["success"] is False
        assert "fail" in result["error"]
