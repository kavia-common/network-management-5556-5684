import os
import threading
from typing import Optional
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database

# Module-level singleton references
_client_lock = threading.Lock()
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

DEFAULT_DB_NAME = "network_devices"
DEVICES_COLLECTION = "devices"


def _build_mongo_client() -> MongoClient:
    """
    Internal helper to build a MongoClient from environment variables.
    Required:
      - MONGO_URI
    Optional:
      - MONGO_DB_NAME (defaults to 'network_devices')
      - MONGO_TLS ('true' enables TLS)
      - MONGO_CONNECT_TIMEOUT_MS (integer)
    """
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        # Explicit message to guide configuration
        raise RuntimeError("MONGO_URI environment variable is required for MongoDB connection.")

    tls_env = os.environ.get("MONGO_TLS", "").strip().lower()
    tls = tls_env == "true"

    connect_timeout_env = os.environ.get("MONGO_CONNECT_TIMEOUT_MS")
    connect_timeout_ms: Optional[int] = None
    if connect_timeout_env:
        try:
            connect_timeout_ms = int(connect_timeout_env)
        except ValueError:
            # Fallback to None if invalid; better to log/raise in a larger app
            connect_timeout_ms = None

    # Assemble kwargs conditionally
    kwargs = {}
    if tls:
        kwargs["tls"] = True
    if connect_timeout_ms is not None:
        kwargs["connectTimeoutMS"] = connect_timeout_ms

    return MongoClient(mongo_uri, **kwargs)


def _ensure_indexes(db: Database) -> None:
    """
    Ensure required indexes exist for the devices collection:
      - Unique index on ip_address (name: 'uniq_ip')
      - Non-unique indexes on 'type' and 'status'
    """
    devices = db[DEVICES_COLLECTION]

    # Unique index on ip_address
    devices.create_index(
        [("ip_address", ASCENDING)],
        name="uniq_ip",
        unique=True,
        background=True,  # Run in background to avoid blocking
    )

    # Index on type
    devices.create_index(
        [("type", ASCENDING)],
        name="idx_type",
        background=True,
    )

    # Index on status
    devices.create_index(
        [("status", ASCENDING)],
        name="idx_status",
        background=True,
    )


# PUBLIC_INTERFACE
def get_client() -> MongoClient:
    """Return a module-level singleton MongoClient, initialized from environment variables."""
    global _client, _db
    if _client is None:
        with _client_lock:
            if _client is None:
                client = _build_mongo_client()
                # Assign to globals after successful construction
                _client = client

                # Initialize database and indexes
                db_name = os.environ.get("MONGO_DB_NAME", DEFAULT_DB_NAME)
                _db = _client[db_name]
                _ensure_indexes(_db)
    return _client


# PUBLIC_INTERFACE
def get_db() -> Database:
    """Return the default Database instance, initializing the client if needed."""
    if _db is None:
        get_client()  # ensures _db is set
    assert _db is not None  # for type checkers
    return _db


# PUBLIC_INTERFACE
def get_collection(name: str) -> Collection:
    """Return a collection from the default database by name."""
    return get_db()[name]


# Trigger client initialization optionally during import if MONGO_URI is present.
# We avoid raising here when MONGO_URI is missing so app can still start in environments
# where the database is not yet configured; actual DB access will raise if required.
try:
    if os.environ.get("MONGO_URI"):
        get_client()
except Exception:
    # Swallow exceptions at import-time to not crash startup logs; real access will raise
    # In a larger app, consider proper logging.
    pass
