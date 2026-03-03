
import pytest
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def brain_path():
    """Create a temporary brain directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / ".brain_test"
        path.mkdir(parents=True)
        yield path

@pytest.fixture
def env(brain_path):
    """Setup environment variables for CLI testing."""
    env = os.environ.copy()
    env['NUCLEAR_BRAIN_PATH'] = str(brain_path)
    # Point PYTHONPATH to src
    src_path = str(Path(__file__).parent.parent / "src")
    env['PYTHONPATH'] = src_path + ":" + env.get('PYTHONPATH', '')
    return env

# =============================================================================
# TESTS
# =============================================================================

def test_brain_init(brain_path, env):
    """Test: nucleus init creates proper brain structure"""
    # If brain_path exists, remove it for a clean user simulation (CLI creates it)
    if brain_path.exists():
        shutil.rmtree(brain_path)

    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'init', str(brain_path), '--template', 'solo'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    
    assert result.returncode == 0, f"Init failed: {result.stderr}"
    
    # Check key directories exist
    required_dirs = ['ledger', 'sessions', 'slots', 'memory']
    for d in required_dirs:
        assert (brain_path / d).exists(), f"Missing directory: {d}"

def test_mounts_json_persistence(brain_path):
    """Test: mounts.json persistence format"""
    mounts_file = brain_path / "mounts.json"
    
    # Create a test mount configuration
    test_config = {
        "test_mount": {
            "transport": "stdio",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem", "/tmp"],
            "status": "configured"
        }
    }
    
    mounts_file.write_text(json.dumps(test_config, indent=2))
    
    # Verify it can be read back
    loaded = json.loads(mounts_file.read_text())
    assert loaded == test_config

def test_mounter_restore_logic(brain_path):
    """Test: Mounter.restore_mounts() logic"""
    # Create a mounts.json
    mounts_file = brain_path / "mounts.json"
    test_config = {
        "mock_server": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-c", "print('mock')"],
            "status": "configured"
        }
    }
    mounts_file.write_text(json.dumps(test_config, indent=2))
    
    # Import Mounter (ensure we use the src version)
    src_path = str(Path(__file__).parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        
    from mcp_server_nucleus.runtime.mounter_ops import Mounter
    
    # Initialize mounter
    mounter = Mounter(brain_path)
    
    # Verify it loaded the config
    assert "mock_server" in mounter.mount_configs
    assert mounter.mount_configs["mock_server"]["command"] == sys.executable

def test_cli_mount_add(brain_path, env):
    """Test: nucleus mount add command"""
    # Ensure brain exists first (usually init does this, but fixture makes a dir)
    # We need a defined mounts.json or empty one? 
    # Mounter handles missing file gracefully, but CLI might expect brain structure?
    # CLI mount add writes to mounts.json.
    
    result = subprocess.run(
        [
            sys.executable, '-m', 'mcp_server_nucleus.cli', 'mount', 'add',
            'test_fs',
            '--transport', 'stdio',
            '--command', 'npx',
            '--args', '@modelcontextprotocol/server-filesystem', '/tmp'
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=5
    )
    
    assert result.returncode == 0, f"Mount add failed: {result.stderr}"
    assert "Mount 'test_fs' added" in result.stdout
    
    # Verify mounts.json was created
    mounts_file = brain_path / "mounts.json"
    assert mounts_file.exists()
    mounts = json.loads(mounts_file.read_text())
    assert 'test_fs' in mounts

def test_cli_mount_list(brain_path, env):
    """Test: nucleus mount list command"""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'mount', 'list'],
        capture_output=True,
        text=True,
        env=env,
        timeout=5
    )
    
    assert result.returncode == 0, f"Mount list failed: {result.stderr}"

def test_cli_argument_parsing(brain_path, env):
    """Test: CLI argument parsing (no collision between 'command' and '--command')"""
    # This should NOT fail with "Unknown command: npx"
    # Note: 'parse_test' is the mount name (positional arg in some CLI parsers)
    result = subprocess.run(
        [
            sys.executable, '-m', 'mcp_server_nucleus.cli', 'mount', 'add',
            'parse_test',
            '--transport', 'stdio',
            '--command', 'npx'
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=5
    )
    
    # Should succeed (even without --args, it will just warn or succeed)
    assert "Unknown command" not in result.stderr
    assert "Unknown command" not in result.stdout

def test_cli_graph_command(brain_path, env):
    """Test: nucleus graph command runs without error."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'graph'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0, f"Graph command failed: {result.stderr}"
    assert "NUCLEUS ENGRAM CONTEXT GRAPH" in result.stdout or "Error" not in result.stdout

def test_cli_graph_json(brain_path, env):
    """Test: nucleus graph --json outputs valid JSON."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'graph', '--json'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0, f"Graph JSON failed: {result.stderr}"
    import json
    parsed = json.loads(result.stdout)
    assert "nodes" in parsed
    assert "stats" in parsed

def test_cli_graph_neighbors_missing(brain_path, env):
    """Test: nucleus graph --neighbors with missing key shows error."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'graph', '--neighbors', 'nonexistent_key_xyz'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0  # Exits cleanly even on missing key

def test_cli_billing_command(brain_path, env):
    """Test: nucleus billing command runs without error."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'billing'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0, f"Billing command failed: {result.stderr}"
    assert "NUCLEUS USAGE BILLING" in result.stdout

def test_cli_billing_json(brain_path, env):
    """Test: nucleus billing --json outputs valid JSON."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'billing', '--json'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0, f"Billing JSON failed: {result.stderr}"
    import json
    parsed = json.loads(result.stdout)
    assert "total_cost_units" in parsed
    assert "cost_model" in parsed

def test_cli_billing_group_by_tier(brain_path, env):
    """Test: nucleus billing --group-by tier works."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'billing', '--group-by', 'tier'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0, f"Billing tier failed: {result.stderr}"
    assert "NUCLEUS USAGE BILLING" in result.stdout

def test_cli_billing_group_by_session(brain_path, env):
    """Test: nucleus billing --group-by session works."""
    result = subprocess.run(
        [sys.executable, '-m', 'mcp_server_nucleus.cli', 'billing', '--group-by', 'session'],
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )
    assert result.returncode == 0, f"Billing session failed: {result.stderr}"


def test_version_consistency():
    """Test: Version in pyproject.toml matches expected"""
    dev_toml = Path(__file__).parent.parent / "pyproject.toml"
    
    if dev_toml.exists():
        content = dev_toml.read_text()
        # Updated for v1.2.0 GA release
        assert 'version = "1.2.1"' in content, "pyproject.toml version mismatch"
