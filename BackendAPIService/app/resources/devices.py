from datetime import datetime
from pymongo.errors import DuplicateKeyError, PyMongoError
from flask import request
from flask_smorest import Blueprint
from flask.views import MethodView

from app.db import get_db, Database
from app.models.device_schema import validate_device_payload, serialize_device, VALID_TYPES, VALID_STATUS
from app.utils.errors import error_response
from app.utils.ping import ping_host

blp = Blueprint(
    "Devices",
    "devices",
    url_prefix="/devices",
    description="Device CRUD and status operations",
)


def _db_unavailable_response(detail: str = "Database is unavailable"):
    return error_response(503, "Service Unavailable", {"database": detail})


@blp.route("")
class DeviceList(MethodView):
    """List and create devices."""

    def get(self):
        """
        List devices.
        Query params:
          - type: filter by device type
          - status: filter by status
        """
        db: Database = get_db()
        query = {}
        device_type = request.args.get("type")
        device_status = request.args.get("status")
        if device_type:
            if device_type not in VALID_TYPES:
                return error_response(400, "Invalid 'type' filter")
            query["type"] = device_type
        if device_status:
            if device_status not in VALID_STATUS:
                return error_response(400, "Invalid 'status' filter")
            query["status"] = device_status

        try:
            docs = [serialize_device(d) for d in db.devices.find(query).sort("created_at")]
            return {"items": docs, "count": len(docs)}, 200
        except Exception as e:
            return _db_unavailable_response(str(e))

    def post(self):
        """
        Create a new device.
        Body:
          - name, ip_address, type, location, status
        """
        db: Database = get_db()
        payload = request.get_json(force=True, silent=True) or {}
        cleaned, errors = validate_device_payload(payload, partial=False)
        if errors:
            return error_response(400, "Validation error", errors)

        now = datetime.utcnow()
        doc = {
            **cleaned,
            "created_at": now,
            "updated_at": now,
            "last_checked": None,
        }
        try:
            result = db.devices.insert_one(doc)
            created = db.devices.find_one({"_id": result.inserted_id})
            return serialize_device(created), 201
        except DuplicateKeyError:
            return error_response(409, "Device with this ip_address already exists", {"ip_address": "must be unique"})
        except PyMongoError as e:
            return error_response(500, "Database error", {"detail": str(e)})
        except Exception as e:
            return _db_unavailable_response(str(e))


@blp.route("/<string:device_id>")
class DeviceDetail(MethodView):
    """Retrieve, update, delete a device."""

    def get(self, device_id: str):
        """Get a device by id."""
        db: Database = get_db()
        try:
            oid = db.to_object_id(device_id)
        except ValueError:
            return error_response(400, "Invalid device id")

        try:
            doc = db.devices.find_one({"_id": oid})
            if not doc:
                return error_response(404, "Device not found")
            return serialize_device(doc), 200
        except Exception as e:
            return _db_unavailable_response(str(e))

    def put(self, device_id: str):
        """
        Update a device. Replaces provided fields; fields not provided remain unchanged.
        Body can include: name, ip_address, type, location, status
        """
        db: Database = get_db()
        try:
            oid = db.to_object_id(device_id)
        except ValueError:
            return error_response(400, "Invalid device id")

        payload = request.get_json(force=True, silent=True) or {}
        cleaned, errors = validate_device_payload(payload, partial=True)
        if errors:
            return error_response(400, "Validation error", errors)

        if not cleaned:
            return error_response(400, "No updatable fields provided")

        cleaned["updated_at"] = datetime.utcnow()

        try:
            res = db.devices.find_one_and_update(
                {"_id": oid},
                {"$set": cleaned},
                return_document=True,
            )
            if not res:
                return error_response(404, "Device not found")
            return serialize_device(res), 200
        except DuplicateKeyError:
            return error_response(409, "Device with this ip_address already exists", {"ip_address": "must be unique"})
        except PyMongoError as e:
            return error_response(500, "Database error", {"detail": str(e)})
        except Exception as e:
            return _db_unavailable_response(str(e))

    def delete(self, device_id: str):
        """Delete a device by id."""
        db: Database = get_db()
        try:
            oid = db.to_object_id(device_id)
        except ValueError:
            return error_response(400, "Invalid device id")

        try:
            res = db.devices.delete_one({"_id": oid})
            if res.deleted_count == 0:
                return error_response(404, "Device not found")
            return {"deleted": True}, 200
        except PyMongoError as e:
            return error_response(500, "Database error", {"detail": str(e)})
        except Exception as e:
            return _db_unavailable_response(str(e))


@blp.route("/<string:device_id>/ping")
class DevicePing(MethodView):
    """Ping a device and update its status and last_checked."""

    def post(self, device_id: str):
        """
        Ping a device by id.
        Updates: status (online/offline) and last_checked timestamp.
        """
        db: Database = get_db()
        try:
            oid = db.to_object_id(device_id)
        except ValueError:
            return error_response(400, "Invalid device id")

        try:
            doc = db.devices.find_one({"_id": oid})
            if not doc:
                return error_response(404, "Device not found")
        except Exception as e:
            return _db_unavailable_response(str(e))

        timeout_ms = request.args.get("timeout_ms", type=int) or request.json.get("timeout_ms") if request.is_json else None
        if timeout_ms is None:
            timeout_ms = getattr(request.app, "PING_TIMEOUT_MS", None) or request.environ.get("PING_TIMEOUT_MS")

        # Use app config default if not provided
        from flask import current_app
        timeout_ms = timeout_ms or current_app.config.get("PING_TIMEOUT_MS", 2000)

        is_online, raw = ping_host(doc["ip_address"], timeout_ms=timeout_ms)
        new_status = "online" if is_online else "offline"
        now = datetime.utcnow()
        try:
            updated = db.devices.find_one_and_update(
                {"_id": oid},
                {"$set": {"status": new_status, "last_checked": now, "updated_at": now}},
                return_document=True,
            )
            return {"result": {"online": is_online, "output": raw}, "device": serialize_device(updated)}, 200
        except PyMongoError as e:
            return error_response(500, "Database error", {"detail": str(e)})
        except Exception as e:
            return _db_unavailable_response(str(e))
