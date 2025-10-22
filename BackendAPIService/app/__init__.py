from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

from app.config import Config
from app.db import Database
from app.utils.errors import register_error_handlers
from .routes.health import blp as health_blp
from .resources.devices import blp as devices_blp


def create_app() -> Flask:
    """Create and configure the Flask application with API and DB.

    Notes:
        - DB connection is lazy: no attempt is made at startup. This ensures the
          app starts even if MongoDB is down or URI is unset.
        - DB-backed endpoints should handle connection errors and return a clear
          JSON error response.
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Load config
    cfg = Config()
    app.config["API_TITLE"] = cfg.API_TITLE
    app.config["API_VERSION"] = cfg.API_VERSION
    app.config["OPENAPI_VERSION"] = cfg.OPENAPI_VERSION
    app.config["OPENAPI_URL_PREFIX"] = cfg.OPENAPI_URL_PREFIX
    app.config["OPENAPI_SWAGGER_UI_PATH"] = cfg.OPENAPI_SWAGGER_UI_PATH
    app.config["OPENAPI_SWAGGER_UI_URL"] = cfg.OPENAPI_SWAGGER_UI_URL
    app.config["PING_TIMEOUT_MS"] = cfg.PING_TIMEOUT_MS

    # Init API
    api = Api(app)

    # Initialize DB wrapper only; do not connect here (lazy connection)
    db = Database(
        uri=cfg.MONGODB_URI,
        db_name=cfg.MONGODB_DB_NAME,
        tls=cfg.MONGODB_TLS,
        username=cfg.MONGODB_USER,
        password=cfg.MONGODB_PASSWORD,
    )
    # Store db instance in app extensions
    app.extensions["db_instance"] = db

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    api.register_blueprint(health_blp)
    api.register_blueprint(devices_blp)

    return app


# Expose a default app instance for simple runners
app = create_app()
