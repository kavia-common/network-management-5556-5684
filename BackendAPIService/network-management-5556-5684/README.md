# network-management-5556-5684

This workspace includes a Flask backend service (BackendAPIService) exposing a REST API for network device management with MongoDB persistence.

BackendAPIService:
- API docs available at /docs (OpenAPI via flask-smorest)
- Entrypoints:
  - python BackendAPIService/run.py
  - or from BackendAPIService directory: python -m app.main
- Configure environment via `.env` in BackendAPIService (see `.env.example` for variables)

Key features:
- CRUD endpoints for devices
- Unique index on ip_address; additional indexes on type and status
- Optional device ping to set online/offline status
- Validation for required fields, IPv4 format, and enums (type/status)
- Env-based configuration (MongoDB connection string, TLS, debug, port)
