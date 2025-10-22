from ipaddress import ip_address
from typing import Dict, Tuple, Any

ALLOWED_TYPES = {"router", "switch", "server"}
ALLOWED_STATUS = {"online", "offline", "unknown"}

REQUIRED_FIELDS = ["name", "ip_address", "type", "location", "status"]


# PUBLIC_INTERFACE
def validate_device_payload(payload: Dict[str, Any], partial: bool = False) -> Tuple[bool, Dict[str, str]]:
    """Validate incoming device payload.

    Args:
        payload: The JSON dictionary to validate.
        partial: If True, only validate fields that are present (for updates).

    Returns:
        (is_valid, errors): boolean and dict of field->error message.
    """
    errors: Dict[str, str] = {}

    # Required fields check (only when not partial)
    if not partial:
        for f in REQUIRED_FIELDS:
            if f not in payload:
                errors[f] = "This field is required."

    # name
    if "name" in payload and (not isinstance(payload["name"], str) or not payload["name"].strip()):
        errors["name"] = "Name must be a non-empty string."

    # ip_address
    if "ip_address" in payload:
        if not isinstance(payload["ip_address"], str):
            errors["ip_address"] = "IP address must be a string."
        else:
            try:
                # validate IPv4 only
                ip = ip_address(payload["ip_address"])
                if ip.version != 4:
                    errors["ip_address"] = "Only IPv4 addresses are allowed."
            except ValueError:
                errors["ip_address"] = "Invalid IPv4 address."

    # type
    if "type" in payload:
        if payload["type"] not in ALLOWED_TYPES:
            errors["type"] = f"Type must be one of {sorted(ALLOWED_TYPES)}."

    # location
    if "location" in payload and (not isinstance(payload["location"], str) or not payload["location"].strip()):
        errors["location"] = "Location must be a non-empty string."

    # status
    if "status" in payload:
        if payload["status"] not in ALLOWED_STATUS:
            errors["status"] = f"Status must be one of {sorted(ALLOWED_STATUS)}."

    return (len(errors) == 0), errors
