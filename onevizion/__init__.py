"""OneVizion API v3 Python Wrapper.

This package provides a comprehensive, production-ready wrapper for the OneVizion
API v3, simplifying integration with OneVizion systems.

Key Features:
    - Full CRUD operations for Trackors, Imports, Exports, WorkPlans, and Tasks
    - Automatic error handling and logging via global Config
    - Support for both Basic Auth and Token-based authentication
    - Python 2.7 and Python 3.x compatible
    - Built-in retry logic and timeout handling via curl wrapper

Quick Start:
    >>> import onevizion
    >>> # Configure verbosity for debug output
    >>> onevizion.Config["Verbosity"] = 1
    >>>
    >>> # Create a Trackor instance
    >>> t = onevizion.Trackor(
    ...     trackorType="PROJECT",
    ...     URL="https://my.onevizion.com",
    ...     userName="user",
    ...     password="pass"
    ... )
    >>>
    >>> # Read trackor data
    >>> t.read(trackorId=12345, fields=["TRACKOR_KEY", "PROJECT_NAME"])
    >>> print(t.jsonData)

Configuration:
    The global Config dictionary controls logging, tracing, and parameters:

    - Config["Verbosity"]: 0=errors only, 1=info, 2=debug
    - Config["Trace"]: OrderedDict tracking all API calls
    - Config["Error"]: Boolean flag set when errors occur
    - Config["ParameterData"]: Optional parameter file data
    - Config["SMTPToken"]: Optional SMTP configuration token

Main Classes:
    - Trackor: CRUD operations for trackor instances
    - Import: Run and monitor import processes
    - Export: Run and monitor export processes
    - WorkPlan: Read and manage workplans
    - Task: Read and update workplan tasks
    - EMail: Send email notifications
    - Singleton: Ensure single process execution
    - curl: Low-level HTTP wrapper with retry/timeout

For more examples, see: https://github.com/Onevizion/api-samples
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import datetime
import json
import os
import smtplib
import sys
import time
import urllib
from collections import OrderedDict
from enum import Enum

import requests

Config = {
	"Verbosity":0,
	"ParameterFile":None,
	"ParameterData":{},
	"SMTPToken":None,
	"Trace":OrderedDict(),
	"Error":False
	}

#Let's add some compatibility between Python 2 and 3
try:
	unicode = unicode
except NameError:
	# 'unicode' is undefined, must be Python 3
	str = str
	unicode = str
	bytes = bytes
	basestring = (str,bytes)
	Config["PythonVer"] = "3"
else:
	# 'unicode' exists, must be Python 2
	str = str
	unicode = unicode
	bytes = str
	basestring = basestring
	Config["PythonVer"] = "2"


Config["Platform"] = sys.platform
if Config["Platform"] != 'win32':
	import fcntl

from onevizion.curl import curl
from onevizion.EMail import EMail
from onevizion.export import Export
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.Import import Import
from onevizion.module.log import IntegrationLog, ModuleLog
from onevizion.module.loglevel import LogLevel
from onevizion.ovimport import OVImport
from onevizion.singleton import Singleton
from onevizion.task import Task
from onevizion.trackor import Trackor
from onevizion.util import *
from onevizion.workplan import WorkPlan

if sys.version_info.major >= 3 and sys.version_info.minor >= 4:
	from onevizion.notif.queue import NotifQueue
	from onevizion.notif.queuerecord import NotifQueueRecord
	from onevizion.notif.queuestatus import NotifQueueStatus
	from onevizion.notif.service import NotificationService


