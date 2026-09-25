"""Coverage tests for mcp_server_nucleus.http_transport.server."""
import sys
from unittest import mock

import pytest

from mcp_server_nucleus.http_transport import server as http_server


def test_build_app(monkeypatch):
    """build_app returns a Starlette app with tenant middleware."""
    fake_app = mock.MagicMock()
    fake_app.add_middleware = mock.MagicMock()

    fake_mcp = mock.MagicMock()
    fake_mcp.http_app.return_value = fake_app

    fake_tenant_mw = mock.MagicMock()

    # Patch the imports inside build_app
    monkeypatch.setattr(sys.modules["mcp_server_nucleus"], "mcp", fake_mcp)
    monkeypatch.setattr(
        "mcp_server_nucleus.http_transport.tenant.NucleusTenantMiddleware",
        fake_tenant_mw,
    )

    result = http_server.build_app(transport="sse")
    assert result is fake_app
    fake_mcp.http_app.assert_called_once_with(transport="sse")
    fake_app.add_middleware.assert_called_once_with(fake_tenant_mw)


def test_build_app_default_transport(monkeypatch):
    fake_app = mock.MagicMock()
    fake_mcp = mock.MagicMock()
    fake_mcp.http_app.return_value = fake_app

    monkeypatch.setattr(sys.modules["mcp_server_nucleus"], "mcp", fake_mcp)
    monkeypatch.setattr(
        "mcp_server_nucleus.http_transport.tenant.NucleusTenantMiddleware",
        mock.MagicMock(),
    )

    result = http_server.build_app()
    assert result is fake_app
    fake_mcp.http_app.assert_called_once_with(transport="streamable-http")


def test_main_with_uvicorn(monkeypatch, capsys):
    """main() parses args and runs uvicorn."""
    fake_mcp = mock.MagicMock()
    fake_app = mock.MagicMock()
    fake_app.router.routes = []
    fake_mcp.http_app.return_value = fake_app

    monkeypatch.setattr(sys.modules["mcp_server_nucleus"], "mcp", fake_mcp)
    monkeypatch.setattr(
        "mcp_server_nucleus.http_transport.tenant.NucleusTenantMiddleware",
        mock.MagicMock(),
    )

    fake_relay_route = mock.MagicMock()
    monkeypatch.setattr(
        "mcp_server_nucleus.http_transport.relay_route.relay_route",
        fake_relay_route,
    )

    fake_uvicorn = mock.MagicMock()
    fake_uvicorn.run = mock.MagicMock()
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    monkeypatch.setattr(sys, "argv", ["nucleus-mcp-http", "--port", "9999"])

    http_server.main()

    fake_uvicorn.run.assert_called_once()
    call_kwargs = fake_uvicorn.run.call_args
    assert call_kwargs.kwargs["host"] == "127.0.0.1"
    assert call_kwargs.kwargs["port"] == 9999


def test_main_fallback_no_uvicorn(monkeypatch, capsys):
    """main() falls back to mcp.run when uvicorn is not available."""
    fake_mcp = mock.MagicMock()
    fake_app = mock.MagicMock()
    fake_app.router.routes = []
    fake_mcp.http_app.return_value = fake_app
    fake_mcp.run = mock.MagicMock()

    monkeypatch.setattr(sys.modules["mcp_server_nucleus"], "mcp", fake_mcp)
    monkeypatch.setattr(
        "mcp_server_nucleus.http_transport.tenant.NucleusTenantMiddleware",
        mock.MagicMock(),
    )
    monkeypatch.setattr(
        "mcp_server_nucleus.http_transport.relay_route.relay_route",
        mock.MagicMock(),
    )

    # Make import uvicorn fail
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "uvicorn":
            raise ImportError("no uvicorn")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(sys, "argv", ["nucleus-mcp-http", "--transport", "sse"])

    http_server.main()

    fake_mcp.run.assert_called_once()
    call_kwargs = fake_mcp.run.call_args
    assert call_kwargs.kwargs["transport"] == "sse"
