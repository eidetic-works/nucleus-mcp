"""Tests for runtime.health_check — circuit breaker + engram cache error paths.

Regression coverage, added with zero prior test coverage on these two
functions. ``check_circuit_breakers`` and ``check_engram_cache`` split their
error handling into two except blocks, mirroring ``check_hardening`` /
``check_rate_limiter`` elsewhere in this file:

- ``except ImportError`` -> ``DEGRADED`` + a message (the genuinely benign
  case: the optional module simply isn't installed).
- ``except Exception`` -> ``UNHEALTHY`` + ``"error": str(e)`` (a real runtime
  failure surfaced, not hidden).

Without this split (a bare ``except Exception`` returning ``HEALTHY``
unconditionally — the shape of this file's still-open ``check_event_log``
corruption-detection question, and the pattern already fixed several times
elsewhere in this repo under "reports-clean-without-checking"), a genuine
runtime failure (KeyError on a malformed breaker-state dict, TypeError from
``cache.stats``) would be reported healthy to monitoring/load-balancers,
indistinguishable from the module simply not being installed. These tests
pin all three paths for both functions — healthy, ImportError, and runtime
exception — so a future regression back to the bare-except shape fails loudly.
"""
from __future__ import annotations

import sys
import types

import pytest

from mcp_server_nucleus.runtime import health_check
from mcp_server_nucleus.runtime.health_check import HealthStatus


# ---------------------------------------------------------------------------
# Helpers: install / remove fake submodules under the runtime package so the
# ``from .<mod> import <name>`` lines inside the check functions resolve to
# our fakes. We mutate sys.modules directly because the check functions do a
# local import each call (no module-level import to monkeypatch).
# ---------------------------------------------------------------------------

def _install_module(monkeypatch, modname: str, attrs: dict):
    """Register a fake ``mcp_server_nucleus.runtime.<modname>`` module."""
    pkg_name = "mcp_server_nucleus.runtime"
    pkg = sys.modules.get(pkg_name)
    full = f"{pkg_name}.{modname}"
    fake = types.ModuleType(full)
    for k, v in attrs.items():
        setattr(fake, k, v)
    monkeypatch.setitem(sys.modules, full, fake)
    if pkg is not None:
        monkeypatch.setattr(pkg, modname, fake, raising=False)
    return fake


def _force_importerror(monkeypatch, modname: str):
    """Make ``from .<modname> import X`` raise ImportError."""
    pkg_name = "mcp_server_nucleus.runtime"
    full = f"{pkg_name}.{modname}"

    def _raise_import(name, *args, **kwargs):
        raise ImportError(f"fake: {name} not installed")

    # Remove any cached module so the import machinery re-runs __import__.
    monkeypatch.setitem(sys.modules, full, None)
    real_import = __import__("builtins").__import__

    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == full:
            raise ImportError(f"fake: {modname} not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", patched_import)


# ===========================================================================
# check_circuit_breakers
# ===========================================================================

class TestCheckCircuitBreakers:
    def test_healthy_when_all_breakers_closed(self, monkeypatch):
        breaker_status = {
            "redis": {"state": "closed"},
            "postgres": {"state": "closed"},
        }
        _install_module(
            monkeypatch,
            "circuit_breaker",
            {"get_all_breaker_status": lambda: breaker_status},
        )

        result = health_check.check_circuit_breakers()

        assert result["component"] == "circuit_breakers"
        assert result["status"] == HealthStatus.HEALTHY
        assert result["open_count"] == 0
        assert result["open_names"] == []
        assert result["breakers"] == breaker_status

    def test_degraded_when_breaker_open(self, monkeypatch):
        breaker_status = {
            "redis": {"state": "open"},
            "postgres": {"state": "closed"},
        }
        _install_module(
            monkeypatch,
            "circuit_breaker",
            {"get_all_breaker_status": lambda: breaker_status},
        )

        result = health_check.check_circuit_breakers()

        assert result["status"] == HealthStatus.DEGRADED
        assert result["open_count"] == 1
        assert result["open_names"] == ["redis"]

    def test_importerror_returns_degraded_with_existing_message(self, monkeypatch):
        _force_importerror(monkeypatch, "circuit_breaker")

        result = health_check.check_circuit_breakers()

        assert result["component"] == "circuit_breakers"
        assert result["status"] == HealthStatus.DEGRADED
        assert result["message"] == "Circuit breaker module not available"
        # The benign ImportError path must NOT surface an "error" key.
        assert "error" not in result

    def test_runtime_exception_returns_unhealthy_with_error(self, monkeypatch):
        # Regression test: a real runtime failure must NOT be reported HEALTHY.
        def boom():
            raise KeyError("state")

        _install_module(
            monkeypatch,
            "circuit_breaker",
            {"get_all_breaker_status": boom},
        )

        result = health_check.check_circuit_breakers()

        assert result["component"] == "circuit_breakers"
        assert result["status"] == HealthStatus.UNHEALTHY
        assert "error" in result
        assert "state" in result["error"]
        # The pre-fix bug returned HEALTHY + "message"; pin that it no longer does.
        assert result.get("message") != "Circuit breaker module not available"

    def test_runtime_typeerror_returns_unhealthy(self, monkeypatch):
        def boom():
            raise TypeError("breaker state is not subscriptable")

        _install_module(
            monkeypatch,
            "circuit_breaker",
            {"get_all_breaker_status": boom},
        )

        result = health_check.check_circuit_breakers()

        assert result["status"] == HealthStatus.UNHEALTHY
        assert "error" in result


# ===========================================================================
# check_engram_cache
# ===========================================================================

class TestCheckEngramCache:
    def _good_cache(self):
        class _Cache:
            stats = {
                "cached_engrams": 5,
                "unique_keys": 3,
                "contexts": 2,
                "load_count": 11,
            }

        return _Cache()

    def test_healthy_path(self, monkeypatch):
        cache = self._good_cache()
        _install_module(
            monkeypatch,
            "engram_cache",
            {"get_engram_cache": lambda: cache},
        )

        result = health_check.check_engram_cache()

        assert result["component"] == "engram_cache"
        assert result["status"] == HealthStatus.HEALTHY
        assert result["cached_engrams"] == 5
        assert result["unique_keys"] == 3
        assert result["contexts"] == 2
        assert result["load_count"] == 11

    def test_importerror_returns_degraded_with_existing_message(self, monkeypatch):
        _force_importerror(monkeypatch, "engram_cache")

        result = health_check.check_engram_cache()

        assert result["component"] == "engram_cache"
        assert result["status"] == HealthStatus.DEGRADED
        assert result["message"] == "Engram cache module not available"
        assert "error" not in result

    def test_runtime_exception_returns_unhealthy_with_error(self, monkeypatch):
        # Regression test: a real runtime failure must NOT be reported HEALTHY.
        class _BadCache:
            @property
            def stats(self):
                raise TypeError("stats() returned None, not a dict")

        _install_module(
            monkeypatch,
            "engram_cache",
            {"get_engram_cache": lambda: _BadCache()},
        )

        result = health_check.check_engram_cache()

        assert result["component"] == "engram_cache"
        assert result["status"] == HealthStatus.UNHEALTHY
        assert "error" in result
        assert "stats" in result["error"]
        # Pin the pre-fix bug is gone: no HEALTHY + "message" combo.
        assert result.get("message") != "Engram cache module not available"

    def test_runtime_keyerror_returns_unhealthy(self, monkeypatch):
        class _PartialCache:
            @property
            def stats(self):
                # Missing keys -> KeyError on the success path, which must be
                # caught by the runtime-failure branch, not the ImportError one.
                return {"cached_engrams": 1}

        _install_module(
            monkeypatch,
            "engram_cache",
            {"get_engram_cache": lambda: _PartialCache()},
        )

        result = health_check.check_engram_cache()

        assert result["status"] == HealthStatus.UNHEALTHY
        assert "error" in result
        assert "unique_keys" in result["error"]
