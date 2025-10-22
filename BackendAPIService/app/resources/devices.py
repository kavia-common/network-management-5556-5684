from datetime import datetime
from bson import ObjectId
from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request

from pymongo.errors import DuplicateKeyError, PyMongoError

from ..db import get_mongo_client, get_database, init_indexes, with_timestamps
from ..models.validators import validate_device_payload
from ..utils.ping import check_reachability

blp = Blueprint(
    "Devices",
    "devices",
    url_prefix="/devices",
    description="CRUD operations for network devices and optional reachability checks"
)


def serialize_device(doc: dict) -> dict:
    """Convert MongoDB document to JSON-safe dict."""
    if not doc:
        return doc
    doc = dict(doc)
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def json_response(data=None, message=None, error=None, status_code: int = 200):
    resp = {"data": data, "message": message, "error": error}
    return resp, status_code


def get_col():
    """Get devices collection and ensure indexes (idempotent)."""
    client = get_mongo_client()
    db = get_database(client)
    ok, err = init_indexes(db)
    # Don't fail the request if indexes can't be ensured; continue but note error in message if needed
    return db.devices


@blp.route("/")
class DevicesList(MethodView):
    def get(self):
        """List all devices."""
        col = get_col()
        docs = [serialize_device(d) for d in col.find({}).sort("created_at", 1)]
        return json_response(data=docs, message="Devices fetched")

    def post(self):
        """Create a new device."""
        payload = request.get_json(silent=True) or {}
        valid, errors = validate_device_payload(payload, partial=False)
        if not valid:
            return json_response(data=None, message="Validation failed", error=errors, status_code=400)

        # timestamps
        with_timestamps(payload, is_create=True)

        col = get_col()
        try:
            res = col.insert_one(payload)
            created = serialize_device(col.find_one({"_id": res.inserted_id}))
            return json_response(data=created, message="Device created"), 201
        except DuplicateKeyError:
            return json_response(
                data=None,
                message="Duplicate key error",
                error={"ip_address": "A device with this IP address already exists."},
                status_code=409,
            )
        except PyMongoError as ex:
            return json_response(data=None, message="Database error", error={"detail": str(ex)}, status_code=500)


@blp.route("/<string:device_id>")
class DeviceItem(MethodView):
    def get(self, device_id: str):
        """Get a device by id."""
        col = get_col()
        try:
            oid = ObjectId(device_id)
        except Exception:
            return json_response(data=None, message="Invalid id", error={"_id": "Invalid ObjectId"}, status_code=400)

        doc = col.find_one({"_id": oid})
        if not doc:
            return json_response(data=None, message="Not found", error={"_id": "Device not found"}, status_code=404)
        return json_response(data=serialize_device(doc), message="Device fetched")

    def put(self, device_id: str):
        """Update a device by id."""
        payload = request.get_json(silent=True) or {}
        valid, errors = validate_device_payload(payload, partial=True)
        if not valid:
            return json_response(data=None, message="Validation failed", error=errors, status_code=400)

        try:
            oid = ObjectId(device_id)
        except Exception:
            return json_response(data=None, message="Invalid id", error={"_id": "Invalid ObjectId"}, status_code=400)

        with_timestamps(payload, is_create=False)

        col = get_col()
        try:
            res = col.find_one_and_update({"_id": oid}, {"$set": payload}, return_document=True)
            # Some older pymongo versions need ReturnDocument, but here we can refetch:
            if not res:
                # refetch to check existence
                doc = col.find_one({"_id": oid})
                if not doc:
                    return json_response(data=None, message="Not found", error={"_id": "Device not found"}, status_code=404)
                # fallback fetch fresh
                res = col.find_one({"_id": oid})
            updated = serialize_device(res)
            return json_response(data=updated, message="Device updated")
        except DuplicateKeyError:
            return json_response(
                data=None,
                message="Duplicate key error",
                error={"ip_address": "A device with this IP address already exists."},
                status_code=409,
            )
        except PyMongoError as ex:
            return json_response(data=None, message="Database error", error={"detail": str(ex)}, status_code=500)

    def delete(self, device_id: str):
        """Delete a device by id."""
        try:
            oid = ObjectId(device_id)
        except Exception:
            return json_response(data=None, message="Invalid id", error={"_id": "Invalid ObjectId"}, status_code=400)
        col = get_col()
        res = col.delete_one({"_id": oid})
        if res.deleted_count == 0:
            return json_response(data=None, message="Not found", error={"_id": "Device not found"}, status_code=404)
        return json_response(data={"deleted": True}, message="Device deleted")


@blp.route("/<string:device_id>/ping")
class DevicePing(MethodView):
    def post(self, device_id: str):
        """Ping a device by id; updates last_checked and optionally status."""
        try:
            oid = ObjectId(device_id)
        except Exception:
            return json_response(data=None, message="Invalid id", error={"_id": "Invalid ObjectId"}, status_code=400)

        col = get_col()
        doc = col.find_one({"_id": oid})
        if not doc:
            return json_response(data=None, message="Not found", error={"_id": "Device not found"}, status_code=404)

        ip = doc.get("ip_address")
        reachable, method = check_reachability(ip, timeout_seconds=2)
        new_status = "online" if reachable else "offline"
        now = datetime.utcnow().isoformat() + "Z"
        try:
            col.update_one(
                {"_id": oid},
                {"$set": {"last_checked": now, "status": new_status, "updated_at": now}},
            )
            updated = serialize_device(col.find_one({"_id": oid}))
            return json_response(
                data={"device": updated, "reachable": reachable, "method": method},
                message="Ping completed",
            )
        except PyMongoError as ex:
            return json_response(data=None, message="Database error", error={"detail": str(ex)}, status_code=500)
