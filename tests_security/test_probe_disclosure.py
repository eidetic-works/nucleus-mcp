"""Unauthenticated probes must not describe the server (HS-5).

`/ready` is exempt from tenant resolution and auth, so whatever it returns goes
to anybody who can reach the service. It returned the absolute brain path on
success and `str(e)` on failure. Probed against the live relay on 2026-09-11:

    $ curl -s https://relay.nucleusos.dev/ready
    {"status":"ready","brain":"/home/ubuntu/.nucleus/tenants/default/.brain"}

That one line gives an anonymous caller the OS username, the tenant directory
layout, and the name of the default tenant. The failure path was worse: a path
resolver's exception text names directories, environment variables, and
sometimes a user.

A probe needs a status code, not a story. These tests pin that, and pin which
paths are exempt from auth at all — `/metrics` must not join them, because it
serves process-global tool-call counts, error rates and latencies.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

APP = SRC / "mcp_server_nucleus" / "http_transport" / "app.py"
TENANT = SRC / "mcp_server_nucleus" / "http_transport" / "tenant.py"

pytest.importorskip("starlette")
pytest.importorskip("pytest_asyncio", reason="async handlers need pytest-asyncio")

def _app_module():
    """Import app.py, or skip.

    The AST checks below read the file as text and need nothing installed —
    those are what actually pin the fix. The handler tests import the module,
    which builds the whole Starlette app and pulls in fastmcp. A checkout
    without it, or an environment the app declines to build in, should skip
    these rather than report a security regression that is really a missing
    dependency.
    """
    try:
        import importlib

        return importlib.import_module("mcp_server_nucleus.http_transport.app")
    except Exception as e:  # noqa: BLE001 — any import-time failure means skip
        pytest.skip(f"app.py is not importable here: {type(e).__name__}: {e}")


def _source(path: Path, func: str) -> str:
    """The function's code with its docstring removed.

    The docstring has to go: these tests search for the very strings the fix
    removed, and the comment explaining the fix names them. Matching your own
    explanation is a test that can never pass.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        (n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func),
        None,
    )
    assert node is not None, f"{path.name} has no {func}()"
    body = list(node.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    assert body, f"{func}() is nothing but a docstring"
    return "\n".join(ast.unparse(stmt) for stmt in body)


# --- /ready must not describe the filesystem ------------------------------


def test_ready_does_not_return_the_brain_path():
    body = _source(APP, "ready")
    assert "str(brain)" not in body, (
        "GET /ready returns the absolute brain path to unauthenticated callers; "
        "on the live relay that disclosed the OS username and the tenant layout"
    )
    assert "'brain'" not in body and '"brain"' not in body


def test_ready_does_not_return_raw_exception_text():
    body = _source(APP, "ready")
    assert "str(e)" not in body, (
        "GET /ready returns the exception message to unauthenticated callers"
    )


def test_ready_logs_the_detail_it_stops_returning():
    """Withholding it from the response must not mean losing it."""
    body = _source(APP, "ready")
    assert "logger.exception" in body or "logger.error" in body, (
        "the failure detail is neither returned nor logged, so it is simply gone"
    )


@pytest.mark.asyncio
async def test_ready_still_answers_ready_when_the_brain_exists(tmp_path, monkeypatch):
    """Stripping the body must not break the probe."""
    app_mod = _app_module()

    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.common.get_brain_path", lambda *a, **k: brain
    )
    response = await app_mod.ready(object())
    assert response.status_code == 200
    assert json.loads(response.body) == {"status": "ready"}


@pytest.mark.asyncio
async def test_ready_reports_not_ready_with_a_503_and_nothing_else(tmp_path, monkeypatch):
    app_mod = _app_module()

    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.common.get_brain_path",
        lambda *a, **k: tmp_path / "absent" / ".brain",
    )
    response = await app_mod.ready(object())
    assert response.status_code == 503
    assert json.loads(response.body) == {"status": "not_ready"}


@pytest.mark.asyncio
async def test_a_raising_resolver_still_yields_a_bare_503(monkeypatch):
    app_mod = _app_module()

    def boom(*a, **k):
        raise RuntimeError("NUCLEUS_BRAIN_PATH=/home/someone/secret is not a directory")

    monkeypatch.setattr("mcp_server_nucleus.runtime.common.get_brain_path", boom)
    response = await app_mod.ready(object())
    assert response.status_code == 503
    body = response.body.decode()
    assert "secret" not in body and "someone" not in body, (
        "the exception text reached an unauthenticated caller"
    )


# --- what is exempt from auth at all --------------------------------------


def _skip_list() -> set:
    """Every literal path the tenant middleware lets through unauthenticated."""
    body = _source(TENANT, "dispatch")
    tree = ast.parse(body)
    paths = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and any(
            isinstance(op, ast.In) for op in node.ops
        ):
            for comparator in node.comparators:
                if isinstance(comparator, (ast.Tuple, ast.List, ast.Set)):
                    for elt in comparator.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            paths.add(elt.value)
    return paths


def test_metrics_is_not_exempt_from_auth():
    """It serves process-global tool counts, error rates and latencies."""
    assert "/metrics" not in _skip_list(), (
        "GET /metrics bypasses tenant resolution, so process-wide operational "
        "detail is served to any caller"
    )


def test_the_exempt_list_is_only_what_it_needs_to_be():
    """A new exemption should be a deliberate edit, not a quiet addition."""
    expected = {
        "/health", "/ready", "/",            # probes
        "/authorize", "/token", "/register", # OAuth, per the MCP DCR spec
        "/revoke", "/auth/clerk/callback",
    }
    assert _skip_list() == expected, (
        "the set of unauthenticated paths changed; every entry here is reachable "
        "without any credential, so confirm the addition is intended"
    )
