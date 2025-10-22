from flask import current_app
from pymongo import MongoClient, ASCENDING, errors
from .config import Config

_CLIENT_KEY = "_mongo_client"

def _get_tls_option(cfg: Config) -> dict:
    """Derive TLS options from config."""
    opts = {}
    v = (cfg.MONGODB_TLS or "").strip().lower()
    if v in ("true", "1", "yes"):
        opts["tls"] = True
    elif v in ("false", "0", "no"):
        opts["tls"] = False
    # else leave empty to let URI drive TLS
    return opts

# PUBLIC_INTERFACE
def get_db():
    """Return the MongoDB database handle from the application context."""
    return current_app.config["MONGO_DB"]

def _ensure_indexes(db):
    """Create necessary indexes for collections."""
    devices = db.get_collection("devices")
    # Unique index on ip_address
    devices.create_index([("ip_address", ASCENDING)], name="uniq_ip", unique=True)
    # Indexes for frequent queries
    devices.create_index([("type", ASCENDING)], name="idx_type")
    devices.create_index([("status", ASCENDING)], name="idx_status")

def init_db(app) -> None:
    """
    Initialize MongoDB client and DB on app startup and create indexes.
    """
    cfg: Config = app.config.get("CONFIG_OBJECT") or app.config.get("config") or Config()
    # Store config object for later use
    app.config["CONFIG_OBJECT"] = cfg

    missing = cfg.validate()
    if missing:
        app.logger.warning("Missing required env vars: %s. DB features may fail until set.", ", ".join(missing))

    client_kwargs = _get_tls_option(cfg)
    try:
        client = MongoClient(cfg.MONGODB_URI, **client_kwargs) if cfg.MONGODB_URI else None
        db = client[cfg.MONGODB_DB_NAME] if (client and cfg.MONGODB_DB_NAME) else None
        app.config["MONGO_CLIENT"] = client
        app.config["MONGO_DB"] = db
        if db is not None:
            _ensure_indexes(db)
    except errors.PyMongoError as exc:
        app.logger.error("Failed to initialize MongoDB: %s", exc)
        app.config["MONGO_CLIENT"] = None
        app.config["MONGO_DB"] = None
