# Security Reports

This directory contains outputs from Bandit static application security testing (SAST).

Generated files:
- bandit_report.json — Machine-readable JSON report.
- bandit_report.txt — Human-readable text summary.

These reports were produced by running:
- JSON: `bandit -r BackendAPIService -q -f json -o BackendAPIService/reports/bandit_report.json`
- Text:  `bandit -r BackendAPIService -q -f txt -o BackendAPIService/reports/bandit_report.txt`

Note: Bandit may exit non-zero when issues are found; report generation still completes successfully.
