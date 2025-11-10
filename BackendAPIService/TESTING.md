# Testing BackendAPIService

Run unit tests with coverage and generate HTML report:

1) Install dev dependencies
   pip install -r requirements.txt

2) Execute tests
   pytest

3) View HTML coverage report
   Open htmlcov/index.html in your browser.

Notes:
- Tests use mongomock to simulate MongoDB in-memory, no external DB required.
- Socket network operations in ping endpoint are mocked to be deterministic.
