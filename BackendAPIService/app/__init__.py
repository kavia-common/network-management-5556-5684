import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_smorest import Api
from marshmallow import ValidationError  # type: ignore
from werkzeug.exceptions import HTTPException, UnprocessableEntity

from .routes import health_blp, devices_blp

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
from . import db as _db  # noqa: E402,F401

app = Flask(__name__)
app.url_map.strict_slashes = False

# -------------------------
# CORS configuration
# -------------------------
# We allow configuring the exact frontend origin via FRONTEND_ORIGIN.
# For development, we default to permissive but safe origins commonly used by React dev servers.
#
# Environment variables:
# - FRONTEND_ORIGIN: A single origin (e.g., "http://localhost:3000" or "https://<preview-host>:3000")
#   If set, only that origin will be allowed.
# - ADDITIONAL_CORS_ORIGINS: Comma-separated list of extra origins to allow (optional).
#
# Notes:
# - In development we enable credentials and common methods/headers.
# - Restrict FRONTEND_ORIGIN in production deployments.
frontend_origin = os.environ.get("FRONTEND_ORIGIN")
additional_origins = os.environ.get("ADDITIONAL_CORS_ORIGINS", "")

# Explicitly include provided task host origins for convenience in this environment
task_specific_frontend = "http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000"

default_dev_origins = [
    "http://localhost:3000",
    # Allow common kavia preview hosts on port 3000 for dev
    "https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000",
    "https://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000",
    task_specific_frontend,
]

allowed_origins = []
if frontend_origin:
    # Use exactly the provided origin; scheme must match (avoid mixed content)
    allowed_origins.append(frontend_origin.strip())
else:
    # Use development-friendly defaults including the task host
    allowed_origins.extend(default_dev_origins)

if additional_origins:
    allowed_origins.extend([o.strip() for o in additional_origins.split(",") if o.strip()])

# De-duplicate while preserving order
seen = set()
allowed_origins = [o for o in allowed_origins if not (o in seen or seen.add(o))]

# If FRONTEND_ORIGIN is explicitly set, restrict to that/those origins; otherwise allow "*"
cors_origins = allowed_origins if frontend_origin else "*"

CORS(
    app,
    resources={r"/*": {"origins": cors_origins}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Type", "Content-Length", "X-Request-Id"],
)
# Minimal startup diagnostics for CORS
try:
    print(f"[Startup][INFO] CORS allowed origins: {cors_origins}")
except Exception:
    pass

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


# Normalize validation errors from flask-smorest/webargs (default 422) to HTTP 400
@app.errorhandler(UnprocessableEntity)
def handle_unprocessable_entity(e: UnprocessableEntity):
    # Convert 422 to 400 with a compact error structure
    data = getattr(e, "data", None)
    messages = None
    if isinstance(data, dict):
        messages = data.get("messages")
    response = {
        "status": "Bad Request",
        "code": 400,
        "message": "Validation failed",
        "errors": messages if messages else {},
        "path": request.path,
    }
    return jsonify(response), 400


@app.errorhandler(ValidationError)
def handle_validation_error(e: ValidationError):
    response = {
        "status": "Bad Request",
        "code": 400,
        "message": "Validation failed",
        "errors": e.messages if hasattr(e, "messages") else {},
        "path": request.path,
    }
    return jsonify(response), 400


# Global JSON error handling to ensure clients always receive JSON with proper content type
@app.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException):
    # Build a consistent JSON body
    response = {
        "status": e.name,
        "code": e.code,
        "message": e.description if isinstance(e.description, str) else str(e.description),
        "path": request.path,
    }
    return jsonify(response), e.code


@app.errorhandler(Exception)
def handle_unexpected_exception(e: Exception):
    # Do not leak internals; provide a generic message and status 500
    # Include minimal path for diagnostics
    print(f"[ERROR] Unhandled exception at {request.path}: {e}")
    response = {
        "status": "Internal Server Error",
        "code": 500,
        "message": "An unexpected error occurred while processing the request.",
        "path": request.path,
    }
    return jsonify(response), 500


# Try DB initialization on startup to surface issues early, but do not abort the app.
# Health endpoint will still report detailed DB errors.
try:
    _db.get_client()  # initializes client and ensures indexes; will ping internally
    # After client init, log effective DB name and devices collection
    try:
        effective_db = _db.get_db()
        from .db import DEVICES_COLLECTION as _DEV_COLL  # local import to avoid circulars
        print(f"[Startup][INFO] MongoDB initialized: db='{effective_db.name}', collection='{_DEV_COLL}'")
    except Exception as _e_db:
        print(f"[Startup][WARN] Could not determine DB/collection after init: {_e_db}")
except Exception as e:
    # Log warning without crashing so the API (including /health) can start.
    print(f"[Startup][WARN] MongoDB initialization failed (continuing to start API): {e}")
