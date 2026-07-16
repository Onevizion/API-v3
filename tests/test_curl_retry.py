"""Tests for curl retry logic.

Tests demonstrate:
- 5xx errors should be retried (server errors are transient)
- 4xx errors should NOT be retried (client errors are permanent)
- Exponential backoff between retries
"""
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import time

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import requests
from onevizion.curl import curl


class TestCurlRetry(object):
    """Test curl retry logic for transient failures."""

    def test_curl_retries_on_500_error(self):
        """5xx errors should be retried (server errors are transient)."""
        call_count = [0]

        def failing_request(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                # First 2 calls fail with 503
                response = mock.MagicMock()
                response.status_code = 503
                response.reason = "Service Unavailable"
                response.text = "Server overloaded"
                return response
            else:
                # Third call succeeds
                response = mock.MagicMock()
                response.status_code = 200
                response.text = '{"status": "ok"}'
                return response

        with mock.patch('requests.request', side_effect=failing_request):
            c = curl('GET', 'http://api.com/data', max_retries=3)

            # Should eventually succeed after retries
            assert call_count[0] == 3, "Should have made 3 attempts"
            assert len(c.errors) == 0, "Should succeed after retries"
            assert c.request.status_code == 200

    def test_curl_no_retry_on_404_error(self):
        """4xx errors should NOT be retried (client errors are permanent)."""
        call_count = [0]

        def failing_request(*args, **kwargs):
            call_count[0] += 1
            response = mock.MagicMock()
            response.status_code = 404
            response.reason = "Not Found"
            response.text = "Resource not found"
            return response

        with mock.patch('requests.request', side_effect=failing_request):
            c = curl('GET', 'http://api.com/missing', max_retries=3)

            # Should NOT retry on 4xx errors
            assert call_count[0] == 1, "Should only attempt once (no retries for 4xx)"
            assert len(c.errors) > 0, "Should have error"
            assert "404" in c.errors[0]

    def test_curl_exponential_backoff(self):
        """Retries should use exponential backoff."""
        call_times = []

        def failing_request(*args, **kwargs):
            call_times.append(time.time())
            response = mock.MagicMock()
            response.status_code = 503
            response.reason = "Service Unavailable"
            response.text = "Retry later"
            return response

        with mock.patch('requests.request', side_effect=failing_request):
            c = curl('GET', 'http://api.com/data', max_retries=3, retry_backoff=0.1)

            # Check delays between attempts (initial + 3 retries = 4 total)
            assert len(call_times) == 4, "Should make 4 attempts (initial + 3 retries)"

            # Delays should be approximately: 0.1s, 0.2s, 0.4s (exponential)
            if len(call_times) >= 2:
                delay1 = call_times[1] - call_times[0]
                assert 0.08 < delay1 < 0.15, "First retry delay ~0.1s"

            if len(call_times) >= 3:
                delay2 = call_times[2] - call_times[1]
                assert 0.15 < delay2 < 0.30, "Second retry delay ~0.2s (exponential)"

            if len(call_times) >= 4:
                delay3 = call_times[3] - call_times[2]
                assert 0.35 < delay3 < 0.50, "Third retry delay ~0.4s (exponential)"

    def test_curl_max_retries_respected(self):
        """Should not retry more than max_retries times."""
        call_count = [0]

        def always_fails(*args, **kwargs):
            call_count[0] += 1
            raise requests.ConnectionError("Connection refused")

        with mock.patch('requests.request', side_effect=always_fails):
            c = curl('GET', 'http://dead-server.com', max_retries=2)

            # Should try initial + 2 retries = 3 total
            assert call_count[0] == 3, "Should attempt 3 times (initial + 2 retries)"
            assert len(c.errors) > 0, "Should have error"

    def test_curl_no_retry_by_default(self):
        """Default behavior: no retries (backward compatible)."""
        call_count = [0]

        def failing_request(*args, **kwargs):
            call_count[0] += 1
            response = mock.MagicMock()
            response.status_code = 503
            response.reason = "Service Unavailable"
            response.text = "Server error"
            return response

        with mock.patch('requests.request', side_effect=failing_request):
            # Default: max_retries=0
            c = curl('GET', 'http://api.com/data')

            # Should only try once (no retries by default)
            assert call_count[0] == 1, "Should only attempt once (default: no retries)"
            assert len(c.errors) > 0

    def test_curl_retries_on_connection_error(self):
        """Network errors (ConnectionError, Timeout) should be retried."""
        call_count = [0]

        def intermittent_failure(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise requests.ConnectionError("Connection refused")
            else:
                response = mock.MagicMock()
                response.status_code = 200
                response.text = '{"status": "ok"}'
                return response

        with mock.patch('requests.request', side_effect=intermittent_failure):
            c = curl('GET', 'http://api.com/data', max_retries=2)

            # Should succeed after retry
            assert call_count[0] == 2, "Should attempt twice"
            assert len(c.errors) == 0, "Should succeed after retry"
            assert c.request.status_code == 200
