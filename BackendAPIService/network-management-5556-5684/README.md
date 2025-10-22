# network-management-5556-5684

This workspace contains the BackendAPIService for a lightweight network device management application.

- BackendAPIService (Flask): Provides REST API for device CRUD and ping, integrates with MongoDB, and serves OpenAPI docs at /docs.

Folder structure:
- BackendAPIService/
  - app/
    - __init__.py (Flask app factory and API registration)
    - db.py (MongoDB connection and indexes)
    - routes/health.py (Health check)
    - resources/devices.py (Device CRUD and ping endpoints)
    - models/validators.py (Payload validation)
    - utils/ping.py (Reachability checks)
  - run.py (App runner; binds to APP_HOST:APP_PORT)
  - requirements.txt
  - .env.example
  - README.md (service-specific docs)
