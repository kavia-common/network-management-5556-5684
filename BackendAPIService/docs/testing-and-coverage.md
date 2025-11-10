# Backend Testing and Coverage Guide

## Overview
This guide explains how to run all backend tests for the Flask service and how to generate code coverage reports using either pytest-cov or the coverage CLI. It is intended for developers working on BackendAPIService. The repository includes a pytest.ini that already enables coverage by default, so running pytest alone will produce coverage and an HTML report.

## Prerequisites
Before running tests, make sure your environment is prepared with Python tooling and the project dependencies.

- Use Python 3.10+.
- Change directory to the backend service:
  - cd network-management-5556-5684/BackendAPIService
- Create and activate a virtual environment (recommended):
  - python -m venv .venv
  - source .venv/bin/activate  # Windows: .venv\Scripts\activate
- Install dependencies:
  - pip install -r requirements.txt
- Coverage tooling:
  - pytest and pytest-cov are included in requirements.txt.
  - For using coverage CLI directly, install coverage if not already available:
    - pip install coverage
- Environment variables for tests:
  - Tests use mongomock and monkeypatch PyMongo, so no real MongoDB is required.
  - conftest.py sets defaults for MONGO_URI and MONGO_DB_NAME automatically for test runs.

## Quick Start (Most Common)
The quickest way to run tests and generate coverage HTML is simply:

```
pytest
```

Because pytest.ini includes:
- --cov=app to measure the app package
- --cov-report=term-missing to show missing lines in the terminal
- --cov-report=html:htmlcov to write HTML coverage to htmlcov/

After the run completes:
- Open htmlcov/index.html to explore detailed coverage.

## Option A: Using pytest-cov (recommended)

### What does --cov=app mean?
The value app refers to the Python package directory that contains the backend source code (the folder named app under BackendAPIService). When you pass --cov=app, pytest-cov measures coverage only for modules inside that package, ignoring third-party libraries and other unrelated files.

- If your source package is renamed or moved, update this argument accordingly. For example, if you rename app to backend:
  ```
  pytest --cov=backend --cov-report=term-missing --cov-report=html
  ```
- You can target multiple packages by repeating the argument:
  ```
  pytest --cov=app --cov=another_pkg --cov-report=term-missing
  ```
Run tests with coverage summary and reports. Use these explicit commands if you want to override the defaults in pytest.ini.

- Run all tests with terminal summary only:
  ```
  pytest --cov=app --cov-report=term-missing
  ```

- Run with coverage (terminal summary + HTML report):
  ```
  pytest --cov=app --cov-report=term-missing --cov-report=html
  ```

- Run and emit XML coverage for CI:
  ```
  pytest --cov=app --cov-report=xml
  ```

Example terminal output excerpt (term-missing):

```
Name                         Stmts   Miss  Cover   Missing
---------------------------------------------------------
app/__init__.py                 18      0   100%
app/db.py                      130      5    96%   47, 83, 120-121, 186
app/routes/devices.py          210      8    96%   55, 72, 105, 161-164, 188
app/routes/health.py            14      0   100%
app/schemas.py                 120      3    98%   28, 94, 117
---------------------------------------------------------
TOTAL                          492     16    97%
```

The “Missing” column lists specific lines that were not executed by tests.

## Option B: Using coverage CLI directly
You can invoke coverage to run pytest and then produce reports. This is useful when you want to separate test execution from reporting or enforce source filters.

- Erase previous coverage data (optional but recommended between runs):
  ```
  coverage erase
  ```
  What does this do?
  - coverage erase removes the cached coverage data file(s), typically .coverage and any parallel data files like .coverage.*. This ensures you start from a clean slate so that new reports do not include results from prior runs.

  When should you use it?
  - Before switching branches where code layout changed significantly.
  - When you want to ensure the report only reflects the current test session.
  - If you moved/renamed modules and see unexpected files lingering in the HTML report.

  Brief example:
  ```
  # Clean old data, rerun tests, and regenerate reports
  coverage erase
  coverage run --source=app -m pytest
  coverage report -m
  coverage html
  ```

- Run tests under coverage:
  ```
  coverage run -m pytest
  ```
  To limit measurement only to the app package:
  ```
  coverage run --source=app -m pytest
  ```

- Show terminal summary with missing lines:
  ```
  coverage report -m
  ```

- Generate an HTML report:
  ```
  coverage html
  ```
  Then open htmlcov/index.html in your browser.

- Generate XML (useful for CI systems like SonarQube or Codecov):
  ```
  coverage xml
  ```

Example coverage report -m output:

```
Name                         Stmts   Miss  Cover   Missing
---------------------------------------------------------
app/__init__.py                 18      0   100%
app/db.py                      130      5    96%   47, 83, 120-121, 186
app/routes/devices.py          210      8    96%   55, 72, 105, 161-164, 188
app/routes/health.py            14      0   100%
app/schemas.py                 120      3    98%   28, 94, 117
---------------------------------------------------------
TOTAL                          492     16    97%
```

## Step-by-Step: Full Workflow
Follow this end-to-end sequence on a fresh machine or environment.

1) Set up Python environment
   - Ensure Python 3.10+ is installed.
   - cd network-management-5556-5684/BackendAPIService
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) Install dependencies
   - pip install -r requirements.txt

3) Verify test discovery
   - pytest -q
   - You should see collected tests from tests/ (e.g., tests/test_health.py, tests/test_devices.py).

4) Generate coverage with pytest-cov
   - pytest
   - Inspect terminal output for coverage summary and missing lines.

5) Open HTML coverage
   - Open htmlcov/index.html in your browser and drill into modules and lines.

6) Optional: Regenerate reports cleanly
   - coverage erase
   - coverage run --source=app -m pytest
   - coverage html
   - coverage report -m

## Environment Setup Details
- Default environment for tests is handled by tests/conftest.py:
  - It sets MONGO_URI and MONGO_DB_NAME if they are not present.
  - It patches PyMongo’s MongoClient with mongomock.MongoClient, so tests run fully in-memory.
  - Socket operations used by the ping endpoint are mocked within tests where needed.
- You do not need a running Flask server for tests; they use Flask’s test client.

If you still want to run the app locally in development for manual checks:
- export FLASK_APP=run.py
- python run.py
- Visit http://localhost:3001 and http://localhost:3001/docs

## Common Issues and Fixes
- Issue: “No data was collected” or coverage is 0%.
  - Cause: Incorrect path in --cov, or tests not importing target modules.
  - Fix: Use --cov=app (the top-level backend package). Ensure tests import or execute code paths in app/.

- Issue: “ImportError: No module named app”
  - Cause: Running commands from the wrong directory.
  - Fix: cd network-management-5556-5684/BackendAPIService before running pytest or coverage.

- Issue: Tests attempt to connect to a real MongoDB instance.
  - Cause: Test patching did not apply or environment variables override behavior.
  - Fix: Ensure you are running via pytest so conftest.py executes. Do not run test files directly with python. Remove custom DB_INIT_ON_IMPORT=true if set in your shell.

- Issue: “mongomock not installed: …” and tests skipped
  - Cause: Missing dev dependency.
  - Fix: pip install -r requirements.txt to ensure mongomock is present.

- Issue: HTML report not found at htmlcov/index.html
  - Cause: Report not generated or different output path.
  - Fix: Use --cov-report=html (pytest) or coverage html (coverage CLI). By default, both write to htmlcov/.

- Issue: Want to include only specific files or folders in coverage
  - Fix: Use coverage run --source=app -m pytest, or configure .coveragerc if you add one in the future.

## Target Paths and Packages
- Project root for backend: network-management-5556-5684/BackendAPIService
- Source package measured for coverage: app
- Tests directory: tests
- Coverage HTML output: htmlcov/index.html
- pytest configuration: pytest.ini
  - addopts includes --cov=app, --cov-report=term-missing, and --cov-report=html:htmlcov

## Focused Test Runs
Run a specific test file or node while still collecting coverage:

- Single file:
  ```
  pytest tests/test_devices.py --cov=app --cov-report=term-missing
  ```

- Single test within a file:
  ```
  pytest tests/test_devices.py::test_create_and_get_device --cov=app --cov-report=term-missing
  ```

## Example CI-Friendly Commands
- Terminal summary + XML:
  ```
  pytest --cov=app --cov-report=term-missing --cov-report=xml
  ```
  This produces coverage.xml at project root, consumable by most CI tools.

- Fail build if coverage drops below a threshold (example 90%):
  ```
  pytest --cov=app --cov-fail-under=90
  ```

## Opening the Coverage Report
After generating the HTML report, open:
- htmlcov/index.html

Use the report to drill down into files and identify lines missed by tests. The term-missing output in the terminal also shows exact line numbers not covered, which can guide you to write additional tests. Combine both views to prioritize the most critical untested paths.
