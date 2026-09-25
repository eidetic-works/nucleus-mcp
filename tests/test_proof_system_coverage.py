"""
Coverage tests for runtime/capabilities/proof_system.py
"""
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.capabilities.proof_system import ProofSystem


@pytest.fixture
def proof_system(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return ProofSystem()


@pytest.fixture
def proof_system_default(monkeypatch, tmp_path):
    """ProofSystem with no env var set (uses default .brain)."""
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    return ProofSystem()


# ---------------------------------------------------------------------------
# Properties & Init
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, proof_system):
        assert proof_system.name == "proof_system"

    def test_description(self, proof_system):
        assert "proof" in proof_system.description.lower() or "evidence" in proof_system.description.lower()

    def test_init_creates_proofs_dir(self, proof_system, tmp_path):
        proofs_dir = tmp_path / ".brain" / "features" / "proofs"
        assert proofs_dir.exists()

    def test_init_default_brain_path(self, proof_system_default, tmp_path):
        assert proof_system_default.brain_path == Path(".brain")
        assert proof_system_default.proofs_dir.exists()


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_three_tools(self, proof_system):
        tools = proof_system.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_generate_proof" in names
        assert "brain_get_proof" in names
        assert "brain_list_proofs" in names

    def test_generate_proof_required(self, proof_system):
        tools = proof_system.get_tools()
        tool = [t for t in tools if t["name"] == "brain_generate_proof"][0]
        assert tool["parameters"]["required"] == ["feature_id"]

    def test_get_proof_required(self, proof_system):
        tools = proof_system.get_tools()
        tool = [t for t in tools if t["name"] == "brain_get_proof"][0]
        assert tool["parameters"]["required"] == ["feature_id"]


# ---------------------------------------------------------------------------
# _generate_proof
# ---------------------------------------------------------------------------
class TestGenerateProof:
    def test_generate_minimal(self, proof_system):
        result = proof_system._generate_proof({"feature_id": "test_feature"})
        assert result["success"] is True
        assert "test_feature" in result["message"]
        file_path = proof_system.proofs_dir / "test_feature.md"
        assert file_path.exists()
        content = file_path.read_text()
        assert "test_feature" in content
        assert "No thinking provided" in content
        assert "N/A" in content

    def test_generate_full(self, proof_system):
        result = proof_system._generate_proof({
            "feature_id": "full_feature",
            "thinking": "I decided to do X because Y",
            "deployed_url": "https://app.example.com",
            "files_changed": ["src/main.py", "tests/test_main.py"],
            "risk_level": "high",
            "rollback_time": "5 minutes"
        })
        assert result["success"] is True
        content = (proof_system.proofs_dir / "full_feature.md").read_text()
        assert "I decided to do X because Y" in content
        assert "https://app.example.com" in content
        assert "src/main.py" in content
        assert "tests/test_main.py" in content
        assert "HIGH" in content
        assert "5 minutes" in content

    def test_generate_with_empty_files(self, proof_system):
        result = proof_system._generate_proof({
            "feature_id": "empty_files",
            "files_changed": []
        })
        assert result["success"] is True
        content = (proof_system.proofs_dir / "empty_files.md").read_text()
        assert "None" in content

    def test_generate_overwrites_existing(self, proof_system):
        proof_system._generate_proof({"feature_id": "overwrite_test", "thinking": "v1"})
        proof_system._generate_proof({"feature_id": "overwrite_test", "thinking": "v2"})
        content = (proof_system.proofs_dir / "overwrite_test.md").read_text()
        assert "v2" in content
        assert "v1" not in content

    def test_generate_default_risk_level(self, proof_system):
        proof_system._generate_proof({"feature_id": "default_risk"})
        content = (proof_system.proofs_dir / "default_risk.md").read_text()
        assert "LOW" in content

    def test_generate_default_rollback_time(self, proof_system):
        proof_system._generate_proof({"feature_id": "default_rollback"})
        content = (proof_system.proofs_dir / "default_rollback.md").read_text()
        assert "Unknown" in content

    def test_generate_returns_path(self, proof_system):
        result = proof_system._generate_proof({"feature_id": "path_test"})
        assert "path" in result
        assert "path_test.md" in result["path"]


# ---------------------------------------------------------------------------
# _get_proof
# ---------------------------------------------------------------------------
class TestGetProof:
    def test_get_existing(self, proof_system):
        proof_system._generate_proof({"feature_id": "get_me", "thinking": "Find this"})
        result = proof_system._get_proof("get_me")
        assert "Find this" in result

    def test_get_nonexistent(self, proof_system):
        result = proof_system._get_proof("nonexistent_proof")
        assert "not found" in result


# ---------------------------------------------------------------------------
# _list_proofs
# ---------------------------------------------------------------------------
class TestListProofs:
    def test_list_empty(self, proof_system):
        result = proof_system._list_proofs()
        assert result == []

    def test_list_with_proofs(self, proof_system):
        proof_system._generate_proof({"feature_id": "proof_a"})
        proof_system._generate_proof({"feature_id": "proof_b"})
        result = proof_system._list_proofs()
        assert "proof_a.md" in result
        assert "proof_b.md" in result
        assert len(result) == 2

    def test_list_only_md_files(self, proof_system):
        # Create a non-md file
        (proof_system.proofs_dir / "not_a_proof.txt").write_text("ignore me")
        proof_system._generate_proof({"feature_id": "real_proof"})
        result = proof_system._list_proofs()
        assert "real_proof.md" in result
        assert "not_a_proof.txt" not in result


# ---------------------------------------------------------------------------
# execute_tool dispatch
# ---------------------------------------------------------------------------
class TestExecuteTool:
    def test_dispatch_generate(self, proof_system):
        result = proof_system.execute_tool("brain_generate_proof", {"feature_id": "dispatch_gen"})
        assert result["success"] is True

    def test_dispatch_get(self, proof_system):
        proof_system._generate_proof({"feature_id": "dispatch_get"})
        result = proof_system.execute_tool("brain_get_proof", {"feature_id": "dispatch_get"})
        assert "dispatch_get" in result

    def test_dispatch_list(self, proof_system):
        proof_system._generate_proof({"feature_id": "dispatch_list"})
        result = proof_system.execute_tool("brain_list_proofs", {})
        assert isinstance(result, list)
        assert len(result) == 1

    def test_dispatch_unknown(self, proof_system):
        result = proof_system.execute_tool("nonexistent", {})
        assert "not found" in result

    def test_dispatch_exception_handled(self, proof_system):
        """When _generate_proof raises, execute_tool catches it."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(proof_system, "_generate_proof", lambda x: (_ for _ in ()).throw(Exception("Boom")))
            result = proof_system.execute_tool("brain_generate_proof", {})
            assert "Error" in result
            assert "Boom" in result
