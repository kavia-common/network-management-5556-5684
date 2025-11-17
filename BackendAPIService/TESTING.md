# Testing BackendAPIService

Run unit tests with coverage and generate HTML report:

1) Install dev dependencies
   pip install -r requirements.txt

2) Execute tests (with coverage and HTML)
   - Simplest (pytest-cov via pytest.ini):
     pytest
   - Or using coverage CLI directly:
     coverage erase
     PYTHONPATH=. coverage run --source=app -m pytest
     coverage report -m
     coverage html -d htmlcov

3) Makefile shortcuts
   - make test           # pytest -q
   - make coverage       # terminal report
   - make coverage-html  # generates htmlcov/index.html

4) View HTML coverage report
   Open htmlcov/index.html in your browser.

Notes:
- Tests use mongomock to simulate MongoDB in-memory, no external DB required.
- Socket network operations in ping endpoint are mocked to be deterministic.
- Coverage thresholds: global minimum 90% (configured in .coveragerc).
