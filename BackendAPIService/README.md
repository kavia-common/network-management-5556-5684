# BackendAPIService

Flask-based Backend API for Network Device Management.

This service integrates with MongoDB via `pymongo` and exposes REST APIs (flask-smorest). This document covers environment variables, MongoDB configuration, and available endpoints.

## Requirements

- Python 3.10+
- MongoDB instance accessible to the service
- Environment variables configured (see below)

Install dependencies:

```
pip install -r requirements.txt
```

Note: The app loads variables from a `.env` file automatically using `python-dotenv` if present.

## Environment Variables

Preferred single-URI configuration:
- MONGODB_URI (preferred)
  - MongoDB connection URI. Defaults to `mongodb://localhost:27017/network_devices` if not provided.
  - Example: `mongodb://localhost:27017/network_devices` or `mongodb+srv://<user>:<pass>@cluster0.mongodb.net/<db>`

Fallback individual settings (used only if MONGODB_URI is not set):
- MONGODB_HOST (default: `localhost`)
- MONGODB_PORT (default: `27017`)
- MONGODB_USERNAME (optional)
- MONGODB_PASSWORD (optional)
- MONGODB_OPTIONS (optional, query string without leading `?`, e.g. `replicaSet=rs0&authSource=admin`)

Common settings:
- MONGODB_DB_NAME (optional, default: `network_devices`)
- MONGODB_COLLECTION (optional, default: `device`) — collection used by the app; indexes are created here
- MONGODB_TLS (optional, `true` enables TLS)
- MONGODB_CONNECT_TIMEOUT_MS (optional, default: `5000`)

Example `.env` content (see `.env.example` for a ready-to-copy template):

```
# Preferred
MONGODB_URI=mongodb://localhost:27017/network_devices
MONGODB_DB_NAME=network_devices
MONGODB_COLLECTION=device
MONGODB_TLS=false
MONGODB_CONNECT_TIMEOUT_MS=5000

# Or construct from parts (if MONGODB_URI is not provided)
# MONGODB_HOST=localhost
# MONGODB_PORT=27017
# MONGODB_USERNAME=
# MONGODB_PASSWORD=
# MONGODB_OPTIONS=
```

Note: Do not commit your real `.env` file. Provide environment variables via your deployment system.

## Database and Indexes

On startup, the app initializes a singleton `MongoClient`, verifies connectivity using `admin.command('ping')`, and ensures indexes on the `device` collection (or collection specified via `MONGODB_COLLECTION`):

- Unique index on `ip_address` (name: `uniq_ip`)
- Index on `type` (name: `idx_type`)
- Index on `status` (name: `idx_status`)

## Using the DB helpers in code

The `app/db.py` module exposes the following functions:

- get_client(): returns the singleton `MongoClient`
- get_db(): returns the configured `Database` instance
- get_collection(name): returns a `Collection` by name
- ping(): returns `(bool_ok, error_message_or_none)` for health checks

Example usage within a route:

```python
from app.db import get_collection

devices = get_collection("devices")
device = devices.find_one({"ip_address": "192.168.1.10"})
```

## Endpoints

- GET `/` — Health check
- GET `/health/db` — Database health (pings MongoDB, returns {"status":"ok"} or {"status":"error","message":"..."})
- GET `/devices` — List devices
  - Optional query params: `page` (1-based), `limit` (default 10, max 1000)
  - If `page` or `limit` provided: returns `{ items, total, page, limit }`
  - Otherwise: returns full array `[]`
- POST `/devices` — Create a device
  - Body: `{ name, ip_address (IPv4), type (router|switch|server), location, status (online|offline|unknown) }`
  - On duplicate `ip_address`: `400` with `{ "error": { "field": "ip_address", "message": "already exists" } }`
- GET `/devices/{id}` — Retrieve a device by id
- PUT `/devices/{id}` — Update fields of a device (all optional)
  - Same validation rules as create; uniqueness enforced on `ip_address`
- DELETE `/devices/{id}` — Delete a device
- POST `/devices/{id}/ping` — Perform a safe reachability check
  - Non-privileged approach (DNS resolve + short TCP connect to 80/443)
  - Updates `status` and `last_checked` timestamp

All device responses map Mongo `_id` to `id` and include `created_at`, `updated_at`, and `last_checked` (nullable).

## Running the app

Development:

1) Configure environment
   - Copy `.env.example` to `.env` and fill in values (prefer MONGODB_URI).

2) Install dependencies
```
pip install -r requirements.txt
```

3) Start server
```
export FLASK_APP=run.py
export FLASK_ENV=development
python run.py
```

Preview links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

The generated OpenAPI JSON file is also written to `interfaces/openapi.json`. To regenerate from the running app context:
```
python BackendAPIService/generate_openapi.py
```

## Verify MongoDB health

- Ensure MongoDB is reachable at your MONGODB_URI.
- Start the API as above.
- Test the DB health endpoint:
  - curl: `curl -s http://localhost:3001/health/db`
  - Expected response: `{"status":"ok"}` when the database is reachable.
  - On failure, you'll get: `{"status":"error","message":"<details>"}` with HTTP 500.

## Acceptance Criteria Mapping

- Backend reads MongoDB settings from env vars and connects on startup: Implemented in `app/db.py` with `MONGODB_URI` preferred and fallbacks; `.env` auto-loaded via `python-dotenv`.
- Default DB name `network_devices` (or provided DB name): Implemented via DEFAULT_DB_NAME and usage.
- Indexes created on `ip_address` (unique), `type`, `status`: Ensured in `_ensure_indexes`.
- Graceful error handling and clear logs if connection fails: `get_client` raises `RuntimeError` with details; health endpoint surfaces errors.
- Health endpoint `/health/db`: Implemented in `app/routes/health.py` returning {"status":"ok"} or {"status":"error","message":"..."} with appropriate HTTP status.
- Env vars documented and `.env.example` updated: Provided above.
