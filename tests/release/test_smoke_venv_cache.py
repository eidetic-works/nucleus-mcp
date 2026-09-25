"""The first-run smoke gate must survive without anyone remembering an env var.

tests/release/test_stranger_first_run.py is the release gate for a stranger's
very first `pip install nucleus-mcp && nucleus init`. It had NEVER executed on
this machine: its module fixture builds a fresh venv and installs the wheel,
which takes minutes, while conftest.py:41 caps every test at 30 seconds. All
five beats errored in the fixture, every run, and nothing recorded that the gate
was dark. Given a pre-built venv via $NUCLEUS_SMOKE_VENV it passes 5/5 in 34s —
so the gate works and only its setup was impossible.

Two fixes, tested here:
  * the module raises its own timeout, because a real install cannot fit in 30s;
  * the venv is cached on disk and reused across runs, so only the first run
    pays for it and no human has to set anything.

THE CONTROL THAT MATTERS is the stale-wheel one. The cache key is derived from
the wheel's CONTENT, so rebuilding the package produces a different key and a
different venv. Keying on a path or a version string instead would silently
smoke-test yesterday's build — which nearly happened today: dist/ held a wheel
from 07:37 built at an earlier commit, and the fixture's own resolution order
prefers the newest wheel in dist/, so the gate would have reported on code that
was not the code under test.
"""
from __future__ import annotations

import pytest

from tests.release import _wheel_utils as wu


def _write_wheel(path, payload: bytes):
    import zipfile

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mcp_server_nucleus/__init__.py", payload)
    return path


# ── the cache key ──────────────────────────────────────────────────────────


def test_cache_key_is_stable_for_identical_wheels(tmp_path):
    a = _write_wheel(tmp_path / "a.whl", b"same content")
    b = _write_wheel(tmp_path / "b.whl", b"same content")
    assert wu.venv_cache_key(a) == wu.venv_cache_key(b)


def test_cache_key_changes_when_the_wheel_changes(tmp_path):
    """THE CONTROL: a rebuilt wheel must not reuse the old venv."""
    a = _write_wheel(tmp_path / "a.whl", b"version one")
    b = _write_wheel(tmp_path / "b.whl", b"version two")
    assert wu.venv_cache_key(a) != wu.venv_cache_key(b)


def test_cache_key_ignores_the_filename(tmp_path):
    """Two builds of the same content land at the same key even when the file
    is named differently — the key is the content, not the path."""
    a = _write_wheel(tmp_path / "nucleus_mcp-1.0.0-py3-none-any.whl", b"x")
    b = _write_wheel(tmp_path / "totally-different-name.whl", b"x")
    assert wu.venv_cache_key(a) == wu.venv_cache_key(b)


def test_cache_key_is_a_safe_directory_name(tmp_path):
    key = wu.venv_cache_key(_write_wheel(tmp_path / "a.whl", b"x"))
    assert key and key.isalnum() and len(key) <= 32


# ── the cache directory ────────────────────────────────────────────────────


def test_cache_root_is_overridable(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_SMOKE_VENV_CACHE", str(tmp_path / "somewhere"))
    assert str(tmp_path / "somewhere") in str(wu.venv_cache_root())


def test_cache_root_defaults_outside_the_repo(monkeypatch):
    """A venv inside the repo would land in git status and in the archive."""
    monkeypatch.delenv("NUCLEUS_SMOKE_VENV_CACHE", raising=False)
    root = wu.venv_cache_root()
    assert "nucleus-renaissance" not in str(root)


# ── the timeout override ───────────────────────────────────────────────────


def test_first_run_module_overrides_the_30s_cap():
    """conftest applies timeout(30) to any test lacking its own. A real wheel
    install cannot fit, so this module must carry its own larger mark — without
    it the gate is dark again whatever the cache does."""
    from tests.release import test_stranger_first_run as mod

    marks = getattr(mod, "pytestmark", [])
    marks = marks if isinstance(marks, list) else [marks]
    timeouts = [m for m in marks if getattr(m, "name", "") == "timeout"]
    assert timeouts, "test_stranger_first_run has no module-level timeout mark"
    assert timeouts[0].args[0] >= 600, (
        f"timeout {timeouts[0].args[0]}s is too small for a venv + wheel install"
    )


# ── the completion marker ──────────────────────────────────────────────────
# A venv is not relocatable: bin/ scripts bake the interpreter's absolute path
# into their shebang. Building elsewhere and renaming into the cache produced a
# directory whose bin/nucleus EXISTED and whose interpreter did not — the cold
# run failed with FileNotFoundError naming the very path `ls` had just shown.
# Hence: build in place, record completion with a marker.


def test_unmarked_venv_is_not_reused(tmp_path):
    """NEGATIVE CONTROL: a killed run leaves a directory that looks plausible.
    It must be rebuilt, not trusted."""
    v = tmp_path / "venv"
    (v / "bin").mkdir(parents=True)
    (v / "bin" / "nucleus").write_text("#!/bin/sh\n", encoding="utf-8")
    assert wu.cached_venv_is_usable(v) is False


def test_marked_but_gutted_venv_is_not_reused(tmp_path):
    """The marker alone is not enough — the entrypoint must still be there."""
    v = tmp_path / "venv"
    v.mkdir()
    (v / wu.VENV_COMPLETE_MARKER).write_text("ok", encoding="utf-8")
    assert wu.cached_venv_is_usable(v) is False


def test_complete_venv_is_reused(tmp_path):
    """POSITIVE CONTROL: the whole point of the cache."""
    v = tmp_path / "venv"
    (v / "bin").mkdir(parents=True)
    (v / "bin" / "nucleus").write_text("#!/bin/sh\n", encoding="utf-8")
    (v / wu.VENV_COMPLETE_MARKER).write_text("ok", encoding="utf-8")
    assert wu.cached_venv_is_usable(v) is True


# ── the staleness guard ────────────────────────────────────────────────────
# find_or_build_wheel prefers the newest *.whl in <repo_root>/dist. A guard
# already rejects one older than the sources it should contain, and it works:
# measured 2026-09-20, dist/ held a wheel built 07:37 while the newest packaged
# source was 23:17, and the guard rebuilt rather than grading the old artifact.
#
# What it did NOT handle is not knowing. `_newest_source_mtime` returns None
# when it cannot find any packaged source, and the guard read
#
#     if newest_src is None or wheel_mtime >= newest_src:  ->  use the wheel
#
# so "I could not establish freshness" was treated as "it is fresh". That is the
# third state coerced to green, in the one place whose entire job is to stop a
# stale artifact being graded as current. Unknown must fall through to a rebuild:
# slower and correct beats fast and unverified.


def _wheel_at(dist_dir, mtime):
    import os

    dist_dir.mkdir(parents=True, exist_ok=True)
    w = _write_wheel(dist_dir / "pkg-1.0.0-py3-none-any.whl", b"x")
    os.utime(w, (mtime, mtime))
    return w


def _src_at(root, mtime):
    import os

    src = root / "src" / "pkg"
    src.mkdir(parents=True, exist_ok=True)
    f = src / "__init__.py"
    f.write_text("x = 1\n", encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def test_source_mtime_is_none_when_there_is_no_packaged_source(tmp_path):
    (tmp_path / "dist").mkdir()
    assert wu._newest_source_mtime(tmp_path) is None


def test_prebuilt_wheel_is_not_trusted_when_freshness_is_unknowable(tmp_path, monkeypatch):
    """NEGATIVE CONTROL: no src/ to compare against. The guard cannot establish
    the wheel is current, so it must NOT hand it back as if it had."""
    monkeypatch.delenv("NUCLEUS_WHEEL", raising=False)
    _wheel_at(tmp_path / "dist", 1_000_000)
    path, reason = wu.find_or_build_wheel(tmp_path, tmp_path / "out")
    assert "dist/pkg-1.0.0-py3-none-any.whl" not in (reason or ""), (
        f"unverifiable prebuilt wheel was graded as current: {reason}"
    )


def test_stale_wheel_is_rejected(tmp_path, monkeypatch):
    """NEGATIVE CONTROL: wheel older than the source it should contain."""
    monkeypatch.delenv("NUCLEUS_WHEEL", raising=False)
    _wheel_at(tmp_path / "dist", 1_000_000)
    _src_at(tmp_path, 2_000_000)
    _, reason = wu.find_or_build_wheel(tmp_path, tmp_path / "out")
    assert "dist/pkg-1.0.0" not in (reason or ""), f"stale wheel accepted: {reason}"


def test_fresh_wheel_is_reused(tmp_path, monkeypatch):
    """POSITIVE CONTROL: a wheel newer than every packaged source is the whole
    reason the fast path exists. Without this the fix is just 'never reuse'."""
    monkeypatch.delenv("NUCLEUS_WHEEL", raising=False)
    _src_at(tmp_path, 1_000_000)
    _wheel_at(tmp_path / "dist", 2_000_000)
    path, reason = wu.find_or_build_wheel(tmp_path, tmp_path / "out")
    assert path is not None and "dist/pkg-1.0.0" in reason, (
        f"fresh wheel was not reused: {reason}"
    )
