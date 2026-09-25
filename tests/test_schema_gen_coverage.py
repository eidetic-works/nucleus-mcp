"""Comprehensive tests for mcp_server_nucleus.runtime.schema_gen.

Covers _to_json_serializable, generate_tool_schema (tools/prompts/resources/errors),
and export_schema_to_file.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server_nucleus.runtime import schema_gen
from mcp_server_nucleus.runtime.schema_gen import (
    _to_json_serializable,
    generate_tool_schema,
    export_schema_to_file,
)


# ── _to_json_serializable ──

class TestToJsonSerializable:
    def test_pydantic_model_dump(self):
        class FakeModel:
            def model_dump(self):
                return {"key": "value"}
        result = _to_json_serializable(FakeModel())
        assert result == {"key": "value"}

    def test_legacy_dict_method(self):
        class FakeModel:
            def dict(self):
                return {"legacy": True}
        result = _to_json_serializable(FakeModel())
        assert result == {"legacy": True}

    def test_list(self):
        # Non-model/list/dict items are converted to str()
        result = _to_json_serializable([1, "two", {"three": 3}])
        assert result == ["1", "two", {"three": "3"}]

    def test_dict(self):
        # Non-model/list/dict items are converted to str()
        result = _to_json_serializable({"a": 1, "b": [2, 3]})
        assert result == {"a": "1", "b": ["2", "3"]}

    def test_nested_pydantic_in_list(self):
        class FakeModel:
            def model_dump(self):
                return {"x": 1}
        result = _to_json_serializable([FakeModel(), FakeModel()])
        assert result == [{"x": 1}, {"x": 1}]

    def test_nested_pydantic_in_dict(self):
        class FakeModel:
            def model_dump(self):
                return {"y": 2}
        result = _to_json_serializable({"model": FakeModel()})
        assert result == {"model": {"y": 2}}

    def test_fallback_to_str(self):
        result = _to_json_serializable(42)
        assert result == "42"

    def test_none(self):
        result = _to_json_serializable(None)
        assert result == "None"

    def test_empty_list(self):
        assert _to_json_serializable([]) == []

    def test_empty_dict(self):
        assert _to_json_serializable({}) == {}


# ── Mock MCP server ──

class MockArg:
    def __init__(self, name, description, required=False):
        self.name = name
        self.description = description
        self.required = required


class MockTool:
    def __init__(self, name, description, parameters=None, output_schema=None):
        self.name = name
        self.description = description
        self.parameters = parameters or {"type": "object", "properties": {}}
        self.output_schema = output_schema


class MockPrompt:
    def __init__(self, name, description, arguments=None):
        self.name = name
        self.description = description
        self.arguments = arguments or []


class MockResource:
    def __init__(self, name, description, uri, mime_type=None):
        self.name = name
        self.description = description
        self.uri = uri
        self.mime_type = mime_type


class MockMCP:
    def __init__(self, name="test-server", version="1.0.0",
                 tools=None, prompts=None, prompt_names=None,
                 resources=None, resource_uris=None):
        self.name = name
        self.version = version
        self._tools = tools or []
        self._prompts = prompts or {}
        self._prompt_names = prompt_names or []
        self._resources = resources or {}
        self._resource_uris = resource_uris or []

    async def list_tools(self):
        return self._tools

    async def get_prompts(self):
        return self._prompt_names

    async def get_prompt(self, name):
        return self._prompts.get(name)

    async def get_resources(self):
        return self._resource_uris

    async def get_resource(self, uri):
        return self._resources.get(uri)


# ── generate_tool_schema ──

class TestGenerateToolSchema:
    @pytest.mark.asyncio
    async def test_empty_server(self):
        mcp = MockMCP()
        schema = await generate_tool_schema(mcp)
        assert schema["openapi"] == "3.0.0"
        assert schema["info"]["title"] == "test-server API"
        assert schema["info"]["version"] == "1.0.0"
        assert schema["paths"] == {}

    @pytest.mark.asyncio
    async def test_tools_with_output_schema(self):
        tool = MockTool("my_tool", "Does something",
                        parameters={"type": "object", "properties": {"x": {"type": "string"}}},
                        output_schema={"type": "object", "properties": {"result": {"type": "string"}}})
        mcp = MockMCP(tools=[tool])
        schema = await generate_tool_schema(mcp)
        path = schema["paths"]["/tools/my_tool"]
        assert path["post"]["summary"] == "Tool: my_tool"
        assert path["post"]["operationId"] == "tool_my_tool"
        assert "x" in path["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
        assert "result" in path["post"]["responses"]["200"]["content"]["application/json"]["schema"]["properties"]

    @pytest.mark.asyncio
    async def test_tools_without_output_schema(self):
        tool = MockTool("simple", "Simple tool", output_schema=None)
        mcp = MockMCP(tools=[tool])
        schema = await generate_tool_schema(mcp)
        resp = schema["paths"]["/tools/simple"]["post"]["responses"]["200"]
        assert resp["content"]["application/json"]["schema"] == {"type": "object"}

    @pytest.mark.asyncio
    async def test_tools_default_version(self):
        mcp = MockMCP(name="no-ver")
        del mcp.version
        schema = await generate_tool_schema(mcp)
        assert schema["info"]["version"] == "0.5.0"

    @pytest.mark.asyncio
    async def test_prompts_with_arguments(self):
        prompt = MockPrompt("greet", "Greeting prompt",
                            arguments=[MockArg("name", "Person name", required=True),
                                       MockArg("style", "Greeting style")])
        mcp = MockMCP(prompt_names=["greet"], prompts={"greet": prompt})
        schema = await generate_tool_schema(mcp)
        path = schema["paths"]["/prompts/greet"]
        assert path["post"]["summary"] == "Prompt: greet"
        props = path["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
        assert "name" in props
        assert "style" in props
        required = path["post"]["requestBody"]["content"]["application/json"]["schema"]["required"]
        assert "name" in required
        assert "style" not in required

    @pytest.mark.asyncio
    async def test_prompts_no_arguments(self):
        prompt = MockPrompt("simple", "Simple prompt")
        mcp = MockMCP(prompt_names=["simple"], prompts={"simple": prompt})
        schema = await generate_tool_schema(mcp)
        path = schema["paths"]["/prompts/simple"]
        assert path["post"]["summary"] == "Prompt: simple"

    @pytest.mark.asyncio
    async def test_prompts_failure_handled(self):
        mcp = MockMCP()
        # Make get_prompts raise
        async def fail_prompts():
            raise RuntimeError("prompt error")
        mcp.get_prompts = fail_prompts
        schema = await generate_tool_schema(mcp)
        # Should still have tools paths (empty) and not crash
        assert "paths" in schema

    @pytest.mark.asyncio
    async def test_resources_with_mime_type(self):
        resource = MockResource("data", "Data resource", "file:///data",
                                mime_type="application/json")
        mcp = MockMCP(resource_uris=["file:///data"],
                      resources={"file:///data": resource})
        schema = await generate_tool_schema(mcp)
        path = schema["paths"]["/resources/data"]
        assert path["get"]["summary"] == "Resource: data"
        assert "file:///data" in path["get"]["description"]
        content = path["get"]["responses"]["200"]["content"]
        assert "application/json" in content

    @pytest.mark.asyncio
    async def test_resources_without_mime_type(self):
        resource = MockResource("text", "Text resource", "file:///text",
                                mime_type=None)
        mcp = MockMCP(resource_uris=["file:///text"],
                      resources={"file:///text": resource})
        schema = await generate_tool_schema(mcp)
        content = schema["paths"]["/resources/text"]["get"]["responses"]["200"]["content"]
        assert "text/plain" in content

    @pytest.mark.asyncio
    async def test_resources_failure_handled(self):
        mcp = MockMCP()
        async def fail_resources():
            raise RuntimeError("resource error")
        mcp.get_resources = fail_resources
        schema = await generate_tool_schema(mcp)
        assert "paths" in schema

    @pytest.mark.asyncio
    async def test_list_tools_failure_returns_error(self):
        mcp = MockMCP()
        async def fail_tools():
            raise RuntimeError("tools error")
        mcp.list_tools = fail_tools
        schema = await generate_tool_schema(mcp)
        assert "error" in schema
        assert "tools error" in schema["error"]

    @pytest.mark.asyncio
    async def test_full_server(self):
        tool = MockTool("tool1", "Tool one")
        prompt = MockPrompt("prompt1", "Prompt one",
                            arguments=[MockArg("arg1", "First arg", required=True)])
        resource = MockResource("res1", "Resource one", "uri://1", "text/plain")
        mcp = MockMCP(
            name="full-server",
            version="2.0.0",
            tools=[tool],
            prompt_names=["prompt1"],
            prompts={"prompt1": prompt},
            resource_uris=["uri://1"],
            resources={"uri://1": resource},
        )
        schema = await generate_tool_schema(mcp)
        assert "/tools/tool1" in schema["paths"]
        assert "/prompts/prompt1" in schema["paths"]
        assert "/resources/res1" in schema["paths"]


# ── export_schema_to_file ──

class TestExportSchemaToFile:
    def test_writes_json_file(self, tmp_path):
        schema = {"openapi": "3.0.0", "paths": {}}
        out = tmp_path / "schema.json"
        export_schema_to_file(schema, str(out))
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded == schema

    def test_writes_unicode(self, tmp_path):
        schema = {"info": {"title": "Tëst Sërver — 日本語"}}
        out = tmp_path / "unicode.json"
        export_schema_to_file(schema, str(out))
        loaded = json.loads(out.read_text())
        assert "日本語" in loaded["info"]["title"]

    def test_writes_empty_schema(self, tmp_path):
        out = tmp_path / "empty.json"
        export_schema_to_file({}, str(out))
        assert json.loads(out.read_text()) == {}

    def test_overwrites_existing(self, tmp_path):
        out = tmp_path / "overwrite.json"
        out.write_text("old content")
        export_schema_to_file({"new": True}, str(out))
        assert json.loads(out.read_text()) == {"new": True}
