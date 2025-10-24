from flask_smorest import Blueprint
from flask.views import MethodView
from app import db as _db  # use db.ping for health
from flask import jsonify

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
          200: {"status": "ok"} when MongoDB ping succeeds
          500: {"status": "error", "message": "<details>"} when connectivity fails
        """
        ok, err = _db.ping()
        if ok:
            # Success format required by task
            return jsonify({"status": "ok"}), 200
        # Error format and 500 status required by task, include actionable context
        return jsonify({"status": "error", "message": err}), 500
