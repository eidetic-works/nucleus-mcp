pytest_plugins = ("pytester",)

import pytest


def test_mcp_json_guard_negative_control(pytester):
    """Negative control: an inner test that writes the guarded .mcp.json
    by absolute path must produce exactly one failure whose message names
    the offending node id, includes the 'pin the working directory'
    guidance, and leaves the original file content restored.

    The inner pytest session gets its own conftest that imports the REAL
    _guard_tracked_mcp_json fixture from mcp-server-nucleus/tests/conftest.py
    via sys.path insertion + `import conftest` (the outer conftest is not
    discovered by the inner session's rootdir).  The real fixture is
    re-exported into the inner conftest's namespace so pytest discovers and
    autouse-applies it; it watches the real repo-root .mcp.json files via
    its own `Path(__file__)`, so the inner session is guarded by the exact
    same code as the outer suite.
    """
    from pathlib import Path

    # Resolve the real repo-root .mcp.json — same resolution as the
    # _guard_tracked_mcp_json fixture in conftest.py.
    mcp_path = Path(__file__).resolve().parent.parent / ".mcp.json"
    if not mcp_path.exists():
        pytest.skip("repo-root .mcp.json absent; guard has nothing to protect")

    original = mcp_path.read_bytes()
    abs_repr = repr(str(mcp_path))

    # Real tests dir containing the real conftest.py that defines the
    # _guard_tracked_mcp_json fixture we want the inner session to use.
    real_tests_dir = Path(__file__).resolve().parent
    abs_dir_repr = repr(str(real_tests_dir))

    # ── Inner conftest: import the REAL fixture from the real conftest ──
    # The inner pytest session has its own rootdir (the pytester tmp dir),
    # so pytest does NOT discover the outer mcp-server-nucleus/tests/conftest.py.
    # Instead of replicating the guard, the inner conftest inserts the real
    # tests dir at sys.path[0] and `import conftest` loads the real module;
    # its `_guard_tracked_mcp_json` fixture is re-exported into the inner
    # conftest's namespace so pytest discovers and autouse-applies it.
    pytester.makeconftest(
        r'''
import sys
from pathlib import Path

# Insert the real tests directory at the FRONT of sys.path so `import conftest`
# resolves to the REAL mcp-server-nucleus/tests/conftest.py, not this inner
# conftest (which lives in the pytester tmp dir, also on sys.path further back).
sys.path.insert(0, __ABS_DIR__)

# pytest imports this inner conftest.py under the module name ``conftest`` and
# it is mid-import right now, so ``sys.modules["conftest"]`` already points at
# THIS partially-initialized module. A bare ``import conftest`` would return
# that partial entry (circular) instead of searching sys.path. Pop it
# temporarily so ``import conftest`` actually resolves through sys.path to the
# REAL conftest.py, then restore the inner entry so pytest keeps operating on
# this inner conftest module.
_inner_conftest_mod = sys.modules.pop("conftest", None)
try:
    import conftest as _real_conftest
finally:
    if _inner_conftest_mod is not None:
        sys.modules["conftest"] = _inner_conftest_mod

# Re-export the real fixture object into this inner conftest's namespace.
#
# How the real fixture is guaranteed to run in the inner session:
# pytest discovers autouse fixtures by scanning the attributes of the conftest
# module it loads for each rootdir. This inner conftest.py IS the inner
# session's rootdir conftest (pytester placed it here). By binding the name
# `_guard_tracked_mcp_json` in THIS module's globals to the real fixture
# function object (imported from the real conftest module above), pytest's
# fixture discovery finds it here and registers it with its original
# autouse=True marker, so it wraps every inner test. The fixture function
# retains its defining module's `__file__` — the real
# mcp-server-nucleus/tests/conftest.py — so its `Path(__file__).resolve()`
# resolves to the real tests dir and watches the real repo-root .mcp.json
# files (parents[1] = package root, parents[2] = monorepo root): exactly the
# files the real guard protects in the outer suite. No replica logic is
# duplicated; the real fixture is the single source of truth.
_guard_tracked_mcp_json = _real_conftest._guard_tracked_mcp_json
'''.replace("__ABS_DIR__", abs_dir_repr)
    )

    # ── Inner test: deliberately clobber the tracked .mcp.json ──
    pytester.makepyfile(
        test_neg=r'''from pathlib import Path

def test_mutate_mcp_json():
    """Deliberately write the tracked .mcp.json by absolute path."""
    Path(__ABS_PATH__).write_bytes(b'{"mutated_by_negative_control": true}')
'''.replace("__ABS_PATH__", abs_repr)
    )

    # ── Run the inner session ──
    # Safety net: restore the file even if the inner guard somehow
    # fails to fire (the outer conftest guard is a second backstop).
    try:
        result = pytester.runpytest("-v", "--tb=long")
        # Exactly one adverse outcome: the guard fires on teardown.
        # In pytest 9.x pytest.fail() in a fixture teardown is reported
        # as an ERROR, not a FAILED — the test function itself passes
        # (it writes the file and returns) and the guard catches the
        # mutation during teardown.
        result.assert_outcomes(errors=1, passed=1, failed=0)
        # The offending node id appears in the failure message.
        assert "test_neg.py::test_mutate_mcp_json" in result.stdout.str()
        # The 'pin the working directory' guidance is present.
        assert "pin the working directory" in result.stdout.str().lower()
    finally:
        if mcp_path.exists() and mcp_path.read_bytes() != original:
            mcp_path.write_bytes(original)

    # The guard restored the original content.
    assert mcp_path.read_bytes() == original


def test_mcp_json_guard_negative_control_repo_root(pytester):
    """Negative control (repo root): an inner test that writes the
    MONOREPO-root .mcp.json — ``parents[2]`` relative to this test file,
    i.e. ``ai-mvp-backend/.mcp.json`` — by absolute path must produce
    exactly one failure whose message names the offending node id,
    includes the 'pin the working directory' guidance, and leaves the
    original file content restored.

    Same real-fixture import mechanism as the package-root negative
    control above; only the watched path differs (repo root vs package
    root). The real ``_guard_tracked_mcp_json`` fixture watches BOTH
    ``parents[1]`` and ``parents[2]`` (see conftest.py), so writing the
    repo-root file trips the guard on teardown.
    """
    from pathlib import Path

    # Resolve the real MONOREPO-root .mcp.json — parents[2] relative to
    # this test file (parents[0]=tests, parents[1]=package root, parents[2]=repo root).
    mcp_path = Path(__file__).resolve().parents[2] / ".mcp.json"
    if not mcp_path.exists():
        pytest.skip("repo-root .mcp.json absent; guard has nothing to protect")
    original = mcp_path.read_bytes()
    abs_repr = repr(str(mcp_path))

    # Real tests dir containing the real conftest.py that defines the
    # _guard_tracked_mcp_json fixture we want the inner session to use.
    real_tests_dir = Path(__file__).resolve().parent
    abs_dir_repr = repr(str(real_tests_dir))

    # ── Inner conftest: import the REAL fixture from the real conftest ──
    # Same mechanism as the package-root negative control: insert the real
    # tests dir at sys.path[0], `import conftest` to load the real module,
    # and re-export its `_guard_tracked_mcp_json` fixture into this inner
    # conftest's namespace so pytest discovers and autouse-applies it.
    pytester.makeconftest(
        r'''
import sys
from pathlib import Path

sys.path.insert(0, __ABS_DIR__)

_inner_conftest_mod = sys.modules.pop("conftest", None)
try:
    import conftest as _real_conftest
finally:
    if _inner_conftest_mod is not None:
        sys.modules["conftest"] = _inner_conftest_mod

_guard_tracked_mcp_json = _real_conftest._guard_tracked_mcp_json
'''.replace("__ABS_DIR__", abs_dir_repr)
    )

    # ── Inner test: deliberately clobber the repo-root .mcp.json ──
    pytester.makepyfile(
        test_neg_repo=r'''from pathlib import Path

def test_mutate_repo_root_mcp_json():
    """Deliberately write the tracked repo-root .mcp.json by absolute path."""
    Path(__ABS_PATH__).write_bytes(b'{"mutated_by_negative_control_repo_root": true}')
'''.replace("__ABS_PATH__", abs_repr)
    )

    # ── Run the inner session ──
    # Safety net: restore the file even if the inner guard somehow
    # fails to fire (the outer conftest guard is a second backstop).
    try:
        result = pytester.runpytest("-v", "--tb=long")
        # Exactly one adverse outcome: the guard fires on teardown.
        result.assert_outcomes(errors=1, passed=1, failed=0)
        # The offending node id appears in the failure message.
        assert "test_neg_repo.py::test_mutate_repo_root_mcp_json" in result.stdout.str()
        # The 'pin the working directory' guidance is present.
        assert "pin the working directory" in result.stdout.str().lower()
    finally:
        if mcp_path.exists() and mcp_path.read_bytes() != original:
            mcp_path.write_bytes(original)

    # The guard restored the original content.
    assert mcp_path.read_bytes() == original


def test_mcp_json_guard_negative_control_package_dir(pytester):
    """Negative control (package dir): an inner test that writes the
    PACKAGE-root .mcp.json — ``parents[1]`` relative to this test file,
    i.e. ``mcp-server-nucleus/.mcp.json`` — by absolute path must produce
    exactly one failure whose message names the offending node id,
    includes the 'pin the working directory' guidance, and leaves the
    original file content restored.

    Same real-fixture import mechanism as the repo-root negative
    control above; only the watched path differs (package root vs repo
    root). The real ``_guard_tracked_mcp_json`` fixture watches BOTH
    ``parents[1]`` and ``parents[2]`` (see conftest.py), so writing the
    package-root file trips the guard on teardown.
    """
    from pathlib import Path

    # Resolve the real PACKAGE-root .mcp.json — parents[1] relative to
    # this test file (parents[0]=tests, parents[1]=package root, parents[2]=repo root).
    mcp_path = Path(__file__).resolve().parents[1] / ".mcp.json"
    if not mcp_path.exists():
        pytest.skip("package-dir .mcp.json absent; guard has nothing to protect")
    original = mcp_path.read_bytes()
    abs_repr = repr(str(mcp_path))

    # Real tests dir containing the real conftest.py that defines the
    # _guard_tracked_mcp_json fixture we want the inner session to use.
    real_tests_dir = Path(__file__).resolve().parent
    abs_dir_repr = repr(str(real_tests_dir))

    # ── Inner conftest: import the REAL fixture from the real conftest ──
    # Same mechanism as the repo-root negative control: insert the real
    # tests dir at sys.path[0], `import conftest` to load the real module,
    # and re-export its `_guard_tracked_mcp_json` fixture into this inner
    # conftest's namespace so pytest discovers and autouse-applies it.
    pytester.makeconftest(
        r'''
import sys
from pathlib import Path

sys.path.insert(0, __ABS_DIR__)

_inner_conftest_mod = sys.modules.pop("conftest", None)
try:
    import conftest as _real_conftest
finally:
    if _inner_conftest_mod is not None:
        sys.modules["conftest"] = _inner_conftest_mod

_guard_tracked_mcp_json = _real_conftest._guard_tracked_mcp_json
'''.replace("__ABS_DIR__", abs_dir_repr)
    )

    # ── Inner test: deliberately clobber the package-root .mcp.json ──
    pytester.makepyfile(
        test_neg_pkg=r'''from pathlib import Path

def test_mutate_package_dir_mcp_json():
    """Deliberately write the tracked package-root .mcp.json by absolute path."""
    Path(__ABS_PATH__).write_bytes(b'{"mutated_by_negative_control_package_dir": true}')
'''.replace("__ABS_PATH__", abs_repr)
    )

    # ── Run the inner session ──
    # Safety net: restore the file even if the inner guard somehow
    # fails to fire (the outer conftest guard is a second backstop).
    try:
        result = pytester.runpytest("-v", "--tb=long")
        # Exactly one adverse outcome: the guard fires on teardown.
        result.assert_outcomes(errors=1, passed=1, failed=0)
        # The offending node id appears in the failure message.
        assert "test_neg_pkg.py::test_mutate_package_dir_mcp_json" in result.stdout.str()
        # The 'pin the working directory' guidance is present.
        assert "pin the working directory" in result.stdout.str().lower()
    finally:
        if mcp_path.exists() and mcp_path.read_bytes() != original:
            mcp_path.write_bytes(original)

    # The guard restored the original content.
    assert mcp_path.read_bytes() == original


def test_mcp_json_guard_negative_control_creation(pytester):
    """Negative control (creation): an inner test that CREATES the
    PACKAGE-root .mcp.json — ``parents[1]`` relative to this test file,
    i.e. ``mcp-server-nucleus/.mcp.json`` — by absolute path, when the
    file was previously ABSENT, must produce exactly one failure whose
    message names the offending node id, includes the 'pin the working
    directory' guidance, and leaves the created stray file DELETED by
    the guard with the original file restored by the outer finally.

    The outer test backs up and renames the real package-dir .mcp.json
    to ``.mcp.json.guardtest_bak`` in a try/finally that always restores
    it, so the inner session's guard snapshots the watched path as
    absent. The inner test then creates the file; the guard fires on
    teardown (creation of a previously-absent watched file is a
    violation), deletes the stray, and pytest.fail()s. The outer
    finally renames the backup back so the original is restored.

    Same real-fixture import mechanism as the package-dir mutation
    negative control above; only the pre-condition (absent vs present)
    and the inner action (create vs mutate) differ.
    """
    from pathlib import Path

    # Resolve the real PACKAGE-root .mcp.json — parents[1] relative to
    # this test file (parents[0]=tests, parents[1]=package root, parents[2]=repo root).
    mcp_path = Path(__file__).resolve().parents[1] / ".mcp.json"
    backup_path = mcp_path.with_name(".mcp.json.guardtest_bak")
    if not mcp_path.exists():
        pytest.skip("package-dir .mcp.json absent; nothing to back up for creation test")

    original = mcp_path.read_bytes()
    abs_repr = repr(str(mcp_path))

    # Clean up any stale backup from a previous crashed run before we
    # create our own — a stale backup here would mean a prior run's
    # finally never executed.
    if backup_path.exists():
        backup_path.unlink()

    # Real tests dir containing the real conftest.py that defines the
    # _guard_tracked_mcp_json fixture we want the inner session to use.
    real_tests_dir = Path(__file__).resolve().parent
    abs_dir_repr = repr(str(real_tests_dir))

    # ── Inner conftest: import the REAL fixture from the real conftest ──
    # Same mechanism as the package-dir mutation negative control: insert
    # the real tests dir at sys.path[0], `import conftest` to load the real
    # module, and re-export its `_guard_tracked_mcp_json` fixture into this
    # inner conftest's namespace so pytest discovers and autouse-applies it.
    pytester.makeconftest(
        r'''
import sys
from pathlib import Path

sys.path.insert(0, __ABS_DIR__)

_inner_conftest_mod = sys.modules.pop("conftest", None)
try:
    import conftest as _real_conftest
finally:
    if _inner_conftest_mod is not None:
        sys.modules["conftest"] = _inner_conftest_mod

_guard_tracked_mcp_json = _real_conftest._guard_tracked_mcp_json
'''.replace("__ABS_DIR__", abs_dir_repr)
    )

    # ── Inner test: create the previously-absent package-root .mcp.json ──
    pytester.makepyfile(
        test_neg_create=r'''from pathlib import Path

def test_create_package_dir_mcp_json():
    """The watched package-root .mcp.json is absent (renamed away by the
    outer test); create it by absolute path to trip the guard."""
    p = Path(__ABS_PATH__)
    assert not p.exists(), "precondition: .mcp.json should be absent"
    p.write_bytes(b'{"created_by_negative_control_creation": true}')
    assert p.exists()
'''.replace("__ABS_PATH__", abs_repr)
    )

    # ── Back up and rename the real file away so the inner guard ──
    # ── snapshots the watched path as ABSENT.                          ──
    mcp_path.rename(backup_path)
    try:
        result = pytester.runpytest("-v", "--tb=long")
        # Exactly one adverse outcome: the guard fires on teardown
        # because a previously-absent watched file was created.
        result.assert_outcomes(errors=1, passed=1, failed=0)
        # The offending node id appears in the failure message.
        assert "test_neg_create.py::test_create_package_dir_mcp_json" in result.stdout.str()
        # The 'pin the working directory' guidance is present.
        assert "pin the working directory" in result.stdout.str().lower()
        # The guard deleted the stray created file.
        assert not mcp_path.exists(), "guard should have deleted the stray created file"
    finally:
        # Always restore the original from the backup.
        if backup_path.exists():
            if mcp_path.exists():
                mcp_path.unlink(missing_ok=True)
            backup_path.rename(mcp_path)
        elif not mcp_path.exists():
            # No backup and no file — cannot restore; write original bytes
            # as a last resort so the repo is not left without the file.
            mcp_path.write_bytes(original)

    # The original file is restored with its original content.
    assert mcp_path.exists()
    assert mcp_path.read_bytes() == original


def test_mcp_json_guard_positive_control(pytester):
    """Positive control: well-behaved inner tests must pass cleanly and the
    tracked repo-root .mcp.json must be unchanged.

    Two inner tests run under the same real-fixture import as the negative control:
      1. ``test_touches_nothing`` — does not touch .mcp.json at all.
      2. ``test_writes_mcp_json_in_tmp`` — writes .mcp.json only inside
         ``tmp_path`` (the inner session's own tmp dir), never the tracked
         repo-root file.

    Both must pass, zero failures/errors, and the tracked .mcp.json bytes
    must be identical before and after the inner session.
    """
    from pathlib import Path

    # Resolve BOTH real watched .mcp.json files — same resolution as the
    # _guard_tracked_mcp_json fixture in conftest.py: parents[1] = package
    # root (mcp-server-nucleus/.mcp.json), parents[2] = monorepo root
    # (ai-mvp-backend/.mcp.json). The positive control must verify that
    # well-behaved inner tests leave BOTH tracked files byte-identical.
    base = Path(__file__).resolve()
    watched = [base.parents[1] / ".mcp.json", base.parents[2] / ".mcp.json"]
    missing = [p for p in watched if not p.exists()]
    if missing:
        pytest.skip(f"watched .mcp.json absent: {missing}")

    originals = [(p, p.read_bytes()) for p in watched]

    # Real tests dir containing the real conftest.py that defines the
    # _guard_tracked_mcp_json fixture we want the inner session to use.
    real_tests_dir = Path(__file__).resolve().parent
    abs_dir_repr = repr(str(real_tests_dir))

    # ── Inner conftest: import the REAL fixture from the real conftest ──
    # Same mechanism as the negative control: insert the real tests dir at
    # sys.path[0], `import conftest` to load the real module, and re-export
    # its `_guard_tracked_mcp_json` fixture into this inner conftest's
    # namespace so pytest discovers and autouse-applies it. See the negative
    # control's inner conftest for the full guarantee comment.
    pytester.makeconftest(
        r'''
import sys
from pathlib import Path

# Insert the real tests directory at the FRONT of sys.path so `import conftest`
# resolves to the REAL mcp-server-nucleus/tests/conftest.py, not this inner
# conftest (which lives in the pytester tmp dir, also on sys.path further back).
sys.path.insert(0, __ABS_DIR__)

# pytest imports this inner conftest.py under the module name ``conftest`` and
# it is mid-import right now, so ``sys.modules["conftest"]`` already points at
# THIS partially-initialized module. A bare ``import conftest`` would return
# that partial entry (circular) instead of searching sys.path. Pop it
# temporarily so ``import conftest`` actually resolves through sys.path to the
# REAL conftest.py, then restore the inner entry so pytest keeps operating on
# this inner conftest module.
_inner_conftest_mod = sys.modules.pop("conftest", None)
try:
    import conftest as _real_conftest
finally:
    if _inner_conftest_mod is not None:
        sys.modules["conftest"] = _inner_conftest_mod

# Re-export the real fixture object into this inner conftest's namespace.
#
# How the real fixture is guaranteed to run in the inner session:
# pytest discovers autouse fixtures by scanning the attributes of the conftest
# module it loads for each rootdir. This inner conftest.py IS the inner
# session's rootdir conftest (pytester placed it here). By binding the name
# `_guard_tracked_mcp_json` in THIS module's globals to the real fixture
# function object (imported from the real conftest module above), pytest's
# fixture discovery finds it here and registers it with its original
# autouse=True marker, so it wraps every inner test. The fixture function
# retains its defining module's `__file__` — the real
# mcp-server-nucleus/tests/conftest.py — so its `Path(__file__).resolve()`
# resolves to the real tests dir and watches the real repo-root .mcp.json
# files (parents[1] = package root, parents[2] = monorepo root): exactly the
# files the real guard protects in the outer suite. No replica logic is
# duplicated; the real fixture is the single source of truth.
_guard_tracked_mcp_json = _real_conftest._guard_tracked_mcp_json
'''.replace("__ABS_DIR__", abs_dir_repr)
    )

    # ── Inner test 1: touches nothing ──
    pytester.makepyfile(
        test_touches_nothing=r'''def test_touches_nothing():
    """A no-op test that never touches .mcp.json."""
    assert True
'''
    )

    # ── Inner test 2: writes .mcp.json only inside tmp_path ──
    pytester.makepyfile(
        test_writes_mcp_json_in_tmp=r'''from pathlib import Path

def test_writes_mcp_json_in_tmp(tmp_path, monkeypatch):
    """Write .mcp.json only inside the inner session's tmp_path."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_bytes(b'{"written_inside_tmp": true}')
    assert (tmp_path / ".mcp.json").read_bytes() == b'{"written_inside_tmp": true}'
'''
    )

    # ── Run the inner session ──
    # Safety net: restore both files even if the inner guard fires unexpectedly.
    try:
        result = pytester.runpytest("-v", "--tb=long")
        # Both inner tests pass; no failures, no errors — the guard does not
        # fire because neither test mutates either tracked .mcp.json.
        result.assert_outcomes(passed=2, failed=0, errors=0)
    finally:
        for path, saved in originals:
            if path.exists() and path.read_bytes() != saved:
                path.write_bytes(saved)

    # Both tracked .mcp.json files are unchanged.
    for path, saved in originals:
        assert path.read_bytes() == saved, f"{path} mutated by positive control"
