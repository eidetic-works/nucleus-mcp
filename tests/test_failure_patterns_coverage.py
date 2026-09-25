"""
Coverage tests for mcp_server_nucleus.runtime.failure_patterns.

Targets 90%+ line coverage. Uses tmp_path for filesystem. No real
network/subprocess.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime import failure_patterns as fp
from mcp_server_nucleus.runtime.failure_patterns import (
    _classify_failure,
    _count_pattern,
    _detect_root,
    _patterns_path,
    catalog_failure,
    get_all_patterns,
    get_recurring_patterns,
)


# ──────────────────────────────────────────────────────────────────────
# _patterns_path
# ──────────────────────────────────────────────────────────────────────

def test_patterns_path_creates_dir(tmp_path):
    p = _patterns_path(tmp_path)
    assert p == tmp_path / ".brain" / "governance" / "failure_patterns.jsonl"
    assert p.parent.exists()


def test_patterns_path_idempotent(tmp_path):
    p1 = _patterns_path(tmp_path)
    p2 = _patterns_path(tmp_path)
    assert p1 == p2


# ──────────────────────────────────────────────────────────────────────
# _classify_failure
# ──────────────────────────────────────────────────────────────────────

def test_classify_file_missing():
    assert _classify_failure({"check": "outcome_file"}) == "file_missing"


def test_classify_zero_delta():
    assert _classify_failure({"actual_delta": 0, "claimed_delta": 5}) == "zero_delta"


def test_classify_negative_delta():
    assert _classify_failure({"actual_delta": -3, "claimed_delta": 5}) == "negative_delta"


def test_classify_insufficient_delta():
    # claimed 100, actual 10 (< 25) => insufficient
    assert _classify_failure({"actual_delta": 10, "claimed_delta": 100}) == "insufficient_delta"


def test_classify_insufficient_delta_boundary():
    # claimed 100, actual 25 (== 25%, not <) => unknown
    assert _classify_failure({"actual_delta": 25, "claimed_delta": 100}) == "unknown"


def test_classify_unknown_when_claimed_zero():
    assert _classify_failure({"actual_delta": 5, "claimed_delta": 0}) == "unknown"


def test_classify_unknown_default():
    assert _classify_failure({"actual_delta": 50, "claimed_delta": 100}) == "unknown"


def test_classify_missing_keys_defaults():
    # actual defaults to 0 => zero_delta
    assert _classify_failure({}) == "zero_delta"


# ──────────────────────────────────────────────────────────────────────
# catalog_failure
# ──────────────────────────────────────────────────────────────────────

def test_catalog_failure_skips_passed(tmp_path):
    catalog_failure({"passed": True, "metric": "cov", "actual_delta": 0}, "plan.md", tmp_path)
    pp = _patterns_path(tmp_path)
    assert not pp.exists() or pp.read_text() == ""


def test_catalog_failure_writes_entry(tmp_path):
    catalog_failure(
        {"passed": False, "metric": "coverage", "actual_delta": 0, "claimed_delta": 5,
         "hit_ratio": 0.1},
        "plan.md", tmp_path,
    )
    pp = _patterns_path(tmp_path)
    lines = [l for l in pp.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["pattern_key"] == "coverage:zero_delta"
    assert entry["metric"] == "coverage"
    assert entry["failure_mode"] == "zero_delta"
    assert entry["plan_file"] == "plan.md"
    assert entry["hit_ratio"] == 0.1
    assert "ts" in entry


def test_catalog_failure_uses_check_when_no_metric(tmp_path):
    catalog_failure(
        {"passed": False, "check": "outcome_file", "actual_delta": 0},
        "plan.md", tmp_path,
    )
    entry = json.loads(_patterns_path(tmp_path).read_text().strip())
    assert entry["metric"] == "outcome_file"
    assert entry["failure_mode"] == "file_missing"


def test_catalog_failure_defaults_root_when_none(tmp_path, monkeypatch):
    # project_root=None triggers _detect_root(); force it to tmp_path
    monkeypatch.setattr(fp, "_detect_root", lambda: tmp_path)
    catalog_failure({"passed": False, "metric": "m", "actual_delta": -1}, "p.md", None)
    assert _patterns_path(tmp_path).exists()


def test_catalog_failure_write_error_swallowed(tmp_path, monkeypatch):
    # Make open raise
    real_open = open

    def boom(path, *a, **kw):
        if "failure_patterns.jsonl" in str(path):
            raise OSError("disk full")
        return real_open(path, *a, **kw)

    monkeypatch.setattr("builtins.open", boom)
    # Should not raise
    catalog_failure({"passed": False, "metric": "m", "actual_delta": 0}, "p.md", tmp_path)


def test_catalog_failure_recurring_logs_at_three(tmp_path, caplog):
    for _ in range(3):
        catalog_failure({"passed": False, "metric": "m", "actual_delta": 0}, "p.md", tmp_path)
    # 4th triggers the recurring log (count >= 3)
    with caplog.at_level("INFO", logger="nucleus.failure_patterns"):
        catalog_failure({"passed": False, "metric": "m", "actual_delta": 0}, "p.md", tmp_path)
    assert any("Recurring failure pattern" in r.message for r in caplog.records)


# ──────────────────────────────────────────────────────────────────────
# _count_pattern
# ──────────────────────────────────────────────────────────────────────

def test_count_pattern_no_file(tmp_path):
    # Force file to not exist
    pp = _patterns_path(tmp_path)
    pp.unlink(missing_ok=True)
    assert _count_pattern(tmp_path, "x:y") == 0


def test_count_pattern_counts_matches(tmp_path):
    pp = _patterns_path(tmp_path)
    pp.write_text(
        json.dumps({"pattern_key": "a:b"}) + "\n"
        + json.dumps({"pattern_key": "a:b"}) + "\n"
        + json.dumps({"pattern_key": "c:d"}) + "\n"
    )
    assert _count_pattern(tmp_path, "a:b") == 2
    assert _count_pattern(tmp_path, "c:d") == 1
    assert _count_pattern(tmp_path, "z:z") == 0


def test_count_pattern_skips_blank_and_invalid(tmp_path):
    pp = _patterns_path(tmp_path)
    pp.write_text(
        "\n"
        + "   \n"
        + "{bad json}\n"
        + json.dumps({"pattern_key": "a:b"}) + "\n"
    )
    assert _count_pattern(tmp_path, "a:b") == 1


# ──────────────────────────────────────────────────────────────────────
# get_recurring_patterns
# ──────────────────────────────────────────────────────────────────────

def test_get_recurring_patterns_no_file(tmp_path):
    pp = _patterns_path(tmp_path)
    pp.unlink(missing_ok=True)
    assert get_recurring_patterns(tmp_path) == []


def test_get_recurring_patterns_filters_by_min_count(tmp_path):
    pp = _patterns_path(tmp_path)
    for _ in range(3):
        pp.write_text(
            json.dumps({"pattern_key": "a:b", "metric": "m", "failure_mode": "b", "ts": "t1"}) + "\n",
            "a",  # append
        ) if False else None
    # write properly
    with open(pp, "w") as f:
        for i in range(3):
            f.write(json.dumps({"pattern_key": "a:b", "metric": "m", "failure_mode": "b", "ts": f"t{i}"}) + "\n")
        f.write(json.dumps({"pattern_key": "c:d", "metric": "m2", "failure_mode": "d", "ts": "t"}) + "\n")
    rec = get_recurring_patterns(tmp_path, min_count=3)
    assert len(rec) == 1
    assert rec[0]["pattern_key"] == "a:b"
    assert rec[0]["count"] == 3
    assert rec[0]["metric"] == "m"
    assert rec[0]["failure_mode"] == "b"
    assert rec[0]["last_occurrence"] == "t2"


def test_get_recurring_patterns_min_count_higher(tmp_path):
    pp = _patterns_path(tmp_path)
    with open(pp, "w") as f:
        for i in range(3):
            f.write(json.dumps({"pattern_key": "a:b", "metric": "m", "failure_mode": "b", "ts": f"t{i}"}) + "\n")
    assert get_recurring_patterns(tmp_path, min_count=5) == []


def test_get_recurring_patterns_skips_invalid_lines(tmp_path):
    pp = _patterns_path(tmp_path)
    with open(pp, "w") as f:
        f.write("{bad}\n")
        f.write("\n")
        for i in range(3):
            f.write(json.dumps({"pattern_key": "a:b", "metric": "m", "failure_mode": "b", "ts": f"t{i}"}) + "\n")
    rec = get_recurring_patterns(tmp_path, min_count=3)
    assert len(rec) == 1


def test_get_recurring_patterns_missing_fields_defaults(tmp_path):
    pp = _patterns_path(tmp_path)
    with open(pp, "w") as f:
        for _ in range(3):
            f.write(json.dumps({"pattern_key": "a:b"}) + "\n")
    rec = get_recurring_patterns(tmp_path, min_count=3)
    assert rec[0]["metric"] == "?"
    assert rec[0]["failure_mode"] == "?"
    assert rec[0]["last_occurrence"] == "?"


# ──────────────────────────────────────────────────────────────────────
# get_all_patterns
# ──────────────────────────────────────────────────────────────────────

def test_get_all_patterns_no_file(tmp_path):
    pp = _patterns_path(tmp_path)
    pp.unlink(missing_ok=True)
    assert get_all_patterns(tmp_path) == []


def test_get_all_patterns_returns_all(tmp_path):
    pp = _patterns_path(tmp_path)
    with open(pp, "w") as f:
        f.write(json.dumps({"pattern_key": "a:b"}) + "\n")
        f.write(json.dumps({"pattern_key": "c:d"}) + "\n")
        f.write("{bad}\n")
        f.write("\n")
    entries = get_all_patterns(tmp_path)
    assert len(entries) == 2
    assert entries[0]["pattern_key"] == "a:b"


# ──────────────────────────────────────────────────────────────────────
# _detect_root
# ──────────────────────────────────────────────────────────────────────

def test_detect_root_finds_git(tmp_path, monkeypatch):
    sub = tmp_path / "deep" / "nested"
    sub.mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(sub)
    assert _detect_root() == tmp_path.resolve()


def test_detect_root_no_git_returns_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _detect_root() == tmp_path.resolve()
