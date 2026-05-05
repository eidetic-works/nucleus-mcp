"""Saturation telemetry — task#219 / Bucket B5.

Reads turn data captured by ``measurement_proxy`` (jsonl files at
``.brain/measurement/turns.jsonl`` + ``turns.peer.jsonl``), establishes
rolling baselines on per-turn token usage + cross-turn latency, and
flags saturation when a metric exceeds a configurable factor of baseline.

Primitive contract (per Cowork B5 directive
``relay_20260426_191346_88772643``):

  - **Token-per-coord-decision baseline**: median total_tokens per turn
    over the last ``window_size`` turns.
  - **Cycle-latency baseline**: median seconds between consecutive turns.
  - **Saturation flag**: any single turn whose total_tokens or inter-turn
    latency exceeds ``threshold_factor * baseline`` (default 2.0).

On flag-trip, callers fire a ``[SATURATION-WARNING]`` relay to Cowork via
``relay_post`` (this module emits the verdict struct; relay-emit is the
caller's choice so we don't accidentally spam the bus).

5-axis primitive-gate:
  - any-OS: PRIMITIVE (jsonl read, stdlib only)
  - any-user: PRIMITIVE (env-keyed brain path)
  - any-agent: PRIMITIVE (surface field is free string per ADR-0005)
  - any-LLM: PRIMITIVE (works on any provider whose proxy logs the schema)
  - any-environment: PRIMITIVE (deploy scripts can use either env-var
    name via PR #172 dual-write shim)

Reference: cowork directive ``relay_20260426_191346_88772643`` §B5.
"""

from __future__ import annotations

import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .common import get_brain_path


DEFAULT_WINDOW_SIZE = 100
DEFAULT_THRESHOLD_FACTOR = 2.0


def _measurement_root() -> Path:
    """Resolve the measurement directory under the brain path."""
    return get_brain_path() / "measurement"


def _turns_path(surface: str = "main") -> Path:
    """Return the jsonl path for the given surface (main / peer / preflight)."""
    name = {
        "main": "turns.jsonl",
        "peer": "turns.peer.jsonl",
        "preflight": "preflight_turns.jsonl",
    }.get(surface, f"turns.{surface}.jsonl")
    return _measurement_root() / name


def _read_recent_turns(
    path: Path, window_size: int = DEFAULT_WINDOW_SIZE
) -> list[dict[str, Any]]:
    """Read the last ``window_size`` turns from a jsonl file.

    Tail-reads efficiently for large files: pulls the entire file then
    keeps the trailing ``window_size`` parsed lines. Malformed lines are
    skipped silently (best-effort).
    """
    if not path.exists():
        return []
    turns: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                turns.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return turns[-window_size:] if window_size > 0 else turns


def _total_tokens(turn: dict[str, Any]) -> int | None:
    """Extract total tokens (input + output) from a turn record.

    Returns None if the schema fields are missing — caller filters Nones
    so a malformed turn doesn't poison the baseline.
    """
    counters = turn.get("response_usage_counters") or {}
    inp = counters.get("input_tokens")
    out = counters.get("output_tokens")
    if not isinstance(inp, int) or not isinstance(out, int):
        return None
    return inp + out


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None


def _inter_turn_latencies(turns: list[dict[str, Any]]) -> list[float]:
    """Compute seconds between consecutive turns (timestamp-ordered).

    Drops turns with malformed timestamps. Negative deltas (clock skew or
    out-of-order writes) are clamped to 0.
    """
    parsed = []
    for t in turns:
        ts = _parse_iso(t.get("timestamp", ""))
        if ts is not None:
            parsed.append(ts)
    parsed.sort()
    out = []
    for prev, curr in zip(parsed, parsed[1:]):
        delta = (curr - prev).total_seconds()
        out.append(max(0.0, delta))
    return out


def compute_baselines(
    surface: str = "main",
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> dict[str, Any]:
    """Compute token + latency baselines from the recent turn window.

    Returns a verdict struct:
        {
          "surface": "main",
          "window_size": 100,
          "turn_count": 100,
          "tokens_baseline_median": 4123,
          "tokens_p95": 18204,
          "latency_baseline_median_s": 8.2,
          "latency_p95_s": 42.1,
          "data_present": True,
          "data_warnings": []
        }

    When fewer than 10 turns exist, ``data_present`` stays True but
    ``data_warnings`` includes a "low-confidence: <n> turns" entry. When
    the file is empty or missing, ``data_present`` is False.
    """
    path = _turns_path(surface)
    turns = _read_recent_turns(path, window_size=window_size)
    warnings: list[str] = []
    if not turns:
        return {
            "surface": surface,
            "window_size": window_size,
            "turn_count": 0,
            "tokens_baseline_median": None,
            "tokens_p95": None,
            "latency_baseline_median_s": None,
            "latency_p95_s": None,
            "data_present": False,
            "data_warnings": [
                f"no turns at {path} (file missing or empty)",
            ],
        }
    tokens = [tk for tk in (_total_tokens(t) for t in turns) if tk is not None]
    latencies = _inter_turn_latencies(turns)
    if len(turns) < 10:
        warnings.append(f"low-confidence: only {len(turns)} turns")
    if len(tokens) < len(turns):
        warnings.append(
            f"schema: {len(turns) - len(tokens)} turns missing token counters"
        )
    return {
        "surface": surface,
        "window_size": window_size,
        "turn_count": len(turns),
        "tokens_baseline_median": int(statistics.median(tokens)) if tokens else None,
        "tokens_p95": (
            int(_percentile(tokens, 95)) if len(tokens) >= 5 else None
        ),
        "latency_baseline_median_s": (
            round(statistics.median(latencies), 2) if latencies else None
        ),
        "latency_p95_s": (
            round(_percentile(latencies, 95), 2) if len(latencies) >= 5 else None
        ),
        "data_present": True,
        "data_warnings": warnings,
    }


def _percentile(values: Iterable[float], pct: float) -> float:
    """Compute a percentile (0-100) without numpy dependency."""
    sorted_vals = sorted(values)
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_vals) - 1)
    frac = rank - low
    return sorted_vals[low] * (1 - frac) + sorted_vals[high] * frac


def check_saturation(
    surface: str = "main",
    window_size: int = DEFAULT_WINDOW_SIZE,
    threshold_factor: float = DEFAULT_THRESHOLD_FACTOR,
    *,
    inspect_recent_n: int = 10,
) -> dict[str, Any]:
    """Compute baselines + scan the most recent ``inspect_recent_n`` turns
    for any whose total_tokens or inter-turn latency exceeds
    ``threshold_factor * baseline``. Returns a verdict struct:

        {
          "surface": "main",
          "saturated": False,
          "threshold_factor": 2.0,
          "baselines": {...},
          "flagged_turns": [
            {"turn_index": 1635, "metric": "tokens",
             "value": 28000, "baseline": 4100, "ratio": 6.83},
            ...
          ],
          "checked_count": 10
        }

    Designed to be cheap (read jsonl tail + compute medians once); safe to
    call on every coord-turn boundary by callers wanting auto-warning.
    """
    baselines = compute_baselines(surface=surface, window_size=window_size)
    if not baselines["data_present"]:
        return {
            "surface": surface,
            "saturated": False,
            "threshold_factor": threshold_factor,
            "baselines": baselines,
            "flagged_turns": [],
            "checked_count": 0,
            "no_data_reason": baselines["data_warnings"],
        }
    path = _turns_path(surface)
    turns = _read_recent_turns(path, window_size=window_size)
    recent = turns[-inspect_recent_n:] if inspect_recent_n > 0 else turns
    tokens_baseline = baselines["tokens_baseline_median"] or 0
    latency_baseline = baselines["latency_baseline_median_s"] or 0.0
    flagged: list[dict[str, Any]] = []
    # Token-flag scan: compare each recent turn's tokens to baseline.
    for t in recent:
        tk = _total_tokens(t)
        if tk is None or tokens_baseline == 0:
            continue
        ratio = tk / tokens_baseline
        if ratio >= threshold_factor:
            flagged.append({
                "turn_index": t.get("turn_index"),
                "session_id": t.get("session_id"),
                "timestamp": t.get("timestamp"),
                "metric": "tokens",
                "value": tk,
                "baseline": tokens_baseline,
                "ratio": round(ratio, 2),
            })
    # Latency-flag scan: compare consecutive-turn latencies in the recent
    # window to baseline. We need at least two consecutive turns.
    recent_latencies = _inter_turn_latencies(recent)
    parsed_recent = [
        (t.get("turn_index"), _parse_iso(t.get("timestamp", "")))
        for t in recent
    ]
    parsed_recent = [p for p in parsed_recent if p[1] is not None]
    parsed_recent.sort(key=lambda p: p[1])
    for (idx_prev, ts_prev), (idx_curr, ts_curr), latency in zip(
        parsed_recent, parsed_recent[1:], recent_latencies
    ):
        if latency_baseline == 0:
            continue
        ratio = latency / latency_baseline
        if ratio >= threshold_factor:
            flagged.append({
                "turn_index": idx_curr,
                "metric": "latency",
                "value": round(latency, 2),
                "baseline": latency_baseline,
                "ratio": round(ratio, 2),
            })
    return {
        "surface": surface,
        "saturated": bool(flagged),
        "threshold_factor": threshold_factor,
        "baselines": baselines,
        "flagged_turns": flagged,
        "checked_count": len(recent),
    }


def saturation_warning_payload(
    verdict: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a [SATURATION-WARNING] relay body from a check_saturation verdict.

    Returns None if the verdict isn't saturated. Caller is responsible for
    actually firing the relay via ``relay_post``; this is just the body
    builder so the schema stays consistent.
    """
    if not verdict.get("saturated"):
        return None
    surface = verdict.get("surface", "?")
    flagged = verdict.get("flagged_turns", [])
    threshold = verdict.get("threshold_factor", DEFAULT_THRESHOLD_FACTOR)
    metrics = sorted({f["metric"] for f in flagged})
    summary_lines = [
        f"Saturation flagged on {surface} surface ({len(flagged)} turns over "
        f"{threshold}x baseline). Metrics: {metrics}."
    ]
    for f in flagged[:5]:
        summary_lines.append(
            f"  - turn_index={f.get('turn_index')} {f['metric']}="
            f"{f['value']} (baseline {f['baseline']}, ratio {f['ratio']}x)"
        )
    if len(flagged) > 5:
        summary_lines.append(f"  ... and {len(flagged) - 5} more")
    return {
        "summary": "\n".join(summary_lines),
        "tags": ["saturation-warning", "experiment-mitigation", "task-219"],
        "artifact_refs": [
            f".brain/measurement/turns{'.peer' if surface == 'peer' else ''}.jsonl",
        ],
        "saturated": True,
        "verdict": verdict,
        "auto_generated": True,
    }
