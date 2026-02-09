
import pytest
import os
import tempfile
import json
from pathlib import Path
from mcp_server_nucleus.runtime.common import get_brain_path

@pytest.fixture
def temp_brain():
    """Create a temporary brain directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_brain = os.environ.get("NUCLEAR_BRAIN_PATH")
        os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
        
        # Initialize structure
        brain_path = Path(tmpdir)
        (brain_path / "engrams").mkdir(parents=True, exist_ok=True)
        (brain_path / "ledger").mkdir(parents=True, exist_ok=True)
        
        yield brain_path
        
        if old_brain:
            os.environ["NUCLEAR_BRAIN_PATH"] = old_brain
        else:
            del os.environ["NUCLEAR_BRAIN_PATH"]

@pytest.fixture
def sample_engrams(temp_brain):
    """Seed the brain with sample engrams."""
    engram_path = temp_brain / "engrams" / "ledger.jsonl"
    engrams = [
        {"key": "db_choice", "value": "PostgreSQL", "context": "Architecture", "intensity": 8},
        {"key": "ui_theme", "value": "Dark Mode", "context": "UI", "intensity": 5},
        {"key": "api_key", "value": "SECRET", "context": "Security", "intensity": 10},
    ]
    
    with open(engram_path, "w") as f:
        for e in engrams:
            f.write(json.dumps(e) + "\n")
            
    return engrams
