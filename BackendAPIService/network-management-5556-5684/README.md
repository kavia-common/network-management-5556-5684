# Network Management Backend (Flask)

This workspace hosts the Backend API Service for the network management project.

Quick links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

Setup:
1) Create and configure environment variables
   - Copy BackendAPIService/.env.example to BackendAPIService/.env
   - Ensure MONGODB_URI is set to a reachable MongoDB instance, or rely on the default `mongodb://localhost:27017/network_devices`.
   - Optional:
     - MONGODB_DB_NAME (default: network_devices)
     - MONGODB_COLLECTION (default: device)

2) Install dependencies
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the app
   python run.py
   The API will listen on http://localhost:3001 (Flask default development server).

Health:
- Service: GET /
- Database: GET /health/db -> {"status":"ok"} or {"status":"error","message":"..."}
