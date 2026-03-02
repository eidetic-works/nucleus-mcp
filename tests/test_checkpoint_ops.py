"""Tests for V3.1 Checkpoint & Handoff Operations on UnifiedOrchestrator."""

import time
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from mcp_server_nucleus.runtime.orchestrator_unified import UnifiedOrchestrator


@pytest.fixture
def orch(tmp_path):
    """Create a fresh UnifiedOrchestrator with a temp brain path."""
    with patch("mcp_server_nucleus.runtime.orchestrator_unified.DirectivesLoader") as mock_dl, \
         patch("mcp_server_nucleus.runtime.orchestrator_unified.ContextFactory") as mock_cf:
        mock_dl.return_value = MagicMock()
        mock_cf.return_value = MagicMock()
        return UnifiedOrchestrator(brain_path=tmp_path)


@pytest.fixture
def task_with_checkpoint(orch):
    """Create a task and checkpoint it."""
    result = orch.add_task("Phase 5 outreach", priority=1, tier="T1_STRATEGY")
    task_id = result["task"]["id"]
    orch.checkpoint_task(task_id, {"step": 3, "progress_percent": 60, "context": "Drafting Reddit posts"})
    return task_id


class TestCheckpointTask:
    def test_checkpoint_success(self, orch):
        result = orch.add_task("Test checkpoint", priority=2)
        task_id = result["task"]["id"]

        cp_result = orch.checkpoint_task(task_id, {"step": 1, "progress_percent": 25})

        assert cp_result["success"] is True
        assert cp_result["checkpoint"]["enabled"] is True
        assert cp_result["checkpoint"]["data"]["step"] == 1
        assert cp_result["checkpoint"]["data"]["progress_percent"] == 25
        assert "last_checkpoint_at" in cp_result["checkpoint"]

    def test_checkpoint_not_found(self, orch):
        result = orch.checkpoint_task("nonexistent_task", {"step": 1})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_checkpoint_overwrites_previous(self, orch):
        result = orch.add_task("Overwrite test", priority=2)
        task_id = result["task"]["id"]

        orch.checkpoint_task(task_id, {"step": 1})
        cp2 = orch.checkpoint_task(task_id, {"step": 5, "progress_percent": 90})

        assert cp2["checkpoint"]["data"]["step"] == 5
        assert cp2["checkpoint"]["data"]["progress_percent"] == 90


class TestResumeFromCheckpoint:
    def test_resume_success(self, task_with_checkpoint, orch):
        result = orch.resume_from_checkpoint(task_with_checkpoint)

        assert result["success"] is True
        assert result["task_id"] == task_with_checkpoint
        assert result["checkpoint"]["data"]["step"] == 3
        assert result["checkpoint"]["data"]["progress_percent"] == 60
        assert "Resume from step 3" in result["resume_instructions"]

    def test_resume_not_found(self, orch):
        result = orch.resume_from_checkpoint("nonexistent_task")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_resume_no_checkpoint(self, orch):
        result = orch.add_task("No checkpoint task", priority=2)
        task_id = result["task"]["id"]

        result = orch.resume_from_checkpoint(task_id)
        assert result["success"] is False
        assert "No checkpoint found" in result["error"]


class TestGenerateContextSummary:
    def test_summary_success(self, orch):
        result = orch.add_task("Summary test", priority=2)
        task_id = result["task"]["id"]

        summary_result = orch.generate_context_summary(
            task_id,
            summary="Completed 3 of 5 outreach posts",
            key_decisions=["Use lowercase tone", "No direct links"],
            handoff_notes="Next agent should post to r/LocalLLaMA first"
        )

        assert summary_result["success"] is True
        cs = summary_result["context_summary"]
        assert cs["summary"] == "Completed 3 of 5 outreach posts"
        assert len(cs["key_decisions"]) == 2
        assert cs["handoff_notes"] == "Next agent should post to r/LocalLLaMA first"
        assert "generated_at" in cs

    def test_summary_not_found(self, orch):
        result = orch.generate_context_summary("nonexistent", "test")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_summary_defaults(self, orch):
        result = orch.add_task("Defaults test", priority=2)
        task_id = result["task"]["id"]

        summary_result = orch.generate_context_summary(task_id, "Minimal summary")

        cs = summary_result["context_summary"]
        assert cs["key_decisions"] == []
        assert cs["handoff_notes"] == ""


class TestGetAllTasks:
    def test_get_all_unfiltered(self, orch):
        orch.add_task("Task A", priority=1)
        orch.add_task("Task B", priority=2)
        assert len(orch.get_all_tasks()) == 2

    def test_get_all_filtered_by_status(self, orch):
        result = orch.add_task("Task A", priority=1)
        orch.add_task("Task B", priority=2)
        orch.claim_task(result["task"]["id"], "agent_1")
        assert len(orch.get_all_tasks(status="PENDING")) == 1
        assert len(orch.get_all_tasks(status="IN_PROGRESS")) == 1

    def test_get_all_empty(self, orch):
        assert orch.get_all_tasks() == []


class TestClaimTask:
    def test_claim_success(self, orch):
        result = orch.add_task("Claimable", priority=1)
        task_id = result["task"]["id"]
        claim = orch.claim_task(task_id, "agent_1")
        assert claim["success"] is True
        assert claim["task"]["claimed_by"] == "agent_1"
        assert claim["task"]["status"] == "IN_PROGRESS"

    def test_claim_conflict(self, orch):
        result = orch.add_task("Contested", priority=1)
        task_id = result["task"]["id"]
        orch.claim_task(task_id, "agent_1")
        conflict = orch.claim_task(task_id, "agent_2")
        assert conflict["success"] is False
        assert "already claimed" in conflict["error"]

    def test_claim_not_found(self, orch):
        result = orch.claim_task("nonexistent", "agent_1")
        assert result["success"] is False


class TestCompleteTask:
    def test_complete_success(self, orch):
        result = orch.add_task("Completable", priority=1)
        task_id = result["task"]["id"]
        orch.claim_task(task_id, "agent_1")
        done = orch.complete_task(task_id, "agent_1", "success")
        assert done["success"] is True
        assert done["task"]["status"] == "DONE"

    def test_complete_failure(self, orch):
        result = orch.add_task("Failing", priority=1)
        task_id = result["task"]["id"]
        done = orch.complete_task(task_id, "agent_1", "failure")
        assert done["task"]["status"] == "FAILED"

    def test_complete_not_found(self, orch):
        result = orch.complete_task("nonexistent", "agent_1")
        assert result["success"] is False


class TestPoolMetrics:
    def test_metrics_empty(self, orch):
        metrics = orch.get_pool_metrics()
        assert metrics["total_tasks"] == 0
        assert metrics["pending"] == 0

    def test_metrics_with_tasks(self, orch):
        r1 = orch.add_task("A", priority=1)
        r2 = orch.add_task("B", priority=2)
        orch.claim_task(r1["task"]["id"], "agent_1")
        orch.checkpoint_task(r1["task"]["id"], {"step": 1})
        metrics = orch.get_pool_metrics()
        assert metrics["total_tasks"] == 2
        assert metrics["in_progress"] == 1
        assert metrics["pending"] == 1
        assert metrics["with_checkpoints"] == 1


class TestDependencyGraph:
    def test_graph_empty(self, orch):
        graph = orch.get_dependency_graph()
        assert graph["forward_deps"] == {}
        assert graph["reverse_deps"] == {}

    def test_graph_with_deps(self, orch):
        r1 = orch.add_task("Parent", priority=1)
        parent_id = r1["task"]["id"]
        r2 = orch.add_task("Child", priority=2, blocked_by=[parent_id])
        child_id = r2["task"]["id"]
        graph = orch.get_dependency_graph()
        assert parent_id in graph["forward_deps"][child_id]
        assert child_id in graph["reverse_deps"][parent_id]
        assert graph["depths"][child_id] == 1
        assert graph["depths"][parent_id] == 0


class TestE2ECheckpointOpsLayer:
    """E2E: Verify checkpoint_ops.py _impl functions route through to UnifiedOrchestrator."""

    def test_checkpoint_impl_e2e(self, orch):
        """_brain_checkpoint_task_impl → get_orch() → UnifiedOrchestrator.checkpoint_task"""
        result = orch.add_task("E2E checkpoint test", priority=1)
        task_id = result["task"]["id"]

        with patch("mcp_server_nucleus.runtime.checkpoint_ops._lazy") as mock_lazy:
            mock_lazy.return_value = lambda: orch
            from mcp_server_nucleus.runtime.checkpoint_ops import _brain_checkpoint_task_impl
            output = _brain_checkpoint_task_impl(task_id, step=2, progress_percent=50, context="E2E test")

        assert "Checkpoint saved" in output
        assert task_id in output

        # Verify it actually persisted in the orchestrator
        task = orch.get_task(task_id)
        assert task["checkpoint"]["data"]["step"] == 2
        assert task["checkpoint"]["data"]["progress_percent"] == 50

    def test_resume_impl_e2e(self, orch):
        """_brain_resume_from_checkpoint_impl → get_orch() → UnifiedOrchestrator.resume_from_checkpoint"""
        result = orch.add_task("E2E resume test", priority=1)
        task_id = result["task"]["id"]
        orch.checkpoint_task(task_id, {"step": 3, "progress_percent": 75, "context": "Almost done"})

        with patch("mcp_server_nucleus.runtime.checkpoint_ops._lazy") as mock_lazy:
            mock_lazy.return_value = lambda: orch
            from mcp_server_nucleus.runtime.checkpoint_ops import _brain_resume_from_checkpoint_impl
            output = _brain_resume_from_checkpoint_impl(task_id)

        assert "Resume Instructions" in output
        assert "Step: 3" in output
        assert "Progress: 75" in output

    def test_handoff_summary_impl_e2e(self, orch):
        """_brain_generate_handoff_summary_impl → get_orch() → UnifiedOrchestrator.generate_context_summary"""
        result = orch.add_task("E2E handoff test", priority=1)
        task_id = result["task"]["id"]

        with patch("mcp_server_nucleus.runtime.checkpoint_ops._lazy") as mock_lazy:
            mock_lazy.return_value = lambda: orch
            from mcp_server_nucleus.runtime.checkpoint_ops import _brain_generate_handoff_summary_impl
            output = _brain_generate_handoff_summary_impl(
                task_id, "Summary of work done", ["Decision A", "Decision B"], "Notes for next agent"
            )

        assert "Handoff summary generated" in output
        assert "Key decisions: 2" in output

        # Verify persistence
        task = orch.get_task(task_id)
        assert task["context_summary"]["summary"] == "Summary of work done"
        assert len(task["context_summary"]["key_decisions"]) == 2

    def test_checkpoint_not_found_impl_e2e(self, orch):
        """Verify error path through impl layer."""
        with patch("mcp_server_nucleus.runtime.checkpoint_ops._lazy") as mock_lazy:
            mock_lazy.return_value = lambda: orch
            from mcp_server_nucleus.runtime.checkpoint_ops import _brain_checkpoint_task_impl
            output = _brain_checkpoint_task_impl("nonexistent_task", step=1)

        assert "Checkpoint failed" in output
        assert "not found" in output

    def test_full_e2e_roundtrip(self, orch):
        """Full E2E: create → checkpoint (impl) → summary (impl) → resume (impl)."""
        result = orch.add_task("Full E2E roundtrip", priority=1)
        task_id = result["task"]["id"]

        with patch("mcp_server_nucleus.runtime.checkpoint_ops._lazy") as mock_lazy:
            mock_lazy.return_value = lambda: orch
            from mcp_server_nucleus.runtime.checkpoint_ops import (
                _brain_checkpoint_task_impl,
                _brain_generate_handoff_summary_impl,
                _brain_resume_from_checkpoint_impl,
            )

            # Checkpoint
            cp_out = _brain_checkpoint_task_impl(task_id, step=4, progress_percent=80,
                                                  context="Nearly complete", artifacts=["file1.py", "file2.py"])
            assert "Checkpoint saved" in cp_out

            # Summary
            sum_out = _brain_generate_handoff_summary_impl(
                task_id, "4 of 5 steps done", ["Used security-first approach"], "Finish step 5"
            )
            assert "Handoff summary generated" in sum_out

            # Resume
            res_out = _brain_resume_from_checkpoint_impl(task_id)
            assert "Resume Instructions" in res_out
            assert "Step: 4" in res_out
            assert "Previous Summary" in res_out
            assert "4 of 5 steps done" in res_out
            assert "security-first approach" in res_out


class TestCheckpointResumeRoundtrip:
    def test_full_cycle(self, orch):
        """Create → Checkpoint → Summary → Resume: full roundtrip."""
        # Create
        result = orch.add_task("Roundtrip test", priority=1, tier="T1_STRATEGY")
        task_id = result["task"]["id"]

        # Checkpoint
        orch.checkpoint_task(task_id, {
            "step": 2,
            "progress_percent": 40,
            "context": "Halfway through outreach",
            "artifacts": ["draft_secithub.md", "draft_pwnhub.md"]
        })

        # Summary
        orch.generate_context_summary(
            task_id,
            summary="2 of 3 Reddit drafts complete",
            key_decisions=["Security-first angle", "No product links"],
            handoff_notes="LocalLLaMA draft still pending"
        )

        # Resume
        resume = orch.resume_from_checkpoint(task_id)

        assert resume["success"] is True
        assert resume["checkpoint"]["data"]["step"] == 2
        assert resume["checkpoint"]["data"]["artifacts"] == ["draft_secithub.md", "draft_pwnhub.md"]
        assert resume["context_summary"]["summary"] == "2 of 3 Reddit drafts complete"
        assert len(resume["context_summary"]["key_decisions"]) == 2
        assert resume["context_summary"]["handoff_notes"] == "LocalLLaMA draft still pending"
        assert "Resume from step 2" in resume["resume_instructions"]
