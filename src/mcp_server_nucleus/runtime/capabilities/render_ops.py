from typing import List, Dict, Any
import os
import json
import urllib.request
import urllib.error
from .base import Capability

class RenderOps(Capability):
    def __init__(self):
        self.api_key = os.environ.get("RENDER_API_KEY")
        self.base_url = "https://api.render.com/v1"

    @property
    def name(self) -> str:
        return "render_ops"

    @property
    def description(self) -> str:
        return "Tools for interacting with the Render.com API (Deployments, Services)."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "render_list_services",
                "description": "List all services in Render account.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "render_deploy_service",
                "description": "Trigger a deployment for a specific service.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "service_id": {"type": "string"}
                    },
                    "required": ["service_id"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> str:
        if not self.api_key:
            return "Error: RENDER_API_KEY not found in environment."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            if tool_name == "render_list_services":
                url = f"{self.base_url}/services?limit=20"
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        data = json.load(response)
                        services = [f"{s['service']['name']} ({s['service']['id']})" for s in data]
                        return "Services:\n" + "\n".join(services)
                    return f"Error listing services: HTTP {response.status}"

            elif tool_name == "render_deploy_service":
                sid = args.get('service_id')
                url = f"{self.base_url}/services/{sid}/deploys"
                data = json.dumps({"clearCache": "clear"}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                
                with urllib.request.urlopen(req) as response:
                    if response.status == 201:
                        deploy = json.load(response)
                        return f"Deployment triggered: {deploy['id']}"
                    return f"Error triggering deploy: HTTP {response.status}"

        except urllib.error.HTTPError as e:
            return f"Render API Error ({e.code}): {e.read().decode('utf-8')}"
        except Exception as e:
            return f"Exception calling Render API: {e}"

        return f"Tool {tool_name} not found in RenderOps."
