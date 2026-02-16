from typing import List, Dict, Any
from .base import Capability

class WebOps(Capability):
    @property
    def name(self) -> str:
        return "web_ops"

    @property
    def description(self) -> str:
        return "Tools for browsing the web (simulated via requests/search)."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "web_search",
                "description": "Search Google for a query.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "query": {"type": "string"},
                        "num_results": {"type": "integer", "default": 5}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "web_read_page",
                "description": "Read text content from a URL.",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> str:
        """Execute web operations."""
        if tool_name == "web_search":
            query = args['query']
            num_results = args.get('num_results', 5)
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=num_results))
                
                if not results:
                    return f"No results found for '{query}'."
                
                formatted = []
                for r in results:
                    formatted.append(f"- [{r['title']}]({r['href']})\n  {r['body']}")
                
                return "\n\n".join(formatted)
            except ImportError:
                return "Error: duckduckgo-search not installed. Please install it to use this feature."
            except Exception as e:
                return f"Search error: {e}"

        elif tool_name == "web_read_page":
            url = args['url']
            try:
                import urllib.request
                from bs4 import BeautifulSoup
                
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    html_content = response.read().decode('utf-8')
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                    script.decompose()
                
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                return f"URL: {url}\n\n{text[:8000]}..." # Truncate to 8k chars
            except ImportError:
                 return "Error: beautifulsoup4 not installed. Please install it to use this feature."
            except Exception as e:
                return f"Error reading {url}: {e}"
                
        return f"Tool {tool_name} not found in WebOps."
