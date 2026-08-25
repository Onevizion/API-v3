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

import pytest
import requests
import responses

if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

from onevizion.curl import curl


class TestCurlRetry(object):
    """Test curl retry logic for transient failures."""

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle multiple responses for same URL")
    @responses.activate
    def test_curl_retries_on_500_error(self):
        """5xx errors should be retried (server errors are transient)."""
        # First 2 calls fail with 503
        responses.add(responses.GET, 'http://api.com/data',
                      body="Server overloaded", status=503)
        responses.add(responses.GET, 'http://api.com/data',
                      body="Server overloaded", status=503)
        # Third call succeeds
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        c = curl('GET', 'http://api.com/data', max_retries=3)

        # Should eventually succeed after retries
        assert len(responses.calls) == 3, "Should have made 3 attempts"
        assert len(c.errors) == 0, "Should succeed after retries"
        assert c.request.status_code == 200

    @responses.activate
    def test_curl_no_retry_on_404_error(self):
        """4xx errors should NOT be retried (client errors are permanent)."""
        responses.add(responses.GET, 'http://api.com/missing',
                      body="Resource not found", status=404)

        c = curl('GET', 'http://api.com/missing', max_retries=3)

        # Should NOT retry on 4xx errors
        assert len(responses.calls) == 1, "Should only attempt once (no retries for 4xx)"
        assert len(c.errors) > 0, "Should have error"
        assert "404" in c.errors[0]

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle multiple responses for same URL")
    @responses.activate
    def test_curl_exponential_backoff(self):
        """Retries should use exponential backoff."""
        call_times = []

        def request_callback(request):
            call_times.append(time.time())
            return (503, {}, "Retry later")

        # Need 4 responses total (initial + 3 retries)
        responses.add_callback(responses.GET, 'http://api.com/data',
                               callback=request_callback)
        responses.add_callback(responses.GET, 'http://api.com/data',
                               callback=request_callback)
        responses.add_callback(responses.GET, 'http://api.com/data',
                               callback=request_callback)
        responses.add_callback(responses.GET, 'http://api.com/data',
                               callback=request_callback)

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

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle multiple responses for same URL")
    @responses.activate
    def test_curl_max_retries_respected(self):
        """Should not retry more than max_retries times."""
        # Add 3 responses (initial + 2 retries)
        responses.add(responses.GET, 'http://dead-server.com',
                      body=requests.ConnectionError("Connection refused"))
        responses.add(responses.GET, 'http://dead-server.com',
                      body=requests.ConnectionError("Connection refused"))
        responses.add(responses.GET, 'http://dead-server.com',
                      body=requests.ConnectionError("Connection refused"))

        c = curl('GET', 'http://dead-server.com', max_retries=2)

        # Should try initial + 2 retries = 3 total
        assert len(responses.calls) == 3, "Should attempt 3 times (initial + 2 retries)"
        assert len(c.errors) > 0, "Should have error"

    @responses.activate
    def test_curl_no_retry_by_default(self):
        """Default behavior: no retries (backward compatible)."""
        responses.add(responses.GET, 'http://api.com/data',
                      body="Server error", status=503)

        # Default: max_retries=0
        c = curl('GET', 'http://api.com/data')

        # Should only try once (no retries by default)
        assert len(responses.calls) == 1, "Should only attempt once (default: no retries)"
        assert len(c.errors) > 0

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle multiple responses for same URL")
    @responses.activate
    def test_curl_retries_on_connection_error(self):
        """Network errors (ConnectionError, Timeout) should be retried."""
        # First call fails with ConnectionError
        responses.add(responses.GET, 'http://api.com/data',
                      body=requests.ConnectionError("Connection refused"))
        # Second call succeeds
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        c = curl('GET', 'http://api.com/data', max_retries=2)

        # Should succeed after retry
        assert len(responses.calls) == 2, "Should attempt twice"
        assert len(c.errors) == 0, "Should succeed after retry"
        assert c.request.status_code == 200

    def test_sub_200_status_terminates_loop(self):
        """Statuses below 200 must error out instead of spinning the retry loop.

        Regression test for the fallthrough at curl.py:223-225. A 1xx response
        matched no branch, so `attempt` was never incremented and the loop ran
        forever.

        The stub stops serving responses after a bounded number of requests so
        that a regression cannot hang CI until the job timeout. Its error is
        absorbed by the catch-all handler at curl.py:237, which breaks the
        loop, so the failure surfaces as the call-count assertion below (4 != 1)
        rather than as a raised exception.
        """
        calls = []

        def _informational(*args, **kwargs):
            calls.append(1)
            if len(calls) > 3:
                raise AssertionError(
                    "retry loop did not terminate on a sub-200 status "
                    "({0} requests made)".format(len(calls))
                )
            resp = mock.MagicMock()
            resp.status_code = 100
            resp.reason = "Continue"
            resp.text = ""
            return resp

        # patch.object on the module, not a dotted path: the py2.7 mock backport
        # cannot resolve "onevizion.curl.requests.request" through a module
        # attribute. onevizion.curl uses this same requests module object.
        with mock.patch.object(requests, "request", side_effect=_informational):
            c = curl('GET', 'http://api.com/informational', max_retries=2)

        assert len(calls) == 1, "sub-200 status is permanent and must not be retried"
        assert len(c.errors) > 0, "sub-200 status should record an error"
        assert "100" in c.errors[0]
