# -*- coding: utf-8 -*-
"""Regression tests for error-trace diagnostics (Config["Trace"] output).

The trace output written on API errors is consumed by external tooling, so its
shape is part of the public contract. These tests pin the two things that broke
when error logging moved into Trackor._execute_api_call():

  1. -PostBody must be serialized exactly once. Callers pass the request body as
     an object; LogErrorToTrace() does the json.dumps(). Pre-serializing at the
     call site yields a JSON string literal with escaped newlines.
  2. Payload keys must not be written as top-level trace entries. Passing the
     request body as extra_data= gave every field its own entry, and a trackor
     field named "URL" or "Body" then overwrote the trace's own -URL / -Body.

Expected values come from master (shipped v1.1.6) for read() and create(). The
update(trackorId=...) path is a DELIBERATE divergence: v1.1.6 traced the full
{"fields": {...}} object while the wire payload was the bare FieldsSection, so
the trace disagreed with what was actually sent. #18 traces FieldsSection
instead. That is a change to the shipped trace format, pinned by
test_post_body_single_encoded_and_is_fields_section below.
"""
from __future__ import print_function

import json
import sys
from collections import OrderedDict

import pytest
import responses

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import onevizion
from onevizion.trackor import Trackor
from onevizion.util import LogErrorToTrace

BASE = "https://t.example.com"
TRACKORS_URL = BASE + "/api/v3/trackor_types/TT/trackors"

# The keys LogErrorToTrace writes for a body-carrying call with no extra_data.
SHIPPED_KEYS = {"-URL", "-PostBody", "-StatusCode", "-Reason", "-Body"}


def make_trackor():
    return Trackor(trackorType="TT", URL="t.example.com", userName="u", password="p")


def trace_suffixes(trackor):
    """Trace keys with the generated timestamp tag stripped off."""
    tag = trackor.TraceTag
    return {key[len(tag):] for key in onevizion.Config["Trace"] if key.startswith(tag)}


def trace_value(trackor, suffix):
    return onevizion.Config["Trace"][trackor.TraceTag + suffix]


def assert_http_error_path(trackor):
    """Guard against a test passing via the no-response -Errors fallback."""
    assert "-StatusCode" in trace_suffixes(trackor)


class TraceTestBase(object):
    """Restore the globals these tests touch.

    LogErrorToTrace writes to Config["Trace"] and also sets Config["Error"]
    (util.py:256); both are module-level state shared by the whole suite, so
    each is reset to its declared default from onevizion/__init__.py.
    """

    def _reset_config(self):
        onevizion.Config["Trace"] = OrderedDict()
        onevizion.Config["Verbosity"] = 0
        onevizion.Config["Error"] = False

    def setup_method(self, method):
        self._reset_config()

    def teardown_method(self, method):
        self._reset_config()


class TestLogErrorToTraceContract(TraceTestBase):
    """Direct tests of the LogErrorToTrace serialization contract."""

    def make_call(self, status_code=500, reason="Internal Server Error", text='{"errors": []}'):
        ov_call = mock.MagicMock()
        ov_call.errors = ["error"]
        ov_call.request.status_code = status_code
        ov_call.request.reason = reason
        ov_call.request.text = text
        return ov_call

    def test_post_body_object_is_serialized_once(self):
        tag = LogErrorToTrace(self.make_call(), BASE + "/x", post_body={"fields": {"A": 1}})
        body = onevizion.Config["Trace"][tag + "-PostBody"]
        assert body == json.dumps({"fields": {"A": 1}}, indent=2)
        # Single decode must yield the original object, not another JSON string.
        assert json.loads(body) == {"fields": {"A": 1}}

    def test_pre_serialized_post_body_would_double_encode(self):
        """Documents why callers must pass the object, not a string."""
        tag = LogErrorToTrace(
            self.make_call(), BASE + "/x",
            post_body=json.dumps({"fields": {"A": 1}}, indent=2),
        )
        # A pre-serialized body needs TWO decodes to get back to the object,
        # which is exactly what breaks trace-consuming tooling.
        once = json.loads(onevizion.Config["Trace"][tag + "-PostBody"])
        assert json.loads(once) == {"fields": {"A": 1}}

    def test_post_body_none_omits_key(self):
        tag = LogErrorToTrace(self.make_call(), BASE + "/x", post_body=None)
        assert tag + "-PostBody" not in onevizion.Config["Trace"]

    def test_empty_post_body_still_logged(self):
        tag = LogErrorToTrace(self.make_call(), BASE + "/x", post_body={})
        assert onevizion.Config["Trace"][tag + "-PostBody"] == "{}"

    def test_extra_data_still_supported_for_upload(self):
        """upload() legitimately uses extra_data; that path must keep working."""
        tag = LogErrorToTrace(
            self.make_call(), BASE + "/x", extra_data={"FileName": "report.pdf"}
        )
        assert onevizion.Config["Trace"][tag + "-FileName"] == "report.pdf"

    def test_sets_the_global_error_flag(self):
        """Config["Error"] is documented public contract (__init__.py:35).

        Nothing else in the suite asserts it, so removing the assignment at
        util.py:256 would otherwise go unnoticed.
        """
        onevizion.Config["Error"] = False
        LogErrorToTrace(self.make_call(), BASE + "/x", post_body={})
        assert onevizion.Config["Error"] is True

    def test_url_is_recorded(self):
        tag = LogErrorToTrace(self.make_call(), BASE + "/some/path")
        assert onevizion.Config["Trace"][tag + "-URL"] == BASE + "/some/path"


class TestUpdateErrorTrace(TraceTestBase):

    @responses.activate
    def test_url_entry_not_clobbered_by_url_field(self):
        """A trackor field named URL must not overwrite the trace's own -URL."""
        responses.add(responses.PUT, BASE + "/api/v3/trackors/42",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.update(trackorId=42, fields={"URL": "http://not-the-request-url", "F_NAME": "x"})
        assert trace_value(t, "-URL") == BASE + "/api/v3/trackors/42"

    @responses.activate
    def test_body_entry_not_clobbered_by_body_field(self):
        responses.add(responses.PUT, BASE + "/api/v3/trackors/42",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.update(trackorId=42, fields={"Body": "field value"})
        assert trace_value(t, "-Body").startswith("Body:")

    @responses.activate
    def test_payload_keys_are_not_separate_trace_entries(self):
        responses.add(responses.PUT, BASE + "/api/v3/trackors/42",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.update(trackorId=42, fields={"F_NAME": "x", "F_CODE": "y"})
        assert trace_suffixes(t) == SHIPPED_KEYS

    @responses.activate
    def test_post_body_single_encoded_and_is_fields_section(self):
        """With trackorId the wire payload is FieldsSection, so that is what we trace."""
        responses.add(responses.PUT, BASE + "/api/v3/trackors/42",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.update(trackorId=42, fields={"F_NAME": "x"})
        assert json.loads(trace_value(t, "-PostBody")) == {"F_NAME": "x"}
        assert_http_error_path(t)

    @responses.activate
    def test_post_body_with_filters_is_full_payload(self):
        """Without trackorId the wire payload is the full fields/parents object."""
        responses.add(responses.PUT, TRACKORS_URL, json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.update(filters={"KEY": "K1"}, fields={"F_NAME": "x"},
                 parents={"PROGRAM": {"PROGRAM_KEY": "P1"}})
        decoded = json.loads(trace_value(t, "-PostBody"))
        assert decoded["fields"] == {"F_NAME": "x"}
        assert decoded["parents"] == [
            {"trackor_type": "PROGRAM", "filter": {"PROGRAM_KEY": "P1"}}
        ]

    @pytest.mark.skipif(
        sys.version_info[0] < 3,
        reason="Pre-existing py2.7 bug (also in master/v1.1.6): JSONEndValue's "
               "str(objToEncode) at util.py:191 raises UnicodeEncodeError on "
               "unicode field values, before any trace is written.",
    )
    @responses.activate
    def test_non_ascii_field_value_survives_trace(self):
        responses.add(responses.PUT, BASE + "/api/v3/trackors/42",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.update(trackorId=42, fields={"F_NAME": u"café"})
        assert json.loads(trace_value(t, "-PostBody")) == {"F_NAME": u"café"}

    @responses.activate
    def test_no_trace_written_on_success(self):
        responses.add(responses.PUT, BASE + "/api/v3/trackors/42", json={}, status=200)
        t = make_trackor()
        t.update(trackorId=42, fields={"F_NAME": "x"})
        assert len(onevizion.Config["Trace"]) == 0


class TestCreateErrorTrace(TraceTestBase):

    @responses.activate
    def test_url_entry_not_clobbered_by_url_field(self):
        responses.add(responses.POST, TRACKORS_URL, json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.create(fields={"URL": "http://not-the-request-url"})
        assert trace_value(t, "-URL") == TRACKORS_URL

    @responses.activate
    def test_post_body_single_encoded_and_is_full_payload(self):
        responses.add(responses.POST, TRACKORS_URL, json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.create(fields={"F_NAME": "x"}, parents={"PROGRAM": {"PROGRAM_KEY": "P1"}})
        decoded = json.loads(trace_value(t, "-PostBody"))
        assert decoded["fields"] == {"F_NAME": "x"}
        assert decoded["parents"] == [
            {"trackor_type": "PROGRAM", "filter": {"PROGRAM_KEY": "P1"}}
        ]

    @responses.activate
    def test_payload_keys_are_not_separate_trace_entries(self):
        responses.add(responses.POST, TRACKORS_URL, json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.create(fields={"F_NAME": "x", "F_CODE": "y"})
        assert trace_suffixes(t) == SHIPPED_KEYS


class TestReadErrorTrace(TraceTestBase):

    @responses.activate
    def test_empty_search_body_traced_as_empty_object(self):
        responses.add(responses.GET, TRACKORS_URL, json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.read(filters={"KEY": "K1"}, fields=["F_NAME"])
        assert trace_value(t, "-PostBody") == "{}"
        assert_http_error_path(t)

    @responses.activate
    def test_search_body_single_encoded(self):
        """search= switches read() to POST /search with a body."""
        responses.add(responses.POST, TRACKORS_URL + "/search",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.read(search={"F_NAME": "x"}, fields=["F_NAME"])
        assert json.loads(trace_value(t, "-PostBody")) == {"data": {"F_NAME": "x"}}
        assert_http_error_path(t)

    @responses.activate
    def test_payload_keys_are_not_separate_trace_entries(self):
        responses.add(responses.POST, TRACKORS_URL + "/search",
                      json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.read(search={"F_NAME": "x"}, fields=["F_NAME"])
        assert trace_suffixes(t) == SHIPPED_KEYS


class TestUploadErrorTrace(TraceTestBase):

    @responses.activate
    def test_filename_still_traced_via_extra_data(self):
        url = BASE + "/api/v3/trackor/42/file/F_DOC"
        responses.add(responses.POST, url, json={"errors": ["boom"]}, status=500)
        t = make_trackor()
        t.UploadFileByFileContents(trackorId=42, fieldName="F_DOC",
                                   fileName="report.pdf", fileContents=b"data")
        assert trace_value(t, "-FileName") == "report.pdf"
        assert trace_value(t, "-URL").startswith(url)
