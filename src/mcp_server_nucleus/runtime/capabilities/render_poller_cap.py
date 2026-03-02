from typing import List, Dict, Any, Optional
import os
import time
import asyncio
import logging
import urllib.request
import urllib.error
import json
from pathlib import Path
from .base import Capability

logger = logging.getLogger("nucleus.render_poller")

# Global dict to store active polls in memory
# {service_id: {"commit_sha": str, "start_time": float, "status": str, "task": asyncio.Task}}
ACTIVE_POLLS = {}

class RenderPolling(Capability):
    def __init__(self):
        self._brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", "/Users/nucleus-os/.gemini/antigravity/brain/7c654df4-b83e-43f9-8620-f15868ec39d1"))
        self._api_key = os.environ.get("RENDER_API_KEY")
        
    @property
    def name(self) -> str:
        return "render_poller"

    @property
    def description(self) -> str:
        return "Automated deployment monitoring for Render services."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_start_deploy_poll",
                "description": "Start monitoring a Render deploy in the background.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_id": {"type": "string", "description": "Render service ID (e.g., 'srv-abc123')"},
                        "commit_sha": {"type": "string", "description": "Optional Git commit SHA being deployed"}
                    },
                    "required": ["service_id"]
                }
            },
            {
                "name": "brain_check_deploy",
                "description": "Check status of an active deploy poll.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_id": {"type": "string", "description": "Render service ID to check"}
                    },
                    "required": ["service_id"]
                }
            },
            {
                "name": "brain_smoke_test",
                "description": "Run a smoke test on any URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Base URL of service (e.g., 'https://myapp.onrender.com')"},
                        "endpoint": {"type": "string", "description": "Health endpoint to hit (default: '/api/health')"}
                    },
                    "required": ["url"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> Any:
        try:
            if tool_name == "brain_start_deploy_poll":
                return self._start_poll(args.get("service_id"), args.get("commit_sha"))
            elif tool_name == "brain_check_deploy":
                return self._check_poll(args.get("service_id"))
            elif tool_name == "brain_smoke_test":
                return self._smoke_test(args.get("url"), args.get("endpoint", "/api/health"))
            return f"Tool {tool_name} not found"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _start_poll(self, service_id: str, commit_sha: Optional[str] = None) -> Dict:
        """Start a background polling task."""
        if not service_id:
            return {"error": "service_id required"}

        # Cancel existing poll for this service
        if service_id in ACTIVE_POLLS:
            existing = ACTIVE_POLLS[service_id]
            if not existing["task"].done():
                existing["task"].cancel()
                logger.info(f"Cancelled existing poll for {service_id}")

        # Start new task
        task = asyncio.create_task(self._poll_loop(service_id, commit_sha))
        
        ACTIVE_POLLS[service_id] = {
            "commit_sha": commit_sha or "latest",
            "start_time": time.time(),
            "status": "polling",
            "task": task,
            "logs": []
        }
        
        # Log event
        try:
            from ... import _emit_event
            _emit_event("deploy_poll_started", "render_poller", {
                "service_id": service_id,
                "commit_sha": commit_sha
            })
        except ImportError:
            pass # Circular import or not available

        return {
            "success": True, 
            "message": f"Started polling {service_id}",
            "poll_id": f"poll_{service_id}_{int(time.time())}"
        }

    def _check_poll(self, service_id: str) -> Dict:
        """Check status of an active poll."""
        if service_id not in ACTIVE_POLLS:
            return {"status": "not_found", "message": "No active poll for this service."}
        
        poll = ACTIVE_POLLS[service_id]
        uptime = int(time.time() - poll["start_time"])
        
        # Check if task is done (failed or finished)
        if poll["task"].done():
             try:
                 result = poll["task"].result()
                 return {
                     "status": "complete",
                     "result": result,
                     "uptime_seconds": uptime
                 }
             except asyncio.CancelledError:
                 return {"status": "cancelled", "uptime_seconds": uptime}
             except Exception as e:
                 return {"status": "error", "error": str(e), "uptime_seconds": uptime}
        
        return {
            "status": "polling",
            "uptime_seconds": uptime,
            "commit_sha": poll["commit_sha"]
        }

    async def _poll_loop(self, service_id: str, commit_sha: Optional[str]):
        """Async loop to check Render API."""
        timeout_mins = 20
        start_time = time.time()
        
        if not self._api_key:
            # Simulation mode if no key
            await asyncio.sleep(2)
            if service_id == "srv-test":
                await asyncio.sleep(1)
                return {"success": True, "url": "https://test-app.onrender.com", "simulated": True}
                
            raise ValueError("RENDER_API_KEY not set")

        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"https://api.render.com/v1/services/{service_id}/deploys?limit=1"
        req = urllib.request.Request(url, headers=headers)
        
        while time.time() - start_time < (timeout_mins * 60):
            try:
                loop = asyncio.get_running_loop()
                # Use run_in_executor for blocking urlopen
                msg = await loop.run_in_executor(None, lambda: self._fetch_url(req))
                
                if "error" in msg:
                    logger.error(f"Render API error: {msg['error']}")
                else:
                    data = msg.get("json", [])
                    if data:
                        latest = data[0].get("deploy")
                        if latest:
                            status = latest.get("status")
                            # Match commit if provided
                            latest_commit = latest.get("commit", {}).get("id")
                            if commit_sha and latest_commit and not latest_commit.startswith(commit_sha):
                                # Not our commit yet
                                pass
                            elif status == "live":
                                deploy_url = f"https://{service_id}.onrender.com" # Simplification
                                
                                # Run smoke test!
                                smoke = self._smoke_test(deploy_url)
                                
                                # Log complete
                                try:
                                    from ... import _emit_event
                                    _emit_event("deploy_complete", "render_poller", {
                                        "service_id": service_id,
                                        "status": "live",
                                        "url": deploy_url,
                                        "smoke_test": smoke
                                    })
                                except Exception:
                                    pass
                                
                                return {
                                    "success": True,
                                    "url": deploy_url,
                                    "smoke_test": smoke
                                }
                            elif status in ["build_failed", "update_failed", "canceled"]:
                                return {"success": False, "status": status}
            
            except Exception as e:
                logger.error(f"Poll error: {e}")

            await asyncio.sleep(30)
            
        return {"success": False, "error": "Timeout"}
        
    def _fetch_url(self, req) -> Dict:
        """Helper to fetch URL synchronously."""
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status == 200:
                    return {"json": json.load(response)}
                return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    def _smoke_test(self, url: str, endpoint: str = "/api/health") -> Dict:
        """Run a smoke test."""
        try:
            target = f"{url.rstrip('/')}{endpoint}"
            start = time.time()
            
            req = urllib.request.Request(target)
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    latency = (time.time() - start) * 1000
                    passed = response.status == 200
                    # Check JSON content if valid
                    try:
                        data = json.load(response)
                        if isinstance(data, dict) and data.get("status") == "healthy":
                            passed = True
                    except Exception:
                        pass
                    
                    return {
                        "passed": passed,
                        "status_code": response.status,
                        "latency_ms": latency
                    }
            except urllib.error.HTTPError as e:
                 return {
                    "passed": False,
                    "status_code": e.code,
                    "error": str(e)
                }
            except Exception as e:
                 return {
                    "passed": False, 
                    "error": str(e)
                 }

        except Exception as e:
            return {"passed": False, "error": str(e)}
