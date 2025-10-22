from typing import Dict, Any, Tuple, List, Optional

from ..db import get_repository, DuplicateIPError
from ..validators import validate_device_payload
from ..utils import now_utc, try_ping

# PUBLIC_INTERFACE
def list_devices(filters: Dict[str, Optional[str]], page: int = 1, page_size: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """List devices with optional filters and simple pagination."""
    repo = get_repository()
    page = max(1, int(page or 1))
    page_size = min(100, max(1, int(page_size or 20)))
    sorting = ("created_at", -1)
    return repo.list_devices(filters, (page, page_size), sorting)

# PUBLIC_INTERFACE
def create_device(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new device after validation."""
    ok, errs = validate_device_payload(payload, partial=False)
    if not ok:
        raise ValueError("; ".join([f"{k}: {v}" for k, v in errs.items()]))

    repo = get_repository()
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
    try:
        return repo.create_device(doc)
    except DuplicateIPError as exc:
        # Re-raise for resource layer to map to 409
        raise exc

# PUBLIC_INTERFACE
def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    """Get a device by id."""
    repo = get_repository()
    return repo.get_device_by_id(device_id)

# PUBLIC_INTERFACE
def update_device(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a device by id; partial updates allowed."""
    if not payload:
        raise ValueError("Empty payload")

    ok, errs = validate_device_payload(payload, partial=True)
    if not ok:
        raise ValueError("; ".join([f"{k}: {v}" for k, v in errs.items()]))

    repo = get_repository()
    up_fields: Dict[str, Any] = {}
    for k in ("name", "ip_address", "type", "location", "status", "last_checked"):
        if k in payload:
            v = payload[k]
            if isinstance(v, str):
                v = v.strip()
            up_fields[k] = v
    if not up_fields:
        raise ValueError("No updatable fields provided")
    up_fields["updated_at"] = now_utc()

    try:
        return repo.update_device(device_id, up_fields)
    except DuplicateIPError as exc:
        raise exc

# PUBLIC_INTERFACE
def delete_device(device_id: str) -> bool:
    """Delete a device by id. Returns True if deleted, False if not found."""
    repo = get_repository()
    return repo.delete_device(device_id)

# PUBLIC_INTERFACE
def ping_device(device_id: str) -> Optional[Dict[str, Any]]:
    """Ping a device and update its status and last_checked."""
    repo = get_repository()
    doc = repo.get_device_by_id(device_id)
    if not doc:
        return None
    ip = doc.get("ip_address")
    status = try_ping(ip)
    updated = repo.update_device(device_id, {"status": status, "last_checked": now_utc(), "updated_at": now_utc()})
    return updated
