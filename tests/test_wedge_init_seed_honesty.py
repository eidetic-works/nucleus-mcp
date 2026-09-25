"""``nucleus init`` must not report success over an empty brain.

``init_cmd.do_init`` asked ``ensure_seeds`` for the list of keys it wrote and
treated an empty list as proof the seeds were already there::

    written = ensure_seeds(store)
    if not written:
        seeds_status = f"{len(SEED_KEYS)} skipped (already present)"

An empty list has TWO causes. One is "all three seeds are already in the store".
The other is "``.brain/memory/engrams.json`` — the file the seed values are
copied FROM — does not exist, so there was nothing to copy". ``ensure_seeds``
``continue``s past a missing entry silently, so both collapse to ``[]``.

Measured on a fresh ``git init`` directory: ``nucleus init`` prints
``seeds: 3 skipped (already present)`` while ``history.jsonl`` has 0 rows and
none of the three seeds exist anywhere. It is the first command a new user runs
and it reports success over nothing. This is the same failure as everywhere else
in this repo — a value coerced to green because the check could not express the
third state.

The fix does not make init fail; a brain with no seeds is still usable. It makes
init say which of the two things happened. ``already present`` must become
reachable ONLY when the seeds are genuinely present, which is what the positive
control below pins down — otherwise this fix is just a differently-worded lie.
"""
from __future__ import annotations

import json

import pytest

from nucleus_wedge.init_cmd import do_init
from nucleus_wedge.seed import SEED_KEYS
from nucleus_wedge.store import Store


@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.chdir(repo)
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    return repo


def _seed_source(brain, keys=SEED_KEYS):
    """Write the engrams.json that ensure_seeds copies FROM."""
    d = brain / "memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / "engrams.json").write_text(
        json.dumps(
            [{"key": k, "value": f"seed body for {k}", "context": "seed", "intensity": 7} for k in keys]
        ),
        encoding="utf-8",
    )


def _status_line(capsys):
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("seeds:"):
            return line
    raise AssertionError("init printed no seeds: line")


# ── NEGATIVE CONTROL: the false success ────────────────────────────────────


def test_fresh_init_does_not_claim_seeds_are_already_present(fresh, capsys):
    """The exact line a brand-new user saw over an empty brain."""
    assert do_init(None, "default", False) == 0
    line = _status_line(capsys)
    assert "already present" not in line, (
        f"init claimed the seeds were already present over an empty brain: {line!r}"
    )


def test_fresh_init_names_the_missing_seed_source(fresh, capsys):
    """A user who is told 'nothing happened' needs to know why, or they
    cannot act on it."""
    do_init(None, "default", False)
    line = _status_line(capsys).lower()
    assert "engrams.json" in line or "seed source" in line
    assert "0" in line or "none" in line


def test_fresh_init_leaves_a_brain_with_no_seeds(fresh):
    """Pins the underlying fact the message must not contradict."""
    do_init(None, "default", False)
    present = Store(brain_path=fresh / ".brain").keys_present()
    assert not (set(SEED_KEYS) & present)


# ── POSITIVE CONTROL: "added" and "already present" must stay reachable ────


def test_init_reports_added_when_the_seed_source_exists(fresh, capsys):
    brain = fresh / ".brain"
    _seed_source(brain)
    do_init(None, "default", False)
    line = _status_line(capsys)
    assert "added" in line
    assert "already present" not in line
    assert set(SEED_KEYS) <= Store(brain_path=brain).keys_present()


def test_second_init_reports_already_present_only_when_genuinely_present(fresh, capsys):
    """Stops the fix being over-applied — 'already present' must still be
    reachable, and only for the case it actually describes."""
    brain = fresh / ".brain"
    _seed_source(brain)
    do_init(None, "default", False)
    capsys.readouterr()
    do_init(None, "default", False)
    line = _status_line(capsys)
    assert "already present" in line
    assert set(SEED_KEYS) <= Store(brain_path=brain).keys_present()


def test_partial_seed_source_reports_both_halves(fresh, capsys):
    """One seed available, two not. Neither 'added' nor 'already present'
    alone is honest here."""
    brain = fresh / ".brain"
    _seed_source(brain, keys=SEED_KEYS[:1])
    do_init(None, "default", False)
    line = _status_line(capsys)
    assert "1 added" in line
    assert "already present" not in line


def test_seeds_none_mode_is_unchanged(fresh, capsys):
    do_init(None, "none", False)
    assert "--seeds none" in _status_line(capsys)
