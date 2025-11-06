# Network Management Backend (Flask)

This workspace hosts the Backend API Service for the network management project.

Quick links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

Setup:
1) Create and configure environment variables
   - Copy BackendAPIService/.env.example to BackendAPIService/.env
   - Ensure MONGODB_URI is set to a reachable MongoDB instance (e.g., mongodb://localhost:27017/network). The backend will fail fast at startup if this is missing or invalid.
   - Configure CORS to match your frontend origin:
       Preferred (comma-separated): BACKEND_CORS_ORIGINS="http://localhost:3000"
       Or single: FRONTEND_ORIGIN="http://localhost:3000"
       Legacy supported: FRONTEND_ORIGIN_ALLOWLIST / CORS_ALLOWED_ORIGINS
     If none are set, default is http://localhost:3000. Set CORS_SUPPORTS_CREDENTIALS=true only if you intend to use cookies.

2) Install dependencies
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the app
   python run.py
   The API will listen on http://localhost:3001 (Flask default development server).