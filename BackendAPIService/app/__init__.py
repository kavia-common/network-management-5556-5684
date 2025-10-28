from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
from .routes import health_blp, devices_blp
import os

# Load environment variables from .env if present.
# We explicitly attempt to load BackendAPIService/.env to be robust to different CWDs.
try:
    from dotenv import load_dotenv  # type: ignore

    # Resolve potential .env locations
    this_dir = os.path.dirname(os.path.abspath(__file__))
    service_root = os.path.abspath(os.path.join(this_dir, os.pardir))
    explicit_env_path = os.path.join(service_root, ".env")

    loaded = False
    if os.path.isfile(explicit_env_path):
        loaded = load_dotenv(dotenv_path=explicit_env_path, override=False)
        if loaded:
            print(f"[Startup][INFO] Loaded environment from {explicit_env_path}")
    if not loaded:
        # Fallback: default search (nearest .env)
        loaded = load_dotenv()
        if loaded:
            print("[Startup][INFO] Loaded environment from default .env search")
except Exception as _e:
    # If python-dotenv is not installed or any error occurs, proceed without failing.
    print(f"[Startup][WARN] Could not load .env automatically: {_e}")

# Import db to initialize Mongo connection on startup if env is configured
from . import db as _db  # noqa: F401

app = Flask(__name__)
app.url_map.strict_slashes = False

# Configure CORS for React frontend on http://localhost:3000 covering all routes.
# Allow standard methods and common headers; enable credentials support for future use.
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:3000"]}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

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

# Try DB initialization on startup to surface issues early, but do not abort the app.
# Health endpoint will still report detailed DB errors.
try:
    _db.get_client()  # initializes client and ensures indexes; will ping internally
except Exception as e:
    # Log warning without crashing so the API (including /health) can start.
    print(f"[Startup][WARN] MongoDB initialization failed (continuing to start API): {e}")
