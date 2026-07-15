"""Tests for onevizion.EMail module."""
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys
import tempfile
import os
from collections import OrderedDict

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import onevizion
from onevizion.EMail import EMail


SMTP_CONFIG = {
    "UserName": "sender@example.com",
    "Password": "secret",
    "Server": "smtp.example.com",
    "Port": "587",
    "Security": "STARTTLS",
}


class TestEMailInit(object):
    """Test EMail.__init__."""

    def setup_method(self, method):
        onevizion.Config["SMTPToken"] = None

    def test_init_defaults(self):
        email = EMail()
        assert email.server == "mail.onevizion.com"
        assert email.port == 587
        assert email.security == "STARTTLS"
        assert email.to == []
        assert email.cc == []
        assert email.files == []
        assert email.message == ""

    def test_init_with_smtp_dict(self):
        email = EMail(SMTP=SMTP_CONFIG)
        assert email.server == "smtp.example.com"
        assert email.userName == "sender@example.com"
        assert email.password == "secret"

    def test_init_with_smtp_token(self):
        onevizion.Config["SMTPToken"] = "mysmtp"
        onevizion.Config["ParameterData"]["mysmtp"] = SMTP_CONFIG.copy()
        email = EMail()
        assert email.server == "smtp.example.com"
        onevizion.Config["SMTPToken"] = None


class TestEMailParameterData(object):
    """Test EMail.parameterData method."""

    def test_parameter_data_sets_server_user_pass(self):
        email = EMail()
        email.parameterData(SMTP_CONFIG)
        assert email.server == "smtp.example.com"
        assert email.userName == "sender@example.com"
        assert email.password == "secret"

    def test_parameter_data_sets_port(self):
        cfg = dict(SMTP_CONFIG, Port="465")
        email = EMail()
        email.parameterData(cfg)
        assert email.port == 465

    def test_parameter_data_sets_security(self):
        cfg = dict(SMTP_CONFIG, Security="SSL")
        email = EMail()
        email.parameterData(cfg)
        assert email.security == "SSL"

    def test_parameter_data_with_tls(self):
        cfg = dict(SMTP_CONFIG, TLS="True")
        email = EMail()
        email.parameterData(cfg)
        assert email.security == "STARTTLS"

    def test_parameter_data_with_from(self):
        cfg = dict(SMTP_CONFIG, **{"From": "from@example.com"})
        email = EMail()
        email.parameterData(cfg)
        assert email.sender == "from@example.com"

    def test_parameter_data_without_from_uses_username(self):
        email = EMail()
        email.parameterData(SMTP_CONFIG)
        assert email.sender == SMTP_CONFIG["UserName"]

    def test_parameter_data_with_to_string(self):
        cfg = dict(SMTP_CONFIG, To="to@example.com")
        email = EMail()
        email.parameterData(cfg)
        assert "to@example.com" in email.to

    def test_parameter_data_with_to_list(self):
        cfg = dict(SMTP_CONFIG, To=["a@example.com", "b@example.com"])
        email = EMail()
        email.parameterData(cfg)
        assert "a@example.com" in email.to
        assert "b@example.com" in email.to

    def test_parameter_data_with_cc_string(self):
        cfg = dict(SMTP_CONFIG, CC="cc@example.com")
        email = EMail()
        email.parameterData(cfg)
        assert "cc@example.com" in email.cc

    def test_parameter_data_with_cc_list(self):
        cfg = dict(SMTP_CONFIG, CC=["cc1@example.com", "cc2@example.com"])
        email = EMail()
        email.parameterData(cfg)
        assert "cc1@example.com" in email.cc

    def test_parameter_data_raises_on_missing_required(self):
        email = EMail()
        with pytest.raises((Exception, TypeError)):
            email.parameterData({"Server": "smtp.example.com"})

    def test_password_data_is_alias_for_parameter_data(self):
        email = EMail()
        email.passwordData(SMTP_CONFIG)
        assert email.server == "smtp.example.com"


class TestEMailSendmail(object):
    """Test EMail.sendmail method."""

    def _make_email(self, security="STARTTLS"):
        email = EMail()
        email.server = "smtp.example.com"
        email.port = 587
        email.security = security
        email.userName = "sender@example.com"
        email.password = "secret"
        email.sender = "sender@example.com"
        email.to = ["recipient@example.com"]
        email.subject = "Test Subject"
        email.message = "Test message body"
        return email

    @mock.patch("smtplib.SMTP")
    def test_sendmail_starttls(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email(security="STARTTLS")
        email.sendmail()
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @mock.patch("smtplib.SMTP")
    def test_sendmail_tls_alias(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email(security="TLS")
        email.sendmail()
        mock_smtp.starttls.assert_called_once()

    @mock.patch("smtplib.SMTP_SSL")
    def test_sendmail_ssl(self, mock_smtp_ssl_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_ssl_cls.return_value = mock_smtp
        email = self._make_email(security="SSL")
        email.sendmail()
        mock_smtp.login.assert_called_once()
        mock_smtp.sendmail.assert_called_once()

    @mock.patch("smtplib.SMTP_SSL")
    def test_sendmail_ssl_tls_alias(self, mock_smtp_ssl_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_ssl_cls.return_value = mock_smtp
        email = self._make_email(security="SSL/TLS")
        email.sendmail()
        mock_smtp_ssl_cls.assert_called_once()

    @mock.patch("smtplib.SMTP")
    def test_sendmail_no_security(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email(security="NONE")
        email.sendmail()
        mock_smtp.starttls.assert_not_called()
        mock_smtp.login.assert_called_once()

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_info_dict(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email()
        email.info = OrderedDict([("Key1", "Value1"), ("Key2", "Value2")])
        email.sendmail()
        assert "Key1" in email.body
        assert "Value1" in email.body

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_multiline_info(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email()
        email.info = OrderedDict([("Report", "line1\nline2\nline3")])
        email.sendmail()
        assert "Report" in email.body

    @mock.patch("smtplib.SMTP")
    def test_sendmail_duration_tracked(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email()
        email.sendmail()
        assert email.duration >= 0

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_sender_empty_uses_username(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email()
        email.sender = ""
        email.sendmail()
        assert email.sender == email.userName

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_text_attachment(self, mock_smtp_cls, tmp_path):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        # Create a temp text file
        txt_file = tmp_path / "report.txt"
        with open(str(txt_file), 'w') as f:
            f.write("col1,col2\nval1,val2\n")
        email = self._make_email()
        email.files = [str(txt_file)]
        email.sendmail()
        mock_smtp.sendmail.assert_called_once()

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_binary_attachment(self, mock_smtp_cls, tmp_path):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        bin_file = tmp_path / "data.bin"
        bin_file.write_bytes(b"\x00\x01\x02\x03")
        email = self._make_email()
        email.files = [str(bin_file)]
        email.sendmail()
        mock_smtp.sendmail.assert_called_once()

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_info_non_string_value(self, mock_smtp_cls):
        mock_smtp = mock.MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        email = self._make_email()
        email.info = OrderedDict([("Count", 42)])
        email.sendmail()
        assert "Count" in email.body
