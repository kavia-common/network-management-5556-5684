from flask_smorest import Blueprint
from flask.views import MethodView
from flask import jsonify
import logging

# Import the db module as a namespace so tests can monkeypatch functions like db.get_db, db.get_collection, etc.
# Import as namespace so tests can monkeypatch members like get_client/get_collection.
import app.db as db

blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")


@blp.route("/")
class HealthCheck(MethodView):
    """Simple health check endpoint."""

    def get(self):
        """Return service health."""
        return {"message": "Healthy"}


@blp.route("/health")
class HealthStatus(MethodView):
    """
    Composite health endpoint that reports service and DB status.
    Always returns HTTP 200 with db_status field.
    """

    def get(self):
        """
        GET /health
        Returns:
          200: {
            "status": "ok",
            "db_status": "unconfigured" | "ok" | "error",
            "db_message": "<optional message when error/unconfigured>"
          }
        """
        ok, err = db.ping()
        if err is None:
            return jsonify({"status": "ok", "db_status": "ok"}), 200
        # Determine unconfigured vs error by message content
        db_status = "unconfigured" if "unconfigured" in err.lower() else "error"
        return jsonify({"status": "ok", "db_status": db_status, "db_message": err}), 200


@blp.route("/health/db")
class DBHealth(MethodView):
    """
    Database health endpoint.
    Pings MongoDB and returns JSON indicating status, never failing the overall app health.
    """

    def get(self):
        """
        GET /health/db
        Summary: Verify database connectivity.
        Returns:
          200 with:
            {"status":"ok","server":{"ok":1.0},"db_status":"ok"} on success
            {"status":"ok","db_status":"unconfigured","message":"..."} when not configured
            {"status":"ok","db_status":"error","message":"..."} when configured but failing
        """
        ok, err = db.ping()
        if ok:
            # Best-effort minimal server info
            try:
                client = db.get_client()
                ping_result = client.admin.command("ping")
                server_info = {"ok": ping_result.get("ok", 0)}
            except Exception:
                server_info = {"ok": 1.0}
            return jsonify({"status": "ok", "db_status": "ok", "server": server_info}), 200

        # Not OK
        db_status = "unconfigured" if err and "unconfigured" in err.lower() else "error"
        payload = {"status": "ok", "db_status": db_status}
        if err:
            payload["message"] = err
        # Always 200 to avoid taking app down due to DB
        return jsonify(payload), 200


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
            # Gracefully derive dbName; tolerate failures and None return
            try:
                active_db = db.get_db()
                db_name = getattr(active_db, "name", "unknown") or "unknown"
            except Exception:
                db_name = "unknown"

            # Use namespaced access for collection helpers/constants
            coll = db.get_collection(db.DEVICES_COLLECTION)

            count = 0
            sample_ids = []
            try:
                count = coll.count_documents({})
                # Fetch only _id to avoid any sensitive fields; limit to 3
                cursor = coll.find({}, {"_id": 1}).sort("_id", -1).limit(3)
                sample_ids = [str(doc.get("_id")) for doc in cursor if "_id" in doc]
            except Exception as coll_err:
                logging.getLogger(__name__).warning("Devices summary collection access issue: %s", coll_err)

            return jsonify({
                "dbName": db_name,
                "collection": db.DEVICES_COLLECTION,
                "count": count,
                "sampleIds": sample_ids,
            }), 200
        except Exception as e:
            logging.getLogger(__name__).error("Devices summary error: %s", str(e))
            return jsonify({"error": "Failed to load devices summary", "message": str(e)}), 500
