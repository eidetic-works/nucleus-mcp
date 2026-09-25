"""No dependency may be declared twice in pyproject.toml.

Shipped defect (1.16.6): `cryptography` was declared with two different floors --
an old incidental `>=46.0.6` and a `>=48.0.1` added by CVE remediation (497d5139,
"cryptography 46->49.0.0 (1 CVE)"). Both reached PKG-INFO as separate
Requires-Dist lines. pip intersects them, so the effective floor was the higher
one, and any consumer already pinning cryptography below it got
ResolutionImpossible rather than a readable conflict.

Why no existing check caught it: a clean venv resolves 42 Requires-Dist lines
happily, because nothing constrains the package yet. The defect is only
observable against an environment that ALREADY pins the duplicated dependency --
which is what a real consumer is and what a fresh test venv never is. The
instrument that found it was a downstream build, not a test.

This test is the cheap standing replacement: a duplicate is a static property of
the file and needs no environment at all to detect.
"""
import re
import tomllib
from collections import Counter
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _name(spec: str) -> str:
    """PEP 508 spec -> normalised distribution name."""
    return re.split(r"[<>=!~\[;( ]", spec.strip(), maxsplit=1)[0].lower().replace("_", "-")


def _all_dependency_groups():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = data.get("project", {})
    yield "dependencies", project.get("dependencies", [])
    for extra, specs in (project.get("optional-dependencies") or {}).items():
        yield f"optional-dependencies.{extra}", specs


def test_no_duplicate_dependency_declarations():
    problems = []
    for group, specs in _all_dependency_groups():
        counts = Counter(_name(s) for s in specs)
        for name, n in counts.items():
            if n > 1:
                dupes = [s for s in specs if _name(s) == name]
                problems.append(f"{group}: {name} declared {n}x -> {dupes}")
    assert not problems, "duplicate dependency declarations:\n  " + "\n  ".join(problems)


def test_detector_fires_on_a_planted_duplicate():
    """Positive control -- the check must be able to emit non-zero.

    A duplicate-detector that has never seen a duplicate is indistinguishable
    from one that cannot see them.
    """
    specs = ["alpha>=1.0", "beta", "alpha>=2.0"]
    counts = Counter(_name(s) for s in specs)
    assert counts["alpha"] == 2


def test_cryptography_floor_is_the_cve_floor():
    """The 1.16.6 regression specifically: the CVE floor must survive.

    497d5139 moved cryptography off the 46.x line for a known CVE. If a future
    edit reintroduces a lower floor, resolving the duplicate by keeping the
    LOWER one would silently undo that remediation.
    """
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    specs = [s for s in data["project"]["dependencies"] if _name(s) == "cryptography"]
    assert len(specs) == 1, f"cryptography declared {len(specs)}x: {specs}"
    m = re.search(r">=\s*(\d+)", specs[0])
    assert m, f"cryptography has no lower bound: {specs[0]!r}"
    assert int(m.group(1)) >= 48, (
        f"cryptography floor {specs[0]!r} is below the CVE remediation floor (>=48)"
    )


# ── The metadata PyPI will reject (no check existed for this at all) ─────────
#
# 1.16.5->1.16.6 was unpublishable for six weeks because project.urls carried
# `Contact = "mailto:hello@nucleusos.dev"`. PyPI answers 400:
#     'mailto:hello@nucleusos.dev' is not a valid url
# Nothing in the repo asserted this property, and the only instrument that could
# observe it was an upload attempt -- which nobody made, because nobody released.
# You cannot add a positive control to a process that is never run; you can add
# a static assertion about the artifact that process consumes.

_ALLOWED_URL_SCHEMES = ("http://", "https://")


def test_project_urls_are_http_only():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    urls = (data.get("project", {}).get("urls") or {})
    bad = {
        label: value
        for label, value in urls.items()
        if not value.lower().startswith(_ALLOWED_URL_SCHEMES)
    }
    assert not bad, (
        f"PyPI rejects non-http(s) project.urls with 400 'is not a valid url': {bad}"
    )


def test_url_check_fires_on_a_planted_mailto():
    """Positive control: the exact value that blocked 1.16.6 must be rejected."""
    planted = "mailto:" + "hello@nucleusos.dev"
    assert not planted.lower().startswith(_ALLOWED_URL_SCHEMES)
