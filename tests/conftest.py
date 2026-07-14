"""Pytest configuration and fixtures for onevizion tests."""
import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


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
        "record_mode": "once",  # Record cassettes once, then replay
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
