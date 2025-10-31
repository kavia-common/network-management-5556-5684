import os
import pytest

@pytest.fixture(scope='session', autouse=True)
def set_test_env():
    os.environ.setdefault('FLASK_ENV', 'testing')
    os.environ.setdefault('PYTHON_ENV', 'testing')
    yield
