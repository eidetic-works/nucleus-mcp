"""Tool-layer tests for nucleus_delegate (cross-vendor dispatch facade).

Verifies the THIN facade over runtime.vendor_dispatch:
  - action='dispatch' with cross-vendor enabled → calls dispatch_and_capture
    and returns its captured result (status, vendor output, artifact_ref,
    capture path).
  - action='list' → returns available vendors (VENDOR_SPECS keys) + the
    cross_vendor_enabled() flag.
  - action='dispatch' with cross-vendor DISABLED → returns a clear error
    string telling the caller to run `nucleus onboard` first; does NOT crash
    and never invokes the executor.
  - unknown vendor → clear error, no executor call.
  - missing prompt / artifact_ref → clear error, no executor call.
  - action='review' wraps content in the hardened verdict-format prompt and
    dispatches via dispatch_and_capture; returns the captured result.
  - action='review' missing content → clear error, no executor call.
  - action='review' with cross-vendor DISABLED → clear error, no executor call.
  - the tool registers under the name `nucleus_delegate`.
"""

import asyncio
import json

import pytest

from mcp_server_nucleus.tools import vendor_delegate


class _StubMcp:
    """Captures @mcp.tool-decorated facades by fn name (mirrors test_audit_log_tool)."""

    def __init__(self):
        self.registered = {}

    def tool(self, **kwargs):
        def decorator(fn):
            self.registered[fn.__name__] = fn
            return fn
        return decorator


def _make_response(ok, data=None, error=None):
    return json.dumps({"success": ok, "data": data, "error": error})


@pytest.fixture
def tool_fn(monkeypatch):
    # Ensure a clean enablement state per test (no env, no onboard config).
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    mcp = _StubMcp()
    helpers = {"make_response": _make_response}
    vendor_delegate.register(mcp, helpers)
    return mcp.registered["nucleus_delegate"]


# ── registration ─────────────────────────────────────────────────────────────

def test_tool_registers_as_nucleus_delegate(tool_fn):
    # The facade MUST register under the exact name `nucleus_delegate` so any
    # agent connected to nucleus sees it in its MCP tool list.
    assert tool_fn is not None
    assert tool_fn.__name__ == "nucleus_delegate"


# ── action='dispatch' (enabled) ──────────────────────────────────────────────

async def test_dispatch_enabled_returns_captured_result(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    captured = {
        "vendor": "agy",
        "model_family": "gemini",
        "model_id": "gemini-3.1-pro-high",
        "rc": 0,
        "status": "ok",
        "result": "review looks good",
        "duration": 1.23,
        "prompt_digest": "sha256:abc",
        "artifact_ref": "deadbeef",
        "to": "cross_vendor",
        "mode": "write",
        "effect": "unknown",
        "changed_paths": [],
        "capture": {"relay": {"sent": True}, "engram": {}},
    }

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        assert vendor == "agy"
        assert prompt == "review this diff"
        # The tool MUST blank any caller-supplied artifact_ref before calling
        # dispatch_and_capture, which stamps it from the worktree HEAD SHA.
        # Previously this asserted == "deadbeef", pinning the forgeable
        # passthrough that PRINCIPAL v3 line 77 forbids.
        assert artifact_ref == ""
        assert to_role == "cross_vendor"
        return captured

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )

    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy",
        "prompt": "review this diff",
        "artifact_ref": "deadbeef",
    }))
    assert out["success"] is True
    data = out["data"]
    assert data["status"] == "ok"
    assert data["vendor"] == "agy"
    assert data["result"] == "review looks good"
    assert data["artifact_ref"] == "deadbeef"
    assert data["capture"]["relay"]["sent"] is True


async def test_dispatch_passes_to_role_override(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["to_role"] = to_role
        return {"status": "ok", "result": "", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin",
        "prompt": "build it",
        "artifact_ref": "PR#42",
        "to": "main",
    }))
    assert out["success"] is True
    assert seen["to_role"] == "main"


# ── action='dispatch' (DISABLED — gating, no crash) ──────────────────────────

async def test_dispatch_disabled_returns_clear_error_no_crash(tool_fn, monkeypatch):
    # cross-vendor OFF: no env, no onboard config (fixture already cleared env).
    # Patch the onboard config reader to guarantee disabled regardless of host.
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vendor_dispatch._onboard_config_enabled",
        lambda: False,
    )
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy",
        "prompt": "x",
        "artifact_ref": "y",
    }))
    assert out["success"] is False
    assert "nucleus onboard" in out["error"]
    # The executor MUST NOT have been invoked when the gate is closed.
    assert called["n"] == 0


# ── action='list' ────────────────────────────────────────────────────────────

async def test_list_returns_vendors_and_enabled_flag(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    out = json.loads(await tool_fn("list", {}))
    assert out["success"] is True
    data = out["data"]
    # VENDOR_SPECS keys are the available vendors.
    assert {"agy", "devin"}.issubset(set(data["vendors"]))
    assert data["cross_vendor_enabled"] is True
    # Each vendor carries its static spec summary.
    assert "agy" in data["vendor_specs"]
    assert data["vendor_specs"]["agy"]["model_family"] == "gemini"
    assert data["vendor_specs"]["devin"]["model_family"] == "swe"
    assert data["vendor_specs"]["devin"]["model_families"]["swe-2-max"] == "swe"
    assert data["vendor_specs"]["devin"]["model_families"]["swe-1-7"] == "swe"
    assert data["vendor_specs"]["devin"]["model_families"]["glm-5-2"] == "glm"


async def test_list_reports_disabled_flag(tool_fn, monkeypatch):
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vendor_dispatch._onboard_config_enabled",
        lambda: False,
    )
    out = json.loads(await tool_fn("list", {}))
    assert out["success"] is True
    assert out["data"]["cross_vendor_enabled"] is False


# ── validation (enabled, but bad params) ─────────────────────────────────────

async def test_dispatch_unknown_vendor_clear_error(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "chatgpt",
        "prompt": "x",
        "artifact_ref": "y",
    }))
    assert out["success"] is False
    assert "chatgpt" in out["error"]


async def test_dispatch_missing_prompt_clear_error(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy",
        "artifact_ref": "y",
    }))
    assert out["success"] is False
    assert "prompt" in out["error"]


async def test_dispatch_without_artifact_ref_is_accepted(tool_fn, monkeypatch):
    """INVERTED 2026-07-31. This previously asserted that omitting
    artifact_ref was a clear ERROR — i.e. the caller was REQUIRED to supply
    the binding that G1 crit-4 reads as proof of cross-vendor coordination.
    PRINCIPAL v3 line 77 forbids the schema accepting it at all, so omitting
    it is now the normal, correct case: the capture instrument stamps it from
    the vendor worktree's git HEAD SHA.
    """
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["artifact_ref"] = artifact_ref
        return {"vendor": vendor, "status": "ok", "rc": 0, "result": "ok",
                "artifact_ref": "b" * 40, "artifact_ref_source": "vendor_derived",
                "capture": {"relay": {"sent": True}, "engram": None}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )

    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy",
        "prompt": "x",
    }))
    assert out["success"] is True, out
    # Nothing was supplied and nothing was invented — the tool passes "" and
    # the instrument does the stamping.
    assert seen["artifact_ref"] == ""
    assert out["data"]["artifact_ref_source"] == "vendor_derived"


# ── action='review' (enabled) ────────────────────────────────────────────────

async def test_review_wraps_content_in_verdict_prompt_and_dispatches(tool_fn, monkeypatch):
    """review builds the hardened verdict-format prompt around the content and
    dispatches via dispatch_and_capture, returning its captured result.
    Default vendor is now 'agy' (diverse Gemini lens)."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    captured = {
        "vendor": "agy",
        "model_family": "gemini",
        "model_id": "gemini-3.1-pro-high",
        "rc": 0,
        "status": "ok",
        "result": "SOUND\nnone",
        "duration": 0.9,
        "prompt_digest": "sha256:xyz",
        "artifact_ref": "review",
        "to": "cross_vendor",
        "mode": "read",
        "effect": "unknown",
        "changed_paths": [],
        "capture": {"relay": {"sent": True}, "engram": {}},
    }
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["vendor"] = vendor
        seen["prompt"] = prompt
        seen["artifact_ref"] = artifact_ref
        seen["to_role"] = to_role
        seen["model"] = model
        seen["mode"] = mode
        return captured

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )

    content = "def add(a, b):\n    return a + b\n"
    out = json.loads(await tool_fn("review", {"content": content}))

    # Dispatched to the default vendor 'agy' with the default ref 'review',
    # forced read mode, and the agy default model.
    assert out["success"] is True
    assert seen["vendor"] == "agy"
    assert seen["artifact_ref"] == "review"
    assert seen["to_role"] == "cross_vendor"
    assert seen["mode"] == "read"
    assert seen["model"] == "gemini-3.1-pro-high"
    # The hardened verdict-format prompt wraps the content.
    assert "one-word verdict" in seen["prompt"]
    assert content in seen["prompt"]
    # The captured result is returned verbatim (same shape as 'dispatch').
    data = out["data"]
    assert data["status"] == "ok"
    assert data["vendor"] == "agy"
    assert data["result"] == "SOUND\nnone"
    assert data["artifact_ref"] == "review"
    assert data["capture"]["relay"]["sent"] is True


async def test_review_passes_ref_vendor_and_to_overrides(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen.update(vendor=vendor, artifact_ref=artifact_ref, to_role=to_role)
        return {"status": "ok", "result": "RISKY\noff-by-one", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("review", {
        "content": "x = x + 1",
        "ref": "PR#99",
        "vendor": "agy",
        "to": "main",
    }))
    assert out["success"] is True
    assert seen["vendor"] == "agy"
    assert seen["artifact_ref"] == "PR#99"
    assert seen["to_role"] == "main"


# ── action='review' (validation + gating) ────────────────────────────────────

async def test_review_missing_content_clear_error(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("review", {}))
    assert out["success"] is False
    assert "content" in out["error"]
    assert called["n"] == 0


async def test_review_unknown_vendor_clear_error(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("review", {
        "content": "x",
        "vendor": "chatgpt",
    }))
    assert out["success"] is False
    assert "chatgpt" in out["error"]
    assert called["n"] == 0


async def test_review_disabled_returns_clear_error_no_crash(tool_fn, monkeypatch):
    # cross-vendor OFF: no env (fixture cleared it), no onboard config.
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vendor_dispatch._onboard_config_enabled",
        lambda: False,
    )
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("review", {"content": "x"}))
    assert out["success"] is False
    assert "nucleus onboard" in out["error"]
    # The executor MUST NOT have been invoked when the gate is closed.
    assert called["n"] == 0


# ── default capture bucket is 'cross_vendor' (not 'peer') ─────────────────────

async def test_dispatch_no_to_defaults_to_cross_vendor(tool_fn, monkeypatch):
    """dispatch with NO `to` param must capture to the dedicated 'cross_vendor'
    bucket — cross-vendor envelopes are audit/census records, not peer-lane
    messages."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["to_role"] = to_role
        return {"status": "ok", "result": "", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin",
        "prompt": "build it",
        "artifact_ref": "PR#42",
    }))
    assert out["success"] is True
    assert seen["to_role"] == "cross_vendor"


async def test_dispatch_explicit_to_peer_still_routes_to_peer(tool_fn, monkeypatch):
    """An explicit to='peer' override must still route to 'peer' — only the
    DEFAULT changes; the param remains fully overridable."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["to_role"] = to_role
        return {"status": "ok", "result": "", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin",
        "prompt": "build it",
        "artifact_ref": "PR#42",
        "to": "peer",
    }))
    assert out["success"] is True
    assert seen["to_role"] == "peer"


async def test_review_no_to_defaults_to_cross_vendor(tool_fn, monkeypatch):
    """review with NO `to` param must capture to 'cross_vendor'."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["to_role"] = to_role
        return {"status": "ok", "result": "", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("review", {"content": "x = 1"}))
    assert out["success"] is True
    assert seen["to_role"] == "cross_vendor"


async def test_review_explicit_to_peer_still_routes_to_peer(tool_fn, monkeypatch):
    """An explicit to='peer' override on review must still route to 'peer'."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["to_role"] = to_role
        return {"status": "ok", "result": "", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("review", {"content": "x = 1", "to": "peer"}))
    assert out["success"] is True
    assert seen["to_role"] == "peer"


# ── Regression tests: cold-start hardening (tool layer) ───────────────────────
# Items 19-24: MCP handler coverage for the harden spec.

# 19. _h_dispatch model/mode validation + forwarding
async def test_dispatch_model_forwarded(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["model"] = model
        seen["mode"] = mode
        return {"status": "ok", "result": "ok", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
        # A currently-selectable non-default model, so this still proves the
        # model is FORWARDED rather than defaulted. swe-2-max is the current
        # default; swe-1-7-medium is a selectable fallback.
        "model": "swe-1-7-medium",
    }))
    assert out["success"] is True
    assert seen["model"] == "swe-1-7-medium"


async def test_dispatch_bogus_model_never_invokes_executor(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
        "model": "bogus",
    }))
    assert out["success"] is False
    # The rejection must name the real alternatives, so pin the current
    # default rather than a model the cost freeze removed.
    assert "swe-2-max" in out["error"]
    assert called["n"] == 0


async def test_dispatch_bogus_mode_never_invokes_executor(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
        "mode": "bogus",
    }))
    assert out["success"] is False
    assert "read" in out["error"] or "write" in out["error"]
    assert called["n"] == 0


# 20. disabled gate before model/mode validation
async def test_dispatch_disabled_gate_before_validation(tool_fn, monkeypatch):
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vendor_dispatch._onboard_config_enabled",
        lambda: False,
    )
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    # Even with bogus model/mode, the gate fires FIRST → _DISABLED_MSG
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
        "model": "bogus", "mode": "bogus",
    }))
    assert out["success"] is False
    assert "nucleus onboard" in out["error"]
    assert called["n"] == 0


# 21. _h_dispatch success gating
async def test_dispatch_success_gating(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    def _make_dispatch(status, effect="unknown"):
        def _fd(v, p, a, *, to_role=None, model=None, mode="write",
                expect_paths=None, timeout_s=None):
            return {"status": status, "effect": effect, "result": "x",
                    "changed_paths": [], "capture": {}}
        return _fd

    # empty_output → success False, error mentions no-op/no output
    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _make_dispatch("empty_output"),
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
    }))
    assert out["success"] is False
    assert "no" in out["error"].lower()
    assert out["data"] is not None

    # ok + no_files_touched → success False, error mentions files
    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _make_dispatch("ok", "no_files_touched"),
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
    }))
    assert out["success"] is False
    assert "file" in out["error"].lower()

    # ok + files_touched → success True
    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _make_dispatch("ok", "files_touched"),
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
    }))
    assert out["success"] is True

    # ok + effect unknown (no expect_paths) → success True (common case)
    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _make_dispatch("ok", "unknown"),
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
    }))
    assert out["success"] is True

    # not_found → success False, error mentions nucleus onboard
    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _make_dispatch("not_found"),
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
    }))
    assert out["success"] is False
    assert "nucleus onboard" in out["error"]


# 22. _h_dispatch forwards expect_paths
async def test_dispatch_forwards_expect_paths(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(v, p, a, *, to_role=None, model=None, mode="write",
                       expect_paths=None, timeout_s=None):
        seen["expect_paths"] = expect_paths
        return {"status": "ok", "effect": "unknown", "result": "x", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "devin", "prompt": "x", "artifact_ref": "y",
        "expect_paths": ["a.py", "b.py"],
    }))
    assert out["success"] is True
    assert seen["expect_paths"] == ["a.py", "b.py"]


# 23. _h_review default vendor agy + success gating
async def test_review_default_vendor_agy(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(v, p, a, *, to_role=None, model=None, mode="write",
                       expect_paths=None, timeout_s=None):
        seen["vendor"] = v
        seen["model"] = model
        seen["mode"] = mode
        return {"status": "ok", "effect": "unknown", "result": "x", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("review", {"content": "x"}))
    assert out["success"] is True
    assert seen["vendor"] == "agy"
    assert seen["model"] == "gemini-3.1-pro-high"
    assert seen["mode"] == "read"


async def test_review_empty_output_success_false(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    def _fake_dispatch(v, p, a, *, to_role=None, model=None, mode="write",
                       expect_paths=None, timeout_s=None):
        return {"status": "empty_output", "effect": "unknown", "result": "",
                "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("review", {"content": "x"}))
    assert out["success"] is False


async def test_review_vendor_devin_routes_devin(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(v, p, a, *, to_role=None, model=None, mode="write",
                       expect_paths=None, timeout_s=None):
        seen["vendor"] = v
        seen["mode"] = mode
        return {"status": "ok", "effect": "unknown", "result": "x", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("review", {"content": "x", "vendor": "devin"}))
    assert out["success"] is True
    assert seen["vendor"] == "devin"
    assert seen["mode"] == "read"


# 24. _h_list new fields + no bare model key
async def test_list_new_fields_no_bare_model(tool_fn, monkeypatch):
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    out = json.loads(await tool_fn("list", {}))
    assert out["success"] is True
    data = out["data"]
    assert data["modes"] == ["read", "write"]
    assert data["default_mode"] == "write"
    assert "dispatch" in data["actions"]
    assert "review" in data["actions"]
    assert "list" in data["actions"]
    for name in ("agy", "devin"):
        spec = data["vendor_specs"][name]
        assert "selectable_models" in spec
        assert "default_model" in spec
        assert "model_family" in spec
        assert "model" not in spec  # bare 'model' key killed


async def test_list_works_disabled(tool_fn, monkeypatch):
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vendor_dispatch._onboard_config_enabled",
        lambda: False,
    )
    out = json.loads(await tool_fn("list", {}))
    assert out["success"] is True
    assert out["data"]["cross_vendor_enabled"] is False


# ── timeout_s passthrough + validation ────────────────────────────────────────

async def test_dispatch_timeout_s_passed_through(tool_fn, monkeypatch):
    """A valid timeout_s is forwarded to dispatch_and_capture as a kwarg."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["timeout_s"] = timeout_s
        return {"status": "ok", "result": "ok", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy", "prompt": "x", "artifact_ref": "y",
        "timeout_s": 120,
    }))
    assert out["success"] is True, out
    assert seen["timeout_s"] == 120


async def test_dispatch_timeout_s_negative_rejected(tool_fn, monkeypatch):
    """A negative timeout_s is rejected before the executor is invoked."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy", "prompt": "x", "artifact_ref": "y",
        "timeout_s": -5,
    }))
    assert out["success"] is False
    assert "timeout_s" in out["error"]
    assert "non-negative" in out["error"]
    assert called["n"] == 0


async def test_dispatch_timeout_s_non_int_rejected(tool_fn, monkeypatch):
    """A non-int timeout_s (e.g. a string) is rejected before invocation."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy", "prompt": "x", "artifact_ref": "y",
        "timeout_s": "120",
    }))
    assert out["success"] is False
    assert "timeout_s" in out["error"]
    assert "non-negative int" in out["error"]
    assert called["n"] == 0


async def test_dispatch_timeout_s_zero_accepted(tool_fn, monkeypatch):
    """timeout_s=0 means no-timeout and MUST be accepted (not rejected)."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["timeout_s"] = timeout_s
        return {"status": "ok", "result": "ok", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy", "prompt": "x", "artifact_ref": "y",
        "timeout_s": 0,
    }))
    assert out["success"] is True, out
    assert seen["timeout_s"] == 0


async def test_dispatch_timeout_s_bool_rejected(tool_fn, monkeypatch):
    """A bool is not an int for timeout_s purposes (bool is a subclass of int
    in Python but is semantically wrong here)."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    called = {"n": 0}

    def _should_not_run(*a, **k):
        called["n"] += 1
        return {"status": "ok"}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _should_not_run,
    )
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy", "prompt": "x", "artifact_ref": "y",
        "timeout_s": True,
    }))
    assert out["success"] is False
    assert "timeout_s" in out["error"]
    assert called["n"] == 0


async def test_dispatch_timeout_s_omitted_uses_default(tool_fn, monkeypatch):
    """Omitting timeout_s forwards the executor's default, not None."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    seen = {}

    def _fake_dispatch(vendor, prompt, artifact_ref, *, to_role=None,
                       model=None, mode="write", expect_paths=None,
                       timeout_s=None):
        seen["timeout_s"] = timeout_s
        return {"status": "ok", "result": "ok", "capture": {}}

    monkeypatch.setattr(
        "mcp_server_nucleus.tools.vendor_delegate.dispatch_and_capture",
        _fake_dispatch,
    )
    from mcp_server_nucleus.tools.vendor_delegate import _DEFAULT_VENDOR_TIMEOUT_S
    out = json.loads(await tool_fn("dispatch", {
        "vendor": "agy", "prompt": "x", "artifact_ref": "y",
    }))
    assert out["success"] is True, out
    assert seen["timeout_s"] == _DEFAULT_VENDOR_TIMEOUT_S
