
import json
from typing import Dict, Any
import logging

logger = logging.getLogger("nucleus.schema")

def _to_json_serializable(obj):
    """Helper to convert Pydantic models/objects to serializable dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    # Handle specific MCP objects if needed
    return str(obj)

async def generate_tool_schema(mcp) -> Dict[str, Any]:
    """
    Introspects the MCP server and generates a combined JSON Schema for tools, prompts, and resources.
    """
    try:
        schema = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{mcp.name} API",
                "version": getattr(mcp, "version", "0.5.0"),
                "description": "Auto-generated schema for Nucleus MCP Tools, Prompts, and Resources"
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }
        
        # 1. Tools
        tool_names = await mcp.get_tools()
        for name in tool_names:
            tool = await mcp.get_tool(name)
            path = f"/tools/{tool.name}"
            schema["paths"][path] = {
                "post": {
                    "summary": f"Tool: {tool.name}",
                    "description": tool.description,
                    "operationId": f"tool_{tool.name}",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": _to_json_serializable(tool.parameters)
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful tool execution",
                            "content": {
                                "application/json": {
                                    "schema": _to_json_serializable(tool.output_schema) if tool.output_schema else {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        
        # 2. Prompts
        try:
            prompt_names = await mcp.get_prompts()
            for name in prompt_names:
                prompt = await mcp.get_prompt(name)
                path = f"/prompts/{prompt.name}"
                schema["paths"][path] = {
                    "post": {
                        "summary": f"Prompt: {prompt.name}",
                        "description": prompt.description,
                        "operationId": f"prompt_{prompt.name}",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            arg.name: {
                                                "description": arg.description,
                                                "type": "string" # MCP prompt args are usually strings
                                            } for arg in getattr(prompt, "arguments", [])
                                        },
                                        "required": [arg.name for arg in getattr(prompt, "arguments", []) if getattr(arg, "required", False)]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful prompt render"
                            }
                        }
                    }
                }
        except Exception as e:
            logger.warning(f"Failed to introspect prompts: {e}")

        # 3. Resources
        try:
            resources = await mcp.get_resources()
            for uri in resources:
                resource = await mcp.get_resource(uri)
                path = f"/resources/{resource.name}"
                schema["paths"][path] = {
                    "get": {
                        "summary": f"Resource: {resource.name}",
                        "description": f"{resource.description} (URI: {resource.uri})",
                        "operationId": f"resource_{resource.name}",
                        "responses": {
                            "200": {
                                "description": "Successful resource read",
                                "content": {
                                    resource.mime_type or "text/plain": {}
                                }
                            }
                        }
                    }
                }
        except Exception as e:
            logger.warning(f"Failed to introspect resources: {e}")
            
        return schema
    except Exception as e:
        logger.error(f"Error generating schema: {e}")
        return {"error": str(e)}

def export_schema_to_file(schema: Dict[str, Any], output_path: str):
    """
    Writes the generated schema to a JSON file.
    """
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
