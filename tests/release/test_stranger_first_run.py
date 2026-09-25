"""Release gate: the stranger's first-run transcript (ADR-0043 W2, kill-list §3).

friction_killlist.md section 3 defines the ONE command a stranger runs and the
exact beats they must observe:

    pip install nucleus-mcp && nucleus init
      ✓ brain created, exit 0, no traceback, no 🚨 banner, no FutureWarnings
      ✓ a Memory self-test: remember "<seed>" then recall echoes it back
      ✓ Claude Code detected → wrote .mcp.json {"command": "nucleus-mcp"}
      ✓ two-agent demo: `nucleus relay send peer` / `nucleus relay inbox`
      Done in <60s, ≤20 lines of output.

This test encodes those beats against a REAL fresh venv + wheel install.

Split by readiness:
  * INSTALL / BOOT beats MUST pass today — they are what the smoke gate protects
    (a stranger can install the wheel and boot a working MCP server).
  * WOW beats (recall-on-screen, .mcp.json auto-write, relay CLI, ≤20 lines) are
    delivered by the separate `feat/stranger-wow` PR and kill-list item 4
    (relay CLI). They are marked xfail(strict=False) with references, so this
    file flips those beats green automatically once that work lands — and tells
    us (XPASS) the moment it does.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# A real venv + wheel install cannot fit in the 30s cap conftest.py applies to
# every unmarked test. Without this the gate errors in its fixture no matter
# what the cache does — which is exactly how it stayed dark.
pytestmark = pytest.mark.timeout(900)

from tests.release._wheel_utils import (
    cached_venv_for,
    cached_venv_is_usable,
    VENV_COMPLETE_MARKER,
    find_or_build_wheel,
    oldest_supported_python,
    repo_root_from,
    requires_python_floor,
)

WOW_PR = "feat/stranger-wow (ADR-0043 W2 kill-list items 3/4)"
SANDBOX_PATH = "/usr/bin:/bin"


class FirstRun:
    """Captured artifacts of a stranger's fresh install + `nucleus init`."""

    def __init__(self, venv_dir: Path, init_stdout: str, init_stderr: str,
                 init_rc: int, init_seconds: float, project_dir: Path,
                 sandbox_home: Path):
        self.venv_dir = venv_dir
        self.init_stdout = init_stdout
        self.init_stderr = init_stderr
        self.init_rc = init_rc
        self.init_seconds = init_seconds
        self.project_dir = project_dir
        self.sandbox_home = sandbox_home

    @property
    def nucleus(self) -> str:
        return str(self.venv_dir / "bin" / "nucleus")

    @property
    def nucleus_mcp(self) -> str:
        return str(self.venv_dir / "bin" / "nucleus-mcp")

    @property
    def output(self) -> str:
        return self.init_stdout + "\n" + self.init_stderr


def _sandbox_env(home: Path, **extra: str) -> dict:
    env = {"HOME": str(home), "PATH": SANDBOX_PATH}
    env.update(extra)
    return env


@pytest.fixture(scope="module")
def first_run() -> FirstRun:
    """Fresh venv on the oldest supported Python + wheel install + `nucleus init`.

    Honors ``$NUCLEUS_SMOKE_VENV`` (a venv that already has the wheel installed)
    to avoid a duplicate network install when the smoke script hands one off.
    """
    repo_root = repo_root_from(__file__)
    floor = requires_python_floor(repo_root / "pyproject.toml")

    tmp = Path(tempfile.mkdtemp(prefix="nucleus_firstrun_"))
    sandbox_home = tmp / "home"
    project_dir = tmp / "project"
    sandbox_home.mkdir()
    project_dir.mkdir()

    reuse = os.environ.get("NUCLEUS_SMOKE_VENV")
    if reuse and (Path(reuse) / "bin" / "nucleus").exists():
        venv_dir = Path(reuse)
    else:
        interp = oldest_supported_python(floor)
        if not interp:
            pytest.skip(f"no python >= {floor[0]}.{floor[1]} on PATH")

        wheel, reason = find_or_build_wheel(repo_root, tmp / "dist")
        if wheel is None:
            pytest.skip(reason)

        # Reuse a venv already built from THIS EXACT wheel. The key is the
        # wheel's content, so a rebuild gets a fresh venv rather than silently
        # testing the previous build.
        cached = cached_venv_for(wheel)
        if cached_venv_is_usable(cached):
            venv_dir = cached
            nucleus = str(venv_dir / "bin" / "nucleus")
            started = time.monotonic()
            proc = subprocess.run(
                [nucleus, "init"], cwd=str(project_dir), env=_sandbox_env(sandbox_home),
                capture_output=True, text=True, timeout=120,
            )
            yield FirstRun(venv_dir, proc.stdout, proc.stderr, proc.returncode,
                           time.monotonic() - started, project_dir, sandbox_home)
            if not os.environ.get("KEEP_WORKDIR"):
                shutil.rmtree(tmp, ignore_errors=True)
            return

        # Built IN PLACE, not moved into position: a venv bakes absolute paths
        # into its bin/ shebangs, so relocating it yields an entrypoint whose
        # interpreter no longer exists. Completion is recorded by a marker file.
        venv_dir = cached
        shutil.rmtree(venv_dir, ignore_errors=True)
        venv_dir.parent.mkdir(parents=True, exist_ok=True)
        rc = subprocess.run([interp, "-m", "venv", str(venv_dir)],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            pytest.skip(f"venv creation failed: {rc.stderr.strip()[:200]}")
        vpy = str(venv_dir / "bin" / "python")
        install = subprocess.run(
            [vpy, "-m", "pip", "install", "--disable-pip-version-check", "-q", str(wheel)],
            capture_output=True, text=True, timeout=900,
        )
        if install.returncode != 0:
            shutil.rmtree(venv_dir, ignore_errors=True)
            # Network-less shard: degrade to skip rather than a spurious failure.
            pytest.skip(f"wheel install failed (offline?): "
                        f"{(install.stderr or install.stdout).strip()[-300:]}")

        # Mark complete only once the install SUCCEEDED, so a killed run leaves
        # an unmarked directory that the next run rebuilds rather than trusts.
        (venv_dir / VENV_COMPLETE_MARKER).write_text("ok", encoding="utf-8")

    nucleus = str(venv_dir / "bin" / "nucleus")
    started = time.monotonic()
    proc = subprocess.run(
        [nucleus, "init"],
        cwd=str(project_dir),
        env=_sandbox_env(sandbox_home),
        capture_output=True, text=True, timeout=120,
    )
    elapsed = time.monotonic() - started

    yield FirstRun(venv_dir, proc.stdout, proc.stderr, proc.returncode,
                   elapsed, project_dir, sandbox_home)

    if not os.environ.get("KEEP_WORKDIR"):
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# MUST-PASS beats — the install/boot floor the smoke gate protects.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.release
def test_beat_install_and_init_exit_clean(first_run: FirstRun) -> None:
    """`nucleus init` exits 0 with no Python traceback and no 🚨 INSECURE banner."""
    assert first_run.init_rc == 0, (
        f"nucleus init exited {first_run.init_rc}\n"
        f"--- stdout ---\n{first_run.init_stdout[-1500:]}\n"
        f"--- stderr ---\n{first_run.init_stderr[-1500:]}"
    )
    out = first_run.output
    assert "Traceback (most recent call last)" not in out, \
        f"init emitted a Python traceback:\n{out[-1500:]}"
    assert "NameError" not in out, f"init emitted a NameError (1.8.8 cli bug):\n{out[-800:]}"
    assert "🚨 INSECURE MODE" not in out, \
        "init screamed the INSECURE-MODE banner on a normal run (kill-list item 7)"


@pytest.mark.release
def test_beat_init_creates_brain(first_run: FirstRun) -> None:
    """The brain directory is actually created (README's promised payload)."""
    brain = first_run.project_dir / ".brain"
    assert brain.is_dir(), f"nucleus init did not create {brain}"
    # A couple of the load-bearing pieces a stranger's next command needs.
    assert (brain / "ledger" / "state.json").exists()
    assert (brain / "memory" / "engrams.json").exists()


@pytest.mark.release
def test_beat_no_futurewarnings(first_run: FirstRun) -> None:
    """No dependency FutureWarnings on a supported interpreter (kill-list item 7)."""
    assert "FutureWarning" not in first_run.output, (
        "init leaked FutureWarnings (the py3.9-EOL google-cloud spam) on a "
        "supported interpreter:\n" + first_run.output[-1200:]
    )


@pytest.mark.release
def test_beat_boot_server_handshake(first_run: FirstRun) -> None:
    """The installed wheel boots a working MCP server (initialize+list+real call)."""
    probe = str(Path(__file__).parent / "mcp_stdio_probe.py")
    env = _sandbox_env(
        first_run.sandbox_home,
        NUCLEUS_BRAIN_PATH=str(first_run.project_dir / ".brain"),
    )
    vpy = str(first_run.venv_dir / "bin" / "python")
    proc = subprocess.run(
        [vpy, probe, "--", first_run.nucleus_mcp],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, (
        "MCP stdio handshake / tool call failed (1.8.8 'listed but dead' class):\n"
        + proc.stdout[-1500:] + "\n" + proc.stderr[-800:]
    )


@pytest.mark.release
def test_beat_init_completes_under_60s(first_run: FirstRun) -> None:
    """`nucleus init` itself finishes well under the 60s wall-time budget."""
    assert first_run.init_seconds < 60, \
        f"nucleus init took {first_run.init_seconds:.1f}s (>60s budget)"


# ─────────────────────────────────────────────────────────────────────────────
# WOW beats — delivered by feat/stranger-wow / relay-CLI. xfail until they land;
# XPASS is the signal to drop the xfail marker.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.release
# xfail removed 2026-09-20: it XPASSed. `nucleus init` really does print
# "✓ memory self-test: remember … recall …" (cli.py `_finish_init_with_value`).
# A marker saying a shipped feature is unshipped keeps it off the kill-list
# as unfinished work, and hides a real regression behind an expected failure.
def test_beat_init_prints_memory_self_test(first_run: FirstRun) -> None:
    """init demonstrates persistence on screen: remember → recall echoes the seed."""
    out = first_run.output
    has_remember = re.search(r"\bremember\b", out, re.IGNORECASE) is not None
    has_recall = re.search(r"\brecall\b", out, re.IGNORECASE) is not None
    # The recall line must echo back a hit count / latency, proving a round-trip.
    has_hit = re.search(r"\b1 hit\b|→\s*\"", out) is not None
    assert has_remember and has_recall and has_hit, (
        "init did not print a remember→recall self-test echoing the seed engram"
    )


@pytest.mark.release
# xfail removed 2026-09-20: it XPASSed once get_nucleus_mcp_command stopped
# falling back to the interpreter when nucleus-mcp sits beside it. init has
# auto-written .mcp.json for a while; what was missing was the entrypoint.
def test_beat_init_writes_mcp_json_config(first_run: FirstRun) -> None:
    """A config file named in the output exists and pins {"command":"nucleus-mcp"}."""
    # Search the whole sandbox HOME + project for a written MCP config.
    candidates: list[Path] = []
    for base in (first_run.project_dir, first_run.sandbox_home):
        candidates += list(base.rglob("*.mcp.json"))
        candidates += list(base.rglob("mcp*.json"))
        candidates += list(base.rglob("claude_desktop_config.json"))
    written = None
    for c in candidates:
        try:
            if '"command": "nucleus-mcp"' in c.read_text(encoding="utf-8").replace(" ", "").replace('":"', '": "'):
                written = c
                break
            if "nucleus-mcp" in c.read_text(encoding="utf-8") and "command" in c.read_text(encoding="utf-8"):
                written = c
                break
        except OSError:
            continue
    assert written is not None, (
        "init wrote no MCP config naming the nucleus-mcp entrypoint. If the "
        "command is an interpreter with [\"-m\", \"mcp_server_nucleus\"], "
        "get_nucleus_mcp_command fell through both the PATH lookup and the "
        "sibling-of-sys.executable lookup — the config will stop launching the "
        "server as soon as that interpreter moves or is rebuilt."
    )


# Any claim that something was put on the clipboard is FABRICATED BY
# CONSTRUCTION: the package contains zero clipboard-write mechanisms (measured
# 2026-09-20 — no pbcopy, xclip, xsel, wl-copy, pyperclip, or clipboard.copy
# anywhere under src/). So this does not need to guess whether a claim is true;
# any such claim is false.
#
# It used to test one exact uppercase string, "COPIED TO CLIPBOARD", which
# occurs zero times in src/ — the assertion could not fail, and its xfail
# ("clipboard claim not yet removed") described a condition that no longer
# existed, since cli.py:809 replaced that tail. A guard whose success looks
# identical to its absence is not a guard. Matching the CLAIM FAMILY rather
# than one literal is the difference between checking and appearing to check.
_CLIPBOARD_CLAIM = re.compile(
    r"copied[^.\n]{0,40}clipboard"
    r"|clipboard[^.\n]{0,25}\bcopi?(?:ed|y)\b"
    r"|\bpaste[ds]?\b[^.\n]{0,25}clipboard",
    re.IGNORECASE,
)


def fabricated_clipboard_claims(text: str) -> list[str]:
    """Every clipboard-copy claim in ``text``. Non-empty means fabrication."""
    return [m.group(0) for m in _CLIPBOARD_CLAIM.finditer(text)]


@pytest.mark.release
def test_beat_no_false_clipboard_claim(first_run: FirstRun) -> None:
    """A headless init must not claim it copied anything to the clipboard."""
    claims = fabricated_clipboard_claims(first_run.output)
    assert not claims, (
        f"init claims a clipboard copy it cannot perform: {claims}"
    )


def test_clipboard_claim_detector_fires_on_planted_output() -> None:
    """POSITIVE CONTROL. Without this the test above is indistinguishable from
    the vacuous one it replaced — both pass, neither proves anything."""
    for planted in (
        "  ✅ COPIED TO CLIPBOARD",
        "Config copied to your clipboard.",
        "Clipboard: copied the snippet",
        "Pasted to clipboard for you",
    ):
        assert fabricated_clipboard_claims(planted), f"detector missed: {planted!r}"


def test_clipboard_claim_detector_ignores_innocent_mentions() -> None:
    """NEGATIVE CONTROL. Over-broad matching would fail every run the moment
    anything merely mentioned the word, and the test would be disabled."""
    for innocent in (
        'permissions: {"clipboard": "ask"}',
        "Press Cmd-C to copy the line above.",
        "# replaces the former clipboard-claiming tail",
    ):
        assert not fabricated_clipboard_claims(innocent), f"false positive: {innocent!r}"


@pytest.mark.release
@pytest.mark.xfail(reason="relay CLI verb not shipped — kill-list item 4 (T2+T7)", strict=False)
def test_beat_relay_cli_two_agent_roundtrip(first_run: FirstRun) -> None:
    """`nucleus relay send peer` then `nucleus relay inbox` shows the message."""
    env = _sandbox_env(
        first_run.sandbox_home,
        NUCLEUS_BRAIN_PATH=str(first_run.project_dir / ".brain"),
    )
    token = "handoff_smoke_token_xyzzy"
    send = subprocess.run(
        [first_run.nucleus, "relay", "send", "peer", token],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert send.returncode == 0, f"`nucleus relay send` failed: {send.stderr[-300:]}"
    inbox = subprocess.run(
        [first_run.nucleus, "relay", "inbox"],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert inbox.returncode == 0, f"`nucleus relay inbox` failed: {inbox.stderr[-300:]}"
    assert token in inbox.stdout, "relayed message not visible in inbox"


@pytest.mark.release
@pytest.mark.xfail(reason=f"init output not yet slimmed to ≤20 lines — {WOW_PR}", strict=False)
def test_beat_init_output_at_most_20_lines(first_run: FirstRun) -> None:
    """The ideal first-run transcript is ≤20 lines of signal."""
    lines = [ln for ln in first_run.init_stdout.splitlines() if ln.strip()]
    assert len(lines) <= 20, f"init printed {len(lines)} non-blank lines (>20)"
