"""
Coverage tests for runtime/capabilities/web_ops.py
"""
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities.web_ops import WebOps


@pytest.fixture
def web_ops():
    return WebOps()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, web_ops):
        assert web_ops.name == "web_ops"

    def test_description(self, web_ops):
        assert "web" in web_ops.description.lower()


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_two_tools(self, web_ops):
        tools = web_ops.get_tools()
        names = [t["name"] for t in tools]
        assert "web_search" in names
        assert "web_read_page" in names

    def test_search_required(self, web_ops):
        tools = web_ops.get_tools()
        tool = [t for t in tools if t["name"] == "web_search"][0]
        assert tool["parameters"]["required"] == ["query"]

    def test_read_page_required(self, web_ops):
        tools = web_ops.get_tools()
        tool = [t for t in tools if t["name"] == "web_read_page"][0]
        assert tool["parameters"]["required"] == ["url"]


# ---------------------------------------------------------------------------
# web_search
# ---------------------------------------------------------------------------
class TestWebSearch:
    def test_search_success(self, web_ops):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "Body 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Body 2"},
        ]

        mock_ddgs_class = MagicMock()
        mock_ddgs_class.return_value = mock_ddgs

        with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
            result = web_ops.execute_tool("web_search", {"query": "test query", "num_results": 2})
            assert "Result 1" in result
            assert "https://example.com/1" in result
            assert "Result 2" in result

    def test_search_no_results(self, web_ops):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = []

        mock_ddgs_class = MagicMock()
        mock_ddgs_class.return_value = mock_ddgs

        with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
            result = web_ops.execute_tool("web_search", {"query": "nonexistent"})
            assert "No results" in result

    def test_search_import_error(self, web_ops):
        # Simulate duckduckgo_search not installed
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "duckduckgo_search":
                raise ImportError("Not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = web_ops.execute_tool("web_search", {"query": "test"})
            assert "duckduckgo-search not installed" in result

    def test_search_exception(self, web_ops):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.side_effect = Exception("API error")

        mock_ddgs_class = MagicMock()
        mock_ddgs_class.return_value = mock_ddgs

        with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
            result = web_ops.execute_tool("web_search", {"query": "test"})
            assert "Search error" in result

    def test_search_default_num_results(self, web_ops):
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"title": "R", "href": "https://e.com", "body": "B"},
        ]

        mock_ddgs_class = MagicMock()
        mock_ddgs_class.return_value = mock_ddgs

        with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
            web_ops.execute_tool("web_search", {"query": "test"})
            # Default num_results should be 5
            mock_ddgs.text.assert_called_once_with("test", max_results=5)


# ---------------------------------------------------------------------------
# web_read_page
# ---------------------------------------------------------------------------
class TestWebReadPage:
    def test_read_page_success(self, web_ops):
        html = "<html><body><h1>Hello World</h1><p>Content here</p></body></html>"
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = html.encode('utf-8')

        mock_bs4 = MagicMock()
        mock_soup = MagicMock()
        mock_soup.get_text.return_value = "Hello World\nContent here"
        mock_bs4.BeautifulSoup.return_value = mock_soup

        with patch("urllib.request.urlopen", return_value=mock_response):
            with patch.dict("sys.modules", {"bs4": mock_bs4}):
                result = web_ops.execute_tool("web_read_page", {"url": "https://example.com"})
                assert "https://example.com" in result
                assert "Hello World" in result

    def test_read_page_strips_script_style(self, web_ops):
        """Verify script/style/nav elements are decomposed."""
        html = "<html><script>bad()</script><style>.x{}</style><body>Good</body></html>"
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = html.encode('utf-8')

        # Use real BeautifulSoup if available, otherwise mock
        try:
            from bs4 import BeautifulSoup
            with patch("urllib.request.urlopen", return_value=mock_response):
                result = web_ops.execute_tool("web_read_page", {"url": "https://example.com"})
                assert "Good" in result
                assert "bad()" not in result
        except ImportError:
            # Mock bs4
            mock_bs4 = MagicMock()
            mock_soup = MagicMock()
            mock_soup.get_text.return_value = "Good"
            mock_bs4.BeautifulSoup.return_value = mock_soup
            with patch("urllib.request.urlopen", return_value=mock_response):
                with patch.dict("sys.modules", {"bs4": mock_bs4}):
                    result = web_ops.execute_tool("web_read_page", {"url": "https://example.com"})
                    assert "Good" in result

    def test_read_page_import_error(self, web_ops):
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "bs4":
                raise ImportError("Not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = web_ops.execute_tool("web_read_page", {"url": "https://example.com"})
            assert "beautifulsoup4 not installed" in result

    def test_read_page_exception(self, web_ops):
        mock_bs4 = MagicMock()

        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with patch.dict("sys.modules", {"bs4": mock_bs4}):
                result = web_ops.execute_tool("web_read_page", {"url": "https://bad.url"})
                assert "Error reading" in result
                assert "Connection refused" in result


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------
class TestUnknownTool:
    def test_unknown_tool(self, web_ops):
        result = web_ops.execute_tool("nonexistent", {})
        assert "not found" in result
