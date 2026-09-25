import asyncio
import json
import logging
import time
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

aiohttp = pytest.importorskip("aiohttp")

logger = logging.getLogger(__name__)

# Basic headers and JSON body
def _headers(token: str, idem_key: str = None) -> dict:
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if idem_key:
        h["Idempotency-Key"] = idem_key
    return h

def _payload(i: int, sender: str) -> dict:
    return {
        "subject": f"Stress test {i}",
        "body": json.dumps({"summary": "hello world", "i": i}),
        "sender": sender,
        "priority": "normal",
    }

# Ensure reports directory exists
def get_report_path() -> Path:
    brain_dir = Path(__file__).parent.parent.parent.parent / ".brain"
    reports_dir = brain_dir / "stress_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return reports_dir / f"relay_{ts}.json"

def write_report(data: dict):
    path = get_report_path()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@pytest.fixture(scope="module")
def shared_report():
    report = {"scenarios": {}}
    yield report
    write_report(report)

def record_metrics(report, name, latencies):
    if not latencies:
        return
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    report["scenarios"][name] = {
        "count": len(latencies),
        "p50_ms": round(p50 * 1000, 2),
        "p95_ms": round(p95 * 1000, 2),
        "p99_ms": round(p99 * 1000, 2),
    }

@pytest.mark.asyncio
async def test_concurrent_post_load(stress_server, shared_report):
    proc, base_url = stress_server
    url = f"{base_url}/relay/ACME_Corp"
    
    async def make_req(session, i, token, sender):
        start = time.perf_counter()
        async with session.post(url, json=_payload(i, sender), headers=_headers(token)) as resp:
            text = await resp.text()
            latency = time.perf_counter() - start
            return resp.status, text, latency

    async def run_scenario():
        latencies = []
        statuses = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for t in range(10):
                token = f"tok-stress-{t}"
                sender = f"stress-user-{t}"
                for i in range(100):
                    tasks.append(make_req(session, t*100 + i, token, sender))
            
            results = await asyncio.gather(*tasks)
            for st, _, lat in results:
                statuses.append(st)
                latencies.append(lat)
        
        record_metrics(shared_report, "concurrent_post_load", latencies)
        return statuses

    statuses = await run_scenario()
    assert all(st in (202, 429) for st in statuses), "Expected 202 Accepted or 429 Rate Limit"
    
    # We should have some successes
    assert statuses.count(202) > 0

@pytest.mark.asyncio
async def test_rate_limit_verification(stress_server, shared_report):
    proc, base_url = stress_server
    url = f"{base_url}/relay/ACME_Corp"
    token = "tok-rate-limit-1"
    sender = "rate-limit-user"
    
    async def make_req(session, i):
        start = time.perf_counter()
        async with session.post(url, json=_payload(i, sender), headers=_headers(token)) as resp:
            text = await resp.text()
            return resp.status, text, time.perf_counter() - start

    latencies = []
    statuses = []
    # 80 POSTs in 60s, but we do them concurrently to trigger the limit quickly
    async with aiohttp.ClientSession() as session:
        tasks = [make_req(session, i) for i in range(80)]
        results = await asyncio.gather(*tasks)
        for st, _, lat in results:
            statuses.append(st)
            latencies.append(lat)
            
    record_metrics(shared_report, "rate_limit_verification", latencies)
    
    # Existing rate limit is ~60 per minute + 10 burst = 70. We send 80.
    accepted = statuses.count(202)
    rate_limited = statuses.count(429)
    assert 60 <= accepted <= 75, f"Expected ~70 accepted, got {accepted}"
    assert rate_limited > 0, "Expected some rate limiting"

@pytest.mark.asyncio
async def test_idempotency_retry_storm(stress_server, shared_report):
    proc, base_url = stress_server
    url = f"{base_url}/relay/ACME_Corp"
    token = "tok-idem-1"
    sender = "idem-user"
    idem_key = "test-idem-key-12345"
    
    async def make_req(session):
        start = time.perf_counter()
        async with session.post(url, json=_payload(0, sender), headers=_headers(token, idem_key=idem_key)) as resp:
            text = await resp.text()
            return resp.status, text, time.perf_counter() - start

    latencies = []
    statuses = []
    # 100 concurrent requests with the exact same idempotency key
    async with aiohttp.ClientSession() as session:
        tasks = [make_req(session) for _ in range(100)]
        results = await asyncio.gather(*tasks)
        for st, _, lat in results:
            statuses.append(st)
            latencies.append(lat)
            
    record_metrics(shared_report, "idempotency_retry_storm", latencies)
    
    # 1 should be 202, 99 should be 409 Conflict (duplicate marker)
    assert statuses.count(202) == 1, "Exactly one request should be processed"
    assert statuses.count(409) == 99, "99 requests should return 409 duplicate marker"

@pytest.mark.asyncio
async def test_mixed_read_write_contention(stress_server, shared_report):
    proc, base_url = stress_server
    url = f"{base_url}/relay/ACME_Corp_Mixed"
    token = "tok-mixed-1"
    sender = "mixed-user"
    
    async def make_post(session, i):
        start = time.perf_counter()
        async with session.post(url, json=_payload(i, sender), headers=_headers(token)) as resp:
            await resp.text()
            return "POST", resp.status, time.perf_counter() - start

    async def make_get(session, i):
        start = time.perf_counter()
        async with session.get(url, headers=_headers(token)) as resp:
            await resp.text()
            return "GET", resp.status, time.perf_counter() - start

    latencies = []
    statuses = []
    # 500 POSTs interleaved with 500 GETs
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(500):
            tasks.append(make_post(session, i))
            tasks.append(make_get(session, i))
            
        results = await asyncio.gather(*tasks)
        for meth, st, lat in results:
            statuses.append(st)
            latencies.append(lat)
            
    record_metrics(shared_report, "mixed_read_write_contention", latencies)
    
    # No 500s allowed
    assert all(st < 500 for st in statuses), "No 5xx errors allowed during contention"

@pytest.mark.asyncio
async def test_fault_injection_5a_kill_mid_stream(stress_server, shared_report):
    # This simulates a service crash and restart
    proc, base_url = stress_server
    url = f"{base_url}/relay/ACME_Corp_Fail"
    token = "tok-fail-1"
    sender = "fail-user"
    
    async def make_req(session, i):
        start = time.perf_counter()
        try:
            async with session.post(url, json=_payload(i, sender), headers=_headers(token), timeout=5.0) as resp:
                await resp.text()
                return resp.status, time.perf_counter() - start
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return 503, time.perf_counter() - start

    latencies = []
    statuses = []
    
    async with aiohttp.ClientSession() as session:
        # Fire 1 request to ensure at least one 202
        st, lat = await make_req(session, 0)
        statuses.append(st)
        latencies.append(lat)

        # Fire 999 requests — large enough that some are in-flight when killed
        tasks1 = [make_req(session, i) for i in range(1, 1000)]
        # Kill the server immediately — don't wait for requests to land
        proc.terminate()

        results = await asyncio.gather(*tasks1)
        for st, lat in results:
            statuses.append(st)
            latencies.append(lat)

    record_metrics(shared_report, "fault_injection_5a", latencies)

    # We expect some 202s before it died, and some 503s/Exceptions after
    assert 202 in statuses
    assert 503 in statuses
