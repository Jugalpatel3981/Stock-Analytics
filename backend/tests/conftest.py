import pytest

from app.core.cache import clear_all_caches
from app.core.rate_limit import reset_all_rate_limits


@pytest.fixture(autouse=True)
def isolate_shared_state():
    clear_all_caches()
    reset_all_rate_limits()
    yield
    clear_all_caches()
    reset_all_rate_limits()
