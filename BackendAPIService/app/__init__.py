import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api

from .routes.health import blp as health_blp
from .resources.devices import blp as devices_blp


def create_app() -> Flask:
    """Application factory for the Backend API Service."""
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # CORS for future frontend usage
    CORS(app, resources={r"/*": {"origins": "*"}})

    # OpenAPI / Swagger config
    app.config["API_TITLE"] = "Network Device Management API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    api = Api(app)

    # Register blueprints
    api.register_blueprint(health_blp)
    api.register_blueprint(devices_blp)

    # Global error handlers for JSON consistency
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"data": None, "message": "Not Found", "error": {"detail": "Resource not found"}}), 404

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"data": None, "message": "Internal Server Error", "error": {"detail": str(e)}}), 500

    return app


# Initialize default app for WSGI servers
app = create_app()

# Allow running via `python -m app` if needed
if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "3001"))
    app.run(host=host, port=port)
