# Security Reports

This directory contains outputs from static analysis tools.

## Bandit (Python SAST)

- JSON report: `bandit-report.json`
- SARIF report: Not generated. The installed Bandit version (1.8.6) does not support SARIF (`-f sarif` invalid). If SARIF is required, consider using:
  - `pip install bandit[toml]` and verify if a newer Bandit version adds SARIF; or
  - a wrapper/convertor tool to transform JSON -> SARIF; or
  - run Bandit via GitHub Action/CodeQL integrations that emit SARIF.

### How these reports were generated

From the BackendAPIService root:

1. Ensure Bandit is installed:
   `python3 -m pip show bandit` (installed version detected: 1.8.6)

2. Generate JSON report:
   `bandit -q -r . -f json -o security-reports/bandit-report.json`

3. Attempt SARIF (unsupported in current Bandit):
   `bandit -q -r . -f sarif -o security-reports/bandit-report.sarif` -> format unsupported.

The `security-reports/` directory is ensured to exist prior to writing reports.
