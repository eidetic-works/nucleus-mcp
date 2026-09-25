"""Read-only HTTP surfaces must be tenant-scoped and not enumerate installs (HS-2, HS-3).

Neither of these is a bypass — they are read exposure:

  - the fleet dashboard resolved its brain from a process-wide env var rather
    than the per-request brain the middleware had already resolved, so every
    tenant on a multi-tenant deployment saw the same view
  - GET /telemetry/g35 returned every install_id the process had ever seen,
    with per-install activity counts, to any caller

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

fleet = pytest.importorskip("mcp_server_nucleus.http_transport.fleet_dashboard")
telemetry = pytest.importorskip("mcp_server_nucleus.http_transport.telemetry_route")
# The telemetry handlers are async. CI installs this via .[dev]; a bare checkout
# should skip these rather than error out at collection.
pytest.importorskip("pytest_asyncio", reason="async tests need pytest-asyncio")


class FakeState:
    def __init__(self, brain=None):
        if brain is not None:
            self.nucleus_brain_path = str(brain)


class FakeRequest:
    def __init__(self, brain=None, headers=None):
        self.state = FakeState(brain)
        self.headers = headers or {}


# --- HS-2: the dashboard must follow the request, not the process ----------

def test_dashboard_uses_the_brain_the_middleware_resolved(tmp_path, monkeypatch):
    process_brain = tmp_path / "process" / ".brain"
    tenant_brain = tmp_path / "tenants" / "acme" / ".brain"
    tenant_brain.mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(process_brain))

    resolved = fleet._request_brain(FakeRequest(brain=tenant_brain))
    assert resolved == tenant_brain, (
        "the dashboard served the process-wide brain, so every tenant saw the same view"
    )


def test_dashboard_falls_back_when_no_middleware_ran(tmp_path, monkeypatch):
    """stdio and solo have no middleware and must keep working."""
    process_brain = tmp_path / "process"
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(process_brain))
    assert fleet._request_brain(FakeRequest()) == process_brain.resolve()


def test_both_dashboard_handlers_are_request_scoped():
    """Repointing only one handler would leave the polled one leaking."""
    import ast

    tree = ast.parse(Path(fleet.__file__).read_text(encoding="utf-8"))
    for name in ("get_fleet_dashboard", "get_fleet_panel"):
        fn = next(
            (n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name),
            None,
        )
        assert fn is not None, f"fleet_dashboard.py has no {name}()"
        src = ast.unparse(fn)
        assert "_request_brain(request)" in src, f"{name}() is not request-scoped"
        assert "_brain_root()" not in src, (
            f"{name}() still reaches for the process-wide brain"
        )


# --- HS-3: install enumeration is operator-only ----------------------------

@pytest.fixture(autouse=True)
def clean_telemetry(monkeypatch):
    monkeypatch.delenv("NUCLEUS_TELEMETRY_ADMIN_TOKEN", raising=False)
    telemetry.reset_state()
    yield
    telemetry.reset_state()


async def _g35(request):
    return await telemetry.get_telemetry_g35(request)


def _body(response):
    import json
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_per_install_is_withheld_from_an_anonymous_caller():
    telemetry._seen_install_ids.update({"install-a", "install-b"})
    payload = _body(await _g35(FakeRequest()))
    assert payload["per_install"] == [], (
        "any caller who could reach the route got the full install roster"
    )
    assert payload["per_install_withheld"] is True


@pytest.mark.asyncio
async def test_aggregate_metrics_stay_public():
    """The aggregates are the point of the endpoint and must keep working."""
    telemetry._seen_install_ids.update({"install-a", "install-b"})
    payload = _body(await _g35(FakeRequest()))
    assert payload["distinct_installs"] == 2
    assert "g35_metrics" in payload and "g35_pass" in payload


@pytest.mark.asyncio
async def test_the_operator_token_unlocks_the_detail(monkeypatch):
    monkeypatch.setenv("NUCLEUS_TELEMETRY_ADMIN_TOKEN", "operator-secret")
    telemetry._seen_install_ids.add("install-a")
    req = FakeRequest(headers={"authorization": "Bearer operator-secret"})
    payload = _body(await _g35(req))
    assert payload["per_install_withheld"] is False
    assert [e["install_id"] for e in payload["per_install"]] == ["install-a"]


@pytest.mark.asyncio
async def test_a_wrong_token_does_not_unlock_the_detail(monkeypatch):
    monkeypatch.setenv("NUCLEUS_TELEMETRY_ADMIN_TOKEN", "operator-secret")
    telemetry._seen_install_ids.add("install-a")
    req = FakeRequest(headers={"authorization": "Bearer guess"})
    assert _body(await _g35(req))["per_install"] == []


@pytest.mark.asyncio
async def test_an_unset_token_cannot_be_matched_by_an_empty_header(monkeypatch):
    """With the variable unset, no header value may unlock the detail."""
    telemetry._seen_install_ids.add("install-a")
    for header in ({}, {"authorization": "Bearer "}, {"authorization": "Bearer "}):
        assert _body(await _g35(FakeRequest(headers=header)))["per_install"] == []
