"""Tests for the Anthropic-Messages-over-vendor-CLI shim.

Two of these encode defects that unit tests did NOT find — a live `claude -p`
run did. They are kept as regressions because both were invisible until real
Claude Code traffic hit the shim.
"""
from __future__ import annotations

import json

import pytest

from mcp_server_nucleus.runtime import vendor_shim as vs


# ── routing ──────────────────────────────────────────────────────────────────
def test_parse_model_hyphenated_vendor_is_disambiguated():
    """REGRESSION. A generic `([a-z0-9-]+)-(model)` regex is greedy, so
    `nucleus/devin-glm-5.2` parsed as vendor `devin-glm-5` / model `2`. The
    ambiguity is real rather than cosmetic: `devin-swe` is itself a hyphenated
    vendor name. Alternation over known vendors, longest-first, resolves both."""
    assert vs.parse_model("nucleus/devin-glm-5.2") == ("devin", "glm-5.2")
    assert vs.parse_model("nucleus/devin-swe-swe-1.7") == ("devin-swe", "swe-1.7")
    assert vs.parse_model("nucleus/agy-gemini-3.1-pro-high") == ("agy", "gemini-3.1-pro-high")


@pytest.mark.parametrize("model", [
    "claude-haiku-4-5-20251001",   # CC's internal traffic must NOT be captured
    "claude-sonnet-5",
    "nucleus/bogus-x",             # unknown vendor
    "devin-glm-5.2",               # missing namespace
    "",
])
def test_parse_model_rejects_everything_outside_the_namespace(model):
    """The namespace is deliberate: routing on a bare tier name would drag Claude
    Code's own haiku traffic (titles, summarisation) through a slow CLI."""
    assert vs.parse_model(model) is None


def test_resolve_rejects_cross_wired_model():
    with pytest.raises(ValueError):
        vs.resolve("agy", "glm-5.2")
    with pytest.raises(ValueError):
        vs.resolve("nosuchvendor", "glm-5.2")


# ── request flattening ───────────────────────────────────────────────────────
def test_tool_blocks_are_rendered_not_dropped():
    """Silently discarding tool_use/tool_result would corrupt a multi-turn
    conversation while the response still looked valid."""
    prompt, tool = vs.flatten({
        "system": "SYSTEM_MARKER",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "USER_MARKER"}]},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Read", "input": {"file": "a.py"}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "content": "RESULT_MARKER"}]},
        ],
    })
    for marker in ("SYSTEM_MARKER", "USER_MARKER", "Read", "RESULT_MARKER"):
        assert marker in prompt
    assert tool is None


# ── tool_choice semantics (the live-run defect) ──────────────────────────────
@pytest.mark.parametrize("tool_choice", [None, {"type": "auto"}])
def test_available_tools_do_not_force_json(tool_choice):
    """REGRESSION, found by a live `claude -p` run — 2 of 4 calls corrupted.

    Claude Code sends its FULL tool array on every request because those tools
    are *available*, not *required*. Demanding JSON whenever tools were present
    made the vendor answer a plain question with "expected JSON for tool 'Agent',
    got unparseable output". tool_choice is the signal, not the presence of tools.
    """
    payload = {
        "messages": [{"role": "user", "content": "what is 2+2"}],
        "tools": [{"name": "Agent", "input_schema": {}},
                  {"name": "Read", "input_schema": {}}],
    }
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    prompt, tool = vs.flatten(payload)
    assert tool is None, "text must remain a valid answer when no tool is forced"
    assert "CANNOT call them" in prompt, "model must be told it cannot call the listed tools"
    assert "REQUIRED OUTPUT FORMAT" not in prompt


def test_forced_tool_choice_demands_json():
    """A schema stage sets tool_choice — that is exactly when JSON is correct."""
    tools = [{"name": "StructuredOutput", "input_schema": {"type": "object"}}]
    _, t_any = vs.flatten({"messages": [{"role": "user", "content": "x"}],
                           "tools": tools, "tool_choice": {"type": "any"}})
    assert t_any == "StructuredOutput"

    prompt, t_named = vs.flatten({
        "messages": [{"role": "user", "content": "x"}],
        "tools": [{"name": "Agent", "input_schema": {}}, *tools],
        "tool_choice": {"type": "tool", "name": "Agent"}})
    assert t_named == "Agent"
    assert "REQUIRED OUTPUT FORMAT" in prompt


# ── JSON extraction ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ('```json\n{"a":1}\n```', {"a": 1}),
    ('```\n{"a":1}\n```', {"a": 1}),
    ('prose before {"a":2} prose after', {"a": 2}),
    ('{"a":3}', {"a": 3}),
])
def test_extract_json_handles_vendor_wrapping(raw, expected):
    """Vendors fence or narrate their JSON regardless of instruction."""
    assert vs.extract_json(raw) == expected


@pytest.mark.parametrize("raw", ["", "no json at all", "{not valid}"])
def test_extract_json_returns_none_rather_than_guessing(raw):
    assert vs.extract_json(raw) is None


# ── tool_use synthesis — the reason this shim is worth building ──────────────
def test_tool_use_block_is_synthesised_from_vendor_json():
    """A schema stage is a FORCED tool call: Claude Code will not accept prose
    where it expects a tool_use block, and the vendor CLI cannot emit one. This
    synthesis is what makes agent(..., {schema}) work at all on this backend."""
    body = vs.build_response(
        "nucleus/devin-glm-5.2", '{"verdict":"ADOPT","n":3}', "StructuredOutput", "p")
    block = body["content"][0]
    assert block["type"] == "tool_use"
    assert block["name"] == "StructuredOutput"
    assert block["input"] == {"verdict": "ADOPT", "n": 3}
    assert block["id"].startswith("toolu_")
    assert body["stop_reason"] == "tool_use"


def test_unparseable_json_fails_loudly_not_silently():
    """A schema stage that quietly degrades to prose is indistinguishable from a
    model choosing not to call a tool. The live-run defect was only visible
    because this text is emitted into the answer."""
    body = vs.build_response("nucleus/devin-glm-5.2", "just prose", "StructuredOutput", "p")
    assert body["content"][0]["type"] == "text"
    assert "expected JSON" in body["content"][0]["text"]
    assert body["stop_reason"] == "end_turn"


def test_plain_text_response_when_no_tool_forced():
    body = vs.build_response("nucleus/devin-glm-5.2", "hello", None, "p")
    assert body["content"] == [{"type": "text", "text": "hello"}]
    assert body["stop_reason"] == "end_turn"


# ── SSE ──────────────────────────────────────────────────────────────────────
def test_sse_emits_the_full_anthropic_event_sequence():
    body = vs.build_response("nucleus/devin-glm-5.2", "hi", None, "p")
    s = vs.sse_frames(body)
    for event in ("message_start", "content_block_start", "content_block_delta",
                  "content_block_stop", "message_delta", "message_stop"):
        assert f"event: {event}" in s
    assert "text_delta" in s
    for line in s.splitlines():
        if line.startswith("data: "):
            json.loads(line[6:])          # every frame must be valid JSON


def test_sse_tool_use_uses_input_json_delta():
    body = vs.build_response("nucleus/devin-glm-5.2", '{"a":1}', "StructuredOutput", "p")
    s = vs.sse_frames(body)
    assert "input_json_delta" in s
    assert "text_delta" not in s


# ── fail closed ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("model", ["claude-sonnet-5", "nucleus/bogus-x", None])
def test_out_of_namespace_is_400_and_never_proxied(model):
    """There is NO fallback to Anthropic. A fallback would return a real answer
    from a model the caller did not ask for, indistinguishable from success."""
    status, body, stream = vs.handle_messages(
        {"model": model, "messages": [{"role": "user", "content": "x"}]})
    assert status == 400
    assert body["error"]["type"] == "invalid_request_error"
    assert stream is False


def test_empty_request_is_rejected():
    # Must use a model that PASSES validation, or this returns 400 for
    # "unsupported model" and never reaches the empty-messages check -- the
    # test would pass while proving nothing. glm-5.2 was removed from devin's
    # models[] by the 2026-08-15 cost freeze, which is exactly what happened.
    status, body, _ = vs.handle_messages(
        {"model": "nucleus/devin-claude-5-fable-low", "messages": []})
    assert status == 400


def test_vendor_failure_is_502_not_a_fallback(monkeypatch):
    class _Fail:
        status, rc, duration, result = "timed_out", None, 300.0, ""
        produced_output = False

        def __init__(self, *a, **k):
            pass

        def run(self):
            return self

    monkeypatch.setattr(vs, "VendorCLIExecutor", _Fail)
    # Same trap as test_empty_request_is_rejected: with the frozen glm-5.2 this
    # returned 400 at model validation and never invoked the executor at all,
    # so the 502 path this test exists to cover was never executed.
    status, body, _ = vs.handle_messages({
        "model": "nucleus/devin-claude-5-fable-low",
        "messages": [{"role": "user", "content": "x"}]})
    assert status == 502
    assert "did not produce output" in body["error"]["message"]
