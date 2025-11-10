import os
import pytest

# Ensure a Mongo URI is present for app.db to initialize, but we will monkeypatch MongoClient itself.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "test_network_devices")

@pytest.fixture(autouse=True)
def _patch_mongo(monkeypatch):
    """
    Autouse fixture that patches app.db.MongoClient with mongomock.MongoClient
    so that all DB operations happen in-memory with no external dependency.
    This ensures no real connections to localhost:27017 occur during tests.
    """
    try:
        import mongomock  # type: ignore
    except Exception as e:
        pytest.skip(f"mongomock not installed: {e}")

    # Create a single mongomock client instance per test (fresh per test function).
    mm_client = mongomock.MongoClient()

    def fake_mongo_client(uri=None, **kwargs):  # match signature loosely
        # ignore uri and kwargs; return the mongomock client
        return mm_client

    # Ensure deterministic env for TLS flag
    monkeypatch.setenv("MONGO_TLS", "false")

    # Reload app.db to make sure we patch the exact symbol used by the application code.
    import importlib
    import app.db as app_db
    importlib.reload(app_db)

    # Patch the exact symbol app.db.MongoClient so that _build_mongo_client uses our fake.
    monkeypatch.setattr(app_db, "MongoClient", fake_mongo_client, raising=True)

    yield

    # cleanup: reload app_db to clear any cached singletons between tests
    importlib.reload(app_db)


@pytest.fixture
def client():
    """
    Test client for the Flask app.
    """
    from app import app
    app.config.update(TESTING=True)
    return app.test_client()
