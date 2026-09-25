"""Shared helpers for release-hygiene wheel checks.

These utilities let a test walk the *source* import graph and compare it
against the *built wheel* contents. The class of bug this catches is the one
that shipped in the 1.8.8 wheel: a module physically present in the source
tree and referenced by ``import`` statements, but silently dropped from the
built wheel by the packaging backend — so the server lists tools that all
raise ``No module named ...`` at call time.

Nothing here imports the package under test; everything works off the source
files on disk and the zip contents of the wheel, so it runs in a bare venv
that has only the wheel installed.
"""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Top-level packages the wheel is expected to ship (mirrors
# [tool.hatch.build.targets.wheel].packages in pyproject.toml).
INTERNAL_TOP_LEVEL = ("mcp_server_nucleus", "nucleus_wedge")


def requires_python_floor(pyproject: Path) -> tuple[int, int]:
    """Parse the ``requires-python`` floor from pyproject.toml -> (major, minor)."""
    text = pyproject.read_text(encoding="utf-8")
    m = re.search(r'^requires-python\s*=\s*"[^"]*?(\d+)\.(\d+)', text, re.MULTILINE)
    if not m:
        raise RuntimeError("could not parse requires-python from pyproject.toml")
    return int(m.group(1)), int(m.group(2))


def oldest_supported_python(floor: tuple[int, int]) -> str | None:
    """Return the path to the oldest ``python3.X`` on PATH that is >= floor."""
    major, minor = floor
    for m in range(minor, 21):
        exe = shutil.which(f"python{major}.{m}")
        if exe:
            return exe
    return None


def repo_root_from(test_file: str) -> Path:
    """Return the mcp-server-nucleus project root given a test file path."""
    # tests/release/<file>.py -> project root is two parents up.
    return Path(test_file).resolve().parents[2]


def _module_name(rel_posix: str) -> str:
    """Convert a package-relative posix path to a dotted module name."""
    assert rel_posix.endswith(".py")
    dotted = rel_posix[:-3].replace("/", ".")
    if dotted.endswith(".__init__"):
        dotted = dotted[: -len(".__init__")]
    return dotted


def source_modules(src_root: Path) -> set[str]:
    """Every dotted module name physically present under the internal packages."""
    mods: set[str] = set()
    for top in INTERNAL_TOP_LEVEL:
        base = src_root / top
        if not base.is_dir():
            continue
        for py in base.rglob("*.py"):
            rel = py.relative_to(src_root).as_posix()
            mods.add(_module_name(rel))
    return mods


def wheel_modules(wheel_path: Path) -> set[str]:
    """Every dotted module name shipped inside the wheel's internal packages."""
    mods: set[str] = set()
    with zipfile.ZipFile(wheel_path) as zf:
        for name in zf.namelist():
            if not name.endswith(".py"):
                continue
            top = name.split("/", 1)[0]
            if top in INTERNAL_TOP_LEVEL:
                mods.add(_module_name(name))
    return mods


def _package_for(rel_posix: str) -> str:
    """Dotted package that owns a source file (its containing directory)."""
    dotted = _module_name(rel_posix)
    # For a plain module a.b.c the owning package is a.b; for a package
    # __init__ (already collapsed to a.b) the owning package is a.b itself.
    parts = dotted.split(".")
    # If the file was a/__init__.py it collapses to "a" and is its own package.
    # Distinguish by checking the original path.
    if rel_posix.endswith("/__init__.py") or rel_posix == "__init__.py":
        return dotted
    return ".".join(parts[:-1])


def _resolve_relative(package: str, level: int, module: str | None) -> str | None:
    """Resolve a ``from ... import`` relative reference to an absolute base."""
    parts = package.split(".") if package else []
    # level 1 => current package; level 2 => parent; etc.
    if level - 1 > len(parts):
        return None
    base_parts = parts[: len(parts) - (level - 1)]
    base = ".".join(base_parts)
    if module:
        base = f"{base}.{module}" if base else module
    return base or None


def internal_import_targets(src_root: Path) -> set[str]:
    """Walk every source file's AST and collect internal import targets.

    Returns dotted module names that the code imports and that belong to one of
    the internal top-level packages. Both module-level and function-scoped
    imports are captured, absolute and relative, plus string-literal dynamic
    imports via ``import_module("...")``.

    A ``from a.b import c`` reference contributes both ``a.b`` and the candidate
    submodule ``a.b.c`` (the caller filters candidates down to those that are
    real source modules, so attribute imports are harmless).
    """
    targets: set[str] = set()

    def _is_internal(dotted: str) -> bool:
        top = dotted.split(".", 1)[0]
        return top in INTERNAL_TOP_LEVEL

    for top in INTERNAL_TOP_LEVEL:
        base = src_root / top
        if not base.is_dir():
            continue
        for py in base.rglob("*.py"):
            rel = py.relative_to(src_root).as_posix()
            pkg = _package_for(rel)
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_internal(alias.name):
                            targets.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.level > 0:
                        base_mod = _resolve_relative(pkg, node.level, node.module)
                        if not base_mod or not _is_internal(base_mod):
                            continue
                        targets.add(base_mod)
                        for alias in node.names:
                            if alias.name != "*":
                                targets.add(f"{base_mod}.{alias.name}")
                    elif node.module and _is_internal(node.module):
                        targets.add(node.module)
                        for alias in node.names:
                            if alias.name != "*":
                                targets.add(f"{node.module}.{alias.name}")
                elif isinstance(node, ast.Call):
                    # importlib.import_module("mcp_server_nucleus.x.y") /
                    # __import__("mcp_server_nucleus.x.y") with a literal arg.
                    fn = node.func
                    fn_name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                    if fn_name in ("import_module", "__import__") and node.args:
                        arg0 = node.args[0]
                        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                            if _is_internal(arg0.value):
                                targets.add(arg0.value)
    return targets


def _newest_source_mtime(repo_root: Path) -> float | None:
    """Newest mtime across packaged Python sources, or None if none found.

    Used to reject a pre-built wheel that predates the code it should contain.
    Scans only the packaged trees under src/ — build outputs, caches and venvs
    are irrelevant and would make every wheel look stale.
    """
    newest: float | None = None
    src = repo_root / "src"
    if not src.is_dir():
        return None
    for p in src.rglob("*.py"):
        if any(part in {"__pycache__", ".venv", "build", "dist"} for part in p.parts):
            continue
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if newest is None or m > newest:
            newest = m
    return newest


def find_or_build_wheel(repo_root: Path, out_dir: Path) -> tuple[Path | None, str]:
    """Locate a pre-built wheel, or build one.

    Resolution order:
      1. ``$NUCLEUS_WHEEL`` if it points at an existing ``.whl``.
      2. Newest ``*.whl`` under ``<repo_root>/dist``.
      3. Build one with ``python -m build --wheel --no-isolation`` using the
         first build-capable interpreter found (current, then common 3.1x).

    Returns ``(path, reason)``. ``path`` is ``None`` when no wheel could be
    obtained; ``reason`` explains why (for a clear pytest skip message).
    """
    env_wheel = os.environ.get("NUCLEUS_WHEEL")
    if env_wheel:
        p = Path(env_wheel)
        if p.is_file() and p.suffix == ".whl":
            return p, f"NUCLEUS_WHEEL={p}"

    dist = repo_root / "dist"
    if dist.is_dir():
        whls = sorted(dist.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if whls:
            # STALENESS GUARD. A pre-built wheel older than the sources it is
            # supposed to contain must never be graded as current. Without this,
            # `dist/nucleus_mcp-1.16.0-py3-none-any.whl` (built 2026-07-24) was
            # preferred over a fresh build for a week, so these tests reported
            # `liveness`, `prove`, `receipt`, `growth_registry` "absent from the
            # built wheel" when a wheel built that day contained all four. The
            # packaging config was never broken; the artifact under test was
            # simply a week old.
            #
            # This is the same defect class the product itself guards against
            # ("coverage database older than changed files" -> INSUFFICIENT).
            # Fall through to a fresh build rather than failing, so a stale
            # artifact degrades to a slower correct answer, not a false red.
            # `None` means the freshness of this wheel could not be
            # ESTABLISHED — no packaged source was found to compare against. It
            # used to be read as "then it is fine" and the wheel was handed back
            # unchecked, which is the third state coerced to green in the one
            # place whose entire job is to stop a stale artifact being graded as
            # current. Unknown now falls through to a rebuild: slower and
            # correct beats fast and unverified.
            newest_src = _newest_source_mtime(repo_root)
            wheel_mtime = whls[0].stat().st_mtime
            if newest_src is not None and wheel_mtime >= newest_src:
                return whls[0], f"dist/{whls[0].name}"

    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = [sys.executable, "python3.10", "python3.11", "python3.12", "python3", "python3.13"]
    # `--no-isolation` is tried FIRST because it is fast, but it requires the
    # build backend (hatchling) to already be importable in that interpreter.
    # On a machine where it is not, every candidate failed and these tests
    # SKIPPED — a release gate that silently does not run protects nothing, and
    # a skip reads as green in any summary line. Retry each interpreter WITH
    # isolation, which provisions hatchling itself; that is the mode a real
    # `python -m build` uses and it succeeds where the fast path cannot.
    modes = [
        ("--no-isolation", ["--no-isolation"]),
        ("isolated", []),
    ]
    last_err = ""
    for interp in candidates:
        for mode_name, mode_args in modes:
            try:
                proc = subprocess.run(
                    [interp, "-m", "build", "--wheel", *mode_args, "-o", str(out_dir)],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                last_err = f"{interp} ({mode_name}): {exc}"
                continue
            if proc.returncode == 0:
                whls = sorted(
                    out_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True
                )
                if whls:
                    return whls[0], f"built via {interp} -m build ({mode_name})"
                last_err = f"{interp} ({mode_name}): build exited 0 but produced no wheel"
            else:
                tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["build failed"]
                last_err = f"{interp} ({mode_name}): {tail[0]}"
    return None, (
        "no wheel available: set NUCLEUS_WHEEL, drop one in dist/, or install "
        f"the 'build' module in a supported interpreter (last error: {last_err})"
    )


# ── Smoke-venv cache ───────────────────────────────────────────────────────
# The first-run gate builds a venv and installs the wheel. That takes minutes,
# and conftest caps every test at 30s, so the gate errored in its fixture every
# run and nobody noticed it was dark. Cache the venv so only the first run pays.
#
# The key is a hash of the wheel's CONTENT, never its path or version. Keying on
# either would reuse a venv built from an older build of the same version — and
# that is not hypothetical: dist/ routinely holds a wheel from an earlier commit
# and find_or_build_wheel prefers the newest file in dist/, so a path-keyed cache
# would smoke-test code that is not the code under test.


def venv_cache_key(wheel: Path) -> str:
    """Stable 32-char key derived from the wheel's bytes."""
    import hashlib

    h = hashlib.sha256()
    with open(wheel, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


def venv_cache_root() -> Path:
    """Where cached smoke venvs live. Outside the repo on purpose — a venv
    inside it would show up in git status and in the export archive.
    Override with $NUCLEUS_SMOKE_VENV_CACHE."""
    override = os.environ.get("NUCLEUS_SMOKE_VENV_CACHE", "").strip()
    if override:
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME", "").strip()
    return (Path(base) if base else Path.home() / ".cache") / "nucleus-smoke-venv"


def cached_venv_for(wheel: Path) -> Path:
    """Path this wheel's venv occupies, whether or not it exists yet."""
    return venv_cache_root() / venv_cache_key(wheel)


#: Written into a cached venv only after its wheel install SUCCEEDS. A venv is
#: NOT relocatable — bin/ scripts bake the interpreter's absolute path into their
#: shebang — so the usual build-elsewhere-then-rename trick produces a directory
#: whose entrypoint exists and whose interpreter does not. Measured: bin/nucleus
#: present on disk, running it raised FileNotFoundError for that same path.
#: So the venv is built in place and a marker records completion instead.
VENV_COMPLETE_MARKER = ".nucleus-smoke-complete"


def cached_venv_is_usable(venv_dir: Path) -> bool:
    """True only for a cache entry that finished installing.

    Both conditions matter: the marker proves the install completed, and the
    entrypoint proves the directory was not partially removed afterwards.
    """
    return (venv_dir / VENV_COMPLETE_MARKER).exists() and (venv_dir / "bin" / "nucleus").exists()
