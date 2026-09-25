"""The withhold list, the packaging config and the gate must agree.

For 33 releases they did not. `scripts/validate_public_surface.sh` declared 21
paths SOVEREIGN; `pyproject.toml` had no exclusions at all; eight of those paths
shipped in every wheel. Neither side was lying — the gate checked the
`git archive` mirror, `export-ignore` governs only that archive, and hatchling
builds from the VCS tree. Two mechanisms answering one question, never compared.

So the rule is not "exclude these files", it is "one list, and anything that
reads it must match it". These tests fail when the copies drift.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
LIST = PKG_ROOT / ".withheld-modules.txt"
PYPROJECT = PKG_ROOT / "pyproject.toml"


def withheld_list() -> list[str]:
    return [ln.strip() for ln in LIST.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def targets() -> dict:
    return tomllib.loads(PYPROJECT.read_text())["tool"]["hatch"]["build"]["targets"]


def test_the_list_exists_and_is_not_empty():
    """An empty list would make every downstream check vacuously pass."""
    assert LIST.is_file(), f"{LIST.name} is the single source; without it the gate is blind"
    assert withheld_list(), "an empty withhold list makes the gate uninformative"


@pytest.mark.parametrize("target", ["wheel", "sdist"])
def test_packaging_excludes_exactly_the_withheld_list(target):
    """Both build targets, because only-include takes src/ wholesale in the sdist."""
    declared = set(targets()[target].get("exclude", []))
    expected = set(withheld_list())
    missing = expected - declared
    extra = declared - expected
    assert not missing, (
        f"{target} target does not exclude {sorted(missing)} — they are in "
        f"{LIST.name} and would ship. This is the exact drift that let eight "
        "withheld modules reach PyPI across 33 releases."
    )
    assert not extra, (
        f"{target} target excludes {sorted(extra)}, which is not in {LIST.name}. "
        "Either add it to the list or stop excluding it; a second copy of the "
        "answer is how the two got out of step."
    )


def test_every_withheld_path_exists_in_the_source_tree():
    """A stale entry is how the old gate ended up listing tools/archive.py, a
    file that does not exist and is not tracked — checked forever, found never."""
    for entry in withheld_list():
        p = PKG_ROOT / entry
        assert p.exists(), (
            f"{entry} is on the withhold list but is not in the tree. A list "
            "entry that matches nothing is indistinguishable from a working one."
        )


def test_withheld_cli_verbs_are_guarded():
    """Excluding a module whose import is bare turns a missing feature into a
    traceback. Each of these verbs must catch ImportError and say so."""
    cli = (PKG_ROOT / "src" / "mcp_server_nucleus" / "cli.py").read_text()
    for verb in ("siphon", "distill", "replay", "validate"):
        if not (PKG_ROOT / f"src/mcp_server_nucleus/{verb}.py").exists():
            continue
        assert f"_withheld('{verb}')" in cli, (
            f"cli.py does not guard the '{verb}' import. With the module "
            "excluded, this build raises instead of reporting."
        )
