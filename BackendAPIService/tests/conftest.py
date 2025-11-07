"""Global pytest configuration and fixtures for BackendAPIService tests.

This conftest ensures:
- The BackendAPIService root is added to sys.path so that 'import app' works from tests.
- Provides shared 'app' and 'client' fixtures for tests that don't define their own.
- Sets testing-friendly environment variables and permissive CORS for predictable headers.

Fixtures:
- app: A Flask app with registered health and devices blueprints
- client: Flask test client bound to the 'app' fixture
"""
import os
import sys
from typing import Generator

import pytest


def _ensure_path():
    """
    Ensure the BackendAPIService package root is on sys.path so `import app` works.

    We compute the project root as the parent directory of this file's parent (tests/..).
    """
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    service_root = os.path.abspath(os.path.join(tests_dir, os.pardir))
    if service_root not in sys.path:
        sys.path.insert(0, service_root)


_ensure_path()


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> Generator[None, None, None]:
    """
    Set environment variables for test session.

    - Enable Flask testing mode
    - Allow permissive CORS for simpler header assertions
    - Prevent accidental real DB connections by leaving MONGODB_* unset (tests monkeypatch db access)
    """
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("PYTHON_ENV", "testing")
    # Configure CORS to be permissive by default during tests
    os.environ.setdefault("BACKEND_CORS_ORIGINS", "*")
    yield


@pytest.fixture()
def app(monkeypatch):
    """
    Build a minimal Flask app for unit/integration tests using the real blueprints.

    Notes:
    - Tests will monkeypatch app.db.get_collection and related functions to avoid real DB usage.
    - We also provide a dummy get_client to satisfy health endpoints when not explicitly patched.
    """
    from flask import Flask
    from flask_smorest import Api

    # Import actual blueprints from the application
    from app.routes.devices import blp as devices_blp
    from app.routes.health import blp as health_blp

    # Provide a dummy get_client by default so health endpoints can succeed unless a test overrides it
    try:
        from app import db as db_module

        class _DummyAdmin:
            @staticmethod
            def command(_cmd):
                return {"ok": 1.0}

        class _DummyClient:
            admin = _DummyAdmin()

        if not hasattr(db_module, "_TEST_DUMMY_CLIENT_SET"):
            # Only set a default dummy once; tests can still override with monkeypatch
            monkeypatch.setattr(db_module, "get_client", lambda: _DummyClient(), raising=False)
            setattr(db_module, "_TEST_DUMMY_CLIENT_SET", True)
    except Exception:
        # If import issues arise, we don't fail here; tests that need db will patch explicitly.
        pass

    app = Flask(__name__)
    app.config.update(
        {
            "TESTING": True,
            "API_TITLE": "Network Devices API",
            "API_VERSION": "v1",
            "OPENAPI_VERSION": "3.0.3",
        }
    )
    api = Api(app)
    api.register_blueprint(health_blp)
    api.register_blueprint(devices_blp)
    return app


@pytest.fixture()
def client(app):
    """
    Provide a Flask test client bound to the 'app' fixture.
    """
    return app.test_client()
