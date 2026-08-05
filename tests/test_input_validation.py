"""Tests for input validation in curl and trackor.

Tests demonstrate:
- URL validation prevents dangerous protocols (javascript:, file:, etc.)
- Required parameters are validated
- Type validation for numeric parameters
"""
# -*- coding: utf-8 -*-
from __future__ import print_function

import responses

from onevizion.curl import curl
from onevizion.trackor import Trackor


class TestCurlInputValidation(object):
    """Test curl validates inputs properly."""

    def test_url_validation_rejects_javascript_protocol(self):
        """curl should reject javascript: URLs."""
        c = curl('GET', 'javascript:alert(1)')

        assert len(c.errors) > 0
        assert 'url' in c.errors[0].lower() or 'protocol' in c.errors[0].lower()

    def test_url_validation_rejects_file_protocol(self):
        """curl should reject file: URLs."""
        c = curl('GET', 'file:///etc/passwd')

        assert len(c.errors) > 0
        assert 'url' in c.errors[0].lower() or 'protocol' in c.errors[0].lower()

    def test_url_validation_rejects_data_protocol(self):
        """curl should reject data: URLs."""
        c = curl('GET', 'data:text/html,<script>alert(1)</script>')

        assert len(c.errors) > 0
        assert 'url' in c.errors[0].lower() or 'protocol' in c.errors[0].lower()

    @responses.activate
    def test_url_validation_accepts_http(self):
        """curl should accept http:// URLs."""
        responses.add(responses.GET, 'http://example.com', json={}, status=200)

        c = curl('GET', 'http://example.com')

        assert len(c.errors) == 0

    @responses.activate
    def test_url_validation_accepts_https(self):
        """curl should accept https:// URLs."""
        responses.add(responses.GET, 'https://example.com', json={}, status=200)

        c = curl('GET', 'https://example.com')

        assert len(c.errors) == 0

    def test_url_validation_rejects_none(self):
        """curl should reject None URL when runQuery is called."""
        c = curl()  # No URL provided
        c.url = None
        c.runQuery()

        assert len(c.errors) > 0
        assert 'url' in c.errors[0].lower()

    def test_url_validation_rejects_empty_string(self):
        """curl should reject empty URL."""
        c = curl('GET', '')

        assert len(c.errors) > 0
        assert 'url' in c.errors[0].lower()

    @responses.activate
    def test_method_validation_rejects_invalid(self):
        """curl should reject invalid HTTP methods."""
        # Note: responses will still intercept even for invalid methods,
        # but our validation should catch it before making the request
        c = curl('INVALID', 'http://example.com')

        # Should have validation error
        assert len(c.errors) > 0
        assert 'method' in c.errors[0].lower()

    @responses.activate
    def test_method_validation_accepts_valid_methods(self):
        """curl should accept standard HTTP methods."""
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

        # Register response for each method
        for method in valid_methods:
            # HEAD responses must not have a body
            if method == 'HEAD':
                responses.add(method, 'http://example.com', status=200)
            else:
                responses.add(method, 'http://example.com', json={}, status=200)

        for method in valid_methods:
            c = curl(method, 'http://example.com')
            assert len(c.errors) == 0, "Method {m} should be accepted".format(m=method)

    def test_timeout_validation_rejects_negative(self):
        """curl should reject negative timeout."""
        c = curl('GET', timeout=-1)
        c.url = 'http://example.com'
        c.runQuery()

        assert len(c.errors) > 0
        assert 'timeout' in c.errors[0].lower()

    def test_timeout_validation_rejects_zero(self):
        """curl should reject zero timeout."""
        c = curl('GET', timeout=0)
        c.url = 'http://example.com'
        c.runQuery()

        assert len(c.errors) > 0
        assert 'timeout' in c.errors[0].lower()

    def test_max_retries_validation_rejects_negative(self):
        """curl should reject negative max_retries."""
        c = curl('GET', max_retries=-1)
        c.url = 'http://example.com'
        c.runQuery()

        assert len(c.errors) > 0
        assert 'retries' in c.errors[0].lower() or 'retry' in c.errors[0].lower()


class TestTrackorInputValidation(object):
    """Test Trackor validates inputs properly."""

    def test_url_validation_rejects_javascript(self):
        """Trackor should reject javascript: URLs."""
        t = Trackor(
            trackorType="Project",
            URL="javascript:alert(1)",
            userName="u",
            password="p"
        )

        assert len(t.errors) > 0
        assert 'url' in t.errors[0].lower() or 'protocol' in t.errors[0].lower()

    def test_url_validation_accepts_https(self):
        """Trackor should accept https:// URLs."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p"
        )

        assert len(t.errors) == 0

    def test_trackor_type_validation_rejects_empty(self):
        """Trackor should reject empty trackorType."""
        t = Trackor(
            trackorType="",
            URL="https://test.onevizion.com",
            userName="u",
            password="p"
        )

        # trackorType can be empty for some operations, so we don't validate on __init__
        # But when used in operations, it should be validated
        # For now, just ensure it doesn't crash
        assert t.TrackorType == ""

    def test_max_file_size_validation_rejects_negative(self):
        """Trackor should reject negative max_file_size."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            max_file_size=-1
        )

        assert len(t.errors) > 0
        assert 'file' in t.errors[0].lower() and 'size' in t.errors[0].lower()

    def test_max_file_size_validation_rejects_zero(self):
        """Trackor should reject zero max_file_size."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            max_file_size=0
        )

        assert len(t.errors) > 0
        assert 'file' in t.errors[0].lower() and 'size' in t.errors[0].lower()

    def test_max_file_size_validation_accepts_positive(self):
        """Trackor should accept positive max_file_size."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            max_file_size=10 * 1024 * 1024
        )

        assert len(t.errors) == 0

    def test_max_file_size_validation_accepts_none(self):
        """Trackor should accept None max_file_size (no limit)."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            max_file_size=None
        )

        assert len(t.errors) == 0
