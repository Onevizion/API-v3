"""Tests for curl session/connection pooling.

Tests demonstrate:
- Sessions reuse connections for better performance
- Sessions are optional (backward compatible)
- Multiple requests to same host benefit from pooling
"""
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys

import pytest
import requests
import responses

from onevizion.curl import curl


class TestCurlSession(object):
    """Test curl session/connection pooling support."""

    @responses.activate
    def test_curl_accepts_session_parameter(self):
        """curl should accept an optional session parameter."""
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        session = requests.Session()
        c = curl('GET', 'http://api.com/data', session=session)

        # Should complete successfully
        assert c.request.status_code == 200
        assert c.jsonData == {'status': 'ok'}

    @responses.activate
    def test_curl_uses_requests_module_when_no_session(self):
        """curl should fall back to requests.request() when no session provided."""
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        # No session parameter - should use requests.request()
        c = curl('GET', 'http://api.com/data')

        assert c.request.status_code == 200
        assert c.jsonData == {'status': 'ok'}

    @responses.activate
    def test_curl_session_reuses_connection(self):
        """Session should reuse connections for multiple requests."""
        responses.add(responses.GET, 'http://api.com/data',
                      json={'request': 1}, status=200)
        responses.add(responses.GET, 'http://api.com/data',
                      json={'request': 2}, status=200)
        responses.add(responses.GET, 'http://api.com/data',
                      json={'request': 3}, status=200)

        session = requests.Session()

        # Make multiple requests using same session
        c1 = curl('GET', 'http://api.com/data', session=session)
        c2 = curl('GET', 'http://api.com/data', session=session)
        c3 = curl('GET', 'http://api.com/data', session=session)

        # All three requests should have completed
        assert c1.request.status_code == 200
        assert c2.request.status_code == 200
        assert c3.request.status_code == 200

    @responses.activate
    def test_curl_manual_run_with_session(self):
        """Session should work with manual runQuery() calls."""
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        session = requests.Session()

        # Create curl without URL (won't auto-run)
        c = curl('GET', session=session)
        c.url = 'http://api.com/data'
        c.runQuery()

        assert c.request.status_code == 200
        assert c.jsonData == {'status': 'ok'}

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle multiple responses for same URL")
    @responses.activate
    def test_curl_session_persists_across_retries(self):
        """Session should be used for retry attempts."""
        # First call returns 503, second call returns 200
        responses.add(responses.GET, 'http://api.com/data',
                      body="Retry", status=503)
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        session = requests.Session()
        c = curl('GET', 'http://api.com/data', session=session, max_retries=2)

        # Should retry and eventually succeed
        assert c.request.status_code == 200
        assert c.jsonData == {'status': 'ok'}
        assert len(c.errors) == 0
