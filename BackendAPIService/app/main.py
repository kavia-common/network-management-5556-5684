import os
from app import create_app

# PUBLIC_INTERFACE
def run():
    """Entrypoint to run the Flask app using env PORT."""
    app = create_app()
    port = int(os.getenv("PORT", app.config.get("PORT", 3001)))
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    run()
