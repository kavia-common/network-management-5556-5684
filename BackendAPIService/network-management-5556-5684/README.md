# Network Management Backend (Flask)

This workspace hosts the Backend API Service for the network management project.

Quick links:
- API base: http://localhost:3001
- API docs (Swagger UI): http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

Setup:
1) Create and configure environment variables
   - Copy BackendAPIService/.env.example to BackendAPIService/.env
   - Ensure MONGODB_URI is set to a reachable MongoDB instance.
   - For frontend integration, set:
     - FRONTEND_ORIGIN to the exact frontend origin (e.g., http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3000)
     - The frontend should set REACT_APP_API_BASE_URL to the backend base URL (e.g., http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001)

2) Install dependencies
   cd BackendAPIService
   pip install -r requirements.txt

3) Run the app
   python run.py
   The API will listen on http://localhost:3001 (Flask dev server bound to 0.0.0.0:3001 via run.py).

Verification:
- Health: curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health
- DB health: curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health/db
- DB name: curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/health/db-name (expected "network" by default)
- Devices: curl -s http://vscode-internal-34539-beta.beta01.cloud.kavia.ai:3001/devices
- CORS: Set FRONTEND_ORIGIN to the exact frontend origin to avoid CORS preflight failures.

Troubleshooting:
- If the browser reports “Network error”:
  - Confirm the backend is reachable from the frontend host via curl to /health.
  - Ensure CORS allows your exact frontend origin (scheme+host+port).
  - Ensure the frontend requests use REACT_APP_API_BASE_URL and not relative paths.
  - Avoid mixed-content: If the frontend runs over HTTPS, proxy the backend or enable HTTPS for the backend.
