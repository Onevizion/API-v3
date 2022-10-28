import requests
import urllib
import json
import smtplib
import os
import sys
import datetime
import time
import base64
from collections import OrderedDict
from enum import Enum

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

from onevizion.util import *

from onevizion.singleton import Singleton

from onevizion.curl import curl

from onevizion.httpbearer import HTTPBearerAuth

from onevizion.ovimport import OVImport

from onevizion.trackor import Trackor

from onevizion.workplan import WorkPlan

from onevizion.task import Task

from onevizion.Import import Import

from onevizion.export import Export

from onevizion.EMail import EMail

from onevizion.integration.log import IntegrationLog
from onevizion.integration.loglevel import LogLevel

if sys.version_info.major >= 3 and sys.version_info.minor >= 4:
	from onevizion.notif.service import NotificationService
	from onevizion.notif.queue import NotifQueue
	from onevizion.notif.queuerecord import NotifQueueRecord
	from onevizion.notif.queuestatus import NotifQueueStatus


