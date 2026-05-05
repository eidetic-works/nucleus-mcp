"""Tests for mcp-server-nucleus/bin/ scripts — primitive-gate contract.

Bucket A Slice 4 promotes two shell primitives from ``scripts/`` into the
package's ``bin/`` dir: ``cc-jsonl-mirror`` (Claude Code session-tail parser)
and ``backup-brain`` (brain snapshot archiver). Both now consume env vars
exclusively — no hardcoded absolute paths, no developer-machine assumptions.

Tests assert:

- Required env vars trigger a clean exit 1 (operator misconfig) when absent.
- Source-dir-missing triggers a clean exit 1 (primitive-gate failure contract).
- Happy path produces the expected artifacts (status.json, archive copy).
- Atomic write leaves no ``.tmp`` leak on success.
- Legacy ``scripts/*`` shims exec into the promoted ``bin/`` targets so
  existing launchd plists / cron entries still work after promotion.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest


# Resolve repo paths relative to this test file — no env dependency.
# tests/ is two directories under the package root, so bin/ is at
# ``<pkg>/bin`` and the legacy shim dir is ``<repo-root>/scripts``.
_PKG_ROOT = Path(__file__).resolve().parent.parent          # mcp-server-nucleus/
_REPO_ROOT = _PKG_ROOT.parent                               # repo root
_BIN_DIR = _PKG_ROOT / "bin"
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

CC_MIRROR_BIN = _BIN_DIR / "cc-jsonl-mirror"
CC_MIRROR_SHIM = _SCRIPTS_DIR / "cc_jsonl_mirror.sh"

BACKUP_BRAIN_BIN = _BIN_DIR / "backup-brain"
BACKUP_BRAIN_SHIM = _SCRIPTS_DIR / "backup-brain.sh"


# ---------------------------------------------------------------------------
# bin/ existence + executable bit (primitive-gate surface)
# ---------------------------------------------------------------------------


def test_cc_jsonl_mirror_is_executable():
    assert CC_MIRROR_BIN.exists(), "cc-jsonl-mirror missing from bin/"
    assert os.access(CC_MIRROR_BIN, os.X_OK), "cc-jsonl-mirror not executable"


def test_backup_brain_is_executable():
    assert BACKUP_BRAIN_BIN.exists(), "backup-brain missing from bin/"
    assert os.access(BACKUP_BRAIN_BIN, os.X_OK), "backup-brain not executable"


# ---------------------------------------------------------------------------
# cc-jsonl-mirror — env contract
# ---------------------------------------------------------------------------


def _run(cmd, env):
    """Subprocess runner with minimal-env isolation.

    We strip NUCLEUS_* from the inherited env so the tests control the
    exact env contract, and we keep PATH so python3 / basic tools resolve.
    """
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("NUCLEUS_")}
    clean_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15,
    )


def test_cc_mirror_fails_without_env(tmp_path):
    """No NUCLEUS_ROOT and no NUCLEUS_CC_PROJECT_DIR → exit 1."""
    result = _run([str(CC_MIRROR_BIN)], env={})
    assert result.returncode == 1
    assert "NUCLEUS_CC_PROJECT_DIR" in result.stderr or "NUCLEUS_ROOT" in result.stderr


def test_cc_mirror_fails_when_source_missing(tmp_path):
    """NUCLEUS_CC_PROJECT_DIR set but dir does not exist → exit 1."""
    result = _run(
        [str(CC_MIRROR_BIN)],
        env={
            "NUCLEUS_CC_PROJECT_DIR": str(tmp_path / "does-not-exist"),
            "NUCLEUS_CC_STATUS_PATH": str(tmp_path / "status.json"),
        },
    )
    assert result.returncode == 1
    assert "source dir not found" in result.stderr


def test_cc_mirror_happy_path(tmp_path):
    """Fixture JSONL → status.json emitted with expected shape.

    Writes a minimal Claude Code session JSONL (last turn = assistant reply
    with a tool_use block) and asserts the status summary classifies it as
    an active session waiting on a tool.
    """
    src_dir = tmp_path / "projects" / "-fake-repo"
    src_dir.mkdir(parents=True)

    session_id = "abcd-1234"
    jsonl_path = src_dir / f"{session_id}.jsonl"

    # Two turns so the last-turn parser can walk back from EOF.
    turn_user = {
        "type": "user",
        "timestamp": "2026-04-24T00:00:00Z",
        "message": {"role": "user", "content": "hi"},
    }
    turn_assistant = {
        "type": "assistant",
        "timestamp": "2026-04-24T00:00:01Z",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
            ],
        },
    }
    jsonl_path.write_text(
        json.dumps(turn_user) + "\n" + json.dumps(turn_assistant) + "\n"
    )

    status_path = tmp_path / "out" / "status.json"
    result = _run(
        [str(CC_MIRROR_BIN)],
        env={
            "NUCLEUS_CC_PROJECT_DIR": str(src_dir),
            "NUCLEUS_CC_STATUS_PATH": str(status_path),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert status_path.exists(), "status.json not written"

    payload = json.loads(status_path.read_text())
    assert payload["active_count"] == 1
    assert session_id in payload["sessions"]
    entry = payload["sessions"][session_id]
    assert entry["in_active_window"] is True
    assert entry["is_waiting_on_tool"] is True
    assert entry["last_tool_name"] == "Bash"
    assert entry["heuristic_state"] == "waiting_on_tool"


def test_cc_mirror_no_tmp_leak(tmp_path):
    """After a successful run, no ``*.json.tmp`` artifact should remain."""
    src_dir = tmp_path / "projects" / "-fake-repo-2"
    src_dir.mkdir(parents=True)
    (src_dir / "sess.jsonl").write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "x"}}) + "\n"
    )

    status_path = tmp_path / "out" / "status.json"
    result = _run(
        [str(CC_MIRROR_BIN)],
        env={
            "NUCLEUS_CC_PROJECT_DIR": str(src_dir),
            "NUCLEUS_CC_STATUS_PATH": str(status_path),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    tmp_files = list(status_path.parent.glob("*.tmp"))
    assert tmp_files == [], f"stray tmp file(s): {tmp_files}"


def test_cc_mirror_derives_source_from_nucleus_root(tmp_path, monkeypatch):
    """When NUCLEUS_CC_PROJECT_DIR unset but NUCLEUS_ROOT set, the source dir
    is derived by replacing ``/`` with ``-`` under ``~/.claude/projects/``.

    We point HOME at tmp_path so the test is hermetic.
    """
    fake_home = tmp_path / "home"
    nucleus_root = tmp_path / "some" / "repo"
    nucleus_root.mkdir(parents=True)
    # Claude Code CLI encoding: absolute path with / replaced by -.
    project_id = str(nucleus_root).replace("/", "-")
    cc_dir = fake_home / ".claude" / "projects" / project_id
    cc_dir.mkdir(parents=True)
    # Empty project dir — mirror should still succeed (zero sessions).

    result = _run(
        [str(CC_MIRROR_BIN)],
        env={
            "HOME": str(fake_home),
            "NUCLEUS_ROOT": str(nucleus_root),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    status_path = nucleus_root / ".brain" / "cc_transcripts" / "_status.json"
    assert status_path.exists(), "derived status path not written"
    payload = json.loads(status_path.read_text())
    assert payload["active_count"] == 0
    assert payload["total_count"] == 0


# ---------------------------------------------------------------------------
# backup-brain — env contract
# ---------------------------------------------------------------------------


def test_backup_brain_fails_without_source():
    result = _run([str(BACKUP_BRAIN_BIN)], env={})
    assert result.returncode == 1
    assert "NUCLEUS_BACKUP_SOURCE" in result.stderr


def test_backup_brain_fails_without_archive(tmp_path):
    src = tmp_path / "brain"
    src.mkdir()
    result = _run(
        [str(BACKUP_BRAIN_BIN)],
        env={"NUCLEUS_BACKUP_SOURCE": str(src)},
    )
    assert result.returncode == 1
    assert "NUCLEUS_BACKUP_ARCHIVE" in result.stderr


def test_backup_brain_fails_when_source_missing(tmp_path):
    result = _run(
        [str(BACKUP_BRAIN_BIN)],
        env={
            "NUCLEUS_BACKUP_SOURCE": str(tmp_path / "no-such-brain"),
            "NUCLEUS_BACKUP_ARCHIVE": str(tmp_path / "archive"),
        },
    )
    assert result.returncode == 1
    assert "source dir not found" in result.stderr


def test_backup_brain_happy_path_without_git(tmp_path):
    """Copy source → archive when archive parent is NOT a git repo.

    Verifies the commit step is skipped cleanly (primitive-gate: must work
    on hosts without git installed or where the archive lives outside any
    git tree).
    """
    src = tmp_path / "brain"
    src.mkdir()
    (src / "hello.txt").write_text("hi")
    (src / "subdir").mkdir()
    (src / "subdir" / "nested.txt").write_text("nested")

    archive = tmp_path / "archive"

    result = _run(
        [str(BACKUP_BRAIN_BIN)],
        env={
            "NUCLEUS_BACKUP_SOURCE": str(src),
            "NUCLEUS_BACKUP_ARCHIVE": str(archive),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # cp -r src/ archive/ copies the contents of src into archive.
    assert (archive / "hello.txt").exists()
    assert (archive / "subdir" / "nested.txt").exists()
    # Without a git repo, the script prints a skip note and exits 0.
    assert "skipping commit" in result.stdout or "not a git repo" in result.stdout


def test_backup_brain_monthly_without_cloud_env(tmp_path):
    """--monthly without NUCLEUS_BACKUP_CLOUD set → skipped, exit 0."""
    src = tmp_path / "brain"
    src.mkdir()
    (src / "x").write_text("x")
    archive = tmp_path / "archive"

    result = _run(
        [str(BACKUP_BRAIN_BIN), "--monthly"],
        env={
            "NUCLEUS_BACKUP_SOURCE": str(src),
            "NUCLEUS_BACKUP_ARCHIVE": str(archive),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "NUCLEUS_BACKUP_CLOUD not set" in result.stdout
    assert (archive / "x").exists()


def test_backup_brain_monthly_writes_cloud(tmp_path):
    """--monthly with NUCLEUS_BACKUP_CLOUD set → copies to both targets."""
    src = tmp_path / "brain"
    src.mkdir()
    (src / "payload").write_text("payload")

    archive = tmp_path / "archive"
    cloud = tmp_path / "cloud"

    result = _run(
        [str(BACKUP_BRAIN_BIN), "--monthly"],
        env={
            "NUCLEUS_BACKUP_SOURCE": str(src),
            "NUCLEUS_BACKUP_ARCHIVE": str(archive),
            "NUCLEUS_BACKUP_CLOUD": str(cloud),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert (archive / "payload").exists()
    assert (cloud / "payload").exists()


# ---------------------------------------------------------------------------
# Legacy scripts/ shims — exec hop to bin/
# ---------------------------------------------------------------------------


def test_cc_mirror_shim_forwards(tmp_path):
    """scripts/cc_jsonl_mirror.sh must exec into bin/cc-jsonl-mirror.

    We assert by running the shim and confirming it produces the same
    artifact the bin/ script would — identical env contract, identical output.
    """
    assert CC_MIRROR_SHIM.exists(), "legacy shim missing"
    assert os.access(CC_MIRROR_SHIM, os.X_OK), "legacy shim not executable"

    src_dir = tmp_path / "projects" / "-fake-repo-shim"
    src_dir.mkdir(parents=True)
    (src_dir / "s.jsonl").write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "x"}}) + "\n"
    )
    status_path = tmp_path / "shim-status.json"

    result = _run(
        [str(CC_MIRROR_SHIM)],
        env={
            "NUCLEUS_CC_PROJECT_DIR": str(src_dir),
            "NUCLEUS_CC_STATUS_PATH": str(status_path),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert status_path.exists()
    payload = json.loads(status_path.read_text())
    assert payload["total_count"] == 1


def test_backup_brain_shim_forwards(tmp_path):
    """scripts/backup-brain.sh must exec into bin/backup-brain."""
    assert BACKUP_BRAIN_SHIM.exists(), "legacy shim missing"
    assert os.access(BACKUP_BRAIN_SHIM, os.X_OK), "legacy shim not executable"

    src = tmp_path / "brain"
    src.mkdir()
    (src / "file.txt").write_text("via shim")
    archive = tmp_path / "archive"

    result = _run(
        [str(BACKUP_BRAIN_SHIM)],
        env={
            "NUCLEUS_BACKUP_SOURCE": str(src),
            "NUCLEUS_BACKUP_ARCHIVE": str(archive),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert (archive / "file.txt").read_text() == "via shim"
