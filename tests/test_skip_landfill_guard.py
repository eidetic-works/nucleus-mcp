"""G0 skip-landfill guard — pin sparse-environment SKIPs (ADR-0043 red-team).

Background
----------
PR #659 added a shared sparse-environment skip marker to the repo-root-dependent
tests: ``tests/_sparse.py::requires_repo_scripts`` — a ``pytest.mark.skipif``
keyed on the presence of the repo-root ``scripts/`` directory. In a full
checkout the marker is a no-op (``scripts/`` present → guarded tests RUN); in a
package-only sparse checkout it fires with the reason
``"repo-root scripts/ not present (sparse checkout)"`` so a missing sibling
directory becomes a clean SKIP instead of 11 hard failures.

Why this guard exists (PRINCIPAL G0)
------------------------------------
Conditional skips are a landfill: without a tripwire they silently accumulate.
A 12th, 13th, ... sparse-skip can be added and the suite still reports green in
CI while more and more coverage quietly evaporates in the sparse environment.
This guard is the tripwire. It:

  1. Counts the tests carrying the #659 sparse-skip *mechanism* by running a
     REAL pytest collection (a ``--collect-only`` sub-pass with an in-process
     hook that reads every collected item's ``skipif`` reason). Using real
     collection — not a static grep — means class-level markers are correctly
     expanded to their per-method items, i.e. exactly the set pytest itself
     would skip. The count is pinned at ``PINNED_SPARSE_SKIP_COUNT``.

  2. Enforces a *live reason predicate*: a test only counts if its skip reason
     is the real sparse-environment reason. A bare ``@pytest.mark.skip`` or a
     skipif with some unrelated reason does NOT count — so the guard cannot be
     satisfied (or defeated) by adding noise skips elsewhere.

  3. FAILS LOUDLY if the count changes: a 12th sparse-skip trips it (the
     landfill tripwire); removing one trips it too (the pin caught drift).

Raising the pin is a deliberate, reviewed act
---------------------------------------------
``PINNED_SPARSE_SKIP_COUNT`` is a human checkpoint, not an auto-updated cache.
If you legitimately add a new repo-root-dependent test, bump the number HERE in
the SAME PR and justify it in review. Never "fix" a red guard by blindly
bumping the number or by keying the guard on a weaker signal.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── The pinned contract ────────────────────────────────────────────────────
# Number of collected test ITEMS carrying the #659 sparse-skip mechanism.
# Provenance (full checkout, origin/main):
#   test_bin_scripts.py : test_cc_mirror_shim_forwards, test_backup_brain_shim_forwards  (2)
#   test_org.py::TestDelegateCLI                                                          (2)
#   test_org.py::TestAuditTokenCost                                                       (7)
# Raising this REQUIRES a deliberate edit + PR review (see module docstring).
PINNED_SPARSE_SKIP_COUNT = 11

# The canonical reason string emitted by tests/_sparse.py::requires_repo_scripts.
# This is the "live reason predicate" the guard keys on.
SPARSE_SKIP_REASON = "repo-root scripts/ not present (sparse checkout)"

# Import/usage token for the shared marker. Used only to scope which test files
# the collection sub-pass has to look at (keeps the guard fast: it does not
# re-collect the whole >11k-test suite). A new sparse-skip must reference one of
# these — either it imports ``requires_repo_scripts`` from ``._sparse`` or it
# hardcodes SPARSE_SKIP_REASON — so scoping on either token cannot miss one.
SPARSE_SKIP_MARKER = "requires_repo_scripts"

# In-process pytest plugin: after collection, dump each item's skipif reason(s).
_COLLECTOR_PLUGIN = '''
import json
import os


def pytest_collection_modifyitems(session, config, items):
    rows = []
    for item in items:
        # iter_markers propagates class-level markers down to each method item,
        # so a class decorated with @requires_repo_scripts is counted once per
        # test method — matching what pytest actually skips.
        for mark in item.iter_markers(name="skipif"):
            rows.append({"nodeid": item.nodeid, "reason": mark.kwargs.get("reason", "")})
    with open(os.environ["_LANDFILL_OUT"], "w", encoding="utf-8") as fh:
        json.dump(rows, fh)
'''

_TESTS_DIR = Path(__file__).resolve().parent
_PACKAGE_ROOT = _TESTS_DIR.parent


def _candidate_test_files() -> list[Path]:
    """Test files that could carry a sparse-skip (import the marker or the
    reason string). Excludes this guard file itself, whose source necessarily
    mentions both tokens."""
    me = Path(__file__).name
    hits: list[Path] = []
    for path in sorted(_TESTS_DIR.rglob("test_*.py")):
        if path.name == me:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if SPARSE_SKIP_MARKER in text or SPARSE_SKIP_REASON in text:
            hits.append(path)
    return hits


def _collect_skipif_rows() -> list[dict]:
    """Run a real pytest --collect-only sub-pass over the candidate files and
    return one row per (item, skipif-marker) with its reason."""
    targets = _candidate_test_files()
    assert targets, (
        "No test file references the sparse-skip mechanism "
        f"({SPARSE_SKIP_MARKER!r} / {SPARSE_SKIP_REASON!r}). The #659 mechanism "
        "appears to have been removed or renamed — update this guard deliberately."
    )
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "_landfill_collector.py").write_text(_COLLECTOR_PLUGIN, encoding="utf-8")
        out = tdp / "rows.json"
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (str(tdp), str(_PACKAGE_ROOT / "src"), env.get("PYTHONPATH", "")) if p
        )
        env["_LANDFILL_OUT"] = str(out)
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            *[str(t) for t in targets],
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "_landfill_collector",
            "--basetemp",
            str(tdp / "bt"),
        ]
        proc = subprocess.run(
            cmd, env=env, cwd=str(_PACKAGE_ROOT), capture_output=True, text=True
        )
        assert out.is_file(), (
            "collection sub-pass did not produce marker data — the collector "
            "plugin never ran.\nEXIT="
            f"{proc.returncode}\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
        return json.loads(out.read_text(encoding="utf-8"))


def test_sparse_reason_predicate_is_live():
    """Anchor the live reason predicate: the reason string this guard keys on
    must still be the one tests/_sparse.py ships. If the reason is renamed, the
    count read below would silently fall to zero — fail here first, with a clear
    pointer, instead of letting the pin drift unnoticed."""
    sparse_mod = _TESTS_DIR / "_sparse.py"
    assert sparse_mod.is_file(), "tests/_sparse.py (the #659 sparse-skip mechanism) is missing"
    assert SPARSE_SKIP_REASON in sparse_mod.read_text(encoding="utf-8"), (
        f"The canonical sparse-skip reason changed in tests/_sparse.py. Update "
        f"SPARSE_SKIP_REASON ({SPARSE_SKIP_REASON!r}) in this guard to match, "
        "then re-verify the pinned count."
    )


def test_sparse_skip_count_is_pinned():
    """Pin the number of sparse-environment SKIPs and enforce live reasons.

    Landfill tripwire: fails if a 12th sparse-skip is added. Also fails if one
    is removed (the pin caught drift). Either way, reconcile deliberately and
    adjust PINNED_SPARSE_SKIP_COUNT in review — do not silence.
    """
    rows = _collect_skipif_rows()

    # Live reason predicate: keep only skips whose reason IS the real
    # sparse-environment reason. Blanket/unrelated skips are excluded, so they
    # can neither pad nor defeat the count.
    sparse = [r for r in rows if r["reason"] == SPARSE_SKIP_REASON]
    assert all(r["reason"] == SPARSE_SKIP_REASON for r in sparse)  # invariant

    actual = len(sparse)
    assert actual == PINNED_SPARSE_SKIP_COUNT, (
        f"Sparse-environment SKIPs = {actual}, pinned = {PINNED_SPARSE_SKIP_COUNT}.\n"
        f"{'LANDFILL TRIPWIRE: a sparse-skip was ADDED. ' if actual > PINNED_SPARSE_SKIP_COUNT else ''}"
        f"{'A sparse-skip was REMOVED. ' if actual < PINNED_SPARSE_SKIP_COUNT else ''}"
        "If this change is intentional, bump PINNED_SPARSE_SKIP_COUNT in the same "
        "PR and justify it in review; never key the guard on a weaker signal.\n"
        "Sparse-skipped items:\n  " + "\n  ".join(sorted(r["nodeid"] for r in sparse))
    )
