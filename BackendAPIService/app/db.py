import os
import threading
from typing import Optional, Tuple, Dict

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

# Module-level singleton references
_client_lock = threading.Lock()
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

# Per task instruction: hardcode database and collection names
DEFAULT_DB_NAME = "network_devices"
DEVICES_COLLECTION = "devices"


def _env_bool(value: Optional[str]) -> bool:
    """Parse truthy environment variable values."""
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _mask_uri(uri: str) -> str:
    """
    Return a masked Mongo URI suitable for logs by removing credentials.
    Examples:
      mongodb://user:pass@host:27017/db -> mongodb://***:***@host:27017/db
      mongodb+srv://user@cluster.mongodb.net/db -> mongodb+srv://***@cluster.mongodb.net/db
    """
    try:
        if "://" not in uri:
            return uri
        scheme, rest = uri.split("://", 1)
        at_index = rest.find("@")
        slash_index = rest.find("/")
        if at_index != -1 and (slash_index == -1 or at_index < slash_index):
            rest = "***@" + rest[at_index + 1 :]
        return f"{scheme}://{rest}"
    except Exception:
        return uri


def _effective_target_info(uri: str, timeout_ms: int, tls: bool, db_name: str) -> Dict[str, str]:
    """Build a dictionary with effective target info for logging and health reporting."""
    return {
        "uri": _mask_uri(uri),
        "db_name": db_name,
        "timeout_ms": str(timeout_ms),
        "tls": "true" if tls else "false",
    }


# No parts-based builder per instruction; only MONGODB_URI is supported for connection.


def _build_mongo_client() -> Tuple[MongoClient, str]:
    """
    Build a MongoClient strictly from MONGODB_URI and fixed DB/collection per task.
    """
    uri_env = os.environ.get("MONGODB_URI")
    db_name = DEFAULT_DB_NAME

    if not uri_env:
        # Unconfigured state
        return None, db_name  # type: ignore[return-value]

    tls = _env_bool(os.environ.get("MONGODB_TLS"))
    timeout_ms = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
    kwargs = {"serverSelectionTimeoutMS": timeout_ms}
    if tls:
        kwargs["tls"] = True

    info = _effective_target_info(uri_env, timeout_ms, tls, db_name)
    uri_part = f"uri={info['uri']} "
    db_part = f"db={info['db_name']} "
    tls_part = f"tls={info['tls']} "
    to_part = f"timeout_ms={info['timeout_ms']}"
    print("[MongoDB] " + "Connect | " + uri_part + db_part + tls_part + to_part)

    client = MongoClient(uri_env, **kwargs)
    return client, db_name


def _ensure_indexes(db: Database) -> None:
    """Ensure required indexes for device collection."""
    devices = db[DEVICES_COLLECTION]
    devices.create_index([("ip_address", ASCENDING)], name="uniq_ip", unique=True, background=True)
    devices.create_index([("type", ASCENDING)], name="idx_type", background=True)
    devices.create_index([("status", ASCENDING)], name="idx_status", background=True)


def _configuration_state() -> str:
    """
    Return configuration state string using only MONGODB_URI.
    """
    return "configured" if os.environ.get("MONGODB_URI") else "unconfigured"


# PUBLIC_INTERFACE
def get_client() -> MongoClient:
    """
    Return a module-level singleton MongoClient lazily.

    Behavior:
    - If no Mongo configuration is provided, raise RuntimeError only when DB is actually accessed.
    - If configuration exists but invalid, raise with clear details.
    """
    global _client, _db
    if _client is None:
        with _client_lock:
            if _client is None:
                # Build client; may return None if unconfigured
                client_db = _build_mongo_client()
                if client_db[0] is None:
                    # No configuration: warn and raise on access
                    print(
                        "[MongoDB][WARN] No MongoDB configuration detected "
                        "(MONGODB_URI or parts). Database access is disabled until configured."
                    )
                    raise RuntimeError(
                        "MongoDB is unconfigured. "
                        "Set MONGODB_URI or explicit connection parts to enable database access."
                    )
                client, db_name = client_db  # type: ignore[misc]
                try:
                    client.admin.command("ping")
                    _client = client
                    _db = _client[db_name]
                    _ensure_indexes(_db)
                except PyMongoError as e:
                    _client = None
                    _db = None
                    raise RuntimeError(f"Failed to connect to MongoDB: {e}") from e
    return _client  # type: ignore[return-value]


# PUBLIC_INTERFACE
def get_db() -> Database:
    """Return the default Database instance, initializing the client if needed."""
    if _db is None:
        get_client()
    assert _db is not None
    return _db


# PUBLIC_INTERFACE
def get_collection(name: str) -> Collection:
    """Return a collection from the default database by name."""
    return get_db()[name]


# PUBLIC_INTERFACE
def ping() -> Tuple[bool, Optional[str]]:
    """
    Perform a health ping against MongoDB.

    Returns:
      (True, None) if healthy
      (False, error_message) if unhealthy or unconfigured

    The error message includes masked URI/target info when available.
    """
    state = _configuration_state()
    if state == "unconfigured":
        return (
            False,
            "MongoDB is unconfigured; set MONGODB_URI or explicit parts to enable connectivity.",
        )
    try:
        client_db = _build_mongo_client()
        if client_db[0] is None:
            return (
                False,
                "MongoDB is unconfigured; set MONGODB_URI or explicit parts to enable connectivity.",
            )
        client, db_name = client_db  # type: ignore[misc]
        client.admin.command("ping")
        return True, None
    except Exception as e:
        uri_env = os.environ.get("MONGODB_URI")
        db_name = DEFAULT_DB_NAME
        tls = _env_bool(os.environ.get("MONGODB_TLS"))
        timeout_ms = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
        uri = uri_env or "mongodb://<unset>"
        info = _effective_target_info(uri, timeout_ms, tls, db_name)
        hint = "Verify MONGODB_URI, network access, credentials, TLS, and firewall rules."
        err_prefix = f"{str(e)} | target={info['uri']} "
        err_mid = f"db={info['db_name']} tls={info['tls']} "
        err_suf = f"timeout_ms={info['timeout_ms']} | hint: {hint}"
        return False, (err_prefix + err_mid + err_suf)

# Note: No eager initialization at import time. Lazy on first access only.
