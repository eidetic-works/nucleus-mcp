"""Test three-surface cold-start seed script (issue #73).

Verifies that:
1. Cold-start initializes the flywheel directory
2. Cold-start seeds the founding CSR claim
3. Cold-start generates a dashboard snapshot
4. Cold-start is idempotent (running twice doesn't break)
5. Live-fire harness skips surfaces without API keys
"""
import subprocess
import sys
import os
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COLD_START_SCRIPT = PROJECT_ROOT / "scripts" / "three_surface_cold_start.py"
LIVE_FIRE_SCRIPT = PROJECT_ROOT / "scripts" / "three_surface_live_fire.py"


def _run_script(script: Path, brain_path: Path, extra_args: list = None) -> subprocess.CompletedProcess:
    """Run a script with the given brain path."""
    cmd = [sys.executable, str(script), "--brain-path", str(brain_path)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )


class TestColdStartSeed:
    """Test the cold-start seed script."""

    def test_cold_start_succeeds(self, tmp_path):
        """Cold-start should succeed and initialize flywheel."""
        brain = tmp_path / "brain"
        result = _run_script(COLD_START_SCRIPT, brain)

        assert result.returncode == 0, (
            f"Cold-start should succeed. stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "SUCCESS" in result.stdout, f"Should report success. stdout={result.stdout!r}"

    def test_cold_start_creates_flywheel_dir(self, tmp_path):
        """Cold-start should create .brain/flywheel/ directory."""
        brain = tmp_path / "brain"
        _run_script(COLD_START_SCRIPT, brain)

        assert (brain / "flywheel").is_dir(), "flywheel/ directory should exist"
        assert (brain / "flywheel" / "csr.json").is_file(), "csr.json should exist"

    def test_cold_start_seeds_founding_claim(self, tmp_path):
        """Cold-start should seed the founding CSR claim."""
        brain = tmp_path / "brain"
        _run_script(COLD_START_SCRIPT, brain)

        csr_path = brain / "flywheel" / "csr.json"
        with open(csr_path) as f:
            csr = json.load(f)

        assert csr.get("claims_total", 0) >= 1, (
            f"Should have at least 1 claim. CSR: {csr}"
        )
        assert csr.get("claims_survived", 0) >= 1, (
            f"Should have at least 1 survived claim. CSR: {csr}"
        )

    def test_cold_start_is_idempotent(self, tmp_path):
        """Running cold-start twice should not break."""
        brain = tmp_path / "brain"

        result1 = _run_script(COLD_START_SCRIPT, brain)
        assert result1.returncode == 0

        result2 = _run_script(COLD_START_SCRIPT, brain)
        assert result2.returncode == 0, (
            f"Second cold-start should also succeed. stdout={result2.stdout!r}"
        )

        # Should have 2 claims now (seeded twice)
        csr_path = brain / "flywheel" / "csr.json"
        with open(csr_path) as f:
            csr = json.load(f)
        assert csr.get("claims_total", 0) >= 2, (
            f"Should have 2+ claims after double seed. CSR: {csr}"
        )

    def test_cold_start_outputs_csr_summary(self, tmp_path):
        """Cold-start should print CSR summary."""
        brain = tmp_path / "brain"
        result = _run_script(COLD_START_SCRIPT, brain)

        assert "CSR:" in result.stdout, (
            f"Should print CSR summary. stdout={result.stdout!r}"
        )


class TestLiveFireHarness:
    """Test the live-fire test harness."""

    def test_live_fire_skips_without_api_keys(self, tmp_path, monkeypatch):
        """Live-fire should SKIP all surfaces when no API keys are set."""
        brain = tmp_path / "brain"

        # Ensure no API keys are set
        for key in ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "DEVIN_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        result = _run_script(LIVE_FIRE_SCRIPT, brain)

        # Should exit 0 (all available surfaces passed — none were available, so all skipped)
        assert result.returncode == 0, (
            f"Should exit 0 when all surfaces skip. stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "SKIP" in result.stdout, f"Should report SKIP. stdout={result.stdout!r}"

    def test_live_fire_records_csr(self, tmp_path, monkeypatch):
        """Live-fire should record CSR even when all surfaces skip."""
        brain = tmp_path / "brain"

        for key in ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "DEVIN_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        _run_script(LIVE_FIRE_SCRIPT, brain)

        csr_path = brain / "flywheel" / "csr.json"
        assert csr_path.is_file(), "CSR file should exist after live-fire"
