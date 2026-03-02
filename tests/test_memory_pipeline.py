import os
import json
import pytest
import tempfile
import asyncio
from pathlib import Path
from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline, EngramOp

@pytest.fixture
def temp_brain():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

class TestMemoryPipelineBasics:
    """Test basic Engram operations (ADD, UPDATE, DELETE)."""

    def test_explicit_add(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        
        result = pipeline.process(
            text="The sky is blue.",
            context="Fact",
            key="sky_color",
            operation="add"
        )
        
        assert result.get("added") == 1
        assert "mode" in result
        
        # Verify it was added to ledger
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 1
        assert engrams[0]["key"] == "sky_color"
        assert engrams[0]["value"] == "The sky is blue."

    def test_short_string_extraction(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        # "Fix bug" is 7 chars. Should be accepted.
        result = pipeline.process(text="Fix bug")
        assert result.get("added") == 1
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 1
        assert engrams[0]["value"] == "Fix bug"

    def test_explicit_update(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        pipeline.process(text="This system is at version one.", key="test_key", operation="add")
        
        result = pipeline.process(
            text="This system is now at version two.",
            key="test_key",
            operation="update"
        )
        
        assert result.get("updated") == 1
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 1
        assert engrams[0]["value"] == "This system is now at version two."
        assert engrams[0]["version"] == 2

    def test_explicit_delete(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        pipeline.process(text="This item is to be deleted.", key="del_key", operation="add")
        
        result = pipeline.process(
            text="Delete this item completely.",
            key="del_key",
            operation="delete"
        )
        
        assert result.get("deleted") == 1
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 0

class TestMemoryPipelineADUN:
    """Test the ADUN (Add, Delete, Update, Noop) intent processing."""

    def test_auto_pipeline_add(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        
        result = pipeline.process(text="React is a frontend library.")
        assert result.get("added", 0) > 0
        assert result["mode"] == "auto_pipeline"
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 1

    def test_auto_pipeline_noop(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        
        pipeline.process(text="React is a frontend library.")
        # Exact duplicate
        result = pipeline.process(text="React is a frontend library.")
        
        assert result.get("skipped", 0) > 0
        assert result.get("added", 0) == 0
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 1

    def test_auto_pipeline_update(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        # Using explicit key to force an update on the same topic via auto pipeline
        pipeline.process(text="React is incredibly slow.", key="react_speed", operation="add")
        
        result = pipeline.process(text="React is extremely fast actually.", key="react_speed")
        
        # It should auto-detect the value changed for the same key
        assert result["mode"] == "explicit_key"
        assert result.get("updated", 0) > 0
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 1
        assert engrams[0]["value"] == "React is extremely fast actually."

class TestMemoryPipelineDeduplication:
    """Test ledger deduplication logic on read."""

    def test_load_active_engrams_deduplicates(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        ledger_path = temp_brain / "engrams" / "ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Manually write duplicates to the ledger line by line
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"key": "key1", "value": "Value one.", "version": 1, "deleted": False}) + "\n")
            f.write(json.dumps({"key": "key1", "value": "Value two.", "version": 2, "deleted": False}) + "\n")
            f.write(json.dumps({"key": "key2", "value": "Value three.", "version": 1, "deleted": False}) + "\n")
            # This is a deletion record
            f.write(json.dumps({"key": "key2", "value": "", "version": 2, "deleted": True}) + "\n")
        
        engrams = pipeline._load_active_engrams()
        
        # Should be 2 engrams (key1 version 2, and key2 version 1). 
        # The key2 version 2 record was deleted, so it's skipped during load, leaving version 1.
        assert len(engrams) == 2
        
        # Verify key1 deduplication kept version 2
        key1_engram = next(e for e in engrams if e["key"] == "key1")
        assert key1_engram["value"] == "Value two."
        assert key1_engram["version"] == 2
        
        # Verify key2 fallback
        key2_engram = next(e for e in engrams if e["key"] == "key2")
        assert key2_engram["value"] == "Value three."
        assert key2_engram["version"] == 1

class TestMemoryPipelineConcurrency:
    """Simulate concurrent/high-volume writes."""

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, temp_brain):
        pipeline = MemoryPipeline(brain_path=temp_brain)
        
        async def write_process(i):
            # run process in a thread to simulate real usage
            return await asyncio.to_thread(
                pipeline.process,
                f"Concurrent memory {i}",
                "Test",
                5,
                "agent",
                f"concurrent_key_{i}"
            )
            
        # Launch 50 concurrent writes
        tasks = [write_process(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        assert all(r.get("added", 0) == 1 for r in results)
        
        engrams = pipeline._load_active_engrams()
        assert len(engrams) == 50

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
