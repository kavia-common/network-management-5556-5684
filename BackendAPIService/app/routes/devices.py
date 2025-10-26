import socket
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from pymongo.errors import DuplicateKeyError

from app.db import get_collection, DEVICES_COLLECTION
from app.schemas import (
    DeviceCreateSchema,
    DeviceUpdateSchema,
    DeviceOutSchema,
    DeviceListOutSchema,
)

blp = Blueprint(
    "Devices",
    "devices",
    url_prefix="/devices",
    description="CRUD and ping endpoints for devices",
)


def _timestamps_for_create() -> Dict[str, Any]:
    now = datetime.utcnow()
    return {"created_at": now, "updated_at": now, "last_checked": None}


def _timestamp_for_update() -> Dict[str, Any]:
    return {"updated_at": datetime.utcnow()}


def _safe_ping(ip: str) -> Tuple[str, Optional[datetime]]:
    """
    Safe, non-privileged reachability check:
    - Try DNS resolve (handles hostnames mistakenly sent as IP)
    - Try short TCP connect to common ports (80, 443) with short timeout
    Returns: (status, last_checked)
    """
    last = datetime.utcnow()
    try:
        socket.gethostbyname(ip)
    except Exception:
        return "offline", last

    for port in (80, 443):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            if s.connect_ex((ip, port)) == 0:
                s.close()
                return "online", last
        except Exception:
            pass
        finally:
            try:
                s.close()
            except Exception:
                pass
    return "offline", last


@blp.route("")
class DevicesList(MethodView):
    @blp.response(200, DeviceListOutSchema, description="List devices (paginated if page/limit provided)")
    def get(self):
        """
        List devices.
        - If 'page' and 'limit' query params are provided, returns envelope:
          { items: [...], total, page, limit }
        - Otherwise returns full array for convenience (legacy behavior).
        """
        coll = get_collection(DEVICES_COLLECTION)
        page_param = request.args.get("page")
        limit_param = request.args.get("limit")
        if page_param is not None or limit_param is not None:
            try:
                page = int(page_param) if page_param is not None else 1
                limit = int(limit_param) if limit_param is not None else 10
                if page < 1 or limit < 1 or limit > 1000:
                    raise ValueError
            except ValueError:
                abort(400, message="Invalid pagination parameters")

            total = coll.count_documents({})
            cursor = (
                coll.find({})
                .sort("created_at", -1)
                .skip((page - 1) * limit)
                .limit(limit)
            )
            items = list(cursor)
            return {
                "items": DeviceOutSchema(many=True).dump(items),
                "total": total,
                "page": page,
                "limit": limit,
            }
        else:
            items = list(coll.find({}).sort("created_at", -1))
            return DeviceOutSchema(many=True).dump(items)

    @blp.arguments(DeviceCreateSchema, location="json")
    @blp.response(201, DeviceOutSchema, description="Create a new device")
    def post(self, json_data):
        """
        Create a device.
        Enforces unique name and ip_address; returns 409 on duplicate name and 400 on duplicate ip_address.
        """
        coll = get_collection(DEVICES_COLLECTION)
        doc = dict(json_data)

        # Validate name non-empty (schema already ensures min length 1)
        name = (doc.get("name") or "").strip()
        if not name:
            abort(422, message="Invalid name")

        # Enforce uniqueness of name at application level for clear 409 response
        existing = coll.find_one({"name": name})
        if existing:
            abort(409, message="Device name already exists")

        # Set timestamps
        doc.update(_timestamps_for_create())

        try:
            # Rely on DB unique index for ip_address and name (if present)
            coll.insert_one(doc)
        except DuplicateKeyError as e:
            # Determine which field conflicted, if possible
            # This is conservative: ip_address was enforced previously with 400;
            # keep the same behavior for backward compatibility.
            if "ip" in str(e).lower():
                abort(400, error={"field": "ip_address", "message": "already exists"})
            # Name duplicate via race-condition fallback
            abort(409, message="Device name already exists")

        created = coll.find_one({"name": name})
        return created


@blp.route("/<string:id>")
class DeviceItem(MethodView):
    @blp.response(200, DeviceOutSchema, description="Get a device by id")
    def get(self, id: str):
        """
        Retrieve device by name-based id. For backward compatibility,
        if not found by name, attempt legacy lookup by _id string match.
        """
        coll = get_collection(DEVICES_COLLECTION)
        doc = coll.find_one({"name": id})
        if not doc:
            # Legacy support: some clients may pass ObjectId strings; try matching _id as string.
            # Note: no-op unless _id was stored as a string in rare cases.
            doc = coll.find_one(
                {"_id": {"$in": [id]}}
            )
        if not doc:
            abort(404, message="Device not found")
        return doc

    @blp.arguments(DeviceUpdateSchema, location="json")
    @blp.response(200, DeviceOutSchema, description="Update a device by id")
    def put(self, json_data, id: str):
        """
        Update a device by name-based id.
        - Name changes are disallowed. Any 'name' in payload will be ignored.
        - Enforces ip_address uniqueness via DB index (returns 400 on duplicate ip).
        """
        coll = get_collection(DEVICES_COLLECTION)
        update_fields = dict(json_data or {})
        # Ensure name cannot be updated
        if "name" in update_fields:
            update_fields.pop("name", None)

        if not update_fields:
            abort(400, message="No fields provided for update")

        update_fields.update(_timestamp_for_update())
        try:
            res = coll.find_one_and_update(
                {"name": id},
                {"$set": update_fields},
                return_document=True,  # type: ignore[arg-type]
            )
        except DuplicateKeyError:
            abort(400, error={"field": "ip_address", "message": "already exists"})
        if not res:
            abort(404, message="Device not found")
        return res

    @blp.response(204, description="Delete a device by id")
    def delete(self, id: str):
        """Delete a device by its name-based id."""
        coll = get_collection(DEVICES_COLLECTION)
        res = coll.delete_one({"name": id})
        if res.deleted_count == 0:
            abort(404, message="Device not found")
        return ""  # 204 No Content


@blp.route("/<string:id>/ping")
class DevicePing(MethodView):
    @blp.response(200, DeviceOutSchema, description="Ping a device and update its status")
    def post(self, id: str):
        """
        Ping endpoint performs a safe check and updates:
        - status ('online' or 'offline')
        - last_checked (UTC timestamp)
        """
        coll = get_collection(DEVICES_COLLECTION)
        doc = coll.find_one({"name": id})
        if not doc:
            abort(404, message="Device not found")

        ip = doc.get("ip_address")
        status, last = _safe_ping(ip)
        updated = coll.find_one_and_update(
            {"name": id},
            {"$set": {"status": status, "last_checked": last, "updated_at": datetime.utcnow()}},
            return_document=True,  # type: ignore[arg-type]
        )
        return updated
