# BackendAPIService - Network Device Management API

A Flask-based REST API for managing network devices with MongoDB storage. Provides CRUD operations and an optional reachability check (ping). Ships with OpenAPI docs at /docs.

## Features
- CRUD for devices: name, ip_address, type (router|switch|server), location, status (online|offline|unknown)
- Unique constraint on ip_address; indexes on type and status
- Optional ping endpoint to test reachability and update status
- Consistent JSON responses: { data, message, error }
- CORS enabled
- Environment-based configuration

## Requirements
- Python 3.10+
- MongoDB instance reachable via connection string
- pip

## Setup

1. Create and configure environment variables:
   - Copy .env.example to .env and update as needed.
   ```
   cp .env.example .env
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the service:
   ```
   python run.py
   ```
   By default the app binds to 0.0.0.0:3001. Configure via APP_HOST and APP_PORT.

4. Open API docs:
   - Swagger UI: http://localhost:3001/docs
   - OpenAPI JSON: http://localhost:3001/openapi.json

## Environment Variables

- MONGODB_URI (required): MongoDB connection string.
- MONGODB_DB_NAME (required): Database name (e.g., network_devices).
- MONGODB_TLS (optional): true/false to enable TLS/SSL, default false.
- APP_HOST (optional): Host to bind, default 0.0.0.0.
- APP_PORT (optional): Port to bind, default 3001.

See .env.example for a template.

## Data Validation

Required fields on create:
- name: non-empty string
- ip_address: IPv4 address (v4 only)
- type: one of router, switch, server
- location: non-empty string
- status: one of online, offline, unknown

On update (PUT), validation applies only to fields provided.

## Indexes

On startup (on first collection access), the following indexes are created:
- Unique index on ip_address
- Index on type
- Index on status

## Endpoints

- GET /           - Health check
- POST /devices   - Create device
- GET /devices    - List devices
- GET /devices/<id> - Get device by id
- PUT /devices/<id> - Update device by id (partial accepted)
- DELETE /devices/<id> - Delete device by id
- POST /devices/<id>/ping - Reachability check; updates last_checked and status

Response shape:
```
{ "data": <payload_or_null>, "message": "<text>", "error": <object_or_null> }
```

## Notes on Ping

The ping endpoint attempts ICMP using the system `ping` command. If unavailable or blocked, it falls back to attempting a TCP connection to port 80. No elevated privileges are required.

## Development

- Entry point: app/__init__.py (Flask app factory)
- Resources: app/resources/devices.py
- Database: app/db.py (PyMongo connection, indexes)
- Validation: app/models/validators.py
- Utilities: app/utils/ping.py

## License

MIT
