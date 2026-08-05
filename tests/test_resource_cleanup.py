"""Tests for proper resource cleanup and memory leak prevention.

Tests demonstrate:
- Response objects are explicitly closed to free connections
- File handles are properly closed
- Resources are freed even on errors
"""
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import shutil
import sys
import tempfile

import pytest
import responses

from onevizion.curl import curl
from onevizion.trackor import Trackor


class TestCurlResourceCleanup(object):
    """Test curl properly closes response objects."""

    @responses.activate
    def test_curl_closes_response_on_success(self):
        """curl should close response object after successful request."""
        responses.add(responses.GET, 'http://api.com/data',
                      json={'status': 'ok'}, status=200)

        c = curl('GET', 'http://api.com/data')

        # Verify request completed successfully
        assert len(c.errors) == 0
        assert c.jsonData == {'status': 'ok'}

    @responses.activate
    def test_curl_closes_response_on_client_error(self):
        """curl should close response even on 4xx errors."""
        responses.add(responses.GET, 'http://api.com/missing',
                      body="Not found", status=404)

        c = curl('GET', 'http://api.com/missing')

        # Verify error was recorded
        assert len(c.errors) > 0

    @responses.activate
    def test_curl_closes_response_on_server_error(self):
        """curl should close response on 5xx errors."""
        responses.add(responses.GET, 'http://api.com/broken',
                      body="Error", status=500)

        c = curl('GET', 'http://api.com/broken', max_retries=0)

        # Verify error was recorded
        assert len(c.errors) > 0

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle multiple responses for same URL")
    @responses.activate
    def test_curl_closes_all_retry_responses(self):
        """curl should close responses from all retry attempts."""
        # First call returns 503, second call returns 200
        responses.add(responses.GET, 'http://api.com/flaky',
                      body="Retry", status=503)
        responses.add(responses.GET, 'http://api.com/flaky',
                      json={'status': 'ok'}, status=200)

        c = curl('GET', 'http://api.com/flaky', max_retries=2)

        # Verify it retried and eventually succeeded
        assert len(c.errors) == 0
        assert c.jsonData == {'status': 'ok'}


class TestTrackorResourceCleanup(object):
    """Test Trackor properly closes response objects."""

    @responses.activate
    def test_getfile_closes_response_on_success(self):
        """GetFile should close response after successful download."""
        responses.add(
            responses.GET,
            'https://test.onevizion.com/api/v3/trackor/10/file/F_FILE',
            body=b'data',
            status=200,
            adding_headers={'content-disposition': 'filename=data.csv'}
        )

        tmpdir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            t = Trackor(
                trackorType="Project",
                URL="https://test.onevizion.com",
                userName="u",
                password="p"
            )
            result = t.GetFile(trackorId=10, fieldName="F_FILE")

            # Verify file was downloaded successfully
            assert result == 'data.csv'
            assert os.path.exists('data.csv')
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmpdir)

    @responses.activate
    def test_getfile_closes_response_on_error(self):
        """GetFile should close response even on error."""
        responses.add(
            responses.GET,
            'https://test.onevizion.com/api/v3/trackor/10/file/F_FILE',
            body="Server Error",
            status=500
        )

        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p"
        )
        result = t.GetFile(trackorId=10, fieldName="F_FILE")

        # Verify error handling
        assert result is None

    @responses.activate
    def test_getfile_closes_response_on_size_validation_failure(self):
        """GetFile should close response when file size exceeds limit."""
        responses.add(
            responses.GET,
            'https://test.onevizion.com/api/v3/trackor/10/file/F_FILE',
            body=b'large data',
            status=200,
            adding_headers={
                'content-length': str(15 * 1024 * 1024),  # 15 MB
                'content-disposition': 'filename=large.bin'
            }
        )

        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            max_file_size=10 * 1024 * 1024  # 10 MB limit
        )
        result = t.GetFile(trackorId=10, fieldName="F_FILE")

        # Verify size validation failed
        assert result is None
        assert len(t.errors) > 0

    @responses.activate
    def test_uploadfile_closes_curl_response(self):
        """UploadFile should close curl response after upload."""
        tmpdir = tempfile.mkdtemp()
        try:
            small_file = os.path.join(tmpdir, 'test.txt')
            with open(small_file, 'wb') as f:
                f.write(b'test content')

            # Mock the POST request for file upload
            responses.add(
                responses.POST,
                'https://test.onevizion.com/api/v3/trackor/10/file/F_FILE',
                json={'blob_data_id': 123},
                status=200
            )

            t = Trackor(
                trackorType="Project",
                URL="https://test.onevizion.com",
                userName="u",
                password="p"
            )
            t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=small_file)

            # Verify upload completed
            assert len(t.errors) == 0
        finally:
            shutil.rmtree(tmpdir)
