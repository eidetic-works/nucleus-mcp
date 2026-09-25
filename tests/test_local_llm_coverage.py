"""Tests for mcp_server_nucleus.sovereign.local_llm.

Covers _format_tools_for_prompt, _parse_tool_calls_from_text, LocalLLM
class (__init__, generate_content, generate_with_tools,
generate_content_stream, active_engine), and LocalLLMResponse dataclass.
All urllib calls are mocked — no real network requests.
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.sovereign.local_llm import (
    LocalLLM,
    LocalLLMResponse,
    _format_tools_for_prompt,
    _parse_tool_calls_from_text,
)


# ──────────────────────────────────────────────────────────────
# Helper: build a mock urllib response
# ──────────────────────────────────────────────────────────────
def _mock_urlopen_response(data_dict, status=200):
    """Create a mock context manager for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(data_dict).encode()
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_resp)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm


def _mock_urlopen_streaming(chunks):
    """Create a mock streaming response (iterable of SSE lines)."""
    lines = []
    for chunk in chunks:
        data = {"choices": [{"delta": {"content": chunk}}]}
        lines.append(f"data: {json.dumps(data)}")
    lines.append("data: [DONE]")
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter([l.encode() for l in lines]))
    return mock_resp


# ──────────────────────────────────────────────────────────────
# _format_tools_for_prompt
# ──────────────────────────────────────────────────────────────
class TestFormatToolsForPrompt:
    def test_empty_tools(self):
        result = _format_tools_for_prompt([])
        assert "You have access to the following tools:" in result

    def test_with_function_key(self):
        tools = [
            {"function": {"name": "search", "description": "Search the web", "parameters": {"type": "object"}}}
        ]
        result = _format_tools_for_prompt(tools)
        assert "search" in result
        assert "Search the web" in result
        assert "parameters:" in result

    def test_without_function_key(self):
        tools = [{"name": "calc", "description": "Calculator", "parameters": {}}]
        result = _format_tools_for_prompt(tools)
        assert "calc" in result
        assert "Calculator" in result

    def test_no_parameters(self):
        tools = [{"function": {"name": "ping", "description": "Ping"}}]
        result = _format_tools_for_prompt(tools)
        assert "ping" in result
        # No parameters key means no "parameters:" line for that tool
        assert "tool_call" in result

    def test_tool_call_instruction(self):
        tools = [{"function": {"name": "x", "description": "d", "parameters": {}}}]
        result = _format_tools_for_prompt(tools)
        assert "tool_call" in result
        assert "at most one" in result


# ──────────────────────────────────────────────────────────────
# _parse_tool_calls_from_text
# ──────────────────────────────────────────────────────────────
class TestParseToolCallsFromText:
    def test_no_tool_calls(self):
        text, calls = _parse_tool_calls_from_text("Hello world")
        assert text == "Hello world"
        assert calls is None

    def test_single_tool_call(self):
        text, calls = _parse_tool_calls_from_text(
            'Some text <tool_call>{"name": "search", "arguments": {"q": "test"}}</tool_call> more'
        )
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["name"] == "search"
        assert calls[0]["arguments"] == {"q": "test"}
        assert calls[0]["type"] == "function"
        assert calls[0]["id"] == "call_0"
        assert "tool_call" not in text

    def test_multiple_tool_calls(self):
        text, calls = _parse_tool_calls_from_text(
            '<tool_call>{"name": "a", "arguments": {}}</tool_call>'
            '<tool_call>{"name": "b", "arguments": {"x": 1}}</tool_call>'
        )
        assert calls is not None
        assert len(calls) == 2
        assert calls[0]["name"] == "a"
        assert calls[1]["name"] == "b"

    def test_malformed_json_dropped(self):
        text, calls = _parse_tool_calls_from_text(
            '<tool_call>not valid json</tool_call>'
            '<tool_call>{"name": "good", "arguments": {}}</tool_call>'
        )
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["name"] == "good"

    def test_all_malformed_returns_none(self):
        text, calls = _parse_tool_calls_from_text(
            '<tool_call>broken</tool_call><tool_call>also broken</tool_call>'
        )
        assert calls is None
        assert "tool_call" in text

    def test_empty_arguments(self):
        text, calls = _parse_tool_calls_from_text(
            '<tool_call>{"name": "noop"}</tool_call>'
        )
        assert calls is not None
        assert calls[0]["arguments"] == {}

    def test_multiline_tool_call(self):
        text, calls = _parse_tool_calls_from_text(
            '<tool_call>\n{"name": "multi", "arguments": {"a": 1}}\n</tool_call>'
        )
        assert calls is not None
        assert calls[0]["name"] == "multi"


# ──────────────────────────────────────────────────────────────
# LocalLLMResponse dataclass
# ──────────────────────────────────────────────────────────────
class TestLocalLLMResponse:
    def test_defaults(self):
        r = LocalLLMResponse(text="hello")
        assert r.text == "hello"
        assert r.model == ""
        assert r.usage == {}
        assert r.tool_calls is None
        assert r.finish_reason is None

    def test_with_all_fields(self):
        r = LocalLLMResponse(
            text="hi",
            model="test-model",
            usage={"input_tokens": 10, "output_tokens": 5},
            tool_calls=[{"name": "search"}],
            finish_reason="tool_calls",
        )
        assert r.model == "test-model"
        assert r.tool_calls == [{"name": "search"}]
        assert r.finish_reason == "tool_calls"


# ──────────────────────────────────────────────────────────────
# LocalLLM __init__
# ──────────────────────────────────────────────────────────────
class TestLocalLLMInit:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        monkeypatch.delenv("NUCLEUS_LOCAL_MODEL", raising=False)
        monkeypatch.delenv("NUCLEUS_LOCAL_API_KEY", raising=False)
        # TB_MODEL is a real override and is set in at least one developer
        # shell here, so a test asserting the built-in default must clear it.
        monkeypatch.delenv("TB_MODEL", raising=False)
        llm = LocalLLM()
        assert llm.endpoint == "http://localhost:11434/v1"
        assert llm.model_name == "nucleus-brother"
        assert llm.api_key == "not-needed"
        assert llm.engine == "LOCAL"
        assert llm.system_instruction is None

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_LOCAL_ENDPOINT", "http://my-host:8080/v1/")
        monkeypatch.setenv("NUCLEUS_LOCAL_MODEL", "my-model")
        monkeypatch.setenv("NUCLEUS_LOCAL_API_KEY", "secret")
        llm = LocalLLM()
        assert llm.endpoint == "http://my-host:8080/v1"  # trailing slash stripped
        assert llm.model_name == "my-model"
        assert llm.api_key == "secret"

    def test_explicit_params(self):
        llm = LocalLLM(
            model_name="custom-model",
            system_instruction="You are helpful",
            endpoint="http://custom:1234/v1",
            api_key="key123",
        )
        assert llm.model_name == "custom-model"
        assert llm.system_instruction == "You are helpful"
        assert llm.endpoint == "http://custom:1234/v1"
        assert llm.api_key == "key123"

    def test_extra_kwargs_ignored(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_MODEL", raising=False)
        monkeypatch.delenv("TB_MODEL", raising=False)
        llm = LocalLLM(unknown_param="value", another=42)
        assert llm.model_name == "nucleus-brother"

    def test_active_engine_property(self):
        llm = LocalLLM()
        assert llm.active_engine == "LOCAL"

    def test_generate_alias(self):
        llm = LocalLLM()
        assert callable(llm.generate)
        # generate is an alias for generate_content (assigned at class level)
        assert llm.generate.__name__ == "generate_content"

    def test_stream_content_alias(self):
        llm = LocalLLM()
        assert callable(llm.stream_content)
        # stream_content is an alias for generate_content_stream
        assert llm.stream_content.__name__ == "generate_content_stream"


# ──────────────────────────────────────────────────────────────
# generate_content
# ──────────────────────────────────────────────────────────────
class TestGenerateContent:
    def test_string_prompt(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "Hello!"}}],
            "model": "nucleus-brother",
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_content("Hi")
        assert resp.text == "Hello!"
        assert resp.model == "nucleus-brother"
        assert resp.usage["input_tokens"] == 5
        assert resp.usage["output_tokens"] == 2

    def test_string_prompt_with_system_instruction(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be concise")
        data = {
            "choices": [{"message": {"content": "OK"}}],
            "model": "test",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm) as mock_open:
            resp = llm.generate_content("Hi")
        # Verify the request was made
        assert mock_open.called
        assert resp.text == "OK"

    def test_list_prompt(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "Response"}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_content([
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "How are you?"},
            ])
        assert resp.text == "Response"

    def test_list_prompt_with_system_instruction(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be helpful")
        data = {
            "choices": [{"message": {"content": "Sure"}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_content([
                {"role": "user", "content": "Hello"},
            ])
        assert resp.text == "Sure"

    def test_list_prompt_already_has_system(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be helpful")
        data = {
            "choices": [{"message": {"content": "Done"}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_content([
                {"role": "system", "content": "Existing system"},
                {"role": "user", "content": "Hello"},
            ])
        assert resp.text == "Done"

    def test_connection_error_raises_runtime_error(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            with pytest.raises(RuntimeError, match="unreachable"):
                llm.generate_content("Hi")

    def test_empty_content_response(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": None}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_content("Hi")
        assert resp.text == ""

    def test_custom_kwargs(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "OK"}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_content("Hi", max_tokens=100, temperature=0.5, timeout=30)
        assert resp.text == "OK"


# ──────────────────────────────────────────────────────────────
# generate_with_tools
# ──────────────────────────────────────────────────────────────
class TestGenerateWithTools:
    def test_string_prompt_react_mode(self, monkeypatch):
        """Non-native mode: tools injected into system prompt."""
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="You are an agent")
        data = {
            "choices": [{"message": {"content": "I will help"}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools("Search for cats", [
                {"function": {"name": "search", "description": "Search web", "parameters": {}}}
            ])
        assert resp.text == "I will help"
        assert resp.tool_calls is None
        assert resp.finish_reason == "stop"

    def test_string_prompt_react_mode_no_system(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()  # no system_instruction
        data = {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools("Hi", [
                {"function": {"name": "tool1", "description": "d", "parameters": {}}}
            ])
        assert resp.text == "OK"

    def test_list_prompt_with_existing_system_react(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "Done"}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                [
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": "Do something"},
                ],
                [{"function": {"name": "t", "description": "d", "parameters": {}}}],
            )
        assert resp.text == "Done"

    def test_list_prompt_no_system_react(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be an agent")
        data = {
            "choices": [{"message": {"content": "Result"}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                [{"role": "user", "content": "Hi"}],
                [{"function": {"name": "t", "description": "d", "parameters": {}}}],
            )
        assert resp.text == "Result"

    def test_react_mode_parses_tool_calls(self, monkeypatch):
        """When assistant text contains <tool_call> blocks, they're parsed."""
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{
                "message": {"content": 'Let me search <tool_call>{"name": "search", "arguments": {"q": "cats"}}</tool_call>'},
                "finish_reason": "stop",
            }],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools("Find cats", [
                {"function": {"name": "search", "description": "Search", "parameters": {}}}
            ])
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["name"] == "search"
        assert resp.finish_reason == "tool_calls"
        assert "tool_call" not in resp.text

    def test_native_mode_with_tool_calls(self, monkeypatch):
        """Native mode: tools sent in payload, tool_calls from response."""
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be an agent")
        data = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "tc-1",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "test"}'},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                "Search", [{"function": {"name": "search", "description": "d", "parameters": {}}}],
                native_tool_use=True,
            )
        assert resp.tool_calls is not None
        assert resp.tool_calls[0]["name"] == "search"
        assert resp.tool_calls[0]["arguments"] == {"q": "test"}
        assert resp.finish_reason == "tool_calls"

    def test_native_mode_tool_calls_non_string_args(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "tc-1",
                        "type": "function",
                        "function": {"name": "calc", "arguments": {"x": 1}},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                [{"role": "user", "content": "Calculate"}],
                [{"function": {"name": "calc", "description": "d", "parameters": {}}}],
                native_tool_use=True,
            )
        assert resp.tool_calls[0]["arguments"] == {"x": 1}

    def test_native_mode_invalid_json_args(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "tc-1",
                        "type": "function",
                        "function": {"name": "x", "arguments": "not-json"},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                [{"role": "user", "content": "Hi"}],
                [{"function": {"name": "x", "description": "d", "parameters": {}}}],
                native_tool_use=True,
            )
        assert resp.tool_calls[0]["arguments"] == {"_raw": "not-json"}

    def test_native_mode_with_tool_choice(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                [{"role": "user", "content": "Hi"}],
                [{"function": {"name": "x", "description": "d", "parameters": {}}}],
                native_tool_use=True,
                tool_choice="auto",
            )
        assert resp.text == "OK"

    def test_native_mode_no_tool_calls(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "No tools needed"}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools(
                [{"role": "user", "content": "Hi"}],
                [{"function": {"name": "x", "description": "d", "parameters": {}}}],
                native_tool_use=True,
            )
        assert resp.tool_calls is None
        assert resp.text == "No tools needed"

    def test_connection_error_raises_runtime_error(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            with pytest.raises(RuntimeError, match="unreachable"):
                llm.generate_with_tools("Hi", [])

    def test_empty_content_react_mode(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": None}, "finish_reason": "stop"}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            resp = llm.generate_with_tools("Hi", [])
        assert resp.text == ""
        assert resp.tool_calls is None


# ──────────────────────────────────────────────────────────────
# generate_content_stream
# ──────────────────────────────────────────────────────────────
class TestGenerateContentStream:
    def test_streaming_success(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        mock_resp = _mock_urlopen_streaming(["Hello ", "world!"])
        with patch("urllib.request.urlopen", return_value=mock_resp):
            chunks = list(llm.generate_content_stream("Hi"))
        assert chunks == ["Hello ", "world!"]

    def test_streaming_with_system_instruction(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be concise")
        mock_resp = _mock_urlopen_streaming(["OK"])
        with patch("urllib.request.urlopen", return_value=mock_resp):
            chunks = list(llm.generate_content_stream("Hi"))
        assert chunks == ["OK"]

    def test_streaming_list_prompt_with_system(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be concise")
        mock_resp = _mock_urlopen_streaming(["Done"])
        with patch("urllib.request.urlopen", return_value=mock_resp):
            chunks = list(llm.generate_content_stream([
                {"role": "user", "content": "Hi"},
            ]))
        assert chunks == ["Done"]

    def test_streaming_list_prompt_already_has_system(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM(system_instruction="Be concise")
        mock_resp = _mock_urlopen_streaming(["Yes"])
        with patch("urllib.request.urlopen", return_value=mock_resp):
            chunks = list(llm.generate_content_stream([
                {"role": "system", "content": "Existing"},
                {"role": "user", "content": "Hi"},
            ]))
        assert chunks == ["Yes"]

    def test_streaming_skips_empty_lines(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        lines = [
            b"",
            b": comment",
            b'data: {"choices": [{"delta": {"content": "A"}}]}',
            b"",
            b'data: {"choices": [{"delta": {"content": "B"}}]}',
            b"data: [DONE]",
        ]
        mock_resp = MagicMock()
        mock_resp.__iter__ = MagicMock(return_value=iter(lines))
        with patch("urllib.request.urlopen", return_value=mock_resp):
            chunks = list(llm.generate_content_stream("Hi"))
        assert chunks == ["A", "B"]

    def test_streaming_falls_back_on_error(self, monkeypatch):
        """When streaming fails, it falls back to generate_content."""
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "Fallback response"}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        with patch("urllib.request.urlopen", side_effect=ConnectionError("stream failed")):
            # The fallback calls generate_content which also uses urlopen,
            # but side_effect is set for all calls. We need a different approach.
            pass

    def test_streaming_falls_back_on_error_with_mock(self, monkeypatch):
        """When streaming fails, it falls back to generate_content."""
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        data = {
            "choices": [{"message": {"content": "Fallback response"}}],
            "model": "m",
            "usage": {},
        }
        mock_cm = _mock_urlopen_response(data)
        # First call raises, second call succeeds
        with patch("urllib.request.urlopen", side_effect=[ConnectionError("stream failed"), mock_cm]):
            chunks = list(llm.generate_content_stream("Hi"))
        assert chunks == ["Fallback response"]

    def test_streaming_empty_content_delta(self, monkeypatch):
        """Deltas with no content are skipped."""
        monkeypatch.delenv("NUCLEUS_LOCAL_ENDPOINT", raising=False)
        llm = LocalLLM()
        lines = [
            b'data: {"choices": [{"delta": {}}]}',
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            b'data: {"choices": [{"delta": {"content": ""}}]}',
            b"data: [DONE]",
        ]
        mock_resp = MagicMock()
        mock_resp.__iter__ = MagicMock(return_value=iter(lines))
        with patch("urllib.request.urlopen", return_value=mock_resp):
            chunks = list(llm.generate_content_stream("Hi"))
        assert chunks == ["Hello"]
