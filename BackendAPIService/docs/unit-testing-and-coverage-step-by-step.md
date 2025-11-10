# Backend Unit Testing and Coverage: Step-by-Step Guide

## Overview
This guide walks you through running BackendAPIService unit tests and generating coverage reports using both pytest-cov and the coverage CLI. It provides clear, step-by-step instructions with OS-specific command examples for Linux/macOS, Windows PowerShell, and Windows CMD. It also explains why we use `--cov=app`, when to use `coverage erase`, and includes troubleshooting tips.

The commands below assume you are inside the backend service directory:
- network-management-5556-5684/BackendAPIService

## Prerequisites
Ensure your environment is ready before running tests and coverage.

- Python 3.10+ installed.
- Recommended: Use a virtual environment per project.
- From the repository root, change to the backend service directory:
  - Linux/macOS:
    - cd network-management-5556-5684/BackendAPIService
  - Windows (PowerShell or CMD):
    - cd network-management-5556-5684\BackendAPIService

Create and activate a virtual environment, then install dependencies:

- Linux/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

- Windows PowerShell:
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install -r requirements.txt

- Windows CMD:
  - python -m venv .venv
  - .\.venv\Scripts\activate.bat
  - pip install -r requirements.txt

Notes:
- Tests use mongomock and fixtures under tests/conftest.py; no external MongoDB is required.
- Do not set DB_INIT_ON_IMPORT=true when running tests. Pytest will apply the test patches and in-memory DB.

## Option A: Run Tests with pytest-cov (Recommended)
The repository includes pytest.ini that already enables coverage by default:
- --cov=app
- --cov-report=term-missing
- --cov-report=html:htmlcov

This means running pytest alone collects coverage, prints missing lines in the terminal, and generates an HTML report.

Step-by-step:

1) Change directory to BackendAPIService
- Linux/macOS:
  - cd network-management-5556-5684/BackendAPIService
- Windows PowerShell/CMD:
  - cd network-management-5556-5684\BackendAPIService

2) Run tests (pytest.ini will collect coverage and generate htmlcov/)
- Linux/macOS:
  - pytest
- Windows PowerShell:
  - pytest
- Windows CMD:
  - pytest

3) Open the HTML report
- Open BackendAPIService/htmlcov/index.html in your browser.

If you want to run with explicit options (overriding or replicating what pytest.ini does), use:

- Linux/macOS:
  - pytest --cov=app --cov-report=term-missing --cov-report=html
- Windows PowerShell:
  - pytest --cov=app --cov-report=term-missing --cov-report=html
- Windows CMD:
  - pytest --cov=app --cov-report=term-missing --cov-report=html

To emit XML for CI:

- All OS:
  - pytest --cov=app --cov-report=xml

### What does --cov=app mean?
The value `app` points to the backend source package directory (BackendAPIService/app). Passing `--cov=app` instructs pytest-cov to measure coverage for modules in this package and exclude unrelated third-party files. If you rename or move the source package, update this value accordingly. For multiple packages, repeat the argument: `--cov=app --cov=another_pkg`.

## Option B: Run Tests with the coverage CLI
Using the coverage CLI directly gives you fine-grained control and separates test execution from report generation.

1) Start clean (optional but recommended)
- Linux/macOS:
  - coverage erase
- Windows PowerShell:
  - coverage erase
- Windows CMD:
  - coverage erase

This removes previous .coverage data so reports reflect only the current run.

2) Run tests under coverage
To reliably resolve imports, set PYTHONPATH so the app package is importable from the BackendAPIService directory.

- Linux/macOS:
  - PYTHONPATH=. coverage run --source=app -m pytest

- Windows PowerShell:
  - $env:PYTHONPATH = "."
  - coverage run --source=app -m pytest
  - Remove the variable when done if you want to clean up:
    - Remove-Item Env:\PYTHONPATH

- Windows CMD:
  - set PYTHONPATH=.
  - coverage run --source=app -m pytest
  - Optionally clear the variable for the session:
    - set PYTHONPATH=

Explanation:
- PYTHONPATH=. ensures the current directory is on sys.path so `import app` works consistently.
- --source=app limits coverage measurement to the `app` package, which produces accurate backend coverage stats.

3) Produce a terminal summary (with missing lines)
- All OS:
  - coverage report -m

4) Generate HTML report
- All OS:
  - coverage html

Open BackendAPIService/htmlcov/index.html in your browser.

5) Optional: Generate XML for CI
- All OS:
  - coverage xml

### Why use coverage erase?
`coverage erase` deletes prior coverage data files (e.g., .coverage, .coverage.*). Use it when:
- Switching branches or after significant refactors to avoid stale paths.
- You want each report to reflect only the most recent test run.
- You see unexpected files lingering in HTML output.

## OS-Specific Quick Reference

Linux/macOS (bash/zsh):
- Clean:
  - coverage erase
- Run:
  - PYTHONPATH=. coverage run --source=app -m pytest
- Reports:
  - coverage report -m
  - coverage html
  - coverage xml

Windows PowerShell:
- Clean:
  - coverage erase
- Run:
  - $env:PYTHONPATH = "."
  - coverage run --source=app -m pytest
- Reports:
  - coverage report -m
  - coverage html
  - coverage xml
- Optional cleanup:
  - Remove-Item Env:\PYTHONPATH

Windows CMD:
- Clean:
  - coverage erase
- Run:
  - set PYTHONPATH=.
  - coverage run --source=app -m pytest
- Reports:
  - coverage report -m
  - coverage html
  - coverage xml
- Optional cleanup for session:
  - set PYTHONPATH=

## Focused Test Runs (Both Methods)
You can run a specific file or test node while still collecting coverage.

- Single file with pytest-cov:
  - pytest tests/test_devices.py --cov=app --cov-report=term-missing

- Single test with pytest-cov:
  - pytest tests/test_devices.py::test_create_and_get_device --cov=app --cov-report=term-missing

- Using coverage CLI:
  - PYTHONPATH=. coverage run --source=app -m pytest tests/test_devices.py
  - coverage report -m
  - coverage html

## Where to Find Results
- Terminal coverage summary: output from pytest (pytest-cov) or coverage report -m.
- HTML coverage report: BackendAPIService/htmlcov/index.html.
- XML coverage report: BackendAPIService/coverage.xml (if generated).

## Troubleshooting

- ModuleNotFoundError: No module named app
  - Likely cause: Running from the wrong directory or missing PYTHONPATH.
  - Fix: cd network-management-5556-5684/BackendAPIService and rerun. For coverage CLI, set PYTHONPATH before running.

- pytest not found or ImportError: No module named pytest
  - Likely cause: Dependencies not installed or venv not activated.
  - Fix: Activate the virtual environment and run pip install -r requirements.txt.

- No data was collected
  - Likely cause: Coverage did not measure the intended source or tests did not exercise `app` modules.
  - Fix: Use --cov=app with pytest-cov or --source=app with coverage run, and ensure tests import/execute `app` code paths.

- HTML report not found at htmlcov/index.html
  - Likely cause: Report not generated or a different output path configured.
  - Fix: For pytest-cov, include --cov-report=html or rely on pytest.ini defaults. For coverage CLI, run coverage html. By default, both use htmlcov/.

- Tests attempt to connect to a real MongoDB
  - Likely cause: Running tests without pytest so conftest fixtures do not apply, or environment overrides.
  - Fix: Always run via pytest so tests/conftest.py applies mongomock patches. Avoid exporting DB_INIT_ON_IMPORT=true during tests.

- Stale files or mismatched paths in coverage output
  - Cause: Old coverage data from prior sessions.
  - Fix: coverage erase, then re-run tests and regenerate reports.

## Reference
- Test runner configuration: pytest.ini
  - addopts includes -q, --maxfail, --cov=app, --cov-report=term-missing, --cov-report=html:htmlcov
- Project dependencies: requirements.txt
- Test fixtures and environment setup: tests/conftest.py
- Source package measured: app
- Tests directory: tests

By following these steps, you can reliably run unit tests, collect coverage, and generate reports across Linux/macOS and Windows environments using either pytest-cov or the coverage CLI.
