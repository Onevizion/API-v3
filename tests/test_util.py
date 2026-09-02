"""Tests for onevizion.util module."""
# -*- coding: utf-8 -*-
from __future__ import print_function

import base64
import json
import sys
from collections import OrderedDict
from datetime import date, datetime

import pytest

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    pass
else:
    pass

import onevizion
from onevizion.util import (
    CheckParameters,
    CheckPasswords,
    EFileEncode,
    GetParameters,
    GetPasswords,
    JSONEncode,
    JSONEndValue,
    JSONValue,
    Message,
    TraceMessage,
    URLEncode,
    getUrlContainingScheme,
)


class TestGetUrlContainingScheme(object):
    """Test getUrlContainingScheme function."""

    def test_bare_domain_gets_https(self):
        assert getUrlContainingScheme("example.com") == "https://example.com"

    def test_https_url_unchanged(self):
        assert getUrlContainingScheme("https://example.com") == "https://example.com"

    def test_http_url_unchanged(self):
        assert getUrlContainingScheme("http://example.com") == "http://example.com"

    def test_none_returns_empty_string(self):
        assert getUrlContainingScheme(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert getUrlContainingScheme("") == ""

    def test_uppercase_https_unchanged(self):
        assert getUrlContainingScheme("HTTPS://example.com") == "HTTPS://example.com"

    def test_mixed_case_http(self):
        assert getUrlContainingScheme("HTTP://example.com") == "HTTP://example.com"

    def test_url_with_path(self):
        result = getUrlContainingScheme("example.com/api/v3")
        assert result == "https://example.com/api/v3"


class TestMessage(object):
    """Test Message function."""

    def test_message_printed_when_level_at_or_below_verbosity(self, capsys):
        onevizion.Config["Verbosity"] = 2
        Message("hello", 1)
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_message_suppressed_when_level_above_verbosity(self, capsys):
        onevizion.Config["Verbosity"] = 0
        Message("should not appear", 2)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_message_at_level_zero_always_prints(self, capsys):
        onevizion.Config["Verbosity"] = 0
        Message("always", 0)
        captured = capsys.readouterr()
        assert "always" in captured.out

    def teardown_method(self, method):
        onevizion.Config["Verbosity"] = 0


class TestTraceMessage(object):
    """Test TraceMessage function."""

    def setup_method(self, method):
        onevizion.Config["Trace"] = OrderedDict()
        onevizion.Config["Verbosity"] = 0

    def test_trace_message_stored_with_generated_tag(self):
        TraceMessage("trace msg", 0)
        # Should have stored the message in Trace
        values = list(onevizion.Config["Trace"].values())
        assert "trace msg" in values

    def test_trace_message_stored_with_explicit_tag(self):
        TraceMessage("explicit trace", 0, TraceTag="my-tag")
        assert onevizion.Config["Trace"]["my-tag"] == "explicit trace"

    def test_trace_message_calls_message(self, capsys):
        onevizion.Config["Verbosity"] = 0
        TraceMessage("printed msg", 0, TraceTag="t1")
        captured = capsys.readouterr()
        assert "printed msg" in captured.out

    def teardown_method(self, method):
        onevizion.Config["Trace"] = OrderedDict()
        onevizion.Config["Verbosity"] = 0


class TestGetParameters(object):
    """Test GetParameters / GetPasswords functions."""

    def test_get_parameters_loads_json_file(self, tmp_path):
        param_data = {"mytoken": {"url": "test.com", "UserName": "u", "Password": "p"}}
        param_file = tmp_path / "params.json"
        with open(str(param_file), 'w') as f:
            f.write(json.dumps(param_data))
        result = GetParameters(str(param_file))
        assert result == param_data
        assert onevizion.Config["ParameterData"] == param_data

    def test_get_parameters_missing_file_quits(self, tmp_path):
        missing = str(tmp_path / "missing.json")
        with pytest.raises(SystemExit):
            GetParameters(missing)

    def test_get_passwords_is_alias_for_get_parameters(self, tmp_path):
        param_data = {"smtp": {"UserName": "u", "Password": "p", "Server": "s"}}
        param_file = tmp_path / "pass.json"
        with open(str(param_file), 'w') as f:
            f.write(json.dumps(param_data))
        result = GetPasswords(str(param_file))
        assert result == param_data

    def test_get_parameters_uses_config_file_when_none_given(self, tmp_path):
        param_data = {"token": {"url": "example.com", "UserName": "u", "Password": "p"}}
        param_file = tmp_path / "params.json"
        with open(str(param_file), 'w') as f:
            f.write(json.dumps(param_data))
        onevizion.Config["ParameterFile"] = str(param_file)
        result = GetParameters()
        assert result == param_data
        onevizion.Config["ParameterFile"] = None


class TestCheckParameters(object):
    """Test CheckParameters / CheckPasswords functions."""

    def test_check_parameters_all_keys_present_returns_empty_string(self):
        data = {"mytoken": {"url": "x", "UserName": "u", "Password": "p"}}
        result = CheckParameters(data, "mytoken", ["url", "UserName", "Password"])
        assert result == ""

    def test_check_parameters_token_missing_returns_message(self):
        data = {}
        result = CheckParameters(data, "missingtoken", ["url"])
        assert "missingtoken" in result
        assert len(result) > 0

    def test_check_parameters_key_missing_from_token(self):
        data = {"mytoken": {"url": "x"}}
        result = CheckParameters(data, "mytoken", ["url", "UserName"])
        assert len(result) > 0

    def test_check_parameters_with_optional_list(self):
        data = {}
        result = CheckParameters(data, "tok", ["url"], OptionalList=["comments"])
        assert "comments" in result

    def test_check_passwords_is_alias(self):
        data = {"tok": {"UserName": "u", "Password": "p"}}
        result = CheckPasswords(data, "tok", ["UserName", "Password"])
        assert result == ""


class TestURLEncode(object):
    """Test URLEncode function."""

    def test_encode_simple_string(self):
        result = URLEncode("hello world")
        assert result == "hello+world"

    def test_encode_special_chars(self):
        result = URLEncode("F_STATUS=Active&F_TYPE=Internal")
        assert "=" not in result or "%3D" in result or "+" in result

    def test_encode_none_returns_empty_string(self):
        result = URLEncode(None)
        assert result == ""

    def test_encode_empty_string(self):
        result = URLEncode("")
        assert result == ""

    def test_encode_already_url_safe(self):
        result = URLEncode("hello")
        assert result == "hello"

    def test_encode_slash(self):
        result = URLEncode("path/to/resource")
        assert "/" not in result


class TestJSONEncode(object):
    """Test JSONEncode function."""

    def test_encode_backslash(self):
        result = JSONEncode("back\\slash")
        assert "\\\\" in result

    def test_encode_double_quote(self):
        result = JSONEncode('say "hello"')
        assert '\\"' in result

    def test_encode_newline(self):
        result = JSONEncode("line1\nline2")
        assert "\\n" in result

    def test_encode_carriage_return(self):
        result = JSONEncode("line1\rline2")
        assert "\\r" in result

    def test_encode_tab(self):
        result = JSONEncode("col1\tcol2")
        assert "\\t" in result

    def test_encode_none_returns_empty_string(self):
        result = JSONEncode(None)
        assert result == ""

    def test_encode_plain_string_unchanged(self):
        result = JSONEncode("hello")
        assert result == "hello"


class TestJSONValue(object):
    """Test JSONValue function."""

    def test_none_returns_null(self):
        assert JSONValue(None) == "null"

    def test_integer_returns_string_repr(self):
        assert JSONValue(42) == "42"

    def test_float_returns_string_repr(self):
        assert JSONValue(3.14) == "3.14"

    def test_string_wrapped_in_quotes(self):
        result = JSONValue("hello")
        assert result == '"hello"'

    def test_string_with_special_chars_encoded(self):
        result = JSONValue('say "hi"')
        assert '\\"' in result


class TestJSONEndValue(object):
    """Test JSONEndValue function."""

    def test_none_returns_none(self):
        assert JSONEndValue(None) is None

    def test_integer_returned_as_is(self):
        assert JSONEndValue(42) == 42

    def test_float_returned_as_is(self):
        assert JSONEndValue(3.14) == 3.14

    def test_datetime_formatted_as_iso(self):
        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = JSONEndValue(dt)
        assert result == "2024-06-15T10:30:00"

    def test_date_formatted_as_date_string(self):
        d = date(2024, 6, 15)
        result = JSONEndValue(d)
        assert result == "2024-06-15"

    def test_string_returned_as_str(self):
        assert JSONEndValue("hello") == "hello"

    def test_other_type_converted_to_str(self):
        # bool subclasses int, so True/False hit the int branch.
        # Use a list or tuple to hit the final str() branch.
        result = JSONEndValue([1, 2, 3])
        assert isinstance(result, str)

    def test_bool_hits_int_branch(self):
        # bool is a subclass of int; JSONEndValue returns it unchanged
        result = JSONEndValue(True)
        assert result is True


class TestEFileEncode(object):
    """Test EFileEncode function."""

    def test_encode_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        result = EFileEncode(str(test_file))
        assert result["file_name"] == "test.txt"
        assert "data" in result
        # Decode and verify
        decoded = base64.b64decode(result["data"])
        assert decoded == b"hello world"

    def test_encode_file_with_new_name(self, tmp_path):
        test_file = tmp_path / "original.txt"
        test_file.write_bytes(b"content")
        result = EFileEncode(str(test_file), NewFileName="renamed.txt")
        assert result["file_name"] == "renamed.txt"

    def test_encode_binary_file(self, tmp_path):
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03")
        result = EFileEncode(str(test_file))
        assert isinstance(result["data"], str)
        decoded = base64.b64decode(result["data"])
        assert decoded == b"\x00\x01\x02\x03"
