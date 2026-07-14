"""Tests for onevizion.curl module."""
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

    @vcr.use_cassette('tests/fixtures/cassettes/test_404_error.yaml')
    def test_error_404(self):
        """Test handling of 404 error."""
        c = curl(method='GET', url='https://httpbin.org/status/404')
        assert c.request.status_code == 404
        assert len(c.errors) > 0
        assert '404' in c.errors[0]

    @vcr.use_cassette('tests/fixtures/cassettes/test_500_error.yaml')
    def test_error_500(self):
        """Test handling of 500 error."""
        c = curl(method='GET', url='https://httpbin.org/status/500')
        assert c.request.status_code == 500
        assert len(c.errors) > 0
        assert '500' in c.errors[0]

    @vcr.use_cassette('tests/fixtures/cassettes/test_custom_headers.yaml')
    def test_custom_headers(self):
        """Test request with custom headers."""
        headers = {
            'User-Agent': 'onevizion-test/1.0',
            'X-Custom-Header': 'test-value'
        }
        c = curl(
            method='GET',
            url='https://httpbin.org/headers',
            headers=headers
        )
        assert c.request.status_code == 200
        assert 'headers' in c.jsonData

    def test_manual_run_query(self):
        """Test manually calling runQuery after initialization."""
        c = curl(method='GET')
        c.url = 'https://httpbin.org/get'

        # Use VCR for this test
        with vcr.use_cassette('tests/fixtures/cassettes/test_manual_run.yaml'):
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

    @vcr.use_cassette('tests/fixtures/cassettes/test_non_json_response.yaml')
    def test_non_json_response(self):
        """Test handling of non-JSON response."""
        c = curl(method='GET', url='https://httpbin.org/html')
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
