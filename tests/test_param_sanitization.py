"""
Tests for _dispatch.py input sanitization.

Verifies:
- None params → empty dict
- Non-dict params → ValueError
- Forbidden keys stripped
- Nested depth limit enforced
- String length cap enforced
- Param count limit enforced
- None values stripped
- Non-string keys skipped
- Integration: sanitized params reach dispatch handlers correctly
- Integration: violations produce JSON error responses from dispatch
"""

import json
import pytest

from mcp_server_nucleus.tools._dispatch import (
    sanitize_params,
    dispatch,
    get_dispatch_telemetry,
    _MAX_PARAM_DEPTH,
    _MAX_STRING_LENGTH,
    _MAX_PARAMS_COUNT,
    _FORBIDDEN_KEYS,
)


@pytest.fixture(autouse=True)
def reset_telemetry():
    get_dispatch_telemetry().reset()
    yield
    get_dispatch_telemetry().reset()


# ============================================================
# UNIT: sanitize_params
# ============================================================

class TestSanitizeParams:
    def test_none_returns_empty_dict(self):
        assert sanitize_params(None) == {}

    def test_empty_dict_passthrough(self):
        assert sanitize_params({}) == {}

    def test_normal_params_passthrough(self):
        p = {"key": "val", "count": 42, "flag": True}
        assert sanitize_params(p) == p

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            sanitize_params("not a dict")
        with pytest.raises(ValueError, match="must be a dict"):
            sanitize_params([1, 2, 3])

    def test_forbidden_keys_stripped(self):
        p = {"good_key": "val", "__proto__": "evil", "constructor": "bad"}
        result = sanitize_params(p)
        assert result == {"good_key": "val"}

    def test_all_forbidden_keys(self):
        for fk in _FORBIDDEN_KEYS:
            result = sanitize_params({fk: "evil", "safe": 1})
            assert fk not in result
            assert result == {"safe": 1}

    def test_none_values_stripped(self):
        p = {"a": 1, "b": None, "c": "hello", "d": None}
        result = sanitize_params(p)
        assert result == {"a": 1, "c": "hello"}

    def test_nested_dict_sanitized(self):
        p = {"outer": {"inner": "val", "__proto__": "evil", "x": None}}
        result = sanitize_params(p)
        assert result == {"outer": {"inner": "val"}}

    def test_depth_limit_enforced(self):
        # Build a dict nested _MAX_PARAM_DEPTH + 2 levels deep
        d = {"leaf": "val"}
        for _ in range(_MAX_PARAM_DEPTH + 2):
            d = {"nested": d}
        with pytest.raises(ValueError, match="nested too deep"):
            sanitize_params(d)

    def test_depth_limit_at_boundary(self):
        # Exactly at max depth should work
        d = {"leaf": "val"}
        for _ in range(_MAX_PARAM_DEPTH):
            d = {"nested": d}
        result = sanitize_params(d)
        assert "nested" in result

    def test_string_length_cap(self):
        long_str = "x" * (_MAX_STRING_LENGTH + 1)
        with pytest.raises(ValueError, match="string too long"):
            sanitize_params({"big": long_str})

    def test_string_at_limit_passes(self):
        ok_str = "x" * _MAX_STRING_LENGTH
        result = sanitize_params({"big": ok_str})
        assert len(result["big"]) == _MAX_STRING_LENGTH

    def test_param_count_limit(self):
        too_many = {f"k{i}": i for i in range(_MAX_PARAMS_COUNT + 1)}
        with pytest.raises(ValueError, match="too many params"):
            sanitize_params(too_many)

    def test_param_count_at_limit_passes(self):
        ok = {f"k{i}": i for i in range(_MAX_PARAMS_COUNT)}
        result = sanitize_params(ok)
        assert len(result) == _MAX_PARAMS_COUNT

    def test_non_string_keys_skipped(self):
        p = {"good": 1, 42: "bad", True: "also_bad"}
        result = sanitize_params(p)
        assert result == {"good": 1}

    def test_lists_pass_through(self):
        p = {"tags": ["a", "b"], "ids": [1, 2, 3]}
        result = sanitize_params(p)
        assert result == p

    def test_module_action_in_error_message(self):
        with pytest.raises(ValueError, match="nucleus_test.do_thing"):
            sanitize_params("bad", module_name="nucleus_test", action="do_thing")


# ============================================================
# INTEGRATION: dispatch + sanitization
# ============================================================

def _echo_handler(**kwargs):
    return kwargs

ROUTER = {"echo": _echo_handler}


class TestDispatchSanitization:
    def test_none_params_dispatches_ok(self):
        # params=None should become {} and handler gets no kwargs
        result = json.loads(dispatch("echo", None, ROUTER, "test"))
        assert result == {}

    def test_forbidden_key_stripped_before_handler(self):
        result = json.loads(dispatch("echo", {"ok": 1, "__proto__": "x"}, ROUTER, "test"))
        assert result == {"ok": 1}

    def test_none_values_stripped_before_handler(self):
        result = json.loads(dispatch("echo", {"a": 1, "b": None}, ROUTER, "test"))
        assert result == {"a": 1}

    def test_non_dict_returns_json_error(self):
        result = json.loads(dispatch("echo", "bad_params", ROUTER, "test"))
        assert "error" in result
        assert "must be a dict" in result["error"]

    def test_too_deep_returns_json_error(self):
        d = {"leaf": 1}
        for _ in range(_MAX_PARAM_DEPTH + 2):
            d = {"n": d}
        result = json.loads(dispatch("echo", d, ROUTER, "test"))
        assert "error" in result
        assert "nested too deep" in result["error"]

    def test_sanitization_error_recorded_in_telemetry(self):
        dispatch("echo", "bad", ROUTER, "test_mod")
        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_errors"] >= 1
