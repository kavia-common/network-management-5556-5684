from flask_smorest import Blueprint
from flask.views import MethodView

# Align blueprint name and description; no functional impact
blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")


@blp.route("/")
class HealthCheck(MethodView):
    def get(self):
        """Basic liveness endpoint."""
        return {"message": "Healthy"}
