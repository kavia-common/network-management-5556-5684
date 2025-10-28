# Backend GET /devices Content-Type Checklist

- Ensure the GET /devices endpoint responds with:
  - Status: 200
  - Header: Content-Type: application/json; charset=utf-8
  - Body: JSON envelope { "items": [...], "total": number, "page": number, "limit": number }

Implementation guidance (Flask):
- If using Flask directly, set:
    from flask import jsonify, make_response
    resp = make_response(jsonify(payload), 200)
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    return resp

- If using Flask-RESTful Resource with marshaling or returning dicts, Flask typically sets application/json automatically. Verify explicitly by checking response headers in logs or tests.

- For OPTIONS/204 responses, it's acceptable to have no body. For non-JSON responses, set appropriate Content-Type.

Diagnostics:
- Log the following on each GET /devices call:
  - Computed page/limit
  - Returned items count and total
  - Content-Type header value
