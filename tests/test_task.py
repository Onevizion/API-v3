"""Tests for onevizion.task module."""
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
import onevizion.task
from onevizion.task import Task


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


class TestTaskInit(object):
    """Test Task.__init__."""

    def test_init_default(self):
        t = Task()
        assert t.URL == ""
        assert t.errors == []
        assert t.jsonData == {}

    def test_init_adds_https(self):
        t = Task(URL="test.onevizion.com")
        assert t.URL.startswith("https://")

    def test_init_explicit_url(self):
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        assert t.URL == "https://test.onevizion.com"
        assert isinstance(t.auth, requests.auth.HTTPBasicAuth)

    def test_init_token_auth(self):
        from onevizion.httpbearer import HTTPBearerAuth
        t = Task(URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
        assert isinstance(t.auth, HTTPBearerAuth)

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["task_tok"] = {
            "url": "task.onevizion.com",
            "UserName": "tu",
            "Password": "tp",
        }
        t = Task(paramToken="task_tok")
        assert "task.onevizion.com" in t.URL
        assert t.userName == "tu"

    def test_init_param_token_does_not_override_explicit(self):
        import onevizion
        onevizion.Config["ParameterData"]["task_tok2"] = {
            "url": "task.onevizion.com",
            "UserName": "tu",
            "Password": "tp",
        }
        t = Task(URL="https://explicit.onevizion.com", userName="eu", password="ep", paramToken="task_tok2")
        assert "explicit.onevizion.com" in t.URL
        assert t.userName == "eu"

    def test_init_param_token_with_token_auth(self):
        import onevizion
        from onevizion.httpbearer import HTTPBearerAuth
        onevizion.Config["ParameterData"]["task_tok3"] = {
            "url": "task.onevizion.com",
            "UserName": "k",
            "Password": "s",
            "isTokenAuth": True,
        }
        t = Task(paramToken="task_tok3")
        assert isinstance(t.auth, HTTPBearerAuth)


class TestTaskRead(object):
    """Test Task.read() - all URL building branches."""

    @mock.patch("onevizion.task.curl")
    def test_read_by_task_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"task_id": 10})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.read(taskId=10)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/tasks/10" in call_url
        assert t.jsonData == {"task_id": 10}

    @mock.patch("onevizion.task.curl")
    def test_read_by_workplan_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[{"task_id": 1}, {"task_id": 2}])
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.read(workplanId=5)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/wps/5/tasks" in call_url

    @mock.patch("onevizion.task.curl")
    def test_read_by_workplan_and_order_number(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"task_id": 3})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.read(workplanId=5, orderNumber=2)
        call_url = mock_curl_cls.call_args[0][1]
        assert "workplan_id=5" in call_url
        assert "order_number=2" in call_url

    @mock.patch("onevizion.task.curl")
    def test_read_resets_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.errors = ["stale error"]
        t.read(taskId=1)
        assert t.errors == []

    @mock.patch("onevizion.task.curl")
    def test_read_with_http_error(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found"]
        )
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.read(taskId=999)
        assert len(t.errors) > 0

    @mock.patch("onevizion.task.curl")
    def test_read_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Connection refused"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.read(taskId=1)
        assert len(t.errors) > 0


class TestTaskUpdate(object):
    """Test Task.update(), updatePartial(), and _update() methods."""

    @mock.patch("onevizion.task.curl")
    def test_update_puts_to_task_url(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"task_id": 10})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.update(taskId=10, fields={"task_name": "New Name"}, dynamicDates=[])
        call_args = mock_curl_cls.call_args[0]
        assert call_args[0] == "PUT"
        assert "/tasks/10" in call_args[1]

    @mock.patch("onevizion.task.curl")
    def test_update_partial_patches_to_task_url(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"task_id": 10})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.updatePartial(taskId=10, fields={"task_status": "Completed"}, dynamicDates=[])
        call_args = mock_curl_cls.call_args[0]
        assert call_args[0] == "PATCH"
        assert "/tasks/10" in call_args[1]

    @mock.patch("onevizion.task.curl")
    def test_update_with_dynamic_dates(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"task_id": 10})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        dynamic_dates = [{"date_name": "start_date", "value": "2024-01-01"}]
        t.update(taskId=10, fields={"task_name": "Test"}, dynamicDates=dynamic_dates)
        # dynamic_dates gets merged into fields
        call_kwargs = mock_curl_cls.call_args[1]
        assert "data" in call_kwargs
        payload = json.loads(call_kwargs["data"])
        assert "dynamic_dates" in payload

    @mock.patch("onevizion.task.curl")
    def test_update_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=400, errors=["400 = Bad Request"]
        )
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.update(taskId=10, fields={"bad_field": "value"}, dynamicDates=[])
        assert len(t.errors) > 0

    @mock.patch("onevizion.task.curl")
    def test_update_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Timeout"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.update(taskId=10, fields={"task_name": "Test"}, dynamicDates=[])
        assert len(t.errors) > 0

    @mock.patch("onevizion.task.curl")
    def test_update_resets_errors_and_json(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"task_id": 1})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.errors = ["old error"]
        t.jsonData = {"old": "data"}
        t.update(taskId=1, fields={}, dynamicDates=[])
        assert t.errors == []
        assert t.jsonData == {"task_id": 1}

    @mock.patch("onevizion.task.curl")
    def test_update_sends_json_content_type(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Task(URL="https://test.onevizion.com", userName="u", password="p")
        t.update(taskId=1, fields={"task_name": "Test"}, dynamicDates=[])
        call_kwargs = mock_curl_cls.call_args[1]
        assert call_kwargs.get("headers", {}).get("content-type") == "application/json"
