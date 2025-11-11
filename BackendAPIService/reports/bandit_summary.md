# Bandit Summary (latest run)

This summary reflects the latest Bandit JSON report at `reports/bandit_report.json`.

## Totals
- Total findings: 1583
- By severity:
  - HIGH: 31
  - MEDIUM: 71
  - LOW: 1481

## Project vs Third-Party
- Findings in application code (BackendAPIService/app, BackendAPIService/routes): 0
- Findings in third-party/vendor code: 1583

All remaining issues are inside third-party libraries or tooling (e.g., pytest, click, werkzeug, pymongo). They are not emitted from our application modules.

## Representative Categories and Remediation

1) Weak cryptographic hashes (MD5/SHA1)
- Typical files: `pymongo/ocsp_support.py`, `werkzeug/debug/__init__.py`, `pymongo/results.py`
- Remediation:
  - Upgrade dependencies to versions that avoid weak hashes or explicitly mark non-security usage.
  - If still flagged and unavoidable in vendor code, configure Bandit excludes.

2) Subprocess usage with shell=True or untrusted inputs
- Typical files: CLI/terminal helpers within `click`, framework internals
- Remediation:
  - Upgrade dependencies; prefer versions that mitigate shell=True.
  - Exclude vendor directories in Bandit configuration.

3) Insecure deserialization and eval (pickle, marshal, eval)
- Typical files: `_pytest` internals, some helper modules in dependencies
- Remediation:
  - Ensure app code never feeds untrusted data to these code paths.
  - Prefer dependency upgrades; otherwise exclude vendor directories.

4) Assert statements and try/except/pass patterns
- Typical files: testing and framework internals
- Remediation:
  - Not applicable to our app (0 findings). Continue to avoid asserts for security logic in our code.

## Recommended Bandit Configuration

To focus on our code and reduce third-party noise, run Bandit with excludes similar to:

```
bandit -r . \
  -x \"*/venv/*,*/.venv/*,*/env/*,*/.env/*,*/site-packages/*,*/dist-packages/*,*/.tox/*,*/.pytest_cache/*\" \
  -f json -o reports/bandit_report.json
```

Or create a `bandit.yaml` with:

```yaml
exclude_dirs:
  - venv
  - .venv
  - env
  - .env
  - .tox
  - **/site-packages
  - **/dist-packages
  - **/.pytest_cache
```

Then invoke:
```
bandit -r . -c bandit.yaml -f json -o reports/bandit_report.json
```

## Next Steps
- Keep dependencies updated (Flask, Werkzeug, Click, PyMongo, PyTest).
- Continue scanning our app modules; maintain zero Bandit findings.
- Re-run Bandit with excludes to obtain application-focused reports.

Last updated: (auto-generated)
