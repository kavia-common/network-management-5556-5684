# BackendAPIService

Flask-based Backend API for Network Device Management.

This service integrates with MongoDB via `pymongo` and exposes REST APIs (flask-smorest). This document covers environment variables, MongoDB configuration (Atlas-ready), CORS configuration, and available endpoints.

Preview note:
- The API now starts even if `MONGODB_URI` is missing. MongoDB initialization is deferred until first database access. Use `/health` and `/health/db` for diagnostics. If `MONGODB_URI` is present but invalid, errors are logged and surfaced via health endpoints, but startup will not crash.

## Requirements

- Python 3.10+
- MongoDB instance accessible to the service (MongoDB Atlas recommended)
- Environment variables configured (see below)

Install dependencies:

```
pip install -r requirements.txt
```

Note: The app loads variables from a `.env` file automatically using `python-dotenv` if present.
A default `.env` is provided with a safe placeholder for `MONGODB_URI` (local connection).

## Environment Variables

Preferred single-URI configuration:
- MONGODB_URI (preferred)
  - MongoDB connection URI. Works with Atlas `mongodb+srv://` or standard `mongodb://`.
  - Example (Local): `mongodb://localhost:27017/network`
  - Example (Atlas): `mongodb+srv://<user>:<pass>@cluster0.mongodb.net/network?retryWrites=true&w=majority&appName=myapp`
  - If your URI includes a database path segment (e.g., `/network`), that DB will be used unless you explicitly set MONGODB_DB_NAME to override it.

Common settings:
- MONGODB_DB_NAME (optional, default: `network`)
  - Overrides the database name even if the MONGODB_URI contains a DB path.
- MONGODB_COLLECTION (optional, default: `device`) — collection used by the app; indexes are created here
- MONGODB_TLS (optional, `true` enables TLS)
- MONGODB_CONNECT_TIMEOUT_MS (optional, default: `5000`)

Fallback individual settings (used only if MONGODB_URI is not set and at least one part is provided):
- MONGODB_HOST (default: `localhost`)
- MONGODB_PORT (default: `27017`)
- MONGODB_USERNAME (optional)
- MONGODB_PASSWORD (optional)
- MONGODB_OPTIONS (optional, query string without leading `?`, e.g. `replicaSet=rs0&authSource=admin`)

## CORS / Frontend integration

CORS is provided via `flask-cors` and is initialized in `app/__init__.py`. It permits requests from your frontend origin and handles preflight (OPTIONS) automatically.

Environment variables (priority order):
1) BACKEND_CORS_ORIGINS — comma-separated list of allowed origins.
   - Example: `BACKEND_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"`
2) FRONTEND_ORIGIN — single allowed origin.
   - Example: `FRONTEND_ORIGIN="http://localhost:3000"`
3) FRONTEND_ORIGIN_ALLOWLIST or CORS_ALLOWED_ORIGINS — legacy comma-separated allowlist.

If none are set, default is `http://localhost:3000`.

Behavior:
- Allowed methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
- Allowed headers: Content-Type, Authorization, X-Requested-With
- Exposed headers: Content-Type, Content-Length, X-Request-Id
- Credentials: `CORS_SUPPORTS_CREDENTIALS` (default false). Set to `true` only if you intend to use cookies and configure your frontend to send credentials.

Notes:
- Preflight (OPTIONS) will succeed across all routes.
- Health and API routes are covered by a global CORS resource rule (`/*`).
- For production, set explicit origins rather than using wildcards.

Example `.env` content (see `.env.example` for a ready-to-copy template):

```
# Flask
FLASK_ENV=development
FLASK_DEBUG=1
PORT=3001

# MongoDB (Atlas-ready)
MONGODB_URI="mongodb+srv://db_user:vettel%402012@cluster0.htz84wq.mongodb.net/network?retryWrites=true&w=majority&appName=Cluster0"
MONGODB_DB_NAME="network_devices"

# CORS: allow all origins for development/preview
ALLOWED_ORIGINS="*"

# Optional extras
# MONGODB_COLLECTION=device
# MONGODB_CONNECT_TIMEOUT_MS=5000
# CORS_SUPPORTS_CREDENTIALS=false
```

Migration note:
- Previous default database name was `network_devices`. Existing data will remain there.
- Switching the default to `network` means you may see empty data unless you migrate documents from `network_devices` to `network`.
- You can continue to use the old database by setting `MONGODB_DB_NAME=network_devices`, or include `/network_devices` in your MONGODB_URI.

Important:
- If FRONTEND_ORIGIN_ALLOWLIST is already set in your environment, append `http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000` and `https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000` to the comma-separated list instead of replacing existing entries.
- After changing environment variables, you MUST restart the backend service (stop and start your preview) so the new CORS settings take effect. Flask does not automatically reload environment variable changes.

Note:
- Do not commit your real `.env` file. Provide environment variables via your deployment system.
- If your platform exposes variables with REACT_APP_* prefix (e.g., `REACT_APP_MONGODB_URI` or `REACT_APP_MONGODB_DB_NAME`),
  the backend will automatically map them to MONGODB_* counterparts if the direct vars are not set.

## Database and Indexes

The app initializes a singleton `MongoClient` lazily on first database access. When configured and reachable, it verifies connectivity using `admin.command('ping')` and ensures indexes on the `device` collection (or collection specified via `MONGODB_COLLECTION`):

Migration note:
- The default database name has changed from `network_devices` to `network`.
- Existing data remains in `network_devices`. If you switch to the new default, your app will start with an empty dataset unless you migrate.
- To continue using your existing data without migration, set `MONGODB_DB_NAME=network_devices` or include `/network_devices` in `MONGODB_URI`.

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
- GET `/health/db` — Database health (pings MongoDB, returns {"status":"ok"} or {"status":"error","message":"..."})
- GET `/devices` — List devices
  - Optional query params: `page` (1-based), `limit` (default 10, max 1000)
  - If `page` or `limit` provided: returns `{ items, total, page, limit }`
  - Otherwise: returns full array `[]`
- POST `/devices` — Create a device
  - Body: `{ name, ip_address (IPv4), type (router|switch|server), location, status (online|offline|unknown) }`
  - On validation error: `400` with `{"status":"Bad Request","message":"Validation failed","errors":{...}}`
  - On duplicate `ip_address`: `409` with `{ "error": { "field": "ip_address", "message": "already exists" } }`
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
   - Optionally set `FRONTEND_ORIGIN_ALLOWLIST` to include your preview/dev host (e.g., http://localhost:3000).
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

## Troubleshooting CORS and Fetch Failures

If OPTIONS preflight succeeds but actual GET/POST fails with a "Network error" in the frontend:

- Ensure your frontend origin exactly matches an allowed origin (scheme + host + port).
  - Defaults include:
    - http://localhost:3000
    - http://127.0.0.1:3000
    - http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000
    - http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001
    - https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000
    - https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3000
    - https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001
- CORS headers are applied to all responses (GET/POST and errors), not just OPTIONS, via flask-cors.
- The app sets `app.url_map.strict_slashes = False`, so `/devices` will not redirect to `/devices/` (avoids 301/308 responses that may drop CORS headers).
- The `/devices` handler and error paths always return `Content-Type: application/json; charset=utf-8`.
- Credentials:
  - `CORS_SUPPORTS_CREDENTIALS` is `false` by default. If your frontend uses `credentials: 'omit'`, keep it false.
  - If you need cookie-based auth, set `CORS_SUPPORTS_CREDENTIALS=true` and update your frontend fetch to include credentials.

Quick reproduction from your browser console:

fetch('https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001/health/db', { method: 'GET', credentials: 'omit' })
  .then(r => { console.log('status', r.status); for (const [k,v] of r.headers) console.log(k, v); return r.json(); })
  .then(j => console.log(j))
  .catch(e => console.error('network error', e));

fetch('https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001/devices', { method: 'GET', credentials: 'omit' })
  .then(r => { console.log('status', r.status); for (const [k,v] of r.headers) console.log(k, v); return r.json(); })
  .then(j => console.log(j))
  .catch(e => console.error('network error', e));

If you still see errors:
- Confirm there is no HTTP→HTTPS or path redirect.
- Verify your environment variable `CORS_ALLOWED_ORIGINS` (or `FRONTEND_ORIGIN_ALLOWLIST`) includes the exact frontend origin.
- Restart the backend after changing environment variables.

### CORS diagnostics and reproduction
- Ensure your frontend origin exactly matches one in the allowlist (scheme + host + port). Defaults now include:
  - https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3000
- The server sets `app.url_map.strict_slashes = False`, so it will not redirect `/devices` to `/devices/` (avoids 301/308 without CORS headers).
- Test from the browser console:
  fetch('https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001/health/db', { method: 'GET', credentials: 'omit' })
    .then(r => { console.log('status', r.status); for (const [k,v] of r.headers) console.log(k, v); return r.json(); })
    .then(j => console.log(j))
    .catch(e => console.error('network error', e));

  fetch('https://vscode-internal-28439-beta.beta01.cloud.kavia.ai:3001/devices', { method: 'GET', credentials: 'omit' })
    .then(r => { console.log('status', r.status); for (const [k,v] of r.headers) console.log(k, v); return r.json(); })
    .then(j => console.log(j))
    .catch(e => console.error('network error', e));
```
python BackendAPIService/generate_openapi.py
```

## Verify MongoDB health

- Start the API as above (it will start even without DB configured).
- General health endpoint:
  - curl: `curl -s http://localhost:3001/health`
  - Response examples:
    - `{"status":"ok","db_status":"unconfigured","db_message":"..."}` when no DB configured
    - `{"status":"ok","db_status":"ok"}` when DB reachable
    - `{"status":"ok","db_status":"error","db_message":"..."}` when configured but failing
- DB-specific endpoint:
  - curl: `curl -s http://localhost:3001/health/db`
  - Always 200. When successful: `{"status":"ok","db_status":"ok","server":{"ok":1.0}}`
  - When unconfigured or failing: `{"status":"ok","db_status":"unconfigured|error","message":"<details> | target=mongodb://*** ..."}`
    Target fields are masked to avoid leaking credentials and include effective TLS and timeout values.

## Acceptance Criteria Mapping

- Backend reads MongoDB settings from env vars and connects on startup or first use: Implemented in `app/db.py` with `MONGODB_URI` preferred and fallbacks; `.env` auto-loaded via `python-dotenv`.
- If `MONGODB_DB_NAME` provided, it is used: Supported by `DEFAULT_DB_NAME` override and client setup.
- Graceful error handling and clear logs if connection fails: `get_client` raises `RuntimeError` with details; health endpoint surfaces errors.
- Health endpoint `/health/db`: Implemented in `app/routes/health.py` returning {"status":"ok"} or {"status":"error","message":"..."} with appropriate HTTP status.
- Env vars documented and `.env.example` added: Provided above; includes Atlas guidance.
- CORS enabled and configurable via env: Implemented in `app/__init__.py` using `flask-cors` with FRONTEND_ORIGIN_ALLOWLIST allowlist and secure defaults.
