"""
Nucleus Database Storage Abstraction
====================================
Provides a unified interface for JSON, SQLite, and Postgres backends
for the ContextBroker and Task Ledger. Preserves local-first philosophy
(via SQLite) while allowing Enterprise cloud scaling (via Postgres).
"""

import json
import logging
import sqlite3
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# Import models from broker
from .broker import ContextListing, ContextTransaction

logger = logging.getLogger("nucleus.db")

class StorageBackend(ABC):
    """Abstract interface for Nucleus storage backend."""
    
    @abstractmethod
    def create_listing(self, listing: ContextListing) -> str:
        """Create a new context listing."""
        pass
        
    @abstractmethod
    def search_listings(self, query: str, limit: int = 20, offset: int = 0) -> List[ContextListing]:
        """Search listings."""
        pass
        
    @abstractmethod
    def get_listing(self, listing_id: str) -> Optional[ContextListing]:
        """Get a single listing by ID."""
        pass
        
    @abstractmethod
    def count_listings(self) -> int:
        """Get total number of listings."""
        pass
        
    @abstractmethod
    def create_transaction(self, tx: ContextTransaction) -> str:
        """Record a transaction."""
        pass
        
    @abstractmethod
    def add_task(self, task_dict: Dict[str, Any]) -> str:
        """Add a new task."""
        pass
        
    @abstractmethod
    def list_tasks(self, status: Optional[str] = None, priority: Optional[int] = None, 
                   skill: Optional[str] = None, claimed_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks matching filters."""
        pass
        
    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a single task by ID."""
        pass
        
    @abstractmethod
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task."""
        pass

class JSONBackend(StorageBackend):
    """Legacy file-based storage backend for backward compatibility."""
    
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.listings_path = brain_path / "ledger" / "listings.json"
        self.transactions_path = brain_path / "ledger" / "transactions.jsonl"
        self.tasks_path = brain_path / "ledger" / "tasks.json"
        
        self.listings_path.parent.mkdir(parents=True, exist_ok=True)
        from .locking import get_lock
        self._get_lock = get_lock
        
    def _load_listings(self) -> Dict[str, ContextListing]:
        with self._get_lock("broker", self.brain_path).section():
            if not self.listings_path.exists():
                return {}
            try:
                data = json.loads(self.listings_path.read_text())
                return {k: ContextListing(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading listings: {e}")
                return {}

    def _save_listings(self, listings: Dict[str, ContextListing]):
        with self._get_lock("broker", self.brain_path).section():
            data = {k: v.model_dump() for k, v in listings.items()}
            self.listings_path.write_text(json.dumps(data, indent=2))
            
    def _load_tasks(self) -> List[Dict]:
        with self._get_lock("ledger", self.brain_path).section():
            if not self.tasks_path.exists():
                return []
            try:
                data = self.tasks_path.read_text().strip()
                if not data: return []
                return json.loads(data)
            except Exception as e:
                logger.error(f"Failed to read tasks.json: {e}")
                return []

    def _save_tasks(self, tasks: List[Dict]):
        with self._get_lock("ledger", self.brain_path).section():
            self.tasks_path.parent.mkdir(parents=True, exist_ok=True)
            self.tasks_path.write_text(json.dumps(tasks, indent=2))

    def create_listing(self, listing: ContextListing) -> str:
        listings = self._load_listings()
        listings[listing.id] = listing
        self._save_listings(listings)
        return listing.id

    def search_listings(self, query: str, limit: int = 20, offset: int = 0) -> List[ContextListing]:
        listings = self._load_listings()
        query = query.lower()
        results = []
        skipped = 0
        for lst in listings.values():
            if not query or query in lst.topic.lower() or query in lst.description.lower():
                if skipped < offset:
                    skipped += 1
                    continue
                results.append(lst)
                if len(results) >= limit:
                    break
        return results

    def get_listing(self, listing_id: str) -> Optional[ContextListing]:
        listings = self._load_listings()
        return listings.get(listing_id)

    def count_listings(self) -> int:
        return len(self._load_listings())

    def create_transaction(self, tx: ContextTransaction) -> str:
        with self._get_lock("ledger", self.brain_path).section():
            with open(self.transactions_path, "a") as f:
                f.write(tx.model_dump_json() + "\n")
        return tx.id
        
    def add_task(self, task_dict: Dict[str, Any]) -> str:
        tasks = self._load_tasks()
        tasks.append(task_dict)
        self._save_tasks(tasks)
        return task_dict["id"]
        
    def list_tasks(self, status: Optional[str] = None, priority: Optional[int] = None, 
                   skill: Optional[str] = None, claimed_by: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = self._load_tasks()
        result = []
        for t in tasks:
            if status and t.get("status") != status: continue
            if priority is not None and t.get("priority") != priority: continue
            if skill and skill not in t.get("required_skills", []): continue
            if claimed_by and t.get("claimed_by") != claimed_by: continue
            result.append(t)
        return result
        
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        tasks = self._load_tasks()
        for t in tasks:
            if t.get("id") == task_id:
                return t
        return None
        
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        tasks = self._load_tasks()
        changed = False
        for i, t in enumerate(tasks):
            if t.get("id") == task_id:
                tasks[i].update(updates)
                tasks[i]["updated_at"] = datetime.now().isoformat()
                changed = True
                break
        if changed:
            self._save_tasks(tasks)
        return changed

class SQLiteBackend(StorageBackend):
    """Local SQLite database backend for Sovereign OS defaults."""
    
    def __init__(self, brain_path: Path):
        self.db_path = brain_path / "nucleus.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _get_conn(self):
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10,  # Handle concurrent agent access gracefully
            isolation_level=None  # Manage transactions explicitly if needed
        )
        conn.row_factory = sqlite3.Row
        return conn
        
    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Listings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    provider_id TEXT,
                    topic TEXT,
                    description TEXT,
                    content TEXT,
                    price REAL,
                    type TEXT,
                    created_at TEXT
                )
            ''')
            
            # Index for searches
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_listings_topic ON listings(topic COLLATE NOCASE)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_listings_desc ON listings(description COLLATE NOCASE)')
            
            # Transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    listing_id TEXT,
                    buyer_id TEXT,
                    seller_id TEXT,
                    amount REAL,
                    timestamp TEXT,
                    content TEXT
                )
            ''')
            
            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    status TEXT,
                    priority INTEGER,
                    blocked_by TEXT, -- JSON array
                    required_skills TEXT, -- JSON array
                    claimed_by TEXT,
                    source TEXT,
                    escalation_reason TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)')
            
            conn.commit()

    def create_listing(self, listing: ContextListing) -> str:
        with self._get_conn() as conn:
            conn.execute(
                '''INSERT INTO listings 
                   (id, provider_id, topic, description, content, price, type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (listing.id, listing.provider_id, listing.topic, listing.description, 
                 listing.content, listing.price, listing.type, listing.created_at)
            )
        return listing.id

    def search_listings(self, query: str, limit: int = 20, offset: int = 0) -> List[ContextListing]:
        with self._get_conn() as conn:
            if not query:
                cursor = conn.execute(
                    'SELECT * FROM listings ORDER BY created_at DESC LIMIT ? OFFSET ?',
                    (limit, offset)
                )
            else:
                like_query = f"%{query}%"
                cursor = conn.execute(
                    '''SELECT * FROM listings 
                       WHERE topic LIKE ? OR description LIKE ? 
                       ORDER BY created_at DESC LIMIT ? OFFSET ?''',
                    (like_query, like_query, limit, offset)
                )
            
            return [ContextListing(**dict(row)) for row in cursor.fetchall()]

    def get_listing(self, listing_id: str) -> Optional[ContextListing]:
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT * FROM listings WHERE id = ?', (listing_id,))
            row = cursor.fetchone()
            if row:
                return ContextListing(**dict(row))
            return None

    def count_listings(self) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT COUNT(*) as count FROM listings')
            return cursor.fetchone()['count']

    def create_transaction(self, tx: ContextTransaction) -> str:
        with self._get_conn() as conn:
            conn.execute(
                '''INSERT INTO transactions 
                   (id, listing_id, buyer_id, seller_id, amount, timestamp, content)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (tx.id, tx.listing_id, tx.buyer_id, tx.seller_id, tx.amount, tx.timestamp, tx.content)
            )
        return tx.id

    def add_task(self, task_dict: Dict[str, Any]) -> str:
        with self._get_conn() as conn:
            conn.execute(
                '''INSERT INTO tasks 
                   (id, description, status, priority, blocked_by, required_skills, 
                    claimed_by, source, escalation_reason, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    task_dict["id"], task_dict["description"], task_dict["status"], 
                    task_dict["priority"], json.dumps(task_dict.get("blocked_by", [])),
                    json.dumps(task_dict.get("required_skills", [])), task_dict.get("claimed_by"),
                    task_dict.get("source"), task_dict.get("escalation_reason"),
                    task_dict.get("created_at"), task_dict.get("updated_at")
                )
            )
        return task_dict["id"]

    def list_tasks(self, status: Optional[str] = None, priority: Optional[int] = None, 
                   skill: Optional[str] = None, claimed_by: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)
        if claimed_by:
            query += " AND claimed_by = ?"
            params.append(claimed_by)
            
        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                t = dict(row)
                t["blocked_by"] = json.loads(t["blocked_by"]) if t["blocked_by"] else []
                t["required_skills"] = json.loads(t["required_skills"]) if t["required_skills"] else []
                
                if skill and skill not in t["required_skills"]:
                    continue
                    
                results.append(t)
            return results

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            t = dict(row)
            t["blocked_by"] = json.loads(t["blocked_by"]) if t["blocked_by"] else []
            t["required_skills"] = json.loads(t["required_skills"]) if t["required_skills"] else []
            return t

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
            
        update_cols = []
        params = []
        
        # Format JSON arrays
        for k in ["blocked_by", "required_skills"]:
            if k in updates:
                updates[k] = json.dumps(updates[k])
                
        for k, v in updates.items():
            update_cols.append(f"{k} = ?")
            params.append(v)
            
        update_cols.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        params.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(update_cols)} WHERE id = ?"
        
        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

class PostgresBackend(StorageBackend):
    """Enterprise Postgres backend for scaling Nucleus to multi-node setups."""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
        except ImportError:
            raise ImportError(
                "PostgresBackend requires psycopg2-binary to be installed. "
                "Run: pip install psycopg2-binary"
            )
        self._init_db()
            
    def _get_conn(self):
        return self.psycopg2.connect(self.connection_url, cursor_factory=self.extras.RealDictCursor)
        
    def _init_db(self):
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS listings (
                        id TEXT PRIMARY KEY,
                        provider_id TEXT,
                        topic TEXT,
                        description TEXT,
                        content TEXT,
                        price REAL,
                        type TEXT,
                        created_at TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id TEXT PRIMARY KEY,
                        listing_id TEXT,
                        buyer_id TEXT,
                        seller_id TEXT,
                        amount REAL,
                        timestamp TEXT,
                        content TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        description TEXT,
                        status TEXT,
                        priority INTEGER,
                        blocked_by JSONB,
                        required_skills JSONB,
                        claimed_by TEXT,
                        source TEXT,
                        escalation_reason TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                ''')
            conn.commit()
    
    def create_listing(self, listing: ContextListing) -> str:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''INSERT INTO listings 
                       (id, provider_id, topic, description, content, price, type, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                    (listing.id, listing.provider_id, listing.topic, listing.description, 
                     listing.content, listing.price, listing.type, listing.created_at)
                )
            conn.commit()
        return listing.id

    def search_listings(self, query: str, limit: int = 20, offset: int = 0) -> List[ContextListing]:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                if not query:
                    cursor.execute(
                        'SELECT * FROM listings ORDER BY created_at DESC LIMIT %s OFFSET %s',
                        (limit, offset)
                    )
                else:
                    like_query = f"%{query}%"
                    cursor.execute(
                        '''SELECT * FROM listings 
                           WHERE topic ILIKE %s OR description ILIKE %s 
                           ORDER BY created_at DESC LIMIT %s OFFSET %s''',
                        (like_query, like_query, limit, offset)
                    )
                return [ContextListing(**row) for row in cursor.fetchall()]

    def get_listing(self, listing_id: str) -> Optional[ContextListing]:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM listings WHERE id = %s', (listing_id,))
                row = cursor.fetchone()
                if row:
                    return ContextListing(**row)
                return None

    def count_listings(self) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) as count FROM listings')
                return cursor.fetchone()['count']

    def create_transaction(self, tx: ContextTransaction) -> str:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''INSERT INTO transactions 
                       (id, listing_id, buyer_id, seller_id, amount, timestamp, content)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (tx.id, tx.listing_id, tx.buyer_id, tx.seller_id, tx.amount, tx.timestamp, tx.content)
                )
            conn.commit()
        return tx.id

    def add_task(self, task_dict: Dict[str, Any]) -> str:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''INSERT INTO tasks 
                       (id, description, status, priority, blocked_by, required_skills, 
                        claimed_by, source, escalation_reason, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (
                        task_dict["id"], task_dict["description"], task_dict["status"], 
                        task_dict["priority"], self.extras.Json(task_dict.get("blocked_by", [])),
                        self.extras.Json(task_dict.get("required_skills", [])), task_dict.get("claimed_by"),
                        task_dict.get("source"), task_dict.get("escalation_reason"),
                        task_dict.get("created_at"), task_dict.get("updated_at")
                    )
                )
            conn.commit()
        return task_dict["id"]

    def list_tasks(self, status: Optional[str] = None, priority: Optional[int] = None, 
                   skill: Optional[str] = None, claimed_by: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = %s"
            params.append(status)
        if priority is not None:
            query += " AND priority = %s"
            params.append(priority)
        if claimed_by:
            query += " AND claimed_by = %s"
            params.append(claimed_by)
        if skill:
            query += " AND required_skills @> %s::jsonb"
            params.append(json.dumps([skill]))
            
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return dict(row)

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
            
        update_cols = []
        params = []
        
        for k in ["blocked_by", "required_skills"]:
            if k in updates:
                updates[k] = self.extras.Json(updates[k])
                
        for k, v in updates.items():
            update_cols.append(f"{k} = %s")
            params.append(v)
            
        update_cols.append("updated_at = %s")
        params.append(datetime.now().isoformat())
        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(update_cols)} WHERE id = %s"
        
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows_updated = cursor.rowcount
            conn.commit()
            return rows_updated > 0

def get_storage_backend(brain_path: Path) -> StorageBackend:
    """Factory to get the configured storage backend."""
    import yaml
    
    db_url = os.environ.get("NUCLEUS_DATABASE_URL")
    if db_url:
        logger.info("Using PostgresStorageBackend via NUCLEUS_DATABASE_URL")
        return PostgresBackend(db_url)
        
    config_path = brain_path / "config" / "nucleus.yaml"
    if config_path.exists():
        try:
            with config_path.open() as f:
                config = yaml.safe_load(f) or {}
                storage_conf = config.get("storage", {})
                backend_type = storage_conf.get("backend", "sqlite")
                
                if backend_type == "json":
                    return JSONBackend(brain_path)
                elif backend_type == "postgres":
                    pg_url = storage_conf.get("postgres", {}).get("url")
                    if pg_url:
                        return PostgresBackend(pg_url)
                    else:
                        logger.warning("Postgres backend requested but no URL found. Falling back to SQLite.")
        except Exception as e:
            logger.error(f"Failed to parse storage config: {e}. Falling back to SQLite.")
            
    return SQLiteBackend(brain_path)
