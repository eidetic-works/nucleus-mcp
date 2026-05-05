"""Transport health sidecar — P0 fix #1 from 2026-04-18 Cascade feedback.

Problem: when the MCP stdio transport dies (broken pipe, panic, OOM),
consumers see only "transport closed" with no recovery hint, no pid, no
timestamp of last healthy state. They can't distinguish a crashed server
from a hung handler, can't auto-retry meaningfully, and can't tell the
user what to do next.

Solution: a lightweight sidecar HTTP server bound to a Unix domain
socket (with TCP fallback) that:

  - Runs as a daemon thread inside stdio_server.py, independent of the
    MCP transport event loop.
  - Exposes GET /health, GET /sessions, GET /last-heartbeat, POST /ping.
  - Writes a heartbeat to .brain/heartbeat/stdio.json every 2s.
  - Survives an MCP-side crash long enough for the consumer CLI
    (`nucleus health`) to surface diagnostics.

Acceptance (per 2026-04-18 review):
  - Socket at ~/.nucleus/health.sock is chmod 0600. Verified by os.stat.
  - Heartbeat interval <= 2s. Clients treat (now - last_healthy_at) > 2x
    interval as unhealthy regardless of ok flag.
  - Relay-drop policy on sidecar restart: log to
    .brain/ledger/relay_drops.jsonl, do NOT replay.

This module is transport-only — it does not route to MCP handlers.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import stat
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn, UnixStreamServer
from typing import Any, Dict, Optional

logger = logging.getLogger("nucleus.health_sidecar")


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DEFAULT_SOCKET_DIR = Path.home() / ".nucleus"
DEFAULT_SOCKET_FILE = "health.sock"
DEFAULT_TCP_HOST = "127.0.0.1"
HEARTBEAT_INTERVAL_SEC = 2.0
SOCKET_MODE = 0o600  # rw for owner only (acceptance criterion)

_state_lock = threading.Lock()
_state: Dict[str, Any] = {
    "started_at": None,
    "last_heartbeat_at": None,
    "last_tool_call_at": None,
    "pid": None,
    "sessions": [],
    "version": None,
    "status": "unknown",
}


# -----------------------------------------------------------------------------
# Public state API — called by stdio_server
# -----------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mark_started(pid: int, version: Optional[str] = None) -> None:
    with _state_lock:
        _state["pid"] = pid
        _state["version"] = version
        _state["started_at"] = _now_iso()
        _state["last_heartbeat_at"] = _state["started_at"]
        _state["status"] = "healthy"


def mark_tool_call() -> None:
    with _state_lock:
        _state["last_tool_call_at"] = _now_iso()


def mark_session_active(session_id: str) -> None:
    with _state_lock:
        if session_id not in _state["sessions"]:
            _state["sessions"].append(session_id)


def mark_session_closed(session_id: str) -> None:
    with _state_lock:
        if session_id in _state["sessions"]:
            _state["sessions"].remove(session_id)


def snapshot() -> Dict[str, Any]:
    with _state_lock:
        return dict(_state)


# -----------------------------------------------------------------------------
# Heartbeat writer — file-based, for out-of-process consumers
# -----------------------------------------------------------------------------


class HeartbeatWriter(threading.Thread):
    """Writes heartbeat JSON to `.brain/heartbeat/stdio.json` every interval."""

    def __init__(self, brain_path: Path, interval: float = HEARTBEAT_INTERVAL_SEC):
        super().__init__(daemon=True, name="nucleus-heartbeat")
        self.brain_path = Path(brain_path)
        self.interval = interval
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # pragma: no cover — background loop
        hb_path = self.brain_path / "heartbeat" / "stdio.json"
        hb_path.parent.mkdir(parents=True, exist_ok=True)
        while not self._stop.wait(self.interval):
            try:
                with _state_lock:
                    _state["last_heartbeat_at"] = _now_iso()
                    payload = dict(_state)
                self._atomic_write(hb_path, payload)
            except Exception as e:
                logger.debug("heartbeat write failed: %s", e)

    @staticmethod
    def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as f:
            json.dump(payload, f, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)


# -----------------------------------------------------------------------------
# HTTP handler
# -----------------------------------------------------------------------------


class _HealthHandler(BaseHTTPRequestHandler):
    # Silence default logging — we're running as a sidecar.
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover
        logger.debug("sidecar: " + format, *args)

    def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — stdlib contract
        path = self.path.rstrip("/") or "/"
        if path == "/health":
            snap = snapshot()
            is_stale = _is_heartbeat_stale(snap)
            snap["stale"] = is_stale
            snap["status"] = "stale" if is_stale else snap.get("status", "unknown")
            self._send_json(200, snap)
        elif path == "/sessions":
            self._send_json(200, {"sessions": snapshot()["sessions"]})
        elif path == "/last-heartbeat":
            self._send_json(200, {"last_heartbeat_at": snapshot()["last_heartbeat_at"]})
        else:
            self._send_json(404, {"error_type": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/") or "/"
        if path == "/ping":
            self._send_json(200, {"pong": _now_iso()})
        else:
            self._send_json(404, {"error_type": "not_found", "path": self.path})


def _is_heartbeat_stale(snap: Dict[str, Any]) -> bool:
    """True if last heartbeat is older than 2x interval."""
    last = snap.get("last_heartbeat_at")
    if not isinstance(last, str):
        return True
    try:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return age > 2 * HEARTBEAT_INTERVAL_SEC


# -----------------------------------------------------------------------------
# Sidecar server — UDS with TCP fallback
# -----------------------------------------------------------------------------


class _ThreadingUnixServer(ThreadingMixIn, UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


class HealthSidecar:
    """Manages the sidecar HTTP server lifecycle."""

    def __init__(
        self,
        *,
        socket_dir: Path = DEFAULT_SOCKET_DIR,
        socket_file: str = DEFAULT_SOCKET_FILE,
        tcp_port: Optional[int] = None,
    ):
        self.socket_dir = Path(socket_dir)
        self.socket_path = self.socket_dir / socket_file
        self.tcp_port = tcp_port
        self._server: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._heartbeat: Optional[HeartbeatWriter] = None

    def start(self, brain_path: Path) -> str:
        """Start the sidecar. Returns the bound address string."""
        self.socket_dir.mkdir(parents=True, exist_ok=True)

        # Clean up any stale socket from a prior run.
        try:
            if self.socket_path.exists() or self.socket_path.is_symlink():
                self.socket_path.unlink()
        except OSError:
            pass

        bound: str
        if self.tcp_port is None:
            server = _ThreadingUnixServer(str(self.socket_path), _HealthHandler)
            # Acceptance criterion: socket must be 0600.
            os.chmod(self.socket_path, SOCKET_MODE)
            bound = f"unix://{self.socket_path}"
        else:
            server = ThreadingHTTPServer((DEFAULT_TCP_HOST, self.tcp_port), _HealthHandler)
            bound = f"http://{DEFAULT_TCP_HOST}:{self.tcp_port}"

        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            name="nucleus-health-sidecar",
            daemon=True,
        )
        self._thread.start()

        self._heartbeat = HeartbeatWriter(brain_path)
        self._heartbeat.start()

        mark_started(os.getpid())
        logger.info("health sidecar started at %s", bound)
        return bound

    def stop(self) -> None:
        if self._heartbeat is not None:
            self._heartbeat.stop()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self.tcp_port is None:
            try:
                if self.socket_path.exists():
                    self.socket_path.unlink()
            except OSError:
                pass

    def socket_mode(self) -> Optional[int]:
        """Return the socket's mode bits (for tests). UDS only."""
        if self.tcp_port is not None or not self.socket_path.exists():
            return None
        return stat.S_IMODE(os.stat(self.socket_path).st_mode)


# -----------------------------------------------------------------------------
# Simple client — for `nucleus health` CLI
# -----------------------------------------------------------------------------


def query(
    endpoint: str = "/health",
    *,
    socket_path: Optional[Path] = None,
    tcp_port: Optional[int] = None,
    timeout: float = 1.0,
) -> Dict[str, Any]:
    """Query the sidecar. Returns parsed JSON response or structured error."""
    try:
        if tcp_port is not None:
            import http.client
            conn = http.client.HTTPConnection(DEFAULT_TCP_HOST, tcp_port, timeout=timeout)
            conn.request("GET", endpoint)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            conn.close()
            return json.loads(body)
        path = Path(socket_path) if socket_path else (DEFAULT_SOCKET_DIR / DEFAULT_SOCKET_FILE)
        if not path.exists():
            return {
                "error_type": "transport_closed",
                "recovery_hint": "nucleus-mcp not running; start via `nucleus init` + restart MCP host",
                "detail": f"no socket at {path}",
            }
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(path))
        req = f"GET {endpoint} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        sock.sendall(req.encode("utf-8"))
        chunks = []
        while True:
            data = sock.recv(4096)
            if not data:
                break
            chunks.append(data)
        sock.close()
        raw = b"".join(chunks).decode("utf-8", errors="replace")
        _, _, body = raw.partition("\r\n\r\n")
        try:
            return json.loads(body)
        except ValueError:
            return {"error_type": "handler_error", "recovery_hint": "sidecar returned non-JSON", "detail": body[:200]}
    except (OSError, ConnectionError, socket.timeout) as e:
        return {
            "error_type": "transport_closed",
            "recovery_hint": "sidecar unreachable — MCP host may be dead",
            "detail": str(e),
        }


__all__ = [
    "HealthSidecar",
    "HeartbeatWriter",
    "mark_started",
    "mark_tool_call",
    "mark_session_active",
    "mark_session_closed",
    "snapshot",
    "query",
    "HEARTBEAT_INTERVAL_SEC",
    "SOCKET_MODE",
]
