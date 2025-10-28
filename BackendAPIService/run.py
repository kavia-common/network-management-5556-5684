from app import app

# PUBLIC_INTERFACE
def main():
    """Entrypoint to run the Flask app bound to 0.0.0.0:3001 for consistency with docs."""
    # Bind to all interfaces and use port 3001 as documented
    app.run(host="0.0.0.0", port=3001)

if __name__ == "__main__":
    main()
