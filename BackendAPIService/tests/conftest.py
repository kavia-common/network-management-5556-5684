import os
import pytest

# Ensure a Mongo URI is present for app.db to initialize, but we will monkeypatch MongoClient itself.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "test_network_devices")

@pytest.fixture(autouse=True)
def _patch_mongo(monkeypatch):
    """
    Autouse fixture that patches pymongo.MongoClient with mongomock.MongoClient
    so that all DB operations happen in-memory with no external dependency.
    """
    try:
        import mongomock  # type: ignore
    except Exception as e:
        pytest.skip(f"mongomock not installed: {e}")

    from pymongo import mongo_client as _mongo_client_mod

    # Create a single mongomock client instance per test (fresh per test function).
    mm_client = mongomock.MongoClient()

    def fake_mongo_client(uri, **kwargs):
        # ignore uri and kwargs; return the mongomock client
        return mm_client

    # Patch the constructor used by app.db._build_mongo_client() which imports MongoClient from pymongo
    monkeypatch.setattr(_mongo_client_mod, "MongoClient", fake_mongo_client, raising=True)
    monkeypatch.setenv("MONGO_TLS", "false")

    # Also clear any cached client in app.db to ensure fresh state
    import importlib
    import app.db as app_db
    importlib.reload(app_db)

    yield

    # cleanup
    importlib.reload(app_db)


@pytest.fixture
def client():
    """
    Test client for the Flask app.
    """
    from app import app
    app.config.update(TESTING=True)
    return app.test_client()
