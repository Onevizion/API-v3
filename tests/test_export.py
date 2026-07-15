"""Tests for onevizion.export module."""
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
import onevizion.export
from onevizion.export import Export


def make_mock_curl(status_code=200, json_data=None, errors=None, duration=0.1):
    m = mock.MagicMock()
    m.errors = errors if errors is not None else []
    m.jsonData = json_data if json_data is not None else {}
    m.duration = duration
    mock_request = mock.MagicMock()
    mock_request.status_code = status_code
    mock_request.reason = "OK" if status_code == 200 else "Error"
    mock_request.text = json.dumps(json_data) if json_data else ""
    mock_request.content = b"col1,col2\nval1,val2\n"
    m.request = mock_request
    return m


class TestExportInit(object):
    """Test Export.__init__ behaviour."""

    def test_init_no_args_does_not_run(self):
        exp = Export()
        assert exp.processId is None
        assert exp.errors == []

    def test_init_stores_attributes(self):
        exp = Export(
            URL="https://test.onevizion.com",
            userName="user",
            password="pass",
            trackorType="Project",
            exportMode="CSV",
            delivery="File",
        )
        assert exp.URL == "https://test.onevizion.com"
        assert exp.trackorType == "Project"
        assert exp.exportMode == "CSV"
        assert exp.delivery == "File"

    def test_init_adds_https_to_url(self):
        exp = Export(URL="bare.onevizion.com")
        assert exp.URL.startswith("https://")

    def test_init_empty_url_stays_empty(self):
        exp = Export()
        assert exp.URL == ""

    def test_init_defaults(self):
        exp = Export()
        assert exp.exportMode == "CSV"
        assert exp.delivery == "File"
        assert exp.filters == {}
        assert exp.fields == []
        assert exp.content is None

    @mock.patch("onevizion.export.curl")
    def test_init_runs_when_all_params_present_with_fields_and_filters(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"process_id": 5, "status": "QUEUED"}
        )
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS", "F_NAME"],
            filters={"F_STATUS": "Active"},
        )
        assert exp.processId == 5

    @mock.patch("onevizion.export.curl")
    def test_init_runs_when_view_options_and_filter_options_present(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"process_id": 6, "status": "QUEUED"}
        )
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            viewOptions="MyView",
            filterOptions="F_STATUS eq 'Active'",
        )
        assert exp.processId == 6

    def test_init_does_not_run_without_trackor_type(self):
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert exp.processId is None

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["exp_tok"] = {
            "url": "exp.onevizion.com",
            "UserName": "eu",
            "Password": "ep",
        }
        exp = Export(paramToken="exp_tok")
        assert "exp.onevizion.com" in exp.URL
        assert exp.userName == "eu"

    def test_init_param_token_does_not_override_explicit(self):
        import onevizion
        onevizion.Config["ParameterData"]["exp_tok2"] = {
            "url": "exp.onevizion.com",
            "UserName": "eu",
            "Password": "ep",
        }
        exp = Export(
            URL="https://explicit.onevizion.com",
            userName="expuser",
            password="exppass",
            paramToken="exp_tok2",
        )
        assert "explicit.onevizion.com" in exp.URL
        assert exp.userName == "expuser"

    def test_init_param_token_isTokenAuth_flag_is_stored(self):
        """The isTokenAuth flag from paramToken updates the local var; self.isTokenAuth
        was set before paramToken processing, so it reflects the constructor argument."""
        import onevizion
        onevizion.Config["ParameterData"]["exp_tok_auth"] = {
            "url": "exp.onevizion.com",
            "UserName": "k",
            "Password": "s",
            "isTokenAuth": True,
        }
        # isTokenAuth=False (default) is stored as self.isTokenAuth before paramToken
        # processing. The paramToken block only updates the local variable.
        exp = Export(paramToken="exp_tok_auth")
        assert exp.isTokenAuth is False  # reflects actual source behavior

    def test_init_explicit_token_auth_stored(self):
        """Passing isTokenAuth=True explicitly is stored correctly."""
        exp = Export(
            URL="https://test.onevizion.com",
            userName="k",
            password="s",
            isTokenAuth=True,
        )
        assert exp.isTokenAuth is True


class TestExportRun(object):
    """Test Export.run() - all URL building branches."""

    @mock.patch("onevizion.export.curl")
    def test_run_with_fields_list(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS", "F_NAME"],
            filters={"F_STATUS": "Active"},
        )
        call_url = mock_curl_cls.call_args[0][1]
        assert "fields=F_STATUS,F_NAME" in call_url

    @mock.patch("onevizion.export.curl")
    def test_run_with_view_options(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            viewOptions="ProjectView",
            filters={"F_STATUS": "Active"},
        )
        call_url = mock_curl_cls.call_args[0][1]
        assert "view=" in call_url

    @mock.patch("onevizion.export.curl")
    def test_run_with_filter_options(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filterOptions="F_STATUS eq 'Active'",
        )
        call_url = mock_curl_cls.call_args[0][1]
        assert "filter=" in call_url

    @mock.patch("onevizion.export.curl")
    def test_run_with_filters_dict(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active", "F_TYPE": "Internal"},
        )
        call_url = mock_curl_cls.call_args[0][1]
        assert "F_STATUS" in call_url
        assert "F_TYPE" in call_url

    @mock.patch("onevizion.export.curl")
    def test_run_with_comments(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
            comments="export run",
        )
        call_url = mock_curl_cls.call_args[0][1]
        assert "comments=" in call_url

    @mock.patch("onevizion.export.curl")
    def test_run_with_error_message_in_json(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"error_message": "Trackor type not found"}
        )
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert "Trackor type not found" in exp.errors

    @mock.patch("onevizion.export.curl")
    def test_run_with_http_error(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=500, errors=["500 = Internal Server Error"]
        )
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert len(exp.errors) > 0

    @mock.patch("onevizion.export.curl")
    def test_run_with_http_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["SSL error"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert len(exp.errors) > 0

    @mock.patch("onevizion.export.curl")
    def test_run_sets_status(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 3, "status": "RUNNING"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert exp.status == "RUNNING"

    @mock.patch("onevizion.export.curl")
    def test_run_returns_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 9, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert exp.processId == 9

    @mock.patch("onevizion.export.curl")
    def test_run_uses_basic_auth_by_default(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
        )
        assert isinstance(exp.auth, requests.auth.HTTPBasicAuth)

    @mock.patch("onevizion.export.curl")
    def test_run_uses_token_auth(self, mock_curl_cls):
        from onevizion.httpbearer import HTTPBearerAuth
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        exp = Export(
            URL="https://test.onevizion.com",
            userName="k",
            password="s",
            trackorType="Project",
            fields=["F_STATUS"],
            filters={"F_STATUS": "Active"},
            isTokenAuth=True,
        )
        assert isinstance(exp.auth, HTTPBearerAuth)


class TestExportInterrupt(object):
    """Test Export.interrupt() method."""

    @mock.patch("onevizion.export.curl")
    def test_interrupt_uses_stored_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 55
        exp.interrupt()
        call_url = mock_curl_cls.call_args[0][1]
        assert "/exports/runs/55/interrupt" in call_url

    @mock.patch("onevizion.export.curl")
    def test_interrupt_with_explicit_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.interrupt(ProcessID=66)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/exports/runs/66/interrupt" in call_url
        assert exp.processId == 66

    @mock.patch("onevizion.export.curl")
    def test_interrupt_updates_status(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 10
        exp.interrupt()
        assert exp.status == "INTERRUPTED"

    @mock.patch("onevizion.export.curl")
    def test_interrupt_no_status_key(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"message": "done"})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 10
        exp.status = "QUEUED"
        exp.interrupt()
        # status unchanged
        assert exp.status == "QUEUED"

    @mock.patch("onevizion.export.curl")
    def test_interrupt_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found"]
        )
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 10
        exp.interrupt()
        assert len(exp.errors) > 0

    @mock.patch("onevizion.export.curl")
    def test_interrupt_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Timeout"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 10
        exp.interrupt()
        assert len(exp.errors) > 0


class TestExportGetProcessStatus(object):
    """Test Export.getProcessStatus() method."""

    @mock.patch("onevizion.export.curl")
    def test_get_process_status_by_stored_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "COMPLETED"})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 20
        status = exp.getProcessStatus()
        call_url = mock_curl_cls.call_args[0][1]
        assert "/exports/runs/20" in call_url
        assert status == "COMPLETED"

    @mock.patch("onevizion.export.curl")
    def test_get_process_status_with_explicit_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "RUNNING"})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        status = exp.getProcessStatus(ProcessID=30)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/exports/runs/30" in call_url
        assert status == "RUNNING"

    @mock.patch("onevizion.export.curl")
    def test_get_process_status_no_status_key(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"records": 5})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 1
        status = exp.getProcessStatus()
        assert status == "No Status"

    @mock.patch("onevizion.export.curl")
    def test_get_process_status_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=500, errors=["500 = Server Error"]
        )
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 1
        exp.getProcessStatus()
        assert len(exp.errors) > 0

    @mock.patch("onevizion.export.curl")
    def test_get_process_status_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["DNS failure"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 1
        exp.getProcessStatus()
        assert len(exp.errors) > 0

    @mock.patch("onevizion.export.curl")
    def test_get_process_status_uses_token_auth(self, mock_curl_cls):
        from onevizion.httpbearer import HTTPBearerAuth
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "DONE"})
        exp = Export(URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
        exp.processId = 1
        exp.getProcessStatus()
        assert isinstance(exp.auth, HTTPBearerAuth)


class TestExportGetFile(object):
    """Test Export.getFile() method."""

    @mock.patch("onevizion.export.curl")
    def test_get_file_success(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 10
        content = exp.getFile()
        call_url = mock_curl_cls.call_args[0][1]
        assert "/exports/runs/10/file" in call_url
        # Content is set from request.content when no errors
        assert content == b"col1,col2\nval1,val2\n"

    @mock.patch("onevizion.export.curl")
    def test_get_file_with_explicit_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.getFile(ProcessID=77)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/exports/runs/77/file" in call_url

    @mock.patch("onevizion.export.curl")
    def test_get_file_with_errors_returns_none(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found"]
        )
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 10
        content = exp.getFile()
        assert len(exp.errors) > 0
        assert content is None

    @mock.patch("onevizion.export.curl")
    def test_get_file_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Timeout"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        exp = Export(URL="https://test.onevizion.com", userName="u", password="p")
        exp.processId = 1
        content = exp.getFile()
        assert len(exp.errors) > 0
        assert content is None

    @mock.patch("onevizion.export.curl")
    def test_get_file_uses_token_auth(self, mock_curl_cls):
        from onevizion.httpbearer import HTTPBearerAuth
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        exp = Export(URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
        exp.processId = 1
        exp.getFile()
        assert isinstance(exp.auth, HTTPBearerAuth)
