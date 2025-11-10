# Backend Testing and Coverage Guide

## Overview
This guide explains how to run all backend tests for the Flask service and how to generate code coverage reports using either pytest-cov or the coverage CLI. It is intended for developers working on BackendAPIService.

## Prerequisites
Before running tests, make sure your environment is prepared.

- Change directory to BackendAPIService:
  - cd network-management-5556-5684/BackendAPIService
- Install dependencies:
  - pip install -r requirements.txt
- Ensure pytest and coverage tooling are installed. The project includes pytest and pytest-cov in requirements.txt. If you prefer to use the coverage CLI directly, install coverage as needed:
  - pip install coverage

Note: Tests use mongomock, so no real MongoDB instance is required.

## Option A: Using pytest-cov (recommended)
Run tests with coverage summary and HTML report in a single command. The default pytest.ini in this project already configures sensible defaults for coverage, but you can run explicit commands as shown below.

- Run all tests:
  ```
  pytest
  ```

- Run with coverage (terminal summary + HTML report):
  ```
  pytest --cov=app --cov-report=term-missing --cov-report=html
  ```

Outputs:
- The terminal displays per-file line coverage with missing lines (term-missing).
- An HTML coverage report is generated at htmlcov/index.html.

Other formats:
- XML for CI tools:
  ```
  pytest --cov=app --cov-report=xml
  ```

Notes:
- The --cov=app target matches the main backend package directory ("app"). If the package path changes, update this argument accordingly.
- A project-level pytest.ini already sets addopts to include --cov=app and coverage reports. Running plain pytest will also produce coverage and HTML output by default in this repo.

## Option B: Using coverage CLI directly
You can invoke coverage to run pytest and then produce reports. This provides fine-grained control when you want to adjust options independently of pytest.

- Erase previous coverage data (optional):
  ```
  coverage erase
  ```

- Run tests under coverage (using pytest via -m):
  ```
  coverage run -m pytest
  ```

- Show terminal summary with missing lines:
  ```
  coverage report -m
  ```

- Generate an HTML report:
  ```
  coverage html
  ```
  Open htmlcov/index.html in your browser.

- Generate XML (for CI):
  ```
  coverage xml
  ```

Tips:
- To measure only the app package when using coverage run, you can use:
  ```
  coverage run --source=app -m pytest
  ```

## Common Paths and Tips
- Run all commands from the BackendAPIService directory.
- The coverage target --cov=app matches the main backend package name. If the package path changes, update this argument accordingly.
- If you see "no data collected," ensure tests are discovered by pytest (files named test_*.py in tests/ or alongside modules).
- To focus on a specific test file:
  ```
  pytest tests/test_devices.py --cov=app --cov-report=term-missing
  ```
- The HTML report is generated in htmlcov/. If you regenerate reports frequently, consider removing old data with coverage erase to avoid stale artifacts.

## Opening the Coverage Report
After generating the HTML report, open:
- htmlcov/index.html

Use the report to drill down into files and identify lines missed by tests. The term-missing output in the terminal also shows exact line numbers not covered, which can guide you to write additional tests.
