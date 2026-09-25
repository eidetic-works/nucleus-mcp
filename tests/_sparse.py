"""Shared skip guard for tests that reach outside the package.

A handful of tests exercise shell/python primitives that live in the
repo-root ``scripts/`` directory (one level ABOVE the ``mcp-server-nucleus``
package). A full checkout materialises that directory, so those tests run
normally. A package-only sparse checkout (scratch clones / subtree CI that
pull just ``mcp-server-nucleus/``) does not materialise the sibling
``scripts/`` directory, so the same tests would hard-FAIL on a missing path
rather than expressing a real regression.

This module exports a single ``skipif`` marker keyed on the presence of the
repo-root ``scripts/`` directory. It is a no-op in a full checkout (directory
present -> marker does not fire, every guarded test runs) and converts the
absent-resource case into a clean SKIP with an explicit reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# tests/ -> mcp-server-nucleus/ (package root) -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Repo-root ``scripts/`` directory. Absent under a package-only sparse checkout.
REPO_SCRIPTS_DIR = _REPO_ROOT / "scripts"

#: Fires (SKIP) only when the repo-root ``scripts/`` directory is not present.
requires_repo_scripts = pytest.mark.skipif(
    not REPO_SCRIPTS_DIR.is_dir(),
    reason="repo-root scripts/ not present (sparse checkout)",
)
