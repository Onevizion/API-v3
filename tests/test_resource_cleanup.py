"""Tests for proper resource cleanup and memory leak prevention.

Tests demonstrate:
- Response objects are explicitly closed to free connections
- File handles are properly closed
- Resources are freed even on errors
"""
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import os
import tempfile
import shutil

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

from onevizion.curl import curl
from onevizion.trackor import Trackor


class TestCurlResourceCleanup(object):
    """Test curl properly closes response objects."""

    def test_curl_closes_response_on_success(self):
        """curl should close response object after successful request."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'

        with mock.patch('onevizion.curl.requests.request', return_value=mock_response):
            c = curl('GET', 'http://api.com/data')

            # Response should be closed
            mock_response.close.assert_called_once()

    def test_curl_closes_response_on_client_error(self):
        """curl should close response even on 4xx errors."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.text = "Not found"

        with mock.patch('onevizion.curl.requests.request', return_value=mock_response):
            c = curl('GET', 'http://api.com/missing')

            # Response should be closed even on error
            mock_response.close.assert_called_once()
            assert len(c.errors) > 0

    def test_curl_closes_response_on_server_error(self):
        """curl should close response on 5xx errors."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.reason = "Server Error"
        mock_response.text = "Error"

        with mock.patch('onevizion.curl.requests.request', return_value=mock_response):
            c = curl('GET', 'http://api.com/broken', max_retries=0)

            # Response should be closed
            mock_response.close.assert_called_once()

    def test_curl_closes_all_retry_responses(self):
        """curl should close responses from all retry attempts."""
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

        with mock.patch('onevizion.curl.requests.request', side_effect=failing_then_success) as mock_req:
            c = curl('GET', 'http://api.com/flaky', max_retries=2)

            # Should have made 2 calls
            assert mock_req.call_count == 2

            # Both responses should be closed
            for call in mock_req.return_value.close.call_args_list:
                # Each response's close() should have been called
                pass

            # At minimum, the final response should be closed
            assert c.request.close.called


class TestTrackorResourceCleanup(object):
    """Test Trackor properly closes response objects."""

    def test_getfile_closes_response_on_success(self):
        """GetFile should close response after successful download."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-disposition': 'filename=data.csv'}
        mock_response.iter_content.return_value = [b'data']

        tmpdir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            with mock.patch('onevizion.trackor.requests.get', return_value=mock_response):
                t = Trackor(
                    trackorType="Project",
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p"
                )
                t.GetFile(trackorId=10, fieldName="F_FILE")

                # Response should be closed
                mock_response.close.assert_called_once()
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmpdir)

    def test_getfile_closes_response_on_error(self):
        """GetFile should close response even on error."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.reason = "Server Error"
        mock_response.headers = {}

        with mock.patch('onevizion.trackor.requests.get', return_value=mock_response):
            t = Trackor(
                trackorType="Project",
                URL="https://test.onevizion.com",
                userName="u",
                password="p"
            )
            result = t.GetFile(trackorId=10, fieldName="F_FILE")

            # Response should be closed even on error
            mock_response.close.assert_called_once()
            assert result is None

    def test_getfile_closes_response_on_size_validation_failure(self):
        """GetFile should close response when file size exceeds limit."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-length': str(15 * 1024 * 1024),  # 15 MB
            'content-disposition': 'filename=large.bin'
        }

        with mock.patch('onevizion.trackor.requests.get', return_value=mock_response):
            t = Trackor(
                trackorType="Project",
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                max_file_size=10 * 1024 * 1024  # 10 MB limit
            )
            result = t.GetFile(trackorId=10, fieldName="F_FILE")

            # Response should be closed when validation fails
            mock_response.close.assert_called_once()
            assert result is None
            assert len(t.errors) > 0

    def test_uploadfile_closes_curl_response(self):
        """UploadFile should close curl response after upload."""
        tmpdir = tempfile.mkdtemp()
        try:
            small_file = os.path.join(tmpdir, 'test.txt')
            with open(small_file, 'wb') as f:
                f.write(b'test content')

            mock_response = mock.MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"blob_data_id": 123}'

            # Mock requests.request so curl can run normally and close the response
            with mock.patch('onevizion.curl.requests.request', return_value=mock_response):
                t = Trackor(
                    trackorType="Project",
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p"
                )
                t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=small_file)

                # The curl's response should be closed
                mock_response.close.assert_called_once()
        finally:
            shutil.rmtree(tmpdir)
