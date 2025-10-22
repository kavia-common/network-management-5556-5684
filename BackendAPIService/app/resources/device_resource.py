from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request, jsonify, current_app

from ..services.device_service import (
    list_devices, create_device, get_device, update_device, delete_device, ping_device
)
from ..db import DuplicateIPError

blp = Blueprint(
    "Devices",
    "devices",
    url_prefix="/api/devices",
    description="CRUD and status operations for network devices",
)

@blp.route("")
class DevicesCollection(MethodView):
    def get(self):
        """
        List devices with optional filters and pagination.
        Query params:
        - page (int, default 1)
        - page_size (int, default 20)
        - type (router|switch|server)
        - status (online|offline|unknown)
        - q (search across name and ip_address)
        """
        try:
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 20))
        except ValueError:
            return jsonify({"error": {"code": 400, "status": "Bad Request", "message": "Invalid pagination params"}}), 400

        filters = {
            "type": request.args.get("type"),
            "status": request.args.get("status"),
            "q": request.args.get("q"),
        }
        try:
            data, meta = list_devices(filters, page=page, page_size=page_size)
            return jsonify({"data": data, "meta": meta}), 200
        except Exception as exc:
            current_app.logger.error("List devices error: %s", exc)
            return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "Server error"}}), 500

    def post(self):
        """
        Create a new device.
        Body: {name, ip_address, type, location, status}
        """
        payload = request.get_json(force=True, silent=True) or {}
        try:
            device = create_device(payload)
            return jsonify({"data": device}), 201
        except ValueError as ve:
            return jsonify({"error": {"code": 422, "status": "Unprocessable Entity", "message": str(ve)}}), 422
        except DuplicateIPError:
            return jsonify({"error": {"code": 409, "status": "Conflict", "message": "Device with this IP already exists"}}), 409
        except Exception as exc:
            current_app.logger.error("Create device error: %s", exc)
            return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "Server error"}}), 500


@blp.route("/<string:device_id>")
class DeviceItem(MethodView):
    def get(self, device_id: str):
        """Get a single device by ID."""
        try:
            device = get_device(device_id)
            if not device:
                return jsonify({"error": {"code": 404, "status": "Not Found", "message": "Device not found"}}), 404
            return jsonify({"data": device}), 200
        except ValueError:
            return jsonify({"error": {"code": 400, "status": "Bad Request", "message": "Invalid ID"}}), 400
        except Exception as exc:
            current_app.logger.error("Get device error: %s", exc)
            return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "Server error"}}), 500

    def put(self, device_id: str):
        """Update a device by ID."""
        payload = request.get_json(force=True, silent=True) or {}
        try:
            updated = update_device(device_id, payload)
            if not updated:
                return jsonify({"error": {"code": 404, "status": "Not Found", "message": "Device not found"}}), 404
            return jsonify({"data": updated}), 200
        except ValueError as ve:
            return jsonify({"error": {"code": 422, "status": "Unprocessable Entity", "message": str(ve)}}), 422
        except DuplicateIPError:
            return jsonify({"error": {"code": 409, "status": "Conflict", "message": "Device with this IP already exists"}}), 409
        except Exception as exc:
            current_app.logger.error("Update device error: %s", exc)
            return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "Server error"}}), 500

    def delete(self, device_id: str):
        """Delete a device by ID."""
        try:
            deleted = delete_device(device_id)
            if not deleted:
                return jsonify({"error": {"code": 404, "status": "Not Found", "message": "Device not found"}}), 404
            return jsonify({"message": "Deleted"}), 200
        except ValueError:
            return jsonify({"error": {"code": 400, "status": "Bad Request", "message": "Invalid ID"}}), 400
        except Exception as exc:
            current_app.logger.error("Delete device error: %s", exc)
            return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "Server error"}}), 500


@blp.route("/<string:device_id>/ping")
class DevicePing(MethodView):
    def post(self, device_id: str):
        """
        Ping a device and update its status and last_checked.
        Returns updated device data with new status.
        """
        try:
            updated = ping_device(device_id)
            if not updated:
                return jsonify({"error": {"code": 404, "status": "Not Found", "message": "Device not found"}}), 404
            return jsonify({"data": updated}), 200
        except ValueError:
            return jsonify({"error": {"code": 400, "status": "Bad Request", "message": "Invalid ID"}}), 400
        except Exception as exc:
            current_app.logger.error("Ping device error: %s", exc)
            return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "Server error"}}), 500
