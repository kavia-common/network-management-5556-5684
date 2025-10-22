# Environment Variables

The Backend API Service is configured entirely via environment variables.

Required:
- MONGODB_URI: MongoDB connection string. Example: mongodb+srv://user:pass@cluster0.example.mongodb.net/?retryWrites=true&w=majority
- MONGODB_DB_NAME: MongoDB database name. Example: network_devices

Optional:
- MONGODB_TLS: "true" or "false". Overrides TLS behavior regardless of URI.
- SERVER_HOST: Server bind host. Default: 0.0.0.0
- SERVER_PORT: Server port. Default: 3001

Notes:
- Unique index on devices.ip_address is created at startup.
- Additional indexes on devices.type and devices.status are also created.
- If the environment does not allow ping, the status endpoint will return "unknown" without failing.
