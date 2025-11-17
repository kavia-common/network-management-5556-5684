import pytest
from marshmallow import ValidationError
from app.schemas import _ipv4_validator, DeviceCreateSchema, DeviceUpdateSchema

def test_ipv4_validator_valid_values():
    for ip in ["0.0.0.0", "127.0.0.1", "192.168.100.200", "255.255.255.255"]:
        _ipv4_validator(ip)

@pytest.mark.parametrize(
    "ip",
    [
        "256.1.1.1",
        "1.256.1.1",
        "1.1.256.1",
        "1.1.1.256",
        "1.1.1",
        "1.1.1.1.1",
        "a.b.c.d",
        "1.1.1.-1",
        "",
        "  ",
    ],
)
def test_ipv4_validator_rejects_bad_inputs(ip):
    with pytest.raises(ValidationError):
        _ipv4_validator(ip)

def minimal_payload(**overrides):
    data = {
        "name": "r1",
        "ip_address": "10.0.0.1",
        "type": "router",
        "location": "dc1",
        "status": "unknown",
    }
    data.update(overrides)
    return data

def test_device_create_schema_success():
    payload = minimal_payload()
    data = DeviceCreateSchema().load(payload)
    assert data["ip_address"] == "10.0.0.1"

@pytest.mark.parametrize("missing", ["name", "ip_address", "type", "location", "status"])
def test_device_create_missing_required(missing):
    payload = minimal_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        DeviceCreateSchema().load(payload)

@pytest.mark.parametrize("field,value", [
    ("type", "firewall"),
    ("status", "bogus"),
])
def test_device_create_bad_enums(field, value):
    payload = minimal_payload(**{field: value})
    with pytest.raises(ValidationError):
        DeviceCreateSchema().load(payload)

def test_device_update_schema_allows_partial_valid():
    data = DeviceUpdateSchema().load({"name": "x"})
    assert data["name"] == "x"

@pytest.mark.parametrize("field,value", [
    ("type", "notatype"),
    ("status", "notastatus"),
])
def test_device_update_schema_bad_enums(field, value):
    with pytest.raises(ValidationError):
        DeviceUpdateSchema().load({field: value})

def test_device_update_schema_bad_ip():
    with pytest.raises(ValidationError):
        DeviceUpdateSchema().load({"ip_address": "999.0.0.1"})
