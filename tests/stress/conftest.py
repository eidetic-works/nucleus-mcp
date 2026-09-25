import os
import sys
import time
import socket
import subprocess
import pytest
import pytest_asyncio
from pathlib import Path

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def _wait_for_server(host: str, port: int, timeout: float = 15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"Server at {host}:{port} did not start within {timeout}s")

def _start_server(tmp_path, module, extra_env=None):
    port = _free_port()
    src_dir = Path(__file__).parent.parent.parent / "src"
    root_dir = Path(__file__).parent.parent.parent
    
    # Create the token map for all our test tokens
    token_map = {}
    for i in range(10):
        token_map[f"tok-stress-{i}"] = f"stress-user-{i}"
    token_map["tok-rate-limit-1"] = "rate-limit-user"
    token_map["tok-idem-1"] = "idem-user"
    token_map["tok-mixed-1"] = "mixed-user"
    token_map["tok-fail-1"] = "fail-user"
    
    import json
    env = {
        **os.environ,
        "PYTHONPATH": str(src_dir) + os.pathsep + str(root_dir) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "NUCLEUS_BRAIN_ROOT": str(tmp_path / "brains"),
        "NUCLEUS_RELAY_TOKEN_MAP": json.dumps(token_map),
        "NUCLEUS_RELAY_RATE_PER_RECIPIENT": "100",
        "NUCLEUS_LOG_LEVEL": "WARNING",
        "NUCLEUS_HTTP_HOST": "127.0.0.1",
        "PORT": str(port),
    }
    env.pop("NUCLEAR_BRAIN_PATH", None)
    env.pop("NUCLEUS_TENANT_ID", None)

    if extra_env:
        env.update(extra_env)

    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server("127.0.0.1", port)
    except TimeoutError:
        proc.kill()
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Server failed to start: {stderr[-500:]}")
    return proc, f"http://127.0.0.1:{port}"

def _stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

@pytest.fixture
def stress_server(tmp_path):
    """Start a real cloud server subprocess for stress testing."""
    # We use auth so we can simulate multiple different users/bearer tokens.
    # But wait, relay route uses Authorization header? Yes, Bearer token.
    # The instructions say "across 10 bearer tokens". The app accepts anything if NUCLEUS_REQUIRE_AUTH is not strictly set, or it maps tenants.
    # Let's start it without REQUIRE_AUTH if we don't need tenant mapping, or with it if we do. 
    # Let's just start standard cloud app.
    proc, base_url = _start_server(tmp_path, "tests.stress.app")
    yield proc, base_url
    _stop_server(proc)
