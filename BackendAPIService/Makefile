.PHONY: test coverage coverage-html clean

test:
	pytest -q

coverage:
	coverage erase || true
	PYTHONPATH=. coverage run --source=app -m pytest
	coverage report -m

coverage-html:
	coverage erase || true
	PYTHONPATH=. coverage run --source=app -m pytest
	coverage html -d htmlcov
	@echo "Open htmlcov/index.html"

clean:
	rm -rf htmlcov .coverage .pytest_cache
