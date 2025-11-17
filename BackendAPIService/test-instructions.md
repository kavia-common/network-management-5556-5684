# Test and Coverage Instructions

Prerequisites:
- cd network-management-5556-5684/BackendAPIService
- python -m venv .venv && source .venv/bin/activate
- pip install -r requirements.txt

Run tests (with coverage via pytest.ini):
- pytest

Coverage via coverage.py with HTML:
- coverage erase
- PYTHONPATH=. coverage run --source=app -m pytest
- coverage report -m
- coverage html -d htmlcov
- Open htmlcov/index.html

Makefile shortcuts:
- make test
- make coverage
- make coverage-html

Notes:
- mongomock is used to mock MongoDB, no external DB needed.
- Socket calls in ping endpoint are mocked in tests.
- Coverage global threshold is fail_under=90% (see .coveragerc).
