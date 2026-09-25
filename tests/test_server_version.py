"""Tests for the real (unmocked) ``mcp_server_nucleus.mcp`` server version.

Asserts that the FastMCP server object carries the package's own version —
not the upstream fastmcp distribution version, and not the ``"unknown"``
fallback used when package metadata is unavailable.
"""

import importlib.metadata

import mcp_server_nucleus


def test_mcp_version_matches_package_version():
    """``mcp.version`` must equal ``mcp_server_nucleus.__version__``."""
    assert mcp_server_nucleus.mcp.version == mcp_server_nucleus.__version__


def test_mcp_version_is_not_fastmcp_metadata_version():
    """``mcp.version`` must not leak the upstream fastmcp distribution version."""
    try:
        fastmcp_version = importlib.metadata.version("fastmcp")
    except importlib.metadata.PackageNotFoundError:
        import pytest

        pytest.skip("fastmcp package metadata is not installed")
    assert mcp_server_nucleus.mcp.version != fastmcp_version


def test_mcp_version_is_not_unknown():
    """``mcp.version`` must not be the ``"unknown"`` metadata fallback."""
    assert mcp_server_nucleus.mcp.version != "unknown"
