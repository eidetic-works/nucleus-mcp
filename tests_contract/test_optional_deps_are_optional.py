"""A dependency in an extra must not be required to import the code (RF-9).

`google-genai` is declared in `[project.optional-dependencies] full`, not in
`dependencies`, so a default `pip install nucleus-mcp` does not install it.

`runtime/llm_client.py` probes for it with `importlib.util.find_spec`, and the
surrounding comment says why: to learn whether the SDK is present without paying
its 0.5-2s import on every `import mcp_server_nucleus`. Correct goal. But
`find_spec` on a **dotted** name imports the parent package in order to search
it, so `find_spec("google.genai")` raises `ModuleNotFoundError` when `google` is
absent entirely — it does not return `None`. Unguarded, the probe written to make
the dependency optional made it mandatory.

Reproduced before the fix by blocking `google` at `sys.meta_path`:

    ModuleNotFoundError: No module named 'google'
    ... from mcp_server_nucleus.runtime.llm_client line 44

This test does the same thing, so it fails against the unguarded version rather
than asserting the shape of the fix. It deliberately does not check for a
try/except: a later rewrite that probes differently should still pass.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import importlib
import importlib.abc
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Probe target -> the distribution that provides it. Extend as more are added.
OPTIONAL_SDK_ROOTS = ["google"]


def _pyproject() -> str:
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_google_genai_is_still_an_extra_not_a_core_dependency():
    """The premise. If it becomes a core dependency this test stops meaning anything."""
    text = _pyproject()
    core = re.search(r"^dependencies\s*=\s*\[(.*?)^\]", text, re.S | re.M)
    assert core, "could not locate the core dependencies array in pyproject.toml"
    if "google-genai" in core.group(1):
        pytest.skip("google-genai is now a core dependency; the optionality question is moot")
    assert "google-genai" in text, "google-genai is declared nowhere; has the SDK been dropped?"


@pytest.mark.parametrize("blocked", OPTIONAL_SDK_ROOTS)
def test_llm_client_imports_when_the_optional_sdk_is_absent(blocked):
    """The finding itself, run in a subprocess so the block cannot leak into this one."""
    script = textwrap.dedent(
        f"""
        import sys, importlib.abc

        class Block(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path=None, target=None):
                if name == {blocked!r} or name.startswith({blocked!r} + "."):
                    raise ModuleNotFoundError(f"No module named {{name!r}}")
                return None

        sys.meta_path.insert(0, Block())
        for m in [k for k in sys.modules if k.startswith({blocked!r})]:
            del sys.modules[m]

        from mcp_server_nucleus.runtime import llm_client
        assert llm_client.HAS_GENAI is False, (
            "the SDK was blocked, so the availability flag must be False"
        )
        print("OK")
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
        timeout=180,
    )
    assert out.returncode == 0 and "OK" in out.stdout, (
        f"importing llm_client fails when {blocked!r} is absent, which is what a default "
        f"install looks like:\n{out.stderr.strip()[-1500:]}"
    )


def test_the_availability_flag_is_true_here_where_the_sdk_is_installed():
    """Guards against a fix that simply hardcodes False and calls it optional."""
    if importlib.util.find_spec("google") is None:
        pytest.skip("google-genai not installed in this environment")
    from mcp_server_nucleus.runtime import llm_client

    assert llm_client.HAS_GENAI is True, (
        "the SDK is installed here, so the probe should report it as available; a fix that "
        "always returns False would disable the new SDK path everywhere"
    )
