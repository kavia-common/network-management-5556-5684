# Backend Unit Test Coverage with coverage CLI

## Overview
This guide explains how to execute BackendAPIService unit tests using the coverage CLI, and how to generate terminal and HTML reports. It focuses on the exact commands that work in this repository, including using PYTHONPATH to ensure imports resolve as expected.

Using coverage directly lets you separate test execution from reporting and gives you fine‑grained control over what source paths are measured.

## Prerequisites
Before running coverage, ensure your Python environment is set up and dependencies are installed.

- Python 3.10+ recommended.
- Navigate to the backend service directory:
  - cd network-management-5556-5684/BackendAPIService
- Create and activate a virtual environment (recommended):
  - python -m venv .venv
  - source .venv/bin/activate  # Windows: .venv\Scripts\activate
- Install project requirements:
  - pip install -r requirements.txt
- Install coverage if not already available:
  - pip install coverage

Notes:
- Tests use mongomock and fixtures in tests/conftest.py to patch MongoDB calls, so no external database is required.
- Do not set DB_INIT_ON_IMPORT=true during tests; pytest will apply the necessary patches.

## Where to Run
Run commands from the BackendAPIService folder so imports resolve correctly:

- cd network-management-5556-5684/BackendAPIService

When invoking coverage with pytest, it’s safest to prefix with PYTHONPATH=. so the app package is importable relative to this directory:

- PYTHONPATH=. coverage run -m pytest

This ensures the app package (BackendAPIService/app) is discoverable, even in shells that don’t default to adding the current directory to sys.path.

## Clean Start
If you previously generated coverage data or switched branches, start clean:

- coverage erase

This removes .coverage files so your next run reflects only current test execution.

## Run Tests Under Coverage
Execute tests via pytest under coverage. Use PYTHONPATH=. to ensure imports work reliably:

- PYTHONPATH=. coverage run -m pytest

Optionally, restrict coverage measurement to the application package (recommended for precise results):

- PYTHONPATH=. coverage run --source=app -m pytest

Both variants run all tests in tests/ (as configured by pytest.ini). The --source=app option limits coverage measurement to the backend source code.

## View Terminal Report (with missing lines)
After the test run, produce a terminal summary including missing line numbers:

- coverage report -m

This prints a table showing statements, misses, and the exact line ranges not covered.

## Generate HTML Report
Generate an HTML report for interactive exploration:

- coverage html

Open the report at:

- htmlcov/index.html

This folder is created in BackendAPIService/htmlcov/ by default.

## Optional: XML Report for CI
If your CI pipeline (e.g., Codecov, Sonar, Jenkins) requires an XML report:

- coverage xml

This generates coverage.xml in the current directory.

## Common Errors and Fixes
- ModuleNotFoundError: No module named app
  - Cause: Running commands from the wrong directory or missing PYTHONPATH.
  - Fix: cd network-management-5556-5684/BackendAPIService and rerun with PYTHONPATH=. coverage run -m pytest.

- pytest: command not found or ImportError for pytest
  - Cause: Dependencies not installed or venv not activated.
  - Fix: Activate your virtual environment and run pip install -r requirements.txt.

- No data was collected
  - Cause: Coverage did not measure your source or tests didn’t execute target code.
  - Fix: Use coverage run --source=app -m pytest so only the app package is measured and ensure tests import/execute code under app/.

- Stale or unexpected files in HTML report
  - Cause: Previous coverage sessions lingering.
  - Fix: Run coverage erase before re-running tests and coverage html.

- Tests try to hit a real database
  - Cause: Running tests without pytest’s conftest patching.
  - Fix: Run via pytest (not python tests/...), e.g., PYTHONPATH=. coverage run -m pytest.

## Quick Copy-Paste Commands
Use these commands from the BackendAPIService directory for a clean, repeatable workflow:

```
# 1) Optional: start clean
coverage erase

# 2) Run tests under coverage (ensures imports resolve)
PYTHONPATH=. coverage run --source=app -m pytest

# 3) Terminal summary with missing lines
coverage report -m

# 4) HTML report
coverage html

# 5) (Optional) XML report for CI
coverage xml
```

## Where to Find Results
- Terminal report: printed by coverage report -m
- HTML report: BackendAPIService/htmlcov/index.html
- XML report: BackendAPIService/coverage.xml (if generated)

Tip: Keep your shell in network-management-5556-5684/BackendAPIService while running these commands to avoid path and import issues. If you automate in CI, ensure the working directory is set accordingly and include PYTHONPATH=. for consistency.
