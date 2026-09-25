"""Comprehensive tests for mcp_server_nucleus.distill.

Covers DecisionAtom, VibeEngram, AntigravityAdapter, ClaudeAdapter,
WindsurfAdapter, DistillationEngine, _infer_tags_generic, and run_distill.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus import distill
from mcp_server_nucleus.distill import (
    DecisionAtom,
    VibeEngram,
    AntigravityAdapter,
    ClaudeAdapter,
    WindsurfAdapter,
    DistillationEngine,
    _infer_tags_generic,
    DCA_CONTEXT,
    DCA_TYPE,
    VIBE_TYPE,
    run_distill,
)


# ── DecisionAtom ──

class TestDecisionAtom:
    def test_init_defaults(self):
        atom = DecisionAtom(
            decision="Use FastAPI",
            rationale="Fast and modern",
            source_tool="claude",
            source_session="sess-1",
        )
        assert atom.decision == "Use FastAPI"
        assert atom.evidence == []
        assert atom.alternatives == []
        assert atom.confidence == 0.8
        assert atom.tags == []
        assert atom.timestamp is not None
        assert len(atom.sha256) == 16

    def test_init_with_all_fields(self):
        atom = DecisionAtom(
            decision="Dec",
            rationale="Why",
            source_tool="ag",
            source_session="s2",
            evidence=["e1", "e2"],
            alternatives=["a1"],
            confidence=0.95,
            tags=["arch"],
            timestamp="2026-01-01T00:00:00",
        )
        assert atom.evidence == ["e1", "e2"]
        assert atom.alternatives == ["a1"]
        assert atom.confidence == 0.95
        assert atom.tags == ["arch"]
        assert atom.timestamp == "2026-01-01T00:00:00"

    def test_compute_hash_deterministic(self):
        a1 = DecisionAtom("d", "r", "t", "s")
        a2 = DecisionAtom("d", "r", "t", "s")
        assert a1.sha256 == a2.sha256

    def test_compute_hash_differs(self):
        a1 = DecisionAtom("d1", "r", "t", "s")
        a2 = DecisionAtom("d2", "r", "t", "s")
        assert a1.sha256 != a2.sha256

    def test_to_jsonld(self):
        atom = DecisionAtom("d", "r", "t", "s", tags=["x"])
        ld = atom.to_jsonld()
        assert ld["@context"] == DCA_CONTEXT
        assert ld["@type"] == DCA_TYPE
        assert ld["decision"] == "d"
        assert ld["sha256"] == atom.sha256

    def test_to_adr_full(self):
        atom = DecisionAtom(
            decision="Use Postgres",
            rationale="ACID needed",
            source_tool="ag",
            source_session="sess1234567890",
            evidence=["e1"],
            alternatives=["MongoDB"],
            tags=["data"],
        )
        adr = atom.to_adr()
        assert "ADR: Use Postgres" in adr
        assert "ACID needed" in adr
        assert "## Evidence" in adr
        assert "- e1" in adr
        assert "## Alternatives Considered" in adr
        assert "- MongoDB" in adr
        assert "**Tags**: data" in adr

    def test_to_adr_minimal(self):
        atom = DecisionAtom("d", "r", "t", "s")
        adr = atom.to_adr()
        assert "ADR: d" in adr
        assert "## Evidence" not in adr
        assert "## Alternatives" not in adr


# ── VibeEngram ──

class TestVibeEngram:
    def test_init_and_jsonld(self):
        ve = VibeEngram(
            patterns=["concise"],
            tone="formal",
            vocabulary=["henceforth"],
            source_tool="claude",
            source_session="s1",
        )
        ld = ve.to_jsonld()
        assert ld["@context"] == DCA_CONTEXT
        assert ld["@type"] == VIBE_TYPE
        assert ld["patterns"] == ["concise"]
        assert ld["tone"] == "formal"
        assert ld["vocabulary"] == ["henceforth"]
        assert ld["source_tool"] == "claude"


# ── _infer_tags_generic ──

class TestInferTagsGeneric:
    def test_architecture_tag(self):
        tags = _infer_tags_generic("The architecture design pattern", "file.md")
        assert "architecture" in tags

    def test_deployment_tag(self):
        tags = _infer_tags_generic("Deploy to render cloud docker", "file.md")
        assert "deployment" in tags

    def test_testing_tag(self):
        tags = _infer_tags_generic("Run the test verify assert", "file.md")
        assert "testing" in tags

    def test_security_tag(self):
        tags = _infer_tags_generic("Security auth encrypt sign audit", "file.md")
        assert "security" in tags

    def test_performance_tag(self):
        tags = _infer_tags_generic("Performance latency speed optimize", "file.md")
        assert "performance" in tags

    def test_api_tag(self):
        tags = _infer_tags_generic("API endpoint route handler", "file.md")
        assert "api" in tags

    def test_data_tag(self):
        tags = _infer_tags_generic("Database schema migration model", "file.md")
        assert "data" in tags

    def test_ui_tag(self):
        tags = _infer_tags_generic("UI frontend component design", "file.md")
        assert "ui" in tags

    def test_plan_filename_tag(self):
        tags = _infer_tags_generic("some text", "implementation_plan.md")
        assert "planned" in tags

    def test_walkthrough_filename_tag(self):
        tags = _infer_tags_generic("some text", "walkthrough.md")
        assert "verified" in tags

    def test_no_tags(self):
        tags = _infer_tags_generic("hello world", "file.md")
        assert tags == []


# ── AntigravityAdapter ──

class TestAntigravityAdapter:
    def test_discover_sessions_no_brain(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path / "nonexistent")
        assert adapter.discover_sessions() == []

    def test_discover_sessions_with_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        s1 = brain / "session1"
        s1.mkdir()
        (s1 / "f.md").write_text("x")
        s2 = brain / "session2"
        s2.mkdir()
        (s2 / "f.md").write_text("x")
        adapter = AntigravityAdapter(brain_root=brain)
        sessions = adapter.discover_sessions(limit=5)
        assert len(sessions) == 2

    def test_discover_sessions_limit(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        for i in range(5):
            d = brain / f"s{i}"
            d.mkdir()
            (d / "f.md").write_text("x")
        adapter = AntigravityAdapter(brain_root=brain)
        sessions = adapter.discover_sessions(limit=2)
        assert len(sessions) == 2

    def test_extract_from_session_empty(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        adapter = AntigravityAdapter(brain_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert atoms == []

    def test_extract_from_session_with_plan(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        plan = session / "implementation_plan.md"
        plan.write_text(
            "#### [MODIFY] [src/app.py]\nChange the handler to use FastAPI.\n"
        )
        adapter = AntigravityAdapter(brain_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert len(atoms) >= 1
        assert any("app.py" in a.decision for a in atoms)

    def test_extract_from_session_with_tasks(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        task = session / "task.md"
        task.write_text("- [x] Implement the authentication module properly\n")
        adapter = AntigravityAdapter(brain_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert any("Completed" in a.decision for a in atoms)

    def test_extract_from_session_decision_pattern(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        doc = session / "doc.md"
        doc.write_text(
            "**Decision**: We will use a three-layer architecture for the system design here.\n"
        )
        adapter = AntigravityAdapter(brain_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert len(atoms) >= 1

    def test_extract_decisions_dedup(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path)
        content = "**Decision**: We will use a three-layer architecture for the system design here.\n"
        atoms1 = adapter._extract_decisions(content, "s1", "doc.md")
        atoms2 = adapter._extract_decisions(content, "s1", "doc.md")
        # Same content+session => same hash => dedup
        all_atoms = adapter._extract_decisions(content + content, "s1", "doc.md")
        # Should dedup identical atoms
        hashes = [a.sha256 for a in all_atoms]
        assert len(hashes) == len(set(hashes))

    def test_extract_decisions_short_text_filtered(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path)
        content = "**Decision**: short\n"
        atoms = adapter._extract_decisions(content, "s1", "doc.md")
        assert atoms == []

    def test_extract_from_plan_empty_details(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path)
        content = "#### [MODIFY] [src/app.py]\n\n#### [NEW] [other.py]\n"
        atoms = adapter._extract_from_plan(content, "s1")
        # Empty details should produce no atoms
        assert atoms == []

    def test_find_nearby_rationale_found(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path)
        content = "**Decision**: something here\n**Reason**: because of performance needs\n"
        rationale = adapter._find_nearby_rationale(content, 0)
        assert rationale is not None
        assert "performance" in rationale

    def test_find_nearby_rationale_not_found(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path)
        content = "**Decision**: something here with no rationale nearby at all\n"
        rationale = adapter._find_nearby_rationale(content, 0)
        assert rationale is None

    def test_infer_tags(self, tmp_path):
        adapter = AntigravityAdapter(brain_root=tmp_path)
        tags = adapter._infer_tags("The architecture design", "plan.md")
        assert "architecture" in tags
        assert "planned" in tags

    def test_extract_from_session_read_exception(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        f = session / "bad.md"
        f.write_text("good content here")
        adapter = AntigravityAdapter(brain_root=tmp_path)
        with patch("pathlib.Path.read_text", side_effect=Exception("read fail")):
            atoms = adapter.extract_from_session(session)
        assert atoms == []

    def test_extract_from_session_large_file_skipped(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        f = session / "big.md"
        f.write_text("x" * 600_000)
        adapter = AntigravityAdapter(brain_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert atoms == []


# ── ClaudeAdapter ──

class TestClaudeAdapter:
    def test_discover_sessions_empty(self, tmp_path):
        adapter = ClaudeAdapter(project_root=tmp_path, brain_path=tmp_path / ".brain")
        assert adapter.discover_sessions() == []

    def test_discover_sessions_with_exports(self, tmp_path):
        export = tmp_path / "claude project export 1"
        export.mkdir()
        (export / "f.md").write_text("x")
        adapter = ClaudeAdapter(project_root=tmp_path)
        sessions = adapter.discover_sessions()
        assert len(sessions) == 1

    def test_discover_sessions_with_siphon(self, tmp_path):
        brain = tmp_path / ".brain"
        siphon = brain / "siphon" / "claude" / "verified"
        siphon.mkdir(parents=True)
        s = siphon / "session1"
        s.mkdir()
        (s / "f.md").write_text("x")
        adapter = ClaudeAdapter(project_root=tmp_path, brain_path=brain)
        sessions = adapter.discover_sessions()
        assert len(sessions) == 1

    def test_extract_from_session_md(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        md = session / "conv.md"
        md.write_text(
            "### Assistant\n"
            "**Decision**: We will use a three-layer architecture for the system design here.\n"
        )
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert len(atoms) >= 1

    def test_extract_from_session_fallback_no_assistant(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        md = session / "conv.md"
        md.write_text(
            "**Decision**: We will use a three-layer architecture for the system design here.\n"
        )
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert len(atoms) >= 1

    def test_extract_from_session_completed_tasks(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        md = session / "conv.md"
        md.write_text("- [x] Implement the authentication module properly now\n")
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert any("Completed" in a.decision for a in atoms)

    def test_extract_from_session_code_decision(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        md = session / "conv.md"
        md.write_text(
            "```python\n# DECISION: Use connection pooling for the database layer\n"
            "pass\n```\n"
        )
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert any("connection pooling" in a.decision for a in atoms)

    def test_extract_from_session_large_file_skipped(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        md = session / "big.md"
        md.write_text("x" * 1_100_000)
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert atoms == []

    def test_extract_from_conversations_json_list(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        conv_json = session / "conversations.json"
        conv_json.write_text(json.dumps([
            {
                "name": "test-conv",
                "chat_messages": [
                    {
                        "sender": "assistant",
                        "text": "**Decision**: We will use a three-layer architecture for the system design here.",
                    }
                ],
            }
        ]))
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter._extract_from_conversations_json(conv_json, "s1")
        assert len(atoms) >= 1

    def test_extract_from_conversations_json_single(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        conv_json = session / "conversations.json"
        conv_json.write_text(json.dumps({
            "title": "test",
            "messages": [
                {"role": "assistant", "content": "**Decision**: We will use a three-layer architecture for the system design here."}
            ],
        }))
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter._extract_from_conversations_json(conv_json, "s1")
        assert len(atoms) >= 1

    def test_extract_from_conversations_json_invalid(self, tmp_path):
        conv_json = tmp_path / "conv.json"
        conv_json.write_text("not json")
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter._extract_from_conversations_json(conv_json, "s1")
        assert atoms == []

    def test_extract_from_conversations_json_short_text(self, tmp_path):
        conv_json = tmp_path / "conv.json"
        conv_json.write_text(json.dumps([
            {"name": "c", "chat_messages": [{"sender": "assistant", "text": "short"}]}
        ]))
        adapter = ClaudeAdapter(project_root=tmp_path)
        atoms = adapter._extract_from_conversations_json(conv_json, "s1")
        assert atoms == []

    def test_dedup(self, tmp_path):
        a1 = DecisionAtom("d", "r", "t", "s")
        a2 = DecisionAtom("d", "r", "t", "s")
        adapter = ClaudeAdapter(project_root=tmp_path)
        result = adapter._dedup([a1, a2])
        assert len(result) == 1

    def test_extract_from_session_read_exception(self, tmp_path):
        session = tmp_path / "export"
        session.mkdir()
        md = session / "conv.md"
        md.write_text("content")
        adapter = ClaudeAdapter(project_root=tmp_path)
        with patch("pathlib.Path.read_text", side_effect=Exception("fail")):
            atoms = adapter.extract_from_session(session)
        assert atoms == []


# ── WindsurfAdapter ──

class TestWindsurfAdapter:
    def test_discover_sessions_empty(self, tmp_path):
        adapter = WindsurfAdapter(project_root=tmp_path, brain_path=tmp_path / ".brain")
        assert adapter.discover_sessions() == []

    def test_discover_sessions_with_siphon(self, tmp_path):
        brain = tmp_path / ".brain"
        siphon = brain / "siphon" / "windsurf" / "verified"
        siphon.mkdir(parents=True)
        s = siphon / "session1"
        s.mkdir()
        (s / "f.md").write_text("x")
        adapter = WindsurfAdapter(project_root=tmp_path, brain_path=brain)
        sessions = adapter.discover_sessions()
        assert len(sessions) == 1

    def test_extract_from_session_decision(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        md = session / "snap.md"
        md.write_text(
            "**Decision**: We will use a three-layer architecture for the system design here.\n"
        )
        adapter = WindsurfAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert len(atoms) >= 1

    def test_extract_from_session_completed(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        md = session / "snap.md"
        md.write_text("- [x] Implement the authentication module properly now\n")
        adapter = WindsurfAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert any("Completed" in a.decision for a in atoms)

    def test_extract_from_session_txt_file(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        txt = session / "notes.txt"
        txt.write_text(
            "**Decision**: We will use a three-layer architecture for the system design here.\n"
        )
        adapter = WindsurfAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert len(atoms) >= 1

    def test_extract_from_session_large_file_skipped(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        md = session / "big.md"
        md.write_text("x" * 600_000)
        adapter = WindsurfAdapter(project_root=tmp_path)
        atoms = adapter.extract_from_session(session)
        assert atoms == []

    def test_extract_from_session_read_exception(self, tmp_path):
        session = tmp_path / "session"
        session.mkdir()
        md = session / "snap.md"
        md.write_text("content")
        adapter = WindsurfAdapter(project_root=tmp_path)
        with patch("pathlib.Path.read_text", side_effect=Exception("fail")):
            atoms = adapter.extract_from_session(session)
        assert atoms == []

    def test_dedup(self, tmp_path):
        a1 = DecisionAtom("d", "r", "t", "s")
        a2 = DecisionAtom("d", "r", "t", "s")
        adapter = WindsurfAdapter(project_root=tmp_path)
        result = adapter._dedup([a1, a2])
        assert len(result) == 1


# ── DistillationEngine ──

class TestDistillationEngine:
    def test_init(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        assert engine.brain_path == brain
        assert engine.distill_dir.exists()
        assert "antigravity" in engine.adapters
        assert "claude" in engine.adapters
        assert "windsurf" in engine.adapters

    def test_distill_all_empty(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        # Mock all adapters to return no sessions
        for adapter in engine.adapters.values():
            adapter.discover_sessions = lambda limit=5: []
        result = engine.distill(source="all", output_format="jsonld")
        assert result["total_atoms"] == 0
        assert "jsonld" in result["output_paths"]

    def test_distill_unknown_source(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        result = engine.distill(source="unknown", output_format="jsonld")
        assert result["total_atoms"] == 0
        assert result["by_source"] == {}

    def test_distill_output_engram(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        for adapter in engine.adapters.values():
            adapter.discover_sessions = lambda limit=5: []
        result = engine.distill(source="all", output_format="engram")
        assert "engram" in result["output_paths"]

    def test_distill_output_both(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        for adapter in engine.adapters.values():
            adapter.discover_sessions = lambda limit=5: []
        result = engine.distill(source="all", output_format="both")
        assert "jsonld" in result["output_paths"]
        assert "engram" in result["output_paths"]

    def test_write_jsonld(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        atom = DecisionAtom("d", "r", "t", "s")
        path = engine._write_jsonld([atom], "20260101_000000")
        assert path.exists()
        content = path.read_text()
        assert json.loads(content.strip())["@type"] == DCA_TYPE

    def test_write_engram(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        atom = DecisionAtom("d", "r", "t", "s", tags=["arch"], evidence=["e1"])
        path = engine._write_engram([atom], "20260101_000000")
        assert path.exists()
        content = path.read_text()
        assert "Sovereign Context Engram" in content
        assert "Arch" in content

    def test_write_engram_empty_tags(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        atom = DecisionAtom("d", "r", "t", "s")
        path = engine._write_engram([atom], "20260101_000000")
        content = path.read_text()
        assert "General" in content

    def test_distill_with_atoms(self, tmp_path):
        brain = tmp_path / ".brain"
        engine = DistillationEngine(brain_path=brain)
        # Mock adapter to return atoms
        mock_adapter = MagicMockAdapter()
        engine.adapters = {"mock": mock_adapter}
        result = engine.distill(source="mock", output_format="jsonld")
        assert result["total_atoms"] == 1


class MagicMockAdapter:
    TOOL_NAME = "mock"

    def discover_sessions(self, limit=5):
        return [Path("/tmp")]

    def extract_from_session(self, session_path):
        return [DecisionAtom("test decision here", "rationale", "mock", "s1")]


# ── run_distill ──

class TestRunDistill:
    def test_run_distill(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch.object(DistillationEngine, "__init__", lambda self, brain_path=None: (
            setattr(self, "brain_path", brain),
            setattr(self, "distill_dir", brain / "distill"),
            (brain / "distill").mkdir(parents=True, exist_ok=True),
            setattr(self, "adapters", {}),
            None,
        )[-1]):
            result = run_distill(source="all", limit=1, output="jsonld")
        assert "total_atoms" in result
        assert "output_paths" in result
