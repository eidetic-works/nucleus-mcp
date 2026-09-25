# Relay HTTP Stress Testing Harness

This directory contains the concurrent load and failure-injection test harness for the Nucleus HTTP relay service (`relay_route.py`).

## Requirements
The stress tests use `aiohttp` for concurrent client load generation and `pytest-benchmark` (optional) to hook into the pytest framework.
Ensure these are installed (they are in the `[dev]` optional dependencies of `pyproject.toml`).

```bash
pip install -e ".[dev]"
```

## Running the Harness Manually

Do **NOT** run these against the production OCI instance. The tests boot their own isolated local `nucleus-mcp-cloud` fixture on a dynamic port.

To run the complete stress suite:
```bash
pytest tests/stress/test_relay_http_load.py -v
```

This will run all scenarios:
1. 1000 concurrent POST requests
2. Rate-limit verification (70 POSTs in 60s)
3. Idempotency dedup under retry storms (100 concurrent identical POSTs)
4. Mixed read+write contention (500 POSTs + 500 GETs)
5. Failure injection (killing the server mid-stream to simulate 503s and restarts)

## Reports

Each successful execution will write a latency metrics JSON report to:
`.brain/stress_reports/relay_<UTC-timestamp>.json`

These reports capture the P50, P95, and P99 latency numbers for each scenario.
