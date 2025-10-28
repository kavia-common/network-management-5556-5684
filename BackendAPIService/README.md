# BackendAPIService

Flask-based Backend API for Network Device Management.

This service integrates with MongoDB via `pymongo` and exposes REST APIs (flask-smorest). This document covers environment variables, MongoDB configuration (Atlas-ready), CORS configuration, and available endpoints.

## Requirements

- Python 3.10+
- MongoDB instance accessible to the service (MongoDB Atlas recommended)
- Environment variables configured (see below)

Install dependencies:

```
pip install -r requirements.txt
```

Note: The app loads variables from a `.env` file automatically using `python-dotenv` if present.

## Environment Variables

Preferred single-URI configuration:
- MONGODB_URI (preferred)
  - MongoDB connection URI. Works with Atlas `mongodb+srv://` or standard `mongodb://`.
  - Example (Local): `mongodb://localhost:27017/network`
  - Example (Atlas): `mongodb+srv://<user>:<pass>@cluster0.mongodb.net/network?retryWrites=true&w=majority&appName=myapp`

Common settings:
- MONGODB_DB_NAME (optional, default: `network`)
- MONGODB_COLLECTION (optional, default: `device`) — collection used by the app; indexes are created here
- MONGODB_TLS (optional, `true` enables TLS)
- MONGODB_CONNECT_TIMEOUT_MS (optional, default: `5000`)

Fallback individual settings (used only if MONGODB_URI is not set and at least one part is provided):
- MONGODB_HOST (default: `localhost`)
- MONGODB_PORT (default: `27017`)
- MONGODB_USERNAME (optional)
- MONGODB_PASSWORD (optional)
- MONGODB_OPTIONS (optional, query string without leading `?`, e.g. `replicaSet=rs0&authSource=admin`)

CORS / Frontend integration:
- FRONTEND_ORIGIN (optional)
  - A single origin allowed to access the API via CORS, e.g. `http://localhost:3000` or `https://<preview-host>:3000`.
  - If not set, development-safe defaults are used: `http://localhost:3000` and preview hosts on port 3000.
- ADDITIONAL_CORS_ORIGINS (optional)
  - Comma-separated list of additional origins to allow.
- Notes:
  - In production, set `FRONTEND_ORIGIN` to your deployed frontend URL to restrict access.
  - CORS is initialized in `app/__init__.py` using `flask-cors`.

Example `.env` content (see `.env.example` for a ready-to-copy template):

```
# Preferred
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster-host>/<db>?retryWrites=true&w=majority&appName=myapp
MONGODB_DB_NAME=network_devices
MONGODB_COLLECTION=device
MONGODB_CONNECT_TIMEOUT_MS=5000

# Optional CORS tightening (recommended for production)
# FRONTEND_ORIGIN=https://my-frontend.example.com
# ADDITIONAL_CORS_ORIGINS=https://admin.example.com,https://staging.example.com

# Or construct from parts (if MONGODB_URI is not provided)
# MONGODB_HOST=localhost
# MONGODB_PORT=27017
# MONGODB_USERNAME=
# MONGODB_PASSWORD=
# MONGODB_OPTIONS=
```

Note:
- Do not commit your real `.env` file. Provide environment variables via your deployment system.
- If your platform exposes variables with REACT_APP_* prefix (e.g., `REACT_APP_MONGODB_URI` or `REACT_APP_MONGODB_DB_NAME`),
  the backend will automatically map them to MONGODB_* counterparts if the direct vars are not set.

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
from app.db import get_collection, DEVICES_COLLECTION

devices = get_collection(DEVICES_COLLECTION)  # uses env MONGODB_COLLECTION (default: "device")
device = devices.find_one({"ip_address": "192.168.1.10"})
```

## Endpoints

- GET `/` — Health check
- GET `/health` — Health check alias (returns 200)
- GET `/health/db` — Database health (pings MongoDB, returns {"status":"ok"} or {"status":"error","message":"..."})
- GET `/health/db-name` — Returns active DB name for quick verification
- GET `/health/devices-summary` — Shows active DB name, collection, count, and sample IDs
- GET `/devices` — List devices
  - Optional query params: `page` (1-based), `limit` (default 10, max 1000)
  - Returns envelope: `{ items, total, page, limit }`
- POST `/devices` — Create a device
  - Body: `{ name, ip_address (IPv4), type (router|switch|server), location, status (online|offline|unknown) }`
  - On validation error: `400` with `{"status":"Bad Request","message":"Validation failed","errors":{...}}`
  - On duplicate `ip_address`: `409` with `{ "error": { "field": "ip_address", "message": "already exists" } }`
- GET `/devices/{id}` — Retrieve a device by id
- PUT `/devices/{id}` — Update fields of a device (all optional)
- DELETE `/devices/{id}` — Delete a device
- POST `/devices/{id}/ping` — Perform a safe reachability check

All device responses map Mongo `_id` to `id` and include timestamps.

## Running the app

Development:

1) Configure environment
   - Copy `.env.example` to `.env` and fill in values (prefer MONGODB_URI).
   - Optionally set `FRONTEND_ORIGIN` to your frontend dev URL (e.g., http://localhost:3000 or your preview host).
   - The backend attempts a MongoDB ping on startup and fails fast if connection is not possible.

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

## Verification checklist (Frontend network error)

1) Backend listening/binding:
   - The server binds to 0.0.0.0:3001 (see run.py). From the frontend host, verify:
     ```
     curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health
     ```
     Expected: `{"message":"Healthy"}` and HTTP 200.

2) CORS allows exact frontend origin:
   - Set FRONTEND_ORIGIN to your exact frontend origin (scheme + host + port). Example for this task:
     ```
     FRONTEND_ORIGIN=http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000
     ```
   - Restart backend and confirm logs show:
     ```
     [Startup][INFO] CORS allowed origins: ['http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000']
     ```
   - Note: If FRONTEND_ORIGIN is not set, dev mode allows "*" which is permissive, but production should set the exact origin.

3) Frontend base URL:
   - Ensure the frontend uses REACT_APP_API_BASE_URL and does not hardcode relative paths.
   - Example:
     ```
     REACT_APP_API_BASE_URL=http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001
     ```
   - Avoid mixed-content: backend is HTTP, so the base URL must be HTTP if the frontend is loaded over HTTP. If the frontend is HTTPS, the backend should also be HTTPS or be proxied to avoid mixed-content browser blocks.

4) Health endpoints:
   - API health: `curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health`
   - DB health: `curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health/db`
   - DB name: `curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health/db-name`
     - Expected: `{"dbName":"network"}` unless overridden by MONGODB_DB_NAME.

5) MongoDB configuration:
   - Default DB name is `network`. To override: set `MONGODB_DB_NAME`.
   - Ensure `MONGODB_URI` points to a reachable instance. On error, `/health/db` returns details with a masked URI and hint.

6) Devices endpoint:
   - Verify listing:
     ```
     curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/devices
     ```
     Expected 200 JSON envelope.

## Acceptance Criteria Mapping

- Backend reads MongoDB settings from env vars and connects on startup or first use: Implemented (`app/db.py`).
- Active DB name defaults to `network`: Implemented (`DEFAULT_DB_NAME="network"`); verify via `/health/db-name`.
- Health endpoints `/health` and `/health/db`: Implemented.
- CORS: Explicit configuration via `FRONTEND_ORIGIN`; production should allow exact origin; dev defaults remain.
- Documentation and verification steps: Provided above.
