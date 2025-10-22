import os
from app import create_app

if __name__ == "__main__":
    app = create_app()
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "3001"))
    app.run(host=host, port=port)
