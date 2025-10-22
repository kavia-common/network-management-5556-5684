import ipaddress
from typing import Dict, Any, Tuple

ALLOWED_TYPES = {"router", "switch", "server"}
ALLOWED_STATUS = {"online", "offline", "unknown"}

REQUIRED_FIELDS = ["name", "ip_address", "type", "location", "status"]

# PUBLIC_INTERFACE
def validate_device_payload(data: Dict[str, Any], partial: bool = False) -> Tuple[bool, Dict[str, str]]:
    """
    Validate incoming device payload.
    - Ensures required fields (unless partial update)
    - Validates enums and IPv4 format
    - Rejects additional properties beyond allowed known fields
    Returns (is_valid, errors_dict)
    """
    errors: Dict[str, str] = {}
    allowed_fields = set(REQUIRED_FIELDS + ["last_checked", "created_at", "updated_at"])
    extra = set(data.keys()) - allowed_fields
    if extra:
        errors["additional_properties"] = f"Unknown fields: {', '.join(sorted(extra))}"

    if not partial:
        for f in REQUIRED_FIELDS:
            if f not in data:
                errors[f] = "Missing required field"

    # Field-specific validations when present
    if "name" in data and (not isinstance(data["name"], str) or not data["name"].strip()):
        errors["name"] = "Name must be a non-empty string"

    if "ip_address" in data:
        ip = data["ip_address"]
        try:
            ipaddress.ip_address(ip)
            if ":" in ip:
                errors["ip_address"] = "IPv6 not supported; provide IPv4"
        except ValueError:
            errors["ip_address"] = "Invalid IP address format"

    if "type" in data and data["type"] not in ALLOWED_TYPES:
        errors["type"] = f"Invalid type. Allowed: {', '.join(sorted(ALLOWED_TYPES))}"

    if "status" in data and data["status"] not in ALLOWED_STATUS:
        errors["status"] = f"Invalid status. Allowed: {', '.join(sorted(ALLOWED_STATUS))}"

    if "location" in data and (not isinstance(data["location"], str) or not data["location"].strip()):
        errors["location"] = "Location must be a non-empty string"

    return (len(errors) == 0), errors
