from __future__ import annotations

from typing import Optional
from pymongo import MongoClient, ASCENDING
from flask import current_app
from bson import ObjectId


class Database:
    """Simple DB wrapper to manage Mongo client and common operations."""

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

        self._client = MongoClient(self._uri, **kwargs)
        self._db = self._client[self._db_name]
        self._create_indexes()

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
            raise RuntimeError("Database is not connected.")
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
