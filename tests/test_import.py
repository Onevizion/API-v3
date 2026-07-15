"""Tests for onevizion.Import module."""
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys
import os
import json
import tempfile

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import onevizion.Import
from onevizion.Import import Import


def make_mock_curl(status_code=200, json_data=None, errors=None, duration=0.1):
    """Factory for a mock curl object."""
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


def _make_temp_csv():
    """Create a temporary CSV file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    f.write("col1,col2\nval1,val2\n")
    f.close()
    return f.name


class TestImportInit(object):
    """Test Import.__init__ behaviour."""

    def test_init_no_args_does_not_run(self):
        imp = Import()
        # Without all required fields, run() must not be called automatically
        assert imp.processId is None
        assert imp.errors == []

    def test_init_stores_attributes(self):
        imp = Import(
            URL="https://test.onevizion.com",
            userName="user",
            password="pass",
            impSpecId=42,
            action="INSERT",
            comments="test comment",
        )
        assert imp.URL == "https://test.onevizion.com"
        assert imp.userName == "user"
        assert imp.password == "pass"
        assert imp.impSpecId == 42
        assert imp.action == "INSERT"
        assert imp.comments == "test comment"

    def test_init_adds_https_to_url(self):
        imp = Import(URL="bare.onevizion.com")
        assert imp.URL.startswith("https://")

    def test_init_empty_url_stays_empty(self):
        imp = Import()
        assert imp.URL == ""

    @mock.patch("onevizion.curl.curl")
    def test_init_runs_when_all_params_present(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"process_id": 7, "status": "QUEUED"}
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=1,
                file=tmp,
            )
            assert imp.processId == 7
            assert imp.status == "QUEUED"
        finally:
            os.unlink(tmp)

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["imp_token"] = {
            "url": "token.onevizion.com",
            "UserName": "tuser",
            "Password": "tpass",
        }
        imp = Import(paramToken="imp_token")
        assert "token.onevizion.com" in imp.URL
        assert imp.userName == "tuser"

    def test_init_param_token_does_not_override_explicit(self):
        import onevizion
        onevizion.Config["ParameterData"]["imp_token2"] = {
            "url": "token.onevizion.com",
            "UserName": "tuser",
            "Password": "tpass",
        }
        imp = Import(
            URL="https://explicit.onevizion.com",
            userName="expuser",
            password="exppass",
            paramToken="imp_token2",
        )
        assert "explicit.onevizion.com" in imp.URL
        assert imp.userName == "expuser"

    def test_init_param_token_isTokenAuth_flag_stored_as_false(self):
        """The isTokenAuth from paramToken updates only the local var; self.isTokenAuth
        reflects the constructor argument (False by default)."""
        import onevizion
        onevizion.Config["ParameterData"]["imp_tok_auth"] = {
            "url": "tok.onevizion.com",
            "UserName": "k",
            "Password": "s",
            "isTokenAuth": True,
        }
        # self.isTokenAuth is set to False before paramToken processing.
        imp = Import(paramToken="imp_tok_auth")
        assert imp.isTokenAuth is False

    def test_init_explicit_token_auth_stored(self):
        """Passing isTokenAuth=True explicitly is stored correctly."""
        imp = Import(
            URL="https://test.onevizion.com",
            userName="k",
            password="s",
            isTokenAuth=True,
        )
        assert imp.isTokenAuth is True


class TestImportRun(object):
    """Test Import.run() - all branches."""

    @mock.patch("onevizion.curl.curl")
    def test_run_success_with_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"process_id": 5, "status": "QUEUED"}
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
            )
            assert imp.processId == 5
            assert imp.status == "QUEUED"
            assert imp.errors == []
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_with_comments(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"process_id": 6, "status": "QUEUED"}
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
                comments="test run comment",
            )
            call_url = mock_curl_cls.call_args[0][1]
            assert "comments=" in call_url
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_with_incremental(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"process_id": 6, "status": "QUEUED"}
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
                incremental=True,
            )
            call_url = mock_curl_cls.call_args[0][1]
            assert "is_incremental=True" in call_url
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_with_http_error(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=500, errors=["500 = Internal Server Error"]
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
            )
            assert len(imp.errors) > 0
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_with_http_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Connection reset"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
            )
            assert len(imp.errors) > 0
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_with_error_message_in_json(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"error_message": "Import spec not found", "warnings": []}
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
            )
            assert "Import spec not found" in imp.errors
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_with_warnings_in_json(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={
                "process_id": 3,
                "status": "QUEUED",
                "warnings": ["Row 1 skipped", "Row 2 skipped"],
            }
        )
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
            )
            assert imp.warnings == ["Row 1 skipped", "Row 2 skipped"]
            assert imp.processId == 3
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_uses_basic_auth_by_default(self, mock_curl_cls):
        import requests as req
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
            )
            assert isinstance(imp.auth, req.auth.HTTPBasicAuth)
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_uses_token_auth_when_flag_set(self, mock_curl_cls):
        from onevizion.httpbearer import HTTPBearerAuth
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="k",
                password="s",
                impSpecId=10,
                file=tmp,
                isTokenAuth=True,
            )
            assert isinstance(imp.auth, HTTPBearerAuth)
        finally:
            os.unlink(tmp)

    @mock.patch("onevizion.curl.curl")
    def test_run_url_contains_action(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"process_id": 1, "status": "QUEUED"})
        tmp = _make_temp_csv()
        try:
            imp = Import(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=10,
                file=tmp,
                action="INSERT",
            )
            call_url = mock_curl_cls.call_args[0][1]
            assert "action=INSERT" in call_url
        finally:
            os.unlink(tmp)


class TestImportInterrupt(object):
    """Test Import.interrupt() method."""

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_uses_stored_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        imp = Import(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
        )
        imp.processId = 88
        imp.interrupt()
        call_url = mock_curl_cls.call_args[0][1]
        assert "/imports/runs/88/interrupt" in call_url

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_with_explicit_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        imp = Import(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
        )
        imp.interrupt(ProcessID=99)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/imports/runs/99/interrupt" in call_url
        assert imp.processId == 99

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_updates_status(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 10
        imp.interrupt()
        assert imp.status == "INTERRUPTED"

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found"]
        )
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 10
        imp.interrupt()
        assert len(imp.errors) > 0

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Timeout"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 10
        imp.interrupt()
        assert len(imp.errors) > 0

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_uses_token_auth(self, mock_curl_cls):
        from onevizion.httpbearer import HTTPBearerAuth
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "INTERRUPTED"})
        imp = Import(URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
        imp.processId = 5
        imp.interrupt()
        assert isinstance(imp.auth, HTTPBearerAuth)

    @mock.patch("onevizion.curl.curl")
    def test_interrupt_no_status_key_in_response(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"message": "ok"})
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 10
        imp.status = "QUEUED"
        imp.interrupt()
        # status unchanged since key not in response
        assert imp.status == "QUEUED"


class TestImportGetProcessData(object):
    """Test Import.getProcessData() method."""

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_by_stored_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            json_data={"status": "COMPLETED", "records_inserted": 10}
        )
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 7
        result = imp.getProcessData()
        call_url = mock_curl_cls.call_args[0][1]
        assert "/imports/runs/7" in call_url
        assert result == {"status": "COMPLETED", "records_inserted": 10}

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_with_explicit_process_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "RUNNING"})
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.getProcessData(processId=42)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/imports/runs/42" in call_url

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_updates_status(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "COMPLETED"})
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 1
        imp.getProcessData()
        assert imp.status == "COMPLETED"

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_no_status_returns_no_status(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"records": []})
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 1
        imp.getProcessData()
        assert imp.status == "No Status"

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_with_filters(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[{"status": "QUEUED"}])
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 1
        imp.getProcessData(status="QUEUED", importName="MyImport", owner="admin", comments="test")
        call_url = mock_curl_cls.call_args[0][1]
        assert "status=QUEUED" in call_url
        assert "import_name=" in call_url
        assert "owner=" in call_url

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_with_status_list(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[])
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 1
        imp.getProcessData(status=["QUEUED", "RUNNING"])
        call_url = mock_curl_cls.call_args[0][1]
        assert "QUEUED,RUNNING" in call_url

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=500, errors=["500 = Server Error"]
        )
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 1
        imp.getProcessData()
        assert len(imp.errors) > 0

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Network failure"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        imp = Import(URL="https://test.onevizion.com", userName="u", password="p")
        imp.processId = 1
        imp.getProcessData()
        assert len(imp.errors) > 0

    @mock.patch("onevizion.curl.curl")
    def test_get_process_data_uses_token_auth(self, mock_curl_cls):
        from onevizion.httpbearer import HTTPBearerAuth
        mock_curl_cls.return_value = make_mock_curl(json_data={"status": "DONE"})
        imp = Import(URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
        imp.processId = 1
        imp.getProcessData()
        assert isinstance(imp.auth, HTTPBearerAuth)
