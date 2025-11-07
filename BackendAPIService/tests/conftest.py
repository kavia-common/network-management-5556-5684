"""Global pytest configuration and fixtures for BackendAPIService tests.

This conftest ensures:
- The BackendAPIService root is added to sys.path so that 'import app' works from tests.
- Provides shared 'app' and 'client' fixtures for tests that don't define their own.
- Sets testing-friendly environment variables and permissive CORS for predictable headers.
- Monkeypatches DB access (get_collection/get_client) to an in-memory fake by default to avoid real MongoDB.

Fixtures:
- app: A Flask app with registered health and devices blueprints
- client: Flask test client bound to the 'app' fixture
"""
import os
import sys
from typing import Generator, List, Dict, Any

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


class _FakeResult:
    def __init__(self, inserted_id=None, deleted_count=0):
        self.inserted_id = inserted_id
        self.deleted_count = deleted_count


class _FakeCursor:
    def __init__(self, data: List[Dict[str, Any]]):
        self._data = list(data)

    # Maintain chainability; ignore actual sort semantics for tests
    def sort(self, key, direction):
        return _FakeCursor(list(self._data))

    def skip(self, n: int):
        return _FakeCursor(self._data[n:])

    def limit(self, n: int):
        return _FakeCursor(self._data[:n])

    def __iter__(self):
        return iter(self._data)


class _FakeCollection:
    """
    Minimal in-memory collection emulating the subset of PyMongo used by routes.
    """
    def __init__(self, initial=None):
        self.docs: List[Dict[str, Any]] = list(initial or [])
        self._id_counter = 100

    def _match(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        if "_id" in query:
            return [d for d in self.docs if d.get("_id") == query["_id"]]
        return list(self.docs)

    def count_documents(self, query: Dict[str, Any]) -> int:
        return len(self._match(query))

    def find(self, query: Dict[str, Any], projection: Dict[str, Any] | None = None):
        items = self._match(query)
        if projection is not None and projection.get("_id") == 1:
            items = [{"_id": d["_id"]} for d in items if "_id" in d]
        return _FakeCursor(items)

    def find_one(self, query: Dict[str, Any]):
        m = self._match(query)
        return dict(m[0]) if m else None

    def insert_one(self, doc: Dict[str, Any]):
        # Enforce unique ip_address like our schema/index
        for d in self.docs:
            if d.get("ip_address") == doc.get("ip_address"):
                from pymongo.errors import DuplicateKeyError
                raise DuplicateKeyError("duplicate ip")
        new_id = f"id-{self._id_counter}"
        self._id_counter += 1
        new_doc = dict(doc)
        new_doc["_id"] = new_id
        self.docs.append(new_doc)
        return _FakeResult(inserted_id=new_id)

    def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], return_document=True):
        m = self._match(query)
        if not m:
            return None
        idx = self.docs.index(m[0])
        set_fields = update.get("$set", {})
        updated = {**self.docs[idx], **set_fields}
        self.docs[idx] = updated
        return dict(updated)

    def delete_one(self, query: Dict[str, Any]):
        m = self._match(query)
        if not m:
            return _FakeResult(deleted_count=0)
        self.docs.remove(m[0])
        return _FakeResult(deleted_count=1)


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> Generator[None, None, None]:
    """
    Set environment variables for test session.

    - Enable Flask testing mode
    - Allow permissive CORS for simpler header assertions
    - Prevent accidental real DB connections (leave MONGODB_* unset)
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

    Default behavior:
    - Monkeypatch app.db.get_collection to return an in-memory fake collection shared for the app instance.
    - Monkeypatch app.db.get_client to a dummy that returns ping ok for health routes.
    Tests remain free to override these with their own monkeypatches.
    """
    from flask import Flask
    from flask_smorest import Api

    # Import actual blueprints from the application
    from app.routes.devices import blp as devices_blp
    from app.routes.health import blp as health_blp

    # Prepare default in-memory data used by many unit tests
    initial_docs = [
        {
            "_id": "id-1",
            "name": "Core",
            "ip_address": "192.168.0.1",
            "type": "router",
            "location": "DC",
            "status": "online",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "last_checked": None,
        },
        {
            "_id": "id-2",
            "name": "Edge",
            "ip_address": "10.0.0.2",
            "type": "switch",
            "location": "HQ",
            "status": "offline",
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "last_checked": None,
        },
    ]
    fake_coll = _FakeCollection(initial=initial_docs)

    # Monkeypatch db accessors globally for the app instance
    from app import db as db_module

    monkeypatch.setattr(db_module, "get_collection", lambda name: fake_coll, raising=False)

    class _DummyAdmin:
        @staticmethod
        def command(_cmd):
            return {"ok": 1.0}

    class _DummyClient:
        admin = _DummyAdmin()

    monkeypatch.setattr(db_module, "get_client", lambda: _DummyClient(), raising=False)

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
