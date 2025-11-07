import os
import threading
import urllib.parse
from typing import Optional, Tuple, Dict

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

# Bridge for environments that provide REACT_APP_* variables (commonly used by frontend builds).
# If backend variables are not present, map REACT_APP_* to backend MONGODB_* equivalents.
_REACT_TO_BACKEND_ENV_MAP = {
    "REACT_APP_MONGODB_URI": "MONGODB_URI",
    "REACT_APP_MONGODB_DB_NAME": "MONGODB_DB_NAME",
    "REACT_APP_MONGODB_USERNAME": "MONGODB_USERNAME",
    "REACT_APP_MONGODB_PASSWORD": "MONGODB_PASSWORD",
    "REACT_APP_MONGODB_OPTIONS": "MONGODB_OPTIONS",
}
for react_key, backend_key in _REACT_TO_BACKEND_ENV_MAP.items():
    if backend_key not in os.environ and react_key in os.environ:
        os.environ[backend_key] = os.environ[react_key]

# Module-level singleton references
_client_lock = threading.Lock()
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

DEFAULT_DB_NAME = "network"  # Default DB per updated requirement; can be overridden via MONGODB_DB_NAME
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


def _build_uri_from_parts() -> Tuple[str, str]:
    """
    Build a MongoDB URI from individual parts when MONGODB_URI is not provided.

    Supports:
      - MONGODB_HOST (default: localhost)
      - MONGODB_PORT (default: 27017)
      - MONGODB_USERNAME (optional)
      - MONGODB_PASSWORD (optional)
      - MONGODB_DB_NAME (default: network)
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
    Build a MongoClient from environment variables with lazy behavior.

    Preference:
      - Use MONGODB_URI if present (preferred)
      - Otherwise construct from parts if any related vars set
      - If nothing provided, do not raise here; allow app to start and only raise on actual DB access.

    Also reads:
      - MONGODB_DB_NAME (default 'network')
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
        # Nothing configured: return a sentinel to indicate unconfigured state
        return None, db_name  # type: ignore[return-value]

    tls = _env_bool(os.environ.get("MONGODB_TLS"))
    timeout_ms = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
    kwargs = {"serverSelectionTimeoutMS": timeout_ms}
    if tls:
        kwargs["tls"] = True

    info = _effective_target_info(uri, timeout_ms, tls, db_name)
    # Use multiple concatenated f-strings to stay within line length limits for flake8 (E501)
    # Compose message parts to comply with flake8 E501 (max line length 120)
    uri_part = f"uri={info['uri']} "
    db_part = f"db={info['db_name']} "
    tls_part = f"tls={info['tls']} "
    to_part = f"timeout_ms={info['timeout_ms']}"
    print("[MongoDB] " + "Connect | " + uri_part + db_part + tls_part + to_part)

    client = MongoClient(uri, **kwargs)
    return client, db_name


def _ensure_indexes(db: Database) -> None:
    """Ensure required indexes for device collection."""
    devices = db[DEVICES_COLLECTION]
    devices.create_index([("ip_address", ASCENDING)], name="uniq_ip", unique=True, background=True)
    devices.create_index([("type", ASCENDING)], name="idx_type", background=True)
    devices.create_index([("status", ASCENDING)], name="idx_status", background=True)


def _configuration_state() -> str:
    """
    Return configuration state string:
      - 'unconfigured' if no URI/parts present
      - 'configured' if some configuration exists (may still be invalid)
    """
    if os.environ.get("MONGODB_URI"):
        return "configured"
    if any(os.environ.get(k) for k in ("MONGODB_HOST", "MONGODB_PORT", "MONGODB_USERNAME", "MONGODB_PASSWORD", "MONGODB_OPTIONS")):
        return "configured"
    return "unconfigured"


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
        return False, "MongoDB is unconfigured; set MONGODB_URI or explicit parts to enable connectivity."
    try:
        client_db = _build_mongo_client()
        if client_db[0] is None:
            return False, "MongoDB is unconfigured; set MONGODB_URI or explicit parts to enable connectivity."
        client, db_name = client_db  # type: ignore[misc]
        client.admin.command("ping")
        return True, None
    except Exception as e:
        uri_env = os.environ.get("MONGODB_URI")
        db_name = os.environ.get("MONGODB_DB_NAME", DEFAULT_DB_NAME)
        tls = _env_bool(os.environ.get("MONGODB_TLS"))
        timeout_ms = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
        try:
            uri = uri_env or (_build_uri_from_parts()[0] if state == "configured" else "mongodb://<unset>")
        except Exception:
            uri = "mongodb://<error-building-uri>"
        info = _effective_target_info(uri, timeout_ms, tls, db_name)
        hint = "Verify MONGODB_URI, network access, credentials, TLS, and firewall rules."
        err_prefix = f"{str(e)} | target={info['uri']} "
        err_mid = f"db={info['db_name']} tls={info['tls']} "
        err_suf = f"timeout_ms={info['timeout_ms']} | hint: {hint}"
        return False, (err_prefix + err_mid + err_suf)

# Note: No eager initialization at import time. Lazy on first access only.
