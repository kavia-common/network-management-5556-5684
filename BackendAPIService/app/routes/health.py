from flask_smorest import Blueprint
from flask.views import MethodView
from app import db as _db  # use db.ping for health
from flask import jsonify
import logging

# Import helpers for the devices summary endpoint
from app.db import get_db, DEVICES_COLLECTION, get_network_collection

blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")


@blp.route("/")
class HealthCheck(MethodView):
    """Simple health check endpoint."""
    def get(self):
        """Return service health."""
        return {"message": "Healthy"}


@blp.route("/health/db")
class DBHealth(MethodView):
    """
    Database health endpoint.
    Pings MongoDB and returns JSON indicating status.
    """
    def get(self):
        """
        GET /health/db
        Summary: Verify database connectivity.
        Returns:
          200: {"status": "ok", "server": {"ok": 1.0}} on success with minimal server info
          500: {"status": "error", "message": "<details>"} when connectivity fails
        """
        try:
            # Use global client to get minimal server info without exposing sensitive details
            client = _db.get_client()
            # Mongo 'ping' along with basic admin info
            ping_result = client.admin.command("ping")  # {'ok': 1.0} on success
            # Only include minimal non-sensitive info
            server_info = {"ok": ping_result.get("ok", 0)}
            return jsonify({"status": "ok", "server": server_info}), 200
        except Exception as e:
            # Fallback to standard ping error details from helper for actionable message
            ok, err = _db.ping()
            # Optional logging without leaking secrets
            logging.getLogger(__name__).error("DB healthcheck failed: %s", err or str(e))
            return jsonify({"status": "error", "message": err or "Database ping failed"}), 500


@blp.route("/health/devices-summary")
class DevicesSummary(MethodView):
    """
    Diagnostic endpoint to confirm active DB/collection and document visibility.
    Returns minimal, non-sensitive details to help diagnose data visibility issues.
    """
    def get(self):
        """
        GET /health/devices-summary
        Summary: Show current DB name, devices collection name, a document count, and up to 3 sample IDs.
        Returns:
          200: {
            "dbName": "<active db name>",
            "collection": "<resolved devices collection>",
            "count": <int>,
            "sampleIds": ["<id1>", "<id2>", "<id3>"]
          }
          500: {"error": "<message>"} on failure
        Notes:
          - Uses get_db() and get_collection(DEVICES_COLLECTION).
          - Does not expose credentials or full documents.
        """
        try:
            db = get_db()
            coll = get_network_collection()
            count = coll.count_documents({})
            # Fetch only _id to avoid any sensitive fields; limit to 3
            cursor = coll.find({}, {"_id": 1}).sort("_id", -1).limit(3)
            sample_ids = [str(doc["_id"]) for doc in cursor]
            return jsonify({
                "dbName": db.name,
                "collection": DEVICES_COLLECTION,
                "count": count,
                "sampleIds": sample_ids,
            }), 200
        except Exception as e:
            logging.getLogger(__name__).error("Devices summary error: %s", str(e))
            return jsonify({"error": "Failed to load devices summary", "message": str(e)}), 500
