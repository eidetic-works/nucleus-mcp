"""The TypeScript SDK must be buildable and publishable (CS-3).

`sdk/typescript/` shipped `src/`, a complete `tsconfig.json` and a README telling
users to `npm install @nucleus/relay-sdk` — with no `package.json`. That name
could not exist, there was no build script, and nothing declared the toolchain
or the Node type definitions the source needs. Its Python sibling has had a
`pyproject.toml` the whole time.

These are static checks. The real proof is that the thing builds, and that was
done once by hand with the declared toolchain rather than asserted:

    npm install                 # ok
    npm run build               # exit 0, emits dist/*.js + *.d.ts
    npm run typecheck           # exit 0
    node -e "require('./dist')" # RelayClient present
    npm pack --dry-run          # 13.5 kB: dist/, README.md, package.json

CI here is Python-only, so these tests guard the packaging metadata rather than
re-run that. They are written to catch the ways it silently stops being true:
the entry points drifting from what tsconfig emits, or the Node types being
dropped from a source that imports Node builtins.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "sdk" / "typescript"

pytestmark = pytest.mark.skipif(not SDK.is_dir(), reason="TS SDK not in this export")


@pytest.fixture(scope="module")
def pkg():
    path = SDK / "package.json"
    assert path.exists(), (
        "sdk/typescript has no package.json, so the package name its README "
        "tells users to install cannot exist and there is no build command"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tsconfig():
    raw = (SDK / "tsconfig.json").read_text(encoding="utf-8")
    # tsconfig allows // comments; strip them before parsing.
    return json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))


def test_the_package_name_matches_what_the_readme_tells_people_to_install(pkg):
    readme = (SDK / "README.md").read_text(encoding="utf-8")
    assert pkg["name"] in readme, (
        f"README does not mention {pkg['name']}; one of the two is wrong and a "
        "user will follow the README"
    )


def test_the_entry_points_match_what_the_compiler_emits(pkg, tsconfig):
    """main/types pointing outside outDir publishes an empty package."""
    out = tsconfig["compilerOptions"]["outDir"].lstrip("./").rstrip("/")
    for field in ("main", "types"):
        assert out in pkg[field], (
            f"package.json {field}={pkg[field]!r} does not point into tsconfig's "
            f"outDir ({out}); npm would publish files that were never built"
        )


def test_declaration_output_is_on_since_the_package_advertises_types(pkg, tsconfig):
    assert tsconfig["compilerOptions"].get("declaration") is True, (
        "package.json declares a types entry but tsconfig does not emit "
        "declarations, so the .d.ts it points at is never produced"
    )


def test_there_is_a_build_script(pkg):
    scripts = pkg.get("scripts", {})
    assert "build" in scripts, "no build script; `npm run build` does nothing"
    assert "tsc" in scripts["build"]


def test_the_node_type_definitions_are_declared(pkg):
    """The source imports node: builtins; without these it will not typecheck."""
    source = (SDK / "src" / "index.ts").read_text(encoding="utf-8")
    if "node:" not in source and "process" not in source:
        pytest.skip("source uses no Node builtins")
    dev = pkg.get("devDependencies", {})
    assert "@types/node" in dev, (
        "src/index.ts imports Node builtins but @types/node is not declared, so "
        "a clean `npm install && npm run build` fails on a fresh machine"
    )


def test_the_typescript_compiler_is_declared(pkg):
    assert "typescript" in pkg.get("devDependencies", {}), (
        "the build script runs tsc but nothing declares which TypeScript to use"
    )


def test_the_published_file_list_ships_the_build_not_the_source(pkg):
    files = pkg.get("files")
    assert files, "no files field; npm would publish the whole directory"
    assert any("dist" in f for f in files), "the build output is not published"
    assert not any(f.strip("./") == "src" for f in files), (
        "src/ is published instead of, or as well as, the build"
    )


def test_the_sdk_declares_no_runtime_dependencies(pkg):
    """The README promises this; it is the reason the SDK is safe to embed."""
    readme = (SDK / "README.md").read_text(encoding="utf-8")
    if "Zero runtime deps" not in readme:
        pytest.skip("README no longer promises zero runtime dependencies")
    assert not pkg.get("dependencies"), (
        f"README promises zero runtime deps but package.json declares "
        f"{list(pkg.get('dependencies', {}))}"
    )


def test_both_sdks_agree_on_version_and_licence(pkg):
    """They implement one protocol; a version skew between them is a trap."""
    pyproject = ROOT / "sdk" / "python" / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("python SDK not in this export")
    text = pyproject.read_text(encoding="utf-8")
    py_version = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert py_version, "could not read the python SDK version"
    assert pkg["version"] == py_version.group(1), (
        f"TypeScript SDK is {pkg['version']}, Python SDK is {py_version.group(1)}; "
        "they implement the same protocol version"
    )
    assert pkg["license"] == "MIT" and "MIT" in text
