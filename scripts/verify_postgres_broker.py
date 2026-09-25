import os
import sys
import logging
import uuid
from pathlib import Path
from datetime import datetime

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from mcp_server_nucleus.runtime.broker import ContextBroker, ContextListing, ContextTransaction
    from mcp_server_nucleus.runtime.db import get_storage_backend, PostgresBackend, SQLiteBackend
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("Postgres Verification")

def test_crud_operations(broker):
    logger.info("Starting CRUD tests...")
    
    # 1. Create Listings
    logger.info("Testing CREATE listings...")
    list_ids = []
    for i in range(5):
        l_id = broker.publish_listing(
            provider_id=f"agent-{i}",
            topic=f"Test Topic {i}",
            description=f"A very important test description for scalability test {i}",
            content=f"Secret Content {i}",
            price=1.5 * i
        )
        list_ids.append(l_id)
        
    logger.info(f"Published {len(list_ids)} listings.")
    
    # 2. Search Listings
    logger.info("Testing READ/SEARCH listings...")
    results = broker.search_listings(query="scalability", limit=3, offset=0)
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    
    results_page_2 = broker.search_listings(query="scalability", limit=3, offset=3)
    assert len(results_page_2) == 2, f"Expected 2 results, got {len(results_page_2)}"
    logger.info("Search pagination works correctly!")
    
    # 3. Get Listing by ID
    single_listing = broker.get_listing(list_ids[0])
    assert single_listing is not None
    assert single_listing.topic == "Test Topic 0"
    logger.info("Get listing by ID works correctly!")
    
    # 4. Count Listings
    count = broker.count_listings()
    assert count >= 5
    logger.info(f"Listing count works correctly: {count}")
    
    # 5. Transactions
    logger.info("Testing Transactions...")
    tx = broker.buy_context(buyer_id="agent-buyer", listing_id=list_ids[0])
    assert tx is not None
    assert tx.content == "Secret Content 0"
    logger.info("Transaction processed successfully!")
    
    # Task Backend Check
    logger.info("Testing Task CRUD...")
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    broker.storage.add_task({
        "id": task_id,
        "description": "Test Task",
        "status": "PENDING",
        "priority": 1,
        "blocked_by": [],
        "required_skills": ["python"],
        "claimed_by": None,
        "source": "test",
        "escalation_reason": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    
    task_fetched = broker.storage.get_task(task_id)
    assert task_fetched is not None
    assert task_fetched["description"] == "Test Task"
    
    broker.storage.update_task(task_id, {"status": "COMPLETED"})
    task_fetched_updated = broker.storage.get_task(task_id)
    assert task_fetched_updated["status"] == "COMPLETED"
    
    logger.info("CRUD operations completed successfully.")

def main():
    pg_url = os.environ.get("NUCLEUS_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    logger.info(f"Testing Postgres at: {pg_url}")
    
    os.environ["NUCLEUS_DATABASE_URL"] = pg_url
    
    brain_path = Path(".brain_test")
    brain_path.mkdir(exist_ok=True)
    
    try:
        backend = get_storage_backend(brain_path)
        if isinstance(backend, PostgresBackend):
            logger.info("🟢 Using PostgresBackend for verification.")
        else:
            logger.error("Failed to initialize a SQL-based backend.")
            return
    except Exception as e:
        logger.error(f"Backend connection failed: {e}")
        logger.warning("🟡 Falling back to SQLiteBackend for structural verification.")
        if "NUCLEUS_DATABASE_URL" in os.environ:
            del os.environ["NUCLEUS_DATABASE_URL"]
        backend = get_storage_backend(brain_path)
        if isinstance(backend, SQLiteBackend):
             logger.info("🟢 SQLite fallback initialized.")
        else:
            logger.error(f"Fallback Backend failed.")
            return
        
    broker = ContextBroker(brain_path)
    # Inject our testing backend directly to bypass the default JSON backend if necessary
    broker.storage = backend
    
    try:
        test_crud_operations(broker)
        logger.info("🟢 SQLITE/POSTGRES BROKER VERIFICATION: PASSED")
    except Exception as e:
        logger.error(f"🔴 SQLITE/POSTGRES BROKER VERIFICATION: FAILED - {e}")

if __name__ == "__main__":
    main()
