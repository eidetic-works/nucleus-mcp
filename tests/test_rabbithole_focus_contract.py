"""Focused persistence and validation tests for rabbithole focus contracts."""

import sqlite3

import pytest

from mcp_server_nucleus.rabbithole import store


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "rabbithole.db")
    try:
        yield connection
    finally:
        connection.close()


def _start(conn, session_id="session-1", **overrides):
    values = {
        "question": "Which fix is justified?",
        "deliverable": "A tested patch",
        "evidence_budget": 3,
        "depth_budget": 2,
        "exit_condition": "Enough evidence to choose an exit",
        "session_id": session_id,
    }
    values.update(overrides)
    return store.focus_start(conn, **values)


def test_connect_migrates_an_existing_store(tmp_path):
    db_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(db_path)
    legacy.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    legacy.commit()
    legacy.close()

    migrated = store.connect(db_path)
    try:
        columns = {
            row["name"]
            for row in migrated.execute("PRAGMA table_info(focus_contracts)").fetchall()
        }
    finally:
        migrated.close()

    assert {
        "session_id",
        "question",
        "deliverable",
        "evidence_budget",
        "depth_budget",
        "exit_condition",
        "status",
        "outcome",
        "evidence",
        "trigger",
        "owner",
        "missing_fact",
        "created_at",
        "updated_at",
        "resolved_at",
    } <= columns


def test_start_and_status_are_per_session(conn):
    started = _start(conn)

    assert started["active"] is True
    assert started["remaining_evidence_budget"] == 3
    assert store.focus_status(conn, "session-1")["contract"]["id"] == started["id"]
    assert store.focus_status(conn, "session-2") == {
        "session_id": "session-2",
        "active": False,
        "contract": None,
    }
    assert "already has active" in _start(conn)["error"]
    assert "error" not in _start(conn, session_id="session-2")


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"question": ""}, "question"),
        ({"deliverable": " "}, "deliverable"),
        ({"exit_condition": ""}, "exit_condition"),
        ({"evidence_budget": 0}, "evidence_budget"),
        ({"depth_budget": "bad"}, "depth_budget"),
    ],
)
def test_start_validation(conn, overrides, error):
    assert error in _start(conn, **overrides)["error"]


@pytest.mark.parametrize(
    ("outcome", "kwargs", "error"),
    [
        ("ACT", {"evidence": ""}, "requires evidence"),
        (
            "DEFER_WITH_TRIGGER",
            {"evidence": "logs", "trigger": "", "owner": "ops"},
            "trigger",
        ),
        (
            "DEFER_WITH_TRIGGER",
            {"evidence": "logs", "trigger": "new logs", "owner": ""},
            "owner",
        ),
        (
            "STOP_INSUFFICIENT",
            {"evidence": "searched tests", "missing_fact": ""},
            "missing_fact",
        ),
        ("UNKNOWN", {"evidence": "something"}, "outcome must be one of"),
    ],
)
def test_resolution_validation_keeps_contract_active(conn, outcome, kwargs, error):
    _start(conn)

    result = store.focus_resolve(conn, outcome, session_id="session-1", **kwargs)

    assert error in result["error"]
    assert store.focus_status(conn, "session-1")["active"] is True


@pytest.mark.parametrize(
    ("outcome", "kwargs"),
    [
        ("ACT", {"evidence": "failing test now passes"}),
        (
            "DEFER_WITH_TRIGGER",
            {"evidence": "dependency absent", "trigger": "dependency ships", "owner": "ops"},
        ),
        (
            "STOP_INSUFFICIENT",
            {"evidence": "repository searched", "missing_fact": "production trace"},
        ),
    ],
)
def test_valid_outcomes_resolve_explicitly(conn, outcome, kwargs):
    _start(conn)

    resolved = store.focus_resolve(
        conn, outcome, session_id="session-1", **kwargs
    )

    assert resolved["status"] == "resolved"
    assert resolved["outcome"] == outcome
    assert resolved["resolved_at"]
    assert store.focus_status(conn, "session-1")["active"] is False


def test_reads_and_writes_do_not_resolve_contract(conn):
    _start(conn, evidence_budget=2)

    first = store.focus_record_read(conn, "session-1")
    store.hook_reset(conn, "session-1")
    second = store.focus_record_read(conn, "session-1")

    assert first["contract"]["remaining_evidence_budget"] == 1
    assert second["contract"]["remaining_evidence_budget"] == 0
    assert second["active"] is True
    assert "already has active" in _start(conn)["error"]

    store.focus_resolve(conn, "ACT", "two relevant reads", session_id="session-1")
    assert "error" not in _start(conn)


def test_weekly_review_reports_action_conversion_without_a_daemon(conn):
    _start(conn)
    store.focus_resolve(conn, "ACT", "tested patch", session_id="session-1")
    _start(conn)
    store.focus_resolve(
        conn,
        "DEFER_WITH_TRIGGER",
        "dependency absent",
        trigger="dependency ships",
        owner="ops",
        session_id="session-1",
    )
    _start(conn)

    review = store.weekly_review(conn)

    assert review["focus_contracts"] == {
        "total": 3,
        "resolved": 2,
        "acted": 1,
        "deferred": 1,
        "insufficient": 0,
        "active": 1,
        "action_conversion_rate": 0.5,
    }
    assert "Focus contracts: 2/3 resolved" in review["narrative"]
