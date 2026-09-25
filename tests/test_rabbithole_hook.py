"""Focused tests for the advisory rabbithole PostToolUse hook."""

import io
import json
import sqlite3

from mcp_server_nucleus.rabbithole import hook, store


def _payload(tool_name, tool_input, session_id="hook-session"):
    return {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _run_hook(monkeypatch, payload, db_path):
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.delenv("RABBITHOLE_HOOK_DISABLED", raising=False)
    monkeypatch.setenv("RABBITHOLE_DB_PATH", str(db_path))
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(hook.sys, "stdout", stdout)
    monkeypatch.setattr(hook.sys, "stderr", stderr)
    hook.main()
    return stdout.getvalue(), stderr.getvalue()


def test_contract_aware_warning_is_advisory(monkeypatch, tmp_path):
    db_path = tmp_path / "hook.db"
    conn = store.connect(db_path)
    store.focus_start(
        conn,
        question="Should this parser change?",
        deliverable="A tested parser decision",
        evidence_budget=2,
        depth_budget=1,
        exit_condition="Choose a validated exit",
        session_id="hook-session",
    )
    conn.close()
    monkeypatch.setenv("RABBITHOLE_DEPTH_DANGER", "1")
    monkeypatch.setenv("RABBITHOLE_DEPTH_RABBITHOLE", "2")

    stdout, stderr = _run_hook(
        monkeypatch,
        _payload("Read", {"file_path": "/repo/parser.py"}),
        db_path,
    )

    assert stderr == ""
    output = json.loads(stdout)
    human = output["systemMessage"]
    model = output["hookSpecificOutput"]["additionalContext"]
    for message in (human, model):
        assert "Should this parser change?" in message
        assert "evidence remaining 1/2" in message
        assert "ACT, DEFER_WITH_TRIGGER, STOP_INSUFFICIENT" in message
        assert "only focus_resolve closes" in message
    assert "permissionDecision" not in output["hookSpecificOutput"]


def test_write_resets_streak_but_does_not_resolve_contract(monkeypatch, tmp_path):
    db_path = tmp_path / "hook.db"
    conn = store.connect(db_path)
    store.focus_start(
        conn,
        question="Question",
        deliverable="Deliverable",
        evidence_budget=3,
        depth_budget=2,
        exit_condition="Exit",
        session_id="hook-session",
    )
    store.hook_increment(conn, "hook-session", "first.py")
    conn.close()

    stdout, stderr = _run_hook(
        monkeypatch,
        _payload("Edit", {"file_path": "/repo/other.py"}),
        db_path,
    )

    assert stdout == ""
    assert stderr == ""
    conn = store.connect(db_path)
    try:
        assert store.hook_get_state(conn, "hook-session") == {"depth": 0, "streak": []}
        status = store.focus_status(conn, "hook-session")
    finally:
        conn.close()
    assert status["active"] is True
    assert status["contract"]["evidence_used"] == 0


def test_existing_threshold_warning_without_contract(monkeypatch, tmp_path):
    db_path = tmp_path / "hook.db"
    monkeypatch.setenv("RABBITHOLE_DEPTH_DANGER", "2")
    monkeypatch.setenv("RABBITHOLE_DEPTH_RABBITHOLE", "4")

    first, _ = _run_hook(
        monkeypatch,
        _payload("Read", {"file_path": "/repo/one.py"}),
        db_path,
    )
    second, _ = _run_hook(
        monkeypatch,
        _payload("Read", {"file_path": "/repo/two.py"}),
        db_path,
    )

    assert first == ""
    output = json.loads(second)
    assert "2 reads, no edits (DANGER)" in output["systemMessage"]
    assert "Active focus question" not in output["systemMessage"]


def test_focus_failure_preserves_existing_threshold_warning(monkeypatch, tmp_path):
    db_path = tmp_path / "hook.db"
    monkeypatch.setenv("RABBITHOLE_DEPTH_DANGER", "1")
    monkeypatch.setenv("RABBITHOLE_DEPTH_RABBITHOLE", "2")

    def _fail_focus(*args, **kwargs):
        raise sqlite3.OperationalError("focus unavailable")

    monkeypatch.setattr(store, "focus_record_read", _fail_focus)
    stdout, stderr = _run_hook(
        monkeypatch,
        _payload("Read", {"file_path": "/repo/one.py"}),
        db_path,
    )

    assert "1 reads, no edits (DANGER)" in json.loads(stdout)["systemMessage"]
    assert "non-fatal focus error" in stderr


def test_fail_safe_swallows_malformed_input(monkeypatch, tmp_path):
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setenv("RABBITHOLE_DB_PATH", str(tmp_path / "hook.db"))
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO("not-json"))
    monkeypatch.setattr(hook.sys, "stdout", stdout)
    monkeypatch.setattr(hook.sys, "stderr", stderr)

    hook.main()

    assert stdout.getvalue() == ""
    assert "non-fatal error" in stderr.getvalue()


def test_classification_and_periodic_threshold_behavior_remain_unchanged():
    assert hook._classify("Read", {}) == "read"
    assert hook._classify("Edit", {}) == "write"
    assert hook._classify("WebFetch", {}) == "neutral"
    assert hook._should_emit(10, danger=10, rabbithole=15) is True
    assert hook._should_emit(11, danger=10, rabbithole=15) is False
    assert hook._should_emit(20, danger=10, rabbithole=15) is True
