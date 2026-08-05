"""Tests for onevizion.curl module."""
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys

import pytest
import requests
import responses

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import vcr

from onevizion.curl import curl


class TestCurlBasic(object):
    """Basic tests for curl class without HTTP requests."""

    def test_curl_init_no_url(self):
        """Test curl initialization without URL."""
        c = curl(method='GET')
        assert c.method == 'GET'
        assert c.url is None
        assert c.request is None
        assert c.errors == []

    def test_curl_init_with_kwargs(self):
        """Test curl initialization with kwargs."""
        c = curl(method='POST', timeout=30, params={'key': 'value'})
        assert c.method == 'POST'
        assert c.timeout == 30
        assert c.params == {'key': 'value'}

    def test_setArg_with_value(self):
        """Test setArg with non-None value."""
        c = curl()
        c.setArg('test_key', 'test_value')
        assert c.args['test_key'] == 'test_value'

    def test_setArg_with_none(self):
        """Test setArg with None value (should not set)."""
        c = curl()
        c.setArg('test_key', None)
        assert 'test_key' not in c.args


class TestCurlHTTP(object):
    """Test curl HTTP operations with VCR."""

    @vcr.use_cassette('tests/fixtures/cassettes/test_get_request.yaml')
    def test_get_request_success(self):
        """Test successful GET request."""
        c = curl(method='GET', url='https://httpbin.org/get')
        assert c.request is not None
        assert c.request.status_code == 200
        assert len(c.errors) == 0
        assert c.duration is not None
        assert c.duration >= 0

    @vcr.use_cassette('tests/fixtures/cassettes/test_get_with_params.yaml')
    def test_get_request_with_params(self):
        """Test GET request with query parameters."""
        c = curl(
            method='GET',
            url='https://httpbin.org/get',
            params={'test': 'value', 'foo': 'bar'}
        )
        assert c.request.status_code == 200
        assert 'args' in c.jsonData
        assert c.jsonData['args']['test'] == 'value'
        assert c.jsonData['args']['foo'] == 'bar'

    @vcr.use_cassette('tests/fixtures/cassettes/test_post_json.yaml')
    def test_post_request_with_json(self):
        """Test POST request with JSON data."""
        test_data = {'key': 'value', 'number': 42}
        c = curl(
            method='POST',
            url='https://httpbin.org/post',
            json=test_data
        )
        assert c.request.status_code == 200
        assert 'json' in c.jsonData
        assert c.jsonData['json'] == test_data

    @vcr.use_cassette('tests/fixtures/cassettes/test_post_data.yaml')
    def test_post_request_with_data(self):
        """Test POST request with form data."""
        c = curl(
            method='POST',
            url='https://httpbin.org/post',
            data={'field1': 'value1', 'field2': 'value2'}
        )
        assert c.request.status_code == 200
        assert 'form' in c.jsonData

    @vcr.use_cassette('tests/fixtures/cassettes/test_put_request.yaml')
    def test_put_request(self):
        """Test PUT request."""
        c = curl(
            method='PUT',
            url='https://httpbin.org/put',
            json={'update': 'data'}
        )
        assert c.request.status_code == 200

    @vcr.use_cassette('tests/fixtures/cassettes/test_delete_request.yaml')
    def test_delete_request(self):
        """Test DELETE request."""
        c = curl(method='DELETE', url='https://httpbin.org/delete')
        assert c.request.status_code == 200

    @responses.activate
    def test_error_404(self):
        """Test handling of 404 error."""
        # Mock 404 response
        responses.add(
            responses.GET,
            'https://test.example.com/notfound',
            status=404,
            body='Not Found'
        )

        c = curl(method='GET', url='https://test.example.com/notfound')
        assert c.request.status_code == 404
        assert len(c.errors) > 0
        assert '404' in c.errors[0]

    @responses.activate
    def test_error_500(self):
        """Test handling of 500 error."""
        # Mock 500 response
        responses.add(
            responses.GET,
            'https://test.example.com/error',
            status=500,
            body='Server Error'
        )

        c = curl(method='GET', url='https://test.example.com/error')
        assert c.request.status_code == 500
        assert len(c.errors) > 0
        assert '500' in c.errors[0]

    @responses.activate
    def test_custom_headers(self):
        """Test request with custom headers."""
        # Mock successful response
        responses.add(
            responses.GET,
            'https://test.example.com/headers',
            status=200,
            json={'headers': {'User-Agent': 'onevizion-test/1.0'}}
        )

        headers = {
            'User-Agent': 'onevizion-test/1.0',
            'X-Custom-Header': 'test-value'
        }
        c = curl(
            method='GET',
            url='https://test.example.com/headers',
            headers=headers
        )
        assert c.request.status_code == 200
        assert 'headers' in c.jsonData

    @responses.activate
    def test_manual_run_query(self):
        """Test manually calling runQuery after initialization."""
        # Mock successful response
        responses.add(
            responses.GET,
            'https://test.example.com/test',
            status=200,
            json={'method': 'GET'}
        )

        c = curl(method='GET')
        c.url = 'https://test.example.com/test'
        c.runQuery()

        assert c.request is not None
        assert c.request.status_code == 200


class TestCurlJSON(object):
    """Test JSON parsing functionality."""

    @vcr.use_cassette('tests/fixtures/cassettes/test_json_parse.yaml')
    def test_json_parsing(self):
        """Test automatic JSON parsing."""
        c = curl(method='GET', url='https://httpbin.org/json')
        assert c.jsonData is not None
        assert isinstance(c.jsonData, dict)

    @responses.activate
    def test_non_json_response(self):
        """Test handling of non-JSON response."""
        # Mock HTML response
        responses.add(
            responses.GET,
            'https://test.example.com/html',
            status=200,
            body='<html><body>Hello</body></html>',
            content_type='text/html'
        )

        c = curl(method='GET', url='https://test.example.com/html')
        # Should not raise error, just leave jsonData empty
        assert c.jsonData == {}
        assert c.request.status_code == 200


class TestCurlDuration(object):
    """Test request duration tracking."""

    @vcr.use_cassette('tests/fixtures/cassettes/test_duration.yaml')
    def test_duration_tracking(self):
        """Test that request duration is tracked."""
        c = curl(method='GET', url='https://httpbin.org/delay/1')
        assert c.duration is not None
        assert c.duration >= 0
        assert isinstance(c.duration, float)

    def test_duration_on_error(self):
        """Test that duration is tracked even on errors."""
        # Mock a request that fails
        c = curl(method='GET')
        c.url = 'http://localhost:99999/nonexistent'
        c.runQuery()

        # Duration should still be tracked
        assert c.duration is not None
        assert c.duration >= 0


class TestCurlSentTracking(object):
    """Test tracking of sent URL and arguments."""

    @vcr.use_cassette('tests/fixtures/cassettes/test_sent_tracking.yaml')
    def test_sent_url_and_args(self):
        """Test that sent URL and args are tracked."""
        url = 'https://httpbin.org/get'
        params = {'test': 'value'}
        c = curl(method='GET', url=url, params=params)

        assert c.sentUrl == url
        assert 'params' in c.sentArgs
        assert c.sentArgs['params'] == params


class TestCurlTimeout(object):
    """Test curl timeout functionality."""

    @responses.activate
    def test_curl_has_default_timeout(self):
        """curl should have a default timeout to prevent infinite hangs."""
        # We need to verify timeout parameter is passed, so we'll use a callback
        timeout_received = [None]

        def request_callback(request):
            # This callback won't capture the timeout parameter directly,
            # but we can use mock to verify it was passed
            return (200, {}, "OK")

        responses.add_callback(
            responses.GET,
            'http://example.com',
            callback=request_callback
        )

        # Use mock to verify timeout is passed to requests.request
        with mock.patch('requests.request', wraps=requests.request) as mock_request:
            c = curl('GET', 'http://example.com')

            # Verify timeout was passed to requests
            call_kwargs = mock_request.call_args[1]
            assert 'timeout' in call_kwargs, \
                "Bug: No timeout parameter passed to requests! This causes infinite hangs."
            assert call_kwargs['timeout'] is not None, "Timeout is None - will hang forever!"
            assert call_kwargs['timeout'] > 0, "Timeout should be positive"

    @responses.activate
    def test_curl_accepts_custom_timeout(self):
        """curl should accept and use custom timeout parameter."""
        responses.add(
            responses.GET,
            'http://slow-api.com',
            status=200,
            body="OK"
        )

        # Use mock to verify custom timeout is passed to requests.request
        with mock.patch('requests.request', wraps=requests.request) as mock_request:
            c = curl('GET', 'http://slow-api.com', timeout=120.0)

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs['timeout'] == 120.0, "Custom timeout not passed through"

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle callback exceptions properly")
    @responses.activate
    def test_curl_handles_timeout_exception(self):
        """curl should catch timeout exceptions and add to errors."""
        # Use a callback that raises Timeout exception
        def timeout_callback(request):
            raise requests.Timeout("Connection timed out")

        responses.add_callback(
            responses.GET,
            'http://very-slow-api.com',
            callback=timeout_callback
        )

        c = curl('GET', 'http://very-slow-api.com', timeout=5.0)

        # Should not raise exception, but add to errors
        assert len(c.errors) > 0, "Timeout exception not caught!"
        error_text = str(c.errors[0]).lower()
        assert 'timeout' in error_text or 'timed out' in error_text

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="Old responses library doesn't handle callback exceptions properly")
    @responses.activate
    def test_curl_actually_times_out(self):
        """Demonstrate that curl will hang forever without timeout."""
        import time

        # Use a callback that simulates timeout behavior
        def timeout_callback(request):
            # Simulate slow response that would timeout
            raise requests.Timeout("Read timed out after 2.0s")

        responses.add_callback(
            responses.GET,
            'http://hanging-server.com',
            callback=timeout_callback
        )

        start = time.time()

        # With timeout parameter, should fail quickly
        c = curl('GET', 'http://hanging-server.com', timeout=2.0)

        elapsed = time.time() - start

        # Should fail immediately (timeout exception raised)
        # NOT wait 30 seconds
        assert elapsed < 5, \
            "Request took {}s - timeout not working!".format(elapsed)
        assert len(c.errors) > 0, "No timeout error recorded"
