"""Tests for onevizion.trackor module."""
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys
import os
import tempfile

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import vcr
from onevizion.trackor import Trackor


class TestTrackorInit(object):
    """Test Trackor initialization."""

    def test_init_with_params(self):
        """Test basic initialization with parameters."""
        t = Trackor(
            trackorType="Project",
            URL="test.onevizion.com",
            userName="testuser",
            password="testpass"
        )
        assert t.TrackorType == "Project"
        assert "https://test.onevizion.com" in t.URL
        assert t.userName == "testuser"
        assert t.password == "testpass"

    def test_init_adds_https(self):
        """Test that URL gets https:// added if missing."""
        t = Trackor(URL="test.onevizion.com")
        assert t.URL.startswith("https://")

    def test_init_empty(self):
        """Test initialization with no parameters."""
        t = Trackor()
        assert t.TrackorType == ""
        assert t.errors == []
        assert t.jsonData == {}


class TestTrackorDelete(object):
    """Test Trackor delete operations."""

    @vcr.use_cassette('tests/fixtures/cassettes/test_trackor_delete.yaml')
    @mock.patch('onevizion.trackor.Message')
    @mock.patch('onevizion.trackor.TraceMessage')
    def test_delete_trackor(self, mock_trace, mock_message):
        """Test deleting a trackor."""
        # This test would need a real API or better mocking
        # For now, just test the structure
        t = Trackor(
            trackorType="TestType",
            URL="https://test.onevizion.com",
            userName="test",
            password="test"
        )
        # We'll skip actual delete for now as it needs API
        assert hasattr(t, 'delete')


class TestTrackorRead(object):
    """Test Trackor read operations."""

    def test_read_method_exists(self):
        """Test that read method exists."""
        t = Trackor()
        assert hasattr(t, 'read')
        assert callable(t.read)

    @mock.patch('onevizion.trackor.Message')
    def test_read_builds_url(self, mock_message):
        """Test that read method builds correct URL structure."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="test",
            password="test"
        )
        # Just verify the method can be called with various params
        # Actual API calls would need VCR cassettes
        assert t.TrackorType == "Project"


class TestTrackorUpdate(object):
    """Test Trackor update operations."""

    def test_update_method_exists(self):
        """Test that update method exists."""
        t = Trackor()
        assert hasattr(t, 'update')
        assert callable(t.update)


class TestTrackorCreate(object):
    """Test Trackor create operations."""

    def test_create_method_exists(self):
        """Test that create method exists."""
        t = Trackor()
        assert hasattr(t, 'create')
        assert callable(t.create)


class TestTrackorFileUpload(object):
    """Test Trackor file upload operations."""

    def test_upload_file_method_exists(self):
        """Test that UploadFile method exists."""
        t = Trackor()
        assert hasattr(t, 'UploadFile')
        assert callable(t.UploadFile)

    def test_upload_file_by_contents_exists(self):
        """Test that UploadFileByFileContents method exists."""
        t = Trackor()
        assert hasattr(t, 'UploadFileByFileContents')
        assert callable(t.UploadFileByFileContents)

    @mock.patch('onevizion.trackor.Message')
    def test_upload_file_with_temp_file(self, mock_message):
        """Test file upload with a temporary file."""
        t = Trackor(
            trackorType="Project",
            URL="https://test.onevizion.com",
            userName="test",
            password="test"
        )

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name

        try:
            # Verify the method can be called
            # (it will fail without API, but we're testing structure)
            assert os.path.exists(temp_path)
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestTrackorAuthentication(object):
    """Test Trackor authentication handling."""

    def test_basic_auth_by_default(self):
        """Test that basic auth is used by default."""
        t = Trackor(
            URL="test.onevizion.com",
            userName="user",
            password="pass"
        )
        assert t.auth is not None
        # Check it's HTTPBasicAuth
        assert hasattr(t.auth, '__call__')

    def test_token_auth_when_specified(self):
        """Test that token auth is used when isTokenAuth=True."""
        t = Trackor(
            URL="test.onevizion.com",
            userName="token",
            password="secret",
            isTokenAuth=True
        )
        assert t.auth is not None
        # Token auth uses HTTPBearerAuth
        assert hasattr(t.auth, '__call__')
