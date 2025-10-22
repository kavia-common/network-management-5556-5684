from app import create_app

# PUBLIC_INTERFACE
def application():
    """WSGI application factory."""
    return create_app()

app = create_app()
