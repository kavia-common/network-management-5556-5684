from flask_smorest import Blueprint
from flask.views import MethodView
from flask import jsonify

# Define a clean blueprint name and import name without spaces to avoid registration issues.
blp = Blueprint(
    "Health",
    "health",
    url_prefix="/",
    description="Basic health check endpoint that does not require any external services.",
)


@blp.route("/")
class HealthCheck(MethodView):
    """
    Health check route.

    Returns a simple JSON indicating the service is up. This endpoint does not
    depend on any database or external service and is safe to call for liveness checks.
    """
    def get(self):
        """
        GET /
        Summary: Service health check
        Description: Returns a 200 OK with a simple payload to indicate the service is running.
        """
        # Consistent response shape used across the API
        return jsonify({"data": {"status": "ok"}, "message": "Healthy", "error": None}), 200
