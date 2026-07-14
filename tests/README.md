# OneVizion API v3 Tests

This directory contains tests for the onevizion Python package.

## Running Tests

### Local Testing with tox

Test across multiple Python versions:

```bash
# Install tox
pip install tox

# Run tests for all environments
tox

# Run tests for specific Python version
tox -e py27
tox -e py37
tox -e py311

# Run linting
tox -e lint

# Run type checking (Python 3.7+)
tox -e type
```

### Running with pytest directly

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=onevizion --cov-report=html

# Run specific test file
pytest tests/test_curl.py

# Run specific test
pytest tests/test_curl.py::TestCurlBasic::test_curl_init_no_url

# Run with verbose output
pytest -v
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_curl.py` - Tests for HTTP client (`curl` class)
- `test_trackor.py` - Tests for Trackor CRUD operations
- `fixtures/` - Test fixtures and data
- `fixtures/cassettes/` - VCR cassettes for HTTP mocking

## VCR Cassettes

Tests use [VCR.py](https://vcrpy.readthedocs.io/) to record and replay HTTP interactions. This allows tests to run without hitting real APIs.

### Recording New Cassettes

1. Delete the existing cassette file (if any)
2. Run the test - it will make a real HTTP request and record it
3. Subsequent runs will use the recorded cassette

### Cassette Management

- Cassettes are stored in `tests/fixtures/cassettes/`
- Sensitive data (auth headers, API keys) is filtered out (see `conftest.py`)
- Cassettes should be committed to git

### Re-recording Cassettes

To re-record all cassettes:

```bash
# Delete all cassettes
rm -rf tests/fixtures/cassettes/*.yaml

# Run tests (will make real HTTP calls and record)
pytest tests/
```

## Python Version Compatibility

Tests are designed to run on Python 2.7 through 3.13:

- Python 2.7: Uses older pytest (<5.0) and vcrpy (<2.0)
- Python 3.5: Uses pytest (<6.2) and vcrpy (<4.0)
- Python 3.6+: Uses latest pytest and vcrpy

## Code Coverage

Coverage reports are generated in:
- `htmlcov/` - HTML format (open `htmlcov/index.html` in browser)
- `coverage.xml` - XML format (for CI tools)
- Terminal output - Summary shown after test run

## CI/CD

GitHub Actions automatically runs tests on:
- Python 2.7 (ubuntu-20.04) - minimum supported version
- Python 3.5-3.6 (ubuntu-20.04)
- Python 3.7-3.13 (ubuntu-latest)

See `.github/workflows/test.yml` for details.

## Writing New Tests

### Basic Test Structure

```python
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import vcr
from onevizion.your_module import YourClass


class TestYourClass(object):
    """Test suite for YourClass."""

    def test_something(self):
        """Test description."""
        obj = YourClass()
        assert obj.method() == expected_value

    @vcr.use_cassette('tests/fixtures/cassettes/test_api_call.yaml')
    def test_api_call(self):
        """Test API interaction with VCR."""
        obj = YourClass()
        result = obj.api_method()
        assert result is not None
```

### Python 2/3 Compatibility Tips

- Use `from __future__ import print_function` for print compatibility
- Use `sys.version_info` to conditionally import `mock` vs `unittest.mock`
- Avoid f-strings (use `.format()` instead)
- Use `class Name(object):` instead of `class Name:`
- Test unicode handling for both Python 2 and 3

## Troubleshooting

### Import Errors

If you get import errors, make sure you've installed dev dependencies:

```bash
pip install -r requirements-dev.txt
```

### VCR Cassette Errors

If VCR can't find cassettes or they're mismatched:

```bash
# Re-record specific cassette
rm tests/fixtures/cassettes/problem_test.yaml
pytest tests/test_file.py::test_name
```

### Python 2.7 Specific Issues

For Python 2.7, use older dependency versions:

```bash
pip install "pytest<5.0" "pytest-cov<2.6" "vcrpy<2.0" mock
```
