"""Unit tests for cross-trio observability scripts.

Each test sets NUCLEUS_BRAIN_PATH to a tmp dir with seeded fixtures and asserts script
output. Stdlib-only execution path; YAML loaded via minimal parser fallback.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "observability"


def _seed_brain(tmp: Path) -> Path:
    brain = tmp / ".brain"
    (brain / "ledger").mkdir(parents=True)
    (brain / "relay" / "claude_code_main").mkdir(parents=True)
    (brain / "relay" / "claude_code_peer").mkdir(parents=True)
    (brain / "charters").mkdir(parents=True)
    return brain


def _write_relay(bucket: Path, rid: str, sender: str, sid: str, tags: list[str], created: str = "2026-05-02T01:00:00Z") -> None:
    body = json.dumps({"summary": "test", "tags": tags})
    relay = {
        "id": rid, "from": sender, "from_session_id": sid, "to": "claude_code_peer",
        "subject": "test", "body": body, "created_at": created,
    }
    (bucket / f"{rid}.json").write_text(json.dumps(relay))


def _write_taxonomy(brain: Path) -> None:
    yaml_text = """\
claude_code_main:
  description: "test main"
  permitted_tags:
    - oci
    - merge-coord
    - status
  permitted_event_types:
    - relay_fired

claude_code_peer:
  description: "test peer"
  permitted_tags:
    - coord-events
    - tier-2
  permitted_event_types:
    - relay_fired
"""
    (brain / "charters" / "scope_taxonomy.yaml").write_text(yaml_text)


def _run(script: str, tmp: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {"NUCLEUS_BRAIN_PATH": str(tmp / ".brain"), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *args],
        capture_output=True, text=True, env=env, cwd=str(tmp),
    )


def test_sender_coercion_alarm_no_incidents(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", "sess-A", ["oci"])
    _write_relay(brain / "relay" / "claude_code_peer", "r2", "claude_code_peer", "sess-B", ["coord-events"])
    res = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["count"] == 0


def test_sender_coercion_alarm_multi_sender_per_session(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    # Same session_id, two different senders that aren't the legacy upgrade
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", "sess-A", ["oci"])
    _write_relay(brain / "relay" / "claude_code_main", "r2", "windsurf", "sess-A", ["bridge"])
    res = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res.returncode == 1
    out = json.loads(res.stdout)
    assert out["count"] == 1
    assert out["incidents"][0]["type"] == "multi_sender_per_session"
    assert out["incidents"][0]["severity"] == "high"


def test_sender_coercion_alarm_legacy_upgrade_is_low(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code", "sess-A", ["status"])
    _write_relay(brain / "relay" / "claude_code_main", "r2", "claude_code_peer", "sess-A", ["coord-events"])
    res = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res.returncode == 0  # low severity = exit 0
    out = json.loads(res.stdout)
    assert out["count"] == 1
    assert out["incidents"][0]["type"] == "legacy_bare_to_role_aware"


def test_sender_coercion_alarm_sid_unknown_is_low_severity_rolled_up(tmp_path: Path) -> None:
    """Multiple agents sharing literal sid='unknown' is wiring artifact, not coercion.

    Per peer 2026-05-02: 10/27 cowork+windsurf relays in real corpus use literal 'unknown'.
    Without this carveout, alarm fires HIGH-SEV every cron run. Roll up into one low-sev.
    """
    brain = _seed_brain(tmp_path)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "cowork", "unknown", ["consult"])
    _write_relay(brain / "relay" / "claude_code_main", "r2", "windsurf", "unknown", ["bridge"])
    _write_relay(brain / "relay" / "claude_code_main", "r3", "cowork", "unknown", ["aggregate"])
    res = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res.returncode == 0  # low-sev only
    out = json.loads(res.stdout)
    assert out["count"] == 1
    inc = out["incidents"][0]
    assert inc["type"] == "unknown_session_id"
    assert inc["severity"] == "low"
    assert inc["count"] == 3
    assert "cowork" in inc["senders_observed"]
    assert "windsurf" in inc["senders_observed"]


def test_multi_envelope_session_carveout(tmp_path: Path) -> None:
    """Session in multi_envelope_sessions allow-list with multiple senders → 1 low-sev, not high-sev.

    The cc-tb training-session lane (discovered 2026-05-02) legitimately fires under both
    claude_code_main and claude_code_peer envelopes by design. Without the allow-list,
    sender_coercion_alarm.py would emit HIGH-SEV on every cron run for that sid.
    Mirrors the sid='unknown' carveout pattern shipped in PR #218.
    """
    brain = _seed_brain(tmp_path)
    cc_tb_sid = "f6b976a1-5627-47c3-a431-af7d6be2633d"
    # Write scope_taxonomy.yaml that includes the sid in multi_envelope_sessions
    yaml_text = f"""\
multi_envelope_sessions:
  - {cc_tb_sid}  # cc-tb training-session lane

claude_code_main:
  description: "test main"
  permitted_tags:
    - oci
  permitted_event_types:
    - relay_fired

claude_code_peer:
  description: "test peer"
  permitted_tags:
    - coord-events
  permitted_event_types:
    - relay_fired
"""
    (brain / "charters" / "scope_taxonomy.yaml").write_text(yaml_text)
    # Same sid, two different senders (main + peer) — legitimate multi-envelope lane
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", cc_tb_sid, ["oci"])
    _write_relay(brain / "relay" / "claude_code_peer", "r2", "claude_code_peer", cc_tb_sid, ["coord-events"])
    res = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res.returncode == 0, f"expected exit 0 (low-sev only), got {res.returncode}. stderr={res.stderr}"
    out = json.loads(res.stdout)
    assert out["count"] == 1, f"expected exactly 1 incident, got {out['count']}: {out['incidents']}"
    inc = out["incidents"][0]
    assert inc["type"] == "multi_envelope_session_carveout"
    assert inc["severity"] == "low"
    assert inc["session_id"] == cc_tb_sid
    assert "claude_code_main" in inc["senders_observed"]
    assert "claude_code_peer" in inc["senders_observed"]


def test_multi_envelope_session_with_envelope_filter(tmp_path: Path) -> None:
    """Session in multi_envelope_sessions with an explicit allowed_envelopes filter.
    
    If list form is present, senders must be a subset of the allowed envelopes.
    """
    brain = _seed_brain(tmp_path)
    filtered_sid = "test-sid-filter"
    yaml_text = f"""\
multi_envelope_sessions:
  - sid: "{filtered_sid}"
    allowed_envelopes:
      - "claude_code_main"
      - "perplexity"

claude_code_main:
  description: "test main"
  permitted_tags:
    - oci
  permitted_event_types:
    - relay_fired
"""
    (brain / "charters" / "scope_taxonomy.yaml").write_text(yaml_text)
    
    # 1. Valid sender
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", filtered_sid, ["oci"])
    # 2. Valid sender
    _write_relay(brain / "relay" / "claude_code_main", "r2", "perplexity", filtered_sid, ["cross-vendor"])
    
    res = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert out["count"] == 1
    assert out["incidents"][0]["severity"] == "low"
    assert out["incidents"][0]["type"] == "multi_envelope_session_carveout"

    # 3. Invalid sender (windsurf not in allowed_envelopes)
    _write_relay(brain / "relay" / "claude_code_main", "r3", "windsurf", filtered_sid, ["bridge"])
    
    res2 = _run("sender_coercion_alarm.py", tmp_path, "--json")
    assert res2.returncode == 1
    out2 = json.loads(res2.stdout)
    assert out2["count"] == 1
    assert out2["incidents"][0]["severity"] == "high"
    assert out2["incidents"][0]["type"] == "multi_sender_per_session"


def test_scope_drift_detector_no_drift(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_taxonomy(brain)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", "sess-A", ["oci", "status"])
    res = _run("scope_drift_detector.py", tmp_path, "--json")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["count"] == 0


def test_scope_drift_detector_off_charter_tag(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_taxonomy(brain)
    # claude_code_main using tier-2 tag (peer's lane, not in main's permitted list)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", "sess-A", ["tier-2"])
    res = _run("scope_drift_detector.py", tmp_path, "--json")
    assert res.returncode == 1
    out = json.loads(res.stdout)
    assert out["count"] == 1
    assert "tier-2" in out["drifts"][0]["off_charter_tags"]


def test_scope_drift_detector_no_charter_for_agent(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_taxonomy(brain)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "antigravity", "sess-A", ["any"])
    res = _run("scope_drift_detector.py", tmp_path, "--json")
    assert res.returncode == 0  # low severity
    out = json.loads(res.stdout)
    assert out["count"] == 1
    assert out["drifts"][0]["type"] == "no_charter_for_agent"


def test_dashboard_smoke(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_taxonomy(brain)
    _write_relay(brain / "relay" / "claude_code_main", "r1", "claude_code_main", "sess-A", ["oci"])
    # Empty coord_events
    (brain / "ledger" / "coordination_events.jsonl").write_text("")
    res = _run("cross_trio_dashboard.py", tmp_path, "--json", "--since", "2026-05-01T00:00:00Z")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert "per_agent_relay_rate_per_hour" in out
    assert out["per_agent_relay_rate_per_hour"]["claude_code_main"] > 0


def test_dashboard_ack_latency_pairs_events(tmp_path: Path) -> None:
    brain = _seed_brain(tmp_path)
    _write_taxonomy(brain)
    # Seed 1 fired + 1 processed for same relay_id
    events = [
        {"id": "coord_1", "timestamp": "2026-05-02T01:00:00.000Z", "event_type": "relay_fired",
         "agent": "claude_code_main", "session_id": "s", "context_summary": "",
         "available_options": [], "chosen_option": "relay_X", "reasoning_summary": ""},
        {"id": "coord_2", "timestamp": "2026-05-02T01:00:30.000Z", "event_type": "relay_processed",
         "agent": "claude_code_peer", "session_id": "s", "context_summary": "",
         "available_options": [], "chosen_option": "relay_X", "reasoning_summary": ""},
    ]
    (brain / "ledger" / "coordination_events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n"
    )
    res = _run("cross_trio_dashboard.py", tmp_path, "--json", "--since", "2026-05-01T00:00:00Z")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    al = out["ack_latency"]
    assert al["paired_count"] == 1
    assert al["mean_seconds"] == 30.0


def test_cross_talk_uses_taxonomy_exclusive_tags(tmp_path):
    """Tag appearing under EXACTLY ONE agent triggers cross-talk; shared tags do not.

    Validates that cross_trio_dashboard.cross_talk_rate now reads
    .brain/charters/scope_taxonomy.yaml at runtime instead of a hard-coded
    dict (dashboard v0.2 — taxonomy-driven). Edits to the YAML flow through
    without code changes.
    """
    brain = _seed_brain(tmp_path)
    # Custom taxonomy: 'oci' is main-exclusive; 'status' is shared (main+peer);
    # 'tier-2' is peer-exclusive.
    yaml_text = """\
claude_code_main:
  description: "test main"
  permitted_tags:
    - oci
    - status
  permitted_event_types:
    - relay_fired

claude_code_peer:
  description: "test peer"
  permitted_tags:
    - tier-2
    - status
  permitted_event_types:
    - relay_fired
"""
    (brain / "charters" / "scope_taxonomy.yaml").write_text(yaml_text)

    # 3 relays from main: one with main-only tag (no cross-talk), one with
    # peer-exclusive tag (CROSS-TALK), one with shared tag (no cross-talk
    # because 'status' is not exclusive to either).
    _write_relay(brain / "relay" / "claude_code_peer", "r1", "claude_code_main", "s1",
                 tags=["oci"], created="2026-05-02T01:00:00Z")
    _write_relay(brain / "relay" / "claude_code_peer", "r2", "claude_code_main", "s1",
                 tags=["tier-2"], created="2026-05-02T01:01:00Z")
    _write_relay(brain / "relay" / "claude_code_peer", "r3", "claude_code_main", "s1",
                 tags=["status"], created="2026-05-02T01:02:00Z")

    res = _run("cross_trio_dashboard.py", tmp_path, "--json", "--since", "2026-05-01T00:00:00Z")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    ct = out["cross_talk"]
    assert ct["total_relays"] == 3
    # Only r2 (peer-exclusive 'tier-2' from main) is cross-talk.
    assert ct["cross_talk_count"] == 1
    pairs = dict((tuple(p[0]), p[1]) for p in ct["top_pairs"]) if ct["top_pairs"] else {}
    assert pairs.get(("claude_code_main", "claude_code_peer")) == 1


def test_cross_talk_falls_back_when_taxonomy_missing(tmp_path):
    """No taxonomy file → cross-talk reports 0% rather than crashing."""
    brain = _seed_brain(tmp_path)
    # NO _write_taxonomy call — file absent
    _write_relay(brain / "relay" / "claude_code_peer", "r1", "claude_code_main", "s1",
                 tags=["anything"], created="2026-05-02T01:00:00Z")
    res = _run("cross_trio_dashboard.py", tmp_path, "--json", "--since", "2026-05-01T00:00:00Z")
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["cross_talk"]["cross_talk_rate"] == 0
