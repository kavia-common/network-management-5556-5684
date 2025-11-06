# Network Management Backend (Flask)

This workspace hosts the Backend API Service for the network management project.

Quick links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

Setup:
1) Create and configure environment variables
   - Copy BackendAPIService/.env.example to BackendAPIService/.env
   - Ensure MONGODB_URI is set to a reachable MongoDB instance (e.g., mongodb://localhost:27017/network). If MONGODB_URI does not include a database segment, the backend will use 'network_devices' as fallback only when MONGODB_DB_NAME is provided; otherwise set MONGODB_DB_NAME to override (default app DB is 'network').
   - Configure CORS to match your frontend:
       Preferred: BACKEND_CORS_ORIGINS="http://localhost:3000"
       Or single: FRONTEND_ORIGIN="http://localhost:3000"
       Legacy: FRONTEND_ORIGIN_ALLOWLIST / CORS_ALLOWED_ORIGINS (comma-separated)

2) Install dependencies
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the app
   python run.py
   The API will listen on http://localhost:${PORT:-3001} (reads PORT from environment; defaults to 3001).
