# FrontendApplication

React-based UI for Network Device Management.

## Environment variables

Create a `.env` file (copy from `.env.example`) and set:

- REACT_APP_API_BASE_URL: Base URL for the backend API (no trailing slash), e.g.:
  - Local dev: `http://localhost:3001`
  - Deployment: set to your backend URL

Important:
- Any change to REACT_APP_* variables requires rebuilding the React app (stop dev server and restart, or re-run the build).

## API client

Use the centralized API client:

```js
import { api } from './src/api/client';

// Examples:
api.get('/devices');
api.post('/devices', { name, ip_address, type, location, status });
api.put(`/devices/${id}`, { name });
api.delete(`/devices/${id}`);
```

The client reads `process.env.REACT_APP_API_BASE_URL`. If it is missing, a console error is logged to help diagnose misconfiguration.

## Development

1) Copy `.env.example` to `.env` and set REACT_APP_API_BASE_URL.
2) Start the dev server (e.g., npm start or your project’s script).
3) If you modify `.env`, stop the dev server and start it again to pick up changes.

No backend URLs are hardcoded in the code; all requests are built from the configured base URL.
