"""The CLI must not pay for the MCP server stack it is not using.

Measured 2026-08-23, before any fix:

    nucleus --version   8.63s median
    nucleus --help      6.73s median
    import mcp_server_nucleus   4.74s median  (stdlib baseline: 0.05s)

`-X importtime` attributes 4.99s cumulative to `fastmcp`. The cause is
__init__.py:127, which builds a module-level FastMCP singleton eagerly:

    try:
        from fastmcp import FastMCP
        mcp = FastMCP("Nucleus Brain", version=__version__)

None of it is project code -- mcp.types 419ms self, fastmcp.settings 233ms,
key_value.aio.stores.base 217ms, plus beartype, a redis store, httpx_sse. The
file already resolves its OWN submodules lazily through a PEP 562 __getattr__,
and then eagerly imports the one expensive third-party dependency.

`nucleus --version` prints a string. It has no business loading an MCP server.

The fix is to move the singleton into the existing __getattr__. The @mcp.tool
decorators in tools/*.py still get the real object, because those modules are
only imported during registration, which is already lazy.

These tests are an opposed set: one proves the cost is gone, the others prove
the fix did not break the thing the eager import was there for.
"""
import subprocess
import sys
import time

import pytest

_BUDGET_S = 2.0
_BASELINE_MODULE_COUNT = 18  # tools._ALL_MODULE_NAMES, updated after adding "runs" facade


def _run_py(code: str):
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180)


def test_importing_cli_does_not_import_fastmcp():
    """THE FIX: importing the CLI must not drag in the MCP server stack.

    Fails before the fix -- fastmcp lands in sys.modules via __init__.py:127.
    """
    out = _run_py(
        "import sys, mcp_server_nucleus.cli; "
        "print('fastmcp' in sys.modules or 'mcp.server.fastmcp' in sys.modules)"
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip() == "False", (
        "importing mcp_server_nucleus.cli loaded fastmcp. A CLI that only parses "
        "arguments is paying ~5s for an MCP server stack it never uses."
    )


def test_version_is_fast():
    """A stranger's first command must not take the better part of ten seconds."""
    ts = []
    for _ in range(3):
        s = time.perf_counter()
        r = subprocess.run(
            [sys.executable, "-m", "mcp_server_nucleus.cli", "--version"],
            capture_output=True, text=True, timeout=180,
        )
        ts.append(time.perf_counter() - s)
    median = sorted(ts)[1]
    assert median < _BUDGET_S, (
        f"`nucleus --version` median {median:.2f}s exceeds the {_BUDGET_S}s budget "
        f"(runs: {[f'{t:.2f}' for t in ts]}). Measured 8.63s before the lazy-import fix."
    )


def test_mcp_singleton_is_still_a_real_server_when_asked_for():
    """OPPOSED: laziness must not turn `mcp` into a stub for real MCP use."""
    out = _run_py(
        "import mcp_server_nucleus as m; "
        "obj = m.mcp; print(type(obj).__name__)"
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip() == "FastMCP", (
        f"expected a real FastMCP instance on attribute access, got {out.stdout.strip()!r}"
    )


def test_every_tool_module_still_registers():
    """OPPOSED: the tool surface must be identical to before the fix.

    A faster import that quietly registers fewer tools is a regression wearing a
    speedup's clothes.
    """
    out = _run_py(
        "import mcp_server_nucleus  # noqa\n"
        "from mcp_server_nucleus import tools\n"
        "print(len(tools._ALL_MODULE_NAMES))"
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert int(out.stdout.strip()) == _BASELINE_MODULE_COUNT


def test_missing_fastmcp_still_falls_back_to_mockmcp():
    """OPPOSED: the except-ImportError path must survive being made lazy.

    Blocks `fastmcp` at the meta-path before the package is imported, which is
    what a machine without the dependency looks like.
    """
    code = (
        "import sys\n"
        "class Block:\n"
        "    def find_module(self, name, path=None):\n"
        "        return self if name == 'fastmcp' or name.startswith('fastmcp.') else None\n"
        "    def load_module(self, name):\n"
        "        raise ImportError('blocked for test')\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'fastmcp' or name.startswith('fastmcp.'):\n"
        "            raise ImportError('blocked for test')\n"
        "        return None\n"
        "sys.meta_path.insert(0, Block())\n"
        "import mcp_server_nucleus as m\n"
        "print(type(m.mcp).__name__)\n"
    )
    out = _run_py(code)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip() == "MockMCP", (
        f"without fastmcp the singleton must fall back to MockMCP, got {out.stdout.strip()!r}"
    )
