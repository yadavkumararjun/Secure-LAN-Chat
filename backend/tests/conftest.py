import pytest
from app.database import init_db
from app.services.rate_limiter import auth_rate_limiter, chat_rate_limiter, upload_rate_limiter


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Autouse fixture: initializes database schema and resets all rate limiters before and after each test."""
    init_db()
    auth_rate_limiter.reset_all()
    chat_rate_limiter.reset_all()
    upload_rate_limiter.reset_all()
    yield
    auth_rate_limiter.reset_all()
    chat_rate_limiter.reset_all()
    upload_rate_limiter.reset_all()
