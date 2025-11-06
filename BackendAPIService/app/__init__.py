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

# Import db module but do not force initialization at startup.
# We will defer connection until first DB access and have health endpoint report status.
from . import db as _db  # noqa: E402,F401

app = Flask(__name__)
app.url_map.strict_slashes = False

# -------------------------
# CORS configuration
# -------------------------
# We allow configuring the exact frontend origin via environment variables.
# Priority (first found wins):
#   1) BACKEND_CORS_ORIGINS (comma-separated list)
#   2) FRONTEND_ORIGIN (single origin)
#   3) FRONTEND_ORIGIN_ALLOWLIST or CORS_ALLOWED_ORIGINS (legacy comma-separated)
#   4) Default to http://localhost:3000
#
# Supports credentials via CORS_SUPPORTS_CREDENTIALS=true|false (default: false).
# Allowed methods/headers include OPTIONS to ensure preflight succeeds.


def _env_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


supports_credentials = _env_bool(os.environ.get("CORS_SUPPORTS_CREDENTIALS"), default=False)


def _resolve_allowed_origins() -> list[str] | str:
    # New primary var: BACKEND_CORS_ORIGINS (comma-separated)
    raw = os.environ.get("BACKEND_CORS_ORIGINS")
    if raw and raw.strip():
        values = [o.strip() for o in raw.split(",") if o.strip()]
        return values if values else "http://localhost:3000"

    # Secondary: single explicit FRONTEND_ORIGIN
    single = os.environ.get("FRONTEND_ORIGIN")
    if single and single.strip():
        return [single.strip()]

    # Legacy allowlists
    legacy = os.environ.get("FRONTEND_ORIGIN_ALLOWLIST") or os.environ.get("CORS_ALLOWED_ORIGINS")
    if legacy and legacy.strip():
        values = [o.strip() for o in legacy.split(",") if o.strip()]
        return values if values else "http://localhost:3000"

    # Fallback default for common dev setup
    return ["http://localhost:3000"]


resolved_origins = _resolve_allowed_origins()

# Normalize return type; flask-cors accepts "*" or list of origins.
if isinstance(resolved_origins, str):
    cors_origins = resolved_origins
else:
    cors_origins = [o for o in resolved_origins if o] or ["http://localhost:3000"]


CORS(
    app,
    resources={r"/*": {"origins": cors_origins}},
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


# Lazy DB initialization: do not touch DB at startup.
# Health endpoints and actual DB-using routes will initialize on first access and surface errors gracefully.
