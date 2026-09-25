"""Regression test: _increment_fence_token must be atomic under concurrency.

The old implementation did a non-locked read-modify-write on
ledger/fence_counter.json. Two concurrent callers could read the same value
and both write the same token => duplicate fence tokens => double-execution /
resource corruption (the fence token is a unique, monotonically increasing
mutual-exclusion token).

This test runs N=20 concurrent threads each calling _increment_fence_token()
and asserts:
  (a) all N returned tokens are UNIQUE, and
  (b) the final counter value == start + N (no lost updates).

It FAILS against the old unlocked code and PASSES with the fcntl.flock fix.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest


@pytest.fixture
def brain(tmp_path, monkeypatch):
    """Create a fully-structured brain directory and point env at it."""
    b = tmp_path / ".brain"
    for sub in ["ledger", "slots", "protocols", "config", "artifacts"]:
        (b / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(b))
    return b


def _set_start_value(brain, start):
    """Seed the fence counter with a known start value."""
    counter = {"value": start, "last_issued": None, "history": []}
    (brain / "ledger" / "fence_counter.json").write_text(json.dumps(counter))
    return start


class TestFenceTokenConcurrency:
    N = 20

    def test_concurrent_tokens_are_unique(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _increment_fence_token

        start = _set_start_value(brain, 1000)
        tokens = []
        lock = threading.Lock()

        def worker():
            token = _increment_fence_token()
            with lock:
                tokens.append(token)

        with ThreadPoolExecutor(max_workers=self.N) as pool:
            futures = [pool.submit(worker) for _ in range(self.N)]
            for f in as_completed(futures):
                f.result()  # propagate exceptions

        # (a) all N returned tokens are UNIQUE
        assert len(tokens) == self.N, f"expected {self.N} tokens, got {len(tokens)}"
        assert len(set(tokens)) == self.N, (
            f"duplicate fence tokens detected: {sorted(tokens)}"
        )

        # (b) final counter value == start + N (no lost updates)
        counter = json.loads(
            (brain / "ledger" / "fence_counter.json").read_text()
        )
        assert counter["value"] == start + self.N, (
            f"lost updates: expected {start + self.N}, got {counter['value']}"
        )

    def test_concurrent_tokens_monotonic_range(self, brain):
        """All tokens must fall in (start, start+N] with no gaps or dups."""
        from mcp_server_nucleus.runtime.orch_helpers import _increment_fence_token

        start = _set_start_value(brain, 500)
        tokens = []
        lock = threading.Lock()

        def worker():
            token = _increment_fence_token()
            with lock:
                tokens.append(token)

        with ThreadPoolExecutor(max_workers=self.N) as pool:
            futures = [pool.submit(worker) for _ in range(self.N)]
            for f in as_completed(futures):
                f.result()

        expected = set(range(start + 1, start + 1 + self.N))
        assert set(tokens) == expected, (
            f"token set mismatch: got {sorted(tokens)}, "
            f"expected {sorted(expected)}"
        )
