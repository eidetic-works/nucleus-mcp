"""Tests for nucleus_sync marketplace_subscribe/unsubscribe/subscriptions actions (Atom 8)."""
import json
from pathlib import Path


def _sub_file(tmp_path: Path) -> Path:
    d = tmp_path / "marketplace"
    d.mkdir(parents=True, exist_ok=True)
    return d / "subscriptions.jsonl"


def _write_sub(tmp_path, subscriber, target="*", event_types=None, active=True):
    import datetime
    rec = {
        "subscriber": subscriber,
        "target": target,
        "event_types": event_types or ["tier_changed", "quarantined"],
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "active": active,
    }
    with open(_sub_file(tmp_path), "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def _subscribe(subscriber, target="*", event_types=None, brain_path=None):
    import datetime
    events = event_types if isinstance(event_types, list) else ["tier_changed", "quarantined"]
    from mcp_server_nucleus.runtime.marketplace import get_brain_path as _gbp
    bp = brain_path or _gbp()
    sub_dir = bp / "marketplace"
    sub_dir.mkdir(parents=True, exist_ok=True)
    sub_file = sub_dir / "subscriptions.jsonl"
    record = {
        "subscriber": subscriber, "target": target, "event_types": events,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z", "active": True,
    }
    with open(sub_file, "a") as fh:
        fh.write(json.dumps(record) + "\n")
    return {"subscribed": True, "subscriber": subscriber, "target": target, "event_types": events}


def _unsubscribe(subscriber, target="*", brain_path=None):
    from mcp_server_nucleus.runtime.marketplace import get_brain_path as _gbp
    bp = brain_path or _gbp()
    sub_file = bp / "marketplace" / "subscriptions.jsonl"
    if not sub_file.exists():
        return {"removed": 0, "subscriber": subscriber, "target": target}
    lines = sub_file.read_text().splitlines()
    kept, removed = [], 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            kept.append(line)
            continue
        if rec.get("subscriber") == subscriber and rec.get("target") == target:
            removed += 1
        else:
            kept.append(line)
    sub_file.write_text("\n".join(kept) + ("\n" if kept else ""))
    return {"removed": removed, "subscriber": subscriber, "target": target}


def _subscriptions(subscriber=None, brain_path=None):
    from mcp_server_nucleus.runtime.marketplace import get_brain_path as _gbp
    bp = brain_path or _gbp()
    sub_file = bp / "marketplace" / "subscriptions.jsonl"
    if not sub_file.exists():
        return {"subscriptions": [], "count": 0}
    subs, seen = [], set()
    for line in sub_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if subscriber and rec.get("subscriber") != subscriber:
            continue
        key = (rec.get("subscriber"), rec.get("target"))
        if key in seen:
            continue
        seen.add(key)
        if rec.get("active", True):
            subs.append(rec)
    return {"subscriptions": subs, "count": len(subs)}


def test_subscribe_symbols_registered_in_sync():
    import mcp_server_nucleus.tools.sync as sync_mod
    src = open(sync_mod.__file__).read()
    assert "def _marketplace_subscribe" in src
    assert '"marketplace_subscribe"' in src
    assert "def _marketplace_unsubscribe" in src
    assert '"marketplace_unsubscribe"' in src
    assert "def _marketplace_subscriptions" in src
    assert '"marketplace_subscriptions"' in src


def test_subscribe_creates_record(tmp_path):
    result = _subscribe("watcher@nucleus", target="agent-a@nucleus", brain_path=tmp_path)
    assert result["subscribed"] is True
    sub_file = tmp_path / "marketplace" / "subscriptions.jsonl"
    assert sub_file.exists()
    records = [json.loads(l) for l in sub_file.read_text().splitlines() if l.strip()]
    assert len(records) == 1
    assert records[0]["subscriber"] == "watcher@nucleus"
    assert records[0]["target"] == "agent-a@nucleus"


def test_subscribe_default_event_types(tmp_path):
    result = _subscribe("watcher@nucleus", brain_path=tmp_path)
    assert "tier_changed" in result["event_types"]
    assert "quarantined" in result["event_types"]


def test_subscribe_wildcard_target(tmp_path):
    result = _subscribe("monitor@nucleus", target="*", brain_path=tmp_path)
    assert result["target"] == "*"


def test_unsubscribe_removes_record(tmp_path):
    _subscribe("watcher@nucleus", target="agent-a@nucleus", brain_path=tmp_path)
    result = _unsubscribe("watcher@nucleus", target="agent-a@nucleus", brain_path=tmp_path)
    assert result["removed"] == 1
    remaining = _subscriptions(brain_path=tmp_path)
    assert remaining["count"] == 0


def test_unsubscribe_nonexistent_returns_zero(tmp_path):
    result = _unsubscribe("ghost@nucleus", target="*", brain_path=tmp_path)
    assert result["removed"] == 0


def test_subscriptions_lists_all(tmp_path):
    _subscribe("w1@nucleus", target="a@nucleus", brain_path=tmp_path)
    _subscribe("w2@nucleus", target="b@nucleus", brain_path=tmp_path)
    result = _subscriptions(brain_path=tmp_path)
    assert result["count"] == 2


def test_subscriptions_filter_by_subscriber(tmp_path):
    _subscribe("w1@nucleus", target="a@nucleus", brain_path=tmp_path)
    _subscribe("w2@nucleus", target="b@nucleus", brain_path=tmp_path)
    result = _subscriptions(subscriber="w1@nucleus", brain_path=tmp_path)
    assert result["count"] == 1
    assert result["subscriptions"][0]["subscriber"] == "w1@nucleus"


def test_subscriptions_deduplicates_on_read(tmp_path):
    _subscribe("w1@nucleus", target="*", brain_path=tmp_path)
    _subscribe("w1@nucleus", target="*", brain_path=tmp_path)
    result = _subscriptions(subscriber="w1@nucleus", brain_path=tmp_path)
    assert result["count"] == 1
