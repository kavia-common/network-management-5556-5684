BackendAPIService test suite

How to run:
- From BackendAPIService directory:
  pip install -r requirements.txt
  pytest -q

Notes:
- Tests stub MongoDB calls using monkeypatch and a FakeCollection; no live DB required.
- Flask app is assembled inside the app fixture using flask-smorest blueprints from app.routes.
- Endpoints covered: /devices CRUD+ping and /, /health/db, /health/devices-summary.
