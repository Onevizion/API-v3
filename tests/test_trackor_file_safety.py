"""Tests for file safety features in trackor.

Tests demonstrate:
- File size validation prevents uploading/downloading huge files
- Atomic file writes prevent corrupt partial downloads
"""
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import os
import tempfile
import shutil

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

from onevizion.trackor import Trackor


class TestFileSizeValidation(object):
    """Test file size limits for uploads and downloads."""

    def test_upload_rejects_oversized_file(self):
        """UploadFile should reject files exceeding max_file_size."""
        # Create a test file larger than limit
        tmpdir = tempfile.mkdtemp()
        try:
            large_file = os.path.join(tmpdir, 'large.bin')
            with open(large_file, 'wb') as f:
                f.write(b'x' * (11 * 1024 * 1024))  # 11 MB file

            t = Trackor(
                trackorType="Project",
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                max_file_size=10 * 1024 * 1024  # 10 MB limit
            )

            # Should fail without making HTTP request
            with mock.patch("onevizion.trackor.curl") as mock_curl:
                t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=large_file)

                # Should not attempt upload
                assert not mock_curl.called, "Should not make HTTP request for oversized file"
                assert len(t.errors) > 0, "Should have error"
                assert "file size" in t.errors[0].lower() or "too large" in t.errors[0].lower()
        finally:
            shutil.rmtree(tmpdir)

    def test_upload_accepts_file_within_limit(self):
        """UploadFile should accept files within max_file_size."""
        tmpdir = tempfile.mkdtemp()
        try:
            small_file = os.path.join(tmpdir, 'small.txt')
            with open(small_file, 'wb') as f:
                f.write(b'small content')

            mock_curl_instance = mock.MagicMock()
            mock_curl_instance.errors = []
            mock_curl_instance.jsonData = {"blob_data_id": 123}
            mock_curl_instance.duration = 0.5
            mock_curl_instance.request = mock.MagicMock(status_code=200)

            with mock.patch("onevizion.trackor.curl", return_value=mock_curl_instance):
                t = Trackor(
                    trackorType="Project",
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p",
                    max_file_size=10 * 1024 * 1024  # 10 MB limit
                )
                t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=small_file)

                # Should succeed
                assert len(t.errors) == 0, "Should not have errors for file within limit"
        finally:
            shutil.rmtree(tmpdir)

    def test_download_rejects_oversized_response(self):
        """GetFile should reject downloads exceeding max_file_size."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-length': str(15 * 1024 * 1024),  # 15 MB
            'content-disposition': 'filename=large.bin'
        }
        mock_response.iter_content.return_value = [b'x' * 1024] * 100

        with mock.patch("onevizion.trackor.requests.get", return_value=mock_response):
            t = Trackor(
                trackorType="Project",
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                max_file_size=10 * 1024 * 1024  # 10 MB limit
            )
            result = t.GetFile(trackorId=10, fieldName="F_FILE")

            # Should reject
            assert result is None, "Should not download oversized file"
            assert len(t.errors) > 0, "Should have error"
            assert "file size" in t.errors[0].lower() or "too large" in t.errors[0].lower()

    def test_default_no_size_limit(self):
        """By default, no file size limit (backward compatible)."""
        tmpdir = tempfile.mkdtemp()
        try:
            large_file = os.path.join(tmpdir, 'large.bin')
            with open(large_file, 'wb') as f:
                f.write(b'x' * (100 * 1024 * 1024))  # 100 MB

            mock_curl_instance = mock.MagicMock()
            mock_curl_instance.errors = []
            mock_curl_instance.jsonData = {"blob_data_id": 123}
            mock_curl_instance.duration = 0.5
            mock_curl_instance.request = mock.MagicMock(status_code=200)

            with mock.patch("onevizion.trackor.curl", return_value=mock_curl_instance):
                t = Trackor(
                    trackorType="Project",
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p"
                    # No max_file_size specified
                )
                t.UploadFile(trackorId=10, fieldName="F_FILE", fileName=large_file)

                # Should not reject (no limit)
                assert len(t.errors) == 0, "Should allow large files when no limit set"
        finally:
            shutil.rmtree(tmpdir)


class TestAtomicFileWrites(object):
    """Test atomic file writes prevent corrupt partial downloads."""

    def test_download_uses_temp_file_then_renames(self):
        """GetFile should write to .tmp then rename on success."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-disposition': 'filename=data.csv'}
        mock_response.iter_content.return_value = [b'data']

        with mock.patch("onevizion.trackor.requests.get", return_value=mock_response):
            with mock.patch("builtins.open" if sys.version_info[0] >= 3 else "__builtin__.open", mock.mock_open()) as mock_file:
                with mock.patch("os.rename") as mock_rename:
                    t = Trackor(
                        trackorType="Project",
                        URL="https://test.onevizion.com",
                        userName="u",
                        password="p"
                    )
                    result = t.GetFile(trackorId=10, fieldName="F_FILE")

                    # Should rename from .tmp to final name
                    assert mock_rename.called, "Should rename temp file to final name"
                    assert result == "data.csv"

    def test_download_cleans_up_temp_on_error(self):
        """GetFile should remove .tmp file if download fails."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.reason = "Server Error"
        mock_response.headers = {}

        tmpdir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            with mock.patch("onevizion.trackor.requests.get", return_value=mock_response):
                t = Trackor(
                    trackorType="Project",
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p"
                )
                result = t.GetFile(trackorId=10, fieldName="F_FILE")

                # Should not leave .tmp file behind
                tmp_files = [f for f in os.listdir('.') if f.endswith('.tmp')]
                assert len(tmp_files) == 0, "Should clean up .tmp file on error"
                assert result is None, "Should return None on error"
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmpdir)
