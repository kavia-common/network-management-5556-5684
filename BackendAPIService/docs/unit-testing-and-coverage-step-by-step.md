# Backend Unit Testing and Coverage (Beginner-Friendly)

## 1) Where to run commands
Run everything from this folder:
- network-management-5556-5684/BackendAPIService

Tip: If commands fail with “No module named app,” you are likely in the wrong folder.

## 2) Quick Setup (once per machine)
Create a virtual environment and install dependencies.

- Linux/macOS
  1. cd network-management-5556-5684/BackendAPIService
  2. python -m venv .venv
  3. source .venv/bin/activate
  4. pip install -r requirements.txt

- Windows PowerShell
  1. cd network-management-5556-5684\BackendAPIService
  2. python -m venv .venv
  3. .\.venv\Scripts\Activate.ps1
  4. pip install -r requirements.txt

- Windows CMD
  1. cd network-management-5556-5684\BackendAPIService
  2. python -m venv .venv
  3. .\.venv\Scripts\activate.bat
  4. pip install -r requirements.txt

Notes:
- Tests run in-memory via mongomock. No real MongoDB needed.
- Do not export DB_INIT_ON_IMPORT=true for test runs.

## 3) Quick path (pytest-cov) — simplest
Pytest is already configured to collect coverage and generate an HTML report.

- Linux/macOS
  1. cd network-management-5556-5684/BackendAPIService
  2. pytest

- Windows PowerShell
  1. cd network-management-5556-5684\BackendAPIService
  2. pytest

- Windows CMD
  1. cd network-management-5556-5684\BackendAPIService
  2. pytest

What happens:
- Coverage is collected for the app package (because pytest.ini has --cov=app).
- Missing lines show in the terminal (term-missing).
- An HTML report is generated in htmlcov/.

## 4) Alternative (coverage CLI) — more control
Use this if you want to explicitly control coverage steps.

- Linux/macOS (copy-paste)
  1. cd network-management-5556-5684/BackendAPIService
  2. coverage erase
  3. PYTHONPATH=. coverage run --source=app -m pytest
  4. coverage report -m
  5. coverage html

- Windows PowerShell (copy-paste)
  1. cd network-management-5556-5684\BackendAPIService
  2. coverage erase
  3. $env:PYTHONPATH="."
  4. coverage run --source=app -m pytest
  5. coverage report -m
  6. coverage html
  7. Remove-Item Env:\PYTHONPATH   # optional cleanup

- Windows CMD (copy-paste)
  1. cd network-management-5556-5684\BackendAPIService
  2. coverage erase
  3. set PYTHONPATH=.
  4. coverage run --source=app -m pytest
  5. coverage report -m
  6. coverage html
  7. set PYTHONPATH=               # optional cleanup

## 5) Where is the report?
Open this file in your browser:
- network-management-5556-5684/BackendAPIService/htmlcov/index.html

## 6) What does --cov=app mean?
- app is the backend source package folder: BackendAPIService/app
- --cov=app tells coverage tools to measure only our application code, not third‑party libraries.

## 7) What does coverage erase do?
- Deletes old coverage data files (like .coverage).
- Use it when switching branches or after big changes, so reports only reflect your latest run.

## 8) Tiny troubleshooting
- Error: ModuleNotFoundError: No module named app
  - Fix: Make sure you ran the commands inside BackendAPIService and set PYTHONPATH for coverage CLI runs.
- Error: pytest not found
  - Fix: Activate your virtual environment and run pip install -r requirements.txt.
- No HTML report
  - Fix: With pytest-cov, just run pytest (pytest.ini already writes htmlcov). With coverage CLI, run coverage html.

## 9) Optional: XML for CI
If your CI needs XML:
- pytest-cov: pytest --cov=app --cov-report=xml
- coverage CLI: coverage xml
