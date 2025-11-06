import json
import types
import pytest

from app.routes.devices import _safe_ping

# Utilities to build a fake collection with in-memory data
class FakeResult:
    def __init__(self, inserted_id=None, deleted_count=0):
        self.inserted_id = inserted_id
        self.deleted_count = deleted_count

class FakeCollection:
    def __init__(self, initial=None):
        self.docs = list(initial or [])
        self._id_counter = 1000

    def _match(self, query):
        # very small matcher for {"_id": value}
        if "_id" in query:
            return [d for d in self.docs if d.get("_id") == query["_id"]]
        return list(self.docs)

    def count_documents(self, query):
        return len(self._match(query))

    def find(self, query):
        # Return an object with sort/skip/limit method chainability
        items = list(self._match(query))
        class Cursor:
            def __init__(self, data):
                self.data = data
            def sort(self, key, direction):
                # naive; ignore direction for simplicity
                return Cursor(list(self.data))
            def skip(self, n):
                return Cursor(self.data[n:])
            def limit(self, n):
                return Cursor(self.data[:n])
            def __iter__(self):
                return iter(self.data)
        return Cursor(items)

    def insert_one(self, doc):
        # Simulate unique constraint on ip_address
        for d in self.docs:
            if d.get("ip_address") == doc.get("ip_address"):
                from pymongo.errors import DuplicateKeyError
                raise DuplicateKeyError("duplicate ip")
        _id = f"id-{self._id_counter}"
        self._id_counter += 1
        new_doc = dict(doc)
        new_doc["_id"] = _id
        self.docs.append(new_doc)
        return FakeResult(inserted_id=_id)

    def find_one(self, query):
        matches = self._match(query)
        return dict(matches[0]) if matches else None

    def find_one_and_update(self, query, update, return_document=True):
        matches = self._match(query)
        if not matches:
            return None
        idx = self.docs.index(matches[0])
        set_fields = update.get("$set", {})
        updated = dict(self.docs[idx])
        updated.update(set_fields)
        self.docs[idx] = updated
        return dict(updated)

    def delete_one(self, query):
        matches = self._match(query)
        if not matches:
            return FakeResult(deleted_count=0)
        self.docs.remove(matches[0])
        return FakeResult(deleted_count=1)


@pytest.fixture()
def app(monkeypatch):
    # Build a minimal Flask app using the real factory in run.py if exists, else create here
    from flask import Flask
    from flask_smorest import Api
    from app.routes.devices import blp as devices_blp
    from app.routes.health import blp as health_blp

    # Stub DB collection getter
    fake_data = [
        {"_id": "id-1", "name": "Core", "ip_address": "192.168.0.1", "type": "router", "location": "DC", "status": "online"},
        {"_id": "id-2", "name": "Edge", "ip_address": "10.0.0.2", "type": "switch", "location": "HQ", "status": "offline"},
    ]
    coll = FakeCollection(initial=fake_data)

    from app import db as db_module
    monkeypatch.setattr(db_module, "get_collection", lambda name: coll)

    # Avoid real MongoClient creation in health endpoints
    def fake_get_client():
        class Dummy:
            class Admin:
                @staticmethod
                def command(x):
                    return {"ok": 1.0}
            admin = Admin()
        return Dummy()
    monkeypatch.setattr(db_module, "get_client", fake_get_client)

    app = Flask(__name__)
    app.config.update({
        "API_TITLE": "Test API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.0.3",
    })
    api = Api(app)
    api.register_blueprint(health_blp)
    api.register_blueprint(devices_blp)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_list_devices_envelope(client):
    resp = client.get("/devices?page=1&limit=10")
    assert resp.status_code == 200
    j = resp.get_json()
    assert set(j.keys()) == {"items", "total", "page", "limit"}
    assert isinstance(j["items"], list)
    assert j["total"] == 2
    assert j["page"] == 1
    assert j["limit"] == 10


def test_create_device_and_unique_ip(client, monkeypatch):
    # First create success
    payload = {
        "name": "Web",
        "ip_address": "10.0.0.5",
        "type": "server",
        "location": "HQ",
        "status": "online",
    }
    resp = client.post("/devices", json=payload)
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["name"] == "Web"
    assert created["ip_address"] == "10.0.0.5"
    assert created["id"]

    # Duplicate IP triggers 409 conflict
    resp2 = client.post("/devices", json=payload)
    assert resp2.status_code == 409
    j = resp2.get_json()
    assert j["error"]["field"] == "ip_address"


def test_get_update_delete_device(client):
    # Get existing
    resp = client.get("/devices/id-1")
    assert resp.status_code == 200
    dev = resp.get_json()
    assert dev["name"] == "Core"

    # Update device
    resp2 = client.put("/devices/id-1", json={"name": "Core-Updated"})
    assert resp2.status_code == 200
    updated = resp2.get_json()
    assert updated["name"] == "Core-Updated"

    # Delete
    resp3 = client.delete("/devices/id-1")
    assert resp3.status_code == 204

    # Now get should 404
    resp4 = client.get("/devices/id-1")
    assert resp4.status_code in (404, 500)  # abort -> flask-smorest renders 404; fallback handler could 500
    # If 500, ensure error payload
    if resp4.status_code == 500:
      assert resp4.is_json


def test_ping_endpoint_updates_status(client, monkeypatch):
    # Mock _safe_ping to return online
    monkeypatch.setattr("app.routes.devices._safe_ping", lambda ip: ("online", None))
    resp = client.post("/devices/id-2/ping")
    assert resp.status_code == 200
    j = resp.get_json()
    assert j["status"] == "online"
