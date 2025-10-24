# Network Management Backend (Flask)

This workspace hosts the Backend API Service for the network management project.

Quick links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

Setup:
1) Create and configure environment variables
   - Copy BackendAPIService/.env.example to BackendAPIService/.env
   - Ensure MONGODB_URI is set to a reachable MongoDB instance (or provide fallback parts as documented in BackendAPIService/README.md).
   - Optional vars supported: MONGODB_DB_NAME, MONGODB_TLS, MONGODB_CONNECT_TIMEOUT_MS, MONGODB_COLLECTION
   - Fallback parts (used only when MONGODB_URI is empty): MONGODB_HOST, MONGODB_PORT, MONGODB_USERNAME, MONGODB_PASSWORD, MONGODB_OPTIONS

2) Install dependencies
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the app
   python run.py
   The API will listen on http://localhost:3001 (Flask default development server).

Health checks:
- Service health: GET http://localhost:3001/
- Database health: GET http://localhost:3001/health/db -> {"status":"ok"} when MongoDB is reachable
