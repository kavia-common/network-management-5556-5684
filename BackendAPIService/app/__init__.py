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
# Configure precise allowed origins via FRONTEND_ORIGIN_ALLOWLIST (comma-separated).
# Defaults cover localhost and the common vscode-internal preview host ports (3000/3001).
#
# Environment variables:
# - FRONTEND_ORIGIN_ALLOWLIST or CORS_ALLOWED_ORIGINS (comma-separated)
#     Defaults to:
#       http://localhost:3000,
#       http://127.0.0.1:3000,
#       http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000,
#       http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001,
#       https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000,
#       https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001
#   If FRONTEND_ORIGIN_ALLOWLIST/CORS_ALLOWED_ORIGINS is provided in the environment or .env,
#   those values will override the defaults. To include an additional origin, append it to the
#   comma-separated list (e.g., add https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001).
# - CORS_SUPPORTS_CREDENTIALS (optional bool): "true"/"false" to enable cookie-based auth if needed.
#
# Allowed methods/headers include OPTIONS to ensure preflight succeeds.
default_allowlist = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000",
    "http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001",
    # Add HTTPS preview origins to avoid mixed-content and strict-origin issues
    "https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000",
    # Explicitly allow the running frontend preview origin used in this workspace
    "https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3000",
    "https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001",
]
# Support both legacy and new env var names
env_allowlist_raw = os.environ.get("FRONTEND_ORIGIN_ALLOWLIST") or os.environ.get("CORS_ALLOWED_ORIGINS", "")
if env_allowlist_raw.strip():
    origins = [o.strip() for o in env_allowlist_raw.split(",") if o.strip()]
else:
    origins = list(default_allowlist)

# De-duplicate while preserving order and ensure required preview hosts remain allowed
_required = {
    "https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000",
    "https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001",
}
_seen = set()
origins = [o for o in origins if not (o in _seen or _seen.add(o))]
for req in _required:
    if req not in origins:
        origins.append(req)


def _env_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


supports_credentials = _env_bool(os.environ.get("CORS_SUPPORTS_CREDENTIALS"), default=False)

CORS(
    app,
    resources={r"/*": {"origins": origins}},
    supports_credentials=supports_credentials,
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Type", "Content-Length", "X-Request-Id"],
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
except Exception as e:
    # Log warning without crashing so the API (including /health) can start.
    print(f"[Startup][WARN] MongoDB initialization failed (continuing to start API): {e}")
