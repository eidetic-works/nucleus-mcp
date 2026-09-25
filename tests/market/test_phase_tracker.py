#!/usr/bin/env python3
"""Tests for phase_tracker.py"""
import os
import sys
import json
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts/market'))
import phase_tracker as pt


def test_internal_senders_set():
    assert "claude_code_main" in pt.INTERNAL_SENDERS
    assert "windsurf" in pt.INTERNAL_SENDERS


def test_detect_phase_founding():
    senders = {"claude_code_main", "windsurf"}
    phase, _ = pt.detect_phase(senders, {})
    assert phase == 1


def test_detect_phase_first_external():
    senders = {"claude_code_main", "ext_tool"}
    phase, _ = pt.detect_phase(senders, {"ext_to_int": 5})
    assert phase == 2


def test_detect_phase_registry():
    senders = {"claude_code_main", "a", "b", "c", "d", "e"}
    phase, _ = pt.detect_phase(senders, {"ext_to_int": 10})
    assert phase == 3


def test_prometheus_output():
    metrics = pt.PhaseMetrics(phase=2, internal_tools=3, external_tools=1,
                              external_to_external_7d=0, external_to_internal_7d=5,
                              evidence="test")
    out = pt.output_prometheus(metrics)
    assert "nucleus_market_phase 2" in out


if __name__ == "__main__":
    test_internal_senders_set()
    print("✓ test_internal_senders_set")
    test_detect_phase_founding()
    print("✓ test_detect_phase_founding")
    test_detect_phase_first_external()
    print("✓ test_detect_phase_first_external")
    test_detect_phase_registry()
    print("✓ test_detect_phase_registry")
    test_prometheus_output()
    print("✓ test_prometheus_output")
    print("\nAll tests passed!")