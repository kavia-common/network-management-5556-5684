import os
from dataclasses import dataclass

@dataclass
class Config:
    """
    Configuration loaded from environment variables.

    Environment Variables:
    - MONGODB_URI: MongoDB connection string (required)
    - MONGODB_DB_NAME: Database name (required)
    - MONGODB_TLS: Optional, "true"/"false" to enforce TLS (defaults to auto by URI)
    - SERVER_HOST: Host to bind Flask server (default: 0.0.0.0)
    - SERVER_PORT: Port to bind Flask server (default: 3001)
    """
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "")
    MONGODB_TLS: str = os.getenv("MONGODB_TLS", "")
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "3001"))

    def validate(self):
        """Validate required config values are present."""
        missing = []
        if not self.MONGODB_URI:
            missing.append("MONGODB_URI")
        if not self.MONGODB_DB_NAME:
            missing.append("MONGODB_DB_NAME")
        return missing
