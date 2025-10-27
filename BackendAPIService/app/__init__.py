from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
from .routes import health_blp, devices_blp

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # If python-dotenv is not installed or any error occurs, proceed without failing.
    pass

# Import db to initialize Mongo connection on startup if env is configured
from . import db as _db  # noqa: F401

app = Flask(__name__)
app.url_map.strict_slashes = False
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure API documentation
app.config["API_TITLE"] = "Network Devices API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["OPENAPI_TAGS"] = [
    {"name": "Health", "description": "Health check route"},
    {"name": "Devices", "description": "CRUD and ping endpoints for devices"},
]

api = Api(app)
api.register_blueprint(health_blp)
api.register_blueprint(devices_blp)

# Fail fast on startup if DB is misconfigured or unreachable.
# This attempts a ping; if it fails, raise to stop the app early with a clear message.
try:
    _db.get_client()  # initializes client and ensures indexes; will ping internally
except Exception as e:
    # Print a clear startup failure message and re-raise to abort startup.
    print(f"[Startup] MongoDB initialization failed: {e}")
    raise
