import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "3001"))
    app.run(host=host, port=port)
