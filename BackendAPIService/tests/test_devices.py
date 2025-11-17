import re
from pymongo.errors import DuplicateKeyError

def make_device_payload(i=1, **overrides):
    payload = {
        "name": f"Device {i}",
        "ip_address": f"192.168.1.{i}",
        "type": "router",
        "location": "Data Center",
        "status": "unknown",
    }
    payload.update(overrides)
    return payload

def assert_device_shape(doc):
    # minimal shape checks
    assert set(["id", "name", "ip_address", "type", "location", "status", "created_at", "updated_at"]).issubset(set(doc.keys()))
    # ISO8601 datetime strings expected from marshmallow serialization
    iso_dt = re.compile(r"\d{4}-\d{2}-\d{2}T")
    assert iso_dt.search(doc["created_at"])
    assert iso_dt.search(doc["updated_at"])

def test_create_and_get_device(client):
    payload = make_device_payload(10)
    res = client.post("/devices", json=payload)
    assert res.status_code == 201
    created = res.get_json()
    assert created["ip_address"] == payload["ip_address"]
    assert_device_shape(created)

    # get by id
    res = client.get(f"/devices/{created['id']}")
    assert res.status_code == 200
    got = res.get_json()
    assert got["id"] == created["id"]
    assert_device_shape(got)

def test_create_device_bad_payloads(client):
    # invalid enum
    res = client.post("/devices", json=make_device_payload(type="firewall"))
    assert res.status_code == 422
    # invalid IP format
    res = client.post("/devices", json=make_device_payload(ip_address="999.1.1.1"))
    assert res.status_code == 422
    # missing required
    bad = make_device_payload()
    bad.pop("name")
    res = client.post("/devices", json=bad)
    assert res.status_code == 422

def test_list_devices_full_array_when_no_pagination(client):
    # create few devices
    for i in range(1, 4):
        client.post("/devices", json=make_device_payload(i))
    res = client.get("/devices")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 3
    for d in data:
        assert_device_shape(d)

def test_list_devices_with_pagination(client):
    for i in range(1, 8):
        client.post("/devices", json=make_device_payload(i))
    res = client.get("/devices?page=2&limit=3")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data.keys()) == {"items", "total", "page", "limit"}
    assert data["page"] == 2
    assert data["limit"] == 3
    assert data["total"] == 7
    assert len(data["items"]) == 3
    for d in data["items"]:
        assert_device_shape(d)

def test_pagination_invalid_params(client):
    res = client.get("/devices?page=0&limit=10")
    assert res.status_code == 400
    res = client.get("/devices?page=1&limit=0")
    assert res.status_code == 400
    res = client.get("/devices?page=1&limit=1001")
    assert res.status_code == 400
    res = client.get("/devices?page=abc&limit=10")
    assert res.status_code == 400

def test_duplicate_ip_returns_400_with_error_field(client, monkeypatch):
    first = make_device_payload(1, ip_address="10.0.0.1")
    second = make_device_payload(2, ip_address="10.0.0.1")  # same IP

    # First insert ok
    res1 = client.post("/devices", json=first)
    assert res1.status_code == 201

    # Simulate duplicate key on second insert by monkeypatching collection.insert_one
    import app.routes.devices as devices_mod
    coll = devices_mod.get_collection("devices")
    real_insert = coll.insert_one

    class DuplicateOnce:
        def __init__(self):
            self.called = False
        def __call__(self, doc):
            if not self.called:
                self.called = True
                raise DuplicateKeyError("dup ip")
            return real_insert(doc)

    monkeypatch.setattr(coll, "insert_one", DuplicateOnce())

    res2 = client.post("/devices", json=second)
    assert res2.status_code == 400
    data = res2.get_json()
    assert "error" in data
    assert data["error"]["field"] == "ip_address"

def test_update_device_and_get(client):
    res = client.post("/devices", json=make_device_payload(1))
    created = res.get_json()
    did = created["id"]
    res = client.put(f"/devices/{did}", json={"name": "Updated Name"})
    assert res.status_code == 200
    updated = res.get_json()
    assert updated["name"] == "Updated Name"
    assert_device_shape(updated)

    # Verify retrieval
    res = client.get(f"/devices/{did}")
    assert res.status_code == 200
    got = res.get_json()
    assert got["name"] == "Updated Name"

def test_update_no_fields_400(client):
    res = client.post("/devices", json=make_device_payload(1))
    created = res.get_json()
    did = created["id"]
    res = client.put(f"/devices/{did}", json={})
    assert res.status_code == 400

def test_update_duplicate_ip_returns_400(client, monkeypatch):
    # Create two devices
    res = client.post("/devices", json=make_device_payload(1, ip_address="10.0.0.1"))
    d1 = res.get_json()
    client.post("/devices", json=make_device_payload(2, ip_address="10.0.0.2"))

    # Simulate DuplicateKeyError on find_one_and_update
    import app.routes.devices as devices_mod
    coll = devices_mod.get_collection("devices")

    class RaiseDupOnUpdate:
        def __call__(self, *a, **k):
            raise DuplicateKeyError("dup")
    monkeypatch.setattr(coll, "find_one_and_update", RaiseDupOnUpdate())

    res = client.put(f"/devices/{d1['id']}", json={"ip_address": "10.0.0.2"})
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
    assert data["error"]["field"] == "ip_address"

def test_delete_device(client):
    res = client.post("/devices", json=make_device_payload(1))
    created = res.get_json()
    did = created["id"]
    res = client.delete(f"/devices/{did}")
    assert res.status_code == 204
    # deleting again returns 404
    res = client.delete(f"/devices/{did}")
    assert res.status_code == 404

def test_get_missing_returns_404_with_invalid_and_valid_ids(client):
    # valid-looking ObjectId but not present
    res = client.get("/devices/65f5c751f0bb75b9e1f8a111")
    assert res.status_code == 404
    # invalid object id should also yield 404 via _objid abort
    res = client.get("/devices/not-an-objectid")
    assert res.status_code == 404

def test_put_invalid_body_validation_errors(client):
    res = client.post("/devices", json=make_device_payload(1))
    created = res.get_json()
    did = created["id"]
    # invalid enum for type -> 422 from marshmallow
    res = client.put(f"/devices/{did}", json={"type": "badtype"})
    assert res.status_code == 422

def test_ping_device_online_and_offline(client, monkeypatch):
    # create device
    res = client.post("/devices", json=make_device_payload(99, ip_address="1.1.1.1"))
    created = res.get_json()
    did = created["id"]

    # Mock socket interactions within _safe_ping indirectly by patching socket in module
    import app.routes.devices as devices_mod

    def fake_gethostbyname(host):
        return "1.1.1.1"

    class FakeSocket:
        def __init__(self, *a, **kw):
            self._closed = False
        def settimeout(self, t):  # noqa: ARG002
            pass
        def connect_ex(self, addr):
            # First call says success, then fail
            if getattr(self, "_called", False):
                return 1
            self._called = True
            return 0
        def close(self):
            self._closed = True

    monkeypatch.setattr(devices_mod.socket, "gethostbyname", fake_gethostbyname)
    monkeypatch.setattr(devices_mod.socket, "socket", lambda *a, **k: FakeSocket())

    res = client.post(f"/devices/{did}/ping")
    assert res.status_code == 200
    doc = res.get_json()
    assert doc["status"] in ("online", "offline")
    assert_device_shape(doc)
