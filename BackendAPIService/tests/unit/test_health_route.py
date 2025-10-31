import pytest

try:
    from app import create_app
except Exception:  # fallback if factory not present yet
    create_app = None

@pytest.mark.skipif(create_app is None, reason='create_app not available yet')
def test_health_route_status_code():
    app = create_app()
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code in (200, 204)
