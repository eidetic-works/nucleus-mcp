"""Coverage tests for mcp_server_nucleus.core.tool_registration_impl."""
import sys
from unittest import mock

import pytest

from mcp_server_nucleus.core import tool_registration_impl as tri


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module-level state between tests."""
    tri._REGISTERING_TOOL = False
    tri._original_mcp_tool = None
    tri._rpc_firewall_hook = None
    yield
    tri._REGISTERING_TOOL = False
    tri._original_mcp_tool = None
    tri._rpc_firewall_hook = None


class FakeMCP:
    """Minimal MCP mock that records tool registrations."""
    def __init__(self):
        self.registered = []
        self.tool = self._tool_impl

    def _tool_impl(self, *args, **kwargs):
        def decorator(fn):
            self.registered.append(fn.__name__)
            # Return a mock tool object that is callable
            tool = mock.MagicMock()
            tool.__name__ = fn.__name__
            return tool
        if len(args) == 1 and callable(args[0]):
            fn = args[0]
            self.registered.append(fn.__name__)
            tool = mock.MagicMock()
            tool.__name__ = fn.__name__
            return tool
        return decorator


def test_configure_tiered_tool_registration():
    mcp = FakeMCP()
    original = mcp.tool
    result = tri.configure_tiered_tool_registration(mcp)
    assert result is mcp
    assert tri._original_mcp_tool is original
    assert mcp.tool is tri._tiered_tool_wrapper


def test_configure_with_custom_firewall_hook():
    mcp = FakeMCP()
    custom_hook = mock.MagicMock()
    tri.configure_tiered_tool_registration(mcp, rpc_firewall_hook=custom_hook)
    assert tri._rpc_firewall_hook is custom_hook


def test_tiered_wrapper_not_configured_raises():
    tri._original_mcp_tool = None
    with pytest.raises(RuntimeError, match="not configured"):
        tri._tiered_tool_wrapper(mock.MagicMock())


def test_tiered_wrapper_allowed_tool():
    mcp = FakeMCP()
    tri.configure_tiered_tool_registration(mcp)

    @mcp.tool()
    def nucleus_engrams():
        """Test tool."""
        return "hello"

    # Tool should be registered
    assert "nucleus_engrams" in mcp.registered


def test_tiered_wrapper_filtered_tool(monkeypatch):
    mcp = FakeMCP()
    # Set tier to 0 (LAUNCH) so non-launch tools are filtered
    monkeypatch.setenv("NUCLEUS_TOOL_TIER", "0")
    # Clear the tier cache
    import mcp_server_nucleus.tool_tiers as tt
    tt._ACTIVE_TIER_CACHE = 0
    tri.configure_tiered_tool_registration(mcp)

    @mcp.tool()
    def some_unknown_tool():
        """Filtered tool."""
        return "filtered"

    # Tool should NOT be registered (filtered by tier)
    assert "some_unknown_tool" not in mcp.registered
    # Restore cache
    tt._ACTIVE_TIER_CACHE = None


def test_tiered_wrapper_decorator_no_parens():
    mcp = FakeMCP()
    tri.configure_tiered_tool_registration(mcp)

    @mcp.tool
    def nucleus_engrams():
        """Test tool."""
        return "hello"

    assert "nucleus_engrams" in mcp.registered


def test_tiered_wrapper_recursion_guard():
    """When _REGISTERING_TOOL is True, calls original directly."""
    mcp = FakeMCP()
    tri.configure_tiered_tool_registration(mcp)
    tri._REGISTERING_TOOL = True

    @mcp.tool()
    def nucleus_engrams():
        return "hello"

    # Should still be registered via original
    assert "nucleus_engrams" in mcp.registered


def test_default_rpc_firewall_hook_protected_path():
    """default_rpc_firewall_hook blocks writes to protected paths."""
    tri._rpc_firewall_hook = tri.default_rpc_firewall_hook

    # Mock the watchdog with protected paths
    fake_watchdog = mock.MagicMock()
    fake_watchdog.protected_paths = ["/protected/file.py"]

    with mock.patch("mcp_server_nucleus.runtime.hypervisor_ops._watchdog", fake_watchdog):
        with pytest.raises(PermissionError, match="RPC Firewall"):
            tri.default_rpc_firewall_hook(
                "write_to_file",
                (),
                {"TargetFile": "/protected/file.py"},
            )


def test_default_rpc_firewall_hook_unprotected_path():
    """default_rpc_firewall_hook allows writes to non-protected paths."""
    fake_watchdog = mock.MagicMock()
    fake_watchdog.protected_paths = ["/protected/file.py"]

    with mock.patch("mcp_server_nucleus.runtime.hypervisor_ops._watchdog", fake_watchdog):
        # Should not raise
        tri.default_rpc_firewall_hook("write_to_file", (), {"TargetFile": "/safe/file.py"})


def test_default_rpc_firewall_hook_non_write_tool():
    """default_rpc_firewall_hook ignores non-write tools."""
    tri.default_rpc_firewall_hook("read_file", (), {"path": "/anywhere"})


def test_default_rpc_firewall_hook_no_target_path():
    """default_rpc_firewall_hook does nothing when no target path."""
    tri.default_rpc_firewall_hook("write_to_file", (), {})


def test_default_rpc_firewall_hook_exception_swallowed():
    """default_rpc_firewall_hook swallows non-PermissionError exceptions."""
    fake_watchdog = mock.MagicMock()
    fake_watchdog.protected_paths = ["/protected"]
    # Make Path.resolve raise
    with mock.patch("mcp_server_nucleus.runtime.hypervisor_ops._watchdog", fake_watchdog):
        # Should not raise — exception is logged and swallowed
        tri.default_rpc_firewall_hook("write_to_file", (), {"TargetFile": None})


def test_callable_tool_proxy():
    """When the registered tool is not callable, a CallableTool proxy is created."""
    mcp = FakeMCP()

    # Override tool to return a non-callable object
    class NonCallableTool:
        """A tool object that is NOT callable."""
        def __init__(self):
            self.name = "test"
        def model_dump(self, *a, **kw):
            return {"dump": True}
        def model_dump_json(self, *a, **kw):
            return '{"dump": true}'
        def some_attr(self):
            return "attr_value"

    def non_callable_tool(*args, **kwargs):
        def decorator(fn):
            return NonCallableTool()
        return decorator

    mcp.tool = non_callable_tool
    tri.configure_tiered_tool_registration(mcp)

    @mcp.tool()
    def nucleus_engrams():
        """Test tool."""
        return "result"

    # The returned tool should be callable via the CallableTool proxy
    result = nucleus_engrams()
    assert result == "result"
    # Proxy delegates to underlying tool
    assert nucleus_engrams.model_dump() == {"dump": True}
    assert nucleus_engrams.some_attr() == "attr_value"


def test_callable_tool_model_dump():
    """CallableTool proxy delegates model_dump and model_dump_json."""
    mcp = FakeMCP()

    class NonCallableTool:
        def model_dump(self, *a, **kw):
            return {"dump": True}
        def model_dump_json(self, *a, **kw):
            return '{"dump": true}'

    def non_callable_tool(*args, **kwargs):
        def decorator(fn):
            return NonCallableTool()
        return decorator

    mcp.tool = non_callable_tool
    tri.configure_tiered_tool_registration(mcp)

    @mcp.tool()
    def nucleus_engrams():
        return "x"

    assert nucleus_engrams.model_dump() == {"dump": True}
    assert nucleus_engrams.model_dump_json() == '{"dump": true}'


def test_callable_tool_getattr_proxy():
    """CallableTool.__getattr__ delegates to the underlying tool."""
    mcp = FakeMCP()

    class NonCallableTool:
        custom_attribute = "custom_value"
        def model_dump(self, *a, **kw):
            return {}
        def model_dump_json(self, *a, **kw):
            return '{}'

    def non_callable_tool(*args, **kwargs):
        def decorator(fn):
            return NonCallableTool()
        return decorator

    mcp.tool = non_callable_tool
    tri.configure_tiered_tool_registration(mcp)

    @mcp.tool()
    def nucleus_engrams():
        return "x"

    assert nucleus_engrams.custom_attribute == "custom_value"


def test_tiered_wrapper_registration_exception():
    """When the original mcp.tool raises, the exception propagates."""
    mcp = FakeMCP()

    def failing_tool(*args, **kwargs):
        def decorator(fn):
            raise RuntimeError("registration failed")
        return decorator

    mcp.tool = failing_tool
    tri.configure_tiered_tool_registration(mcp)

    with pytest.raises(RuntimeError, match="registration failed"):
        @mcp.tool()
        def nucleus_engrams():
            return "x"
