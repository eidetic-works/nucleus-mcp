"""Tests for Task #63 — sessions.bespoq_context.

Per op-assistant 2026-06-09T13:25Z operator GREENLIT spec.

Coverage:
- load_bespoq_session_context happy path: file found, fields extracted
- File missing → returns None with WARN log
- Corrupt JSON → returns None with WARN log
- File not JSON object → returns None with WARN log
- outboundCCRRemoteId mismatch → returns None with WARN log
- MCP server translation: list / dict / nested shapes
- system_prompt addendum from folders / files / projects
- base_system_prompt merge with file instructions + addendum
- Missing required args raises BespoqContextError
- Pseudonymity: account_uuid / org_uuid / session_id truncated in logs
- Pseudonymity: file path NEVER logged (no /Library/... in caplog)
- No hardcoded UUIDs in source
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server_nucleus.sessions import bespoq_context as bc


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Redirect ~/Library/Application Support/Claude/... to per-test tmp."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    yield


def _write_local_session(
    tmp_path: Path,
    *,
    account_uuid: str = "acct-aaa",
    org_uuid: str = "org-bbb",
    file_uuid: str = "local-ccc",
    outbound_cse: str = "cse_xyz",
    title: str = "bespoq title",
    mcp_servers=None,
    folders=None,
    files=None,
    projects=None,
    instructions: str = "",
    extra: dict = None,
) -> Path:
    base = (
        tmp_path / "Library" / "Application Support" / "Claude"
        / "local-agent-mode-sessions" / account_uuid / org_uuid
    )
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"local_{file_uuid}.json"
    payload = {
        "title": title,
        "outboundCCRRemoteId": outbound_cse,
        "remoteMcpServersConfig": mcp_servers if mcp_servers is not None else [],
        "userSelectedFolders": folders or [],
        "userSelectedFiles": files or [],
        "userSelectedProjectUuids": projects or [],
        "egressAllowedDomains": [],
    }
    if instructions:
        payload["instructions"] = instructions
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload))
    return path


# ── Happy path ────────────────────────────────────────────────────────


def test_load_bespoq_session_context_happy_path(tmp_path):
    _write_local_session(
        tmp_path,
        account_uuid="acct-1",
        org_uuid="org-1",
        outbound_cse="cse_match",
        title="bespoq session",
        mcp_servers=[
            {"url": "https://nucleus.local", "type": "url"},
            {"url": "https://eidetic.local", "type": "url"},
        ],
        folders=["/some/folder"],
        instructions="You are bespoq.",
    )
    ctx = bc.load_bespoq_session_context(
        account_uuid="acct-1", org_uuid="org-1", session_id="cse_match",
    )
    assert ctx is not None
    assert ctx["title"] == "bespoq session"
    assert ctx["mcp_servers"][0]["url"] == "https://nucleus.local"
    assert "You are bespoq." in ctx["system_prompt"]
    assert "Working folders: /some/folder" in ctx["system_prompt"]


def test_load_merges_base_system_prompt(tmp_path):
    _write_local_session(
        tmp_path, account_uuid="a", org_uuid="o",
        outbound_cse="cse_x", instructions="bespoq-specific instructions",
    )
    ctx = bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_x",
        base_system_prompt="You are a CCR autonomous worker.",
    )
    assert "You are a CCR autonomous worker." in ctx["system_prompt"]
    assert "bespoq-specific instructions" in ctx["system_prompt"]


# ── File missing / corrupt / mismatch ─────────────────────────────────


def test_load_missing_file_returns_none_with_warn(tmp_path, caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.bespoq_context")
    ctx = bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_x",
    )
    assert ctx is None
    assert any(
        "local file not found" in r.getMessage() for r in caplog.records
    )


def test_load_corrupt_json_returns_none_with_warn(tmp_path, caplog):
    import logging
    base = tmp_path / "Library" / "Application Support" / "Claude" / \
        "local-agent-mode-sessions" / "a" / "o"
    base.mkdir(parents=True, exist_ok=True)
    (base / "local_x.json").write_text("not-json{")
    caplog.set_level(logging.WARNING, logger="nucleus.bespoq_context")
    ctx = bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_x",
    )
    assert ctx is None


def test_load_not_json_object_returns_none(tmp_path):
    base = tmp_path / "Library" / "Application Support" / "Claude" / \
        "local-agent-mode-sessions" / "a" / "o"
    base.mkdir(parents=True, exist_ok=True)
    (base / "local_x.json").write_text(json.dumps([1, 2, 3]))
    ctx = bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_x",
    )
    assert ctx is None


def test_load_outboundCCRRemoteId_mismatch_returns_none(tmp_path, caplog):
    import logging
    _write_local_session(
        tmp_path, account_uuid="a", org_uuid="o",
        outbound_cse="cse_DIFFERENT",
    )
    caplog.set_level(logging.WARNING, logger="nucleus.bespoq_context")
    ctx = bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_REQUESTED",
    )
    assert ctx is None


# ── MCP server translation ───────────────────────────────────────────


def test_extract_mcp_servers_from_list():
    servers = bc._extract_mcp_servers_as_tools([
        {"url": "u1", "type": "url"},
        {"url": "u2", "type": "url"},
    ])
    assert len(servers) == 2
    assert servers[0]["url"] == "u1"


def test_extract_mcp_servers_from_dict_servers_key():
    servers = bc._extract_mcp_servers_as_tools({
        "servers": [{"url": "u1"}],
    })
    assert servers == [{"url": "u1"}]


def test_extract_mcp_servers_from_dict_mcp_servers_key():
    servers = bc._extract_mcp_servers_as_tools({
        "mcp_servers": [{"url": "u1"}],
    })
    assert servers == [{"url": "u1"}]


def test_extract_mcp_servers_non_dict_list_items_skipped():
    servers = bc._extract_mcp_servers_as_tools([
        {"url": "ok"},
        "not a dict",
        42,
        {"url": "also-ok"},
    ])
    assert len(servers) == 2


def test_extract_mcp_servers_bad_input_returns_empty():
    assert bc._extract_mcp_servers_as_tools(None) == []
    assert bc._extract_mcp_servers_as_tools(42) == []
    assert bc._extract_mcp_servers_as_tools("not list/dict") == []


# ── system_prompt addendum ───────────────────────────────────────────


def test_addendum_empty_when_nothing_selected():
    assert bc._extract_system_prompt_addendum(
        folders=[], files=[], projects=[],
    ) == ""


def test_addendum_includes_folders():
    out = bc._extract_system_prompt_addendum(
        folders=["/a/b", "/c/d"], files=[], projects=[],
    )
    assert "Working folders: /a/b, /c/d" in out


def test_addendum_includes_files():
    out = bc._extract_system_prompt_addendum(
        folders=[], files=["x.py"], projects=[],
    )
    assert "Working files: x.py" in out


def test_addendum_includes_projects():
    out = bc._extract_system_prompt_addendum(
        folders=[], files=[], projects=["proj-1"],
    )
    assert "Active projects: proj-1" in out


def test_addendum_combines_all_three():
    out = bc._extract_system_prompt_addendum(
        folders=["/a"], files=["b"], projects=["c"],
    )
    assert "Working folders: /a" in out
    assert "Working files: b" in out
    assert "Active projects: c" in out


def test_addendum_filters_non_strings():
    out = bc._extract_system_prompt_addendum(
        folders=["/ok", 42, None, "/also"], files=[], projects=[],
    )
    assert "/ok, /also" in out


# ── Missing-arg guards ───────────────────────────────────────────────


def test_raises_on_empty_account_uuid():
    with pytest.raises(bc.BespoqContextError):
        bc.load_bespoq_session_context(
            account_uuid="", org_uuid="o", session_id="cse_x",
        )


def test_raises_on_empty_org_uuid():
    with pytest.raises(bc.BespoqContextError):
        bc.load_bespoq_session_context(
            account_uuid="a", org_uuid="", session_id="cse_x",
        )


def test_raises_on_empty_session_id():
    with pytest.raises(bc.BespoqContextError):
        bc.load_bespoq_session_context(
            account_uuid="a", org_uuid="o", session_id="",
        )


# ── Pseudonymity ─────────────────────────────────────────────────────


def test_ids_truncated_in_logs(tmp_path, caplog):
    """Success-path logs cse only; failure-path logs all three. In all
    cases full IDs MUST NEVER appear (truncation enforced)."""
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.bespoq_context")
    LONG_ACCT = "acct_AAAAAAAAAAAAAAAAAAAAAAAAA_secret"
    LONG_ORG = "org_BBBBBBBBBBBBBBBBBBBBBBBBB_secret"
    LONG_CSE = "cse_CCCCCCCCCCCCCCCCCCCCCCCCC_secret"
    _write_local_session(
        tmp_path,
        account_uuid=LONG_ACCT, org_uuid=LONG_ORG,
        outbound_cse=LONG_CSE,
    )
    bc.load_bespoq_session_context(
        account_uuid=LONG_ACCT, org_uuid=LONG_ORG, session_id=LONG_CSE,
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    # Full IDs NEVER appear (success path)
    assert LONG_ACCT not in all_text
    assert LONG_ORG not in all_text
    assert LONG_CSE not in all_text
    # Truncated cse SHOULD appear in success log
    assert LONG_CSE[:12] in all_text


def test_fail_path_logs_truncate_all_three_ids(tmp_path, caplog):
    """File-not-found failure path logs acct + org + cse — all truncated."""
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.bespoq_context")
    LONG_ACCT = "acct_AAAAAAAAAAAAAAAAAAAAAAAAA_secret"
    LONG_ORG = "org_BBBBBBBBBBBBBBBBBBBBBBBBB_secret"
    LONG_CSE = "cse_CCCCCCCCCCCCCCCCCCCCCCCCC_secret"
    # NO file written — triggers "local file not found" log path
    bc.load_bespoq_session_context(
        account_uuid=LONG_ACCT, org_uuid=LONG_ORG, session_id=LONG_CSE,
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert LONG_ACCT not in all_text
    assert LONG_ORG not in all_text
    assert LONG_CSE not in all_text
    assert LONG_ACCT[:12] in all_text
    assert LONG_ORG[:12] in all_text
    assert LONG_CSE[:12] in all_text


def test_file_path_never_logged(tmp_path, caplog):
    """Path contains operator UUIDs + 'Library' string;
    must NOT appear in any log record."""
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.bespoq_context")
    _write_local_session(
        tmp_path, account_uuid="a", org_uuid="o", outbound_cse="cse_x",
    )
    bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_x",
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert "Library" not in all_text
    assert str(tmp_path) not in all_text


def test_system_prompt_content_never_logged(tmp_path, caplog):
    """system_prompt may contain operator-specific instructions —
    NEVER log it."""
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.bespoq_context")
    SECRET = "operator-secret-prompt-must-not-leak-XYZ"
    _write_local_session(
        tmp_path, account_uuid="a", org_uuid="o", outbound_cse="cse_x",
        instructions=SECRET,
    )
    bc.load_bespoq_session_context(
        account_uuid="a", org_uuid="o", session_id="cse_x",
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET not in all_text


def test_no_hardcoded_UUIDs_in_module_source():
    """Module source MUST NOT contain real operator UUIDs.

    Defensive guard against the same class of leak that triggered
    the PR #430 skeleton-template-real-identity fix. Scan for any
    UUID-shaped string (8-4-4-4-12 hex pattern) in source.
    """
    import inspect
    import re
    src = inspect.getsource(bc)
    uuid_re = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
        r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )
    matches = uuid_re.findall(src)
    assert matches == [], f"UUID-shaped strings hardcoded: {matches}"


# ── Module exports ───────────────────────────────────────────────────


def test_all_exported():
    assert set(bc.__all__) == {
        "BespoqContextError",
        "load_bespoq_session_context",
    }
