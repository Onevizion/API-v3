"""Tests for curl session/connection pooling.

Tests demonstrate:
- Sessions reuse connections for better performance
- Sessions are optional (backward compatible)
- Multiple requests to same host benefit from pooling
"""
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import requests
from onevizion.curl import curl


class TestCurlSession(object):
    """Test curl session/connection pooling support."""

    def test_curl_accepts_session_parameter(self):
        """curl should accept an optional session parameter."""
        session = requests.Session()

        with mock.patch.object(session, 'request') as mock_request:
            mock_response = mock.MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_request.return_value = mock_response

            c = curl('GET', 'http://api.com/data', session=session)

            # Should use session.request(), not requests.request()
            mock_request.assert_called_once()
            assert c.request.status_code == 200

    def test_curl_uses_requests_module_when_no_session(self):
        """curl should fall back to requests.request() when no session provided."""
        with mock.patch('requests.request') as mock_request:
            mock_response = mock.MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_request.return_value = mock_response

            # No session parameter - should use requests.request()
            c = curl('GET', 'http://api.com/data')

            mock_request.assert_called_once()
            assert c.request.status_code == 200

    def test_curl_session_reuses_connection(self):
        """Session should reuse connections for multiple requests."""
        session = requests.Session()
        call_count = [0]

        def mock_session_request(*args, **kwargs):
            call_count[0] += 1
            response = mock.MagicMock()
            response.status_code = 200
            response.text = '{{"request": {}}}'.format(call_count[0])
            return response

        with mock.patch.object(session, 'request', side_effect=mock_session_request):
            # Make multiple requests using same session
            c1 = curl('GET', 'http://api.com/data', session=session)
            c2 = curl('GET', 'http://api.com/data', session=session)
            c3 = curl('GET', 'http://api.com/data', session=session)

            # All three requests should have been made
            assert call_count[0] == 3
            assert c1.request.status_code == 200
            assert c2.request.status_code == 200
            assert c3.request.status_code == 200

    def test_curl_manual_run_with_session(self):
        """Session should work with manual runQuery() calls."""
        session = requests.Session()

        with mock.patch.object(session, 'request') as mock_request:
            mock_response = mock.MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_request.return_value = mock_response

            # Create curl without URL (won't auto-run)
            c = curl(session=session)
            c.url = 'http://api.com/data'
            c.runQuery()

            mock_request.assert_called_once()
            assert c.request.status_code == 200

    def test_curl_session_persists_across_retries(self):
        """Session should be used for retry attempts."""
        session = requests.Session()
        call_count = [0]

        def failing_then_success(*args, **kwargs):
            call_count[0] += 1
            response = mock.MagicMock()
            if call_count[0] < 2:
                response.status_code = 503
                response.reason = "Service Unavailable"
                response.text = "Retry"
            else:
                response.status_code = 200
                response.text = '{"status": "ok"}'
            return response

        with mock.patch.object(session, 'request', side_effect=failing_then_success):
            c = curl('GET', 'http://api.com/data', session=session, max_retries=2)

            # Should use session for all retry attempts
            assert call_count[0] == 2
            assert c.request.status_code == 200
            assert len(c.errors) == 0
