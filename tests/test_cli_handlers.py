"""CI test: verify all CLI handler functions are defined.

Prevents the class of bug where a handler is called in the dispatch
block but never implemented — causing NameError crashes at runtime.
"""
import ast
import inspect


def test_all_dispatched_handlers_are_defined():
    """Every handle_*_command called in dispatch must have a def or import."""
    import mcp_server_nucleus.cli as cli_mod
    source = inspect.getsource(cli_mod)
    tree = ast.parse(source)

    # Collect all function definitions in the module
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined.add(node.name)
        # Also count imports
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined.add(alias.name)

    # Collect all handle_*_command calls in the dispatch block
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name.endswith('_command') and ('handle' in name or name.startswith('_handle')):
                called.add(name)

    missing = called - defined
    assert not missing, (
        f"{len(missing)} handler(s) called but not defined or imported: "
        f"{sorted(missing)}"
    )


def test_cli_handlers_module_importable():
    """cli_handlers.py can be imported without errors."""
    from mcp_server_nucleus import cli_handlers
    # Verify at least 37 handler functions exist
    handler_names = [
        name for name in dir(cli_handlers)
        if name.endswith('_command') and callable(getattr(cli_handlers, name))
    ]
    assert len(handler_names) >= 37, (
        f"Expected at least 37 handler functions, found {len(handler_names)}: "
        f"{handler_names}"
    )


def test_handler_functions_are_callable():
    """All exported handlers are actually callable functions."""
    from mcp_server_nucleus.cli_handlers import (
        handle_secure_command, handle_sovereign_command, handle_status_command,
        handle_billing_command, handle_features_command, handle_license_command,
        handle_config_command, handle_heartbeat_command,
    )
    for fn in [
        handle_secure_command, handle_sovereign_command, handle_status_command,
        handle_billing_command, handle_features_command, handle_license_command,
        handle_config_command, handle_heartbeat_command,
    ]:
        assert callable(fn), f"{fn.__name__} is not callable"
