# Network Management Backend (Flask)

This workspace hosts the Backend API Service for the network management project.

Quick links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

Setup:
1) Create and configure environment variables
   - Copy BackendAPIService/.env.example to BackendAPIService/.env
   - Ensure MONGODB_URI is set to a reachable MongoDB instance (or set host/port parts).
   - Default DB name is 'network'. To keep using old data in 'network_devices', set MONGODB_DB_NAME=network_devices or include it in your URI.
   - For CORS, ensure FRONTEND_ORIGIN_ALLOWLIST includes your frontend origin. For this environment add: https://vscode-internal-26250-beta.beta01.cloud.kavia.ai:3000
   - After changing environment variables, restart the backend service so new CORS settings apply.

2) Install dependencies
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the app
   python run.py
   The API will listen on http://localhost:3001 (Flask default development server).
