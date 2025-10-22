import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

def register_error_handlers(app: Flask) -> None:
    """Register global error handlers returning consistent JSON."""
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": {"code": 400, "status": "Bad Request", "message": str(e)}},), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": {"code": 404, "status": "Not Found", "message": "Resource not found"}},), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": {"code": 405, "status": "Method Not Allowed", "message": "Method not allowed"}},), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": {"code": 409, "status": "Conflict", "message": str(e)}},), 409

    @app.errorhandler(422)
    def unprocessable(e):
        # webargs/marshmallow use 422
        return jsonify({"error": {"code": 422, "status": "Unprocessable Entity", "message": "Validation failed"}},), 422

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": {"code": 500, "status": "Internal Server Error", "message": "An unexpected error occurred"}},), 500


def create_api(app: Flask) -> Api:
    """Configure Flask-Smorest API with OpenAPI docs."""
    app.config["API_TITLE"] = "Network Device Management API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    api = Api(app)

    # Register blueprints
    from .routes.health import blp as health_blp
    from .resources.device_resource import blp as devices_blp
    api.register_blueprint(health_blp)
    api.register_blueprint(devices_blp)
    return api


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Application factory for the Backend API Service."""
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # CORS: allow all origins for now
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Load configuration
    from .config import Config
    app.config.from_object(Config())

    # Initialize DB
    from .db import init_db
    init_db(app)

    # Register API and routes
    create_api(app)

    # Error handlers
    register_error_handlers(app)

    # Basic root redirect info for convenience
    @app.get("/docs/help")
    def docs_help():
        """
        Returns basic information about API docs and websocket (none) usage.
        """
        return jsonify({
            "message": "OpenAPI docs available at /docs/, spec at /openapi.json.",
            "websocket": "This API does not use websockets.",
        })

    return app


# Allow running via `python -m app`
if __name__ == "__main__":
    # Bind to 0.0.0.0:3001 by default for preview system
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "3001"))
    app = create_app()
    app.run(host=host, port=port)
