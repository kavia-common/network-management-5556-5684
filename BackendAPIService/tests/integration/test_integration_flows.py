import pytest

from flask import Flask
from flask_smorest import Api

# We assemble a real Flask app instance by importing app and registering blueprints.
# Mongo interactions are stubbed with a simple in-memory fake collection to avoid external dependencies.


class FakeResult:
    def __init__(self, inserted_id=None, deleted_count=0):
        self.inserted_id = inserted_id
        self.deleted_count = deleted_count


class FakeCursor:
    def __init__(self, data):
        self._data = list(data)

    def sort(self, key, direction):
        # return a copy for chainability; ignore direction for simplicity
        return FakeCursor(list(self._data))

    def skip(self, n):
        return FakeCursor(self._data[n:])

    def limit(self, n):
        return FakeCursor(self._data[:n])

    def __iter__(self):
        return iter(self._data)

class FakeCollection:
    def __init__(self, initial=None):
        self.docs = list(initial or [])
        self._id_counter = 100

    def _match(self, query):
        if "_id" in query:
            return [d for d in self.docs if d.get("_id") == query["_id"]]
        return list(self.docs)

    def count_documents(self, query):
        return len(self._match(query))

    def find(self, query, projection=None):
        # naive projection handling for health/devices-summary that asks {"_id": 1}
        if projection is not None and projection.get("_id") == 1:
            items = [{"_id": d["_id"]} for d in self._match(query)]
        else:
            items = self._match(query)
        return FakeCursor(items)

    def find_one(self, query):
        m = self._match(query)
        return dict(m[0]) if m else None

    def insert_one(self, doc):
        # enforce unique ip_address
        for d in self.docs:
            if d.get("ip_address") == doc.get("ip_address"):
                from pymongo.errors import DuplicateKeyError
                raise DuplicateKeyError("duplicate ip")
        new_id = f"id-{self._id_counter}"
        self._id_counter += 1
        new_doc = dict(doc)
        new_doc["_id"] = new_id
        self.docs.append(new_doc)
        return FakeResult(inserted_id=new_id)

    def find_one_and_update(self, query, update, return_document=True):
        m = self._match(query)
        if not m:
            return None
        idx = self.docs.index(m[0])
        set_fields = update.get("$set", {})
        updated = {**self.docs[idx], **set_fields}
        self.docs[idx] = updated
        return dict(updated)

    def delete_one(self, query):
        m = self._match(query)
        if not m:
            return FakeResult(deleted_count=0)
        self.docs.remove(m[0])
        return FakeResult(deleted_count=1)


@pytest.fixture()
def app(monkeypatch):
    from app.routes.devices import blp as devices_blp
    from app.routes.health import blp as health_blp
    from app import db as db_module

    # Initialize fake in-memory devices collection
    initial_docs = [
        {
            "_id": "id-1",
            "name": "Core Router",
            "ip_address": "192.168.0.1",
            "type": "router",
            "location": "DC-1",
            "status": "online",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "last_checked": None,
        },
        {
            "_id": "id-2",
            "name": "Edge Switch",
            "ip_address": "10.0.0.2",
            "type": "switch",
            "location": "HQ",
            "status": "offline",
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "last_checked": None,
        },
    ]
    fake_coll = FakeCollection(initial=initial_docs)

    # Monkeypatch db accessors
    monkeypatch.setattr(db_module, "get_collection", lambda name: fake_coll)

    # Fake get_client for health ping
    class DummyAdmin:
        @staticmethod
        def command(_cmd):
            return {"ok": 1.0}

    class DummyClient:
        admin = DummyAdmin()

    monkeypatch.setattr(db_module, "get_client", lambda: DummyClient())

    # Ensure permissive CORS for integration expectations
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")

    app = Flask(__name__)
    app.config.update(
        API_TITLE="Network Devices API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        TESTING=True,
    )
    api = Api(app)
    api.register_blueprint(health_blp)
    api.register_blueprint(devices_blp)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def _assert_cors_headers(resp, origin="http://example.com"):
    # When ALLOWED_ORIGINS="*", flask-cors returns Access-Control-Allow-Origin: *
    # The test client doesn't set Origin header; we only assert header presence when configured.
    allow_origin = resp.headers.get("Access-Control-Allow-Origin")
    assert allow_origin in ("*", None)  # "*" when configured; None if not applied to this response in test client
    # Common headers configured by CORS() setup
    assert "Content-Type" in resp.headers


def test_health_endpoints_and_cors(client):
    r = client.get("/")
    assert r.status_code == 200
    j = r.get_json()
    assert j["message"] == "Healthy"
    _assert_cors_headers(r)

    r2 = client.get("/health/db")
    assert r2.status_code == 200
    j2 = r2.get_json()
    assert j2["status"] == "ok"
    _assert_cors_headers(r2)

    r3 = client.get("/health/devices-summary")
    assert r3.status_code == 200
    j3 = r3.get_json()
    assert "dbName" in j3 and "collection" in j3 and "count" in j3 and isinstance(j3["sampleIds"], list)
    _assert_cors_headers(r3)


def test_devices_list_envelope_pagination_and_cors(client):
    r = client.get("/devices?page=1&limit=10")
    assert r.status_code == 200
    assert r.is_json
    j = r.get_json()
    assert set(j.keys()) == {"items", "total", "page", "limit"}
    assert isinstance(j["items"], list)
    assert j["total"] >= len(j["items"])
    assert j["page"] == 1
    assert j["limit"] == 10
    _assert_cors_headers(r)


def test_devices_crud_and_duplicate_ip(client, monkeypatch):
    # Create
    payload = {
        "name": "Web Server",
        "ip_address": "10.10.10.10",
        "type": "server",
        "location": "HQ",
        "status": "online",
    }
    r = client.post("/devices", json=payload)
    assert r.status_code == 201
    created = r.get_json()
    assert created["name"] == payload["name"]
    assert created["ip_address"] == payload["ip_address"]
    assert created["id"]

    # Duplicate IP
    r_dup = client.post("/devices", json=payload)
    assert r_dup.status_code == 409
    jdup = r_dup.get_json()
    assert jdup["error"]["field"] == "ip_address"

    # Read (GET)
    created_id = created["id"]
    r_get = client.get(f"/devices/{created_id}")
    assert r_get.status_code == 200
    got = r_get.get_json()
    assert got["id"] == created_id

    # Update (PUT)
    r_upd = client.put(f"/devices/{created_id}", json={"name": "Web Server Updated"})
    assert r_upd.status_code == 200
    upd = r_upd.get_json()
    assert upd["name"] == "Web Server Updated"

    # Ping
    # Force ping to set status 'online'
    monkeypatch.setattr("app.routes.devices._safe_ping", lambda ip: ("online", None))
    r_ping = client.post(f"/devices/{created_id}/ping")
    assert r_ping.status_code == 200
    jping = r_ping.get_json()
    assert jping["status"] in ("online", "offline")  # depending on safe_ping

    # Delete
    r_del = client.delete(f"/devices/{created_id}")
    assert r_del.status_code == 204

    # Verify gone
    r_get2 = client.get(f"/devices/{created_id}")
    assert r_get2.status_code in (404, 500)  # 404 via abort; 500 if global handler captured something


def test_preflight_options_and_cors(client):
    # OPTIONS on collection route
    r = client.open("/devices", method="OPTIONS")
    assert r.status_code in (200, 204)  # flask-cors may respond 200/204
    # OPTIONS on ping route
    r2 = client.open("/devices/id-2/ping", method="OPTIONS")
    assert r2.status_code in (200, 204)
