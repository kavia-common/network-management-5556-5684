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
        Returns:
          200: {"status": "up"}
          503: {"status": "down", "error": "<details>"}
        """
        ok, err = _db.ping()
        if ok:
            return jsonify({"status": "up"}), 200
        return jsonify({"status": "down", "error": err}), 503
