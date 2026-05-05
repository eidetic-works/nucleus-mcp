from mcp_server_nucleus.utils import hello_world


def test_hello_world_returns_expected_string():
    assert hello_world() == "Hello from Agent B"
