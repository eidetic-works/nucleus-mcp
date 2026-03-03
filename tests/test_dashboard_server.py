"""Tests for the Nucleus Governance Dashboard server module."""

import pytest
from unittest.mock import patch, MagicMock

from mcp_server_nucleus.dashboard.server import (
    GovernanceDashboardHandler,
    ReusableTCPServer,
    run_dashboard_server,
)


def test_handler_class_has_required_methods():
    """Verify the handler class has all required HTTP method handlers."""
    assert hasattr(GovernanceDashboardHandler, "do_GET")
    assert hasattr(GovernanceDashboardHandler, "do_POST")
    assert hasattr(GovernanceDashboardHandler, "do_OPTIONS")
    assert hasattr(GovernanceDashboardHandler, "_handle_api_get")
    assert hasattr(GovernanceDashboardHandler, "_handle_kyc_post")
    assert hasattr(GovernanceDashboardHandler, "_send_json")


def test_reusable_tcp_server_flag():
    """ReusableTCPServer must set allow_reuse_address."""
    assert ReusableTCPServer.allow_reuse_address is True


@patch("mcp_server_nucleus.dashboard.server.ReusableTCPServer")
def test_run_dashboard_server_lifecycle(mock_server_cls):
    """Verify the server boots on the requested port and shuts down on KeyboardInterrupt."""
    mock_instance = MagicMock()
    mock_server_cls.return_value = mock_instance

    # Simulate Ctrl+C immediately
    mock_instance.serve_forever.side_effect = KeyboardInterrupt()

    run_dashboard_server(port=9999, brain_path="/tmp/mock_brain")

    # Verify binding address
    mock_server_cls.assert_called_once()
    args, _ = mock_server_cls.call_args
    assert args[0] == ("0.0.0.0", 9999)
    assert args[1] == GovernanceDashboardHandler

    # Verify serve_forever then server_close
    mock_instance.serve_forever.assert_called_once()
    mock_instance.server_close.assert_called_once()
