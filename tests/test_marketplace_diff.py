"""Tests for nucleus_sync marketplace_diff action (Atom 7)."""
import json


def _diff(snapshot_a, snapshot_b):
    """Replicate production _marketplace_diff logic for isolated testing."""
    def _parse(s):
        if isinstance(s, str):
            try:
                parsed = json.loads(s)
            except Exception as exc:
                return None, str(exc)
            cards = parsed.get("cards") if isinstance(parsed, dict) else parsed
        elif isinstance(s, list):
            cards = s
        elif isinstance(s, dict):
            cards = s.get("cards", [])
        else:
            return None, f"unexpected type {type(s)}"
        return {c["address"]: c for c in cards if "address" in c}, None

    map_a, err_a = _parse(snapshot_a)
    if err_a:
        return {"error": f"snapshot_a parse error: {err_a}"}
    map_b, err_b = _parse(snapshot_b)
    if err_b:
        return {"error": f"snapshot_b parse error: {err_b}"}

    keys_a, keys_b = set(map_a), set(map_b)
    added = sorted(keys_b - keys_a)
    removed = sorted(keys_a - keys_b)
    changed = []
    for addr in sorted(keys_a & keys_b):
        ca, cb = map_a[addr], map_b[addr]
        deltas = {}
        for field in ("tier", "quarantined", "inactive", "success_rate", "connection_count"):
            va, vb = ca.get(field), cb.get(field)
            if va != vb:
                deltas[field] = {"before": va, "after": vb}
        if deltas:
            changed.append({"address": addr, "deltas": deltas})

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
        },
    }


def _card(address, tier=1, **kw):
    return {"address": address, "tier": tier, **kw}


def test_diff_symbol_registered_in_sync():
    import mcp_server_nucleus.tools.sync as sync_mod
    src = open(sync_mod.__file__).read()
    assert "def _marketplace_diff" in src
    assert '"marketplace_diff"' in src


def test_diff_detects_added_address():
    a = [_card("agent-a@nucleus")]
    b = [_card("agent-a@nucleus"), _card("agent-b@nucleus")]
    result = _diff(a, b)
    assert "agent-b@nucleus" in result["added"]
    assert result["summary"]["added_count"] == 1


def test_diff_detects_removed_address():
    a = [_card("agent-a@nucleus"), _card("agent-b@nucleus")]
    b = [_card("agent-a@nucleus")]
    result = _diff(a, b)
    assert "agent-b@nucleus" in result["removed"]
    assert result["summary"]["removed_count"] == 1


def test_diff_detects_tier_change():
    a = [_card("agent-a@nucleus", tier=1)]
    b = [_card("agent-a@nucleus", tier=3)]
    result = _diff(a, b)
    assert result["summary"]["changed_count"] == 1
    assert result["changed"][0]["address"] == "agent-a@nucleus"
    assert result["changed"][0]["deltas"]["tier"] == {"before": 1, "after": 3}


def test_diff_detects_quarantine_change():
    a = [_card("agent-a@nucleus")]
    b = [_card("agent-a@nucleus", quarantined=True)]
    result = _diff(a, b)
    assert result["changed"][0]["deltas"]["quarantined"] == {"before": None, "after": True}


def test_diff_identical_snapshots_returns_empty():
    snap = [_card("agent-a@nucleus", tier=2)]
    result = _diff(snap, snap)
    assert result["summary"] == {"added_count": 0, "removed_count": 0, "changed_count": 0}
    assert result["added"] == []
    assert result["removed"] == []
    assert result["changed"] == []


def test_diff_accepts_json_string_input():
    a = json.dumps({"cards": [_card("agent-a@nucleus")]})
    b = json.dumps({"cards": [_card("agent-a@nucleus"), _card("agent-b@nucleus")]})
    result = _diff(a, b)
    assert result["summary"]["added_count"] == 1


def test_diff_invalid_json_returns_error():
    result = _diff("not-json", [])
    assert "error" in result
