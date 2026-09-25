"""Comprehensive coverage tests for conversation_ingest_job.py."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.jobs import conversation_ingest_job


@pytest.mark.asyncio
async def test_run_conversation_ingest_success():
    """Successful ingest → ok True with merged result fields."""
    fake_result = {
        "sessions_processed": 3,
        "turns_created": 15,
        "preferences_found": 2,
        "chains_extracted": 1,
        "extra_field": "val",
    }
    fake_fn = MagicMock(return_value=fake_result)
    with patch(
        "mcp_server_nucleus.runtime.conversation_ops.ingest_conversations",
        fake_fn,
    ):
        result = await conversation_ingest_job.run_conversation_ingest()
    assert result["ok"] is True
    assert result["sessions_processed"] == 3
    assert result["turns_created"] == 15
    assert result["preferences_found"] == 2
    assert result["chains_extracted"] == 1
    assert result["extra_field"] == "val"
    fake_fn.assert_called_once_with(mode="incremental")


@pytest.mark.asyncio
async def test_run_conversation_ingest_empty_result():
    """Empty result dict → ok True, result merged (no extra keys)."""
    fake_fn = MagicMock(return_value={})
    with patch(
        "mcp_server_nucleus.runtime.conversation_ops.ingest_conversations",
        fake_fn,
    ):
        result = await conversation_ingest_job.run_conversation_ingest()
    assert result["ok"] is True
    # Empty result dict means only "ok" key is present (source uses .get with defaults for logging only)
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_run_conversation_ingest_exception():
    """ingest_conversations raises → caught, returns error."""
    fake_fn = MagicMock(side_effect=RuntimeError("db connection lost"))
    with patch(
        "mcp_server_nucleus.runtime.conversation_ops.ingest_conversations",
        fake_fn,
    ):
        result = await conversation_ingest_job.run_conversation_ingest()
    assert result["ok"] is False
    assert "db connection lost" in result["error"]


@pytest.mark.asyncio
async def test_run_conversation_ingest_import_error():
    """Import failure → caught by broad except, returns error."""
    with patch(
        "builtins.__import__",
        side_effect=ImportError("module not found"),
    ):
        result = await conversation_ingest_job.run_conversation_ingest()
    assert result["ok"] is False
    assert "error" in result
