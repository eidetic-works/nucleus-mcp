"""Offline tests for the cross-vendor dispatch-and-capture extension.

These NEVER invoke the real ``agy``/``devin`` CLIs or any network: a fake-CLI
shim (a tiny shell script placed first on PATH) stands in for the vendor binary.
Coverage:

  * dispatch → capture writes an ``artifact_refs`` relay envelope + a
    vendor-tagged engram (and the STRICT gate passes because artifact_ref is a
    real reference);
  * a hanging fake-CLI yields a ``timed_out`` envelope (hard kill, no stall);
  * the prompt is passed identity-safe (never in the vendor process argv);
  * flag OFF ⇒ no-op (no invocation, no envelope, no engram);
  * routing tiers are flag-gated (never selected when the flag is off).
"""

from __future__ import annotations

import json
import builtins
import os
import re
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import vendor_dispatch as vd


# ── fake-CLI shim helpers ──────────────────────────────────────────────────────
_ECHO_SCRIPT = """#!/bin/sh
# Record argv (flags only — the prompt must never be here) for identity checks.
if [ -n "$FAKE_CLI_ARGV" ]; then printf '%s\\n' "$*" > "$FAKE_CLI_ARGV"; fi
# Drain the prompt from stdin so subprocess.run(input=...) never blocks.
cat > /dev/null
# Mark that we were actually invoked (flag-OFF test asserts this stays absent).
if [ -n "$FAKE_CLI_MARKER" ]; then echo invoked >> "$FAKE_CLI_MARKER"; fi
echo "FAKE_VENDOR_OUTPUT_TOKEN"
exit 0
"""

_HANG_SCRIPT = """#!/bin/sh
if [ -n "$FAKE_CLI_MARKER" ]; then echo invoked >> "$FAKE_CLI_MARKER"; fi
sleep 30
echo "should never be reached"
"""

# devin PROMPT-FILE fake — mirrors reality: the real ``devin -p --`` (stdin) drops
# into REPL and panics, so devin now runs ``-p --prompt-file <FILE>`` and the
# prompt arrives via that FILE, NOT stdin. This shim reads the prompt from the
# ``--prompt-file`` arg (never touching stdin) so the test exercises the real path.
_PROMPT_FILE_SCRIPT = """#!/bin/sh
# Record argv (flags + the temp-file PATH — never the prompt text) for identity checks.
if [ -n "$FAKE_CLI_ARGV" ]; then printf '%s\\n' "$*" > "$FAKE_CLI_ARGV"; fi
# Locate --prompt-file <path> and read the prompt from that file (not stdin).
pf=""
while [ $# -gt 0 ]; do
    case "$1" in
        --prompt-file) pf="$2"; shift 2 ;;
        *) shift ;;
    esac
done
if [ -n "$FAKE_CLI_MARKER" ]; then echo invoked >> "$FAKE_CLI_MARKER"; fi
# Copy the prompt the executor delivered via the file so the test can assert the
# prompt-file path was actually exercised (proves the prompt was NOT dropped).
if [ -n "$FAKE_CLI_PROMPT_SEEN" ] && [ -n "$pf" ] && [ -f "$pf" ]; then
    cat "$pf" > "$FAKE_CLI_PROMPT_SEEN"
fi
echo "FAKE_VENDOR_OUTPUT_TOKEN"
exit 0
"""


def _install_fake(bindir: Path, name: str, script: str) -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    p = bindir / name
    p.write_text(script)
    p.chmod(0o755)


@pytest.fixture
def fake_bin(tmp_path, monkeypatch):
    """A dir prepended to PATH; install fake vendor CLIs into it per test."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    return bindir


@pytest.fixture(autouse=True)
def _force_temp_brain(tmp_path, monkeypatch):
    """HERMETICITY GUARD — force a per-test temp brain regardless of ambient env.

    The dispatch→capture path writes a relay envelope (via ``relay_ops.relay_post``
    → ``common.get_brain_path``) and a vendor-tagged engram (via
    ``nucleus_wedge.store.Store`` → ``Store.brain_path``). BOTH resolve the brain
    directory from ``NUCLEUS_BRAIN_PATH`` **at call time** — neither caches it at
    import (the executor's ``relay_ops`` / ``Store`` imports are function-local),
    so setting the env here, before any code under test runs, fully redirects the
    writes.

    conftest's ``_ensure_brain_path`` only mints a temp brain when
    ``NUCLEUS_BRAIN_PATH`` is UNSET; when the operator's shell exports it (e.g.
    ``…/.brain``) the suite would otherwise SHARE and WRITE the production brain,
    corrupting it and making 3-4 assertions (single-envelope / single-engram
    counts) fail. This fixture overrides UNCONDITIONALLY so the suite is hermetic
    in a clean env AND under an ambient production pin alike. Autouse + running
    after conftest's fixture means our value always wins at test-body time.
    """
    brain = tmp_path / ".brain"
    (brain / "relay").mkdir(parents=True, exist_ok=True)
    (brain / "engrams").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Neutralize the two resolution layers that sit ABOVE the env var in
    # get_brain_path(): the tenant ContextVar (conftest clears it, belt-and-
    # suspenders here) and NUCLEUS_PROJECT_SPINE project detection — so no ambient
    # tenant pin or project-spine flag can redirect the write away from our tmp.
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    try:
        from mcp_server_nucleus.runtime.common import set_tenant_brain_path

        set_tenant_brain_path(None)
    except Exception:
        pass
    return brain


@pytest.fixture(scope="session")
def _cwd_worktree(tmp_path_factory) -> Path:
    """A real git worktree, created once, for the CWD guard below."""
    import subprocess

    repo = tmp_path_factory.mktemp("dispatch_cwd_worktree")
    q = {"cwd": repo, "capture_output": True}
    subprocess.run(["git", "init"], **q)
    subprocess.run(["git", "config", "user.email", "t@t.invalid"], **q)
    subprocess.run(["git", "config", "user.name", "t"], **q)
    (repo / "seed.txt").write_text("seed")
    subprocess.run(["git", "add", "."], **q)
    subprocess.run(["git", "commit", "-m", "seed"], **q)
    return repo


@pytest.fixture(autouse=True)
def _force_git_cwd(_cwd_worktree, monkeypatch):
    """CWD GUARD — pin the working directory to a real git worktree.

    ``artifact_ref`` is stamped unconditionally from ``_read_worktree_head_sha()``,
    which shells out to git in the CURRENT WORKING DIRECTORY. When CWD is not a
    git worktree that returns None and ``dispatch_and_capture`` FAILS CLOSED —
    correctly, per PRINCIPAL v3 line 77 (no SHA = no qualifying increment) — so
    no relay envelope is written and every ``len(envelopes) == 1`` assertion in
    this module collapses to ``assert 0 == 1``.

    Isolated runs happened to pass because CWD was the repo. Under the FULL
    suite another module leaves CWD in a non-git tmp dir, and five tests here
    failed on 2026-07-31 for that reason alone. The pollution predates this
    module; making the stamp unconditional is what turned it from harmless into
    fatal. Pin CWD rather than weaken the fail-closed guarantee.

    Deliberately a REAL git repo, not a monkeypatched ``_read_worktree_head_sha``
    — stubbing the reader here would hollow out the very code path these tests
    exist to exercise.
    """
    monkeypatch.chdir(_cwd_worktree)


def _brain() -> Path:
    return Path(os.environ["NUCLEUS_BRAIN_PATH"])


def _relay_envelopes(brain: Path):
    """All parsed vendor capture envelopes on disk (body JSON with a 'vendor')."""
    out = []
    relay = brain / "relay"
    if not relay.exists():
        return out
    for f in relay.rglob("*.json"):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            body = msg.get("body")
            parsed = json.loads(body) if isinstance(body, str) else body
        except Exception:
            continue
        if isinstance(parsed, dict) and "vendor" in parsed:
            out.append((msg, parsed))
    return out


def _engram_lines(brain: Path):
    hist = brain / "engrams" / "history.jsonl"
    if not hist.exists():
        return []
    return [json.loads(l) for l in hist.read_text().splitlines() if l.strip()]


# ── flag predicate ─────────────────────────────────────────────────────────────
def test_cross_vendor_enabled_flag(monkeypatch):
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    assert vd.cross_vendor_enabled() is False
    for truthy in ("1", "true", "YES", "on"):
        monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", truthy)
        assert vd.cross_vendor_enabled() is True
    for falsy in ("0", "false", "", "no"):
        monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", falsy)
        assert vd.cross_vendor_enabled() is False


# ── dispatch → capture writes an artifact_refs envelope ─────────────────────────
def test_dispatch_capture_writes_envelope(fake_bin, monkeypatch):
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")  # prove the gate passes

    brain = _brain()
    ref = "a1b2c3d4e5f6 (commit)"
    prompt = "please review the change"
    out = vd.dispatch_and_capture(
        "agy", prompt, ref, to_role="peer", timeout_s=10, budget_usd=0.0,
    )

    assert out["vendor"] == "agy"
    assert out["model_family"] == "gemini"
    assert out["model_id"] == "gemini-3.1-pro-high"
    assert out["status"] == "ok"
    assert out["rc"] == 0
    assert "FAKE_VENDOR_OUTPUT_TOKEN" in out["result"]

    # relay envelope on disk, passed the STRICT gate, carries artifact_refs.
    relay = out["capture"]["relay"]
    assert relay.get("sent") is True, relay
    envelopes = _relay_envelopes(brain)
    assert len(envelopes) == 1
    _msg, body = envelopes[0]
    assert body["vendor"] == "agy"
    assert body["model"] == "gemini"
    # artifact_ref is vendor-derived (worktree HEAD SHA), never the caller's
    # `ref` — see PRINCIPAL v3 line 77 and the regression guard below.
    assert body["artifact_refs"] == [out["artifact_ref"]]
    assert out["artifact_ref"] != ref
    # This fake vendor commits nothing, so the ref is stamped and captured but
    # NON-qualifying (v3.1). The point of this test is that the CALLER'S ref is
    # discarded — that holds either way. See test_cd_chosen_sha_does_not_qualify
    # for why a non-committing dispatch must never score as an increment.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert body["status"] == "ok"
    # prompt_digest is a hash — the RAW prompt never lands in the envelope.
    assert body["prompt_digest"].startswith("sha256:")
    assert prompt not in json.dumps(_msg)

    # vendor-tagged engram appended — the store now shows the Gemini surface.
    lines = _engram_lines(brain)
    vendor_engrams = [
        r for r in lines
        if "vendor:gemini" in (r.get("snapshot", {}).get("context", ""))
    ]
    assert len(vendor_engrams) == 1
    assert "surface:antigravity" in vendor_engrams[0]["snapshot"]["context"]


# ── hanging fake-CLI → timed_out envelope (not a stall) ─────────────────────────
def test_hanging_cli_times_out(fake_bin, monkeypatch):
    _install_fake(fake_bin, "agy", _HANG_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")

    brain = _brain()
    start = time.perf_counter()
    out = vd.dispatch_and_capture(
        "agy", "hello", "deadbeef (commit)", to_role="peer", timeout_s=1, budget_usd=0.0,
    )
    elapsed = time.perf_counter() - start

    # The hard timeout must fire fast — nowhere near the fake's 30s sleep.
    assert elapsed < 15, f"dispatch stalled: {elapsed:.1f}s"
    assert out["status"] == "timed_out"
    assert out["rc"] is None

    # A timed_out run STILL produces a captured envelope, bound to the
    # vendor-derived worktree SHA (never the caller's "deadbeef (commit)").
    envelopes = _relay_envelopes(brain)
    assert len(envelopes) == 1
    _msg, body = envelopes[0]
    assert body["status"] == "timed_out"
    assert body["artifact_refs"] == [out["artifact_ref"]]
    assert body["artifact_refs"] != ["deadbeef (commit)"]


# ── prompt is identity-safe: never in the vendor process argv ───────────────────
def test_prompt_never_in_argv(fake_bin, tmp_path, monkeypatch):
    # devin uses PROMPT-FILE mode: the prompt is written to a private temp file
    # and only its PATH reaches argv. The shim reads the prompt from that file
    # (not stdin), mirroring the real devin.
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # Suppress the preamble so this test stays focused on identity-safe delivery
    # (prompt in temp file, not argv) — preamble content is covered by
    # test_preamble_prepended_by_default_prompt_file_mode.
    monkeypatch.setenv("NUCLEUS_VENDOR_PREAMBLE_DISABLED", "1")
    argv_file = tmp_path / "argv.txt"
    seen_file = tmp_path / "prompt_seen.txt"
    monkeypatch.setenv("FAKE_CLI_ARGV", str(argv_file))
    monkeypatch.setenv("FAKE_CLI_PROMPT_SEEN", str(seen_file))

    secret = "SECRET_IDENTITY_MARKER_zzz"
    out = vd.dispatch_and_capture(
        "devin", secret, "path/to/file.py", to_role="peer", timeout_s=10,
    )
    assert out["status"] == "ok"
    recorded_argv = argv_file.read_text()
    assert secret not in recorded_argv  # prompt went in a temp file, not argv
    # sanity: the vendor flags DID reach argv, including the prompt-file flag
    assert "-p" in recorded_argv
    assert "--prompt-file" in recorded_argv
    # The prompt was actually DELIVERED via the temp file (not dropped): the shim
    # read it back from the --prompt-file path. This is the reality the old stdin
    # path silently failed (real devin panicked with nothing after `--`).
    assert seen_file.read_text() == secret


# ── preamble is prepended to the prompt by default ──────────────────────────────
def test_preamble_prepended_by_default_prompt_file_mode(fake_bin, tmp_path, monkeypatch):
    """The _VENDOR_PREAMBLE is prepended to the dispatch prompt by default.

    Uses the devin prompt-file path: the shim copies the prompt-file contents
    (the full text the executor delivered) into FAKE_CLI_PROMPT_SEEN, so we can
    assert the vendor saw the preamble at the start of the prompt, followed by
    the caller's task body.
    """
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # Ensure no override/suppress env is set so the compiled-in default applies.
    monkeypatch.delenv("NUCLEUS_VENDOR_PREAMBLE", raising=False)
    monkeypatch.delenv("NUCLEUS_VENDOR_PREAMBLE_DISABLED", raising=False)
    seen_file = tmp_path / "prompt_seen.txt"
    monkeypatch.setenv("FAKE_CLI_PROMPT_SEEN", str(seen_file))

    task = "review the change"
    out = vd.dispatch_and_capture(
        "devin", task, "ref.py", to_role="peer", timeout_s=10,
    )
    assert out["status"] == "ok"
    seen = seen_file.read_text()
    # The preamble must be at the very start of the prompt the vendor received.
    assert seen.startswith(vd._VENDOR_PREAMBLE)
    # The caller's task body follows the preamble (not replaced by it).
    assert task in seen


def test_preamble_prepended_by_default_inline_argv_mode(fake_bin, tmp_path, monkeypatch):
    """The _VENDOR_PREAMBLE is prepended to the dispatch prompt by default
    (inline-argv mode). The agy shim records argv; the prompt is the inline
    value of ``-p``, so the preamble text must appear in the recorded argv."""
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.delenv("NUCLEUS_VENDOR_PREAMBLE", raising=False)
    monkeypatch.delenv("NUCLEUS_VENDOR_PREAMBLE_DISABLED", raising=False)
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("FAKE_CLI_ARGV", str(argv_file))

    task = "review the change"
    out = vd.dispatch_and_capture(
        "agy", task, "ref.py", to_role="peer", timeout_s=10,
    )
    assert out["status"] == "ok"
    recorded_argv = argv_file.read_text()
    # The preamble is the inline value of -p; its text must be in argv.
    assert vd._VENDOR_PREAMBLE in recorded_argv
    assert task in recorded_argv


# ── preamble semantic content floor (fw-1786123274) ───────────────────────────
#
# A build once delivered a _VENDOR_PREAMBLE that was structurally perfect
# (four numbered items, under char budget, correctly wired) but semantically
# empty — its content was the module's own design invariants, not behavioural
# instructions for the vendor. Every structural test passed identically
# against the wrong and the right content. This test enforces a keyword floor
# so a semantically-empty preamble fails regardless of its shape.
def test_preamble_contains_required_semantic_keywords():
    """The _VENDOR_PREAMBLE must contain the four behavioural instructions,
    not just be four numbered items of any content.

    Required keywords (one per non-negotiable):
    - FILE SCOPE: the preamble must mention file scope
    - GIT: the preamble must mention git state changes
    - REFUSE: the preamble must mention refusing to widen scope
    - REPORT: the preamble must mention honest reporting
    """
    p = vd._VENDOR_PREAMBLE.upper()
    # Each non-negotiable must be present by its key concept.
    assert "FILE SCOPE" in p, \
        "preamble must mention FILE SCOPE (non-negotiable 1)"
    assert "GIT" in p, \
        "preamble must mention GIT state changes (non-negotiable 2)"
    assert "REFUSE" in p, \
        "preamble must mention REFUSING to widen scope (non-negotiable 3)"
    assert "REPORT" in p or "HONESTLY" in p, \
        "preamble must mention honest REPORTING (non-negotiable 4)"


def test_preamble_is_not_self_descriptive():
    """The preamble must instruct the VENDOR, not describe the module.

    fw-1786123274: the vendor shipped a preamble containing the module's
    own design invariants ('FLAG-GATED, DEFAULT OFF', 'NON-INTERACTIVE',
    'artifact_ref'). Those are module properties, not vendor instructions.
    This test fails if those self-descriptive phrases appear — they are
    the signature of a semantically empty artifact that kept the shape
    but lost the intent.
    """
    p = vd._VENDOR_PREAMBLE.upper()
    forbidden = [
        "FLAG-GATED",
        "NON-INTERACTIVE",
        "ARTIFACT_REF",
        "HARD TIMEOUT",
        "DEFAULT OFF",
    ]
    for term in forbidden:
        assert term not in p, \
            f"preamble contains self-descriptive term '{term}' — " \
            f"it describes the module, not the vendor's behaviour"


# ── prompt-file temp file is unlinked after the run (success AND timeout) ────────
def test_prompt_file_unlinked_after_run(fake_bin, tmp_path, monkeypatch):
    """The 0600 prompt temp file must not outlive the subprocess — the finally
    block deletes it on the success path AND the timeout path."""
    created: list[str] = []

    def fake_mkstemp(*_a, **_k):
        path = str(tmp_path / f"promptfile_{len(created)}.txt")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        created.append(path)
        return fd, path

    monkeypatch.setattr(vd.tempfile, "mkstemp", fake_mkstemp)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    # success path: devin (prompt-file mode) returns quickly, file is cleaned up.
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    out = vd.dispatch_and_capture("devin", "hello", "ref.py", to_role="peer", timeout_s=10)
    assert out["status"] == "ok"
    assert created, "a prompt temp file should have been created"
    for p in created:
        assert not Path(p).exists(), f"temp prompt file leaked on success: {p}"
    # 0600 perms while it existed (mkstemp guarantee, asserted at creation above).

    # timeout path: the hung CLI is hard-killed, and the finally still unlinks.
    created.clear()
    _install_fake(fake_bin, "devin", _HANG_SCRIPT)
    out = vd.dispatch_and_capture("devin", "hang", "ref.py", to_role="peer", timeout_s=1)
    assert out["status"] == "timed_out"
    assert created, "a prompt temp file should have been created on the timeout path"
    for p in created:
        assert not Path(p).exists(), f"temp prompt file leaked on timeout: {p}"


# ── flag OFF ⇒ no-op: no invocation, no envelope, no engram ─────────────────────
def test_flag_off_is_noop(fake_bin, tmp_path, monkeypatch):
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    marker = tmp_path / "marker.txt"
    monkeypatch.setenv("FAKE_CLI_MARKER", str(marker))

    brain = _brain()
    code, payload = vd.dispatch_cli(
        "agy", "hello", "abc123 (commit)", to_role="peer", timeout_s=10,
    )
    assert code == 2
    assert payload["error"] == "cross_vendor_disabled"
    assert "NUCLEUS_CROSS_VENDOR=1" in payload["message"]

    # The fake CLI was NEVER invoked, and nothing was captured.
    assert not marker.exists()
    assert _relay_envelopes(brain) == []
    vendor_engrams = [
        r for r in _engram_lines(brain)
        if "vendor:" in (r.get("snapshot", {}).get("context", ""))
    ]
    assert vendor_engrams == []


# ── swarm vendor-persona hook produces an artifact_refs envelope ────────────────
def test_swarm_vendor_persona_captures(fake_bin, monkeypatch):
    # devin uses prompt-file mode; the shim reads the prompt from --prompt-file.
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")

    brain = _brain()
    artifact = vd.run_swarm_vendor_persona(
        vendor="devin", mission_id="mission-123", goal="ship the thing", step=2,
        timeout_s=10,
    )
    # Same artifact shape the mission loop builds for internal agents.
    assert artifact["agent"] == "devin"
    assert artifact["step"] == 2
    assert artifact["job_type"] == "VENDOR_CLI:swe"
    assert artifact["artifact_refs"] == [".brain/swarms/mission-123/summary.md"]
    assert artifact["vendor_status"] == "ok"

    envelopes = _relay_envelopes(brain)
    assert len(envelopes) == 1
    _msg, body = envelopes[0]
    assert body["vendor"] == "devin"
    # DELIBERATE DIVERGENCE: the swarm-side artifact above still carries the
    # mission summary path (it is bookkeeping for the mission loop), but the
    # RELAY ENVELOPE — the thing G1 crit-4 actually counts — is bound to the
    # vendor-derived worktree SHA and can no longer be set by the caller.
    assert body["artifact_refs"] != [".brain/swarms/mission-123/summary.md"]
    assert len(body["artifact_refs"]) == 1
    assert re.fullmatch(r"[0-9a-f]{40}", body["artifact_refs"][0])


# ── routing tiers are flag-gated ────────────────────────────────────────────────
def test_routing_tiers_flag_gated(monkeypatch):
    from mcp_server_nucleus.runtime.llm_client import TierRouter, LLMTier, get_llm_client

    # Flag OFF: vendor policy job types fall back to normal tiers; a forced
    # vendor tier is ignored.
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    monkeypatch.delenv("NUCLEUS_LLM_TIER", raising=False)
    assert TierRouter.route("SECOND_OPINION") not in (LLMTier.GEMINI_CLI, LLMTier.GLM_CLI)
    monkeypatch.setenv("NUCLEUS_LLM_TIER", "gemini_cli")
    assert TierRouter.route("ORCHESTRATION") != LLMTier.GEMINI_CLI  # ignored when OFF

    # Flag ON: vendor policy job types + forced vendor tier are honored.
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    assert TierRouter.route("ORCHESTRATION") == LLMTier.GEMINI_CLI  # forced honored
    monkeypatch.delenv("NUCLEUS_LLM_TIER", raising=False)
    assert TierRouter.route("SECOND_OPINION") == LLMTier.GLM_CLI
    assert TierRouter.route("ADVERSARIAL") == LLMTier.GLM_CLI
    # Existing job types are unaffected by the vendor policy map.
    assert TierRouter.route("ORCHESTRATION") == LLMTier.STANDARD

    # get_llm_client: vendor provider raises when OFF, instantiates when ON.
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    with pytest.raises(ValueError):
        get_llm_client("gemini_cli")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    client = get_llm_client("glm_cli")
    assert client.__class__.__name__ == "VendorCLILLM"
    assert client.vendor == "devin"


# ── agy CLI 1.1.1 drift: inline-argv prompt + unit'd --print-timeout ────────────
def test_agy_build_argv_inline_prompt_with_timeout_unit():
    """agy ≥1.1.1 takes the prompt as the inline value of `-p` (stdin is dead)
    and `--print-timeout` is a Go time.Duration that REQUIRES a unit (`s`)."""
    argv = vd.VENDOR_SPECS["agy"].build_argv(300, prompt="HELLO")
    assert argv == [
        "agy", "-p", "HELLO", "--print-timeout", "300s", "--dangerously-skip-permissions",
    ]


def test_agy_uses_inline_prompt_not_prompt_file():
    """agy is inline-argv mode, NOT prompt-file mode (and NOT stdin mode)."""
    agy = vd.VENDOR_SPECS["agy"]
    assert agy.uses_inline_prompt is True
    assert agy.uses_prompt_file is False


def test_devin_unchanged_prompt_file_mode():
    """Guard: devin stays on prompt-file mode (inline-argv must not leak into
    the devin path). build_argv still yields the --prompt-file form; in read
    mode --permission-mode auto is appended (fw-1786416432-1-93e8: unscoped
    read mode caused devin to refuse tool calls and silently no-op), in write
    mode --permission-mode dangerous is appended before the model flag."""
    devin = vd.VENDOR_SPECS["devin"]
    assert devin.uses_inline_prompt is False
    assert devin.uses_prompt_file is True
    argv = devin.build_argv(300, prompt_file="/tmp/prompt.txt", prompt="ignored",
                            mode="read")
    assert argv == ["devin", "-p", "--prompt-file", "/tmp/prompt.txt",
                     "--permission-mode", "dangerous", "--respect-workspace-trust", "false"]


# ── Regression tests: cold-start hardening (mode/model/expect_paths/effect) ────
# Items 1-18 + 25-26: runtime-layer coverage for the harden spec.

import re as _re

# 1. VendorSpec fields exact
def test_vendor_spec_fields_exact():
    agy = vd.VENDOR_SPECS["agy"]
    assert agy.default_model == "gemini-3.1-pro-high"
    assert agy.models[0] == "gemini-3.1-pro-high"
    assert agy.model_flag == "--model"
    assert agy.read_flags == ("--dangerously-skip-permissions",)
    assert agy.write_flags == ("--dangerously-skip-permissions",)
    devin = vd.VENDOR_SPECS["devin"]
    assert devin.default_model == "swe-2-max"
    assert devin.model == "swe"
    assert devin.models[0] == "swe-2-max"
    assert "swe-1-7" in devin.models
    assert "glm-5-2" in devin.models
    assert devin.model_flag == "--model"
    assert devin.read_flags == ("--permission-mode", "dangerous", "--respect-workspace-trust", "false")
    assert devin.write_flags == ("--permission-mode", "dangerous", "--respect-workspace-trust", "false")


# 2. build_argv agy write + read (mode-invariant)
def test_build_argv_agy_write_and_read():
    expected = ["agy", "-p", "P", "--print-timeout", "300s",
                "--dangerously-skip-permissions", "--model", "gemini-3.1-pro-high"]
    agy = vd.VENDOR_SPECS["agy"]
    assert agy.build_argv(300, prompt="P", mode="write",
                          model="gemini-3.1-pro-high") == expected
    assert agy.build_argv(300, prompt="P", mode="read",
                          model="gemini-3.1-pro-high") == expected


# 3. build_argv devin read + write
def test_build_argv_devin_read_and_write():
    devin = vd.VENDOR_SPECS["devin"]
    assert devin.build_argv(300, prompt_file="/tmp/x", mode="read",
                            model="glm-5-2") == [
        "devin", "-p", "--prompt-file", "/tmp/x",
        "--permission-mode", "dangerous", "--respect-workspace-trust", "false", "--model", "glm-5-2"]
    assert devin.build_argv(300, prompt_file="/tmp/x", mode="write",
                            model="glm-5-2") == [
        "devin", "-p", "--prompt-file", "/tmp/x",
        "--permission-mode", "dangerous", "--respect-workspace-trust", "false", "--model", "glm-5-2"]


# 4. Order/no-op guards
def test_build_argv_order_guards():
    devin = vd.VENDOR_SPECS["devin"]
    agy = vd.VENDOR_SPECS["agy"]
    # devin write: --permission-mode immediately followed by 'dangerous'
    dw = devin.build_argv(300, prompt_file="/f", mode="write", model="glm-5-2")
    i = dw.index("--permission-mode")
    assert dw[i + 1] == "dangerous"
    # devin read: --permission-mode dangerous, same as write (2026-08-18:
    # 'auto' proved insufficient -- the automatic git-porcelain write
    # detection in run() is the real read-mode safety boundary now)
    dr = devin.build_argv(300, prompt_file="/f", mode="read", model="glm-5-2")
    i = dr.index("--permission-mode")
    assert dr[i + 1] == "dangerous"
    # agy either mode: contains --dangerously-skip-permissions
    for m in ("read", "write"):
        a = agy.build_argv(300, prompt="P", mode=m, model="gemini-3.1-pro-high")
        assert "--dangerously-skip-permissions" in a
        # model_flag immediately followed by id, both LAST two tokens
        assert a[-2] == "--model"
        assert a[-1] == "gemini-3.1-pro-high"
    dw2 = devin.build_argv(300, prompt_file="/f", mode="write", model="glm-5-2")
    assert dw2[-2] == "--model"
    assert dw2[-1] == "glm-5-2"


# 5. build_argv model=None appends NO --model token
def test_build_argv_model_none_no_model_token():
    agy = vd.VENDOR_SPECS["agy"]
    argv = agy.build_argv(300, prompt="P", mode="write", model=None)
    assert "--model" not in argv
    devin = vd.VENDOR_SPECS["devin"]
    argv2 = devin.build_argv(300, prompt_file="/f", mode="read", model=None)
    assert "--model" not in argv2


# 6. normalize_mode aliases + error naming model
def test_normalize_mode_aliases_and_errors():
    assert vd.normalize_mode("build") == "write"
    assert vd.normalize_mode("review") == "read"
    assert vd.normalize_mode("readonly") == "read"
    assert vd.normalize_mode(None) == "write"
    with pytest.raises(ValueError) as exc_info:
        vd.normalize_mode("gemini-3.1-pro-high")
    assert "model" in str(exc_info.value)
    with pytest.raises(ValueError):
        vd.VENDOR_SPECS["agy"].flags_for_mode("bogus")


# 7. resolve_model defaults
def test_resolve_model_defaults():
    assert vd.resolve_model("agy", None) == "gemini-3.1-pro-high"
    assert vd.resolve_model("devin", None) == "swe-2-max"
    assert vd.resolve_model("agy", "") == "gemini-3.1-pro-high"
    # The valid GLM ID uses dashes; the old dotted spelling remains rejected.
    assert vd.resolve_model("devin", "swe-2-max") == "swe-2-max"
    assert vd.resolve_model("devin", "swe-1-7-medium") == "swe-1-7-medium"
    assert vd.resolve_model("devin", "glm-5-2") == "glm-5-2"
    with pytest.raises(ValueError):
        vd.resolve_model("devin", "glm-5.2")


# 8. resolve_model rejects unknown/cross-wired
def test_resolve_model_rejects_unknown_and_cross_wired():
    with pytest.raises(ValueError) as exc_info:
        vd.resolve_model("devin", "gpt-4")
    msg = str(exc_info.value)
    # Error message must mention the unsupported model, the vendor, and a
    # valid model ID from the allowlist (swe-2-max is the current default).
    assert "gpt-4" in msg and "devin" in msg and "swe-2-max" in msg
    with pytest.raises(ValueError) as exc_info2:
        vd.resolve_model("agy", "glm-5.2")
    assert "gemini-3.1-pro-high" in str(exc_info2.value)


# 9. Allowlist members match identity-safe pattern
def test_model_allowlist_identity_safe():
    pat = _re.compile(r"^[A-Za-z0-9._-]+$")
    for spec in vd.VENDOR_SPECS.values():
        for m in spec.models:
            assert pat.match(m), f"model id {m!r} fails identity-safe pattern"


# 10. _classify_completed
def test_classify_completed():
    assert vd._classify_completed(0, "answer") == "ok"
    assert vd._classify_completed(0, "") == "empty_output"
    assert vd._classify_completed(0, "   \n") == "empty_output"
    assert vd._classify_completed(1, "anything") == "error"


# 11. VendorCLIExecutor mode/model defaults + validation
def test_executor_mode_model_defaults_and_validation():
    ex = vd.VendorCLIExecutor("devin", "p")
    assert ex.mode == "write"
    assert ex.model == "swe-2-max"  # SWE-2 Max is the current free default
    ex2 = vd.VendorCLIExecutor("devin", "p", mode="build")
    assert ex2.mode == "write"
    with pytest.raises(ValueError):
        vd.VendorCLIExecutor("devin", "p", model="bogus")
    with pytest.raises(ValueError):
        vd.VendorCLIExecutor("devin", "p", mode="bogus")


# 12. fake CLI rc=0 + empty stdout → empty_output
def test_empty_output_classification(fake_bin, monkeypatch):
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT.replace(
        "echo \"FAKE_VENDOR_OUTPUT_TOKEN\"", ""))
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    ex = vd.VendorCLIExecutor("devin", "p", timeout_s=10)
    result = ex.run()
    assert result.status == "empty_output"
    assert result.produced_output is False
    assert result.rc == 0
    assert result.model_id == "swe-2-max"
    d = result.to_dict()
    assert d["status"] == "empty_output"
    assert d["produced_output"] is False
    assert d["model_id"] == "swe-2-max"
    assert d["model_family"] == "swe"
    assert "model" not in d  # bare 'model' key renamed to model_family


# 13. fake CLI rc=0 non-empty → ok; rc!=0 → error; hang → timed_out
def test_run_status_variants(fake_bin, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # ok
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    r = vd.VendorCLIExecutor("devin", "p", timeout_s=10).run()
    assert r.status == "ok" and r.produced_output is True
    # error
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT.replace("exit 0", "exit 1"))
    r2 = vd.VendorCLIExecutor("devin", "p", timeout_s=10).run()
    assert r2.status == "error" and r2.rc == 1
    # timed_out
    _install_fake(fake_bin, "devin", _HANG_SCRIPT)
    r3 = vd.VendorCLIExecutor("devin", "p", timeout_s=1).run()
    assert r3.status == "timed_out"
    assert r3.produced_output is False
    assert r3.model_id == "swe-2-max"  # current free default


# 14. dispatch_and_capture argv + relay body + engram tags
def test_dispatch_and_capture_argv_and_relay(fake_bin, tmp_path, monkeypatch):
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("FAKE_CLI_ARGV", str(argv_file))
    brain = _brain()
    out = vd.dispatch_and_capture("devin", "p", "src/foo.py", model=None)
    recorded = argv_file.read_text()
    assert "--model" in recorded
    assert "swe-2-max" in recorded
    # Model and ID remain separate argv tokens.
    toks = recorded.split()
    mi = toks.index("--model")
    assert toks[mi + 1] == "swe-2-max"
    assert out["mode"] == "write"
    assert out["model_id"] == "swe-2-max"
    assert out["model_family"] == "swe"
    assert out["effect"] == "unknown"
    assert out["changed_paths"] == []
    # relay body has model_id + status
    _msg, body = _relay_envelopes(brain)[0]
    assert body["model_id"] == "swe-2-max"  # current free default
    assert "status" in body
    # engram tags include model:swe-2-max and NO effect: tag
    lines = _engram_lines(brain)
    ctx = lines[-1]["snapshot"]["context"]
    assert "model:swe-2-max" in ctx
    assert "effect:" not in ctx


# 15. expect_paths effect detection
def test_expect_paths_effect(fake_bin, tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    brain = _brain()
    target = tmp_path / "target.txt"
    target.write_text("before")
    # no-touch: echo fake doesn't modify the file
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    out = vd.dispatch_and_capture("devin", "p", "ref", expect_paths=[str(target)])
    assert out["effect"] == "no_files_touched"
    assert out["changed_paths"] == []
    _msg, body = _relay_envelopes(brain)[-1]
    assert body["effect"] == "no_files_touched"
    lines = _engram_lines(brain)
    assert "effect:no_files_touched" in lines[-1]["snapshot"]["context"]
    # touch: fake that appends to the expected path
    touch_script = _PROMPT_FILE_SCRIPT.replace(
        'echo "FAKE_VENDOR_OUTPUT_TOKEN"',
        'echo appended >> "$FAKE_TOUCH_TARGET"\necho "FAKE_VENDOR_OUTPUT_TOKEN"')
    _install_fake(fake_bin, "devin", touch_script)
    monkeypatch.setenv("FAKE_TOUCH_TARGET", str(target))
    out2 = vd.dispatch_and_capture("devin", "p", "ref", expect_paths=[str(target)])
    assert out2["effect"] == "files_touched"
    assert out2["changed_paths"] == [str(target)]


# 16. no expect_paths → _snapshot_paths returns {} (ZERO fs work)
def test_no_expect_paths_zero_stat(monkeypatch, fake_bin):
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)


# 16a. in-place edit with same file size is detected via content hash (issue #682)
def test_expect_paths_inplace_edit_detected(fake_bin, tmp_path, monkeypatch):
    """In-place edit with same file size should be detected (issue #682).

    The old mtime/size comparison missed this because:
    - Same byte count → size unchanged
    - Rapid edit → mtime may not change within filesystem granularity
    Content hash catches it.
    """
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    target = tmp_path / "target.txt"
    # Write 5 chars, will be replaced with 5 different chars (same size)
    target.write_text("aaaaa")
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    # no-touch first
    out = vd.dispatch_and_capture("devin", "p", "ref", expect_paths=[str(target)])
    assert out["effect"] == "no_files_touched"
    # in-place edit: replace "aaaaa" with "bbbbb" (same file size)
    touch_script = _PROMPT_FILE_SCRIPT.replace(
        'echo "FAKE_VENDOR_OUTPUT_TOKEN"',
        'printf "bbbbb" > "$FAKE_TOUCH_TARGET"\necho "FAKE_VENDOR_OUTPUT_TOKEN"')
    _install_fake(fake_bin, "devin", touch_script)
    monkeypatch.setenv("FAKE_TOUCH_TARGET", str(target))
    out2 = vd.dispatch_and_capture("devin", "p", "ref", expect_paths=[str(target)])
    assert out2["effect"] == "files_touched", (
        f"In-place edit with same size should be detected. Got effect={out2['effect']!r}"
    )
    assert out2["changed_paths"] == [str(target)]


# 16b. empty expect_paths list doesn't cause effect:unknown (issue #682)
def test_empty_expect_paths_list(fake_bin, tmp_path, monkeypatch):
    """Empty expect_paths list should not cause effect:unknown (issue #682).

    The old `if pre:` check failed on empty dict, leaving effect='unknown'.
    Now `if expect_paths:` correctly skips when the list is empty.
    """
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    # Empty list should give effect='unknown' (no paths to check)
    out = vd.dispatch_and_capture("devin", "p", "ref", expect_paths=[])
    assert out["effect"] == "unknown"
    assert out["changed_paths"] == []
    # None should also give effect='unknown'
    out2 = vd.dispatch_and_capture("devin", "p", "ref", expect_paths=None)
    assert out2["effect"] == "unknown"


# 16c. no expect_paths → _snapshot_paths returns {} (ZERO fs work)
def test_no_expect_paths_zero_stat(monkeypatch, fake_bin):
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # _snapshot_paths(None) must return {} without opening any files
    called = {"n": 0}
    real_open = builtins.open

    def counting_open(p, *a, **k):
        called["n"] += 1
        return real_open(p, *a, **k)

    monkeypatch.setattr("builtins.open", counting_open)
    assert vd._snapshot_paths(None) == {}
    assert called["n"] == 0
    # dispatch_and_capture with no expect_paths returns effect 'unknown'
    out = vd.dispatch_and_capture("devin", "p", "ref")
    assert out["effect"] == "unknown"


# 17. dispatch_cli exit codes
def test_dispatch_cli_exit_codes(fake_bin, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    brain = _brain()
    # rc0-empty → exit 1
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT.replace(
        'echo "FAKE_VENDOR_OUTPUT_TOKEN"', ''))
    code, out = vd.dispatch_cli("devin", "p", "ref", timeout_s=10)
    assert code == 1
    assert out["status"] == "empty_output"
    # exactly ONE relay envelope
    assert len(_relay_envelopes(brain)) == 1
    # status ok but effect no_files_touched → exit 1 (monkeypatch the funnel)
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)

    def _fake_dac(*a, **k):
        return {"status": "ok", "effect": "no_files_touched", "result": "x",
                "capture": {"relay": {"sent": True}}}

    monkeypatch.setattr(vd, "dispatch_and_capture", _fake_dac)
    code2, out2 = vd.dispatch_cli("devin", "p", "ref", timeout_s=10)
    assert code2 == 1
    assert out2["effect"] == "no_files_touched"
    # flag OFF → exit 2 unchanged
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vendor_dispatch._onboard_config_enabled",
        lambda: False,
    )
    code3, out3 = vd.dispatch_cli("devin", "p", "ref")
    assert code3 == 2


# 18. back-compat: no new kwargs still works, argv carries --model + write flags
def test_back_compat_no_new_kwargs(fake_bin, tmp_path, monkeypatch):
    _install_fake(fake_bin, "devin", _PROMPT_FILE_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("FAKE_CLI_ARGV", str(argv_file))
    out = vd.dispatch_and_capture("devin", "p", "ref")
    recorded = argv_file.read_text()
    assert "--model" in recorded
    assert "swe-2-max" in recorded  # current free default
    assert "--permission-mode" in recorded
    assert "dangerous" in recorded
    # returned dict is a superset of the old shape
    for k in ("vendor", "model_family", "model_id", "rc", "status", "result",
              "produced_output", "duration", "prompt_digest", "artifact_ref",
              "to", "mode", "effect", "changed_paths", "capture"):
        assert k in out, f"missing key {k!r}"


# 25. Doctrine grep guard
def test_doctrine_no_too_conversational():
    src = vd.__file__
    # Check the tools/vendor_delegate.py source (not runtime)
    tool_src = vd.__file__.replace("runtime/vendor_dispatch", "tools/vendor_delegate")
    with open(tool_src) as f:
        assert "too conversational" not in f.read()


# 26. Existing green tests still pass — covered by the tests above + existing
# suite. Here we assert the capture body family key is retained.
def test_capture_body_family_key_retained(fake_bin, monkeypatch):
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")
    brain = _brain()
    vd.dispatch_and_capture("agy", "p", "ref", to_role="peer", timeout_s=10)
    _msg, body = _relay_envelopes(brain)[0]
    assert body["model"] == "gemini"  # family key retained in capture body


# ── secret hygiene: vendor OUTPUT is best-effort redacted before store/return ──
_SECRET_ECHO_SCRIPT = """#!/bin/sh
cat > /dev/null
echo "leaked: Bearer sk-abcd1234efgh5678ijkl and token=supersecretvalue123 done"
exit 0
"""


def test_redact_secrets_patterns():
    # Assemble sample secrets from parts so no literal high-entropy token appears
    # verbatim in this source (keeps the repo pre-commit secret-scanner quiet; the
    # redactor sees the concatenated value at runtime).
    bearer = "abcDEF" + "123456" + "ghijKLMN"
    jwt = "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "zzzz"
    sk = "sk-" + "ABCDEFGH12345678IJKL"
    aws = "AKIA" + "IOSFODNN7EXAMPLE"
    gh = "ghp_" + ("A" * 36)
    api = "hunter2" + "secretlong"
    red, n = vd._redact_secrets(
        f"Authorization: Bearer {bearer}\njwt {jwt}\nkey {sk}\n"
        f"aws {aws}\ngh {gh}\napi_key = {api}\n"
    )
    assert n >= 5
    for leak in (bearer, jwt, sk, aws, gh, api):
        assert leak not in red, leak
    assert "<REDACTED" in red


def test_redact_secrets_leaves_normal_text():
    code = "def add(a, b):\n    return a + b  # nothing secret here at all\n"
    red, n = vd._redact_secrets(code)
    assert n == 0 and red == code


def test_redact_secrets_empty_and_none():
    assert vd._redact_secrets("") == ("", 0)
    assert vd._redact_secrets(None) == (None, 0)


def test_run_redacts_vendor_output(fake_bin):
    _install_fake(fake_bin, "agy", _SECRET_ECHO_SCRIPT)
    res = vd.VendorCLIExecutor("agy", "diagnose", timeout_s=10).run()
    assert res.status == "ok"
    assert res.redacted > 0
    assert "sk-abcd1234efgh5678ijkl" not in res.result
    assert "supersecretvalue123" not in res.result
    assert "<REDACTED" in res.result
    d = res.to_dict()
    assert d["redacted"] == res.redacted
    assert "sk-abcd1234efgh5678ijkl" not in d["result"]


def test_run_clean_output_zero_redactions(fake_bin):
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    res = vd.VendorCLIExecutor("agy", "hi", timeout_s=10).run()
    assert res.status == "ok" and res.redacted == 0
    assert res.produced_output is True
    assert res.to_dict()["redacted"] == 0


# ── v3 anchor precondition: vendor-derived artifact_ref ───────────────────────


# A fake vendor that actually PRODUCES an increment: it commits in its cwd.
# Required for a `vendor_derived` ref as of v3.1 — a ref only qualifies when
# HEAD moved while the vendor ran, so a non-committing fake can no longer mint
# a causal edge just by standing in a git repo.
_COMMITTING_SCRIPT = """#!/bin/sh
cat > /dev/null
echo "increment" >> vendor_work.txt
git add vendor_work.txt >/dev/null 2>&1
git commit -m "vendor increment" >/dev/null 2>&1
echo "FAKE_VENDOR_OUTPUT_TOKEN"
exit 0
"""


def _init_repo(tmp_path, name="worktree"):
    """A temp git repo with one commit, returned as a Path."""
    import subprocess
    repo = tmp_path / name
    repo.mkdir()
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.email", "test@test.com"],
        ["git", "config", "user.name", "test"],
    ):
        subprocess.run(cmd, cwd=repo, capture_output=True)
    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    return repo


def test_artifact_ref_vendor_derived_stamps_worktree_sha(fake_bin, monkeypatch, tmp_path):
    """A ref is `vendor_derived` ONLY when the vendor moved HEAD in write mode.

    The caller's artifact_ref is discarded either way (unconditional since
    2026-07-31, no env flag). v3.1 adds the before/after check: the stamp must
    name an increment the VENDOR produced, not whatever HEAD happened to be.
    """
    _install_fake(fake_bin, "agy", _COMMITTING_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)          # vendor + stamp share this cwd
    import subprocess
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    brain = _brain()
    caller_ref = "caller_provided_ref"
    out = vd.dispatch_and_capture(
        "agy", "review", caller_ref, to_role="peer", timeout_s=10, mode="write",
        expect_paths=[str(repo / "vendor_work.txt")],
    )

    # The caller's ref must NOT appear — a real 40-char SHA is stamped instead.
    assert out["artifact_ref"] != caller_ref
    assert len(out["artifact_ref"]) == 40
    assert out["artifact_ref_source"] == "vendor_derived"
    # ...and it must be the POST-dispatch SHA, i.e. HEAD genuinely moved.
    assert out["head_before"] == head_before
    assert out["head_after"] != head_before
    assert out["artifact_ref"] == out["head_after"]

    # The relay envelope must carry the vendor-derived SHA, not the caller's ref
    relay = out["capture"]["relay"]
    assert relay.get("sent") is True
    envelopes = _relay_envelopes(brain)
    assert len(envelopes) >= 1
    _msg, body = envelopes[-1]
    assert body["artifact_refs"] == [out["artifact_ref"]]
    assert caller_ref not in json.dumps(body)


def test_artifact_ref_no_expect_paths_is_unprovable(fake_bin, monkeypatch, tmp_path):
    """A write-mode dispatch that moves HEAD but supplies NO expect_paths evidence
    is NOT a qualifying increment — attribution is unprovable.

    The v3.3 intersection needs changed_paths (the pre/post snapshot the caller
    opts into via expect_paths) to attribute the moved HEAD to THIS dispatch.
    Without that evidence the instrument cannot distinguish a vendor-produced
    increment from a concurrent foreign commit, so it fails closed with
    ``attribution_unprovable``. The envelope is still captured and relayed
    (visible and uncountable, not hidden). This is the permanent guard mirroring
    the inverted attribution test above — the same committing vendor, the same
    repo setup, the ONLY difference is the absent expect_paths argument.
    """
    _install_fake(fake_bin, "agy", _COMMITTING_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)          # vendor + stamp share this cwd
    import subprocess
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    _brain()
    out = vd.dispatch_and_capture(
        "agy", "review", "caller_provided_ref",
        to_role="peer", timeout_s=10, mode="write",
        # NO expect_paths — the only difference from the sibling test above.
    )

    # HEAD genuinely moved (the committing vendor ran), but without path
    # evidence the increment cannot be attributed to this dispatch.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "attribution_unprovable"
    assert out["head_after"] != head_before
    # Still captured and relayed — labelled, not suppressed.
    assert out["capture"]["relay"].get("sent") is True


@pytest.mark.parametrize(
    "mode,expected_reason",
    [("read", "read_mode_no_increment"), ("write", "head_unchanged")],
)
def test_cd_chosen_sha_does_not_qualify(
    fake_bin, monkeypatch, tmp_path, mode, expected_reason
):
    """THE ATTACK CONTROL. Standing in a git repo must not mint a causal edge.

    Removing ``--artifact-ref`` closed the path where a caller TYPES the SHA. It
    did not close the path where a caller CHOOSES it: the stamp read ambient
    HEAD in the dispatching process's cwd, and the vendor inherits that cwd. So
    ``cd <outside-labelled repo>`` + 25 free read-only dispatches satisfied
    crit-3 with no commit, no edit and no repo-mint.

    Both halves of the pair must be non-qualifying: a read-mode dispatch makes
    no increment by definition, and a write-mode dispatch that commits nothing
    leaves HEAD exactly where it was. The envelope is still captured and still
    carries the SHA — it is visible and uncountable, not hidden.
    """
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)      # NON-committing vendor
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)
    _brain()

    out = vd.dispatch_and_capture(
        "agy", "look around", "ignored_caller_ref",
        to_role="peer", timeout_s=10, mode=mode,
    )

    assert out["status"] == "ok", out                  # the dispatch SUCCEEDED
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == expected_reason
    assert out["head_before"] == out["head_after"]     # nothing was produced
    # Still captured — labelling closes the hole; suppressing capture would
    # have closed the relay pathway instead (it broke 9 tests when tried).
    assert out["capture"]["relay"] is not None
    assert out["capture"]["relay"].get("sent") is True


def test_artifact_ref_vendor_derived_fails_closed_without_git(monkeypatch):
    """When git is unavailable the capture fails closed — no artifact_ref = no
    qualifying increment. It must NEVER fall back to the caller's value."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    # Mock _read_worktree_head_sha to return None (git unavailable)
    monkeypatch.setattr(vd, "_read_worktree_head_sha", lambda: None)

    out = vd.dispatch_and_capture(
        "agy", "review", "caller_ref", to_role="peer", timeout_s=1,
    )

    # Fail closed: no artifact_ref, no capture
    assert out["artifact_ref"] is None
    assert out["artifact_ref_source"] == "vendor_derived_failed"
    assert out["capture"]["relay"] is None
    assert out["capture"]["error"] == "worktree_sha_unavailable"


def test_artifact_ref_caller_input_is_discarded_with_no_flag_set(fake_bin, monkeypatch):
    """REGRESSION GUARD. This test previously asserted the OPPOSITE: that with
    NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED unset the caller's artifact_ref was
    used as-is. That behaviour violated PRINCIPAL v3 line 77 — it let whoever
    was being measured hand-write the binding that G1 crit-4 reads as proof an
    increment was cross-vendor coordinated. The flag was removed on 2026-07-31
    and this test inverted to pin the invariant it should always have guarded:

        caller-supplied artifact_ref is discarded, with NO flag set.

    If this test ever needs an env var to pass, the flag has been reintroduced
    and the guarantee is configuration again, not code shape.
    """
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # No artifact-ref env var exists any more, and none is set here.

    sentinel_sha = "a" * 40
    monkeypatch.setattr(vd, "_read_worktree_head_sha", lambda: sentinel_sha)

    brain = _brain()
    caller_ref = "caller_provided_ref_123"
    out = vd.dispatch_and_capture(
        "agy", "review", caller_ref, to_role="peer", timeout_s=10,
    )

    assert out["artifact_ref"] == sentinel_sha
    assert out["artifact_ref"] != caller_ref
    # The stub returns the SAME sentinel before and after the dispatch, so HEAD
    # did not move and the ref is NON-qualifying under v3.1. That is correct and
    # is exactly the property being asserted elsewhere: a stable HEAD cannot
    # mint an increment. What this test guards is narrower and unchanged — the
    # caller's string is discarded no matter what the stamp resolves to.
    assert out["artifact_ref_source"] == "no_vendor_increment"
    assert out["artifact_ref_nonqualifying_reason"] == "head_unchanged"

    # And the caller's string must not survive anywhere in the envelope.
    envelopes = _relay_envelopes(brain)
    assert len(envelopes) >= 1
    _msg, body = envelopes[-1]
    assert body["artifact_refs"] == [sentinel_sha]
    assert caller_ref not in json.dumps(body)


# ── stale-local-checkout guard (2026-08-04 incident) ──────────────────────────
# A scout + build pair operated on a worktree 22 commits behind origin/main;
# the scout "found" an already-fixed bug, the build "fixed" it again, and the
# diff would have silently reverted merged upstream work. The guard stamps
# `local_head_behind_upstream` on every dispatch and warns when the count > 0.
# These tests mock `_count_behind_upstream` directly (the helper's own
# subprocess contract is exercised by the real-git integration below) so they
# isolate the dispatch-and-capture wiring: stamping both return paths, the
# warning, and the never-fatal contract.


def _behind_stub(monkeypatch, value):
    """Patch `_count_behind_upstream` to return ``value`` (int or None)."""
    monkeypatch.setattr(vd, "_count_behind_upstream", lambda *a, **k: value)


def test_local_head_behind_upstream_stamps_count_and_warns(
    fake_bin, monkeypatch, caplog,
):
    """Behind by N -> local_head_behind_upstream == N and a warning is logged."""
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    _behind_stub(monkeypatch, 22)

    out = vd.dispatch_and_capture(
        "agy", "scout the code", "ignored_ref", to_role="peer", timeout_s=10,
    )

    assert out["status"] == "ok", out
    assert out["local_head_behind_upstream"] == 22
    # The actionable signal: a warning naming the count and the stale-code risk.
    warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "behind" in r.getMessage()
    ]
    assert len(warnings) == 1, [r.getMessage() for r in caplog.records]
    msg = warnings[0].getMessage()
    assert "22" in msg
    assert "stale" in msg.lower()


def test_local_head_behind_upstream_zero_no_warning(
    fake_bin, monkeypatch, caplog,
):
    """Up to date (0 behind) -> local_head_behind_upstream == 0, no warning."""
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    _behind_stub(monkeypatch, 0)

    out = vd.dispatch_and_capture(
        "agy", "scout the code", "ignored_ref", to_role="peer", timeout_s=10,
    )

    assert out["status"] == "ok", out
    assert out["local_head_behind_upstream"] == 0
    warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "behind" in r.getMessage()
    ]
    assert warnings == []


def test_local_head_behind_upstream_none_when_no_upstream(
    fake_bin, monkeypatch, caplog,
):
    """No upstream configured -> local_head_behind_upstream is None, no crash."""
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    _behind_stub(monkeypatch, None)

    out = vd.dispatch_and_capture(
        "agy", "scout the code", "ignored_ref", to_role="peer", timeout_s=10,
    )

    assert out["status"] == "ok", out
    assert out["local_head_behind_upstream"] is None
    warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "behind" in r.getMessage()
    ]
    assert warnings == []


# ── rebase/merge-in-progress guard (fw-1785838722) ─────────────────────────
# A vendor dispatch subprocess shares the MCP server process's cwd; a stale,
# unrelated interactive rebase left in .git/rebase-merge/ was misread as
# something to resolve, staging unrelated files. `_rebase_or_merge_in_progress`
# is a best-effort signal (mirrors `_count_behind_upstream`'s contract) that
# dispatch_and_capture warns on before the vendor runs.

def _rebase_stub(monkeypatch, value):
    monkeypatch.setattr(vd, "_rebase_or_merge_in_progress", lambda *a, **k: value)


def test_rebase_in_progress_warns(fake_bin, monkeypatch, caplog):
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    _behind_stub(monkeypatch, 0)
    _rebase_stub(monkeypatch, "rebase")

    out = vd.dispatch_and_capture(
        "agy", "scout the code", "ignored_ref", to_role="peer", timeout_s=10,
    )

    assert out["status"] == "ok", out
    warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "in-progress" in r.getMessage()
    ]
    assert len(warnings) == 1, [r.getMessage() for r in caplog.records]
    assert "rebase" in warnings[0].getMessage()


def test_no_rebase_in_progress_no_warning(fake_bin, monkeypatch, caplog):
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    _behind_stub(monkeypatch, 0)
    _rebase_stub(monkeypatch, None)

    out = vd.dispatch_and_capture(
        "agy", "scout the code", "ignored_ref", to_role="peer", timeout_s=10,
    )

    assert out["status"] == "ok", out
    warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "in-progress" in r.getMessage()
    ]
    assert warnings == []


def test_rebase_or_merge_in_progress_detects_real_rebase_dir(tmp_path):
    """Integration: a real .git/rebase-merge/ directory is detected without
    mocking (exercises the actual `git rev-parse --git-path` subprocess)."""
    import subprocess as sp
    repo = tmp_path / "repo"
    repo.mkdir()
    sp.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".git" / "rebase-merge").mkdir()

    assert vd._rebase_or_merge_in_progress(cwd=str(repo)) == "rebase"


def test_rebase_or_merge_in_progress_none_when_clean(tmp_path):
    import subprocess as sp
    repo = tmp_path / "repo"
    repo.mkdir()
    sp.run(["git", "init", "-q"], cwd=repo, check=True)

    assert vd._rebase_or_merge_in_progress(cwd=str(repo)) is None


def test_local_head_behind_upstream_none_on_git_failure_dispatch_succeeds(
    fake_bin, monkeypatch, caplog,
):
    """Git command failure / not a git repo -> None, no crash, dispatch ok.

    Also covers the fail-closed return path: when `_read_worktree_head_sha`
    returns None the dispatch still stamps `local_head_behind_upstream`, so
    the field is present on BOTH return paths (the timeout_s echo-back pattern).
    """
    _install_fake(fake_bin, "agy", _ECHO_SCRIPT)
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    _behind_stub(monkeypatch, None)
    # Force the fail-closed path: no git SHA -> no qualifying increment.
    monkeypatch.setattr(vd, "_read_worktree_head_sha", lambda *a, **k: None)

    out = vd.dispatch_and_capture(
        "agy", "scout the code", "caller_ref", to_role="peer", timeout_s=10,
    )

    # Fail-closed: no artifact_ref, no capture — but the dispatch did not
    # raise, and the stale-checkout field is still stamped.
    assert out["artifact_ref"] is None
    assert out["artifact_ref_source"] == "vendor_derived_failed"
    assert out["local_head_behind_upstream"] is None
    warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "behind" in r.getMessage()
    ]
    assert warnings == []


# ── _record_dispatch_health precondition exclusions ───────────────────────────
# not_found / budget_rejected / prompt_too_large are pre-dispatch rejections:
# the model never ran, so its health state must not move. Recording them as
# failures would push a healthy model into cooldown for caller/environment
# problems. See _record_dispatch_health docstring.
@pytest.mark.parametrize("status", ["not_found", "budget_rejected", "prompt_too_large"])
def test_record_dispatch_health_excludes_preconditions(status):
    """Pre-dispatch rejections must not be recorded as model failures."""
    from mcp_server_nucleus.runtime.model_registry import get_registry

    spec = vd.VENDOR_SPECS["devin"]
    result = vd.VendorResult(
        vendor="devin", model=spec.model, rc=None, status=status,
        result="pre-dispatch rejection", duration=0.0,
        model_id=spec.default_model,
    )
    registry = get_registry()
    # Ensure a clean slate for this model key so we can assert no movement.
    key = registry._key(spec.vendor, spec.default_model)
    registry._models.pop(key, None)

    vd._record_dispatch_health(spec, result)

    health = registry.get(spec.vendor, spec.default_model)
    # Neither success nor failure was stamped — total_dispatches stays 0.
    assert health.total_dispatches == 0
    assert health.total_failures == 0
    assert health.total_successes == 0
    assert health.cooldown_until is None
    assert health.consecutive_failures == 0


def test_record_dispatch_health_records_real_failure(monkeypatch):
    """A real dispatch failure (error/empty/timed_out) IS recorded — the
    exclusion list must not swallow genuine model failures."""
    from mcp_server_nucleus.runtime.model_registry import get_registry

    spec = vd.VENDOR_SPECS["devin"]
    result = vd.VendorResult(
        vendor="devin", model=spec.model, rc=1, status="error",
        result="boom", duration=1.0, model_id=spec.default_model,
    )
    registry = get_registry()
    key = registry._key(spec.vendor, spec.default_model)
    registry._models.pop(key, None)

    vd._record_dispatch_health(spec, result)

    health = registry.get(spec.vendor, spec.default_model)
    assert health.total_dispatches == 1
    assert health.total_failures == 1
    assert health.consecutive_failures == 1


def test_record_dispatch_health_records_success():
    """A successful dispatch clears cooldown and stamps a success."""
    from mcp_server_nucleus.runtime.model_registry import get_registry

    spec = vd.VENDOR_SPECS["agy"]
    result = vd.VendorResult(
        vendor="agy", model=spec.model, rc=0, status="ok",
        result="real output", duration=2.0, model_id=spec.default_model,
    )
    registry = get_registry()
    key = registry._key(spec.vendor, spec.default_model)
    registry._models.pop(key, None)

    vd._record_dispatch_health(spec, result)

    health = registry.get(spec.vendor, spec.default_model)
    assert health.total_dispatches == 1
    assert health.total_successes == 1
    assert health.cooldown_until is None
