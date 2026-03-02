import urllib.request
import urllib.parse
import json
import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Very strict allowlist for Egress proxying
ALLOWED_DOMAINS = [
    "pypi.org",
    "files.pythonhosted.org",
    "docs.python.org",
    "developer.mozilla.org",
    "github.com",
    "raw.githubusercontent.com"
]

def is_domain_allowed(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            return False
        # Exact match or subdomain
        for allowed in ALLOWED_DOMAINS:
            if domain == allowed or domain.endswith("." + allowed):
                return True
        return False
    except Exception:
        return False

def nucleus_curl_impl(url: str, method: str = "GET") -> str:
    """
    [EGRESS FIREWALL] Proxied HTTP fetch for Air-Gapped Agents.
    Enforces strict domain allowlists so agents cannot exfiltrate data.
    """
    if not is_domain_allowed(url):
        error_msg = f"🚨 Egress Firewall Blocked: Domain not in ALLOWED_DOMAINS. URL: {url}"
        logger.warning(error_msg)
        return json.dumps({"success": False, "error": error_msg})
        
    try:
        req = urllib.request.Request(url, method=method, headers={'User-Agent': 'Nucleus-Hypervisor/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            body = response.read()
            # Try to decode as utf-8, else return base64
            try:
                decoded = body.decode('utf-8')
            except UnicodeDecodeError:
                import base64
                decoded = f"[BASE64_ENCODED]: {base64.b64encode(body).decode('utf-8')}"
                
            return json.dumps({
                "success": True,
                "status_code": status,
                "data": decoded[:100000] # Cap at 100KB to prevent memory exhaustion
            })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

def nucleus_pip_install_impl(package: str) -> str:
    """
    [EGRESS FIREWALL] Proxied pip install for Air-Gapped Agents.
    Executes 'pip install' on the host so the isolated agent can use the imported libraries.
    """
    # Basic sanitization to prevent command injection
    import re
    if not re.match(r"^[a-zA-Z0-9_\-\.\=\>\<]+$", package):
        return json.dumps({"success": False, "error": "Invalid pip package name/format."})
        
    try:
        # Run pip install on the host
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return json.dumps({"success": True, "output": result.stdout})
        else:
            return json.dumps({"success": False, "error": result.stderr})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
