"""Release gate: the built wheel must contain every module the source imports.

Regression cover for the 1.8.8 packaging bug (ADR-0043 W2, kill-list item 1/2):
the wheel shipped ``runtime/god_combos/`` with ``pulse_and_polish.py`` *absent*,
yet ``tools/engrams.py`` and ``runtime/stdio_server.py`` import it. The server
listed 12 tools and every ``tools/call`` failed with
``-32603 No module named '...god_combos.pulse_and_polish'``.

This test builds (or locates) the wheel and asserts:

  1. Every internal module that source code ``import``s and that physically
     exists in the source tree is also present inside the wheel.
     (Direct cover for the pulse_and_polish class of bug.)
  2. Belt-and-suspenders: the full set of source ``.py`` modules is a subset of
     the wheel's modules — nothing in src/ is dropped by the build backend.

Marked ``release`` so it is excluded from the default merge suite; the release
smoke gate and CI publish gate run ``pytest -m release`` against a fresh wheel.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tests.release._wheel_utils import (
    find_or_build_wheel,
    internal_import_targets,
    repo_root_from,
    source_modules,
    wheel_modules,
)


def withheld_modules(repo_root: Path) -> set[str]:
    """Dotted module names deliberately excluded from the wheel.

    Read from .withheld-modules.txt — the same file pyproject.toml excludes from
    and scripts/sovereign_surface_gate.py checks the artifact against. Hardcoding
    the set here would create a fourth copy of the answer, which is exactly the
    drift that let the old SOVEREIGN list and the packaging config disagree for
    33 releases.

    An absent or empty list means nothing is exempt, so this gate stays strict by
    default rather than degrading quietly.
    """
    f = repo_root / ".withheld-modules.txt"
    if not f.is_file():
        return set()
    out: set[str] = set()
    for line in f.read_text().splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        rel = entry[len("src/"):] if entry.startswith("src/") else entry
        out.add(rel.rstrip("/").removesuffix(".py").replace("/", "."))
    return out


def _is_withheld(mod: str, withheld: set[str]) -> bool:
    """A package entry on the list covers everything beneath it."""
    return any(mod == w or mod.startswith(w + ".") for w in withheld)


@pytest.fixture(scope="module")
def built_wheel() -> Path:
    repo_root = repo_root_from(__file__)
    with tempfile.TemporaryDirectory(prefix="nucleus_wheel_") as tmp:
        wheel, reason = find_or_build_wheel(repo_root, Path(tmp))
        if wheel is None:
            pytest.skip(reason)
        # Keep the wheel alive for the module's lifetime by copying it out of
        # the TemporaryDirectory context before it is cleaned up.
        import shutil

        persisted = Path(tempfile.mkdtemp(prefix="nucleus_wheel_keep_")) / wheel.name
        shutil.copy2(wheel, persisted)
        print(f"\n[wheel-completeness] using wheel: {reason} -> {persisted.name}")
        return persisted


@pytest.mark.release
def test_import_referenced_modules_present_in_wheel(built_wheel: Path) -> None:
    """Every import-referenced internal module that exists in src is in the wheel."""
    repo_root = repo_root_from(__file__)
    src_root = repo_root / "src"

    src_mods = source_modules(src_root)
    whl_mods = wheel_modules(built_wheel)
    targets = internal_import_targets(src_root)

    # Only enforce import targets that correspond to a REAL source module.
    # (``from a.b import name`` yields candidate ``a.b.name`` which may be an
    # attribute rather than a submodule — those are filtered out here.)
    referenced_real_modules = {t for t in targets if t in src_mods}

    withheld = withheld_modules(repo_root)
    # Deliberate exclusions are not the pulse_and_polish bug. Their importers are
    # ImportError-guarded, asserted by tests/test_packaging_excludes.py.
    missing = sorted(m for m in (referenced_real_modules - whl_mods)
                     if not _is_withheld(m, withheld))

    # Guardrail: the walk must actually resolve the historically-broken module,
    # otherwise a silent parser regression could make this test vacuously pass.
    sentinel = "mcp_server_nucleus.runtime.god_combos.pulse_and_polish"
    assert sentinel in referenced_real_modules, (
        "import walker failed to resolve the pulse_and_polish reference — the "
        "AST walk is not catching the class of bug this gate exists for"
    )

    assert not missing, (
        "Wheel is missing import-referenced modules (the pulse_and_polish class "
        f"of packaging bug). {len(missing)} module(s) imported by source but "
        f"absent from the built wheel:\n  " + "\n  ".join(missing)
    )


@pytest.mark.release
def test_all_source_modules_present_in_wheel(built_wheel: Path) -> None:
    """No source module is silently dropped by the build backend."""
    repo_root = repo_root_from(__file__)
    src_root = repo_root / "src"

    src_mods = source_modules(src_root)
    whl_mods = wheel_modules(built_wheel)

    assert src_mods, "no source modules discovered — src layout changed?"

    withheld = withheld_modules(repo_root)
    src_mods = {m for m in src_mods if not _is_withheld(m, withheld)}
    dropped = sorted(src_mods - whl_mods)
    assert not dropped, (
        f"{len(dropped)} source module(s) present in src/ but absent from the "
        f"built wheel:\n  " + "\n  ".join(dropped)
    )
