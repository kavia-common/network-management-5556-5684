# BackendAPIService

Flask-based Backend API for Network Device Management.

This service integrates with MongoDB via `pymongo` and exposes REST APIs (flask-smorest). This document covers environment variables and MongoDB configuration used by the service.

## Requirements

- Python 3.10+
- MongoDB instance accessible to the service
- Environment variables configured (see below)

Install dependencies:

```
pip install -r requirements.txt
```

## Environment Variables

- MONGO_URI (required)
  - MongoDB connection URI.
  - Example: `mongodb://localhost:27017` or `mongodb+srv://<user>:<pass>@cluster0.mongodb.net`
- MONGO_DB_NAME (optional, default: `network_devices`)
  - Database name to use.
- MONGO_TLS (optional)
  - Set to `true` to enable TLS (`tls=True` passed to MongoClient).
  - Any other value or unset disables TLS.
- MONGO_CONNECT_TIMEOUT_MS (optional)
  - Integer value for MongoClient `connectTimeoutMS`.

Example `.env` content:

```
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=network_devices
MONGO_TLS=false
MONGO_CONNECT_TIMEOUT_MS=10000
```

Note: Do not commit your real `.env` file. Provide environment variables via your deployment system.

## Database and Indexes

On startup (import-time), if `MONGO_URI` is provided, the app initializes a singleton `MongoClient` and ensures indexes on the `devices` collection:

- Unique index on `ip_address` (name: `uniq_ip`)
- Index on `type` (name: `idx_type`)
- Index on `status` (name: `idx_status`)

If `MONGO_URI` is not provided, the application can still start, but any database access will raise a runtime error indicating that `MONGO_URI` is required.

## Using the DB helpers in code

The `app/db.py` module exposes the following functions:

- get_client(): returns the singleton `MongoClient`
- get_db(): returns the configured `Database` instance
- get_collection(name): returns a `Collection` by name

Example usage within a route:

```python
from app.db import get_collection

devices = get_collection("devices")
device = devices.find_one({"ip_address": "192.168.1.10"})
```

## Running the app

Development:

```
export FLASK_APP=run.py
export FLASK_ENV=development
# Ensure MONGO_URI is set in your environment
python run.py
```

The API docs are available under `/docs`.

## Acceptance Criteria Mapping

- Backend starts without errors when `MONGO_URI` provided: Handled by env-driven client in `app/db.py`
- `get_db`/`get_collection` available: Provided in `app/db.py`
- Indexes created on startup: Ensured via import-time initialization and `_ensure_indexes` in `app/db.py`
- Requirements include `pymongo`: Added to `requirements.txt`
- README documents env vars with examples: This document
