"""Guard test for the CORE FAST-GATE manifest (ADR-0043 W1).

The fast gate is defined by ``tests/core_gate_files.txt`` and run by
``scripts/core_gate.sh``. A manifest that silently decays — a path deleted, a
file renamed, the list truncated to zero — would degrade the gate to a no-op
that still exits green. This test is the tripwire against that.

It asserts two invariants:
  1. every manifest path resolves on disk (no dangling entries), and
  2. the manifest still selects more than 500 tests (baseline: 556).

Collection is done in a subprocess via ``pytest --collect-only`` against the
in-tree package (``PYTHONPATH=src``), so the guard measures exactly what the
gate runner selects — not an in-process re-import.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# tests/ -> package root (dir holding pyproject.toml and tests/core_gate_files.txt)
_PKG_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _PKG_ROOT / "tests" / "core_gate_files.txt"

# Floor for the guard. The gate covers the project spine (registration + memory
# SoR + relay); baseline is 556. 500 leaves headroom for churn while still
# catching a collapse toward zero.
_MIN_TESTS = 500


def _manifest_paths() -> list[str]:
    """Parse the manifest the same way scripts/core_gate.sh does."""
    out: list[str] = []
    for raw in _MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def test_manifest_exists() -> None:
    assert _MANIFEST.is_file(), f"core-gate manifest missing: {_MANIFEST}"


def test_manifest_paths_resolve() -> None:
    paths = _manifest_paths()
    assert paths, "core-gate manifest selected 0 files"
    missing = [p for p in paths if not (_PKG_ROOT / p).exists()]
    assert not missing, f"core-gate manifest has dangling path(s): {missing}"


def test_manifest_selects_more_than_500_tests() -> None:
    """The gate must keep selecting >500 tests — never silently decay to zero."""
    paths = _manifest_paths()
    assert paths, "core-gate manifest selected 0 files"

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        cwd=str(_PKG_ROOT),
        env={"PYTHONPATH": "src", "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True,
        text=True,
    )
    # --collect-only exits 0 on a clean collection; a nonzero code means a path
    # failed to import/collect, which is itself a manifest-decay signal.
    assert proc.returncode == 0, (
        f"pytest --collect-only failed (rc={proc.returncode}).\n"
        f"stdout tail:\n{proc.stdout[-2000:]}\n"
        f"stderr tail:\n{proc.stderr[-2000:]}"
    )

    m = re.search(r"(\d+)\s+tests?\s+collected", proc.stdout)
    assert m, f"could not parse collected count from pytest output:\n{proc.stdout[-2000:]}"
    collected = int(m.group(1))
    assert collected > _MIN_TESTS, (
        f"core-gate selects only {collected} tests (floor {_MIN_TESTS}); "
        f"manifest may have decayed — check {_MANIFEST.name}"
    )
