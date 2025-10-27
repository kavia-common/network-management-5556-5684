from flask_smorest import Blueprint
from flask.views import MethodView
from app import db as _db  # use db.ping for health
from flask import jsonify
import logging

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
