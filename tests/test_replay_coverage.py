"""Comprehensive tests for mcp_server_nucleus.replay.

Covers ReplayEngine: load_atoms, filter_atoms, replay_as_system_prompt,
replay_to_engrams, replay_as_brain_seed, and run_replay CLI entry point.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus import replay
from mcp_server_nucleus.replay import ReplayEngine, run_replay


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain"
    b.mkdir()
    return b


@pytest.fixture
def engine(brain):
    return ReplayEngine(brain_path=brain)


@pytest.fixture
def sample_atoms():
    return [
        {
            "decision": "Use FastAPI for the API layer",
            "rationale": "Fast and modern framework",
            "evidence": ["benchmark1"],
            "confidence": 0.9,
            "tags": ["api", "architecture"],
            "sha256": "abc123",
            "source_tool": "claude",
            "source_session": "s1",
        },
        {
            "decision": "Use Postgres for the database",
            "rationale": "ACID compliance needed",
            "evidence": [],
            "confidence": 0.7,
            "tags": ["data"],
            "sha256": "def456",
            "source_tool": "ag",
            "source_session": "s2",
        },
        {
            "decision": "Low confidence decision",
            "rationale": "Extracted from artifact; rationale inferred from context.",
            "evidence": [],
            "confidence": 0.3,
            "tags": ["general"],
            "sha256": "ghi789",
            "source_tool": "windsurf",
            "source_session": "s3",
        },
    ]


# ── ReplayEngine.__init__ ──

class TestInit:
    def test_init_creates_replay_dir(self, brain):
        eng = ReplayEngine(brain_path=brain)
        assert eng.brain_path == brain
        assert eng.replay_dir.exists()
        assert eng.distill_dir == brain / "distill"


# ── load_atoms ──

class TestLoadAtoms:
    def test_no_file_auto_discover_empty(self, engine):
        assert engine.load_atoms() == []

    def test_load_from_explicit_path(self, engine, tmp_path, sample_atoms):
        jsonl = tmp_path / "atoms.jsonl"
        with open(jsonl, "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = engine.load_atoms(source_path=jsonl)
        assert len(result) == 3

    def test_load_skips_blank_lines(self, engine, tmp_path, sample_atoms):
        jsonl = tmp_path / "atoms.jsonl"
        with open(jsonl, "w") as f:
            f.write(json.dumps(sample_atoms[0]) + "\n")
            f.write("\n")
            f.write("   \n")
            f.write(json.dumps(sample_atoms[1]) + "\n")
        result = engine.load_atoms(source_path=jsonl)
        assert len(result) == 2

    def test_load_skips_invalid_json(self, engine, tmp_path, sample_atoms):
        jsonl = tmp_path / "atoms.jsonl"
        with open(jsonl, "w") as f:
            f.write(json.dumps(sample_atoms[0]) + "\n")
            f.write("not json\n")
            f.write(json.dumps(sample_atoms[1]) + "\n")
        result = engine.load_atoms(source_path=jsonl)
        assert len(result) == 2

    def test_auto_discover_latest(self, engine, sample_atoms):
        distill = engine.distill_dir
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms[:1]:
                f.write(json.dumps(atom) + "\n")
        with open(distill / "dca_20260102_000000.jsonl", "w") as f:
            for atom in sample_atoms[:2]:
                f.write(json.dumps(atom) + "\n")
        result = engine.load_atoms()
        assert len(result) == 2


# ── filter_atoms ──

class TestFilterAtoms:
    def test_no_filter(self, engine, sample_atoms):
        result = engine.filter_atoms(sample_atoms, max_atoms=100)
        assert len(result) == 3

    def test_min_confidence(self, engine, sample_atoms):
        result = engine.filter_atoms(sample_atoms, min_confidence=0.7, max_atoms=100)
        assert len(result) == 2
        assert all(a["confidence"] >= 0.7 for a in result)

    def test_tag_filter(self, engine, sample_atoms):
        result = engine.filter_atoms(sample_atoms, tags=["api"], max_atoms=100)
        assert len(result) == 1
        assert "api" in result[0]["tags"]

    def test_max_atoms(self, engine, sample_atoms):
        result = engine.filter_atoms(sample_atoms, max_atoms=1)
        assert len(result) == 1
        # Highest confidence first
        assert result[0]["confidence"] == 0.9

    def test_sorted_by_confidence(self, engine, sample_atoms):
        result = engine.filter_atoms(sample_atoms, max_atoms=100)
        confidences = [a["confidence"] for a in result]
        assert confidences == sorted(confidences, reverse=True)


# ── replay_as_system_prompt ──

class TestReplayAsSystemPrompt:
    def test_empty_atoms(self, engine):
        result = engine.replay_as_system_prompt([])
        assert "No Decision Context" in result

    def test_with_atoms(self, engine, sample_atoms):
        result = engine.replay_as_system_prompt(sample_atoms, min_confidence=0.0)
        assert "Sovereign Context Replay" in result
        assert "FastAPI" in result
        assert "Total Atoms" in result

    def test_auto_load_atoms(self, engine, sample_atoms):
        distill = engine.distill_dir
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = engine.replay_as_system_prompt(min_confidence=0.0)
        assert "Sovereign Context Replay" in result

    def test_rationale_shown_when_not_default(self, engine, sample_atoms):
        result = engine.replay_as_system_prompt(sample_atoms, min_confidence=0.0)
        assert "Why:" in result

    def test_rationale_hidden_when_default(self, engine):
        atoms = [{
            "decision": "A test decision that is long enough here",
            "rationale": "Extracted from artifact; rationale inferred from context.",
            "evidence": [],
            "confidence": 0.9,
            "tags": ["test"],
            "sha256": "x",
        }]
        result = engine.replay_as_system_prompt(atoms, min_confidence=0.0)
        # Default rationale should not show "Why:"
        assert "Why: Extracted from artifact" not in result

    def test_evidence_shown(self, engine):
        atoms = [{
            "decision": "A test decision that is long enough here",
            "rationale": "Custom rationale",
            "evidence": ["proof1", "proof2"],
            "confidence": 0.9,
            "tags": ["test"],
            "sha256": "x",
        }]
        result = engine.replay_as_system_prompt(atoms, min_confidence=0.0)
        assert "Evidence:" in result
        assert "proof1" in result

    def test_no_tags_uses_general(self, engine):
        atoms = [{
            "decision": "A test decision that is long enough here",
            "rationale": "Custom rationale",
            "evidence": [],
            "confidence": 0.9,
            "tags": [],
            "sha256": "x",
        }]
        result = engine.replay_as_system_prompt(atoms, min_confidence=0.0)
        assert "General" in result


# ── replay_to_engrams ──

class TestReplayToEngrams:
    def test_deposit_atoms(self, engine, sample_atoms):
        mock_vault = MagicMock()
        mock_vault.vault_file = str(engine.brain_path / "vault.jsonl")
        with patch("mcp_server_nucleus.runtime.dsor.EngramVault", return_value=mock_vault):
            result = engine.replay_to_engrams(sample_atoms, min_confidence=0.0, max_atoms=100)
        assert result["deposited"] == 3
        assert mock_vault.deposit.call_count == 3

    def test_auto_load_no_atoms(self, engine):
        mock_vault = MagicMock()
        mock_vault.vault_file = "path"
        with patch("mcp_server_nucleus.runtime.dsor.EngramVault", return_value=mock_vault):
            result = engine.replay_to_engrams(min_confidence=0.0)
        assert result["deposited"] == 0


# ── replay_as_brain_seed ──

class TestReplayAsBrainSeed:
    def test_create_seed(self, engine, sample_atoms, brain):
        result = engine.replay_as_brain_seed(sample_atoms, min_confidence=0.0, max_atoms=100)
        assert result["atom_count"] == 3
        seed_dir = Path(result["seed_dir"])
        assert seed_dir.exists()
        assert (seed_dir / "context_replay.md").exists()
        assert (seed_dir / "atoms.jsonl").exists()
        assert (seed_dir / "manifest.json").exists()

    def test_seed_manifest(self, engine, sample_atoms):
        result = engine.replay_as_brain_seed(sample_atoms, min_confidence=0.0, max_atoms=100)
        manifest_path = Path(result["seed_dir"]) / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["version"] == "1.0.0"
        assert manifest["atom_count"] == 3

    def test_seed_auto_load_empty(self, engine):
        result = engine.replay_as_brain_seed(min_confidence=0.0)
        assert result["atom_count"] == 0
        seed_dir = Path(result["seed_dir"])
        assert (seed_dir / "context_replay.md").exists()


# ── run_replay ──

class TestRunReplay:
    def test_no_atoms_found(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = run_replay(mode="system_prompt")
        assert result == {"error": "No DCAs found"}

    def test_system_prompt_mode(self, brain, monkeypatch, sample_atoms):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = run_replay(mode="system_prompt", min_confidence=0.0)
        assert result["mode"] == "system_prompt"
        assert "output" in result

    def test_engram_mode(self, brain, monkeypatch, sample_atoms):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        mock_vault = MagicMock()
        mock_vault.vault_file = "path"
        with patch("mcp_server_nucleus.runtime.dsor.EngramVault", return_value=mock_vault):
            result = run_replay(mode="engram", min_confidence=0.0)
        assert "deposited" in result

    def test_seed_mode(self, brain, monkeypatch, sample_atoms):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = run_replay(mode="seed", min_confidence=0.0)
        assert "seed_dir" in result
        assert "atom_count" in result

    def test_unknown_mode(self, brain, monkeypatch, sample_atoms):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = run_replay(mode="unknown", min_confidence=0.0)
        assert "error" in result
        assert "unknown" in result["error"].lower()

    def test_with_source_path(self, brain, monkeypatch, tmp_path, sample_atoms):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        jsonl = tmp_path / "custom.jsonl"
        with open(jsonl, "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = run_replay(mode="system_prompt", source=str(jsonl), min_confidence=0.0)
        assert result["mode"] == "system_prompt"
