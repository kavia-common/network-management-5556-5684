import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    API_TITLE: str = os.getenv("API_TITLE", "Network Device Management API")
    API_VERSION: str = os.getenv("API_VERSION", "v1")
    OPENAPI_VERSION: str = "3.0.3"
    OPENAPI_URL_PREFIX: str = "/docs"
    OPENAPI_SWAGGER_UI_PATH: str = ""
    OPENAPI_SWAGGER_UI_URL: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    PORT: int = int(os.getenv("PORT", "3001"))

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "network_devices")
    MONGODB_TLS: bool = os.getenv("MONGODB_TLS", "0") in ("1", "true", "True")
    MONGODB_USER: str | None = os.getenv("MONGODB_USER")
    MONGODB_PASSWORD: str | None = os.getenv("MONGODB_PASSWORD")

    # Utilities
    PING_TIMEOUT_MS: int = int(os.getenv("PING_TIMEOUT_MS", "2000"))
