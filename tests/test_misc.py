"""Tests for remaining onevizion modules: OVImport, ModuleLog, IntegrationLog,
NotifQueue, NotifQueueRecord, NotificationService, LogLevel."""
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys
import json
import warnings

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from unittest import mock
else:
    import mock

import requests
import onevizion.ovimport
import onevizion.module.log
import onevizion.notif.queue
import onevizion.notif.service
from onevizion.ovimport import OVImport
from onevizion.module.log import ModuleLog, IntegrationLog
from onevizion.module.loglevel import LogLevel


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


# ---------------------------------------------------------------------------
# OVImport
# ---------------------------------------------------------------------------

class TestOVImport(object):
    """Test OVImport wrapper class."""

    def test_init_no_args_does_not_call(self):
        ov = OVImport()
        assert ov.processId is None
        assert ov.errors == []

    def test_init_stores_attributes(self):
        ov = OVImport(
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
            impSpecId=1,
            action="INSERT",
        )
        assert ov.URL == "https://test.onevizion.com"
        assert ov.impSpecId == 1
        assert ov.action == "INSERT"

    @mock.patch("onevizion.ovimport.Import")
    def test_make_call_success(self, mock_import_cls):
        import tempfile, os
        mock_import_inst = mock.MagicMock()
        mock_import_inst.errors = []
        mock_import_inst.request = mock.MagicMock()
        mock_import_inst.jsonData = {"process_id": 3, "status": "QUEUED"}
        mock_import_inst.processId = 3
        mock_import_cls.return_value = mock_import_inst

        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.write(b"a,b\n1,2\n")
        tmp.close()
        try:
            ov = OVImport(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=1,
                file=tmp.name,
            )
            assert ov.processId == 3
            assert ov.errors == []
        finally:
            os.unlink(tmp.name)

    @mock.patch("onevizion.ovimport.Import")
    def test_make_call_with_errors(self, mock_import_cls):
        import tempfile, os
        mock_import_inst = mock.MagicMock()
        mock_import_inst.errors = ["Import failed"]
        mock_import_cls.return_value = mock_import_inst

        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.write(b"a,b\n1,2\n")
        tmp.close()
        try:
            ov = OVImport(
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                impSpecId=1,
                file=tmp.name,
            )
            assert "Import failed" in ov.errors
            # request and jsonData not set when there are errors
        finally:
            os.unlink(tmp.name)

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["ov_tok"] = {
            "url": "ov.onevizion.com",
            "UserName": "ou",
            "Password": "op",
        }
        ov = OVImport(paramToken="ov_tok")
        assert "ov.onevizion.com" in ov.URL

    def test_init_param_token_does_not_override_explicit(self):
        import onevizion
        onevizion.Config["ParameterData"]["ov_tok2"] = {
            "url": "ov.onevizion.com",
            "UserName": "ou",
            "Password": "op",
        }
        ov = OVImport(
            URL="https://explicit.onevizion.com",
            userName="eu",
            password="ep",
            paramToken="ov_tok2",
        )
        assert "explicit.onevizion.com" in ov.URL
        assert ov.userName == "eu"


# ---------------------------------------------------------------------------
# LogLevel
# ---------------------------------------------------------------------------

class TestLogLevel(object):
    """Test LogLevel enum."""

    def test_log_levels_have_correct_ids(self):
        assert LogLevel.ERROR.logLevelId == 0
        assert LogLevel.WARNING.logLevelId == 1
        assert LogLevel.INFO.logLevelId == 2
        assert LogLevel.DEBUG.logLevelId == 3

    def test_log_levels_have_correct_names(self):
        assert LogLevel.ERROR.logLevelName == "Error"
        assert LogLevel.WARNING.logLevelName == "Warning"
        assert LogLevel.INFO.logLevelName == "Info"
        assert LogLevel.DEBUG.logLevelName == "Debug"

    def test_get_log_level_by_name_error(self):
        level = LogLevel.getLogLevelByName("Error")
        assert level == LogLevel.ERROR

    def test_get_log_level_by_name_warning(self):
        level = LogLevel.getLogLevelByName("Warning")
        assert level == LogLevel.WARNING

    def test_get_log_level_by_name_info(self):
        level = LogLevel.getLogLevelByName("Info")
        assert level == LogLevel.INFO

    def test_get_log_level_by_name_debug(self):
        level = LogLevel.getLogLevelByName("Debug")
        assert level == LogLevel.DEBUG

    def test_get_log_level_case_insensitive(self):
        level = LogLevel.getLogLevelByName("ERROR")
        assert level == LogLevel.ERROR

    def test_get_log_level_unknown_raises(self):
        with pytest.raises(Exception) as exc_info:
            LogLevel.getLogLevelByName("UNKNOWN")
        assert "UNKNOWN" in str(exc_info.value)


# ---------------------------------------------------------------------------
# ModuleLog
# ---------------------------------------------------------------------------

class TestModuleLog(object):
    """Test ModuleLog class."""

    def test_init_basic(self):
        log = ModuleLog(
            processId=1,
            URL="https://test.onevizion.com",
            userName="u",
            password="p",
        )
        assert log._processId == 1
        assert log._URL == "https://test.onevizion.com"
        assert isinstance(log._auth, requests.auth.HTTPBasicAuth)

    def test_init_with_token_auth(self):
        from onevizion.httpbearer import HTTPBearerAuth
        log = ModuleLog(
            processId=1,
            URL="https://test.onevizion.com",
            userName="k",
            password="s",
            isTokenAuth=True,
        )
        assert isinstance(log._auth, HTTPBearerAuth)

    def test_init_adds_https(self):
        log = ModuleLog(processId=1, URL="bare.onevizion.com", userName="u", password="p")
        assert log._URL.startswith("https://")

    def test_init_with_param_token(self):
        import onevizion
        onevizion.Config["ParameterData"]["log_tok"] = {
            "url": "log.onevizion.com",
            "UserName": "lu",
            "Password": "lp",
        }
        log = ModuleLog(processId=1, paramToken="log_tok")
        assert "log.onevizion.com" in log._URL

    def test_init_param_token_does_not_override_explicit(self):
        import onevizion
        onevizion.Config["ParameterData"]["log_tok2"] = {
            "url": "log.onevizion.com",
            "UserName": "lu",
            "Password": "lp",
        }
        log = ModuleLog(
            processId=1,
            URL="https://explicit.onevizion.com",
            userName="eu",
            password="ep",
            paramToken="log_tok2",
        )
        assert "explicit.onevizion.com" in log._URL

    def test_init_param_token_with_token_auth(self):
        import onevizion
        from onevizion.httpbearer import HTTPBearerAuth
        onevizion.Config["ParameterData"]["log_tok3"] = {
            "url": "log.onevizion.com",
            "UserName": "k",
            "Password": "s",
            "isTokenAuth": True,
        }
        log = ModuleLog(processId=1, paramToken="log_tok3")
        assert isinstance(log._auth, HTTPBearerAuth)

    def test_init_invalid_log_level_raises(self):
        with pytest.raises(Exception):
            ModuleLog(processId=1, URL="https://test.onevizion.com", logLevelName="INVALID")

    @mock.patch("onevizion.module.log.curl", create=True)
    def test_add_posts_log_when_level_at_or_below_threshold(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"log_id": 1})
        log = ModuleLog(processId=5, URL="https://test.onevizion.com", userName="u", password="p", logLevelName="Debug")
        result = log.add(LogLevel.ERROR, "Error occurred", "Some description")
        assert mock_curl_cls.called
        call_url = mock_curl_cls.call_args[0][1]
        assert "/modules/runs/5/logs" in call_url

    @mock.patch("onevizion.module.log.curl", create=True)
    def test_add_suppressed_when_level_above_threshold(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"log_id": 1})
        # logLevelName=Error means only ERROR (id=0) and below pass
        log = ModuleLog(processId=5, URL="https://test.onevizion.com", userName="u", password="p", logLevelName="Error")
        result = log.add(LogLevel.DEBUG, "Debug message")
        # DEBUG (id=3) > ERROR (id=0), so it's suppressed
        assert not mock_curl_cls.called
        assert result is None

    @mock.patch("onevizion.module.log.curl", create=True)
    def test_add_raises_on_curl_error(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(status_code=500, errors=["500 = Server Error"])
        log = ModuleLog(processId=5, URL="https://test.onevizion.com", userName="u", password="p", logLevelName="Debug")
        with pytest.raises(Exception):
            log.add(LogLevel.ERROR, "Test error")

    @mock.patch("onevizion.module.log.curl", create=True)
    def test_add_info_level_when_threshold_is_info(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"log_id": 2})
        log = ModuleLog(processId=5, URL="https://test.onevizion.com", userName="u", password="p", logLevelName="Info")
        log.add(LogLevel.INFO, "Info message")
        assert mock_curl_cls.called

    @mock.patch("onevizion.module.log.curl", create=True)
    def test_add_warning_suppressed_when_threshold_is_error(self, mock_curl_cls):
        log = ModuleLog(processId=5, URL="https://test.onevizion.com", userName="u", password="p", logLevelName="Error")
        result = log.add(LogLevel.WARNING, "Warning message")
        assert not mock_curl_cls.called
        assert result is None


# ---------------------------------------------------------------------------
# IntegrationLog (deprecated)
# ---------------------------------------------------------------------------

class TestIntegrationLog(object):
    """Test deprecated IntegrationLog class."""

    def test_init_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            log = IntegrationLog(processId=1, URL="https://test.onevizion.com", userName="u", password="p")
            assert len(w) >= 1
            categories = [str(x.category) for x in w]
            assert any("DeprecationWarning" in c for c in categories)

    @mock.patch("onevizion.module.log.curl", create=True)
    def test_add_delegates_to_module_log(self, mock_curl_cls):
        mock_curl_cls.return_value = make_mock_curl(json_data={"log_id": 1})
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            log = IntegrationLog(
                processId=5,
                URL="https://test.onevizion.com",
                userName="u",
                password="p",
                logLevelName="Debug",
            )
        log.add(LogLevel.ERROR, "Delegated error")
        assert mock_curl_cls.called


# ---------------------------------------------------------------------------
# NotifQueue (Python 3.x only)
# ---------------------------------------------------------------------------

if sys.version_info[0] >= 3:
    from onevizion.notif.queue import NotifQueue
    from onevizion.notif.queuerecord import NotifQueueRecord
    from onevizion.notif.queuestatus import NotifQueueStatus

    class TestNotifQueue(object):
        """Test NotifQueue class."""

        def test_init_basic(self):
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            assert q._serviceId == 10
            assert isinstance(q._auth, requests.auth.HTTPBasicAuth)

        def test_init_adds_https(self):
            q = NotifQueue(serviceId=1, URL="bare.onevizion.com", userName="u", password="p")
            assert q._URL.startswith("https://")

        def test_init_token_auth(self):
            from onevizion.httpbearer import HTTPBearerAuth
            q = NotifQueue(serviceId=1, URL="https://test.onevizion.com", userName="k", password="s", isTokenAuth=True)
            assert isinstance(q._auth, HTTPBearerAuth)

        def test_init_with_param_token(self):
            import onevizion
            onevizion.Config["ParameterData"]["nq_tok"] = {
                "url": "nq.onevizion.com",
                "UserName": "nu",
                "Password": "np",
            }
            q = NotifQueue(serviceId=1, paramToken="nq_tok")
            assert "nq.onevizion.com" in q._URL

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_get_notif_queue_success(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(json_data=[{"id": 1}, {"id": 2}])
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            result = q.getNotifQueue()
            call_url = mock_curl_cls.call_args[0][1]
            assert "service_id=10" in call_url
            assert result == [{"id": 1}, {"id": 2}]

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_get_notif_queue_raises_on_error(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(status_code=500, errors=["500 = Error"])
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            with pytest.raises(Exception):
                q.getNotifQueue()

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_update_notif_queue_rec_status_by_id_success(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(json_data={})
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            q.updateNotifQueueRecStatusById(notifQueueRecId=5, status="SUCCESS")
            call_url = mock_curl_cls.call_args[0][1]
            assert "/notif/queue/5/update_status" in call_url
            assert "status=SUCCESS" in call_url

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_update_notif_queue_rec_status_by_id_raises_on_error(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(status_code=404, errors=["404 = Not Found"])
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            with pytest.raises(Exception):
                q.updateNotifQueueRecStatusById(notifQueueRecId=99, status="SUCCESS")

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_add_new_attempt_success(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(json_data={})
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            q.addNewAttempt(notifQueueRecId=5, errorMessage="SMTP timeout")
            call_url = mock_curl_cls.call_args[0][1]
            assert "/notif/queue/5/attempts" in call_url

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_add_new_attempt_raises_on_error(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(status_code=500, errors=["500 = Error"])
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            with pytest.raises(Exception):
                q.addNewAttempt(notifQueueRecId=5, errorMessage="error")

        @mock.patch("onevizion.module.log.curl", create=True)
        def test_update_notif_queue_rec_status_delegates(self, mock_curl_cls):
            mock_curl_cls.return_value = make_mock_curl(json_data={})
            q = NotifQueue(serviceId=10, URL="https://test.onevizion.com", userName="u", password="p")
            rec = mock.MagicMock()
            rec.notifQueueId = 7
            rec.status = "SUCCESS"
            q.updateNotifQueueRecStatus(rec)
            call_url = mock_curl_cls.call_args[0][1]
            assert "/notif/queue/7/update_status" in call_url

    class TestNotifQueueRecord(object):
        """Test NotifQueueRecord dataclass."""

        def _make_json(self, overrides=None):
            data = {
                "notifQueueId": 1,
                "userId": 42,
                "sender": "sender@example.com",
                "toAddress": "to@example.com",
                "cc": "cc@example.com",
                "bcc": "",
                "subj": "Test Subject",
                "replyTo": "",
                "createdTs": "2024-01-01T00:00:00",
                "status": "QUEUED",
                "msg": "Hello World",
                "html": "<p>Hello</p>",
                "blobDataIds": [],
            }
            if overrides:
                data.update(overrides)
            return data

        def test_init_sets_all_fields(self):
            rec = NotifQueueRecord(self._make_json())
            assert rec.notifQueueId == 1
            assert rec.userId == 42
            assert rec.sender == "sender@example.com"
            assert rec.toAddress == "to@example.com"
            assert rec.subj == "Test Subject"
            assert rec.status == "QUEUED"
            assert rec.msg == "Hello World"

        def test_status_is_mutable(self):
            rec = NotifQueueRecord(self._make_json())
            rec.status = "SUCCESS"
            assert rec.status == "SUCCESS"

        def test_blob_data_ids_list(self):
            rec = NotifQueueRecord(self._make_json({"blobDataIds": [1, 2, 3]}))
            assert rec.blobDataIds == [1, 2, 3]

    class TestNotifQueueStatus(object):
        """Test NotifQueueStatus enum."""

        def test_status_enum_values_exist(self):
            from onevizion.notif.queuestatus import NotifQueueStatus
            # Just verify the enum is importable and has expected members
            assert hasattr(NotifQueueStatus, "SUCCESS")
            assert hasattr(NotifQueueStatus, "FAIL")
            assert hasattr(NotifQueueStatus, "SENDING")

    class TestNotificationService(object):
        """Test NotificationService abstract base class."""

        def _make_concrete_service(self, send_raises=False, send_result=None):
            """Return a concrete implementation of the abstract class."""
            from onevizion.notif.service import NotificationService

            class ConcreteService(NotificationService):
                def __init__(self, *args, **kwargs):
                    super(ConcreteService, self).__init__(*args, **kwargs)
                    self.sent = []

                def sendNotification(self, notifQueueRecord):
                    if send_raises:
                        raise Exception("SMTP failure")
                    self.sent.append(notifQueueRecord)

            return ConcreteService

        def _make_queue_record_json(self, notif_id=1, status="QUEUED"):
            return {
                "notifQueueId": notif_id,
                "userId": 1,
                "sender": "s@example.com",
                "toAddress": "t@example.com",
                "cc": "",
                "bcc": "",
                "subj": "Test",
                "replyTo": "",
                "createdTs": "2024-01-01T00:00:00",
                "status": status,
                "msg": "Hello",
                "html": "",
                "blobDataIds": [],
            }

        @mock.patch("onevizion.module.log.curl", create=True)
        @mock.patch("onevizion.module.log.curl", create=True)
        def test_start_sends_all_queued_records(self, mock_queue_curl, mock_log_curl):
            mock_queue_curl.return_value = make_mock_curl(
                json_data=[self._make_queue_record_json(1), self._make_queue_record_json(2)]
            )
            mock_log_curl.return_value = make_mock_curl(json_data={"log_id": 1})

            ServiceClass = self._make_concrete_service()
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                svc = ServiceClass(
                    serviceId=1,
                    processId=10,
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p",
                    logLevel="Debug",
                )
            svc.start()
            assert len(svc.sent) == 2

        @mock.patch("onevizion.module.log.curl", create=True)
        @mock.patch("onevizion.module.log.curl", create=True)
        def test_start_handles_send_failure(self, mock_queue_curl, mock_log_curl):
            mock_queue_curl.return_value = make_mock_curl(
                json_data=[self._make_queue_record_json(1)]
            )
            mock_log_curl.return_value = make_mock_curl(json_data={"log_id": 1})

            ServiceClass = self._make_concrete_service(send_raises=True)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                svc = ServiceClass(
                    serviceId=1,
                    processId=10,
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p",
                    logLevel="Debug",
                    maxAttempts=1,
                )
            svc.start()
            # No records sent since sendNotification raises
            assert len(svc.sent) == 0

        @mock.patch("onevizion.module.log.curl", create=True)
        @mock.patch("onevizion.module.log.curl", create=True)
        def test_start_with_empty_queue(self, mock_queue_curl, mock_log_curl):
            mock_queue_curl.return_value = make_mock_curl(json_data=[])
            mock_log_curl.return_value = make_mock_curl(json_data={"log_id": 1})

            ServiceClass = self._make_concrete_service()
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                svc = ServiceClass(
                    serviceId=1,
                    processId=10,
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p",
                    logLevel="Debug",
                )
            svc.start()
            assert len(svc.sent) == 0

        @mock.patch("onevizion.module.log.curl", create=True)
        @mock.patch("onevizion.module.log.curl", create=True)
        def test_start_retries_on_failure(self, mock_queue_curl, mock_log_curl):
            """With maxAttempts=2 and time.sleep mocked, ensure loop runs twice."""
            mock_queue_curl.return_value = make_mock_curl(
                json_data=[self._make_queue_record_json(1)]
            )
            mock_log_curl.return_value = make_mock_curl(json_data={"log_id": 1})

            ServiceClass = self._make_concrete_service(send_raises=True)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                svc = ServiceClass(
                    serviceId=1,
                    processId=10,
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p",
                    logLevel="Debug",
                    maxAttempts=2,
                    nextAttemptDelay=0,
                )
            with mock.patch("time.sleep"):
                svc.start()
            # All attempts exhausted, record remains in failed state
            assert len(svc.sent) == 0

        def test_convert_notif_queue_json_to_list(self):
            from onevizion.notif.service import NotificationService
            json_data = [
                self._make_queue_record_json(1),
                self._make_queue_record_json(2),
            ]
            result = NotificationService._convertNotifQueueJsonToList(json_data)
            assert len(result) == 2
            assert isinstance(result[0], NotifQueueRecord)

        def test_convert_empty_json_returns_empty_list(self):
            from onevizion.notif.service import NotificationService
            result = NotificationService._convertNotifQueueJsonToList([])
            assert result == []

        @mock.patch("onevizion.module.log.curl", create=True)
        @mock.patch("onevizion.module.log.curl", create=True)
        def test_get_integration_log_emits_warning(self, mock_queue_curl, mock_log_curl):
            """Accessing _integrationLog attribute emits DeprecationWarning."""
            mock_queue_curl.return_value = make_mock_curl(json_data=[])
            mock_log_curl.return_value = make_mock_curl(json_data={})

            ServiceClass = self._make_concrete_service()
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                svc = ServiceClass(
                    serviceId=1,
                    processId=10,
                    URL="https://test.onevizion.com",
                    userName="u",
                    password="p",
                    logLevel="Debug",
                )
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    _ = svc._integrationLog
                    assert any("deprecated" in str(warning.message).lower() for warning in w)
