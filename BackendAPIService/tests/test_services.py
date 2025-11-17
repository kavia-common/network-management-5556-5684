from datetime import datetime
import re

def test_safe_ping_online(monkeypatch):
    # Patch socket for online simulation
    import app.routes.devices as devices_mod

    def fake_gethostbyname(host):
        assert isinstance(host, str)
    class FakeSocket:
        def __init__(self, *a, **k):
            self.calls = 0
        def settimeout(self, t):  # noqa: ARG002
            pass
        def connect_ex(self, addr):
            self.calls += 1
            return 0  # success immediately
        def close(self):
            pass
    monkeypatch.setattr(devices_mod.socket, "gethostbyname", fake_gethostbyname)
    monkeypatch.setattr(devices_mod.socket, "socket", lambda *a, **k: FakeSocket())
    status, last = devices_mod._safe_ping("8.8.8.8")
    assert status == "online"
    assert isinstance(last, datetime)

def test_safe_ping_offline_due_to_dns(monkeypatch):
    import app.routes.devices as devices_mod
    def fake_gethostbyname(host):
        raise OSError("dns fail")
    monkeypatch.setattr(devices_mod.socket, "gethostbyname", fake_gethostbyname)
    status, last = devices_mod._safe_ping("bad.host")
    assert status == "offline"
    assert isinstance(last, datetime)

def test_serialize_device_and_devices():
    from app.schemas import serialize_device, serialize_devices
    doc = {
        "_id": "65f5c751f0bb75b9e1f8a111",
        "name": "n1",
        "ip_address": "1.2.3.4",
        "type": "router",
        "location": "x",
        "status": "unknown",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_checked": None,
    }
    out = serialize_device(doc)
    assert out["id"] == "65f5c751f0bb75b9e1f8a111"
    assert re.search(r"\\d{4}-\\d{2}-\\d{2}T", out["created_at"])
    many = serialize_devices([doc])
    assert isinstance(many, list) and many and many[0]["id"] == out["id"]
