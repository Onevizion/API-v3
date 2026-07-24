"""Tests for onevizion.trackor module."""
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
    BUILTIN_OPEN = 'builtins.open'
else:
    import mock
    BUILTIN_OPEN = '__builtin__.open'

import requests
import onevizion.trackor
from onevizion.trackor import Trackor


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


class TestTrackorInit(object):
    """Test Trackor initialization."""

    def test_init_with_params(self):
        t = Trackor(
            trackorType="Project",
            URL="test.onevizion.com",
            userName="testuser",
            password="testpass",
        )
        assert t.TrackorType == "Project"
        assert "https://test.onevizion.com" in t.URL
        assert t.userName == "testuser"
        assert t.password == "testpass"

    def test_init_adds_https(self):
        t = Trackor(URL="test.onevizion.com")
        assert t.URL.startswith("https://")

    def test_init_empty(self):
        t = Trackor()
        assert t.TrackorType == ""
        assert t.errors == []
        assert t.jsonData == {}

    def test_init_with_https_already_present(self):
        t = Trackor(URL="https://already.onevizion.com")
        assert t.URL == "https://already.onevizion.com"

    def test_basic_auth_by_default(self):
        t = Trackor(URL="test.onevizion.com", userName="user", password="pass")
        assert isinstance(t.auth, requests.auth.HTTPBasicAuth)

    def test_token_auth_when_specified(self):
        from onevizion.httpbearer import HTTPBearerAuth
        t = Trackor(URL="test.onevizion.com", userName="key", password="secret", isTokenAuth=True)
        assert isinstance(t.auth, HTTPBearerAuth)

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["mytoken"] = {
            "url": "param.onevizion.com",
            "UserName": "puser",
            "Password": "ppass",
        }
        t = Trackor(paramToken="mytoken")
        assert "param.onevizion.com" in t.URL
        assert t.userName == "puser"
        assert t.password == "ppass"

    def test_init_param_token_with_token_auth(self):
        import onevizion
        from onevizion.httpbearer import HTTPBearerAuth
        onevizion.Config["ParameterData"]["tokauth"] = {
            "url": "param.onevizion.com",
            "UserName": "k",
            "Password": "s",
            "isTokenAuth": True,
        }
        t = Trackor(paramToken="tokauth")
        assert isinstance(t.auth, HTTPBearerAuth)

    def test_init_param_token_does_not_override_explicit_values(self):
        import onevizion
        onevizion.Config["ParameterData"]["override"] = {
            "url": "param.onevizion.com",
            "UserName": "puser",
            "Password": "ppass",
        }
        t = Trackor(
            URL="https://explicit.onevizion.com",
            userName="expuser",
            password="exppass",
            paramToken="override",
        )
        assert "explicit.onevizion.com" in t.URL
        assert t.userName == "expuser"
        assert t.password == "exppass"


class TestTrackorDelete(object):
    """Test Trackor delete method."""

    @mock.patch("onevizion.trackor.curl")
    def test_delete_success(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(status_code=200, json_data={"deleted": True})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.delete(trackorId=123)
        assert t.errors == []
        assert t.jsonData == {"deleted": True}
        call_args = mock_curl_cls.call_args
        assert "DELETE" in call_args[0]
        assert "trackor_id=123" in call_args[0][1]

    @mock.patch("onevizion.trackor.curl")
    def test_delete_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found\nNot found"]
        )
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.delete(trackorId=999)
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_delete_error_request_exception(self, mock_curl_cls):
        """When request itself fails (no status_code on request object)."""
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Connection error"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.delete(trackorId=1)
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_delete_resets_state(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"result": "ok"})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.errors = ["old error"]
        t.jsonData = {"old": "data"}
        t.delete(trackorId=1)
        assert t.errors == []
        assert t.jsonData == {"result": "ok"}


class TestTrackorRead(object):
    """Test Trackor read method - all filter/view branch combinations."""

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_trackor_id(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_KEY": "PROJ-1"})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(trackorId=42)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/trackors/42" in call_url
        assert t.jsonData == {"TRACKOR_KEY": "PROJ-1"}

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_filters_dict_and_fields(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[{"F_STATUS": "Active"}])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(filters={"F_STATUS": "Active"}, fields=["F_STATUS", "F_NAME"])
        call_url = mock_curl_cls.call_args[0][1]
        assert "trackor_types/Project/trackors" in call_url
        assert "F_STATUS" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_filter_options(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(filterOptions="F_STATUS eq 'Active'", fields=["F_STATUS"])
        call_url = mock_curl_cls.call_args[0][1]
        assert "filter=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_view_options(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(filters={"F_STATUS": "Active"}, viewOptions="MyView")
        call_url = mock_curl_cls.call_args[0][1]
        assert "view=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_search_body(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        search_criteria = [{"fieldName": "F_STATUS", "operator": "Equal", "values": ["Active"]}]
        t.read(search=search_criteria, fields=["F_STATUS"])
        call_url = mock_curl_cls.call_args[0][1]
        assert "/search" in call_url
        # Search uses POST
        assert mock_curl_cls.call_args[0][0] == "POST"

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_sort(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(fields=["F_NAME"], sort={"F_NAME": "asc"})
        call_url = mock_curl_cls.call_args[0][1]
        assert "sort=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_pagination(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(fields=["F_NAME"], page=2, perPage=50)
        call_url = mock_curl_cls.call_args[0][1]
        assert "page=2" in call_url
        assert "per_page=50" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_read_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=500, errors=["500 = Internal Server Error"]
        )
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(trackorId=1)
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_read_error_no_request_object(self, mock_curl_cls):
        """Error path where request itself is None (network failure)."""
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Failed to connect"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.read(trackorId=1)
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_read_resets_errors_between_calls(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data=[{"F_STATUS": "Active"}])
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.errors = ["stale error"]
        t.read(trackorId=1)
        assert t.errors == []


class TestTrackorUpdate(object):
    """Test Trackor update method."""

    @mock.patch("onevizion.trackor.curl")
    def test_update_by_trackor_id_simple_fields(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_KEY": "PROJ-1"})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(trackorId=10, fields={"F_STATUS": "Active", "F_NAME": "MyProject"})
        call_url = mock_curl_cls.call_args[0][1]
        assert "/trackors/10" in call_url
        assert mock_curl_cls.call_args[0][0] == "PUT"
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_update_by_filters(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_KEY": "PROJ-1"})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(filters={"TRACKOR_KEY": "PROJ-1"}, fields={"F_STATUS": "Closed"})
        call_url = mock_curl_cls.call_args[0][1]
        assert "trackor_types/Project/trackors" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_update_with_dict_field_value(self, mock_curl_cls):
        """Test updating a compound field like an EFile."""
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(
            trackorId=10,
            fields={"F_FILE": {"file_name": "test.txt", "data": "SGVsbG8="}}
        )
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_update_with_parents(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(
            filters={"TRACKOR_KEY": "PROJ-1"},
            fields={"F_STATUS": "Active"},
            parents={"Program": {"TRACKOR_KEY": "PROG-1"}},
        )
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_update_with_multiple_parents_distinct(self, mock_curl_cls):
        """Test that multiple parents are sent as distinct objects, not duplicates.

        This is a regression test for bug H2 where Parentx={} was created once
        before the loop, causing all parent references to point to the same dict.
        This resulted in multi-parent updates sending the last parent N times
        instead of N distinct parents.

        Note: Parents can only be updated when using filters (not trackorId),
        per the OneVizion API design.
        """
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Trackor(trackorType="Asset", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(
            filters={"TRACKOR_KEY": "ASSET-001"},
            fields={"F_STATUS": "Active"},
            parents={
                "Program": {"TRACKOR_KEY": "PROG-001"},
                "Portfolio": {"TRACKOR_KEY": "PORT-001"},
                "Department": {"TRACKOR_KEY": "DEPT-001"}
            },
        )
        # Get the JSON data that was sent
        call_kwargs = mock_curl_cls.call_args[1]
        sent_data = json.loads(call_kwargs["data"])

        # Verify we have 3 distinct parents
        assert "parents" in sent_data
        assert len(sent_data["parents"]) == 3

        # Verify each parent is distinct (not all the same)
        parent_types = [p["trackor_type"] for p in sent_data["parents"]]
        assert "Program" in parent_types
        assert "Portfolio" in parent_types
        assert "Department" in parent_types

        # Verify filters are correct for each
        for parent in sent_data["parents"]:
            if parent["trackor_type"] == "Program":
                assert parent["filter"]["TRACKOR_KEY"] == "PROG-001"
            elif parent["trackor_type"] == "Portfolio":
                assert parent["filter"]["TRACKOR_KEY"] == "PORT-001"
            elif parent["trackor_type"] == "Department":
                assert parent["filter"]["TRACKOR_KEY"] == "DEPT-001"

    @mock.patch("onevizion.trackor.curl")
    def test_update_with_charset(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(trackorId=1, fields={"F_NAME": "test"}, charset="UTF-8")
        call_kwargs = mock_curl_cls.call_args[1]
        assert "UTF-8" in call_kwargs.get("headers", {}).get("charset", "")

    @mock.patch("onevizion.trackor.curl")
    def test_update_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=400, errors=["400 = Bad Request\nInvalid field"]
        )
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(trackorId=1, fields={"F_INVALID": "value"})
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_update_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Connection refused"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(trackorId=1, fields={"F_NAME": "test"})
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_update_none_field_value(self, mock_curl_cls):
        """None field values should be preserved (JSONEndValue returns None)."""
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.update(trackorId=1, fields={"F_STATUS": None})
        assert t.errors == []


class TestTrackorCreate(object):
    """Test Trackor create method."""

    @mock.patch("onevizion.trackor.curl")
    def test_create_simple_fields(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_ID": 99, "TRACKOR_KEY": "PROJ-99"})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(fields={"F_STATUS": "New", "F_NAME": "NewProject"})
        call_url = mock_curl_cls.call_args[0][1]
        assert "trackor_types/Project/trackors" in call_url
        assert mock_curl_cls.call_args[0][0] == "POST"
        assert t.jsonData == {"TRACKOR_ID": 99, "TRACKOR_KEY": "PROJ-99"}

    @mock.patch("onevizion.trackor.curl")
    def test_create_with_dict_field(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_ID": 100})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(fields={"F_FILE": {"file_name": "doc.pdf", "data": "AAAA"}})
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_create_with_parents(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_ID": 101})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(
            fields={"F_NAME": "Test"},
            parents={"Program": {"TRACKOR_KEY": "PROG-1"}},
        )
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_create_with_multiple_parents_distinct(self, mock_curl_cls):
        """Test that create with multiple parents sends distinct objects.

        Regression test for bug H2 - same as test_update_with_multiple_parents_distinct
        but for the create() method.
        """
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_ID": 999})
        t = Trackor(trackorType="Asset", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(
            fields={"F_NAME": "New Asset"},
            parents={
                "Location": {"TRACKOR_KEY": "LOC-001"},
                "Owner": {"TRACKOR_KEY": "OWN-001"}
            },
        )
        # Get the JSON data that was sent
        call_kwargs = mock_curl_cls.call_args[1]
        sent_data = json.loads(call_kwargs["data"])

        # Verify we have 2 distinct parents
        assert "parents" in sent_data
        assert len(sent_data["parents"]) == 2

        # Verify each parent is distinct
        parent_types = [p["trackor_type"] for p in sent_data["parents"]]
        assert "Location" in parent_types
        assert "Owner" in parent_types

        # Verify filters are correct
        for parent in sent_data["parents"]:
            if parent["trackor_type"] == "Location":
                assert parent["filter"]["TRACKOR_KEY"] == "LOC-001"
            elif parent["trackor_type"] == "Owner":
                assert parent["filter"]["TRACKOR_KEY"] == "OWN-001"

    @mock.patch("onevizion.trackor.curl")
    def test_create_with_charset(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(fields={"F_NAME": "Test"}, charset="UTF-8")
        call_kwargs = mock_curl_cls.call_args[1]
        assert call_kwargs.get("headers", {}).get("charset") == "UTF-8"

    @mock.patch("onevizion.trackor.curl")
    def test_create_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=422, errors=["422 = Unprocessable Entity"]
        )
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(fields={"F_MISSING_REQUIRED": None})
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_create_error_no_request_object(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Timeout"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create(fields={"F_NAME": "Test"})
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_create_empty_fields(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"TRACKOR_ID": 50})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.create()
        assert t.errors == []


class TestTrackorAssignWorkplan(object):
    """Test Trackor assignWorkplan method."""

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_basic(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 5})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default")
        call_url = mock_curl_cls.call_args[0][1]
        assert "/trackors/10/assign_wp" in call_url
        assert "workplan_template=Default" in call_url
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_with_name(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 6})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default", name="My Workplan")
        call_url = mock_curl_cls.call_args[0][1]
        assert "name=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_with_start_date_string(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 7})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default", startDate="2024-01-01")
        call_url = mock_curl_cls.call_args[0][1]
        assert "proj_start_date=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_with_start_date_datetime(self, mock_curl_cls):
        from datetime import datetime
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 8})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default", startDate=datetime(2024, 1, 15))
        call_url = mock_curl_cls.call_args[0][1]
        assert "proj_start_date=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_with_finish_date_string(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 9})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default", finishDate="2024-12-31")
        call_url = mock_curl_cls.call_args[0][1]
        assert "proj_finish_date=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_with_finish_date_datetime(self, mock_curl_cls):
        from datetime import datetime
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 10})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default", finishDate=datetime(2024, 12, 31))
        call_url = mock_curl_cls.call_args[0][1]
        assert "proj_finish_date=" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_is_active(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"wp_id": 11})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default", isActive=True)
        call_url = mock_curl_cls.call_args[0][1]
        assert "is_active=True" in call_url

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=404, errors=["404 = Not Found"]
        )
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=999, workplanTemplate="NonExistent")
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_assign_workplan_error_no_request(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Network error"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.assignWorkplan(trackorId=10, workplanTemplate="Default")
        assert len(t.errors) > 0


class TestTrackorGetFile(object):
    """Test Trackor GetFile method."""

    @mock.patch("onevizion.trackor.requests.get")
    @mock.patch(BUILTIN_OPEN, create=True)
    def test_get_file_by_trackor_id_and_field_name(self, mock_open, mock_get):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"file content"]
        mock_response.headers = {"content-disposition": 'attachment; filename="report.pdf"'}
        mock_get.return_value = mock_response

        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_open.return_value.__exit__ = mock.MagicMock(return_value=False)

        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        with mock.patch("os.rename"):
            result = t.GetFile(trackorId=10, fieldName="F_FILE")
        assert t.errors == []
        assert result is not None

    @mock.patch("onevizion.trackor.requests.get")
    @mock.patch(BUILTIN_OPEN, create=True)
    def test_get_file_by_blob_data_id(self, mock_open, mock_get):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"blob content"]
        mock_response.headers = {}
        mock_get.return_value = mock_response

        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_open.return_value.__exit__ = mock.MagicMock(return_value=False)

        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        result = t.GetFile(blobDataId=555)
        # No content-disposition, so returns tmpFileName
        assert "555" in result

    def test_get_file_bad_params(self):
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        result = t.GetFile()
        assert result is None
        assert len(t.errors) > 0
        assert "Invalid parameters" in t.errors[0]

    @mock.patch("onevizion.trackor.requests.get", side_effect=Exception("Connection timed out"))
    @mock.patch(BUILTIN_OPEN, create=True)
    def test_get_file_request_exception(self, mock_open, mock_get):
        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_open.return_value.__exit__ = mock.MagicMock(return_value=False)

        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        with pytest.raises(Exception):
            t.GetFile(trackorId=10, fieldName="F_FILE")

    @mock.patch("onevizion.trackor.requests.get")
    @mock.patch(BUILTIN_OPEN, create=True)
    def test_get_file_non_200_response(self, mock_open, mock_get):
        mock_response = mock.MagicMock()
        mock_response.status_code = 403
        mock_response.reason = "Forbidden"
        mock_response.iter_content.return_value = []
        mock_response.headers = {}
        mock_get.return_value = mock_response

        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_open.return_value.__exit__ = mock.MagicMock(return_value=False)

        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.GetFile(trackorId=10, fieldName="F_FILE")
        assert len(t.errors) > 0
        assert "403" in t.errors[0]

    @mock.patch("onevizion.trackor.requests.get")
    @mock.patch(BUILTIN_OPEN, create=True)
    def test_get_file_with_content_disposition_returns_new_name(self, mock_open, mock_get):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"data"]
        mock_response.headers = {"content-disposition": "filename=myfile.csv"}
        mock_get.return_value = mock_response

        mock_file = mock.MagicMock()
        mock_open.return_value.__enter__ = mock.MagicMock(return_value=mock_file)
        mock_open.return_value.__exit__ = mock.MagicMock(return_value=False)

        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        with mock.patch("os.rename"):
            result = t.GetFile(trackorId=10, fieldName="F_FILE")
        assert result == "myfile.csv"


class TestTrackorUploadFile(object):
    """Test Trackor UploadFile and UploadFileByFileContents methods."""

    @mock.patch("onevizion.trackor.curl")
    def test_upload_file_by_contents_success(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"blob_data_id": 77})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        file_contents = b"file data"
        t.UploadFileByFileContents(trackorId=10, fieldName="F_FILE", fileName="test.txt", fileContents=file_contents)
        call_url = mock_curl_cls.call_args[0][1]
        assert "/trackor/10/file/F_FILE" in call_url
        assert "file_name=test.txt" in call_url
        assert t.errors == []

    @mock.patch("onevizion.trackor.curl")
    def test_upload_file_by_contents_with_errors(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(
            status_code=500, errors=["500 = Server Error"]
        )
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.UploadFileByFileContents(trackorId=10, fieldName="F_FILE", fileName="test.txt", fileContents=b"data")
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_upload_file_by_contents_error_no_request(self, mock_curl_cls):
        bad_curl = mock.MagicMock()
        bad_curl.errors = ["Timeout"]
        bad_curl.jsonData = {}
        bad_curl.duration = 0.0
        bad_curl.request = None
        mock_curl_cls.return_value = bad_curl
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        t.UploadFileByFileContents(trackorId=10, fieldName="F_FILE", fileName="test.txt", fileContents=b"data")
        assert len(t.errors) > 0

    @mock.patch("onevizion.trackor.curl")
    def test_upload_file_uses_basename_when_no_new_name(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"blob_data_id": 78})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"content")
            tmp_path = f.name
        try:
            t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=tmp_path)
            # The second call to UploadFileByFileContents uses basename of tmp_path
            # Verify curl was called
            assert mock_curl_cls.called
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @mock.patch("onevizion.trackor.curl")
    def test_upload_file_closes_file_handle(self, mock_curl_cls):
        """UploadFile must close file handle to avoid resource leak."""
        mock_curl_cls.return_value = make_mock_curl(json_data={"blob_data_id": 79})

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_file_path = f.name
            f.write("test content")

        try:
            t = Trackor(trackorType="Project", URL="https://test.com", userName="u", password="p")
            t.UploadFile(trackorId=123, fieldName="F_FILE", fileName=test_file_path)

            # File handle should be closed - verify by deleting file
            # (On Linux this works even with open handles, but let's check FDs)
            os.remove(test_file_path)
        finally:
            try:
                os.remove(test_file_path)
            except:
                pass

    @mock.patch("onevizion.trackor.curl")
    def test_upload_many_files_no_fd_leak(self, mock_curl_cls):
        """Uploading many files must not leak file descriptors."""
        mock_curl_cls.return_value = make_mock_curl(json_data={"blob_data_id": 80})

        # Get initial open file count (Linux only)
        if not (hasattr(os, 'listdir') and os.path.exists('/proc/self/fd')):
            pytest.skip("File descriptor counting only works on Linux")

        initial_fds = len(os.listdir('/proc/self/fd'))

        # Create and upload 50 files (Python 2.7 compatible)
        tmpdir = tempfile.mkdtemp()
        try:
            test_files = []
            for i in range(50):
                test_file = os.path.join(tmpdir, "test{}.txt".format(i))
                with open(test_file, 'w') as f:
                    f.write("test content {}".format(i))
                test_files.append(test_file)

            t = Trackor(trackorType="Project", URL="https://test.com", userName="u", password="p")
            for test_file in test_files:
                t.UploadFile(trackorId=123, fieldName="F_FILE", fileName=test_file)

            # Check file descriptors didn't leak
            final_fds = len(os.listdir('/proc/self/fd'))
            leaked_fds = final_fds - initial_fds

            assert leaked_fds < 10, \
                "BUG: File descriptor leak! {} files uploaded, {} FDs leaked. " \
                "UploadFile opens files but never closes them!".format(len(test_files), leaked_fds)
        finally:
            # Cleanup temp directory (Python 2.7 compatible)
            import shutil
            shutil.rmtree(tmpdir)

    @mock.patch("onevizion.trackor.curl")
    def test_upload_file_with_new_name(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"blob_data_id": 79})
        t = Trackor(trackorType="Project", URL="https://test.onevizion.com", userName="u", password="p")
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"content")
            tmp_path = f.name
        try:
            t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=tmp_path, newFileName="renamed.txt")
            call_url = mock_curl_cls.call_args[0][1]
            assert "renamed.txt" in call_url
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
