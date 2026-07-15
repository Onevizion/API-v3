"""Tests for onevizion.workplan module."""
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys
import json

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import requests
import onevizion.workplan
from onevizion.workplan import WorkPlan


def make_mock_curl(status_code=200, json_data=None, errors=None, duration=0.1):
    m = mock.MagicMock()
    m.errors = errors if errors is not None else []
    m.jsonData = json_data if json_data is not None else {}
    m.duration = duration
    mock_request = mock.MagicMock()
    mock_request.status_code = status_code
    mock_request.reason = "OK" if status_code == 200 else "Error"
    mock_request.text = json.dumps(json_data) if json_data else ""
    m.request = mock_request
    return m


class TestWorkPlanInit(object):
    """Test WorkPlan.__init__."""

    def test_init_defaults(self):
        wp = WorkPlan()
        assert wp.URL == ""
        assert wp.errors == []
        assert wp.jsonData == {}

    def test_init_adds_https(self):
        wp = WorkPlan(URL="test.onevizion.com")
        assert wp.URL.startswith("https://")

    def test_init_explicit_url(self):
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        assert wp.URL == "https://test.onevizion.com"
        assert isinstance(wp.auth, requests.auth.HTTPBasicAuth)

    def test_init_token_auth(self):
        from onevizion.httpbearer import HTTPBearerAuth
        wp = WorkPlan(URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
        assert isinstance(wp.auth, HTTPBearerAuth)

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["wp_tok"] = {
            "url": "wp.onevizion.com",
            "UserName": "wu",
            "Password": "wp",
        }
        wp = WorkPlan(paramToken="wp_tok")
        assert "wp.onevizion.com" in wp.URL
        assert wp.userName == "wu"

    def test_init_param_token_does_not_override_explicit(self):
        import onevizion
        onevizion.Config["ParameterData"]["wp_tok2"] = {
            "url": "wp.onevizion.com",
            "UserName": "wu",
            "Password": "wp",
        }
        wp = WorkPlan(URL="https://explicit.onevizion.com", userName="eu", password="ep", paramToken="wp_tok2")
        assert "explicit.onevizion.com" in wp.URL
        assert wp.userName == "eu"

    def test_init_param_token_with_token_auth(self):
        import onevizion
        from onevizion.httpbearer import HTTPBearerAuth
        onevizion.Config["ParameterData"]["wp_tok3"] = {
            "url": "wp.onevizion.com",
            "UserName": "k",
            "Password": "s",
            "isTokenAuth": True,
        }
        wp = WorkPlan(paramToken="wp_tok3")
        assert isinstance(wp.auth, HTTPBearerAuth)


class TestWorkPlanRead(object):
    """Test WorkPlan.read() - all URL building branches."""

    @mock.patch("onevizion.workplan.curl", create=True)
    def test_read_by_workplan_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 42, "name": "My Plan"})
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        wp.read(workplanId=42)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/wps/42" in call_url
        assert wp.jsonData == {"wp_id": 42, "name": "My Plan"}

    @mock.patch("onevizion.workplan.curl", create=True)
    def test_read_by_template_and_trackor(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 10})
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        wp.read(workplanTemplate="Default WP", trackorType="Project", trackorId=123)
        call_url = mock_curl_cls.call_args[0][1]
        assert "wp_template=" in call_url
        assert "trackor_type=" in call_url
        assert "trackor_id=123" in call_url

    @mock.patch("onevizion.workplan.curl", create=True)
    def test_read_resets_errors_and_json(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 1})
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        wp.errors = ["stale"]
        wp.jsonData = {"old": "data"}
        wp.read(workplanId=1)
        assert wp.errors == []
        assert wp.jsonData == {"wp_id": 1}

    @mock.patch("onevizion.workplan.curl", create=True)
    def test_read_with_http_error(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found"]
        )
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        wp.read(workplanId=999)
        assert len(wp.errors) > 0

    @mock.patch("onevizion.workplan.curl", create=True)
    def test_read_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Network error"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        wp.read(workplanId=1)
        assert len(wp.errors) > 0

    @mock.patch("onevizion.workplan.curl", create=True)
    def test_read_uses_get_method(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        wp = WorkPlan(URL="https://test.onevizion.com", userName="u", password="p")
        wp.read(workplanId=1)
        assert mock_curl_cls.call_args[0][0] == "GET"
