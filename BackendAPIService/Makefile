.PHONY: test test-html coverage coverage-html clean

# Run tests with coverage and generate HTML report via pytest-cov
# Uses pytest.ini defaults but we pass explicit flags to be robust in CI.
test:
	pytest --cov=app --cov-report=term-missing:skip-covered --cov-report=html:htmlcov

# Alias for explicit HTML generation through pytest
test-html:
	pytest --cov=app --cov-report=term-missing:skip-covered --cov-report=html:htmlcov

# Use coverage CLI directly (terminal report only)
coverage:
	coverage erase || true
	PYTHONPATH=. coverage run --source=app -m pytest
	coverage report -m

# Use coverage CLI directly (HTML report)
coverage-html:
	coverage erase || true
	PYTHONPATH=. coverage run --source=app -m pytest
	coverage html -d htmlcov
	@echo "Open htmlcov/index.html"

clean:
	rm -rf htmlcov .coverage .pytest_cache
