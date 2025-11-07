import json
import logging
import socket
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, List

from bson import ObjectId
from flask import request, Response
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from pymongo.errors import DuplicateKeyError

# Import db as a module namespace so tests can monkeypatch get_collection/DEVICES_COLLECTION
from app import db as db_module
from app.schemas import (
    DeviceCreateSchema,
    DeviceUpdateSchema,
    DeviceOutSchema,
    DeviceListOutSchema,
    serialize_devices,
)
# Import serialize_device to ensure single-object handlers return JSON-serializable dicts
from app.schemas import serialize_device

logger = logging.getLogger(__name__)

blp = Blueprint(
    "Devices",
    "devices",
    url_prefix="/devices",
    description="CRUD and ping endpoints for devices",
)


def _objid(id_str: str):
    """
    Parse an ID string:
    - If it's a valid ObjectId hex string, return an ObjectId
    - Otherwise, return the original string (supporting fake/in-memory collections in tests)
    """
    try:
        if ObjectId.is_valid(id_str):
            return ObjectId(id_str)
        return id_str
    except Exception:
        abort(404, message="Device not found")


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
    # Try resolving; if fails, consider offline
    try:
        # If it's a raw IPv4, gethostbyaddr may fail; ignore reverse lookup
        socket.gethostbyname(ip)
    except Exception:
        return "offline", last

    # Try TCP connect with short timeout
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
    # No connection succeeded: unknown if host is firewalled; mark offline
    return "offline", last


@blp.route("", methods=["GET", "POST", "OPTIONS"])
class DevicesList(MethodView):
    def options(self):
        # Preflight response for CORS
        return Response(status=204)

    @blp.response(200, DeviceListOutSchema, description="List devices with pagination envelope")
    def get(self):
        """
        List devices with unified envelope.
        Always returns:
          { "items": [...], "total": <int>, "page": <int>, "limit": <int> }
        Query params:
          - page (optional, default 1; 1-based)
          - limit (optional, default 10; 1..1000)
        Diagnostics:
          Logs computed page/limit, total count, item count, and content type.
        """
        try:
            # Obtain collection through db module indirection to allow tests to monkeypatch db.get_collection
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)

            # Resolve pagination with safe defaults
            page_param = request.args.get("page")
            limit_param = request.args.get("limit")
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
            raw_items: List[Dict[str, Any]] = list(cursor)
            items = serialize_devices(raw_items)  # ensures ObjectId->str and datetime ISO via schema

            payload = {
                "items": items,
                "total": total,
                "page": page,
                "limit": limit,
            }

            # Structured diagnostics
            logger.info(
                "GET /devices diagnostics | page=%s limit=%s total=%s item_count=%s content_type=%s",
                page,
                limit,
                total,
                len(items),
                "application/json; charset=utf-8",
            )

            # Explicit response with content-type
            return Response(
                response=json.dumps(payload),
                status=200,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
        except Exception as e:
            # Serialize DB/other errors to JSON to prevent fetch parse failures
            logger.error("GET /devices failed: %s", str(e))
            err_payload = {"status": "error", "message": str(e)}
            return Response(
                response=json.dumps(err_payload),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )

    @blp.arguments(DeviceCreateSchema, location="json")
    @blp.response(201, DeviceOutSchema, description="Create a new device")
    def post(self, json_data):
        """
        Create a device.
        Enforces unique ip_address; returns 400 with { field, message } if duplicate.
        """
        try:
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)
            doc = dict(json_data)
            doc.update(_timestamps_for_create())
            try:
                res = coll.insert_one(doc)
            except DuplicateKeyError:
                # Map unique constraint violations to HTTP 409 Conflict
                return Response(
                    response=json.dumps({"error": {"field": "ip_address", "message": "already exists"}}),
                    status=409,
                    mimetype="application/json",
                    content_type="application/json; charset=utf-8",
                )
            created = coll.find_one({"_id": res.inserted_id})
            # Serialize via schema for consistency, then return explicit JSON Response
            payload = serialize_device(created)
            return Response(
                response=json.dumps(payload),
                status=201,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
        except Exception as e:
            logger.error("POST /devices failed: %s", str(e))
            err_payload = {"status": "error", "message": str(e)}
            return Response(
                response=json.dumps(err_payload),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )


@blp.route("/raw")
class DevicesListRaw(MethodView):
    @blp.response(200, description="Raw array of devices for debugging (no envelope)")
    def get(self):
        """
        Debugging endpoint returning a raw array.
        This endpoint returns the plain list of devices (serialized) without envelope.
        """
        try:
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)
            docs = list(coll.find({}).sort("created_at", -1))
            items = serialize_devices(docs)
            logger.info(
                "GET /devices/raw diagnostics | item_count=%s content_type=%s",
                len(items),
                "application/json; charset=utf-8",
            )
            return Response(
                response=json.dumps(items),
                status=200,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
        except Exception as e:
            logger.error("GET /devices/raw failed: %s", str(e))
            return Response(
                response=json.dumps({"status": "error", "message": str(e)}),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )


@blp.route("/<string:id>")
class DeviceItem(MethodView):
    @blp.response(200, DeviceOutSchema, description="Get a device by id")
    def get(self, id: str):
        try:
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)
            key = _objid(id)
            doc = coll.find_one({"_id": key})
            if not doc:
                abort(404, message="Device not found")
            payload = serialize_device(doc)
            return Response(
                response=json.dumps(payload),
                status=200,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
        except Exception as e:
            logger.error("GET /devices/%s failed: %s", id, str(e))
            return Response(
                response=json.dumps({"status": "error", "message": str(e)}),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )

    @blp.arguments(DeviceUpdateSchema, location="json")
    @blp.response(200, DeviceOutSchema, description="Update a device by id")
    def put(self, json_data, id: str):
        try:
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)
            update_fields = dict(json_data)
            if not update_fields:
                abort(400, message="No fields provided for update")
            update_fields.update(_timestamp_for_update())
            try:
                res = coll.find_one_and_update(
                    {"_id": _objid(id)},
                    {"$set": update_fields},
                    return_document=True,  # type: ignore[arg-type]
                )
            except DuplicateKeyError:
                return Response(
                    response=json.dumps({"error": {"field": "ip_address", "message": "already exists"}}),
                    status=409,
                    mimetype="application/json",
                    content_type="application/json; charset=utf-8",
                )
            if not res:
                abort(404, message="Device not found")
            payload = serialize_device(res)
            return Response(
                response=json.dumps(payload),
                status=200,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
        except Exception as e:
            logger.error("PUT /devices/%s failed: %s", id, str(e))
            return Response(
                response=json.dumps({"status": "error", "message": str(e)}),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )

    @blp.response(204, description="Delete a device by id")
    def delete(self, id: str):
        try:
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)
            res = coll.delete_one({"_id": _objid(id)})
            if res.deleted_count == 0:
                abort(404, message="Device not found")
            return ""  # 204 No Content
        except Exception as e:
            logger.error("DELETE /devices/%s failed: %s", id, str(e))
            return Response(
                response=json.dumps({"status": "error", "message": str(e)}),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )


@blp.route("/<string:id>/ping", methods=["POST", "OPTIONS"])
class DevicePing(MethodView):
    def options(self, id: str):
        return Response(status=204)

    @blp.response(200, DeviceOutSchema, description="Ping a device and update its status")
    def post(self, id: str):
        """
        Ping endpoint performs a safe check and updates:
        - status ('online' or 'offline')
        - last_checked (UTC timestamp)
        """
        try:
            coll = db_module.get_collection(db_module.DEVICES_COLLECTION)
            key = _objid(id)
            doc = coll.find_one({"_id": key})
            if not doc:
                abort(404, message="Device not found")

            ip = doc.get("ip_address")
            status, last = _safe_ping(ip)
            updated = coll.find_one_and_update(
                {"_id": doc["_id"]},
                {"$set": {"status": status, "last_checked": last, "updated_at": datetime.utcnow()}},
                return_document=True,  # type: ignore[arg-type]
            )
            if not updated:
                abort(404, message="Device not found")
            payload = serialize_device(updated)
            return Response(
                response=json.dumps(payload),
                status=200,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
        except Exception as e:
            logger.error("POST /devices/%s/ping failed: %s", id, str(e))
            return Response(
                response=json.dumps({"status": "error", "message": str(e)}),
                status=500,
                mimetype="application/json",
                content_type="application/json; charset=utf-8",
            )
