"""The PII gate must catch a stranger's address and ignore a fixture's.

Measured 2026-09-19, before this gate existed: a two-row prospect list passed the
secret scanner (an email is not a credential) and passed the identity gate (none
of those names are the operator's), so it would have shipped in the wheel. The
gate below is the missing instrument; these are the inputs that decide whether it
works.

The hard part is not finding addresses. It is NOT finding the 100+ fixtures this
repo already contains — alice@example.com, t@test.com, foo@bar.com — because a
gate that fires on its own test data is one somebody turns off.
"""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "third_party_pii_gate", PKG_ROOT / "scripts" / "third_party_pii_gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


# --- the positive control -------------------------------------------------

def test_a_strangers_address_is_found():
    found = gate.suspicious_addresses("contact jane.roe@acmecorp.io for access", set())
    assert found == {"jane.roe@acmecorp.io"}


def test_a_prospect_table_is_found_even_with_synthetic_rows():
    """The SHAPE is the signal. A list that looks like contacts does not ship."""
    body = "name,email\nJane Roe,jane@acmecorp.io\n"
    assert gate.looks_like_a_contact_table("data/prospects.csv", body)


# --- the opposed half: this repo's own fixtures must stay silent -----------

def test_placeholder_domains_are_not_flagged():
    text = ("alice@example.com bob@example.com t@test.com foo@bar.com a@b.com "
            "x@y.com operator@example.com you@example.com t@t.invalid")
    assert gate.suspicious_addresses(text, set()) == set(), (
        "these are fixtures; a gate that fires on its own test data gets disabled"
    )


def test_the_products_own_and_protocol_addresses_are_not_flagged():
    text = "hello@nucleusos.dev admin@nucleusos.dev git@github.com 1+x@users.noreply.github.com"
    assert gate.suspicious_addresses(text, set()) == set()


def test_the_allowlist_suppresses_only_what_it_names():
    text = "partnerships@perplexity.ai and jane.roe@acmecorp.io"
    got = gate.suspicious_addresses(text, {"partnerships@perplexity.ai"})
    assert got == {"jane.roe@acmecorp.io"}, (
        f"the allowlist must suppress its entry and nothing else; got {got}"
    )


def test_a_csv_without_an_email_column_is_not_a_contact_table():
    assert not gate.looks_like_a_contact_table("data/metrics.csv", "name,count\nfoo,3\n")


def test_a_non_csv_is_not_a_contact_table():
    assert not gate.looks_like_a_contact_table(
        "docs/notes.md", "name,email\nJane,jane@acmecorp.io\n")


# --- end to end, on a real artifact ---------------------------------------

def _wheel(tmp_path: Path, extra: dict[str, str] | None = None) -> Path:
    p = tmp_path / "a.whl"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("pkg/__init__.py", "# fixtures: alice@example.com t@test.com\n")
        for name, body in (extra or {}).items():
            z.writestr(name, body)
    return p


def test_clean_wheel_exits_zero(tmp_path):
    assert gate.main(["x", str(_wheel(tmp_path))]) == gate.EXIT_CLEAN


def test_poisoned_wheel_exits_two(tmp_path):
    art = _wheel(tmp_path, {"pkg/prospects.csv":
                            "name,email\nJane Roe,jane.roe@acmecorp.io\n"})
    assert gate.main(["x", str(art)]) == gate.EXIT_FOUND


def test_a_missing_artifact_is_insufficient_not_clean(tmp_path):
    """An unreadable input must never read as a pass."""
    assert gate.main(["x", str(tmp_path / "nope.whl")]) == gate.EXIT_INSUFFICIENT


def test_the_report_masks_the_address(capsys, tmp_path):
    art = _wheel(tmp_path, {"pkg/p.csv": "name,email\nJane,jane.roe@acmecorp.io\n"})
    gate.main(["x", str(art)])
    out = capsys.readouterr().out
    assert "jane.roe@acmecorp.io" not in out, "the gate's report must not become the leak"
    assert "acmecorp.io" in out, "but it must say enough to act on"


# --- worktree mode: the scope the gq lane proved was missing -----------------

def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for rel, body in files.items():
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return tmp_path


def test_worktree_mode_fails_on_a_tracked_contact_table(tmp_path):
    """The case that existed for real in GentleQuest and that an artifact-only
    scan can never see: a tracked table that nothing packages."""
    repo = _repo(tmp_path, {
        "marketing/press.csv": "name,outlet,email\nJane Roe,The Post,jane@realoutlet.com\n",
        "ok.py": "x = 1  # alice@example.com\n",
    })
    assert gate.scan_worktree(repo) == gate.EXIT_FOUND


def test_worktree_mode_passes_without_a_table(tmp_path):
    repo = _repo(tmp_path, {"ok.py": "x = 1  # alice@example.com t@test.com\n"})
    assert gate.scan_worktree(repo) == gate.EXIT_CLEAN


def test_loose_addresses_are_reported_but_do_not_fail_the_worktree_scan(tmp_path):
    """A changelog naming a contributor must not turn the gate off.

    Tables are the prospect-list shape and always a finding; a lone address in a
    private repo is a judgement call, so it is reported and not failed.
    """
    repo = _repo(tmp_path, {"CHANGELOG.md": "thanks to someone@realdomain.dev\n"})
    assert gate.scan_worktree(repo) == gate.EXIT_CLEAN


def test_an_empty_tree_is_insufficient_not_clean(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert gate.scan_worktree(tmp_path) == gate.EXIT_INSUFFICIENT


# --- filename-shaped matches: every iOS/Flutter repo hits this --------------

def test_apple_asset_catalog_filenames_are_not_addresses():
    """`Icon-App-20x20@2x.png` parses as user@domain with TLD "png".

    Measured by the gq lane on GentleQuest: two Contents.json files, 15 hits, and
    the same shape appears in every Flutter or iOS project. Fixed as a class —
    a domain ending in a media or document extension is a filename — rather than
    by allowlisting a project's asset catalog.
    """
    catalog = ('{"images":[{"filename":"Icon-App-20x20@2x.png"},'
               '{"filename":"logo@3x.jpg"}],"info":{"author":"xcode"}}')
    assert gate.suspicious_addresses(catalog, set()) == set()


def test_a_real_address_at_a_dotted_modern_tld_still_fires():
    """The narrowing must not swallow real TLDs that look like extensions."""
    assert gate.suspicious_addresses("someone@realstartup.app", set()) == {
        "someone@realstartup.app"}
    assert gate.suspicious_addresses("someone@agency.dev", set()) == {
        "someone@agency.dev"}
