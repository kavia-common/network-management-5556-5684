import pytest

# Re-export fixtures from integration conftest if present, otherwise use local ones
try:
    from ..integration.conftest import *  # noqa: F401,F403
except Exception:
    pass
