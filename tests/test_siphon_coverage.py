"""Comprehensive tests for mcp_server_nucleus.siphon.

Covers ArtifactSiphon: __init__, is_semantic_context, verify_affinity,
siphon_windsurf, siphon_antigravity, siphon_claude, generate_report,
and run_siphon.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.siphon import ArtifactSiphon, run_siphon


@pytest.fixture
def project(tmp_path):
    """Create a fake project with .brain dir."""
    p = tmp_path / "myproject"
    p.mkdir()
    brain = p / ".brain"
    brain.mkdir()
    return p


class TestInit:
    def test_init_with_project_root(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.project_root == project
        assert siphon.project_name == "myproject"
        assert siphon.brain_dir == project / ".brain"
        assert siphon.siphon_dir == project / ".brain" / "siphon"

    def test_init_auto_detect_from_brain(self, project, monkeypatch):
        brain = project / ".brain"
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        siphon = ArtifactSiphon()
        assert siphon.project_root == project

    def test_init_auto_detect_fallback_cwd(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "notbrain"))
        monkeypatch.chdir(tmp_path)
        siphon = ArtifactSiphon()
        assert siphon.project_root == tmp_path

    def test_allowed_extensions(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert ".md" in siphon.allowed_extensions
        assert ".txt" in siphon.allowed_extensions
        assert ".json" in siphon.allowed_extensions

    def test_blocked_extensions(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert ".exe" in siphon.blocked_extensions
        assert ".db" in siphon.blocked_extensions
        assert ".bin" in siphon.blocked_extensions

    def test_signatures(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert "myproject" in siphon.signatures
        assert "Nucleus" in siphon.signatures
        assert "mcp-server-nucleus" in siphon.signatures


class TestIsSemanticContext:
    def test_md_file_allowed(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.md"
        f.write_text("content")
        assert siphon.is_semantic_context(f) is True

    def test_txt_file_allowed(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.txt"
        f.write_text("content")
        assert siphon.is_semantic_context(f) is True

    def test_json_file_allowed(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.json"
        f.write_text("{}")
        assert siphon.is_semantic_context(f) is True

    def test_log_file_allowed(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.log"
        f.write_text("log entry")
        assert siphon.is_semantic_context(f) is True

    def test_exe_blocked(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.exe"
        f.write_text("binary")
        assert siphon.is_semantic_context(f) is False

    def test_db_blocked(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.db"
        f.write_text("data")
        assert siphon.is_semantic_context(f) is False

    def test_unknown_extension_blocked(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.py"
        f.write_text("code")
        assert siphon.is_semantic_context(f) is False

    def test_symlink_blocked(self, project, tmp_path):
        siphon = ArtifactSiphon(project_root=project)
        target = tmp_path / "target.md"
        target.write_text("x")
        link = project / "link.md"
        link.symlink_to(target)
        assert siphon.is_semantic_context(link) is False

    def test_large_file_blocked(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "big.md"
        f.write_text("x" * 1_100_000)
        assert siphon.is_semantic_context(f) is False

    def test_resolved_extension_allowed(self, project):
        siphon = ArtifactSiphon(project_root=project)
        f = project / "test.resolved"
        f.write_text("content")
        assert siphon.is_semantic_context(f) is True


class TestVerifyAffinity:
    def test_content_match(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.verify_affinity("This is about myproject") is True

    def test_content_match_nucleus(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.verify_affinity("This is about Nucleus") is True

    def test_path_match(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.verify_affinity("nothing here", project / "myproject_file.md") is True

    def test_no_match(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.verify_affinity("nothing relevant here") is False

    def test_no_path(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.verify_affinity("nothing relevant") is False

    def test_case_insensitive(self, project):
        siphon = ArtifactSiphon(project_root=project)
        assert siphon.verify_affinity("MYPROJECT is great") is True


class TestSiphonWindsurf:
    def test_no_tracker_home(self, project, monkeypatch):
        siphon = ArtifactSiphon(project_root=project)
        monkeypatch.setattr(Path, "home", lambda: project / "fakehome")
        result = siphon.siphon_windsurf()
        assert result == []

    def test_with_tracker_data(self, project, tmp_path, monkeypatch):
        siphon = ArtifactSiphon(project_root=project)
        # Create fake tracker home
        fake_home = tmp_path / "fakehome"
        tracker = fake_home / ".codeium" / "windsurf" / "code_tracker"
        proj_dir = tracker / "subdir" / f"{project.name}_session1"
        proj_dir.mkdir(parents=True)
        (proj_dir / "notes.md").write_text("myproject content")
        (proj_dir / "data.bin").write_text("binary")
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        result = siphon.siphon_windsurf()
        assert len(result) == 1
        assert "notes.md" in result[0]


class TestSiphonAntigravity:
    def test_no_brain_home(self, project, monkeypatch):
        siphon = ArtifactSiphon(project_root=project)
        monkeypatch.setattr(Path, "home", lambda: project / "fakehome")
        result = siphon.siphon_antigravity()
        assert result == []

    def test_with_sessions(self, project, tmp_path, monkeypatch):
        siphon = ArtifactSiphon(project_root=project)
        fake_home = tmp_path / "fakehome"
        brain = fake_home / ".gemini" / "antigravity" / "brain"
        session = brain / "session1"
        session.mkdir(parents=True)
        (session / "plan.md").write_text("myproject plan")
        (session / "data.bin").write_text("binary")
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        result = siphon.siphon_antigravity()
        assert len(result) == 1
        assert "plan.md" in result[0]

    def test_with_resolved_files(self, project, tmp_path, monkeypatch):
        siphon = ArtifactSiphon(project_root=project)
        fake_home = tmp_path / "fakehome"
        brain = fake_home / ".gemini" / "antigravity" / "brain"
        session = brain / "session1"
        session.mkdir(parents=True)
        (session / "task.resolved").write_text("myproject resolved")
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        result = siphon.siphon_antigravity()
        assert len(result) == 1

    def test_limit(self, project, tmp_path, monkeypatch):
        siphon = ArtifactSiphon(project_root=project)
        fake_home = tmp_path / "fakehome"
        brain = fake_home / ".gemini" / "antigravity" / "brain"
        for i in range(5):
            s = brain / f"session{i}"
            s.mkdir(parents=True)
            (s / "plan.md").write_text("myproject")
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        result = siphon.siphon_antigravity(limit=2)
        assert len(result) == 2


class TestSiphonClaude:
    def test_no_exports(self, project):
        siphon = ArtifactSiphon(project_root=project)
        result = siphon.siphon_claude()
        assert result == []

    def test_with_exports(self, project):
        siphon = ArtifactSiphon(project_root=project)
        export = project / "claude project export 1"
        export.mkdir()
        (export / "conv.md").write_text("myproject conversation")
        sub = export / "sub"
        sub.mkdir()
        (sub / "deep.md").write_text("myproject deep")
        result = siphon.siphon_claude()
        assert len(result) == 2

    def test_skips_non_semantic(self, project):
        siphon = ArtifactSiphon(project_root=project)
        export = project / "claude project export 1"
        export.mkdir()
        (export / "conv.md").write_text("myproject conversation")
        (export / "data.bin").write_text("binary")
        result = siphon.siphon_claude()
        assert len(result) == 1

    def test_skips_non_dir(self, project):
        siphon = ArtifactSiphon(project_root=project)
        (project / "claude project export file").write_text("not a dir")
        result = siphon.siphon_claude()
        assert result == []


class TestGenerateReport:
    def test_empty_stats(self, project):
        siphon = ArtifactSiphon(project_root=project)
        report = siphon.generate_report({"Windsurf": [], "Claude": []})
        assert report.exists()
        content = report.read_text()
        assert "Intellectual Context Siphon" in content
        assert "Total Context Gained**: 0" in content or "**Total Context Gained**: 0" in content

    def test_with_stats(self, project):
        siphon = ArtifactSiphon(project_root=project)
        stats = {
            "Windsurf": ["verified/session1/notes.md"],
            "Claude": ["verified/export1/conv.md", "root_file.md"],
        }
        report = siphon.generate_report(stats)
        content = report.read_text()
        assert "Windsurf" in content
        assert "Claude" in content
        assert "notes.md" in content
        assert "conv.md" in content
        assert "root" in content
        assert "Total Context Gained**: 3" in content or "**Total Context Gained**: 3" in content

    def test_report_in_vault(self, project):
        siphon = ArtifactSiphon(project_root=project)
        report = siphon.generate_report({})
        assert report.parent == project / ".brain" / "vault"


class TestRunSiphon:
    def test_no_context_found(self, project, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(project / ".brain"))
        monkeypatch.setattr(Path, "home", lambda: project / "fakehome")
        # Should not raise, just print
        run_siphon()

    def test_with_context(self, project, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(project / ".brain"))
        # Create a claude export
        export = project / "claude project export 1"
        export.mkdir()
        (export / "conv.md").write_text("myproject conversation")
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")
        run_siphon()
        # Report should be generated
        vault = project / ".brain" / "vault"
        assert vault.exists()
