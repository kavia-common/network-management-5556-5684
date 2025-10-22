from datetime import datetime
import re
from typing import Any, Dict, Tuple

VALID_TYPES = {"router", "switch", "server"}
VALID_STATUS = {"online", "offline", "unknown"}

_ipv4_regex = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


def _now() -> datetime:
    return datetime.utcnow()


def validate_device_payload(data: Dict[str, Any], partial: bool = False) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Validate incoming device payload for create/update operations.

    Args:
        data: request json
        partial: if True, only validate provided fields (for PATCH/PUT); still enforce enums and formats.

    Returns:
        (clean_data, errors)
    """
    errors: Dict[str, str] = {}
    cleaned: Dict[str, Any] = {}

    required = ["name", "ip_address", "type", "location", "status"]
    fields = ["name", "ip_address", "type", "location", "status"]

    for field in fields:
        if field not in data:
            if not partial and field in required:
                errors[field] = "Missing required field"
            continue
        value = data[field]

        if field == "name":
            if not isinstance(value, str) or not value.strip():
                errors[field] = "Name must be a non-empty string"
            else:
                cleaned[field] = value.strip()

        elif field == "ip_address":
            if not isinstance(value, str) or not _ipv4_regex.match(value):
                errors[field] = "ip_address must be a valid IPv4 address"
            else:
                cleaned[field] = value

        elif field == "type":
            if value not in VALID_TYPES:
                errors[field] = f"type must be one of: {', '.join(sorted(VALID_TYPES))}"
            else:
                cleaned[field] = value

        elif field == "location":
            if not isinstance(value, str) or not value.strip():
                errors[field] = "location must be a non-empty string"
            else:
                cleaned[field] = value.strip()

        elif field == "status":
            if value not in VALID_STATUS:
                errors[field] = f"status must be one of: {', '.join(sorted(VALID_STATUS))}"
            else:
                cleaned[field] = value

    return cleaned, errors


def serialize_device(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-safe representation."""
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    # ensure ISO format for datetimes
    for key in ("created_at", "updated_at", "last_checked"):
        if key in out and out[key] is not None:
            if isinstance(out[key], datetime):
                out[key] = out[key].isoformat() + "Z"
    return out
