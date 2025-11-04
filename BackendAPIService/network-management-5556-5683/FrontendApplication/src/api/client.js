//
/**
 PUBLIC_INTERFACE
 createApiClient
 Create a simple API client configured with the base URL from REACT_APP_API_BASE_URL.
 Usage:
   import { api } from './api/client';
   api.get('/devices').then(...)

 Notes:
 - Ensure to set REACT_APP_API_BASE_URL in your environment (e.g., http://localhost:3001).
 - Any change to REACT_APP_* variables requires rebuilding the React app.
 */
export function createApiClient(baseUrl) {
  if (!baseUrl) {
    // Surface a clear message during development builds
    // Avoid throwing in production bundle execution if not configured, but log loudly.
    // Callers should handle null and show a friendly error.
    // eslint-disable-next-line no-console
    console.error(
      '[API] Missing REACT_APP_API_BASE_URL. Set it in .env and rebuild the app.'
    );
  }
  // Normalize base: remove any trailing slashes to avoid double slashes when joining with paths
  const normalizedBase = (baseUrl || '').replace(/\/*$/, '');

  async function request(path, options = {}) {
    const url =
      normalizedBase && path
        ? `${normalizedBase}${path.startsWith('/') ? '' : '/'}${path}`
        : path;
    const resp = await fetch(url, {
      // default JSON headers; allow override/merge
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      credentials: 'omit',
      ...options,
    });

    // Try to parse JSON consistently
    const contentType = resp.headers.get('content-type') || '';
    let body = null;
    if (contentType.includes('application/json')) {
      try {
        body = await resp.json();
      } catch (e) {
        body = null;
      }
    } else {
      body = await resp.text().catch(() => null);
    }

    if (!resp.ok) {
      const error = new Error((body && body.message) || 'API request failed');
      error.status = resp.status;
      error.data = body;
      throw error;
    }
    return body;
  }

  return {
    // PUBLIC_INTERFACE
    /** Perform GET request */
    get: (path) => request(path, { method: 'GET' }),
    // PUBLIC_INTERFACE
    /** Perform POST request with JSON body */
    post: (path, data) =>
      request(path, { method: 'POST', body: JSON.stringify(data || {}) }),
    // PUBLIC_INTERFACE
    /** Perform PUT request with JSON body */
    put: (path, data) =>
      request(path, { method: 'PUT', body: JSON.stringify(data || {}) }),
    // PUBLIC_INTERFACE
    /** Perform DELETE request */
    delete: (path) => request(path, { method: 'DELETE' }),
  };
}

// PUBLIC_INTERFACE
// Default API client instance using env var
/** Default API client instance using process.env.REACT_APP_API_BASE_URL */
export const api = createApiClient(process.env.REACT_APP_API_BASE_URL);
