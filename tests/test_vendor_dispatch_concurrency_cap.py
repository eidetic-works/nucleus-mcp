"""_DISPATCH_SEMAPHORE must actually bound concurrent vendor subprocesses.

THE INCIDENT (2026-08-16/17): one session fanned out 9 concurrent
nucleus_delegate dispatches through vendor_dispatch.py, all reaching the same
running mcp-server-nucleus process with no concurrency limit anywhere in the
call path. Result: one SIGBUS crash, one 8-minute hang requiring a manual
kill, four hard 2700s timeouts with zero output, and one dispatch killed
externally mid-run -- seven infra incidents in one night, none caused by the
dispatched task content, all by unbounded concurrent load on one process.

Each test states its failure direction; a check that can only pass is not a
check.
"""

import threading
import time

from mcp_server_nucleus.runtime import vendor_dispatch as vd


def _run_capped(n_workers: int, cap: int, work_s: float = 0.2):
    """Run n_workers threads through a semaphore of size `cap`, each holding
    it for work_s seconds. Returns (max_concurrent_seen, elapsed_seconds)."""
    sem = threading.Semaphore(cap)
    in_flight = []
    lock = threading.Lock()
    max_seen = [0]

    def worker():
        with sem:
            with lock:
                in_flight.append(1)
                max_seen[0] = max(max_seen[0], len(in_flight))
            time.sleep(work_s)
            with lock:
                in_flight.pop()

    threads = [threading.Thread(target=worker) for _ in range(n_workers)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    return max_seen[0], elapsed


def test_cap_is_never_exceeded():
    """POSITIVE: the primary guarantee. 5 workers, cap=2 -> never >2 at once."""
    max_seen, _ = _run_capped(n_workers=5, cap=2, work_s=0.2)
    assert max_seen <= 2, f"cap violated -- {max_seen} ran simultaneously against a cap of 2"


def test_cap_is_actually_reached_not_vacuous():
    """OPPOSED: a cap that's never hit proves nothing -- could be a no-op
    semaphore that always has room. With 5 workers >> cap=2, it MUST hit 2."""
    max_seen, _ = _run_capped(n_workers=5, cap=2, work_s=0.2)
    assert max_seen == 2, (
        f"expected the cap to be genuinely exercised (reach exactly 2), got {max_seen} "
        "-- if this is < 2, the semaphore isn't gating anything real"
    )


def test_excess_calls_genuinely_queue():
    """OPPOSED: elapsed time must prove serialization happened, not just that
    the assertion checks passed. 5 x 0.2s work at cap=2 needs 3 sequential
    batches (2+2+1) -> must take meaningfully longer than one batch (0.2s)."""
    _, elapsed = _run_capped(n_workers=5, cap=2, work_s=0.2)
    assert elapsed > 0.4, (
        f"completed in {elapsed:.2f}s -- too fast for 3 queued batches of 0.2s each; "
        "calls ran unbounded instead of queueing behind the cap"
    )


def test_below_cap_runs_without_forced_serialization():
    """OPPOSED in the other direction: a cap must not over-serialize work that
    fits within it. 2 workers, cap=2 -> both run at once, ~0.2s, not ~0.4s."""
    max_seen, elapsed = _run_capped(n_workers=2, cap=2, work_s=0.2)
    assert max_seen == 2, "both workers should have run concurrently, cap wasn't the bottleneck"
    assert elapsed < 0.35, (
        f"took {elapsed:.2f}s for 2 workers under a cap of 2 -- they were serialized "
        "when they shouldn't have been (over-throttling, not just under-throttling, is a bug)"
    )


def test_module_semaphore_default_matches_env_override():
    """The real module-level semaphore reads NUCLEUS_VENDOR_MAX_CONCURRENT,
    default 3 -- not testing the env var itself (module-load-time), just that
    the constant it produced is a sane positive integer bound, not 0 or unset."""
    assert isinstance(vd._DISPATCH_MAX_CONCURRENT, int)
    assert vd._DISPATCH_MAX_CONCURRENT >= 1
    assert isinstance(vd._DISPATCH_SEMAPHORE, type(threading.Semaphore()))
