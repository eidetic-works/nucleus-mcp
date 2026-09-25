"""Failures in the audit trail and the state loaders must not be silent (QG-3, QG-5).

These four sites all swallowed their exception with a bare `pass` or a bare
`return`, which made a disk-full or a corrupt file indistinguishable from normal
operation:

  - the JWT and IPC audit-ledger writers, which back the compliance features
  - the atomic task claim, where corruption looked exactly like contention
  - the session state loader, where a damaged session looked like a new one

They still swallow — a failed audit write must not break the auth call that
triggered it — but they now log. This checks the log actually fires, rather than
trusting that the edit was made, because the whole failure mode here is "nobody
noticed".

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_task_claim_says_corruption_not_contention(tmp_path, caplog):
    pytest.importorskip("pydantic", reason="runtime dep not installed in this checkout")
    db_mod = pytest.importorskip("mcp_server_nucleus.runtime.db")

    backend = db_mod.JSONBackend(brain_path=tmp_path) if hasattr(db_mod, "JSONBackend") else None
    if backend is None:
        pytest.skip("JSONBackend not exposed under that name")

    backend.tasks_path.parent.mkdir(parents=True, exist_ok=True)
    backend.tasks_path.write_text("{ this is not json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        claimed = backend.claim_task_atomic("task-1", "agent-a")

    assert claimed is False, "a corrupt ledger must still fail the claim"
    assert caplog.records, (
        "a corrupt tasks.json returned the same False as ordinary contention with "
        "nothing logged, so claims failed forever and looked normal"
    )
    assert "corruption" in caplog.text.lower()


def test_session_state_loader_reports_a_damaged_file(tmp_path, caplog):
    dsor_mod = pytest.importorskip("mcp_server_nucleus.runtime.dsor")

    sor = dsor_mod.SessionStateManager(session_id="sess-test", brain_path=tmp_path)

    sor.state_file.parent.mkdir(parents=True, exist_ok=True)
    sor.state_file.write_text("not json at all", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        state = sor.load_state()

    assert state is None, "a damaged state file still yields no state"
    assert caplog.records, (
        "a damaged session state returned a bare None, indistinguishable from "
        "'no session yet', so corruption silently became a fresh session"
    )


@pytest.mark.parametrize("module_name,func_name", [
    ("mcp_server_nucleus.runtime.auth.jwt_provider", "_log_event"),
    ("mcp_server_nucleus.runtime.auth.ipc_provider", "_persist_meter_entry"),
    ("mcp_server_nucleus.runtime.auth.ipc_provider", "_log_token_event"),
])
def test_audit_writers_no_longer_swallow_in_silence(module_name, func_name):
    """Static check: these three must not end their handler with a bare pass.

    Constructing a real provider needs key material and a populated brain, so
    this asserts the shape instead. A test that needs the whole auth stack up to
    check one log line is a test that gets skipped.
    """
    import ast

    # Resolved by path, never imported. jwt_provider pulls in cryptography and
    # db pulls in pydantic; a shape check that needs the runtime dependencies
    # installed is a shape check that gets skipped on a bare checkout.
    src = Path(__file__).resolve().parents[1] / "src"
    origin = src.joinpath(*module_name.split(".")).with_suffix(".py")
    assert origin.is_file(), f"cannot locate {module_name} at {origin}"
    tree = ast.parse(origin.read_text(encoding="utf-8"))

    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            target = node
            break
    assert target is not None, f"{module_name} has no {func_name}()"

    handlers = [n for n in ast.walk(target) if isinstance(n, ast.ExceptHandler)]
    assert handlers, f"{func_name} has no exception handler to check"
    for handler in handlers:
        body = handler.body
        assert not (len(body) == 1 and isinstance(body[0], ast.Pass)), (
            f"{module_name}.{func_name} swallows its exception with a bare pass. "
            f"This ledger is the evidence trail the compliance features are read "
            f"from; a write that stops working must be visible, not inferred later "
            f"from a gap."
        )
