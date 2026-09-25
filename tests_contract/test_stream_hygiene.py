"""Diagnostics must not corrupt the data stream (QG-6).

The standalone-mode banner in ``mcp_server_nucleus/__init__.py`` terminated with
an escaped ``"\\\\n"`` — the two literal characters, not a newline. On stderr
alone that is invisible. The moment the streams are merged, which is what CI
logs, ``2>&1`` and any subprocess with a combined pipe all do, the banner is
glued to the front of the first line of real output:

    [Nucleus Init] WARNING: ...verification mode.\\n{"key": "deploy-key", ...}
    {"key": "rotation", ...}

A reader consuming one JSON object per line silently drops its first record.
This was found while testing engram search: the first result appeared to be
missing, and the search itself was entirely correct.

This repo already has the rule — CLAUDE.md, "stdout belongs to JSON-RPC" — and
these tests extend it to the terminator, because an unterminated diagnostic
corrupts a merged stream just as surely as one written to the wrong stream.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


def _write_calls(path: Path):
    """Every sys.std*.write(literal) call in a module, as (stream, text)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "write" or not isinstance(node.func.value, ast.Attribute):
            continue
        stream = node.func.value.attr
        if stream not in ("stderr", "stdout"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(
            node.args[0].value, str
        ):
            yield stream, node.args[0].value


PACKAGE_INIT = SRC / "mcp_server_nucleus" / "__init__.py"


def test_no_diagnostic_write_carries_an_escaped_newline():
    """The defect class: "\\\\n" in a write is two characters, not a line break.

    Deliberately not "every write must end in a newline" — the tier banner just
    below the one that was broken is assembled from three writes and terminated
    by the last, which is correct code that a naive rule would flag.
    """
    for stream, text in _write_calls(PACKAGE_INIT):
        assert "\\n" not in text, (
            f"sys.{stream}.write({text!r}) contains a literal backslash-n. It renders as "
            "two characters and terminates nothing, so the next line of output is glued "
            "to this one on any merged stream."
        )


def test_the_standalone_banner_is_terminated():
    """The specific line that was broken, pinned by content."""
    banners = [
        text for _, text in _write_calls(PACKAGE_INIT)
        if "standalone/verification mode" in text
    ]
    assert banners, "the standalone-mode banner moved; update this test"
    for text in banners:
        assert text.endswith("\n") and not text.endswith("\\n"), (
            f"the standalone banner does not end in a real newline: {text!r}"
        )


def test_the_package_init_writes_no_diagnostics_to_stdout():
    """The existing rule, pinned: stdout carries protocol, not commentary."""
    offenders = [text for stream, text in _write_calls(PACKAGE_INIT) if stream == "stdout"]
    assert not offenders, f"diagnostics written to stdout: {offenders}"


@pytest.mark.skipif(
    not (SRC / "mcp_server_nucleus" / "cli.py").exists(), reason="CLI not present"
)
def test_a_merged_stream_keeps_every_line_of_real_output(tmp_path):
    """End to end: the failure this prevents is a dropped first record."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONPATH": str(SRC),
        "HOME": str(tmp_path),
        "NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain"),
    }
    run = lambda *a: subprocess.run(  # noqa: E731
        [sys.executable, "-m", "mcp_server_nucleus.cli", *a],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=120,
    )

    if run("init").returncode != 0:
        pytest.skip("nucleus init unavailable in this environment")
    for key, value in (("alpha-one", "first record"), ("beta-two", "second record")):
        run("engram", "write", key, value)

    clean = run("engram", "search", "record", "-q")
    keys = [ln for ln in clean.stdout.splitlines() if ln.strip()]
    if len(keys) < 2:
        pytest.skip("search returned too few rows to detect a dropped first line")

    # Merge the streams the way a CI log or `2>&1` would, then drop the
    # diagnostic lines. Every data line must still be intact.
    merged = subprocess.run(
        [sys.executable, "-m", "mcp_server_nucleus.cli",
         "engram", "search", "record", "-q"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, env=env, cwd=str(tmp_path), timeout=120,
    ).stdout
    surviving = [
        ln for ln in merged.splitlines()
        if ln.strip() and "[Nucleus" not in ln and "WARNING" not in ln
    ]
    assert surviving == keys, (
        "a diagnostic line was glued to the first row of output, so merging the "
        f"streams lost data: clean={keys} merged={surviving}"
    )
