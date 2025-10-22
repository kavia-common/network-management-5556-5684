from typing import Dict, Any, Tuple, List, Optional
from pymongo.collection import Collection
from pymongo import ReturnDocument
from datetime import datetime

from ..db import get_db
from ..validators import validate_device_payload
from ..utils import to_object_id, now_utc, try_ping

def _devices_col() -> Collection:
    db = get_db()
    if db is None:
        raise ValueError("Database is not configured")
    return db.get_collection("devices")

def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable dict."""
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    # convert datetimes to isoformat
    for f in ("last_checked", "created_at", "updated_at"):
        if doc.get(f) and isinstance(doc[f], datetime):
            doc[f] = doc[f].isoformat() + "Z"
    return doc

# PUBLIC_INTERFACE
def list_devices(filters: Dict[str, Optional[str]], page: int = 1, page_size: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """List devices with optional filters and simple pagination."""
    col = _devices_col()
    q: Dict[str, Any] = {}
    if filters.get("type"):
        q["type"] = filters["type"]
    if filters.get("status"):
        q["status"] = filters["status"]
    if filters.get("q"):
        term = filters["q"]
        # Simple OR search on name or ip_address using regex
        q["$or"] = [
            {"name": {"$regex": term, "$options": "i"}},
            {"ip_address": {"$regex": term, "$options": "i"}},
        ]

    # Bounds for pagination
    page = max(1, int(page or 1))
    page_size = min(100, max(1, int(page_size or 20)))
    skip = (page - 1) * page_size

    total = col.count_documents(q)
    cursor = col.find(q).skip(skip).limit(page_size).sort("created_at", -1)
    data = [_serialize(d) for d in cursor]
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

# PUBLIC_INTERFACE
def create_device(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new device after validation."""
    ok, errs = validate_device_payload(payload, partial=False)
    if not ok:
        raise ValueError("; ".join([f"{k}: {v}" for k, v in errs.items()]))

    col = _devices_col()
    now = now_utc()
    doc = {
        "name": payload["name"].strip(),
        "ip_address": payload["ip_address"].strip(),
        "type": payload["type"],
        "location": payload["location"].strip(),
        "status": payload["status"],
        "last_checked": payload.get("last_checked"),
        "created_at": now,
        "updated_at": now,
    }
    result = col.insert_one(doc)
    created = col.find_one({"_id": result.inserted_id})
    return _serialize(created)

# PUBLIC_INTERFACE
def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    """Get a device by id."""
    col = _devices_col()
    oid = to_object_id(device_id)
    doc = col.find_one({"_id": oid})
    return _serialize(doc) if doc else None

# PUBLIC_INTERFACE
def update_device(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a device by id; partial updates allowed."""
    if not payload:
        raise ValueError("Empty payload")

    ok, errs = validate_device_payload(payload, partial=True)
    if not ok:
        raise ValueError("; ".join([f"{k}: {v}" for k, v in errs.items()]))

    col = _devices_col()
    oid = to_object_id(device_id)

    # Build $set with only provided allowed fields
    up_fields = {}
    for k in ("name", "ip_address", "type", "location", "status", "last_checked"):
        if k in payload:
            v = payload[k]
            if isinstance(v, str):
                v = v.strip()
            up_fields[k] = v
    if not up_fields:
        raise ValueError("No updatable fields provided")
    up_fields["updated_at"] = now_utc()

    updated = col.find_one_and_update(
        {"_id": oid},
        {"$set": up_fields},
        return_document=ReturnDocument.AFTER
    )
    return _serialize(updated) if updated else None

# PUBLIC_INTERFACE
def delete_device(device_id: str) -> bool:
    """Delete a device by id. Returns True if deleted, False if not found."""
    col = _devices_col()
    oid = to_object_id(device_id)
    res = col.delete_one({"_id": oid})
    return res.deleted_count > 0

# PUBLIC_INTERFACE
def ping_device(device_id: str) -> Optional[Dict[str, Any]]:
    """Ping a device and update its status and last_checked."""
    col = _devices_col()
    oid = to_object_id(device_id)
    doc = col.find_one({"_id": oid})
    if not doc:
        return None
    ip = doc.get("ip_address")
    status = try_ping(ip)
    updated = col.find_one_and_update(
        {"_id": oid},
        {"$set": {"status": status, "last_checked": now_utc(), "updated_at": now_utc()}},
        return_document=ReturnDocument.AFTER
    )
    return _serialize(updated) if updated else None
