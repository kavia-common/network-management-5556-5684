# Environment Variables

The Backend API Service is configured entirely via environment variables.

Modes:
- DB_MODE: 'mongo' (default) or 'memory'
  - mongo: Uses MongoDB via PyMongo.
  - memory: Uses an in-memory repository with no persistence.
  - If DB_MODE='mongo' but MongoDB is not configured or connection fails, the app automatically falls back to 'memory' and logs a warning.

Required when DB_MODE='mongo':
- MONGODB_URI: MongoDB connection string. Example: mongodb+srv://user:pass@cluster0.example.mongodb.net/?retryWrites=true&w=majority
- MONGODB_DB_NAME: MongoDB database name. Example: network_devices

Optional:
- MONGODB_TLS: "true" or "false". Overrides TLS behavior regardless of URI.
- SERVER_HOST: Server bind host. Default: 0.0.0.0
- SERVER_PORT: Server port. Default: 3001

Notes:
- Unique constraint on devices.ip_address is enforced in both modes.
- Indexes for type and status are created in MongoDB mode.
- If the environment does not allow ping, the status endpoint will return "unknown" without failing.
- Health endpoint /health returns {"status":"ok","db_mode":"memory|mongo"}.

Examples:
- Memory mode (no .env required):
  DB_MODE=memory

- Mongo mode:
  DB_MODE=mongo
  MONGODB_URI=mongodb+srv://user:pass@cluster.example.mongodb.net/?retryWrites=true&w=majority
  MONGODB_DB_NAME=network_devices
