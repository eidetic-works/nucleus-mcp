"""Org-feature tests: register_session extension, org_delegate, audit_token_cost.

One file for the whole org-v1 feature so related tests stay co-located. 3A
nominated `tests/test_orchestrator.py` which does not exist in this repo —
`test_org.py` is the new home the design-owner picked on the way down.

Covers:
  - register_session backward-compat (legacy 2-arg call unchanged)
  - register_session with new role/tier/charter_path/parent_session kwargs
  - register_session raises ValueError on invalid tier or role/tier mismatch
  - registry iteration correctly filters legacy `current` magic key
  - assemble_prompt loads charter + merges brief + returns metadata
  - assemble_prompt raises FileNotFoundError on missing charter
  - delegate.py CLI --dry-run path
  - audit_token_cost filters events by window, handles orphan spawns,
    tolerates malformed JSONL, emits zero-event table when empty
"""
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"

from mcp_server_nucleus.tools.orchestration import _register_session_impl, _VALID_TIERS
from mcp_server_nucleus.runtime import org_delegate


@pytest.fixture
def sessions_file(tmp_path):
    """Fresh .brain/ledger/active_sessions.json per test."""
    p = tmp_path / "ledger" / "active_sessions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def emit_spy():
    """A MagicMock standing in for _emit_event."""
    return MagicMock()


# ── register_session extension ──────────────────────────────────────────

class TestRegisterSessionExtension:

    def test_legacy_call_unchanged(self, sessions_file, emit_spy):
        """Calling with only (conversation_id, focus_area) writes a 3-field entry, no org fields, no ValueError."""
        result = _register_session_impl(
            "conv-legacy-abc12345", "refactor auth middleware",
            sessions_path=sessions_file, emit_event=emit_spy,
        )
        # handler truncates to conversation_id[:8] in the return string
        assert "conv-leg" in result
        assert "refactor auth middleware" in result
        data = json.loads(sessions_file.read_text())
        entry = data["sessions"]["conv-legacy-abc12345"]
        assert entry["focus"] == "refactor auth middleware"
        assert "tier" not in entry and "role" not in entry
        emit_spy.assert_called_once()
        _, emitter, payload = emit_spy.call_args.args
        assert emitter == "nucleus_mcp"
        assert "tier" not in payload

    def test_with_role_tier_charter_parent(self, sessions_file, emit_spy):
        """New kwargs are merged into entry and event payload."""
        _register_session_impl(
            "conv-sonnet-123", "map facade actions",
            role="sonnet_structure", tier="sonnet",
            charter_path="docs/org/charters/sonnet_structure.md",
            parent_session="conv-opus-parent",
            sessions_path=sessions_file, emit_event=emit_spy,
        )
        entry = json.loads(sessions_file.read_text())["sessions"]["conv-sonnet-123"]
        assert entry["role"] == "sonnet_structure"
        assert entry["tier"] == "sonnet"
        assert entry["charter_path"].endswith("sonnet_structure.md")
        assert entry["parent_session"] == "conv-opus-parent"
        _, _, payload = emit_spy.call_args.args
        assert payload["tier"] == "sonnet"
        assert payload["role"] == "sonnet_structure"

    def test_invalid_tier_raises(self, sessions_file, emit_spy):
        with pytest.raises(ValueError, match="Invalid tier"):
            _register_session_impl(
                "conv-bad", "whatever", tier="foo",
                sessions_path=sessions_file, emit_event=emit_spy,
            )
        emit_spy.assert_not_called()
        assert not sessions_file.exists()

    def test_role_tier_mismatch_raises(self, sessions_file, emit_spy):
        with pytest.raises(ValueError, match="must start with tier prefix"):
            _register_session_impl(
                "conv-bad2", "whatever",
                role="sonnet_structure", tier="opus",
                sessions_path=sessions_file, emit_event=emit_spy,
            )
        emit_spy.assert_not_called()

    def test_registry_iter_skips_legacy_magic_key(self, sessions_file, emit_spy):
        """The `current` magic key has a different shape; iteration that filters `"tier" in v` must skip it."""
        sessions_file.write_text(json.dumps({
            "sessions": {
                "current": {"session_id": "abc", "focus": "legacy"},
                "old-conv-123": {"focus": "old work", "started": "2026-01-01T00:00:00+0000"},
            }
        }))
        _register_session_impl(
            "conv-new-456", "org dogfood",
            role="sonnet_behavior", tier="sonnet",
            sessions_path=sessions_file, emit_event=emit_spy,
        )
        data = json.loads(sessions_file.read_text())["sessions"]
        org_entries = {sid: v for sid, v in data.items() if "tier" in v}
        assert set(org_entries) == {"conv-new-456"}
        assert "current" in data
        assert "old-conv-123" in data

    def test_valid_tiers_set_exported(self):
        """_VALID_TIERS is the single source of truth; regressions to it are caught here."""
        assert _VALID_TIERS == {"opus", "sonnet", "haiku"}


# ── org_delegate.assemble_prompt ────────────────────────────────────────

class TestOrgDelegate:

    @pytest.fixture
    def charters_dir(self, tmp_path):
        d = tmp_path / "charters"
        d.mkdir()
        (d / "sonnet_structure.md").write_text(
            "---\nname: sonnet_structure\n---\n\nYou are S-STRUCTURE. Own code shape.\n"
        )
        return d

    def test_assemble_prompt_concats_charter_and_brief(self, charters_dir):
        prompt, meta = org_delegate.assemble_prompt(
            "sonnet_structure", "map facade actions", charters_dir=charters_dir,
        )
        assert "S-STRUCTURE" in prompt
        assert "map facade actions" in prompt
        assert "# Charter: sonnet_structure" in prompt
        assert "# Brief" in prompt
        assert meta["role"] == "sonnet_structure"
        assert meta["charter_path"].endswith("sonnet_structure.md")
        assert meta["prompt_chars"] == len(prompt)
        assert meta["brief_chars"] == len("map facade actions")

    def test_missing_charter_fails_loud(self, charters_dir):
        with pytest.raises(FileNotFoundError, match="Charter not found"):
            org_delegate.assemble_prompt(
                "sonnet_ghost", "brief", charters_dir=charters_dir,
            )

    def test_default_charters_dir_uses_cwd(self, tmp_path, monkeypatch):
        """Without explicit charters_dir, looks at cwd/docs/org/charters/<role>.md."""
        (tmp_path / "docs" / "org" / "charters").mkdir(parents=True)
        (tmp_path / "docs" / "org" / "charters" / "opus_master.md").write_text("# charter\n")
        monkeypatch.chdir(tmp_path)
        prompt, meta = org_delegate.assemble_prompt("opus_master", "brief")
        assert "# charter" in prompt
        assert "opus_master.md" in meta["charter_path"]


# ── scripts/delegate.py CLI dry-run ─────────────────────────────────────

class TestDelegateCLI:

    def test_dry_run_prints_metadata_and_prompt(self, tmp_path):
        charters_dir = tmp_path / "charters"
        charters_dir.mkdir()
        (charters_dir / "sonnet_behavior.md").write_text("You are S-BEHAVIOR.\n")
        brief_path = tmp_path / "brief.md"
        brief_path.write_text("verify CSR did not drop\n")

        script = _SCRIPTS / "delegate.py"
        result = subprocess.run(
            [sys.executable, str(script),
             "--role", "sonnet_behavior",
             "--brief", str(brief_path),
             "--charters-dir", str(charters_dir),
             "--expect-haiku-count-min", "5",
             "--commit-sha", "deadbeef0011",
             "--dry-run"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert "=== METADATA ===" in result.stdout
        assert "role: sonnet_behavior" in result.stdout
        assert "haiku_count_min: 5" in result.stdout
        assert "commit_sha: deadbeef0011" in result.stdout
        assert "=== PROMPT ===" in result.stdout
        assert "S-BEHAVIOR" in result.stdout
        assert "verify CSR did not drop" in result.stdout
        # Contract block injected into the brief (Gap 1 + Gap 6)
        assert "Contract (Opus-enforced post-return)" in result.stdout
        assert "haiku_count >= 5" in result.stdout
        assert "git show deadbeef0011:" in result.stdout

    def test_missing_charter_exits_nonzero(self, tmp_path):
        charters_dir = tmp_path / "charters"
        charters_dir.mkdir()
        brief_path = tmp_path / "brief.md"
        brief_path.write_text("x\n")
        script = _SCRIPTS / "delegate.py"
        result = subprocess.run(
            [sys.executable, str(script),
             "--role", "sonnet_ghost",
             "--brief", str(brief_path),
             "--charters-dir", str(charters_dir),
             "--expect-haiku-count-min", "5",
             "--commit-sha", "deadbeef0011"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "Charter not found" in (result.stderr + result.stdout)

    def test_missing_required_flags_exits_nonzero(self, tmp_path):
        # Both --expect-haiku-count-min and --commit-sha are required;
        # omitting either must fail loud. Safer than silent default that
        # would let Opus skip fan-out enforcement by accident.
        charters_dir = tmp_path / "charters"
        charters_dir.mkdir()
        (charters_dir / "sonnet_behavior.md").write_text("x\n")
        brief_path = tmp_path / "brief.md"
        brief_path.write_text("y\n")
        script = _SCRIPTS / "delegate.py"
        result = subprocess.run(
            [sys.executable, str(script),
             "--role", "sonnet_behavior",
             "--brief", str(brief_path),
             "--charters-dir", str(charters_dir),
             "--commit-sha", "abc"],  # missing --expect-haiku-count-min
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "expect-haiku-count-min" in (result.stderr + result.stdout)


# ── scripts/audit_token_cost.py ─────────────────────────────────────────

def _write_event(f, ev_type, role, tier, ts, prompt_chars=0, response_chars=0, duration_ms=0):
    ev = {
        "event_id": f"evt-{role}-{ev_type}",
        "timestamp": ts,
        "type": ev_type,
        "emitter": "opus_master",
        "data": {
            "role": role, "tier": tier,
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "duration_ms": duration_ms,
        },
        "description": "",
    }
    f.write(json.dumps(ev) + "\n")


class TestAuditTokenCost:

    def _load_audit(self):
        """Import audit_token_cost.py by path (it lives under scripts/, not a package)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "audit_token_cost", _SCRIPTS / "audit_token_cost.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_sums_within_window(self, tmp_path):
        audit = self._load_audit()
        events_path = tmp_path / "events.jsonl"
        now = datetime.now(timezone.utc)
        with open(events_path, "w") as f:
            _write_event(f, "agent_spawn", "sonnet_structure", "sonnet",
                         now.isoformat().replace("+00:00", "Z"), prompt_chars=4000)
            _write_event(f, "agent_return", "sonnet_structure", "sonnet",
                         (now + timedelta(seconds=10)).isoformat().replace("+00:00", "Z"),
                         response_chars=2000, duration_ms=1500)
        since = now - timedelta(hours=1)
        events, malformed = audit.read_events(events_path, since)
        assert len(events) == 2
        assert malformed == 0
        by_role = audit.summarize(events)
        s = by_role["sonnet_structure"]
        assert s["spawns"] == 1 and s["returns"] == 1 and s["orphans"] == 0
        assert s["prompt_chars"] == 4000 and s["response_chars"] == 2000
        table = audit.format_table(by_role)
        assert "sonnet_structure" in table
        assert "Total proxy tokens" in table

    def test_orphan_spawn_flagged(self, tmp_path):
        audit = self._load_audit()
        events_path = tmp_path / "events.jsonl"
        now = datetime.now(timezone.utc)
        with open(events_path, "w") as f:
            _write_event(f, "agent_spawn", "sonnet_behavior", "sonnet",
                         now.isoformat().replace("+00:00", "Z"), prompt_chars=500)
            # No matching agent_return
        events, _ = audit.read_events(events_path, now - timedelta(hours=1))
        by_role = audit.summarize(events)
        assert by_role["sonnet_behavior"]["orphans"] == 1

    def test_stale_event_outside_window_dropped(self, tmp_path):
        audit = self._load_audit()
        events_path = tmp_path / "events.jsonl"
        old = datetime.now(timezone.utc) - timedelta(days=5)
        with open(events_path, "w") as f:
            _write_event(f, "agent_spawn", "sonnet_narrative", "sonnet",
                         old.isoformat().replace("+00:00", "Z"), prompt_chars=100)
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        events, _ = audit.read_events(events_path, since)
        assert events == []

    def test_malformed_lines_counted_not_fatal(self, tmp_path):
        audit = self._load_audit()
        events_path = tmp_path / "events.jsonl"
        now = datetime.now(timezone.utc)
        with open(events_path, "w") as f:
            f.write("this is not json\n")
            f.write("{malformed but with braces\n")
            _write_event(f, "agent_spawn", "sonnet_structure", "sonnet",
                         now.isoformat().replace("+00:00", "Z"), prompt_chars=10)
        events, malformed = audit.read_events(events_path, now - timedelta(hours=1))
        assert len(events) == 1
        assert malformed == 2

    def test_empty_events_file_returns_empty_table(self, tmp_path):
        audit = self._load_audit()
        events_path = tmp_path / "events.jsonl"
        events_path.write_text("")
        events, malformed = audit.read_events(events_path, datetime.now(timezone.utc) - timedelta(hours=1))
        assert events == [] and malformed == 0
        assert "No agent_spawn" in audit.format_table({})

    def test_missing_events_file_is_graceful(self, tmp_path):
        audit = self._load_audit()
        events, malformed = audit.read_events(tmp_path / "nope.jsonl",
                                              datetime.now(timezone.utc) - timedelta(hours=1))
        assert events == [] and malformed == 0

    def test_non_org_events_ignored(self, tmp_path):
        audit = self._load_audit()
        events_path = tmp_path / "events.jsonl"
        now = datetime.now(timezone.utc)
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt-1",
                "timestamp": now.isoformat().replace("+00:00", "Z"),
                "type": "session_registered",
                "emitter": "nucleus_mcp",
                "data": {"conversation_id": "c1", "focus_area": "x"},
            }) + "\n")
        events, _ = audit.read_events(events_path, now - timedelta(hours=1))
        assert events == []

    # ─── calibration (Gap 3) ───────────────────────────────────────────

    def test_load_calibration_missing_file_returns_empty(self, tmp_path):
        audit = self._load_audit()
        assert audit.load_calibration(tmp_path / "nope.json") == {}

    def test_load_calibration_malformed_raises(self, tmp_path):
        audit = self._load_audit()
        p = tmp_path / "cal.json"
        p.write_text("{not json")
        with pytest.raises(ValueError, match="Calibration JSON malformed"):
            audit.load_calibration(p)

    def test_format_table_no_calibration_labels_uncalibrated(self):
        audit = self._load_audit()
        by_role = {"sonnet_x": {"tier": "sonnet", "spawns": 1, "returns": 1,
                                "orphans": 0, "prompt_chars": 100, "response_chars": 100,
                                "duration_ms": 0}}
        table = audit.format_table(by_role)
        assert "uncalibrated proxy" in table

    def test_format_table_with_calibration_multiplies_sonnet_only(self):
        audit = self._load_audit()
        by_role = {
            "sonnet_x": {"tier": "sonnet", "spawns": 1, "returns": 1,
                         "orphans": 0, "prompt_chars": 1000, "response_chars": 0,
                         "duration_ms": 0},
            "opus_master": {"tier": "opus", "spawns": 1, "returns": 0,
                            "orphans": 1, "prompt_chars": 1000, "response_chars": 0,
                            "duration_ms": 0},
        }
        cal = {"s_structure": {"ratio": 1.10, "status": "ok"}}
        table = audit.format_table(by_role, calibration=cal)
        # Sonnet proxy = 1000 * 0.25 = 250; calibrated = 250 * 1.10 = 275
        assert "275" in table
        # Opus stays uncalibrated even with ratio present
        assert "uncalibrated proxy" in table
        assert "calibration ratio" in table

    def test_format_table_failed_calibration_treated_as_absent(self):
        audit = self._load_audit()
        by_role = {"sonnet_x": {"tier": "sonnet", "spawns": 1, "returns": 1,
                                "orphans": 0, "prompt_chars": 100, "response_chars": 0,
                                "duration_ms": 0}}
        cal = {"s_structure": {"status": "failed", "reason": "usage field missing"}}
        table = audit.format_table(by_role, calibration=cal)
        assert "uncalibrated proxy" in table
        assert "calibration ratio" not in table
