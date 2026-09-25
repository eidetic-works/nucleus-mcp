"""The .mcp.json guard must not be disableable by the code it watches.

Why this exists: the guard asks the filesystem whether .mcp.json still exists
at teardown. test_gcloud_ops_coverage.py monkeypatches `os.path.exists`
globally to return False, so the guard reported that BOTH tracked .mcp.json
files had been mutated — 7 failures over files that were byte-identical to HEAD
the entire time, verified independently via git.

A guard the code under test can switch off is unreliable in BOTH directions.
Here it cried wolf. The symmetric case is worse: a test that patched the same
primitive while genuinely corrupting the file would have been waved through,
and the guard would have reported nothing.

Fixed by binding `os.stat` at import time, before any test can patch anything.
"""

import os

import pytest


def _guard_helpers():
    """Load the guard helper straight from conftest.py by path.

    conftest is not importable by name under this layout, and adding it to
    sys.path just for a test would change collection behaviour for everything
    else. Loading the file directly keeps the blast radius at zero.
    """
    import importlib.util
    from pathlib import Path
    src = Path(__file__).resolve().parent / "conftest.py"
    spec = importlib.util.spec_from_file_location("_conftest_probe", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._real_exists


def test_existence_check_survives_a_patched_os_path_exists(monkeypatch, tmp_path):
    """THE BUG, reproduced: the exact patch the gcloud tests apply."""
    real_exists = _guard_helpers()
    f = tmp_path / "present.json"
    f.write_text("{}")
    monkeypatch.setattr("os.path.exists", lambda p: False)
    assert real_exists(f) is True, (
        "the guard's existence check was disabled by a monkeypatched "
        "os.path.exists — it can be switched off by the code it watches"
    )


def test_existence_check_survives_a_patched_pathlib_exists(monkeypatch, tmp_path):
    """The other obvious way to blind it."""
    real_exists = _guard_helpers()
    f = tmp_path / "present.json"
    f.write_text("{}")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
    assert real_exists(f) is True


def test_it_still_reports_absence_correctly(tmp_path):
    """OPPOSED, load-bearing: a check that always returns True is not a fix,
    it is the same bug with the sign flipped. A genuinely missing file must
    still read as missing."""
    real_exists = _guard_helpers()
    assert real_exists(tmp_path / "definitely-not-here.json") is False


def test_it_reports_absence_even_when_exists_is_patched_to_True(monkeypatch, tmp_path):
    """OPPOSED: and cannot be fooled in the permissive direction either."""
    real_exists = _guard_helpers()
    monkeypatch.setattr("os.path.exists", lambda p: True)
    assert real_exists(tmp_path / "still-not-here.json") is False


def test_the_tracked_mcp_json_is_actually_intact():
    """The claim that justified calling the 7 failures false positives. If the
    file really had been corrupted, the guard was right and this fix is wrong."""
    from pathlib import Path
    base = Path(__file__).resolve()
    for p in (base.parents[1] / ".mcp.json", base.parents[2] / ".mcp.json"):
        if p.exists():
            assert p.stat().st_size > 0, f"{p} is empty — the guard was right"
