from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from flask import current_app
from pymongo import MongoClient, ASCENDING, errors
from pymongo.collection import Collection
from bson import ObjectId

from .config import Config


# -----------------------------
# Repository Abstraction
# -----------------------------

class RepositoryError(Exception):
    """Base repository error."""


class DuplicateIPError(RepositoryError):
    """Raised when a duplicate ip_address is attempted."""


class DeviceRepository:
    """Repository interface for device CRUD operations."""

    # PUBLIC_INTERFACE
    def init(self) -> None:
        """Initialize underlying storage and ensure indexes if needed."""

    # PUBLIC_INTERFACE
    def ensure_indexes(self) -> None:
        """Ensure unique and helpful indexes."""

    # PUBLIC_INTERFACE
    def create_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a device and return the created record."""

    # PUBLIC_INTERFACE
    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a device by its string id."""

    # PUBLIC_INTERFACE
    def get_device_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """Fetch a device by its IP address."""

    # PUBLIC_INTERFACE
    def list_devices(
        self,
        filters: Dict[str, Optional[str]],
        pagination: Tuple[int, int],
        sorting: Tuple[str, int],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """List devices matching filters with pagination and sorting."""

    # PUBLIC_INTERFACE
    def update_device(self, device_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a device and return the updated record."""

    # PUBLIC_INTERFACE
    def delete_device(self, device_id: str) -> bool:
        """Delete a device by id."""


# -----------------------------
# Mongo Implementation
# -----------------------------

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


def _serialize_mongo(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    for f in ("last_checked", "created_at", "updated_at"):
        v = doc.get(f)
        if isinstance(v, datetime):
            doc[f] = v.isoformat() + "Z"
    return doc


class MongoDeviceRepository(DeviceRepository):
    def __init__(self, client: MongoClient, db_name: str) -> None:
        self.client = client
        self.db = client[db_name]

    def _col(self) -> Collection:
        return self.db.get_collection("devices")

    def init(self) -> None:
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        devices = self._col()
        devices.create_index([("ip_address", ASCENDING)], name="uniq_ip", unique=True)
        devices.create_index([("type", ASCENDING)], name="idx_type")
        devices.create_index([("status", ASCENDING)], name="idx_status")

    def create_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            res = self._col().insert_one(data)
        except errors.DuplicateKeyError:
            raise DuplicateIPError("Device with this IP already exists")
        created = self._col().find_one({"_id": res.inserted_id})
        return _serialize_mongo(created)

    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(device_id):
            raise ValueError("Invalid ObjectId")
        doc = self._col().find_one({"_id": ObjectId(device_id)})
        return _serialize_mongo(doc) if doc else None

    def get_device_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        doc = self._col().find_one({"ip_address": ip})
        return _serialize_mongo(doc) if doc else None

    def list_devices(
        self,
        filters: Dict[str, Optional[str]],
        pagination: Tuple[int, int],
        sorting: Tuple[str, int],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        q: Dict[str, Any] = {}
        if filters.get("type"):
            q["type"] = filters["type"]
        if filters.get("status"):
            q["status"] = filters["status"]
        if filters.get("q"):
            term = filters["q"]
            q["$or"] = [
                {"name": {"$regex": term, "$options": "i"}},
                {"ip_address": {"$regex": term, "$options": "i"}},
                {"location": {"$regex": term, "$options": "i"}},
            ]
        page, page_size = pagination
        skip = (page - 1) * page_size
        total = self._col().count_documents(q)
        field, direction = sorting
        cursor = self._col().find(q).skip(skip).limit(page_size).sort(field, direction)
        data = [_serialize_mongo(d) for d in cursor]
        last_page = (total + page_size - 1) // page_size if page_size > 0 else 1
        meta = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": last_page,
            "has_next": page < last_page,
            "has_prev": page > 1,
        }
        return data, meta

    def update_device(self, device_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(device_id):
            raise ValueError("Invalid ObjectId")
        try:
            updated = self._col().find_one_and_update(
                {"_id": ObjectId(device_id)},
                {"$set": data},
                return_document=True,
            )
        except errors.DuplicateKeyError:
            raise DuplicateIPError("Device with this IP already exists")
        return _serialize_mongo(updated) if updated else None

    def delete_device(self, device_id: str) -> bool:
        if not ObjectId.is_valid(device_id):
            raise ValueError("Invalid ObjectId")
        res = self._col().delete_one({"_id": ObjectId(device_id)})
        return res.deleted_count > 0


# -----------------------------
# In-Memory Implementation
# -----------------------------

def _serialize_mem(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(doc)
    for f in ("last_checked", "created_at", "updated_at"):
        v = out.get(f)
        if isinstance(v, datetime):
            out[f] = v.isoformat() + "Z"
    return out


class MemoryDeviceRepository(DeviceRepository):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: Dict[str, Dict[str, Any]] = {}  # id -> doc
        self._ip_index: Dict[str, str] = {}  # ip -> id

    def init(self) -> None:
        # nothing persistent to init
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        # uniqueness enforced via _ip_index
        return

    def create_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            ip = data.get("ip_address", "").strip()
            if ip in self._ip_index:
                raise DuplicateIPError("Device with this IP already exists")
            new_id = str(uuid.uuid4())
            doc = dict(data)
            doc["_id"] = new_id
            self._store[new_id] = doc
            self._ip_index[ip] = new_id
            return _serialize_mem(doc)

    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc = self._store.get(device_id)
            return _serialize_mem(doc) if doc else None

    def get_device_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            did = self._ip_index.get(ip)
            if not did:
                return None
            return _serialize_mem(self._store.get(did))

    def list_devices(
        self,
        filters: Dict[str, Optional[str]],
        pagination: Tuple[int, int],
        sorting: Tuple[str, int],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        with self._lock:
            items = list(self._store.values())

            # Filtering
            t = filters.get("type")
            if t:
                items = [d for d in items if d.get("type") == t]
            s = filters.get("status")
            if s:
                items = [d for d in items if d.get("status") == s]
            term = filters.get("q")
            if term:
                lt = term.lower()
                def matches(d: Dict[str, Any]) -> bool:
                    return any(
                        (str(d.get(k, "")).lower().find(lt) >= 0)
                        for k in ("name", "ip_address", "location")
                    )
                items = [d for d in items if matches(d)]

            # Sorting by created_at
            field, direction = sorting
            reverse = direction < 0
            def sort_key(d: Dict[str, Any]):
                v = d.get(field)
                if isinstance(v, datetime):
                    return v
                # try to parse ISO string if present
                if isinstance(v, str):
                    try:
                        return datetime.fromisoformat(v.replace("Z", ""))
                    except Exception:
                        return datetime.min
                return datetime.min
            items.sort(key=sort_key, reverse=reverse)

            # Pagination
            page, page_size = pagination
            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = items[start:end]
            last_page = (total + page_size - 1) // page_size if page_size > 0 else 1

            data = [_serialize_mem(d) for d in page_items]
            meta = {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": last_page,
                "has_next": page < last_page,
                "has_prev": page > 1,
            }
            return data, meta

    def update_device(self, device_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc = self._store.get(device_id)
            if not doc:
                return None
            # handle ip change uniqueness
            if "ip_address" in data:
                new_ip = (data.get("ip_address") or "").strip()
                if new_ip != doc.get("ip_address"):
                    if new_ip in self._ip_index:
                        raise DuplicateIPError("Device with this IP already exists")
                    # remove old index
                    old_ip = doc.get("ip_address")
                    if old_ip:
                        self._ip_index.pop(old_ip, None)
                    self._ip_index[new_ip] = device_id
            doc.update(data)
            self._store[device_id] = doc
            return _serialize_mem(doc)

    def delete_device(self, device_id: str) -> bool:
        with self._lock:
            doc = self._store.pop(device_id, None)
            if not doc:
                return False
            ip = doc.get("ip_address")
            if ip:
                self._ip_index.pop(ip, None)
            return True


# -----------------------------
# Repository selection helpers
# -----------------------------

_REPOSITORY_KEY = "_active_repository"
_DB_MODE_KEY = "_db_mode"

# PUBLIC_INTERFACE
def get_repository() -> DeviceRepository:
    """Return the active repository instance from Flask application config."""
    repo = current_app.config.get(_REPOSITORY_KEY)
    if not repo:
        raise RuntimeError("Repository not initialized. Did you call init_db(app)?")
    return repo

# PUBLIC_INTERFACE
def get_db_mode() -> str:
    """Return the active db mode string: 'mongo' or 'memory'."""
    return current_app.config.get(_DB_MODE_KEY, "memory")


def init_db(app) -> None:
    """
    Initialize repository based on DB_MODE with fallback to memory.

    - DB_MODE=='mongo': attempt Mongo connection; on missing config or failure, fallback to memory and log warning.
    - DB_MODE=='memory': use in-memory store.
    """
    cfg: Config = app.config.get("CONFIG_OBJECT") or app.config.get("config") or Config()
    app.config["CONFIG_OBJECT"] = cfg

    mode = (cfg.DB_MODE or "mongo").strip().lower()
    selected_mode = "memory"
    repository: DeviceRepository

    if mode == "mongo":
        missing = cfg.validate()
        if missing:
            app.logger.warning(
                "DB_MODE=mongo but missing %s. Falling back to in-memory repository.",
                ", ".join(missing),
            )
            repository = MemoryDeviceRepository()
            selected_mode = "memory"
        else:
            try:
                client_kwargs = _get_tls_option(cfg)
                client = MongoClient(cfg.MONGODB_URI, **client_kwargs)
                # quick ping to validate connection
                client.admin.command("ping")
                repository = MongoDeviceRepository(client, cfg.MONGODB_DB_NAME)
                selected_mode = "mongo"
            except errors.PyMongoError as exc:
                app.logger.warning(
                    "Mongo connection failed (%s). Falling back to in-memory repository.",
                    exc,
                )
                repository = MemoryDeviceRepository()
                selected_mode = "memory"
    else:
        repository = MemoryDeviceRepository()
        selected_mode = "memory"

    # Init and index
    try:
        repository.init()
    except Exception as exc:
        app.logger.warning("Repository init encountered an issue: %s", exc)

    app.config[_REPOSITORY_KEY] = repository
    app.config[_DB_MODE_KEY] = selected_mode

    if selected_mode == "memory":
        app.logger.warning("Running in in-memory DB mode. Data will not persist.")
    else:
        app.logger.info("Running in MongoDB mode.")
