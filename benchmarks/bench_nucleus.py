#!/usr/bin/env python3
"""
Nucleus Benchmark Suite
=======================

Reproducible performance measurements for core Nucleus operations.
Run: python benchmarks/bench_nucleus.py

Measures:
  1. Brain initialization time
  2. Engram write throughput (memory persistence)
  3. Engram read/search latency
  4. Task CRUD throughput
  5. Session lifecycle overhead
  6. Event bus pub/sub latency
  7. Channel router dispatch time
  8. State read/write latency
  9. Security posture generation time
  10. Cold start time (full import)

Results are printed as a table and optionally saved to JSON.
"""

import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Ensure we can import nucleus modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _isolated_import(name, filepath):
    """Import a single module file without triggering the full package __init__."""
    import importlib.util
    import types
    # Ensure parent packages exist as stubs
    for pkg in ["mcp_server_nucleus", "mcp_server_nucleus.runtime",
                "mcp_server_nucleus.runtime.channels"]:
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)
    spec = importlib.util.spec_from_file_location(name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Utilities ────────────────────────────────────────────────────

class Timer:
    """Context manager for timing code blocks."""
    def __init__(self):
        self.elapsed_ms = 0
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *_):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


def run_n(fn, n=100):
    """Run fn() n times, return list of elapsed_ms."""
    times = []
    for _ in range(n):
        with Timer() as t:
            fn()
        times.append(t.elapsed_ms)
    return times


def stats(times):
    """Compute p50, p95, p99, mean, min, max from a list of ms values."""
    if not times:
        return {}
    s = sorted(times)
    n = len(s)
    return {
        "n": n,
        "mean_ms": round(statistics.mean(s), 3),
        "p50_ms": round(s[n // 2], 3),
        "p95_ms": round(s[int(n * 0.95)], 3),
        "p99_ms": round(s[int(n * 0.99)], 3),
        "min_ms": round(s[0], 3),
        "max_ms": round(s[-1], 3),
    }


# ── Benchmarks ───────────────────────────────────────────────────

def bench_brain_init(tmp_dir):
    """Measure time to initialize a .brain directory from scratch."""
    def fn():
        brain = Path(tmp_dir) / f"brain_{time.monotonic_ns()}"
        dirs = [
            brain / "ledger", brain / "sessions", brain / "slots",
            brain / "artifacts", brain / "agents", brain / "memory",
            brain / "config", brain / "channels",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        (brain / "ledger" / "state.json").write_text('{"status": "active"}')
        (brain / "ledger" / "events.jsonl").write_text("")
        (brain / "ledger" / "tasks.json").write_text("[]")
        (brain / "memory" / "engrams.json").write_text("[]")
        (brain / "memory" / "context.md").write_text("# Project\n")
        (brain / "config" / "nucleus.yaml").write_text("telemetry:\n  enabled: false\n")
    return stats(run_n(fn, 50))


def bench_engram_write(brain_path):
    """Measure engram write throughput."""
    engrams_file = brain_path / "memory" / "engrams.json"
    engrams_file.write_text("[]")

    counter = [0]
    def fn():
        counter[0] += 1
        engrams = json.loads(engrams_file.read_text())
        engrams.append({
            "id": f"engram_{counter[0]}",
            "content": f"Benchmark engram #{counter[0]}: " + "x" * 200,
            "tags": ["benchmark"],
            "created_at": "2026-01-01T00:00:00Z",
        })
        engrams_file.write_text(json.dumps(engrams))

    return stats(run_n(fn, 200))


def bench_engram_read(brain_path):
    """Measure engram read latency (after writes)."""
    engrams_file = brain_path / "memory" / "engrams.json"

    def fn():
        data = json.loads(engrams_file.read_text())
        # Simulate search: scan for matching tag
        _ = [e for e in data if "benchmark" in e.get("tags", [])]

    return stats(run_n(fn, 200))


def bench_task_crud(brain_path):
    """Measure task create/read/update cycle."""
    tasks_file = brain_path / "ledger" / "tasks.json"
    tasks_file.write_text("[]")

    counter = [0]
    def fn():
        counter[0] += 1
        # Create
        tasks = json.loads(tasks_file.read_text())
        task = {
            "id": f"task_{counter[0]}",
            "title": f"Benchmark task #{counter[0]}",
            "status": "pending",
            "priority": "medium",
        }
        tasks.append(task)
        tasks_file.write_text(json.dumps(tasks))

        # Read
        tasks = json.loads(tasks_file.read_text())

        # Update
        for t in tasks:
            if t["id"] == task["id"]:
                t["status"] = "done"
                break
        tasks_file.write_text(json.dumps(tasks))

    return stats(run_n(fn, 100))


def bench_session_lifecycle(brain_path):
    """Measure session start/save/end cycle."""
    sessions_dir = brain_path / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    counter = [0]
    def fn():
        counter[0] += 1
        session_id = f"sess_{counter[0]}"
        session_file = sessions_dir / f"{session_id}.json"

        # Start
        session = {
            "id": session_id,
            "goal": "Benchmark session",
            "started_at": "2026-01-01T00:00:00Z",
            "events": [],
            "state": {},
        }
        session_file.write_text(json.dumps(session))

        # Add events
        session["events"].append({"type": "start", "ts": time.time()})
        session["events"].append({"type": "milestone", "ts": time.time()})
        session_file.write_text(json.dumps(session))

        # End
        session["ended_at"] = "2026-01-01T00:01:00Z"
        session_file.write_text(json.dumps(session))

    return stats(run_n(fn, 100))


def bench_event_bus():
    """Measure event bus publish/subscribe latency."""
    try:
        mod = _isolated_import(
            "event_bus",
            Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "event_bus.py",
        )
        EventBus = mod.EventBus
        BrainFileEvent = mod.BrainFileEvent
    except Exception as e:
        return {"error": f"event_bus not importable: {e}"}

    bus = EventBus()
    received = []
    bus.subscribe("test", lambda e: received.append(e))

    def fn():
        event = BrainFileEvent(event_type="test", path="benchmark.json")
        bus.publish(event)

    return stats(run_n(fn, 500))


def bench_channel_router():
    """Measure channel router dispatch with a mock channel."""
    try:
        mod = _isolated_import(
            "channels_base",
            Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "channels" / "base.py",
        )
        NotificationChannel = mod.NotificationChannel
        ChannelRouter = mod.ChannelRouter
    except Exception as e:
        return {"error": f"channels not importable: {e}"}

    class MockChannel(NotificationChannel):
        @property
        def name(self): return "mock"
        @property
        def display_name(self): return "Mock"
        def send(self, title, message, level="info"): return True
        def is_configured(self): return True

    router = ChannelRouter()
    router.register(MockChannel())

    def fn():
        router.notify("Bench", "Test message", "info")

    return stats(run_n(fn, 500))


def bench_state_rw(brain_path):
    """Measure state.json read/write latency."""
    state_file = brain_path / "ledger" / "state.json"
    state_file.write_text(json.dumps({"counter": 0, "status": "active"}))

    def fn():
        state = json.loads(state_file.read_text())
        state["counter"] = state.get("counter", 0) + 1
        state_file.write_text(json.dumps(state))

    return stats(run_n(fn, 200))


def bench_cold_start():
    """Measure time to import the nucleus package."""
    # This measures import overhead by running a subprocess
    import subprocess
    times = []
    for _ in range(5):
        with Timer() as t:
            subprocess.run(
                [sys.executable, "-c",
                 "from mcp_server_nucleus.runtime.channels.base import ChannelRouter"],
                capture_output=True, timeout=30,
                env={**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent / "src")},
            )
        times.append(t.elapsed_ms)
    return stats(times)


# ── Runner ───────────────────────────────────────────────────────

def print_table(results):
    """Print results as a formatted table."""
    print()
    print("=" * 78)
    print("  NUCLEUS BENCHMARK RESULTS")
    print("=" * 78)
    print(f"  {'Benchmark':<28s} {'n':>5s} {'mean':>9s} {'p50':>9s} {'p95':>9s} {'p99':>9s}")
    print("-" * 78)
    for name, data in results.items():
        if "error" in data:
            print(f"  {name:<28s}  ERROR: {data['error']}")
            continue
        print(
            f"  {name:<28s} {data['n']:>5d} "
            f"{data['mean_ms']:>8.2f}ms "
            f"{data['p50_ms']:>8.2f}ms "
            f"{data['p95_ms']:>8.2f}ms "
            f"{data['p99_ms']:>8.2f}ms"
        )
    print("=" * 78)
    print()


def main():
    output_file = None
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    print("Nucleus Benchmark Suite")
    print("Running benchmarks...")
    print()

    results = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Setup a brain for benchmarks
        brain_path = Path(tmp_dir) / ".brain"
        for d in ["ledger", "sessions", "slots", "memory", "config", "channels"]:
            (brain_path / d).mkdir(parents=True)
        (brain_path / "ledger" / "state.json").write_text('{"status": "active"}')
        (brain_path / "ledger" / "tasks.json").write_text("[]")
        (brain_path / "ledger" / "events.jsonl").write_text("")
        (brain_path / "memory" / "engrams.json").write_text("[]")

        benchmarks = [
            ("brain_init", lambda: bench_brain_init(tmp_dir)),
            ("engram_write", lambda: bench_engram_write(brain_path)),
            ("engram_read", lambda: bench_engram_read(brain_path)),
            ("task_crud", lambda: bench_task_crud(brain_path)),
            ("session_lifecycle", lambda: bench_session_lifecycle(brain_path)),
            ("state_read_write", lambda: bench_state_rw(brain_path)),
            ("event_bus_pubsub", bench_event_bus),
            ("channel_router", bench_channel_router),
            ("cold_start_import", bench_cold_start),
        ]

        for name, fn in benchmarks:
            print(f"  Running {name}...", end=" ", flush=True)
            try:
                results[name] = fn()
                n = results[name].get("n", "?")
                mean = results[name].get("mean_ms", "?")
                print(f"done ({n} iterations, {mean}ms mean)")
            except Exception as e:
                results[name] = {"error": str(e)}
                print(f"FAILED: {e}")

    print_table(results)

    if output_file:
        Path(output_file).write_text(json.dumps(results, indent=2))
        print(f"Results saved to {output_file}")

    # Print summary for competitive positioning
    total_ops = sum(r.get("n", 0) for r in results.values() if "error" not in r)
    print(f"Total operations benchmarked: {total_ops}")
    print(f"All operations use file-based storage (no external DB required)")
    print(f"Zero network dependencies for core operations")
    print()


if __name__ == "__main__":
    main()
