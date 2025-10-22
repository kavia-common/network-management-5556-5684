# BackendAPIService - Network Device Management

Flask REST API for managing network devices with MongoDB persistence. Features:
- CRUD for devices
- Unique IP address constraint
- Indexes on `type` and `status`
- Optional ping status check
- Environment-based configuration
- OpenAPI docs via Flask-Smorest at `/docs`

## Quick Start

1. Create and configure your environment file:
```
cp .env.example .env
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Ensure MongoDB is running and accessible via `MONGODB_URI`.

4. Run the server:
```
python -m app.main
```
Server listens on `PORT` (default: 3001).

Docs available at: `http://localhost:3001/docs`

## Environment Variables

- FLASK_ENV: development|production (default: production)
- FLASK_DEBUG: 1/0 (default: 0)
- PORT: Port for the HTTP server (default: 3001)
- API_TITLE: API title (default: Network Device Management API)
- API_VERSION: API version string (default: v1)
- MONGODB_URI: MongoDB connection URI (default: mongodb://localhost:27017)
- MONGODB_DB_NAME: Database name (default: network_devices)
- MONGODB_TLS: 1/0 enable TLS (default: 0)
- MONGODB_USER: Optional username if not included in URI
- MONGODB_PASSWORD: Optional password if not included in URI
- PING_TIMEOUT_MS: Ping timeout in milliseconds (default: 2000)

See `.env.example` for a sample configuration.

## Data Model

Collection: `devices`

Fields:
- _id: ObjectId
- name: string (required)
- ip_address: string (required, unique, IPv4)
- type: string (required; enum: router|switch|server)
- location: string (required)
- status: string (required; enum: online|offline|unknown)
- last_checked: datetime (updated on ping)
- created_at: datetime
- updated_at: datetime

Indexes:
- Unique: `ip_address`
- Non-unique: `type`, `status`

## API Endpoints

- GET `/` Health check
- GET `/devices` List devices (filters: `type`, `status`)
- POST `/devices` Create device
- GET `/devices/<id>` Retrieve device
- PUT `/devices/<id>` Update device (any subset of fields)
- DELETE `/devices/<id>` Delete device
- POST `/devices/<id>/ping` Ping device; updates `status` and `last_checked`

Responses include ISO8601 timestamps and `_id` as a string. Error responses are structured with fields: `code`, `status`, `message`, `errors`.

## Error Handling

- 400 Validation or invalid id
- 404 Not found
- 409 Duplicate IP address
- 500 Database or unexpected errors

## Notes

- On first connection, indexes are created automatically.
- If DB connection fails at startup, the app still serves health/docs; DB-related endpoints will return errors until DB is reachable.

## Development

- Run linters/tests using your preferred workflow.
- Extend validation in `app/models/device_schema.py`.
- Database access in `app/db.py`.
- Endpoints in `app/resources/devices.py`.
