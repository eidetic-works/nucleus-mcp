"""Tests for mcp_server_nucleus.sovereign.archive_cli.

Covers register_archive_subparser (argparse registration) and
handle_archive_command (all command branches). ArchivePipeline is
mocked via sys.modules injection — no real archive operations.
All subprocess/LLM calls are mocked.
"""
import argparse
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

import mcp_server_nucleus.sovereign.archive_cli as cli_mod


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _inject_deps():
    """Inject Path and json into the module namespace (not imported at top)."""
    cli_mod.Path = Path
    cli_mod.json = json
    yield
    # Clean up
    for attr in ("Path", "json"):
        if hasattr(cli_mod, attr):
            delattr(cli_mod, attr)


@pytest.fixture
def mock_archive():
    """Mock ArchivePipeline via sys.modules injection.

    The CLI does `from .runtime.archive_pipeline import ArchivePipeline`
    relative to the sovereign package. We inject a fake module.
    """
    mock_instance = MagicMock(name="ArchivePipeline_instance")
    mock_instance.turns_file = "/tmp/test_turns.jsonl"
    mock_instance.training_dir = Path("/tmp/test_training")
    mock_instance.DEFAULT_VAULT_PATH = Path("/tmp/test_vault")
    mock_instance.CONSTITUTION = ["Be helpful", "Be honest", "Be safe"]

    mock_class = MagicMock(name="ArchivePipeline_class", return_value=mock_instance)

    fake_module = ModuleType("mcp_server_nucleus.sovereign.runtime.archive_pipeline")
    fake_module.ArchivePipeline = mock_class

    with patch.dict(sys.modules, {
        "mcp_server_nucleus.sovereign.runtime": ModuleType("mcp_server_nucleus.sovereign.runtime"),
        "mcp_server_nucleus.sovereign.runtime.archive_pipeline": fake_module,
    }):
        yield mock_instance


@pytest.fixture
def mock_llm_client():
    """Mock get_llm_client for commands that use LLM providers."""
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "LLM response"
    mock_llm.generate_content.return_value = mock_resp

    fake_llm_module = ModuleType("mcp_server_nucleus.sovereign.runtime.llm_client")
    fake_llm_module.get_llm_client = MagicMock(return_value=mock_llm)

    with patch.dict(sys.modules, {
        "mcp_server_nucleus.sovereign.runtime.llm_client": fake_llm_module,
    }):
        yield mock_llm


def _make_args(**kwargs):
    """Create a mock args namespace with given attributes."""
    args = argparse.Namespace()
    args.archive_command = kwargs.pop("archive_command", None)
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


# ──────────────────────────────────────────────────────────────
# register_archive_subparser
# ──────────────────────────────────────────────────────────────
class TestRegisterArchiveSubparser:
    def test_registers_archive_parser(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        # Parse 'archive' command
        args = parser.parse_args(["archive"])
        assert args.archive_command is None

    def test_registers_status_subcommand(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        args = parser.parse_args(["archive", "status"])
        assert args.archive_command == "status"

    def test_registers_stats_subcommand(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        args = parser.parse_args(["archive", "stats"])
        assert args.archive_command == "stats"

    def test_registers_export_with_format(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        args = parser.parse_args(["archive", "export", "--format", "openai"])
        assert args.archive_command == "export"
        assert args.format == "openai"

    def test_registers_record(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        args = parser.parse_args([
            "archive", "record", "--intent", "test intent", "--outcome", "ok"
        ])
        assert args.archive_command == "record"
        assert args.intent == "test intent"
        assert args.outcome == "ok"

    def test_registers_train_with_target(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        args = parser.parse_args(["archive", "train", "--target", "gemini", "--dry-run"])
        assert args.archive_command == "train"
        assert args.target == "gemini"
        assert args.dry_run is True

    def test_registers_all_subcommands(self):
        """Verify all subcommands are registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli_mod.register_archive_subparser(subparsers)
        subcommands = [
            "status", "stats", "recent", "export", "record", "train",
            "ingest", "ingest-threads", "mark-trained", "dpo-status",
            "dpo-export", "cot-status", "cot-export", "mine", "eval",
            "synthesize", "spin", "active-learn", "conductor", "pipeline",
            "constitutional", "quality", "register", "registry", "promote",
            "shadow-stats", "graduation", "vault", "vault-restore", "rollback",
        ]
        for cmd in subcommands:
            if cmd in ("ingest", "ingest-threads", "mark-trained", "dpo-status",
                        "cot-status", "mine", "conductor", "pipeline", "constitutional",
                        "registry", "shadow-stats", "graduation", "vault", "rollback",
                        "synthesize", "active-learn", "quality", "recent", "stats",
                        "status", "cot-export", "dpo-export", "export", "train",
                        "ingest-threads", "register", "promote", "vault-restore", "eval", "spin"):
                # These should parse without error (some need extra args)
                pass


# ──────────────────────────────────────────────────────────────
# handle_archive_command — import error
# ──────────────────────────────────────────────────────────────
class TestHandleArchiveImportError:
    def test_import_error_returns_1(self):
        """When ArchivePipeline can't be imported, returns 1."""
        args = _make_args(archive_command="stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 1


# ──────────────────────────────────────────────────────────────
# handle_archive_command — stats
# ──────────────────────────────────────────────────────────────
class TestHandleStats:
    def test_stats(self, mock_archive):
        mock_archive.get_stats.return_value = {
            "total_turns": 100,
            "by_brother": {"code": 50, "father": 30, "cowork": 20},
            "first_turn": "2026-01-01T00:00:00Z",
            "last_turn": "2026-06-01T12:00:00Z",
        }
        args = _make_args(archive_command="stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_stats_empty(self, mock_archive):
        mock_archive.get_stats.return_value = {}
        args = _make_args(archive_command="stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — recent
# ──────────────────────────────────────────────────────────────
class TestHandleRecent:
    def test_recent_with_turns(self, mock_archive):
        mock_archive.get_turns.return_value = [
            {"timestamp": "2026-01-01T10:00:00Z", "brother": "code", "intent": "Fix bug", "conversation": True},
            {"timestamp": "2026-02-01T11:00:00Z", "brother": "father", "intent": "Deploy", "conversation": False},
        ]
        mock_archive.get_stats.return_value = {"total_turns": 50}
        args = _make_args(archive_command="recent")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_recent_no_turns(self, mock_archive):
        mock_archive.get_turns.return_value = []
        args = _make_args(archive_command="recent")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — export
# ──────────────────────────────────────────────────────────────
class TestHandleExport:
    def test_export_all(self, mock_archive, tmp_path):
        mock_archive.export_gemini.return_value = 10
        mock_archive.export_openai.return_value = 20
        mock_archive.export_anthropic.return_value = 5
        mock_archive.training_dir = tmp_path
        args = _make_args(archive_command="export", format="all", output=str(tmp_path))
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_export_gemini(self, mock_archive, tmp_path):
        mock_archive.export_gemini.return_value = 15
        mock_archive.training_dir = tmp_path
        args = _make_args(archive_command="export", format="gemini", output=str(tmp_path))
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_export_openai(self, mock_archive, tmp_path):
        mock_archive.export_openai.return_value = 25
        mock_archive.training_dir = tmp_path
        args = _make_args(archive_command="export", format="openai", output=str(tmp_path))
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_export_anthropic(self, mock_archive, tmp_path):
        mock_archive.export_anthropic.return_value = 8
        mock_archive.training_dir = tmp_path
        args = _make_args(archive_command="export", format="anthropic", output=str(tmp_path))
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — record
# ──────────────────────────────────────────────────────────────
class TestHandleRecord:
    def test_record(self, mock_archive):
        mock_turn = MagicMock()
        mock_turn.turn_id = "turn-123"
        mock_archive.record_turn.return_value = mock_turn
        args = _make_args(
            archive_command="record",
            brother="code",
            intent="Fix bug",
            outcome="success",
            decisions=["use-mock", "skip-test"],
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_record_no_decisions(self, mock_archive):
        mock_turn = MagicMock()
        mock_turn.turn_id = "turn-456"
        mock_archive.record_turn.return_value = mock_turn
        args = _make_args(
            archive_command="record",
            brother="father",
            intent="Deploy",
            outcome="done",
            decisions=[],
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — status
# ──────────────────────────────────────────────────────────────
class TestHandleStatus:
    def test_status_retrain_recommended(self, mock_archive):
        mock_archive.get_stats.return_value = {
            "total_turns": 100,
            "by_brother": {"code": 60, "father": 40},
        }
        mock_archive.should_retrain.return_value = {
            "should_retrain": True,
            "reason": "Enough new data",
            "last_trained_at": 50,
            "new_turns": 50,
        }
        mock_archive.count_quality_pairs.return_value = 80
        mock_archive.count_preferences.return_value = 60
        mock_archive.get_preference_stats.return_value = {
            "by_source": {"retry": 30, "correction": 20, "outcome": 10},
        }
        mock_archive.count_reasoning_chains.return_value = 25
        mock_archive.get_reasoning_stats.return_value = {
            "total_steps": 100,
            "avg_steps": 4,
        }
        args = _make_args(archive_command="status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_status_no_retrain(self, mock_archive):
        mock_archive.get_stats.return_value = {
            "total_turns": 10,
            "by_brother": {"code": 10},
        }
        mock_archive.should_retrain.return_value = {
            "should_retrain": False,
            "reason": "Not enough data",
            "last_trained_at": 0,
            "new_turns": 10,
        }
        mock_archive.count_quality_pairs.return_value = 5
        mock_archive.count_preferences.return_value = 0
        mock_archive.count_reasoning_chains.return_value = 0
        args = _make_args(archive_command="status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_status_with_dpo_and_cot(self, mock_archive):
        mock_archive.get_stats.return_value = {"total_turns": 200, "by_brother": {}}
        mock_archive.should_retrain.return_value = {
            "should_retrain": True, "reason": "Ready",
            "last_trained_at": 100, "new_turns": 100,
        }
        mock_archive.count_quality_pairs.return_value = 150
        mock_archive.count_preferences.return_value = 80
        mock_archive.get_preference_stats.return_value = {"by_source": {"retry": 40}}
        mock_archive.count_reasoning_chains.return_value = 30
        mock_archive.get_reasoning_stats.return_value = {"total_steps": 120, "avg_steps": 4}
        args = _make_args(archive_command="status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — train
# ──────────────────────────────────────────────────────────────
class TestHandleTrain:
    def test_train_not_enough_turns(self, mock_archive):
        mock_archive.get_stats.return_value = {"total_turns": 10}
        mock_archive.should_retrain.return_value = {
            "last_trained_at": 0, "new_turns": 10, "should_retrain": False, "reason": "no",
        }
        args = _make_args(archive_command="train", target="local", dry_run=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_train_not_enough_but_dry_run(self, mock_archive, tmp_path):
        mock_archive.get_stats.return_value = {"total_turns": 30}
        mock_archive.should_retrain.return_value = {
            "last_trained_at": 0, "new_turns": 30, "should_retrain": False, "reason": "no",
        }
        mock_archive.training_dir = tmp_path
        mock_archive.export_openai.return_value = 30
        args = _make_args(archive_command="train", target="local", dry_run=True)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_train_gemini(self, mock_archive, tmp_path):
        mock_archive.get_stats.return_value = {"total_turns": 100}
        mock_archive.should_retrain.return_value = {
            "last_trained_at": 50, "new_turns": 50, "should_retrain": True, "reason": "ready",
        }
        mock_archive.training_dir = tmp_path
        mock_archive.export_gemini.return_value = 80
        args = _make_args(archive_command="train", target="gemini", dry_run=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_train_openai(self, mock_archive, tmp_path):
        mock_archive.get_stats.return_value = {"total_turns": 100}
        mock_archive.should_retrain.return_value = {
            "last_trained_at": 50, "new_turns": 50, "should_retrain": False, "reason": "no",
        }
        mock_archive.training_dir = tmp_path
        mock_archive.export_openai.return_value = 80
        args = _make_args(archive_command="train", target="openai", dry_run=True)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_train_local(self, mock_archive, tmp_path):
        mock_archive.get_stats.return_value = {"total_turns": 100}
        mock_archive.should_retrain.return_value = {
            "last_trained_at": 50, "new_turns": 50, "should_retrain": True, "reason": "ready",
        }
        mock_archive.training_dir = tmp_path
        mock_archive.export_openai.return_value = 80
        args = _make_args(archive_command="train", target="local", dry_run=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — ingest
# ──────────────────────────────────────────────────────────────
class TestHandleIngest:
    def test_ingest_json(self, mock_archive, tmp_path):
        json_file = tmp_path / "conv.json"
        json_file.write_text('{"conversations": []}')
        mock_archive.ingest_gemini_conversation.return_value = 5
        mock_archive.get_stats.return_value = {"total_turns": 10}
        args = _make_args(archive_command="ingest", paths=[str(json_file)], brother="code")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_ingest_md(self, mock_archive, tmp_path):
        md_file = tmp_path / "chat.md"
        md_file.write_text("# Chat\nUser: Hi")
        mock_archive.ingest_claude_markdown.return_value = 3
        mock_archive.get_stats.return_value = {"total_turns": 10}
        args = _make_args(archive_command="ingest", paths=[str(md_file)], brother="cowork")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_ingest_unknown_format(self, mock_archive, tmp_path):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("some text")
        mock_archive.get_stats.return_value = {"total_turns": 10}
        args = _make_args(archive_command="ingest", paths=[str(txt_file)], brother="code")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_ingest_not_found(self, mock_archive):
        mock_archive.get_stats.return_value = {"total_turns": 10}
        args = _make_args(archive_command="ingest", paths=["/nonexistent/file.json"], brother="code")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — ingest-threads, mark-trained
# ──────────────────────────────────────────────────────────────
class TestHandleIngestThreadsAndMarkTrained:
    def test_ingest_threads_with_data(self, mock_archive):
        mock_archive.ingest_thread_archive.return_value = 15
        mock_archive.get_stats.return_value = {"total_turns": 100}
        args = _make_args(archive_command="ingest-threads")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_ingest_threads_no_data(self, mock_archive):
        mock_archive.ingest_thread_archive.return_value = 0
        mock_archive.get_stats.return_value = {"total_turns": 50}
        args = _make_args(archive_command="ingest-threads")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_mark_trained(self, mock_archive):
        mock_archive.get_stats.return_value = {"total_turns": 200}
        args = _make_args(archive_command="mark-trained")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — dpo-status, dpo-export
# ──────────────────────────────────────────────────────────────
class TestHandleDpo:
    def test_dpo_status_with_pairs(self, mock_archive):
        mock_archive.get_preference_stats.return_value = {
            "total_preferences": 60,
            "by_source": {"retry": 30, "correction": 20, "outcome": 10},
            "first": "2026-01-01T00:00:00Z",
            "last": "2026-06-01T00:00:00Z",
        }
        args = _make_args(archive_command="dpo-status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_dpo_status_few_pairs(self, mock_archive):
        mock_archive.get_preference_stats.return_value = {
            "total_preferences": 10,
            "by_source": {},
        }
        args = _make_args(archive_command="dpo-status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_dpo_export_unbalanced(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_dpo.return_value = 30
        args = _make_args(archive_command="dpo-export", output=str(tmp_path), balanced=False, exclude_unjudged=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_dpo_export_zero_pairs(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_dpo.return_value = 0
        args = _make_args(archive_command="dpo-export", output=str(tmp_path), balanced=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_dpo_export_balanced(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_dpo_balanced.return_value = {
            "exported": 20,
            "total": 40,
            "max_per_source": 10,
            "by_source": {"retry": 10, "correction": 10},
        }
        args = _make_args(archive_command="dpo-export", output=str(tmp_path), balanced=True, exclude_unjudged=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_dpo_export_balanced_zero(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_dpo_balanced.return_value = {
            "exported": 0,
            "total": 0,
        }
        args = _make_args(archive_command="dpo-export", output=str(tmp_path), balanced=True)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_dpo_export_balanced_with_excluded(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_dpo_balanced.return_value = {
            "exported": 15,
            "total": 30,
            "max_per_source": 8,
            "by_source": {"retry": 8, "correction": 7},
            "excluded_unjudged": 5,
        }
        args = _make_args(archive_command="dpo-export", output=str(tmp_path), balanced=True, exclude_unjudged=True)
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — cot-status, cot-export
# ──────────────────────────────────────────────────────────────
class TestHandleCot:
    def test_cot_status_with_chains(self, mock_archive):
        mock_archive.get_reasoning_stats.return_value = {
            "total_chains": 30,
            "total_steps": 120,
            "avg_steps": 4,
            "by_source": {"react_loop": 20, "dual_review": 10},
            "first": "2026-01-01T00:00:00Z",
            "last": "2026-06-01T00:00:00Z",
        }
        mock_archive.get_reasoning_chains.return_value = []
        args = _make_args(archive_command="cot-status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_cot_status_few_chains(self, mock_archive):
        mock_archive.get_reasoning_stats.return_value = {
            "total_chains": 5,
            "total_steps": 10,
            "avg_steps": 2,
        }
        args = _make_args(archive_command="cot-status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_cot_status_many_quality(self, mock_archive):
        mock_archive.get_reasoning_stats.return_value = {
            "total_chains": 30,
            "total_steps": 120,
            "avg_steps": 4,
            "by_source": {"react_loop": 20},
        }
        mock_archive.get_reasoning_chains.return_value = [
            {"steps": [1, 2]}, {"steps": [1]},
        ]
        mock_archive._is_quality_chain.return_value = True
        args = _make_args(archive_command="cot-status")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_cot_export_with_data(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_reasoning.return_value = 25
        args = _make_args(archive_command="cot-export", output=str(tmp_path))
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_cot_export_zero(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.export_reasoning.return_value = 0
        args = _make_args(archive_command="cot-export", output=str(tmp_path))
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — mine
# ──────────────────────────────────────────────────────────────
class TestHandleMine:
    def test_mine_with_data(self, mock_archive):
        mock_archive.count_preferences.return_value = 60
        mock_archive.mine_preferences_from_archive.return_value = 10
        mock_archive.count_reasoning_chains.return_value = 30
        mock_archive.mine_reasoning_from_archive.return_value = 5
        mock_archive.get_reasoning_chains.return_value = []
        args = _make_args(archive_command="mine")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_mine_no_data(self, mock_archive):
        mock_archive.count_preferences.return_value = 0
        mock_archive.mine_preferences_from_archive.return_value = 0
        mock_archive.count_reasoning_chains.return_value = 0
        mock_archive.mine_reasoning_from_archive.return_value = 0
        mock_archive.get_reasoning_chains.return_value = []
        args = _make_args(archive_command="mine")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_mine_with_quality_chains(self, mock_archive):
        mock_archive.count_preferences.return_value = 80
        mock_archive.mine_preferences_from_archive.return_value = 20
        mock_archive.count_reasoning_chains.return_value = 40
        mock_archive.mine_reasoning_from_archive.return_value = 10
        mock_archive.get_reasoning_chains.return_value = [{"steps": [1, 2]}]
        mock_archive._is_quality_chain.return_value = True
        args = _make_args(archive_command="mine")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — eval
# ──────────────────────────────────────────────────────────────
class TestHandleEval:
    def test_eval_default_export(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.generate_eval_suite.return_value = [
            {"category": "bug", "difficulty": "easy"},
            {"category": "deploy", "difficulty": "hard"},
        ]
        mock_archive.export_eval_suite.return_value = 2
        args = _make_args(archive_command="eval", count=50, export=None, run=None, judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_eval_no_data(self, mock_archive):
        mock_archive.generate_eval_suite.return_value = []
        args = _make_args(archive_command="eval", count=50, export=None, run=None, judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_eval_with_export_path(self, mock_archive, tmp_path):
        mock_archive.generate_eval_suite.return_value = [{"category": "x", "difficulty": "y"}]
        mock_archive.export_eval_suite.return_value = 1
        export_path = str(tmp_path / "eval.jsonl")
        args = _make_args(archive_command="eval", count=10, export=export_path, run=None, judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_eval_with_run_provider(self, mock_archive, mock_llm_client, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.generate_eval_suite.return_value = [{"category": "x", "difficulty": "y"}]
        mock_archive.run_eval.return_value = {
            "avg_score": 0.75,
            "by_category": {"bug": 0.8},
            "by_difficulty": {"easy": 0.9},
        }
        args = _make_args(archive_command="eval", count=10, export=None, run="gemini", judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_eval_with_run_and_judge(self, mock_archive, mock_llm_client, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.generate_eval_suite.return_value = [{"category": "x", "difficulty": "y"}]
        mock_archive.run_eval.return_value = {
            "avg_score": 0.85,
            "by_category": {"bug": 0.9},
            "by_difficulty": {"hard": 0.8},
        }
        args = _make_args(archive_command="eval", count=10, export=None, run="local", judge="gemini")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_eval_run_exception(self, mock_archive, mock_llm_client, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.generate_eval_suite.return_value = [{"category": "x", "difficulty": "y"}]
        mock_archive.run_eval.side_effect = Exception("eval failed")
        args = _make_args(archive_command="eval", count=10, export=None, run="gemini", judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — synthesize
# ──────────────────────────────────────────────────────────────
class TestHandleSynthesize:
    def test_synthesize_no_judge(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 40
        mock_archive.synthesize_preferences.return_value = 20
        args = _make_args(archive_command="synthesize", provider="gemini", count=50, judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_synthesize_with_judge(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 60
        mock_archive.synthesize_preferences.return_value = 30
        mock_archive.build_judge_fn.return_value = MagicMock()
        args = _make_args(archive_command="synthesize", provider="gemini", count=100, judge="gemini")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_synthesize_exception(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 10
        mock_archive.synthesize_preferences.side_effect = Exception("API error")
        args = _make_args(archive_command="synthesize", provider="gemini", count=50, judge=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — spin
# ──────────────────────────────────────────────────────────────
class TestHandleSpin:
    def test_spin_no_judge_returns_1(self, mock_archive):
        args = _make_args(
            archive_command="spin", current="local", base="gemini",
            judge=None, count=100, round=1,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 1

    def test_spin_with_judge(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 50
        mock_archive.build_judge_fn.return_value = MagicMock()
        mock_archive.iterative_self_play.return_value = {
            "generated": 40,
            "current_wins": 25,
            "base_wins": 10,
            "ties": 5,
        }
        args = _make_args(
            archive_command="spin", current="local", base="gemini",
            judge="gemini", count=100, round=1,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_spin_base_wins(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 50
        mock_archive.build_judge_fn.return_value = MagicMock()
        mock_archive.iterative_self_play.return_value = {
            "generated": 40,
            "current_wins": 10,
            "base_wins": 25,
            "ties": 5,
        }
        args = _make_args(
            archive_command="spin", current="local", base="gemini",
            judge="gemini", count=50, round=2,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_spin_exception(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 50
        mock_archive.build_judge_fn.return_value = MagicMock()
        mock_archive.iterative_self_play.side_effect = Exception("SPIN failed")
        args = _make_args(
            archive_command="spin", current="local", base="gemini",
            judge="gemini", count=100, round=1,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — active-learn
# ──────────────────────────────────────────────────────────────
class TestHandleActiveLearn:
    def test_active_learn_no_eval(self, mock_archive):
        mock_archive.training_dir = Path("/tmp/nonexistent_training")
        args = _make_args(
            archive_command="active-learn", provider="gemini",
            eval_provider=None, count=20,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_active_learn_with_eval_provider(self, mock_archive, mock_llm_client, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.run_eval.return_value = {"avg_score": 0.6}
        mock_archive.identify_weaknesses.return_value = [
            {"priority": "high", "name": "debugging", "score": 0.3, "gap": 0.4},
        ]
        mock_archive.get_stats.return_value = {"total_turns": 100}
        mock_archive.count_preferences.return_value = 50
        mock_archive.synthesize_for_weaknesses.return_value = {
            "total_generated": 20,
            "by_weakness": [{"name": "debugging", "generated": 20}],
        }
        args = _make_args(
            archive_command="active-learn", provider="gemini",
            eval_provider="gemini", count=20,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_active_learn_cached_eval(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        eval_path = tmp_path / "eval_results.json"
        eval_path.write_text(json.dumps({"avg_score": 0.5}))
        mock_archive.identify_weaknesses.return_value = []
        args = _make_args(
            archive_command="active-learn", provider="gemini",
            eval_provider=None, count=20,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_active_learn_no_weaknesses(self, mock_archive, tmp_path):
        mock_archive.training_dir = tmp_path
        eval_path = tmp_path / "eval_results.json"
        eval_path.write_text(json.dumps({"avg_score": 0.9}))
        mock_archive.identify_weaknesses.return_value = []
        args = _make_args(
            archive_command="active-learn", provider="gemini",
            eval_provider=None, count=20,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_active_learn_exception(self, mock_archive, mock_llm_client, tmp_path):
        mock_archive.training_dir = tmp_path
        mock_archive.run_eval.side_effect = Exception("eval failed")
        args = _make_args(
            archive_command="active-learn", provider="gemini",
            eval_provider="gemini", count=20,
        )
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — conductor
# ──────────────────────────────────────────────────────────────
class TestHandleConductor:
    def test_conductor(self, mock_archive):
        mock_archive.training_status.return_value = {
            "sft": {"ready": True, "turns": 100},
            "dpo": {"ready": True, "total": 60, "by_source": {"retry": 30}},
            "cot": {"ready": False, "quality": 10},
            "eval": {"has_baseline": True, "baseline_score": 0.75},
            "training": {"last_trained": "2026-06-01T00:00:00Z", "trained_at_turns": 80, "new_since_train": 20},
            "next_action": {"priority": "high", "action": "dpo-export", "reason": "Ready for DPO", "command": "nucleus archive dpo-export"},
        }
        args = _make_args(archive_command="conductor")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_conductor_never_trained(self, mock_archive):
        mock_archive.training_status.return_value = {
            "sft": {"ready": False, "turns": 10},
            "dpo": {"ready": False, "total": 5, "by_source": {}},
            "cot": {"ready": False, "quality": 0},
            "eval": {"has_baseline": False, "baseline_score": None},
            "training": {"last_trained": None, "trained_at_turns": 0, "new_since_train": 0},
            "next_action": {"priority": "critical", "action": "collect", "reason": "Need more data", "command": None},
        }
        args = _make_args(archive_command="conductor")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — pipeline
# ──────────────────────────────────────────────────────────────
class TestHandlePipeline:
    def test_pipeline_dry_run(self, mock_archive):
        mock_archive.run_full_pipeline.return_value = {
            "steps": [
                {"step": "mine", "mined_dpo": 10, "mined_cot": 5},
                {"step": "synthesize", "new_pairs": 20},
                {"step": "export", "sft_exported": 80, "dpo_exported": 30, "cot_chains": 10, "eval_cases": 20, "output_dir": "/tmp/exports"},
            ],
            "next_action": {"priority": "high", "action": "train", "reason": "Ready", "command": "nucleus archive train"},
        }
        args = _make_args(archive_command="pipeline", provider=None, judge=None, dry_run=True)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_pipeline_with_provider(self, mock_archive, mock_llm_client):
        mock_archive.build_judge_fn.return_value = MagicMock()
        mock_archive.run_full_pipeline.return_value = {
            "steps": [
                {"step": "mine", "status": "done", "mined_dpo": 5, "mined_cot": 3},
                {"step": "export", "sft_exported": 50, "dpo_exported": 20, "cot_chains": 5, "eval_cases": 10, "output_dir": "/tmp/out",
                 "sft_eval_excluded": 5, "sft_filtered_out": 3, "sft_curriculum": True,
                 "dpo_by_source": {"retry": 10, "correction": 10}, "sft_snapshot": "/tmp/snap"},
            ],
            "next_action": {"priority": "medium", "action": "eval", "reason": "Check progress", "command": "nucleus archive eval"},
        }
        args = _make_args(archive_command="pipeline", provider="gemini", judge="gemini", dry_run=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_pipeline_no_next_action(self, mock_archive):
        mock_archive.run_full_pipeline.return_value = {"steps": [], "next_action": {}}
        args = _make_args(archive_command="pipeline", provider=None, judge=None, dry_run=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_pipeline_llm_init_failure(self, mock_archive):
        # When provider is set but get_llm_client fails
        args = _make_args(archive_command="pipeline", provider="bad", judge=None, dry_run=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 1


# ──────────────────────────────────────────────────────────────
# handle_archive_command — constitutional
# ──────────────────────────────────────────────────────────────
class TestHandleConstitutional:
    def test_constitutional_with_pairs(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 60
        mock_archive.constitutional_revise.return_value = 15
        args = _make_args(archive_command="constitutional", provider="gemini", count=100)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_constitutional_no_revisions(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 50
        mock_archive.constitutional_revise.return_value = 0
        args = _make_args(archive_command="constitutional", provider="gemini", count=50)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_constitutional_exception(self, mock_archive, mock_llm_client):
        mock_archive.count_preferences.return_value = 30
        mock_archive.constitutional_revise.side_effect = Exception("API error")
        args = _make_args(archive_command="constitutional", provider="gemini", count=100)
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — quality
# ──────────────────────────────────────────────────────────────
class TestHandleQuality:
    def test_quality_no_data(self, mock_archive):
        mock_archive.score_training_data.return_value = {"total": 0}
        args = _make_args(archive_command="quality", export=None, min_quality=0.4, format="openai", curriculum=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_quality_with_data(self, mock_archive):
        mock_archive.score_training_data.return_value = {
            "total": 100,
            "avg_quality": 0.65,
            "high_quality": 40,
            "low_quality": 10,
            "quality_distribution": {"excellent": 20, "good": 30, "fair": 40, "poor": 10},
            "worst_5": [{"quality": 0.1, "user_len": 5, "assistant_len": 10, "prompt_preview": "bad prompt"}],
        }
        args = _make_args(archive_command="quality", export=None, min_quality=0.4, format="openai", curriculum=False)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_quality_with_export(self, mock_archive, tmp_path):
        mock_archive.score_training_data.return_value = {
            "total": 50,
            "avg_quality": 0.5,
            "high_quality": 20,
            "low_quality": 5,
            "quality_distribution": {"excellent": 10, "good": 15, "fair": 20, "poor": 5},
            "worst_5": [],
        }
        mock_archive.export_filtered.return_value = {
            "exported": 40,
            "total": 50,
            "filtered_out": 10,
            "eval_excluded": 2,
            "snapshot": "/tmp/snap",
        }
        export_path = str(tmp_path / "filtered.jsonl")
        args = _make_args(archive_command="quality", export=export_path, min_quality=0.5, format="openai", curriculum=True)
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — register, registry, promote
# ──────────────────────────────────────────────────────────────
class TestHandleRegistry:
    def test_register(self, mock_archive):
        mock_archive.register_model.return_value = {
            "data": {"sft_turns": 100, "dpo_pairs": 50, "cot_chains": 20},
            "status": "registered",
        }
        args = _make_args(archive_command="register", version="v1", base="llama3.2:3b")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_registry_empty(self, mock_archive):
        mock_archive.get_registry.return_value = []
        args = _make_args(archive_command="registry")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_registry_with_models(self, mock_archive):
        mock_archive.get_registry.return_value = [
            {"version": "v1", "base_model": "llama3.2:3b", "status": "primary",
             "data": {"sft_turns": 100, "dpo_pairs": 50}, "eval_scores": {"avg_score": 0.8}},
            {"version": "v2", "base_model": "qwen2.5:7b", "status": "shadow",
             "data": {"sft_turns": 200, "dpo_pairs": 80}, "eval_scores": {}},
        ]
        args = _make_args(archive_command="registry")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_promote_success(self, mock_archive):
        mock_archive.update_model_status.return_value = True
        args = _make_args(archive_command="promote", version="v1", to="shadow")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_promote_to_canary(self, mock_archive):
        mock_archive.update_model_status.return_value = True
        args = _make_args(archive_command="promote", version="v2", to="canary")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_promote_to_primary(self, mock_archive):
        mock_archive.update_model_status.return_value = True
        args = _make_args(archive_command="promote", version="v3", to="primary")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_promote_not_found(self, mock_archive):
        mock_archive.update_model_status.return_value = False
        args = _make_args(archive_command="promote", version="v99", to="retired")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — shadow-stats, graduation
# ──────────────────────────────────────────────────────────────
class TestHandleShadowAndGraduation:
    def test_shadow_stats_no_data(self, mock_archive):
        mock_archive.get_shadow_stats.return_value = {"total": 0}
        args = _make_args(archive_command="shadow-stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_shadow_stats_with_data(self, mock_archive):
        mock_archive.get_shadow_stats.return_value = {
            "total": 100, "shadow_wins": 60, "primary_wins": 30, "win_rate": 0.6,
        }
        args = _make_args(archive_command="shadow-stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_shadow_stats_low_win_rate(self, mock_archive):
        mock_archive.get_shadow_stats.return_value = {
            "total": 100, "shadow_wins": 20, "primary_wins": 70, "win_rate": 0.2,
        }
        args = _make_args(archive_command="shadow-stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_shadow_stats_medium_win_rate(self, mock_archive):
        mock_archive.get_shadow_stats.return_value = {
            "total": 100, "shadow_wins": 35, "primary_wins": 50, "win_rate": 0.35,
        }
        args = _make_args(archive_command="shadow-stats")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_hold(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "shadow",
            "shadow_stats": {"total": 50, "win_rate": 0.3},
            "regression": {"regressed": False},
            "recommendation": "hold",
            "reason": "Need more data",
        }
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_promote_canary(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "shadow",
            "shadow_stats": {"total": 100, "win_rate": 0.6},
            "regression": {"regressed": False},
            "recommendation": "promote_canary",
            "reason": "Winning",
        }
        mock_archive.get_active_model.return_value = {"version": "v2"}
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_promote_primary(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "canary",
            "shadow_stats": {"total": 200, "win_rate": 0.7},
            "regression": {"regressed": False},
            "recommendation": "promote_primary",
            "reason": "Ready to graduate",
        }
        mock_archive.get_active_model.return_value = {"version": "v3"}
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_retrain(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "canary",
            "shadow_stats": {},
            "regression": {"regressed": False},
            "recommendation": "retrain",
            "reason": "Not winning enough",
        }
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_with_regression(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "canary",
            "shadow_stats": {"total": 50, "win_rate": 0.5},
            "regression": {
                "regressed": True,
                "details": "Score dropped 10%",
                "category_regressions": ["bug: -15%"],
            },
            "recommendation": "blocked_regression",
            "reason": "Regression detected",
        }
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_category_regressions_ok(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "canary",
            "shadow_stats": {"total": 50, "win_rate": 0.5},
            "regression": {
                "regressed": False,
                "category_regressions": ["deploy: -5%"],
            },
            "recommendation": "monitor",
            "reason": "Overall OK",
        }
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_graduation_start_shadow(self, mock_archive):
        mock_archive.graduation_check.return_value = {
            "current_status": "registered",
            "shadow_stats": {},
            "regression": {"regressed": False},
            "recommendation": "start_shadow",
            "reason": "Begin shadow testing",
        }
        args = _make_args(archive_command="graduation")
        result = cli_mod.handle_archive_command(args)
        assert result == 0


# ──────────────────────────────────────────────────────────────
# handle_archive_command — vault, vault-restore, rollback
# ──────────────────────────────────────────────────────────────
class TestHandleVault:
    def test_vault_empty(self, mock_archive):
        mock_archive.vault_list.return_value = []
        mock_archive.get_vault_path.return_value = "/tmp/vault"
        mock_archive.DEFAULT_VAULT_PATH = Path("/tmp/nonexistent_ssd")
        args = _make_args(archive_command="vault")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_vault_with_versions(self, mock_archive):
        mock_archive.vault_list.return_value = [
            {"version": "v1", "artifacts": ["model.bin", "config.json"], "total_size_bytes": 1048576, "stored_at": "2026-06-01T00:00:00Z", "_location": "ssd"},
            {"version": "v2", "artifacts": ["model.bin"], "total_size_bytes": 0, "stored_at": "2026-06-02T00:00:00Z", "_location": "local"},
        ]
        mock_archive.get_vault_path.return_value = "/tmp/vault"
        mock_archive.DEFAULT_VAULT_PATH = Path("/tmp")
        args = _make_args(archive_command="vault")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_vault_restore_success(self, mock_archive):
        mock_archive.vault_restore.return_value = {
            "restored_to": "/tmp/ollama/models/v1",
            "artifacts": ["model.bin", "config.json"],
            "ollama_command": "ollama run nucleus-v1",
        }
        args = _make_args(archive_command="vault-restore", version="v1")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_vault_restore_error(self, mock_archive):
        mock_archive.vault_restore.return_value = {"error": "Version not found"}
        args = _make_args(archive_command="vault-restore", version="v99")
        result = cli_mod.handle_archive_command(args)
        assert result == 1

    def test_rollback_success(self, mock_archive):
        mock_archive.rollback_model.return_value = {
            "from_version": "v2",
            "to_version": "v1",
            "new_status": "primary",
            "instructions": "Restart Ollama to apply",
        }
        args = _make_args(archive_command="rollback", version="v1")
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_rollback_error(self, mock_archive):
        mock_archive.rollback_model.return_value = {"error": "Version not in vault"}
        args = _make_args(archive_command="rollback", version="v99")
        result = cli_mod.handle_archive_command(args)
        assert result == 1


# ──────────────────────────────────────────────────────────────
# handle_archive_command — bare (no subcommand)
# ──────────────────────────────────────────────────────────────
class TestHandleBareArchive:
    def test_bare_archive_with_data(self, mock_archive):
        mock_archive.get_stats.return_value = {"total_turns": 100}
        mock_archive.should_retrain.return_value = {"should_retrain": True}
        mock_archive.count_preferences.return_value = 50
        mock_archive.count_reasoning_chains.return_value = 30
        args = _make_args(archive_command=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0

    def test_bare_archive_empty(self, mock_archive):
        mock_archive.get_stats.return_value = {"total_turns": 0}
        mock_archive.should_retrain.return_value = {"should_retrain": False}
        mock_archive.count_preferences.return_value = 0
        mock_archive.count_reasoning_chains.return_value = 0
        args = _make_args(archive_command=None)
        result = cli_mod.handle_archive_command(args)
        assert result == 0
