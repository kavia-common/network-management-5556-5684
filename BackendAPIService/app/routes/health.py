from flask_smorest import Blueprint
from flask.views import MethodView

blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")

@blp.route("")
class HealthCheck(MethodView):
    def get(self):
        """Simple health check endpoint."""
        return {"message": "Healthy"}
