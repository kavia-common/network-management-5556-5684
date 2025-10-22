# network-management-5556-5684

This project provides a lightweight web application for managing network devices. The BackendAPIService exposes RESTful APIs with MongoDB integration, validation, and optional ping-based status checks.

Backend docs and API are served from the BackendAPIService container.

## Backend: BackendAPIService

- Framework: Flask with flask-smorest (OpenAPI)
- Database: MongoDB via PyMongo
- Config: Environment variables
- Bind: 0.0.0.0:3001

### Quick Start

1) Prepare environment variables:
   cp BackendAPIService/.env.example BackendAPIService/.env
   # Edit BackendAPIService/.env with your MongoDB URI and DB name

2) Install dependencies:
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the server:
   python run.py
   # Server runs at http://0.0.0.0:3001

4) API Docs:
   - Swagger UI: http://localhost:3001/docs/
   - OpenAPI Spec: http://localhost:3001/openapi.json

### Environment Variables

See BackendAPIService/docs/env.md for detailed documentation.

Required:
- MONGODB_URI
- MONGODB_DB_NAME

Optional:
- MONGODB_TLS
- SERVER_HOST (default 0.0.0.0)
- SERVER_PORT (default 3001)

### Endpoints

- GET  /                 Health
- GET  /docs/            Swagger UI
- GET  /openapi.json     OpenAPI spec

Devices:
- POST   /api/devices
- GET    /api/devices
- GET    /api/devices/<id>
- PUT    /api/devices/<id>
- DELETE /api/devices/<id>
- POST   /api/devices/<id>/ping

Query params for listing:
- page, page_size
- type, status
- q (search by name or ip_address)

### Request Examples

Create:
POST /api/devices
Content-Type: application/json
{
  "name": "Core Switch",
  "ip_address": "192.168.1.10",
  "type": "switch",
  "location": "Data Center A",
  "status": "unknown"
}

Update:
PUT /api/devices/<id>
{
  "name": "Core Switch A",
  "status": "offline"
}

### Behavior Notes

- Unique index on ip_address is enforced; creating/updating to a duplicate IP returns 409 Conflict.
- If ping is not available in the environment, the ping endpoint returns status "unknown" without crashing.
- Consistent JSON error format is used across the API.

### Project Structure (BackendAPIService)

- app/
  - __init__.py           (app factory, API registration, error handlers)
  - config.py             (environment-driven configuration)
  - db.py                 (Mongo client init and indexes)
  - utils.py              (helpers: ObjectId, ping, timestamps)
  - validators.py         (device payload validation)
  - routes/health.py      (health endpoint)
  - resources/device_resource.py (device API endpoints)
  - services/device_service.py   (business logic, CRUD, ping)
  - models/device_schema.py      (schema documentation)
- run.py                  (dev entrypoint, binds 0.0.0.0:3001)
- wsgi.py                 (WSGI entry)
- requirements.txt
- docs/env.md
- .env.example

