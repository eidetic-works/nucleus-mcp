"""A sweep must not queue a ratified governance artifact for "correction".

Why this exists: docs/PRINCIPAL.md declares itself immutable and carries a body
hash that scripts/principal_control.py verifies before it will execute at all.
On 2026-08-19 the doc sweep queued it, a vendor made factual corrections (a
branch name, an ADR count, a moved path -- each individually correct), and
rewrote the displayed hash to match its own edit. Recovering those edits took
the governance gate from PASS to FAIL.

The failure mode is worth naming precisely: every individual edit was RIGHT.
The doc really did say `feat/dsor-verifier` for something now merged to main.
It was a correct change applied to the wrong KIND of object -- one whose content
is fixed by ratification and machine-checked for integrity. And the hash rewrite
made it worse than a plain edit: the doc would have READ consistent to a human
while principal_control still refused to run.
"""

import importlib.util
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SPEC_GEN = _REPO / "scripts" / "spec_gen.py"


def _load():
    spec = importlib.util.spec_from_file_location("spec_gen", _SPEC_GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_principal_is_listed_as_protected():
    assert "docs/PRINCIPAL.md" in _load().PROTECTED_ARTIFACTS


def test_the_generator_refuses_to_emit_a_task_for_it():
    """Behavioural: run the real generator over the real docs and assert the
    artifact is absent from the output. A constant nobody reads is not a guard."""
    out = subprocess.run(
        ["python3", str(_SPEC_GEN), "--glob", "docs/*.md", "--template",
         "audit-doc", "--dry-run", "--exclude-preset", "gq"],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    combined = out.stdout + out.stderr
    assert "refusing" in combined and "PRINCIPAL.md" in combined, (
        "generator did not report refusing the ratified artifact"
    )


def test_ordinary_docs_are_not_swept_up_by_the_protection():
    """OPPOSED: the protected list must be exact. A prefix or substring match
    would silently shrink the audit set -- the same incomplete-set failure this
    sweep has hit repeatedly."""
    protected = _load().PROTECTED_ARTIFACTS
    for ordinary in ("docs/PRINCIPLES.md", "docs/PRINCIPAL_NOTES.md",
                     "docs/ADRS.md", "docs/TESTING.md"):
        assert ordinary not in protected


def test_the_governance_hash_actually_holds_right_now():
    """The regression this protects. If PRINCIPAL.md's body stops hashing to the
    constant principal_control enforces, that script refuses to execute -- so
    this asserts the live repo state, not just the guard around it."""
    import hashlib
    import re
    src = (_REPO / "scripts" / "principal_control.py").read_text()
    expected = re.search(r'PRINCIPAL_BODY_SHA256\s*=\s*["\']([0-9a-f]{64})["\']', src).group(1)
    marker = "<!-- The ratified plan body follows verbatim below this line. -->"
    doc = (_REPO / "docs" / "PRINCIPAL.md").read_text()
    assert marker in doc, "PRINCIPAL body marker missing"
    body = doc.split(marker, 1)[1]
    if body.startswith("\n"):
        body = body[1:]
    got = hashlib.sha256(body.encode()).hexdigest()
    assert got == expected, (
        f"PRINCIPAL.md body hash is {got[:16]}, principal_control expects "
        f"{expected[:16]} -- the governance gate is FAILING and that script "
        f"refuses to execute"
    )
