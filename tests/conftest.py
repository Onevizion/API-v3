"""Pytest configuration and fixtures for onevizion tests."""
import os
import sys

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed


@pytest.fixture
def vcr_config():
    """Configure VCR for recording/replaying HTTP interactions."""
    return {
        "filter_headers": [
            ('authorization', 'REDACTED'),
            ('x-api-key', 'REDACTED'),
        ],
        "filter_query_parameters": [
            ('access_key', 'REDACTED'),
            ('secret_key', 'REDACTED'),
        ],
        "record_mode": "none",  # Never re-record, only use existing cassettes
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "cassette_library_dir": "tests/fixtures/cassettes",
    }


@pytest.fixture
def mock_url():
    """Provide a test URL for HTTP requests."""
    return "https://httpbin.org"


@pytest.fixture
def test_auth():
    """Provide test authentication credentials."""
    return {
        "username": "test_user",
        "password": "test_password",
    }


@pytest.fixture
def ov_credentials():
    """Load OneVizion credentials from environment."""
    return {
        "url": os.getenv("OV_URL", "https://fiberlab.onevizion.com"),
        "username": os.getenv("OV_USERNAME"),
        "password": os.getenv("OV_PASSWORD"),
        "access_key": os.getenv("OV_ACCESS_KEY"),
        "secret_key": os.getenv("OV_SECRET_KEY"),
    }


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires OV credentials)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if credentials not available."""
    skip_integration = pytest.mark.skip(
        reason="Integration tests require OV_USERNAME/OV_PASSWORD or OV_ACCESS_KEY/OV_SECRET_KEY in .env"
    )

    has_creds = (
        (os.getenv("OV_USERNAME") and os.getenv("OV_PASSWORD")) or
        (os.getenv("OV_ACCESS_KEY") and os.getenv("OV_SECRET_KEY"))
    )

    for item in items:
        if "integration" in item.keywords and not has_creds:
            item.add_marker(skip_integration)
