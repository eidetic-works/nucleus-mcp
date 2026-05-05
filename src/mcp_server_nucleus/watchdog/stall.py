"""Relay stall watchdog — GH #74 phase 1.

Detects "ball stopped" in the three-surface relay architecture. A stall is
silence across ALL live buckets (cowork, claude_code_main, claude_code_peer,
legacy claude_code) for longer than ``--threshold-min`` minutes while unread
relays exist somewhere.

Output: JSON to stdout with per-bucket youngest-mtime, unread counts, and a
``stalled: bool`` verdict. Exit 0 = healthy, 1 = stall detected.

Brain resolution order: ``$NUCLEUS_BRAIN`` wins; then ``--brain-path``;
then ``$NUCLEUS_BRAIN_PATH`` for backwards compat; final fallback is
``<NUCLEUS_ROOT>/.brain`` via ``paths.brain_path``.

Usage:
    python3 -m mcp_server_nucleus.watchdog.stall [--threshold-min 30] [--brain-path PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from mcp_server_nucleus.paths import brain_path as _default_brain_path

LIVE_BUCKETS = ("cowork", "claude_code_main", "claude_code_peer", "claude_code")
EXPECT_REPLY_TAGS = ("directive", "question-to-peer", "convergence-call")
ACK_STALL_THRESHOLD_MIN_DEFAULT = 30
REFUSE_PATTERN = re.compile(r"\b(kick(?:ed|back)?|refus(?:e|ed|al)|skip(?:ped)?)\b", re.IGNORECASE)
REFUSE_TAGS = {"kickback", "kicked", "refuse", "refused", "skip", "skipped", "refuse-without-reason"}


def _parse_body(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _expects_reply(data: dict) -> bool:
    body = _parse_body(data.get("body"))
    tags = body.get("tags") or []
    if any(t in EXPECT_REPLY_TAGS for t in tags):
        return True
    summary = (body.get("summary") or "").lower()
    return any(s in summary for s in ("ship-report", "concur", "reply shape"))


def _in_reply_to(data: dict) -> str | None:
    ctx = data.get("context") or {}
    if isinstance(ctx, dict):
        v = ctx.get("in_reply_to")
        if isinstance(v, str) and v:
            return v
    body = _parse_body(data.get("body"))
    v = body.get("in_reply_to")
    if isinstance(v, str) and v:
        return v
    return None


def _iso_to_ts(iso_str: str | None) -> float | None:
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def age_min(now: float, ts: float | None) -> float | None:
    """Age in minutes, clamped to >= 0. Negative raw value means sender clock
    is ahead of local — cycle-2 #13 clock-drift case. Display clamps to 0;
    callers should consult ``clock_drift_buckets`` in the report to know
    whether drift was observed (non-zero == surfacing-now)."""
    if ts is None:
        return None
    return round(max(0.0, (now - ts) / 60), 1)


def resolve_brain_path(cli_value: str | None) -> Path:
    env_new = os.environ.get("NUCLEUS_BRAIN")
    if env_new:
        return Path(env_new)
    if cli_value:
        return Path(cli_value)
    env_legacy = os.environ.get("NUCLEUS_BRAIN_PATH")
    if env_legacy:
        return Path(env_legacy)
    return _default_brain_path(strict=False)


def scan_bucket(bucket_dir: Path) -> tuple[float | None, float | None, int, int]:
    """Return (youngest_mtime_any, youngest_unread_created_at, total, unread).

    ``youngest_unread_created_at`` uses the relay's ``created_at`` field (the
    original landing time). mtime is unreliable for unread — ``relay_ack``
    updates mtime when it flips ``read=true``, so a just-acked old message
    looks "fresh" by mtime. Unread files haven't been acked, so mtime and
    created_at should match, but using created_at is the principled choice.

    Malformed JSON counts as unread (safer — surfaces the error).
    """
    if not bucket_dir.is_dir():
        return (None, None, 0, 0)
    youngest_any: float | None = None
    youngest_unread: float | None = None
    total = 0
    unread = 0
    for p in bucket_dir.glob("*.json"):
        total += 1
        try:
            st = p.stat()
        except OSError:
            continue
        if youngest_any is None or st.st_mtime > youngest_any:
            youngest_any = st.st_mtime
        try:
            data = json.loads(p.read_text())
            if not data.get("read", False):
                unread += 1
                created = data.get("created_at")
                created_ts = None
                if created:
                    try:
                        created_ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                    except (ValueError, AttributeError):
                        created_ts = st.st_mtime
                else:
                    created_ts = st.st_mtime
                if youngest_unread is None or created_ts > youngest_unread:
                    youngest_unread = created_ts
        except (json.JSONDecodeError, OSError):
            unread += 1
            if youngest_unread is None or st.st_mtime > youngest_unread:
                youngest_unread = st.st_mtime
    return (youngest_any, youngest_unread, total, unread)


def _iter_relays(relay_root: Path):
    """Yield (bucket_name, path, data) for every JSON relay under any bucket."""
    if not relay_root.is_dir():
        return
    for bucket in sorted(relay_root.iterdir()):
        if not bucket.is_dir():
            continue
        for p in sorted(bucket.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict):
                yield (bucket.name, p, data)


def find_ack_then_stalls(relay_root: Path, now: float, threshold_min: int) -> list[dict]:
    """LIVE-bucket relays acked but with no follow-on reply past threshold."""
    replied_to: set[str] = set()
    candidates: list[tuple[str, Path, dict]] = []
    for bucket, path, data in _iter_relays(relay_root):
        target = _in_reply_to(data)
        if target:
            replied_to.add(target)
        if bucket in LIVE_BUCKETS and data.get("read_at") and _expects_reply(data):
            candidates.append((bucket, path, data))
    flagged: list[dict] = []
    for bucket, path, data in candidates:
        rid = data.get("id")
        if not rid or rid in replied_to:
            continue
        read_ts = _iso_to_ts(data.get("read_at"))
        if read_ts is None:
            continue
        ack_age = (now - read_ts) / 60
        if ack_age > threshold_min:
            flagged.append({
                "id": rid,
                "bucket": bucket,
                "subject": (data.get("subject") or "")[:120],
                "ack_age_min": round(ack_age, 1),
            })
    return flagged


def find_refuse_without_reason(relay_root: Path) -> list[dict]:
    """Replies that signal refusal but lack a substantive reason (>=20 chars)."""
    flagged: list[dict] = []
    for bucket, path, data in _iter_relays(relay_root):
        if bucket not in LIVE_BUCKETS:
            continue
        target = _in_reply_to(data)
        if not target:
            continue
        body = _parse_body(data.get("body"))
        subject = data.get("subject") or ""
        tags = body.get("tags") or []
        tag_set = {t.lower() for t in tags if isinstance(t, str)}
        is_refusal = (
            REFUSE_PATTERN.search(subject) is not None
            or bool(tag_set & REFUSE_TAGS)
        )
        if not is_refusal:
            continue
        reason = (body.get("reason") or "").strip()
        if len(reason) >= 20:
            continue
        flagged.append({
            "id": data.get("id"),
            "bucket": bucket,
            "subject": subject[:120],
            "in_reply_to": target,
            "reason_len": len(reason),
        })
    return flagged


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold-min", type=int, default=30,
                    help="Stall if youngest relay across all buckets is older than this (minutes).")
    ap.add_argument("--ack-stall-threshold-min", type=int, default=ACK_STALL_THRESHOLD_MIN_DEFAULT,
                    help="Ack-then-stall: flag acked-expects-reply relays older than this (minutes).")
    ap.add_argument("--brain-path", default=None)
    args = ap.parse_args(argv)

    brain = resolve_brain_path(args.brain_path)
    relay_root = brain / "relay"
    now = time.time()
    threshold_sec = args.threshold_min * 60

    per_bucket: dict[str, dict] = {}
    total_unread = 0
    stalled_buckets: list[str] = []
    clock_drift_buckets: list[str] = []

    for name in LIVE_BUCKETS:
        youngest_any, youngest_unread, total, unread = scan_bucket(relay_root / name)
        unread_age_min = age_min(now, youngest_unread)
        if youngest_unread is not None and (now - youngest_unread) < 0:
            clock_drift_buckets.append(name)
        bucket_stalled = (
            unread > 0
            and youngest_unread is not None
            and (now - youngest_unread) > threshold_sec
        )
        per_bucket[name] = {
            "youngest_mtime_any_min": age_min(now, youngest_any),
            "youngest_unread_age_min": unread_age_min,
            "total": total,
            "unread": unread,
            "stalled": bucket_stalled,
        }
        if bucket_stalled:
            stalled_buckets.append(name)
        total_unread += unread

    ack_then_stalls = find_ack_then_stalls(relay_root, now, args.ack_stall_threshold_min)
    refuse_without_reason = find_refuse_without_reason(relay_root)
    silent_mode_detected = bool(ack_then_stalls or refuse_without_reason)

    report = {
        "timestamp": int(now),
        "threshold_min": args.threshold_min,
        "ack_stall_threshold_min": args.ack_stall_threshold_min,
        "total_unread_across_buckets": total_unread,
        "stalled": bool(stalled_buckets),
        "stalled_buckets": stalled_buckets,
        "clock_drift_buckets": clock_drift_buckets,
        "ack_then_stalls": ack_then_stalls,
        "refuse_without_reason": refuse_without_reason,
        "silent_mode_detected": silent_mode_detected,
        "per_bucket": per_bucket,
    }
    if stalled_buckets:
        report["ball_stopped_in"] = max(
            stalled_buckets,
            key=lambda n: per_bucket[n]["youngest_unread_age_min"] or 0,
        )

    print(json.dumps(report, indent=2))
    return 1 if stalled_buckets else 0


if __name__ == "__main__":
    sys.exit(main())
