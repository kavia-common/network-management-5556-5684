from datetime import datetime
from typing import Dict, Any, List

from marshmallow import Schema, fields, validate, ValidationError, pre_dump


def _ipv4_validator(value: str) -> None:
    """Validate IPv4 without external deps."""
    parts = value.split(".")
    if len(parts) != 4:
        raise ValidationError("Invalid IPv4 address format")
    for p in parts:
        if not p.isdigit():
            raise ValidationError("Invalid IPv4 address format")
        n = int(p)
        if n < 0 or n > 255:
            raise ValidationError("Invalid IPv4 address octet out of range")


class BaseDeviceSchema(Schema):
    """Base device schema with common fields and validation."""
    name = fields.String(required=True, validate=validate.Length(min=1), description="Device name")
    ip_address = fields.String(required=True, validate=_ipv4_validator, data_key="ip_address",
                               description="Device IPv4 address")
    type = fields.String(required=True, validate=validate.OneOf(["router", "switch", "server"]),
                         description="Device type")
    location = fields.String(required=True, validate=validate.Length(min=1), description="Device location")
    status = fields.String(required=True, validate=validate.OneOf(["online", "offline", "unknown"]),
                           description="Device status")


class DeviceCreateSchema(BaseDeviceSchema):
    """Schema for creating a device."""
    pass


class DeviceUpdateSchema(Schema):
    """Schema for updating a device (all fields optional)."""
    name = fields.String(validate=validate.Length(min=1), description="Device name")
    ip_address = fields.String(validate=_ipv4_validator, data_key="ip_address",
                               description="Device IPv4 address")
    type = fields.String(validate=validate.OneOf(["router", "switch", "server"]), description="Device type")
    location = fields.String(validate=validate.Length(min=1), description="Device location")
    status = fields.String(validate=validate.OneOf(["online", "offline", "unknown"]), description="Device status")


class DeviceOutSchema(Schema):
    """Schema for serializing device records from MongoDB."""
    id = fields.String(required=True, description="Device ID (MongoDB ObjectId as string)")
    name = fields.String(required=True, description="Device name")
    ip_address = fields.String(required=True, description="Device IPv4 address")
    type = fields.String(required=True, description="Device type")
    location = fields.String(required=True, description="Device location")
    status = fields.String(required=True, description="Device status")
    last_checked = fields.DateTime(allow_none=True, description="Last status check timestamp (ISO8601)")
    created_at = fields.DateTime(required=True, description="Creation timestamp (ISO8601)")
    updated_at = fields.DateTime(required=True, description="Last update timestamp (ISO8601)")

    @pre_dump
    def map_mongo_fields(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Map Mongo _id -> id and ensure timestamps are datetime."""
        # Convert Mongo document to output dict
        out = dict(data)
        # map _id to id
        _id = out.pop("_id", None)
        if _id is not None:
            out["id"] = str(_id)
        # Ensure datetime objects are present
        for k in ("created_at", "updated_at", "last_checked"):
            if k in out and out[k] is not None and not isinstance(out[k], datetime):
                # Attempt parse if string, else set None
                try:
                    out[k] = datetime.fromisoformat(str(out[k]))
                except Exception:
                    out[k] = None
        return out


class DeviceListOutSchema(Schema):
    """Schema for list output with optional pagination envelope."""
    items = fields.List(fields.Nested(DeviceOutSchema), description="List of devices")
    total = fields.Integer(description="Total items available")
    page = fields.Integer(description="Current page number (1-based)")
    limit = fields.Integer(description="Page size limit")


class ErrorFieldSchema(Schema):
    field = fields.String(required=True, description="Field name related to the error")
    message = fields.String(required=True, description="Human readable error message")


class DuplicateErrorSchema(Schema):
    error = fields.Nested(ErrorFieldSchema, required=True, description="Field-level error details")


# PUBLIC_INTERFACE
def serialize_device(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a MongoDB device document to API format using DeviceOutSchema."""
    return DeviceOutSchema().dump(doc)


# PUBLIC_INTERFACE
def serialize_devices(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize a list of MongoDB device documents to API format."""
    return DeviceOutSchema(many=True).dump(docs)
