from app import app
import os


# PUBLIC_INTERFACE
def main():
    """Entrypoint to run the Flask app bound to 0.0.0.0 with port from PORT env (default 3001)."""
    try:
        port = int(os.environ.get("PORT", "3001"))
    except Exception:
        port = 3001
    # Bind to all interfaces and use env-configured port
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
