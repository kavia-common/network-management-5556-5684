import os
import threading
import urllib.parse
from typing import Optional, Tuple, Dict
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

# Module-level singleton references
_client_lock = threading.Lock()
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

DEFAULT_DB_NAME = "network_devices"  # Default DB per task requirement
# Devices collection name will be read from env var MONGODB_COLLECTION with default 'device'
DEVICES_COLLECTION = os.environ.get("MONGODB_COLLECTION", "device")


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
        # Split scheme and the rest
        if "://" not in uri:
            return uri
        scheme, rest = uri.split("://", 1)
        # Credentials exist if '@' before first '/'
        at_index = rest.find("@")
        slash_index = rest.find("/")
        if at_index != -1 and (slash_index == -1 or at_index < slash_index):
            # Replace credentials part up to '@'
            rest = "***@" + rest[at_index + 1 :]
        # If credentials in query string etc., we do not attempt deeper parsing here
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


def _build_uri_from_parts() -> Tuple[str, str]:
    """
    Build a MongoDB URI from individual parts when MONGODB_URI is not provided.

    Supports:
      - MONGODB_HOST (default: localhost)
      - MONGODB_PORT (default: 27017)
      - MONGODB_USERNAME (optional)
      - MONGODB_PASSWORD (optional)
      - MONGODB_DB_NAME (default: network_devices)
      - MONGODB_OPTIONS (optional, query string without leading '?')

    Returns: (uri, db_name)
    """
    host = os.environ.get("MONGODB_HOST", "localhost")
    port = os.environ.get("MONGODB_PORT", "27017")
    username = os.environ.get("MONGODB_USERNAME")
    password = os.environ.get("MONGODB_PASSWORD")
    db_name = os.environ.get("MONGODB_DB_NAME", DEFAULT_DB_NAME)
    options = os.environ.get("MONGODB_OPTIONS", "").strip()

    auth_part = ""
    if username:
        u = urllib.parse.quote_plus(username)
        p = urllib.parse.quote_plus(password or "")
        auth_part = f"{u}:{p}@"

    # Base standard URI (not SRV) to be widely compatible
    base = f"mongodb://{auth_part}{host}:{port}/{db_name}"
    if options:
        if options.startswith("?"):
            options = options[1:]
        uri = f"{base}?{options}"
    else:
        uri = base
    return uri, db_name


def _build_mongo_client() -> Tuple[MongoClient, str]:
    """
    Build a MongoClient from environment variables.

    Preference:
      - Use MONGODB_URI if present (preferred)
      - Otherwise construct from MONGODB_HOST/PORT/USERNAME/PASSWORD/etc., but
        only when an explicit host/port is configured.
      - Do NOT silently fall back to localhost unless explicitly configured.

    Also reads:
      - MONGODB_DB_NAME (default 'network_devices')
      - MONGODB_TLS (optional, boolean)
      - MONGODB_CONNECT_TIMEOUT_MS (optional, default 5000)
    """
    uri_env = os.environ.get("MONGODB_URI")
    db_name = os.environ.get("MONGODB_DB_NAME", DEFAULT_DB_NAME)

    explicit_parts_provided = any(
        os.environ.get(k)
        for k in ("MONGODB_HOST", "MONGODB_PORT", "MONGODB_USERNAME", "MONGODB_PASSWORD", "MONGODB_OPTIONS")
    )

    if uri_env:
        uri = uri_env
    elif explicit_parts_provided:
        uri, db_name = _build_uri_from_parts()
    else:
        # No explicit configuration given: do not assume localhost; construct a non-host URI with db_name only.
        # Many drivers allow URI without host, but for clarity, we will raise a config error upon connect attempt.
        # Using a clear message helps users set MONGODB_URI.
        raise RuntimeError(
            "MongoDB configuration missing. Set MONGODB_URI or provide explicit parts "
            "(MONGODB_HOST/MONGODB_PORT/etc.). No fallback to localhost is performed."
        )

    # TLS and timeout config
    tls = _env_bool(os.environ.get("MONGODB_TLS"))
    timeout_ms = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
    kwargs = {"serverSelectionTimeoutMS": timeout_ms}
    if tls:
        kwargs["tls"] = True

    # Log effective target safely (no credentials)
    info = _effective_target_info(uri, timeout_ms, tls, db_name)
    print(
        f"[MongoDB] Attempting connection | uri={info['uri']} db={info['db_name']} "
        f"tls={info['tls']} timeout_ms={info['timeout_ms']}"
    )

    client = MongoClient(uri, **kwargs)
    return client, db_name


def _ensure_indexes(db: Database) -> None:
    """
    Ensure required indexes exist for the device collection configured via MONGODB_COLLECTION:
      - Unique index on ip_address (name: 'uniq_ip')
      - Non-unique indexes on 'type' and 'status'
    """
    devices = db[DEVICES_COLLECTION]  # DEVICES_COLLECTION defaults to 'device'

    # Unique index on ip_address
    devices.create_index(
        [("ip_address", ASCENDING)],
        name="uniq_ip",
        unique=True,
        background=True,
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
    """
    Return a module-level singleton MongoClient, initialized from environment variables.

    On first initialization, verifies connectivity using 'ping' and ensures required indexes.
    Raises RuntimeError with clear message if connection fails.
    """
    global _client, _db
    if _client is None:
        with _client_lock:
            if _client is None:
                try:
                    client, db_name = _build_mongo_client()
                    # Verify connectivity
                    client.admin.command("ping")
                    # Store globals
                    _client = client
                    _db = _client[db_name]
                    # Ensure indexes
                    _ensure_indexes(_db)
                except PyMongoError as e:
                    # Clear any partial state and raise a descriptive error
                    _client = None
                    _db = None
                    raise RuntimeError(f"Failed to connect to MongoDB: {e}") from e
    return _client


# PUBLIC_INTERFACE
def get_db() -> Database:
    """Return the default Database instance, initializing the client if needed."""
    if _db is None:
        get_client()  # ensures _db is set or raises
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
      (False, error_message) if unhealthy

    The error message includes a masked URI host/cluster, db name, tls and timeout to aid troubleshooting.
    """
    try:
        client = get_client()
        client.admin.command("ping")
        return True, None
    except Exception as e:
        # Try to rebuild info for actionable error message
        uri_env = os.environ.get("MONGODB_URI")
        db_name = os.environ.get("MONGODB_DB_NAME", DEFAULT_DB_NAME)
        tls = _env_bool(os.environ.get("MONGODB_TLS"))
        timeout_ms = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
        explicit_parts_provided = any(
            os.environ.get(k)
            for k in ("MONGODB_HOST", "MONGODB_PORT", "MONGODB_USERNAME", "MONGODB_PASSWORD", "MONGODB_OPTIONS")
        )
        try:
            if uri_env:
                uri = uri_env
            elif explicit_parts_provided:
                uri, db_name = _build_uri_from_parts()
            else:
                uri = "mongodb://<unset>"
        except Exception:
            uri = "mongodb://<error-building-uri>"
        info = _effective_target_info(uri, timeout_ms, tls, db_name)
        hint = (
            "Verify MONGODB_URI, network access, credentials, and TLS settings. "
            "Set MONGODB_CONNECT_TIMEOUT_MS for slower networks if needed."
        )
        return False, (
            f"{str(e)} | target={info['uri']} db={info['db_name']} "
            f"tls={info['tls']} timeout_ms={info['timeout_ms']} | hint: {hint}"
        )


# Attempt eager initialization at import time to surface connectivity early but non-fatal.
try:
    # Try initialization if any Mongo-related configuration is present.
    if (
        os.environ.get("MONGODB_URI")
        or os.environ.get("MONGODB_HOST")
        or os.environ.get("MONGODB_DB_NAME")
        or os.environ.get("MONGODB_COLLECTION")
    ):
        get_client()
except Exception:
    # Avoid crashing import; health endpoint will report down with details.
    pass
