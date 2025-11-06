def test_root_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    j = resp.get_json()
    assert j["message"] == "Healthy"


def test_db_health_ok(client, monkeypatch):
    # monkeypatched in conftest(app fixture) to return ok
    resp = client.get("/health/db")
    assert resp.status_code == 200
    j = resp.get_json()
    assert j["status"] == "ok"
    assert "server" in j and "ok" in j["server"]


def test_devices_summary(client, monkeypatch):
    resp = client.get("/health/devices-summary")
    assert resp.status_code == 200
    j = resp.get_json()
    assert "dbName" in j
    assert "collection" in j
    assert "count" in j
    assert isinstance(j["sampleIds"], list)
