from __future__ import annotations

from typing import Optional
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from flask import current_app
from bson import ObjectId


class Database:
    """Simple DB wrapper to manage Mongo client and common operations.

    Lazy connection strategy:
        - The client is not connected at initialization.
        - On first access to `db` or collections, a connection attempt is made.
        - If connection fails, a RuntimeError is raised with a clear message.
    """

    def __init__(self, uri: str, db_name: str, tls: bool = False, username: Optional[str] = None, password: Optional[str] = None):
        self._client: Optional[MongoClient] = None
        self._db = None
        self._uri = uri
        self._db_name = db_name
        self._tls = tls
        self._username = username
        self._password = password

    def connect(self):
        """Connect to MongoDB and create indexes if needed."""
        kwargs = {"tls": self._tls}
        if self._username and self._password:
            kwargs["username"] = self._username
            kwargs["password"] = self._password

        # Set a short server selection timeout so failures return quickly
        kwargs.setdefault("serverSelectionTimeoutMS", 2000)

        self._client = MongoClient(self._uri, **kwargs)
        # Trigger a server selection to validate connection lazily
        try:
            self._db = self._client[self._db_name]
            # Ping once to confirm server availability; if it fails, let it be handled by caller
            self._client.admin.command("ping")
            self._create_indexes()
        except ServerSelectionTimeoutError as e:
            # Keep client object but mark db as None to reflect disconnected state
            self._db = None
            raise RuntimeError(f"MongoDB is unavailable: {e}") from e
        except PyMongoError as e:
            self._db = None
            raise RuntimeError(f"MongoDB connection error: {e}") from e

    def try_connect(self) -> None:
        """Attempt to connect only if not already connected; do not raise fatal errors."""
        if self._db is not None:
            return
        try:
            self.connect()
        except Exception:
            # Swallow to allow endpoints to decide how to respond; properties will re-raise with a clear message.
            return

    def _create_indexes(self):
        """Create indexes for devices collection."""
        devices = self.devices
        # Unique index on ip_address
        devices.create_index([("ip_address", ASCENDING)], unique=True, name="uniq_ip")
        # Non-unique indexes on type and status
        devices.create_index([("type", ASCENDING)], name="idx_type")
        devices.create_index([("status", ASCENDING)], name="idx_status")

    @property
    def db(self):
        if self._db is None:
            # Attempt to connect lazily
            self.try_connect()
            if self._db is None:
                raise RuntimeError("Database is not connected (MongoDB unavailable or URI not set).")
        return self._db

    @property
    def devices(self):
        return self.db["devices"]

    @staticmethod
    def to_object_id(id_str: str) -> ObjectId:
        """Convert string to ObjectId raising ValueError on invalid values."""
        if not ObjectId.is_valid(id_str):
            raise ValueError("Invalid ObjectId format")
        return ObjectId(id_str)


def get_db() -> Database:
    """Get the Database instance stored in Flask app context."""
    db: Database = current_app.extensions["db_instance"]
    return db
