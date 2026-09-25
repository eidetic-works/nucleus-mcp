"""
Regression tests for ADR-0042 "Project Spine" batch XY-2 (relay project tag).

The D3 contract: envelopes gain a ``project`` field stamped by the writer;
readers filter on (project, role) under ``NUCLEUS_PROJECT_SPINE``. ``board`` is
the cross-project broadcast channel (``project: "*"``). Untagged envelopes are
legacy — surfaced with a grace warning, never dropped.

The load-bearing scenario is the *fashion leak* (ADR §Forces #1): three
nucleus-lane relays leaked into the fashion-lane session stream because
``claude_code_main`` is a role in every project and role-only routing cannot
tell them apart. This module reproduces the leak with two project brains
sharing one role bucket and asserts zero cross-surface under the flag, and
byte-identical behavior with the flag off.

Two reader surfaces are covered because the leak streams through both:
``relay_inbox`` (bulk pull) and ``relay_subscribe_notifications_impl`` (the
live-session push path).

Cooperates with the autouse conftest fixtures (``_ensure_brain_path``,
``_clean_relay_env``, ``_reset_tenant_contextvar``) and XY-1's
``_clean_project_spine_flag`` — tests that need the flag ON set it via
monkeypatch, which runs after the autouse clear and wins for the body.
"""

import asyncio
import json
import logging
import subprocess

import pytest

from mcp_server_nucleus.runtime.relay.core import (
    relay_inbox,
    relay_post,
    relay_status,
)
from mcp_server_nucleus.runtime.relay_notify import (
    relay_subscribe_notifications_impl,
)


# ──────────────────────────────────────────────────────────────
# helpers (lifted from tests/test_project_spine.py, brain optional)
# ──────────────────────────────────────────────────────────────
def _make_project(base, name, *, git=True, remote=None, brain=False):
    """Create a fake project dir. Default: git repo, NO owned .brain.

    Omitting ``.brain`` is deliberate for the leak scenario: get_brain_path's
    XY-1 project arm only diverges from the env pin when the project owns a
    ``.brain``. With no ``.brain``, both writers + reader resolve to the SHARED
    env-pinned bucket (reproducing the role-collision), while the D3 *tag* is
    still driven independently by ``resolve_project(cwd).slug``.
    """
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    if remote:
        subprocess.run(
            ["git", "-C", str(root), "remote", "add", "origin", remote], check=True
        )
    if brain:
        (root / ".brain").mkdir(exist_ok=True)
    return root


def _shared_brain(base):
    shared = base / "shared_brain"
    (shared / "relay").mkdir(parents=True, exist_ok=True)
    return shared


class _FakeCtx:
    """Minimal async Context capturing info/warning notifications."""

    def __init__(self):
        self.infos: list[str] = []
        self.warnings: list[str] = []

    async def info(self, msg):
        self.infos.append(msg)

    async def warning(self, msg):
        self.warnings.append(msg)

    @property
    def all(self):
        return self.infos + self.warnings


def _post(to, sender, subject, *, cwd, monkeypatch, **kw):
    monkeypatch.chdir(cwd)
    return relay_post(to=to, subject=subject, body=subject, sender=sender, **kw)


def _bucket_files(shared, bucket="claude_code_main"):
    return sorted((shared / "relay" / bucket).glob("*.json"))


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════
# CORE: the fashion leak — relay_inbox
# ══════════════════════════════════════════════════════════════
def test_flag_on_inbox_zero_cross_surface(tmp_path, monkeypatch):
    """Flag ON: two brains share ``claude_code_main``; a fashion reader sees
    ONLY the fashion envelope — the nucleus envelope is dropped (the leak
    block)."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    r_nuc = _post("claude_code_main", "claude_code_main", "nucleus-msg",
                  cwd=nucleus, monkeypatch=monkeypatch)
    r_fash = _post("claude_code_main", "claude_code_main", "fashion-msg",
                   cwd=fashion, monkeypatch=monkeypatch)

    # both landed in the SAME shared bucket, tagged by cwd project
    tags = {_load(p).get("project") for p in _bucket_files(shared)}
    assert tags == {"nucleus", "fashion"}

    monkeypatch.chdir(fashion)
    out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    ids = {m["id"] for m in out["messages"]}
    assert r_fash["message_id"] in ids       # fashion reader sees fashion
    assert r_nuc["message_id"] not in ids     # zero cross-surface (the leak block)


def test_flag_off_inbox_sees_both(tmp_path, monkeypatch):
    """Flag OFF: the same reader sees BOTH envelopes — today's behavior."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)

    r_nuc = _post("claude_code_main", "claude_code_main", "nucleus-msg",
                  cwd=nucleus, monkeypatch=monkeypatch)
    r_fash = _post("claude_code_main", "claude_code_main", "fashion-msg",
                   cwd=fashion, monkeypatch=monkeypatch)

    monkeypatch.chdir(fashion)
    out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    ids = {m["id"] for m in out["messages"]}
    assert r_fash["message_id"] in ids
    assert r_nuc["message_id"] in ids         # no filter — both surface


# ══════════════════════════════════════════════════════════════
# CORE: the fashion leak — relay_subscribe_notifications (push path)
# ══════════════════════════════════════════════════════════════
def _arm_once(monkeypatch, state_dir, inbox_name="claude_code_main"):
    """Pre-create the seen-marker dir (so first_run=False and pre-existing
    files surface), then run one burst scan and return the FakeCtx."""
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(state_dir))
    (state_dir / f"server-seen-{inbox_name}").mkdir(parents=True, exist_ok=True)
    ctx = _FakeCtx()
    asyncio.run(
        relay_subscribe_notifications_impl(
            ctx, timeout_seconds=0, inbox_filter=inbox_name
        )
    )
    return ctx


def test_flag_on_notify_zero_cross_surface(tmp_path, monkeypatch):
    """Flag ON: the live push path applies the same filter — a fashion reader
    is notified of the fashion arrival only."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    r_nuc = _post("claude_code_main", "claude_code_main", "nucleus-msg",
                  cwd=nucleus, monkeypatch=monkeypatch)
    r_fash = _post("claude_code_main", "claude_code_main", "fashion-msg",
                   cwd=fashion, monkeypatch=monkeypatch)

    monkeypatch.chdir(fashion)
    ctx = _arm_once(monkeypatch, tmp_path / "state")
    fired = "\n".join(ctx.all)
    assert r_fash["message_id"] in fired
    assert r_nuc["message_id"] not in fired   # leak blocked on the push path too


def test_flag_off_notify_sees_both(tmp_path, monkeypatch):
    """Flag OFF: the push path surfaces both arrivals — byte-identical."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)

    r_nuc = _post("claude_code_main", "claude_code_main", "nucleus-msg",
                  cwd=nucleus, monkeypatch=monkeypatch)
    r_fash = _post("claude_code_main", "claude_code_main", "fashion-msg",
                   cwd=fashion, monkeypatch=monkeypatch)

    monkeypatch.chdir(fashion)
    ctx = _arm_once(monkeypatch, tmp_path / "state")
    fired = "\n".join(ctx.all)
    assert r_fash["message_id"] in fired
    assert r_nuc["message_id"] in fired


# ══════════════════════════════════════════════════════════════
# board passthrough (both flag states)
# ══════════════════════════════════════════════════════════════
def test_board_stamped_star_and_broadcasts_flag_on(tmp_path, monkeypatch):
    """Flag ON: a ``board`` post is stamped ``project="*"`` and surfaces to a
    reader in ANY project."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    r = _post("board", "claude_code_main", "board-msg",
              cwd=nucleus, monkeypatch=monkeypatch)
    stamped = {_load(p).get("project") for p in _bucket_files(shared, "board")}
    assert stamped == {"*"}                   # cross-project broadcast tag

    monkeypatch.chdir(fashion)                # different project reads the board
    out = relay_inbox(recipient="board", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}


def test_board_passthrough_flag_off(tmp_path, monkeypatch):
    """Flag OFF: board posts carry no project key and still surface."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)

    r = _post("board", "claude_code_main", "board-msg",
              cwd=nucleus, monkeypatch=monkeypatch)
    for p in _bucket_files(shared, "board"):
        assert "project" not in _load(p)      # no new field flag-off

    monkeypatch.chdir(nucleus)
    out = relay_inbox(recipient="board", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}


# ══════════════════════════════════════════════════════════════
# legacy-envelope grace: surfaced + warned, NEVER dropped
# ══════════════════════════════════════════════════════════════
def test_legacy_untagged_surfaced_and_warned(tmp_path, monkeypatch, caplog):
    """A legacy envelope with no ``project`` key is surfaced under the flag AND
    emits the grace warning — never dropped."""
    shared = _shared_brain(tmp_path)
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))

    # write a legacy (untagged) envelope by posting with the flag OFF
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    r = _post("claude_code_main", "claude_code_main", "legacy-msg",
              cwd=fashion, monkeypatch=monkeypatch)
    assert all("project" not in _load(p) for p in _bucket_files(shared))

    # now read under the flag ON from a project reader
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")
    monkeypatch.chdir(fashion)
    with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
        out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)

    assert r["message_id"] in {m["id"] for m in out["messages"]}  # surfaced
    assert "legacy untagged envelope" in caplog.text              # warned
    assert r["message_id"] in caplog.text


# ══════════════════════════════════════════════════════════════
# reader-unknown-project degrade: surface-all, never a silent drop
# ══════════════════════════════════════════════════════════════
def test_reader_without_project_degrades_to_surface_all(tmp_path, monkeypatch):
    """Flag ON, reader cwd is NOT a project (resolve_project -> None): it cannot
    discriminate, so it surfaces every tagged envelope rather than dropping."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    bare = tmp_path / "not_a_project"
    bare.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    r = _post("claude_code_main", "claude_code_main", "nucleus-msg",
              cwd=nucleus, monkeypatch=monkeypatch)

    monkeypatch.chdir(bare)
    out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}  # degrade, not drop


# ══════════════════════════════════════════════════════════════
# flag-OFF envelope byte-identity: no new field
# ══════════════════════════════════════════════════════════════
def test_flag_off_no_project_field_written(tmp_path, monkeypatch):
    """Flag OFF: the written envelope has NO ``project`` key at all."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)

    _post("claude_code_main", "claude_code_main", "msg",
          cwd=nucleus, monkeypatch=monkeypatch)
    files = _bucket_files(shared)
    assert files
    for p in files:
        assert "project" not in _load(p)


def test_flag_on_project_field_written(tmp_path, monkeypatch):
    """Flag ON: the written envelope carries the resolved project slug."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    _post("claude_code_main", "claude_code_main", "msg",
          cwd=nucleus, monkeypatch=monkeypatch)
    files = _bucket_files(shared)
    assert files
    assert all(_load(p).get("project") == "nucleus" for p in files)


# ══════════════════════════════════════════════════════════════
# structural sentinel: flag OFF never imports/calls resolve_project
# ══════════════════════════════════════════════════════════════
def test_flag_off_never_touches_project_module(tmp_path, monkeypatch):
    """Booby-trap ``runtime.project.resolve_project`` to raise. Flag OFF: a
    post + inbox round-trip must NOT detonate (the OFF path never imports or
    calls it) — mirrors XY-1's sentinel."""
    import mcp_server_nucleus.runtime.project as project_mod

    def _sentinel(*_a, **_k):
        raise RuntimeError("resolve_project must not run on the flag-OFF path")

    monkeypatch.setattr(project_mod, "resolve_project", _sentinel)
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)

    shared = _shared_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.chdir(tmp_path)

    r = relay_post(to="claude_code_main", subject="s", body="b",
                   sender="claude_code_main")
    assert r["sent"] is True
    out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}
    # relay_status must also stay inert on the OFF path
    st = relay_status()
    assert "mailboxes" in st


# ══════════════════════════════════════════════════════════════
# relay_status counts respect the filter under the flag
# ══════════════════════════════════════════════════════════════
def test_status_counts_filtered_under_flag(tmp_path, monkeypatch):
    """Flag ON: a fashion reader's status counts exclude the nucleus envelope
    sharing the bucket."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    _post("claude_code_main", "claude_code_main", "nucleus-msg",
          cwd=nucleus, monkeypatch=monkeypatch)
    _post("claude_code_main", "claude_code_main", "fashion-msg",
          cwd=fashion, monkeypatch=monkeypatch)

    monkeypatch.chdir(fashion)
    st = relay_status()
    assert st["mailboxes"]["claude_code_main"]["total"] == 1  # only fashion counted

    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    st_off = relay_status()
    assert st_off["mailboxes"]["claude_code_main"]["total"] == 2  # both, flag off


# ══════════════════════════════════════════════════════════════
# Panel follow-up 2: no-sentinel rule
#
# A project-less writer (daemon / launchd-spawned: resolve_project -> None)
# OMITS the project key entirely rather than stamping "unknown". Absent key =
# legacy by construction (surfaced + grace-warned, NEVER dropped). Readers also
# treat a defensively-inbound "unknown" sentinel (a foreign/older writer) as
# legacy — "unknown" must never reach the mismatch-drop branch. Board "*" is
# unaffected. This is the block the adversarial spec judge empirically refuted:
# the old writer stamped "unknown", the reader had no "unknown" case, so every
# project-tagged reader silently dropped the daemon's mail.
# ══════════════════════════════════════════════════════════════
def test_flag_on_projectless_writer_omits_key_and_surfaces(tmp_path, monkeypatch, caplog):
    """Flag ON, writer cwd is NOT a project (daemon / launchd scenario:
    resolve_project -> None): the envelope lands with NO ``project`` key (no
    "unknown" sentinel), is VISIBLE to a project-tagged reader, and fires the
    legacy grace warning — never silently dropped."""
    shared = _shared_brain(tmp_path)
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    daemon_cwd = tmp_path / "daemon_no_project"
    daemon_cwd.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    # writer runs from a non-project cwd → key OMITTED (never "unknown")
    r = _post("claude_code_main", "claude_code_main", "daemon-msg",
              cwd=daemon_cwd, monkeypatch=monkeypatch)
    files = _bucket_files(shared)
    assert files
    for p in files:
        env = _load(p)
        assert "project" not in env             # no key at all — no sentinel

    # a project-tagged reader still SEES it, with the grace warning
    monkeypatch.chdir(fashion)
    with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
        out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}   # visible, not dropped
    assert "legacy untagged envelope" in caplog.text               # grace-warned
    assert r["message_id"] in caplog.text


def test_flag_on_real_project_writer_still_blocks_mismatch(tmp_path, monkeypatch):
    """The no-sentinel writer change does NOT weaken the leak block: a writer
    WITH a real project (nucleus) still stamps its slug, and a fashion reader
    still drops it (genuine cross-project mismatch)."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    r_nuc = _post("claude_code_main", "claude_code_main", "nucleus-msg",
                  cwd=nucleus, monkeypatch=monkeypatch)
    files = _bucket_files(shared)
    assert files and all(_load(p).get("project") == "nucleus" for p in files)  # real slug stamped

    monkeypatch.chdir(fashion)
    out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    assert r_nuc["message_id"] not in {m["id"] for m in out["messages"]}  # still blocked


def test_inbound_unknown_sentinel_surfaced_not_dropped(tmp_path, monkeypatch, caplog):
    """Defensive forward-compat: an INBOUND envelope carrying the legacy
    ``project: "unknown"`` sentinel (a foreign/older writer) is treated as
    legacy — surfaced + grace-warned — even for a reader in a concrete DIFFERENT
    project. "unknown" must never reach the mismatch-drop branch."""
    shared = _shared_brain(tmp_path)
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))

    # write a valid legacy envelope (flag OFF), then stamp the foreign sentinel
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    r = _post("claude_code_main", "claude_code_main", "foreign-msg",
              cwd=fashion, monkeypatch=monkeypatch)
    (fp,) = _bucket_files(shared)
    env = _load(fp)
    env["project"] = "unknown"
    fp.write_text(json.dumps(env), encoding="utf-8")

    # read under the flag from a reader in a DIFFERENT concrete project (nucleus)
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")
    monkeypatch.chdir(nucleus)
    with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
        out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}  # surfaced, not dropped
    assert "legacy untagged envelope" in caplog.text              # grace-warned


def test_board_star_unaffected_by_no_sentinel(tmp_path, monkeypatch):
    """Board ``"*"`` is unaffected by the no-sentinel rule: even a writer with
    NO project context (daemon cwd) posting to ``board`` stamps ``"*"`` (the
    board branch is independent of resolve_project) and broadcasts to a reader
    in any project."""
    shared = _shared_brain(tmp_path)
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    daemon_cwd = tmp_path / "daemon_no_project"
    daemon_cwd.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    r = _post("board", "claude_code_main", "board-msg",
              cwd=daemon_cwd, monkeypatch=monkeypatch)
    stamped = {_load(p).get("project") for p in _bucket_files(shared, "board")}
    assert stamped == {"*"}                      # board stamps "*" regardless of cwd

    monkeypatch.chdir(fashion)
    out = relay_inbox(recipient="board", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}


# ══════════════════════════════════════════════════════════════
# XY-5: XY-2 re-judge defensive nits on the _project_visible predicate
#
# (a) type/emptiness guard — an inbound envelope carrying project="" / an int /
#     a list (unmintable by any in-repo writer — hand-forged or corrupt) is
#     treated as LEGACY (surface + warn), NEVER routed to the silent
#     mismatch-drop. Same silent-drop class the "unknown" sentinel guards.
# (b) board-bucket check precedes the legacy check — an untagged board post
#     surfaces with NO spurious 'legacy' warn (board is the broadcast inbox).
#
# Both are behavior-preserving for genuine tagged/untagged traffic; the genuine
# cross-project leak block (valid slug != valid slug) is unchanged.
# ══════════════════════════════════════════════════════════════
from mcp_server_nucleus.runtime.relay.core import _project_visible


@pytest.mark.parametrize("bad", ["", "   ", 5, 0, ["fashion"], {"p": 1}, 3.14])
def test_project_visible_malformed_tag_is_legacy_not_dropped(bad):
    """Nit (a): a malformed project tag, read by a concrete-project reader, is
    surfaced + warned (legacy) — NOT silently dropped by the mismatch branch."""
    assert _project_visible(bad, "nucleus", "claude_code_main") == (True, True)


def test_project_visible_board_untagged_no_spurious_warn():
    """Nit (b): board reader + untagged (None) -> surface, NO legacy warn."""
    assert _project_visible(None, "nucleus", "board") == (True, False)


def test_project_visible_board_surfaces_every_shape_without_warn():
    """Board precedes legacy/unknown/malformed: broadcast inbox surfaces all,
    never warns (no spurious 'legacy' on an untagged/foreign board post)."""
    for env in (None, "unknown", "", "   ", 5, ["x"], "*", "fashion"):
        assert _project_visible(env, "nucleus", "board") == (True, False)


def test_project_visible_genuine_mismatch_still_blocks():
    """Leak block intact: a valid slug != the reader's valid slug (non-board)
    still DROPS — the guards never let a real cross-project tag through."""
    assert _project_visible("fashion", "nucleus", "claude_code_main") == (False, False)


def test_project_visible_preserved_behaviors_unchanged():
    """Every pre-existing branch for genuine traffic is byte-identical."""
    assert _project_visible(None, "nucleus", "claude_code_main") == (True, True)      # legacy untagged
    assert _project_visible("unknown", "nucleus", "claude_code_main") == (True, True) # foreign sentinel
    assert _project_visible("*", "nucleus", "claude_code_main") == (True, False)      # star broadcast
    assert _project_visible("fashion", None, "claude_code_main") == (True, False)     # reader no-project degrade
    assert _project_visible("nucleus", "nucleus", "claude_code_main") == (True, False)  # same project


def test_inbound_empty_string_project_surfaced_not_dropped(tmp_path, monkeypatch, caplog):
    """Nit (a) end-to-end: an inbound envelope hand-forged with project="" is
    surfaced + grace-warned for a reader in a concrete DIFFERENT project — never
    silently dropped (the class the mismatch branch would otherwise swallow)."""
    shared = _shared_brain(tmp_path)
    fashion = _make_project(tmp_path, "fashion", remote="https://x/acme/fashion.git")
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))

    # write a valid legacy envelope (flag OFF), then stamp a malformed empty tag
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    r = _post("claude_code_main", "claude_code_main", "forged-msg",
              cwd=fashion, monkeypatch=monkeypatch)
    (fp,) = _bucket_files(shared)
    env = _load(fp)
    env["project"] = ""            # unmintable by any in-repo writer
    fp.write_text(json.dumps(env), encoding="utf-8")

    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")
    monkeypatch.chdir(nucleus)     # concrete DIFFERENT project reads it
    with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
        out = relay_inbox(recipient="claude_code_main", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}  # surfaced, not dropped
    assert "legacy untagged envelope" in caplog.text              # grace-warned


def test_board_untagged_no_spurious_legacy_warn(tmp_path, monkeypatch, caplog):
    """Nit (b) end-to-end: an untagged (legacy) envelope in the board bucket,
    read by a board reader under the flag, surfaces with NO spurious 'legacy'
    warn — the board-bucket check now precedes the legacy check."""
    shared = _shared_brain(tmp_path)
    nucleus = _make_project(tmp_path, "nucleus", remote="https://x/acme/nucleus.git")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(shared))

    # untagged board envelope written with the flag OFF (no project key)
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    r = _post("board", "claude_code_main", "board-legacy",
              cwd=nucleus, monkeypatch=monkeypatch)
    for p in _bucket_files(shared, "board"):
        assert "project" not in _load(p)

    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")
    monkeypatch.chdir(nucleus)
    with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
        out = relay_inbox(recipient="board", unread_only=True, limit=50)
    assert r["message_id"] in {m["id"] for m in out["messages"]}  # surfaced
    assert "legacy untagged envelope" not in caplog.text          # no spurious warn
