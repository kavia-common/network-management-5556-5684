from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Register common error handlers for consistent API responses."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        response = {
            "code": e.code,
            "status": e.name,
            "message": e.description,
            "errors": {},
        }
        return jsonify(response), e.code

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"code": 400, "status": "Bad Request", "message": "Invalid request", "errors": {}}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"code": 404, "status": "Not Found", "message": "Resource not found", "errors": {}}), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"code": 409, "status": "Conflict", "message": "Conflict", "errors": {}}), 409

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"code": 500, "status": "Internal Server Error", "message": "An unexpected error occurred", "errors": {}}), 500


# PUBLIC_INTERFACE
def error_response(status_code: int, message: str, errors: dict | None = None):
    """Return a structured error response."""
    from flask import jsonify
    http_names = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
    }
    payload = {
        "code": status_code,
        "status": http_names.get(status_code, "Error"),
        "message": message,
        "errors": errors or {},
    }
    return jsonify(payload), status_code
