import os
from datetime import datetime
from typing import Optional, Tuple

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Internal helper to parse boolean-like env values."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


# PUBLIC_INTERFACE
def get_mongo_client() -> MongoClient:
    """Return a configured MongoClient using environment variables.

    Environment variables:
    - MONGODB_URI: MongoDB connection string. Example: mongodb://user:pass@host:27017
    - MONGODB_TLS: Optional, whether to enable TLS/SSL (true/false). Defaults to false.

    Raises:
        RuntimeError: If MONGODB_URI is not provided.
    """
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise RuntimeError("MONGODB_URI environment variable is required")

    tls_enabled = _get_bool_env("MONGODB_TLS", default=False)

    # Initialize client; other options (timeouts/pool size) can be tuned via URI
    client = MongoClient(mongodb_uri, tls=tls_enabled)
    return client


# PUBLIC_INTERFACE
def get_database(client: MongoClient):
    """Return the MongoDB database object based on MONGODB_DB_NAME env var.

    Environment variables:
    - MONGODB_DB_NAME: Target database name. Example: network_devices

    Raises:
        RuntimeError: If MONGODB_DB_NAME is not provided.
    """
    db_name = os.getenv("MONGODB_DB_NAME")
    if not db_name:
        raise RuntimeError("MONGODB_DB_NAME environment variable is required")
    return client[db_name]


# PUBLIC_INTERFACE
def init_indexes(db) -> Tuple[bool, Optional[str]]:
    """Ensure indexes for the devices collection exist.

    Indexes:
    - Unique index on ip_address
    - Index on type
    - Index on status

    Returns:
        Tuple[bool, Optional[str]]: (success flag, error message if any)
    """
    try:
        devices = db.devices
        devices.create_index([("ip_address", ASCENDING)], unique=True, name="uniq_ip_address")
        devices.create_index([("type", ASCENDING)], name="idx_type")
        devices.create_index([("status", ASCENDING)], name="idx_status")
        return True, None
    except PyMongoError as ex:
        return False, str(ex)


# PUBLIC_INTERFACE
def with_timestamps(payload: dict, is_create: bool = True) -> dict:
    """Attach created_at/updated_at timestamps to payload in ISO format.

    Args:
        payload: dict to mutate and return
        is_create: whether this is a create operation

    Returns:
        dict: payload with timestamps
    """
    now = datetime.utcnow().isoformat() + "Z"
    if is_create:
        payload["created_at"] = now
    payload["updated_at"] = now
    return payload
